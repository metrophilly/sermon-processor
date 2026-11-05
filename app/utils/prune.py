import os
import time

# Only these cache subfolders are ever cleaned. The intro/outro in cache/s3 and
# everything outside the cache are left alone.
PRUNABLE = ("audio", "video", "transcripts", "previews")


def prune_cache(cache_dir="cache", keep_days=28, now=None):
    """
    Deletes files in the cache older than `keep_days`. Returns the removed paths.
    A `keep_days` of 0 or less disables pruning.
    """
    if keep_days <= 0:
        return []
    cutoff = (now if now is not None else time.time()) - keep_days * 86400
    removed = []
    for name in PRUNABLE:
        folder = os.path.join(cache_dir, name)
        if not os.path.isdir(folder):
            continue
        for root, _, files in os.walk(folder):
            for filename in files:
                path = os.path.join(root, filename)
                try:
                    if not os.path.islink(path) and os.path.getmtime(path) < cutoff:
                        os.remove(path)
                        removed.append(path)
                except OSError:
                    continue
    return removed
