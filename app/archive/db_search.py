"""
`sermon search`: ranked full-text search over the sermon transcripts in Postgres.

Searches the edited text of current transcripts. Design: docs/sermon-database-design.md.
Uses the `psql` program, like `sermon db-import`, so it needs no extra Python package.

The query must use the same expression as the index, or Postgres ignores the index:
    to_tsvector('english', "textEdited")
"""

import subprocess

# psql substitutes :'q' (quoted text), :phrase, :per and :lim, so the search text is
# never pasted into the SQL. {published} is one of two fixed strings below.
SEARCH_SQL = """
WITH q AS (
  SELECT CASE WHEN :phrase THEN phraseto_tsquery('english', :'q')
              ELSE websearch_to_tsquery('english', :'q') END AS tsq
),
hits AS (
  SELECT s.id AS sid, s.title, s."spokenDate", s."speakerName", p."paragraphId", p."startMs",
         p."textEdited" AS text,
         ts_rank_cd(to_tsvector('english', p."textEdited"), q.tsq, 32) AS rank
  FROM q, sermon_paragraph p
  JOIN sermon_transcript t ON t.id = p."transcriptId" AND t."isCurrent"
  JOIN sermon s ON s."s3AudioPath" = t."s3Key" AND s."deletedAt" IS NULL{published}
  WHERE to_tsvector('english', p."textEdited") @@ q.tsq
),
ranked AS (
  SELECT *, row_number() OVER (PARTITION BY sid ORDER BY rank DESC, "startMs") AS rn FROM hits
)
SELECT round(rank::numeric, 3), "spokenDate"::date, title, coalesce("speakerName", ''), sid, "paragraphId",
       "startMs", (SELECT count(*) FROM hits),
       replace(ts_headline('english', text, q.tsq,
         'StartSel=[[, StopSel=]], MaxWords=45, MinWords=20, MaxFragments=1'), E'\\n', ' ')
FROM ranked, q
WHERE rn <= :per
ORDER BY rank DESC, "spokenDate" DESC
LIMIT :lim;
"""

PUBLISHED = ' AND s."isPublished"'


def search_sql(published_only):
    return SEARCH_SQL.format(published=PUBLISHED if published_only else "")


def timestamp(start_ms):
    seconds = int(start_ms) // 1000
    return f"{seconds // 3600}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}"


def parse_rows(output):
    """psql -At -F tab output -> list of result dicts."""
    rows = []
    for line in output.splitlines():
        parts = line.split("\t")
        if len(parts) != 9:
            continue
        rank, date, title, speaker, sid, paragraph, start_ms, total, snippet = parts
        rows.append(
            {"rank": float(rank), "date": date, "title": title, "speaker": speaker, "sermon_id": sid,
             "paragraph": paragraph, "start_ms": int(start_ms), "total": int(total), "snippet": snippet}
        )
    return rows


def search(url, text, limit=15, per_sermon=2, phrase=False, published_only=False):
    result = subprocess.run(
        ["psql", url, "-X", "-At", "-F", "\t", "-v", "ON_ERROR_STOP=1",
         "-v", f"q={text}", "-v", f"phrase={'true' if phrase else 'false'}",
         "-v", f"per={int(per_sermon)}", "-v", f"lim={int(limit)}"],
        input=search_sql(published_only), capture_output=True, text=True,
    )
    if result.returncode:
        raise RuntimeError("Search failed: " + result.stderr.strip()[-300:])
    return parse_rows(result.stdout)


def format_rows(rows):
    if not rows:
        return ["No matches."]
    lines = [f"{rows[0]['total']} matching paragraphs. Showing {len(rows)}, best first. Matches are in [[brackets]].", ""]
    for r in rows:
        who = f" ({r['speaker']})" if r["speaker"] else ""
        lines.append(f"{r['date']}  {r['title']}{who}  [{r['rank']}]")
        lines.append(f"  {r['sermon_id']} {r['paragraph']} at {timestamp(r['start_ms'])}")
        lines.append(f"  {r['snippet']}")
        lines.append("")
    return lines
