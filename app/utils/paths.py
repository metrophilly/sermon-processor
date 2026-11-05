import os


def file_ext(path):
    """
    Returns the file extension for the given path.

    Args:
        path (str): The file path.

    Returns:
        str: The file extension, including the leading dot (e.g., ".mp3").

    Raises:
        ValueError: If the path is None or empty.
        FileNotFoundError: If the path does not point to an existing file.
    """
    if not path:
        raise ValueError("Path cannot be None or empty.")
    if not os.path.exists(path):
        raise FileNotFoundError(f"The file does not exist: {path}")

    ext = os.path.splitext(path)[1].lower()
    if not ext:
        raise ValueError(f"No extension found for file: {path}")

    return ext


def tagged_path(path, tag):
    """
    Returns `path` with `tag` inserted before the extension, e.g.
    ("a/b/Sermon.WAV", "_trimmed") -> "a/b/Sermon_trimmed.WAV".

    Unlike `path.replace(ext, ...)`, this only touches the real extension, so it
    works for any casing and can never return the input path unchanged.
    """
    base, ext = os.path.splitext(path)
    return f"{base}{tag}{ext}"


# Audio codec that is valid inside each container. Writing the wrong codec into
# a container (e.g. AAC into .wav) produces files ffmpeg cannot read back.
_AUDIO_CODECS = {
    ".wav": ("pcm_s16le", None),
    ".mp3": ("libmp3lame", "192k"),
    ".flac": ("flac", None),
}


def audio_codec_for(ext):
    """
    Returns (codec, bitrate) appropriate for an output file with extension `ext`.
    bitrate is None for lossless codecs. Defaults to AAC (m4a, mp4, etc.).
    """
    return _AUDIO_CODECS.get(ext.lower(), ("aac", "192k"))
