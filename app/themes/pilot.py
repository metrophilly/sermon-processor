"""
Theme suggestions for sermons (DT-259, DT-273). Pilot tooling.

Boundaries (see Linear DT-273 and docs/theme-pilot-plan.md):
- The passage is fixed first. It comes from the authored Sanity field. The model never
  proposes a passage, and nothing here stores one from a transcript.
- Every result is a suggestion. Only a person approves a theme.
- Code, not the model, checks that each quote exists in the paragraph it cites.

A runner turns (prompt, sermon input) into the model's raw text. Today that is a Claude Code
subagent, started by hand. `ApiRunner` is the same interface for the Anthropic API.
Everything else (input, parsing, checks, report) is the same for both.

Files per sermon, under output/themes/<set>/<sermon_id>/:
  input.md      what the model reads (passage, title, numbered paragraphs)
  raw.json      what the model wrote
  meta.json     prompt version, runner, model
  checked.json  suggestions that passed the quote check, plus dropped ones and problems
"""

import datetime
import glob
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROMPT_VERSION = "v1"
CONFIDENCE = {"high", "medium", "low"}
MAX_EVIDENCE = 3


class ThemeError(Exception):
    pass


def prompt_path(version=PROMPT_VERSION):
    return os.path.join(ROOT, "config", f"theme_prompt_{version}.md")


def load_prompt(version=PROMPT_VERSION):
    with open(prompt_path(version), encoding="utf-8") as handle:
        return handle.read()


def _load(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def sermon_context(archive_dir, sermon_id):
    """Everything the model and the checks need for one sermon. Reads local files only."""
    sanity = {r["_id"].replace("drafts.", "", 1): r for r in _load(os.path.join(archive_dir, "sanity_sermons.json"))}
    doc = sanity.get(sermon_id)
    if not doc:
        raise ThemeError(f"{sermon_id}: not in the Sanity export")
    found = glob.glob(os.path.join(archive_dir, "transcripts", sermon_id, "*.transcript.json"))
    if not found:
        raise ThemeError(f"{sermon_id}: no transcript")
    transcript = _load(found[0])
    edited_path = found[0].replace(".transcript.json", ".edited.json")
    edited = {p["id"]: p["text"] for p in _load(edited_path)["paragraphs"]} if os.path.exists(edited_path) else {}
    speaker = doc.get("speaker") or {}
    return {
        "sermon_id": sermon_id,
        "date": transcript["date"],
        "title": doc.get("title") or "",
        "passage": doc["passage"],
        "series": doc.get("series") or "",
        "speaker": " ".join(x for x in (speaker.get("firstName"), speaker.get("lastName")) if x),
        "word_count": transcript["word_count"],
        "paragraphs": [
            {"id": p["id"], "start_ms": p["start_ms"], "text": edited.get(p["id"], p["text"]), "raw": p["text"]}
            for p in transcript["paragraphs"]
        ],
    }


def build_input(ctx):
    """The text the model reads. Paragraph IDs let it cite evidence."""
    lines = [
        f"Sermon date: {ctx['date']}",
        f"Preacher: {ctx['speaker']}",
        f"Series: {ctx['series']}",
        f"Title: {ctx['title']}",
        f"Authored passage: {ctx['passage']}",
        "",
        "Transcript, by paragraph:",
        "",
    ]
    lines += [f"[{p['id']}] {p['text']}\n" for p in ctx["paragraphs"]]
    return "\n".join(lines)


def parse_output(text):
    """The model's JSON object, tolerating a code fence or stray words around it."""
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ThemeError("No JSON object in the model output")
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError as error:
        raise ThemeError(f"The model output is not valid JSON: {error}") from error


def _norm(text):
    text = text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    return re.sub(r"\s+", " ", text).strip().lower()


def check_result(result, paragraphs):
    """Keep themes whose quotes really appear in the paragraphs they cite. Drop the rest.

    This proves the evidence exists. It does not prove the reading is right.
    """
    by_id = {p["id"]: p for p in paragraphs}
    kept, dropped, problems = [], [], []
    themes = result.get("themes")
    if not isinstance(themes, list):
        raise ThemeError("`themes` is missing or is not a list")
    for theme in themes:
        label = str(theme.get("label", "")).strip()
        reasons = []
        if not label:
            reasons.append("no label")
        if not str(theme.get("why", "")).strip():
            reasons.append("no reason")
        if theme.get("confidence") not in CONFIDENCE:
            reasons.append("confidence is not high, medium or low")
        evidence = theme.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            reasons.append("no evidence")
            evidence = []
        if len(evidence) > MAX_EVIDENCE:
            reasons.append(f"more than {MAX_EVIDENCE} quotes")
        for item in evidence:
            paragraph = by_id.get(item.get("paragraph_id"))
            quote = _norm(str(item.get("quote", "")))
            if not paragraph:
                reasons.append(f"unknown paragraph {item.get('paragraph_id')}")
            elif not quote:
                reasons.append(f"empty quote in {item['paragraph_id']}")
            elif quote not in _norm(paragraph["text"]) and quote not in _norm(paragraph["raw"]):
                reasons.append(f"quote not found in {item['paragraph_id']}")
        (dropped if reasons else kept).append({**theme, "problems": reasons} if reasons else theme)
        if reasons:
            problems.append(f"{label or '(no label)'}: " + "; ".join(reasons))
    if not themes and not str(result.get("none_reason", "")).strip():
        problems.append("no themes and no `none_reason`")
    return {
        "themes": kept,
        "dropped": dropped,
        "frames_not_themes": result.get("frames_not_themes") or [],
        "none_reason": result.get("none_reason"),
        "problems": problems,
    }


# --- Runners ---------------------------------------------------------------


class ThemeRunner:
    """Turns (system prompt, sermon input) into the model's raw text."""

    name = "base"
    model = None

    def run(self, system_prompt, input_text):
        raise NotImplementedError


class SubagentRunner(ThemeRunner):
    """Claude Code subagents. Started by hand, so `run` is not used. See `task_text`."""

    name = "subagent"
    model = "sonnet"

    def run(self, system_prompt, input_text):
        raise ThemeError("Subagent runs are started from Claude Code. Use `sermon themes prepare` to print the tasks.")

    @staticmethod
    def task_text(prompt_file, input_file, output_file):
        return (
            f"Read the instructions in {prompt_file} and the sermon in {input_file}. "
            f"Follow the instructions exactly. Write only the JSON object to {output_file}. "
            "Use no other source. Do not read other sermons or other files under output/themes."
        )


class ApiRunner(ThemeRunner):
    """The Anthropic API, through the official Python SDK. Untested: no API key has been used yet.

    Needs `pip install anthropic` and ANTHROPIC_API_KEY (or `ant auth login`).
    For all sermons use the Message Batches API (half price) instead of one call each.
    """

    name = "api"

    def __init__(self, model="claude-sonnet-5-5", max_tokens=16000):
        self.model = model
        self.max_tokens = max_tokens

    def run(self, system_prompt, input_text):
        import anthropic

        client = anthropic.Anthropic()
        response = client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": input_text}],
        )
        if response.stop_reason == "refusal":
            raise ThemeError(f"The model declined: {getattr(response, 'stop_details', None)}")
        if response.stop_reason == "max_tokens":
            raise ThemeError("The model ran out of tokens. Raise max_tokens.")
        return "".join(block.text for block in response.content if block.type == "text")


RUNNERS = {"subagent": SubagentRunner, "api": ApiRunner}


# --- Files -----------------------------------------------------------------


def sermon_dir(out_dir, sermon_id):
    return os.path.join(out_dir, sermon_id)


def write_json(path, data):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=1, ensure_ascii=False)


def prepare(archive_dir, out_dir, sermon_ids):
    """Writes input.md for each sermon. Returns the contexts."""
    contexts = []
    for sermon_id in sermon_ids:
        ctx = sermon_context(archive_dir, sermon_id)
        folder = sermon_dir(out_dir, sermon_id)
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, "input.md"), "w", encoding="utf-8") as handle:
            handle.write(build_input(ctx))
        contexts.append(ctx)
    return contexts


def run_with(runner, archive_dir, out_dir, sermon_ids, version=PROMPT_VERSION, print_fn=print):
    """Runs a runner that can call a model itself (the API). Writes raw.json and meta.json."""
    system_prompt = load_prompt(version)
    for ctx in prepare(archive_dir, out_dir, sermon_ids):
        folder = sermon_dir(out_dir, ctx["sermon_id"])
        print_fn(f"{ctx['date']} {ctx['title']}: running {runner.name}")
        raw = runner.run(system_prompt, build_input(ctx))
        with open(os.path.join(folder, "raw.json"), "w", encoding="utf-8") as handle:
            handle.write(raw)
        write_json(os.path.join(folder, "meta.json"), meta(runner, version))


def meta(runner, version=PROMPT_VERSION, model=None):
    return {
        "prompt_version": version,
        "runner": runner.name,
        "model": model or runner.model,
        "created": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
    }


def check_sermon(archive_dir, out_dir, sermon_id, runner_name="subagent", model=None, version=PROMPT_VERSION):
    """Reads raw.json, runs the quote check, writes checked.json. Returns the checked result."""
    ctx = sermon_context(archive_dir, sermon_id)
    folder = sermon_dir(out_dir, sermon_id)
    raw_path = os.path.join(folder, "raw.json")
    if not os.path.exists(raw_path):
        raise ThemeError(f"{sermon_id}: no raw.json yet")
    with open(raw_path, encoding="utf-8") as handle:
        checked = check_result(parse_output(handle.read()), ctx["paragraphs"])
    meta_path = os.path.join(folder, "meta.json")
    if not os.path.exists(meta_path):
        write_json(meta_path, {"prompt_version": version, "runner": runner_name, "model": model})
    checked.update(sermon_id=sermon_id, date=ctx["date"], title=ctx["title"], passage=ctx["passage"])
    write_json(os.path.join(folder, "checked.json"), checked)
    return checked


def timestamp(start_ms):
    seconds = int(start_ms) // 1000
    return f"{seconds // 3600}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}"


def report_markdown(archive_dir, out_dir, sermon_ids):
    """A review sheet: each suggested theme with its quotes, audio times and a blank verdict."""
    lines = ["# Theme Suggestions for Review", "",
             "Every theme is a suggestion. Mark each one: agrees, close, wrong or frame.", ""]
    for sermon_id in sermon_ids:
        ctx = sermon_context(archive_dir, sermon_id)
        checked_path = os.path.join(sermon_dir(out_dir, sermon_id), "checked.json")
        if not os.path.exists(checked_path):
            lines += [f"## {ctx['date']} {ctx['title']}", "", "No checked result yet.", ""]
            continue
        checked = _load(checked_path)
        starts = {p["id"]: p["start_ms"] for p in ctx["paragraphs"]}
        lines += [f"## {ctx['date']} {ctx['title']}", "",
                  f"{ctx['speaker']}. {ctx['passage']}. Series: {ctx['series']}.", ""]
        for number, theme in enumerate(checked["themes"], 1):
            lines += [f"### {number}. {theme['label']} ({theme['confidence']})", "", theme["why"], ""]
            for item in theme["evidence"]:
                lines.append(f"- {item['paragraph_id']} at {timestamp(starts[item['paragraph_id']])}: \"{item['quote']}\"")
            lines += ["", "Verdict: ____", ""]
        if not checked["themes"]:
            lines += [f"No themes. {checked.get('none_reason') or ''}", ""]
        if checked["frames_not_themes"]:
            lines.append("Frames the model set aside: " + ", ".join(
                f"{f.get('label')} ({f.get('reason')})" for f in checked["frames_not_themes"]))
            lines.append("")
        if checked["dropped"]:
            lines.append("Dropped by the quote check:")
            lines += [f"- {d.get('label')}: {'; '.join(d['problems'])}" for d in checked["dropped"]]
            lines.append("")
        lines += ["Themes Paul would add that are missing: ____", ""]
    return "\n".join(lines)
