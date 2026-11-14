"""
`sermon scripture find`: sermons preached on a passage, exact matches first.

Reads the authored passage ranges in Postgres (sermon_passage). Nothing here comes from a
transcript. Ranking: 0 the sermon's range is exactly the query, 1 the sermon's range contains
the query, 2 the sermon's range lies inside the query, 3 the ranges only overlap.
"""

import subprocess

from app.scripture import refs

FIND_SQL = """
SELECT min(CASE
         WHEN p."startRef" = :qs AND p."endRef" = :qe THEN 0
         WHEN p."startRef" <= :qs AND p."endRef" >= :qe THEN 1
         WHEN p."startRef" >= :qs AND p."endRef" <= :qe THEN 2
         ELSE 3 END) AS rank,
       s."spokenDate"::date, s.title, coalesce(s."speakerName", ''), s.passage, s.id,
       EXISTS (SELECT 1 FROM sermon_transcript t WHERE t."s3Key" = s."s3AudioPath" AND t."isCurrent"),
       string_agg(DISTINCT p.label || CASE WHEN p.role <> 'EXPOSITED' THEN ' (' || lower(p.role::text) || ')' ELSE '' END, '; ')
FROM sermon_passage p
JOIN sermon s ON s.id = p."sermonId" AND s."deletedAt" IS NULL
WHERE p."startRef" <= :qe AND p."endRef" >= :qs AND (p.role = 'EXPOSITED' OR :supporting)
GROUP BY s.id
ORDER BY 1, s."spokenDate" DESC
LIMIT :lim;
"""

RANK_NAMES = {0: "exact match", 1: "preached on a longer passage that includes it", 2: "preached on part of it", 3: "overlaps it"}


def query_range(text):
    """The range to look up. A list such as 'John 6:1-15, 25-35' uses its first range."""
    return refs.parse_authored(text)[0]


def find(url, text, limit=30, supporting=False):
    r = query_range(text)
    result = subprocess.run(
        ["psql", url, "-X", "-At", "-F", "\t", "-v", "ON_ERROR_STOP=1", "-v", f"qs={r.start}", "-v", f"qe={r.end}",
         "-v", f"lim={int(limit)}", "-v", f"supporting={'true' if supporting else 'false'}"],
        input=FIND_SQL, capture_output=True, text=True,
    )
    if result.returncode:
        raise RuntimeError("Passage search failed: " + result.stderr.strip()[-300:])
    rows = []
    for line in result.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) == 8:
            rank, date, title, speaker, passage, sermon_id, transcript, ranges = parts
            rows.append({"rank": int(rank), "date": date, "title": title, "speaker": speaker, "passage": passage,
                         "sermon_id": sermon_id, "transcript": transcript == "t", "ranges": ranges})
    return r, rows


def format_rows(query, rows):
    if not rows:
        return [f"No sermons on {refs.format_range(query)}."]
    lines = [f"{len(rows)} sermons on {refs.format_range(query)}, best match first.", ""]
    last = None
    for row in rows:
        if row["rank"] != last:
            lines += [f"-- {RANK_NAMES[row['rank']]}", ""]
            last = row["rank"]
        who = f" ({row['speaker']})" if row["speaker"] else ""
        lines.append(f"{row['date']}  {row['title']}{who}")
        lines.append(f"  {row['passage']}  [{'transcript' if row['transcript'] else 'no transcript'}]  {row['sermon_id']}")
    return lines
