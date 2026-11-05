import os
import shutil
import subprocess
import sys

import pytest

from app import cli

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture
def fake_root(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "ROOT", str(tmp_path))
    (tmp_path / "requirements-optional.txt").write_text("requests\n")
    return tmp_path


def _record_runs(monkeypatch):
    runs = []

    def fake_run(command, check=False, **kwargs):
        runs.append(command)
        if command[1:3] == ["-m", "venv"]:
            os.makedirs(command[3], exist_ok=True)

    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    return runs


def test_setup_creates_a_private_venv_and_installs_into_it(fake_root, monkeypatch):
    runs = _record_runs(monkeypatch)
    messages = []

    assert cli.run_setup(messages.append) == 0

    venv = str(fake_root / ".venv")
    assert runs[0] == [sys.executable, "-m", "venv", venv]
    assert runs[1][1:] == ["-m", "pip", "install", "-r", str(fake_root / "requirements-optional.txt")]
    assert runs[1][0].startswith(venv)  # installs with the venv's python, not the system one
    assert any("python3 sermon audio" in m for m in messages)


def test_setup_is_safe_to_run_again(fake_root, monkeypatch):
    (fake_root / ".venv").mkdir()
    runs = _record_runs(monkeypatch)

    assert cli.run_setup(lambda *_: None) == 0
    assert len(runs) == 1 and runs[0][2:4] == ["pip", "install"]  # no second venv creation


def test_setup_failure_is_explained_not_a_traceback(fake_root, monkeypatch):
    def boom(command, check=False, **kwargs):
        raise subprocess.CalledProcessError(1, command)

    monkeypatch.setattr(cli.subprocess, "run", boom)
    messages = []

    assert cli.run_setup(messages.append) == 1
    assert any("Setup failed" in m for m in messages)


def test_setup_does_not_need_ffmpeg(monkeypatch):
    monkeypatch.setattr(cli, "run_setup", lambda print_fn=print: 0)
    monkeypatch.setattr(cli, "ensure_ffmpeg", lambda: (_ for _ in ()).throw(RuntimeError("no ffmpeg")))
    assert cli.main(["setup"]) == 0


@pytest.mark.skipif(os.name == "nt", reason="uses a POSIX shell script as a fake python")
def test_launcher_switches_to_the_private_venv_when_it_exists(tmp_path):
    launcher = tmp_path / "sermon"
    shutil.copy(os.path.join(ROOT, "sermon"), launcher)
    fake_python = tmp_path / ".venv" / "bin" / "python"
    fake_python.parent.mkdir(parents=True)
    fake_python.write_text('#!/bin/sh\necho "VENV-PYTHON $@"\n')
    fake_python.chmod(0o755)

    result = subprocess.run(
        [sys.executable, str(launcher), "audio", "x.wav"], capture_output=True, text=True
    )

    assert result.stdout.startswith("VENV-PYTHON")
    assert result.stdout.strip().endswith("sermon audio x.wav")


@pytest.mark.skipif(os.name == "nt", reason="uses a POSIX shell script as a fake python")
def test_launcher_can_be_told_to_skip_the_venv(tmp_path):
    launcher = tmp_path / "sermon"
    shutil.copy(os.path.join(ROOT, "sermon"), launcher)
    fake_python = tmp_path / ".venv" / "bin" / "python"
    fake_python.parent.mkdir(parents=True)
    fake_python.write_text('#!/bin/sh\necho "VENV-PYTHON"\n')
    fake_python.chmod(0o755)

    result = subprocess.run(
        [sys.executable, str(launcher), "audio", "x.wav"],
        capture_output=True, text=True, env={**os.environ, "SERMON_NO_VENV": "1"},
    )

    assert "VENV-PYTHON" not in result.stdout
