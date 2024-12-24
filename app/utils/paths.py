import os


def relative_path(path):
    """
    Convert an absolute path to a relative path based on the current working directory.
    """
    return os.path.relpath(path, start=os.getcwd())


def absolute_path(path):
    """
    Convert a relative path to an absolute path based on the current working directory.
    """
    return os.path.abspath(path)


def ensure_dir_exists(path):
    """
    Ensure a directory exists. If it doesn't, create it.
    """
    os.makedirs(path, exist_ok=True)
    return path
