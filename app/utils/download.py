import os
import shutil
import urllib.request


def download_file(url, destination):
    """
    Downloads `url` to `destination` using only the standard library, and reuses
    an existing non-empty file.

    The download goes to a temporary name first and is renamed only when it is
    complete, so an interrupted download can never be mistaken for a finished
    cached file next time.
    """
    if os.path.exists(destination) and os.path.getsize(destination) > 0:
        return destination

    os.makedirs(os.path.dirname(os.path.abspath(destination)), exist_ok=True)
    partial = f"{destination}.part"
    print(f"Downloading {url} ...")
    try:
        with urllib.request.urlopen(url, timeout=60) as response, open(partial, "wb") as out:
            shutil.copyfileobj(response, out)
        os.replace(partial, destination)
    finally:
        if os.path.exists(partial):
            os.remove(partial)
    return destination
