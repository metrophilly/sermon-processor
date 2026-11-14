"""
Passage audit: does the audio say the same passage the sermon record does?

Compares the authored `passage` on each Sanity sermon with the passage the reader announces at
the start of its transcript. Reads local files only. Writes a report for a person to read and
nothing else. It never changes a record and never stores a spoken passage. A mismatch can mean a
wrong record, a wrong audio file, a different reading than the sermon text, or a speech to text
error, and only a person can tell which.
"""

import csv
import glob
import json
import os

from app.scripture import refs, spoken


def _load(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def _paragraphs(transcript_path):
    transcript = _load(transcript_path)
    edited_path = transcript_path.replace(".transcript.json", ".edited.json")
    edited = {p["id"]: p["text"] for p in _load(edited_path)["paragraphs"]} if os.path.exists(edited_path) else {}
    return transcript, [{"id": p["id"], "start_ms": p["start_ms"], "text": edited.get(p["id"], p["text"])}
                        for p in transcript["paragraphs"]]


def audit(archive_dir):
    """One row per transcript."""
    sermons = {r["_id"].replace("drafts.", "", 1): r for r in _load(os.path.join(archive_dir, "sanity_sermons.json"))}
    by_audio = {}
    for sermon in sermons.values():
        if sermon.get("s3"):
            by_audio.setdefault(sermon["s3"], []).append(sermon["_id"])
    rows = []
    for path in sorted(glob.glob(os.path.join(archive_dir, "transcripts", "*", "*.transcript.json"))):
        transcript, paragraphs = _paragraphs(path)
        sermon_id = transcript["sermon_id"]
        sermon = sermons.get(sermon_id)
        if not sermon:
            continue
        row = {"sermon_id": sermon_id, "date": transcript["date"], "title": sermon.get("title", ""),
               "authored": sermon["passage"], "shared_audio": len(by_audio.get(sermon.get("s3"), [])) > 1}
        try:
            authored = refs.parse_authored(sermon["passage"])
        except refs.RefError as error:
            row.update(result="authored passage unreadable", spoken="", first_spoken="", note=str(error), when="", excerpt="")
            rows.append(row)
            continue
        found = spoken.find_spoken(paragraphs)
        ranges = [f["range"] for f in found]
        first = found[0] if found else None
        row.update(
            result=spoken.classify(authored, found),
            spoken="; ".join(dict.fromkeys(refs.format_range(r) for r in ranges)),
            first_spoken=refs.format_range(first["range"]) if first else "",
            note="; ".join(sorted({f["kind"] for f in found})),
            when=f"{first['paragraph_id']} at {first['start_ms'] // 1000}s" if first else "",
            excerpt=first["excerpt"].replace("\n", " ") if first else paragraphs[0]["text"][:200].replace("\n", " "),
        )
        rows.append(row)
    return rows


def write_csv(rows, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fields = ["result", "date", "title", "authored", "spoken", "first_spoken", "shared_audio", "when", "note", "sermon_id", "excerpt"]
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(sorted(rows, key=lambda r: (spoken.CLASSES.index(r["result"]) if r["result"] in spoken.CLASSES else -1, r["date"])))


def report_markdown(rows):
    order = ["authored passage unreadable"] + spoken.CLASSES
    counts = {c: sum(1 for r in rows if r["result"] == c) for c in order}
    lines = ["# Passage Audit", "",
             "Compares the authored passage on each sermon with the passage announced at the start of its audio.",
             "A mismatch can mean a wrong record, a wrong audio file, a different reading than the sermon text, or a",
             "transcription error. This report changes nothing. A person decides.", "", "## Counts", ""]
    lines += [f"- {c}: {n}" for c, n in counts.items() if n]
    lines.append(f"- total: {len(rows)}")
    for cls in order:
        group = [r for r in rows if r["result"] == cls]
        if cls in ("exact", "partial", "chapter only", "start only") or not group:
            continue
        lines += ["", f"## {cls.capitalize()} ({len(group)})", ""]
        for r in sorted(group, key=lambda r: r["date"]):
            flag = " [audio file shared with another sermon]" if r["shared_audio"] else ""
            lines += [f"### {r['date']} {r['title']}{flag}", "",
                      f"- Record says: {r['authored']}", f"- Audio says: {r['spoken'] or 'nothing found'} ({r['when']})" if r["spoken"] else
                      f"- Audio says: nothing found in the opening",
                      f"- Opening: {r['excerpt'][:240]}", f"- Sermon: {r['sermon_id']}", ""]
    return "\n".join(lines)
