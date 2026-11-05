import shutil

INSTALL_HELP = """\
ffmpeg and ffprobe were not found.

Install one of:
  macOS:    brew install ffmpeg
  Windows:  winget install ffmpeg
  Any OS:   pip install static-ffmpeg   (downloads a private copy on first run)
"""


def _have_both():
    return bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


def ensure_ffmpeg():
    """
    Makes sure ffmpeg and ffprobe can be run. Uses the system copies when
    present, otherwise falls back to the optional `static-ffmpeg` package, which
    downloads a private copy once and puts it on PATH for this process.
    """
    if _have_both():
        return
    try:
        import static_ffmpeg

        static_ffmpeg.add_paths()
    except ImportError:
        pass
    if not _have_both():
        raise RuntimeError(INSTALL_HELP)
