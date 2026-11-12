"""
`sermon manifest`: list every sermon that should be transcribed (DT-245).

One Sanity query (published sermons only) plus one HEAD request per audio file
in the public sermon bucket. Writes `output/archive/manifest.json` (one row per
sermon, keyed on the published Sanity _id) and `output/archive/report.txt`.

The path stored in Sanity is checked exactly as stored. If only the flat
`/YEAR/DATE.mp3` exists it is reported as a proposed fix, never used silently,
because a transcript must match the file at `s3AudioPath`.
"""

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor

S3_BASE = "https://metrophilly-sermons.s3.us-east-2.amazonaws.com"
SANITY_PROJECT = "w04thztq"
SANITY_DATASET = "production"
API_VERSION = "v2025-01-01"

# Do not stop transcription, but need a human look. Shared files must be de-duplicated
# by `s3_key` before a batch run.
WARNINGS = {"date_mismatch", "same_date_as_other_sermon", "shared_audio_file"}

QUERY = (
    '*[_type=="sermon"]{_id, title, "slug": slug.current, isPublished, spokenDate, passage,'
    ' "speaker": speaker->{firstName, lastName, isMetroLeadership},'
    ' "series": series->title, "s3": mediaPaths.s3AudioPath, "yt": mediaPaths.youtubeVideoID}'
)


def load_env_file(path):
    """Reads KEY=VALUE lines. Returns a dict; never prints values."""
    values = {}
    with open(path) as handle:
        for line in handle:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                values[key.strip()] = value.strip().strip("\"'")
    return values


def fetch_sermons(token, project=SANITY_PROJECT, dataset=SANITY_DATASET):
    """One published-perspective query. Returns the list of sermon documents."""
    url = (
        f"https://{project}.apicdn.sanity.io/{API_VERSION}/data/query/{dataset}?"
        + urllib.parse.urlencode({"query": QUERY, "perspective": "published"})
    )
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)["result"]


def s3_key(path):
    """Percent-decoded key without the leading slash (the identity of a file)."""
    return urllib.parse.unquote(path or "").lstrip("/")


def s3_url(key):
    return f"{S3_BASE}/{urllib.parse.quote(key, safe='/')}"


def head_exists(key, retries=3):
    """True or False for 200 vs 404/403; None if the check itself failed."""
    for _ in range(retries):
        try:
            request = urllib.request.Request(s3_url(key), method="HEAD")
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.status == 200
        except urllib.error.HTTPError as error:
            if error.code in (403, 404):
                return False
        except (urllib.error.URLError, TimeoutError):
            pass
    return None


def check_keys(keys, workers=16):
    keys = sorted(set(keys))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return dict(zip(keys, pool.map(head_exists, keys)))


def _date(value):
    match = re.match(r"^(\d{4}-\d{2}-\d{2})", value or "")
    return match.group(1) if match else None


def _name(speaker):
    return " ".join(p for p in (speaker.get("firstName"), speaker.get("lastName")) if p)


def classify(docs, exists):
    """
    Pure function. `exists(key)` returns True, False or None.
    Returns (rows, excluded_counts). One row per eligible sermon, with a list
    of problems; status is "ready" when the stored path exists and no blocking problem is found; `warnings` hold the rest.
    """
    rows, excluded = [], Counter()
    for doc in docs:
        sermon_id = doc["_id"].removeprefix("drafts.")
        if doc["_id"].startswith("drafts."):
            excluded["draft_document"] += 1
            continue
        if not doc.get("isPublished"):
            excluded["unpublished"] += 1
            continue
        speaker = doc.get("speaker")
        if speaker and not speaker.get("isMetroLeadership"):
            excluded["guest_speaker"] += 1
            continue

        problems, date = [], _date(doc.get("spokenDate"))
        if not speaker:
            problems.append("no_speaker")
        if not doc.get("spokenDate"):
            problems.append("missing_date")
        elif not date:
            problems.append("bad_date")

        path, key, proposed = doc.get("s3"), s3_key(doc.get("s3")), None
        found = None
        if not key:
            problems.append("missing_audio_path")
        else:
            found = exists(key)
            if found is None:
                problems.append("s3_check_failed")
            elif not found:
                flat = f"{date[:4]}/{date}.mp3" if date else None
                if flat and exists(flat):
                    problems.append("path_not_found_fixable")
                    proposed = "/" + flat
                else:
                    problems.append("file_not_found")
            path_date = re.search(r"(\d{4}-\d{2}-\d{2})", key)
            if found and date and path_date and path_date.group(1) != date:
                problems.append("date_mismatch")

        rows.append(
            {
                "sermon_id": sermon_id,
                "slug": doc.get("slug"),
                "title": doc.get("title"),
                "date": date,
                "speaker": _name(speaker) if speaker else None,
                "passage": doc.get("passage"),
                "series": doc.get("series"),
                "s3_path": path,
                "s3_key": key or None,
                "audio_exists": found,
                "proposed_path": proposed,
                "youtube_id": doc.get("yt"),
                "problems": problems,
            }
        )

    by_key, by_date = defaultdict(list), defaultdict(list)
    for row in rows:
        if row["s3_key"] and row["audio_exists"]:
            by_key[row["s3_key"]].append(row)
        if row["date"]:
            by_date[row["date"]].append(row)
    for group in by_key.values():
        if len(group) > 1:
            for row in group:
                row["problems"].append("shared_audio_file")
    for group in by_date.values():
        if len(group) > 1:
            for row in group:
                row["problems"].append("same_date_as_other_sermon")
    for row in rows:
        row["warnings"] = [p for p in row["problems"] if p in WARNINGS]
        row["problems"] = [p for p in row["problems"] if p not in WARNINGS]
        row["status"] = "ready" if not row["problems"] else "problem"
    rows.sort(key=lambda r: (r["date"] or "", r["sermon_id"]))
    return rows, excluded


def report(rows, excluded):
    lines = [f"Eligible sermons (published, leadership speaker): {len(rows)}"]
    lines.append("Excluded: " + (", ".join(f"{k} {v}" for k, v in sorted(excluded.items())) or "none"))
    ready = sum(1 for r in rows if r["status"] == "ready")
    lines.append(f"Ready to transcribe (file found at the stored path, no blocking problem): {ready}")
    lines.append("\nBy year (eligible / ready):")
    years = defaultdict(lambda: [0, 0])
    for r in rows:
        year = (r["date"] or "no date")[:4]
        years[year][0] += 1
        years[year][1] += r["status"] == "ready"
    for year in sorted(years):
        lines.append(f"  {year}: {years[year][0]} / {years[year][1]}")
    counts = Counter(p for r in rows for p in r["problems"] + r["warnings"])
    lines.append("\nProblems (block transcription) and warnings (need a look), by type:")
    lines += [f"  {kind}{' (warning)' if kind in WARNINGS else ''}: {n}" for kind, n in counts.most_common()] or ["  none"]
    for kind in counts:
        lines.append(f"\n{kind}:")
        for r in rows:
            if kind in r["problems"] + r["warnings"]:
                extra = f" -> {r['proposed_path']}" if r["proposed_path"] else ""
                lines.append(f"  {r['date'] or '?'}  {r['sermon_id']}  {r['s3_path'] or '(none)'}{extra}")
    return "\n".join(lines)


def build_manifest(docs, check=check_keys):
    """Classify docs with real S3 checks. Returns (rows, excluded)."""
    probe = {}

    def lookup(key):
        if key not in probe:
            probe[key] = check([key])[key]
        return probe[key]

    # Warm every stored key in parallel first, then classify (flat fallbacks check on demand).
    stored = [s3_key(d.get("s3")) for d in docs if d.get("isPublished") and d.get("s3")]
    probe.update(check([k for k in stored if k]))
    return classify(docs, lookup)
