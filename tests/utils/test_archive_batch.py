import os

import pytest

from app.archive import batch
from app.transcripts.build import build_transcript

pytest.importorskip("jsonschema")

MODEL = {"engine": "fake", "name": "f", "settings": {}}


def row(sermon_id, date, status="ready", key=None, problems=()):
    return {
        "sermon_id": sermon_id, "date": date, "title": f"Sermon {sermon_id}", "status": status,
        "s3_key": key or f"{date[:4]}/{date}.mp3", "problems": list(problems),
    }


def raw_words(count=300):
    return [(i * 0.3, i * 0.3 + 0.25, f" word{i}" + ("." if (i + 1) % 12 == 0 else ""), 0.9) for i in range(count)]


class Env:
    def __init__(self, tmp_path):
        self.archive = str(tmp_path / "archive")
        self.cache = str(tmp_path / "cache")
        os.makedirs(self.archive)
        self.state_path = os.path.join(self.archive, "batch_state.json")
        self.state = batch.load_state(self.state_path)
        self.seen_audio = []
        self.fail_on = set()
        self.interrupt_on = None
        self.logged = []

    def download(self, r, dest):
        with open(dest, "wb") as handle:
            handle.write(b"fake audio " + r["sermon_id"].encode())
        self.seen_audio.append(dest)

    def transcribe(self, path):
        name = os.path.basename(path)
        if any(name.startswith(f) for f in self.fail_on):
            raise RuntimeError("engine blew up")
        if self.interrupt_on and name.startswith(self.interrupt_on):
            raise KeyboardInterrupt
        return raw_words(), MODEL

    def run(self, todo):
        return batch.run(
            todo, self.archive, self.cache, self.state, self.state_path,
            transcribe_fn=self.transcribe, duration_fn=lambda p: 120.0, print_fn=self.logged.append, download_fn=self.download,
        )

    def plan(self, rows, **kw):
        return batch.plan(rows, self.archive, self.state, **kw)


def test_plan_orders_newest_first_and_skips_blocked_and_shared(tmp_path):
    env = Env(tmp_path)
    rows = [
        row("a", "2020-01-05"), row("b", "2022-01-02"),
        row("c", "2021-01-03", status="problem", problems=["file_not_found"]),
        row("d", "2019-01-06", key="2020/2020-01-05.mp3"),  # same file as "a"
    ]
    todo, skipped = env.plan(rows)
    assert [r["sermon_id"] for r in todo] == ["b", "a"]
    reasons = {r["sermon_id"]: why for r, why in skipped}
    assert reasons["c"].startswith("blocked") and reasons["d"].startswith("shared_file")


def test_plan_filters_and_limit(tmp_path):
    env = Env(tmp_path)
    rows = [row("a", "2020-01-05"), row("b", "2021-01-03"), row("c", "2022-01-02")]
    assert [r["sermon_id"] for r in env.plan(rows, years={"2021"})[0]] == ["b"]
    assert [r["sermon_id"] for r in env.plan(rows, only={"2020-01-05"})[0]] == ["a"]
    assert len(env.plan(rows, limit=2)[0]) == 2


def test_run_writes_transcripts_removes_downloads_and_second_run_does_nothing(tmp_path):
    env = Env(tmp_path)
    rows = [row("a", "2020-01-05"), row("b", "2021-01-03")]
    todo, _ = env.plan(rows)
    assert env.run(todo) == 2
    for r in rows:
        assert batch.is_done(env.archive, r)
    assert not [f for f in os.listdir(env.cache)]  # downloads deleted
    assert env.state["sermons"]["a"]["status"] == "done" and env.state["sermons"]["a"]["words"] == 300
    todo, skipped = env.plan(rows)
    assert todo == [] and all(why == "done" for _, why in skipped)


def test_a_failed_file_does_not_stop_the_batch_and_shows_in_the_report(tmp_path):
    env = Env(tmp_path)
    env.fail_on = {"b"}
    rows = [row("a", "2020-01-05"), row("b", "2021-01-03"), row("c", "2022-01-02")]
    todo, skipped = env.plan(rows)
    assert env.run(todo) == 2
    assert env.state["sermons"]["b"]["status"] == "failed" and "engine blew up" in env.state["sermons"]["b"]["error"]
    assert not [f for f in os.listdir(env.cache)]
    text = batch.report(rows, env.archive, env.state, skipped)
    assert "Failed: 1" in text and "engine blew up" in text


def test_failed_sermon_is_retried_then_parked_after_three_attempts(tmp_path):
    env = Env(tmp_path)
    env.fail_on = {"a"}
    rows = [row("a", "2020-01-05")]
    for attempt in (1, 2, 3):
        todo, _ = env.plan(rows)
        assert len(todo) == 1
        env.run(todo)
        assert env.state["sermons"]["a"]["attempts"] == attempt
    todo, skipped = env.plan(rows)
    assert todo == [] and "failed 3 times" in skipped[0][1]
    assert len(env.plan(rows, retry_failed=True)[0]) == 1


def test_stopping_mid_sermon_leaves_nothing_half_done_and_a_rerun_finishes(tmp_path):
    env = Env(tmp_path)
    env.interrupt_on = "b"
    rows = [row("a", "2022-01-02"), row("b", "2021-01-03"), row("c", "2020-01-05")]
    todo, _ = env.plan(rows)
    with pytest.raises(KeyboardInterrupt):
        env.run(todo)
    assert batch.is_done(env.archive, rows[0]) and not batch.is_done(env.archive, rows[1])
    assert not [f for f in os.listdir(env.cache)]
    leftovers = [f for d, _, fs in os.walk(env.archive) for f in fs if f.endswith(".part")]
    assert leftovers == []
    env.interrupt_on = None
    todo, _ = env.plan(rows)
    assert [r["sermon_id"] for r in todo] == ["b", "c"]
    assert env.run(todo) == 2 and all(batch.is_done(env.archive, r) for r in rows)


def test_redo_transcribes_a_finished_sermon_again(tmp_path):
    env = Env(tmp_path)
    rows = [row("a", "2020-01-05")]
    env.run(env.plan(rows)[0])
    assert env.plan(rows)[0] == []
    assert len(env.plan(rows, redo={"a"})[0]) == 1


def test_sparse_windows_flags_quiet_stretches_but_not_the_edges():
    dense = [(i * 0.3, i * 0.3 + 0.25, f"w{i}", 0.9) for i in range(2000)]  # 0 to 600 s
    words = [w for w in dense if not (200 <= w[0] < 240)]  # a 40 second hole in the middle
    transcript = build_transcript(words, "s", "2020-01-05", {"file": "a", "sha256": "0" * 64, "duration_seconds": 600}, MODEL)
    flagged = batch.sparse_windows(transcript, 600)
    assert flagged and all(200 <= w["start_seconds"] < 240 for w in flagged)
    quiet_start = [w for w in dense if w[0] > 80]  # nothing in the first 80 s: edge, ignored
    t2 = build_transcript(quiet_start, "s", "2020-01-05", {"file": "a", "sha256": "0" * 64, "duration_seconds": 600}, MODEL)
    assert batch.sparse_windows(t2, 600) == []


def test_dry_run_text_counts_and_estimates(tmp_path):
    env = Env(tmp_path)
    rows = [row("a", "2020-01-05"), row("b", "2021-01-03", status="problem", problems=["file_not_found"])]
    todo, skipped = env.plan(rows)
    text = batch.dry_run_text(todo, skipped)
    assert "Would transcribe 1 sermons" in text and "blocked 1" in text and "2m 00s" in text
