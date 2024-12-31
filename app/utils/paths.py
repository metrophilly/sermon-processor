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
