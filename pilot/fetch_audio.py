"""Download the pilot audio from the public sermon bucket (no AWS login needed).

Usage:
  python3 pilot/fetch_audio.py            # download any missing file
  python3 pilot/fetch_audio.py --check    # only test that each URL answers 200

Reads pilot/manifest.json. Falls back to /YEAR/DATE.mp3 when the path stored in
Sanity does not exist (all 2020 sermons had a wrong folder path; see the 12 Nov
handoff). Files are saved as pilot/audio/DATE.mp3.
"""
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

BASE = "https://metrophilly-sermons.s3.us-east-2.amazonaws.com"
HERE = Path(__file__).parent


def exists(url):
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status == 200
    except urllib.error.HTTPError:
        return False


def main():
    check = "--check" in sys.argv
    (HERE / "audio").mkdir(exist_ok=True)
    manifest = json.loads((HERE / "manifest.json").read_text())
    bad = 0
    for x in sorted(manifest, key=lambda y: y["spokenDate"]):
        d = x["spokenDate"][:10]
        dest = HERE / "audio" / f"{d}.mp3"
        # s3 path from Sanity is already percent-encoded
        urls = [BASE + x["s3"], f"{BASE}/{d[:4]}/{d}.mp3"]
        url = next((u for u in urls if exists(u)), None)
        if not url:
            print(f"{d} MISSING (tried {len(urls)} URLs)")
            bad += 1
            continue
        if check:
            print(f"{d} ok  {url}")
        elif dest.exists() and dest.stat().st_size > 1_000_000:
            print(f"{d} already downloaded")
        else:
            tmp = dest.with_suffix(".part")
            urllib.request.urlretrieve(url, tmp)
            tmp.rename(dest)
            print(f"{d} downloaded {dest.stat().st_size/1e6:.0f} MB")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
