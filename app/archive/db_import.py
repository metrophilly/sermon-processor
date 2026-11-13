"""
`sermon db-import`: load sermons and transcripts into the Metro Postgres (DT-252).

Design: docs/sermon-database-design.md. Reads local files only (the Sanity export,
the manifest, the transcripts and their edited layers). It never calls Sanity.

- Every sermon in the Sanity export becomes a `sermon` row, keyed on its `_id`.
- Every transcript becomes a `sermon_transcript` keyed by its normalized S3 key,
  with one `sermon_paragraph` row per paragraph (raw text, edited text, edits).
- A transcript links to a sermon by S3 key. There is no foreign key.
- A rerun is safe: the same audio updates in place, a new audio hash makes a new version.

Talks to Postgres through the `psql` program, so it needs no extra Python package.
"""

import datetime
import json
import os
import subprocess
import urllib.parse
import uuid

SERMON_COLUMNS = [
    "id", "title", "slug", "spokenDate", "speakerName", "series", "passage",
    "s3AudioPath", "isPublished", "sanityUpdatedAt",
]
TRANSCRIPT_COLUMNS = [
    "id", "s3Key", "version", "isCurrent", "audioSha256", "durationSeconds",
    "model", "wordCount", "wordsPath", "fixesCommit", "generatedAt",
]
PARAGRAPH_COLUMNS = [
    "id", "transcriptId", "paragraphId", "position", "startMs", "endMs",
    "textRaw", "textEdited", "edits", "avgConfidence",
]


def normalize_key(path):
    """'/2012/2012-02/1-02%20Our%20True%20Joy.mp3' -> '2012/2012-02/1-02 Our True Joy.mp3'."""
    if not path:
        return None
    return urllib.parse.unquote(path).lstrip("/")


def _load(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def sermon_row(doc, updated_at):
    speaker = doc.get("speaker") or {}
    name = " ".join(x for x in (speaker.get("firstName"), speaker.get("lastName")) if x) or None
    slug = doc.get("slug")
    if isinstance(slug, dict):
        slug = slug.get("current")
    return {
        "id": doc["_id"].replace("drafts.", "", 1),
        "title": doc.get("title") or "",
        "slug": slug,
        "spokenDate": doc.get("spokenDate"),
        "speakerName": name,
        "series": doc.get("series"),
        "passage": doc.get("passage"),
        "s3AudioPath": normalize_key(doc.get("s3")),
        "isPublished": bool(doc.get("isPublished")),
        "sanityUpdatedAt": updated_at,
    }


def transcript_paragraphs(transcript, edited):
    """Paragraph rows for one transcript. `edited` is the edited layer or None."""
    edited_text = {p["id"]: p["text"] for p in (edited or {}).get("paragraphs", [])}
    word_to_paragraph = {w["id"]: p["id"] for p in transcript["paragraphs"] for w in p["words"]}
    edits_by_paragraph = {}
    for edit in (edited or {}).get("edits", []):
        edits_by_paragraph.setdefault(word_to_paragraph[edit["word_ids"][0]], []).append(edit)
    rows = []
    for p in transcript["paragraphs"]:
        rows.append(
            {
                "paragraphId": p["id"],
                "position": p["index"],
                "startMs": p["start_ms"],
                "endMs": p["end_ms"],
                "textRaw": p["text"],
                "textEdited": edited_text.get(p["id"], p["text"]),
                "edits": edits_by_paragraph.get(p["id"]),
                "avgConfidence": p["avg_confidence"],
            }
        )
    return rows


def build_plan(archive_dir, sanity_path, fixes_commit):
    """Everything to import plus a report. Reads files only."""
    sanity = _load(sanity_path)
    manifest = {r["sermon_id"]: r for r in _load(os.path.join(archive_dir, "manifest.json"))}
    updated_at = datetime.datetime.fromtimestamp(
        os.path.getmtime(sanity_path), datetime.timezone.utc
    ).isoformat(timespec="seconds")
    sermons = [sermon_row(doc, updated_at) for doc in sanity]

    transcripts, problems = [], []
    root = os.path.join(archive_dir, "transcripts")
    for folder in sorted(os.listdir(root)):
        if not os.path.isdir(os.path.join(root, folder)):
            continue
        for name in sorted(os.listdir(os.path.join(root, folder))):
            if not name.endswith(".transcript.json"):
                continue
            path = os.path.join(root, folder, name)
            transcript = _load(path)
            edited_path = path.replace(".transcript.json", ".edited.json")
            edited = _load(edited_path) if os.path.exists(edited_path) else None
            if edited is None:
                problems.append(f"{transcript['date']} {transcript['sermon_id']}: no edited layer, loading raw text only")
            row = manifest.get(transcript["sermon_id"])
            s3_key = normalize_key(row["s3_key"]) if row else None
            if not s3_key:
                problems.append(f"{transcript['date']} {transcript['sermon_id']}: not in the manifest, skipped")
                continue
            transcripts.append(
                {
                    "s3Key": s3_key,
                    "audioSha256": transcript["audio"]["sha256"],
                    "durationSeconds": transcript["audio"]["duration_seconds"],
                    "model": transcript["model"]["name"],
                    "wordCount": transcript["word_count"],
                    "fixesCommit": fixes_commit,
                    "generatedAt": transcript["generated_at"],
                    "date": transcript["date"],
                    "sermon_id": transcript["sermon_id"],
                    "paragraphs": transcript_paragraphs(transcript, edited),
                }
            )
    keys = {}
    for t in transcripts:
        keys.setdefault(t["s3Key"], []).append(t)
    for key, group in keys.items():
        if len(group) > 1:
            raise ValueError(f"{len(group)} transcripts share the S3 key {key}: " + ", ".join(t["sermon_id"] for t in group))

    by_key = {}
    for s in sermons:
        if s["s3AudioPath"]:
            by_key.setdefault(s["s3AudioPath"], []).append(s)
    report = {
        "sermons": len(sermons),
        "published": sum(s["isPublished"] for s in sermons),
        "transcripts": len(transcripts),
        "paragraphs": sum(len(t["paragraphs"]) for t in transcripts),
        "edited_paragraphs": sum(1 for t in transcripts for p in t["paragraphs"] if p["textEdited"] != p["textRaw"]),
        "no_sermon": [t for t in transcripts if t["s3Key"] not in by_key],
        "shared": [(t, by_key[t["s3Key"]]) for t in transcripts if len(by_key.get(t["s3Key"], [])) > 1],
        "date_mismatch": [],
        "without_transcript": [s for s in sermons if not s["s3AudioPath"] or s["s3AudioPath"] not in keys],
        "problems": problems,
    }
    for t in transcripts:
        for s in by_key.get(t["s3Key"], []):
            if s["spokenDate"] and abs(
                (datetime.date.fromisoformat(s["spokenDate"][:10]) - datetime.date.fromisoformat(t["date"])).days
            ) > 1:
                report["date_mismatch"].append((t, s))
    return {"sermons": sermons, "transcripts": transcripts, "report": report}


def report_lines(plan):
    r = plan["report"]
    lines = [
        f"Sermons from Sanity: {r['sermons']} ({r['published']} published)",
        f"Transcripts: {r['transcripts']}, {r['paragraphs']} paragraphs ({r['edited_paragraphs']} with edits)",
        f"Sermons with no transcript: {len(r['without_transcript'])}",
        f"Transcripts with no sermon: {len(r['no_sermon'])}",
        f"Transcripts matching more than one sermon: {len(r['shared'])}",
        f"Date mismatches (more than 1 day): {len(r['date_mismatch'])}",
    ]
    for t in r["no_sermon"]:
        lines.append(f"  no sermon: {t['date']} {t['sermon_id']} ({t['s3Key']})")
    for t, group in r["shared"]:
        lines.append(f"  shared file {t['s3Key']}: " + ", ".join(f"{s['id']} ({s['spokenDate'][:10]})" for s in group))
    for t, s in r["date_mismatch"]:
        lines.append(f"  date: transcript {t['date']} vs sermon {s['spokenDate'][:10]} ({s['id']})")
    lines += [f"  {p}" for p in r["problems"]]
    return lines


# --- Writing to Postgres ---------------------------------------------------


def _cell(value):
    """One value in COPY text format."""
    if value is None:
        return "\\N"
    if isinstance(value, bool):
        return "t" if value else "f"
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False)
    text = str(value)
    return text.replace("\\", "\\\\").replace("\t", "\\t").replace("\n", "\\n").replace("\r", "\\r")


def _copy(table, columns, rows):
    cols = ", ".join(f'"{c}"' for c in columns)
    body = "".join("\t".join(_cell(r[c]) for c in columns) + "\n" for r in rows)
    return f"COPY {table} ({cols}) FROM STDIN;\n{body}\\.\n"


def build_sql(plan, existing):
    """SQL script for the whole import. `existing` maps s3Key -> (id, version, sha) of current transcripts."""
    sermons = []
    for s in plan["sermons"]:
        sermons.append(s)
    out = ["BEGIN;"]
    out.append('CREATE TEMP TABLE stg_sermon (LIKE sermon INCLUDING DEFAULTS) ON COMMIT DROP;')
    out.append(_copy("stg_sermon", SERMON_COLUMNS, sermons))
    sets = ", ".join(f'"{c}" = EXCLUDED."{c}"' for c in SERMON_COLUMNS if c != "id")
    cols = ", ".join(f'"{c}"' for c in SERMON_COLUMNS)
    out.append(
        f'INSERT INTO sermon ({cols}) SELECT {cols} FROM stg_sermon '
        f'ON CONFLICT ("id") DO UPDATE SET {sets}, "deletedAt" = NULL, "syncedAt" = now();'
    )

    new_transcripts, paragraphs, retire, update = [], [], [], []
    for t in plan["transcripts"]:
        current = existing.get(t["s3Key"])
        if current and current[2] == t["audioSha256"]:
            transcript_id = current[0]
            update.append((transcript_id, t["fixesCommit"]))
        else:
            transcript_id = uuid.uuid4().hex
            version = 1
            if current:
                retire.append(current[0])
                version = current[1] + 1
            new_transcripts.append({**t, "id": transcript_id, "version": version, "isCurrent": True, "wordsPath": None})
        for p in t["paragraphs"]:
            paragraphs.append({**p, "id": uuid.uuid4().hex, "transcriptId": transcript_id})
    for transcript_id in retire:
        out.append(f"UPDATE sermon_transcript SET \"isCurrent\" = false WHERE id = '{transcript_id}';")
    if new_transcripts:
        out.append(_copy("sermon_transcript", TRANSCRIPT_COLUMNS, new_transcripts))
    for transcript_id, commit in update:
        out.append(
            "UPDATE sermon_transcript SET \"fixesCommit\" = "
            + ("NULL" if commit is None else "'" + commit.replace("'", "''") + "'")
            + f" WHERE id = '{transcript_id}';"
        )
    out.append("CREATE TEMP TABLE stg_paragraph (LIKE sermon_paragraph) ON COMMIT DROP;")
    out.append(_copy("stg_paragraph", PARAGRAPH_COLUMNS, paragraphs))
    pcols = ", ".join(f'"{c}"' for c in PARAGRAPH_COLUMNS)
    psets = ", ".join(
        f'"{c}" = EXCLUDED."{c}"'
        for c in ("position", "startMs", "endMs", "textRaw", "textEdited", "edits", "avgConfidence")
    )
    out.append(
        f'INSERT INTO sermon_paragraph ({pcols}) SELECT {pcols} FROM stg_paragraph '
        f'ON CONFLICT ("transcriptId", "paragraphId") DO UPDATE SET {psets};'
    )
    out.append("COMMIT;")
    return "\n".join(out) + "\n", {
        "new": len(new_transcripts), "updated": len(update), "retired": len(retire), "paragraphs": len(paragraphs)
    }


def _psql(url, args=(), sql=None):
    return subprocess.run(
        ["psql", url, "-X", "-v", "ON_ERROR_STOP=1", *args],
        input=sql, capture_output=True, text=True,
    )


def current_transcripts(url):
    result = _psql(url, ["-At", "-F", "\t", "-c",
                         'SELECT "s3Key", id, version, "audioSha256" FROM sermon_transcript WHERE "isCurrent"'])
    if result.returncode:
        raise RuntimeError("Could not read existing transcripts: " + result.stderr.strip()[-300:])
    out = {}
    for line in result.stdout.splitlines():
        key, tid, version, sha = line.split("\t")
        out[key] = (tid, int(version), sha)
    return out


def run_import(plan, url, print_fn=print):
    existing = current_transcripts(url)
    sql, counts = build_sql(plan, existing)
    result = _psql(url, sql=sql)
    if result.returncode:
        raise RuntimeError("Import failed and was rolled back: " + result.stderr.strip()[-500:])
    print_fn(
        f"Imported {len(plan['sermons'])} sermons; {counts['new']} new transcripts, "
        f"{counts['updated']} updated in place, {counts['retired']} retired; {counts['paragraphs']} paragraphs."
    )
    return counts
