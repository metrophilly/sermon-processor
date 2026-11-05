"""
Small desktop conveniences: notifications, opening the result, previewing audio.

Everything here is best-effort. None of it may ever raise, since a missing
notification must not fail a render that already succeeded.
"""

import json
import os
import shutil
import subprocess
import sys


def in_container():
    return os.path.exists("/.dockerenv")


def _run(command, **kwargs):
    try:
        return subprocess.run(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            **kwargs,
        ).returncode == 0
    except Exception:
        return False


def notify(title, message):
    """Rings the terminal bell and shows a desktop notification where possible."""
    try:
        sys.stdout.write("\a")
        sys.stdout.flush()
    except Exception:
        pass
    if in_container():
        return
    if sys.platform == "darwin":
        script = f"display notification {json.dumps(message)} with title {json.dumps(title)}"
        _run(["osascript", "-e", script])
    elif sys.platform.startswith("linux") and shutil.which("notify-send"):
        _run(["notify-send", title, message])


def _audacity_windows():
    for var in ("ProgramFiles", "ProgramFiles(x86)"):
        base = os.environ.get(var)
        if base:
            exe = os.path.join(base, "Audacity", "audacity.exe")
            if os.path.exists(exe):
                return exe
    return None


def open_in_audacity(path):
    """Opens `path` in Audacity. Returns True if Audacity was launched."""
    if in_container():
        return False
    try:
        if sys.platform == "darwin":
            return _run(["open", "-a", "Audacity", path])
        if sys.platform == "win32":
            exe = _audacity_windows()
            if exe:
                subprocess.Popen([exe, path])
                return True
            return False
        exe = shutil.which("audacity")
        if exe:
            subprocess.Popen([exe, path])
            return True
    except Exception:
        pass
    return False


def reveal_in_file_manager(path):
    """Shows `path` in Finder / Explorer / the default file manager."""
    if in_container():
        return False
    try:
        if sys.platform == "darwin":
            return _run(["open", "-R", path])
        if sys.platform == "win32":
            return _run(["explorer", f"/select,{os.path.normpath(path)}"])
        opener = shutil.which("xdg-open")
        if opener:
            return _run([opener, os.path.dirname(path) or "."])
    except Exception:
        pass
    return False


def open_result(path):
    """Opens the finished file in Audacity, else reveals it. Returns what happened."""
    if open_in_audacity(path):
        return "Opened in Audacity"
    if reveal_in_file_manager(path):
        return "Revealed in file manager"
    return None


def play_audio(path):
    """Plays an audio file, blocking until it ends when the platform allows."""
    try:
        if sys.platform == "darwin" and shutil.which("afplay"):
            _run(["afplay", path])
        elif shutil.which("ffplay"):
            _run(["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", path])
        elif sys.platform == "win32":
            os.startfile(path)  # opens in the default player; does not block
        elif shutil.which("xdg-open"):
            _run(["xdg-open", path])
        else:
            print(f"(No audio player found. Open this file to listen: {path})")
    except Exception:
        print(f"(Could not play audio. Open this file to listen: {path})")
