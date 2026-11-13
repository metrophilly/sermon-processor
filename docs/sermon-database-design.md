# Sermon Database Design

Draft for review. Nothing here has been applied. The tables go in the existing Supabase Postgres that the Metro site already uses through Prisma (`metrophilly/frontend/prisma/schema.prisma`). Covers DT-243, DT-244, DT-252 and DT-253.

## Goal and Order

The goal is to search and analyze about 700 sermon transcripts: themes, fallen condition focus, gospel threads. Users arrive in this order, and each phase must work before the next starts:

1. **Scripts (Paul).** Import and search from the command line. Needs the tables and the import only.
2. **Staff in Center City.** Search page for signed-in staff. Needs titles and slugs for display and links, and the webhook so they stay current.
3. **Public site (possible later).** Needs an access rule for the full text before any page exposes it.

A search hit shows the paragraph and links to the sermon, and it can also play the audio from the matched words (see Hit Behavior).

## Checked Facts (13 Nov 2026)

- Postgres 17.6. `vector` 0.8.0, `pg_trgm` 1.6 and `unaccent` 1.1 are available and not installed. Each needs one `CREATE EXTENSION`.
- The database is 14 MB today. The connection limit is 60.
- The Sanity export (`output/archive/sanity_sermons.json`) has 760 sermons: 738 published, 22 unpublished. No duplicate slugs, no drafts, no repeated `_id`. 759 have an `s3` path.
- The manifest has 702 sermons: published, leadership speaker, audio present. Its `sermon_id` is the Sanity `_id` for all 702. 692 have a transcript. 10 do not (9 blocked, 1 shares a file with another sermon).
- The other 58 Sanity sermons are 36 published guest-speaker sermons and 22 unpublished ones. The manifest left them out of transcription, so none has a transcript today.
- `audio.file` in a transcript is named after the sermon ID (`sermon-import-00001.mp3`), not the S3 file. It matches the S3 key in none of the 692. It cannot be used to link a transcript to a sermon.
- Two sermons (2012-08-26 and 2012-09-02) share one S3 file. No two transcripts share an audio hash.
- Raw transcripts are about 700 MB because of per-word timing. That does not go in Postgres.
- Joined by normalized S3 key, 691 of the 692 transcripts match exactly one Sanity sermon. One matches two (the shared file). None match zero.
- The `.env.local` database is the development database, confirmed by Paul. Its 847 users and PCO data come from the PCO webhook, which still runs against it.

## Rules

1. Sanity stays the editor. Postgres holds a small read-only copy. The key is the published Sanity `_id` with any `drafts.` prefix removed. Sanity always wins.
2. A transcript belongs to an audio file, not to a sermon document. The link is the S3 key: `sermon.s3AudioPath` equals `sermon_transcript.s3Key`. Deleting and recreating a sermon in Sanity gives a new `_id` and the same S3 path, so the link survives.
3. The raw layer is never edited. Edited text lives next to it in its own column.
4. Word-level timing stays in files (S3 or the output folder). The database holds a pointer.
5. No scheduled job calls Sanity. Sync is webhook only, plus a manual reconcile (see Sync). Showing a hit must not need a Sanity call either, which is why title and slug are stored.
6. Every analysis finding quotes the transcript and names the transcript version (DT-273, later).

## Tables

Names follow the existing schema: camelCase columns, snake_case table names through `@@map`.

### `sermon` (small copy of Sanity)

Fields that queries filter or sort on, plus the two strings a result needs to display and link. Everything else is fetched from Sanity by the page, as today.

| Column | Type | Note |
| --- | --- | --- |
| `id` | text, primary key | Published Sanity `_id` |
| `title` | text | Shown on a hit |
| `slug` | text, nullable | Links the hit. Not unique, because a recreated sermon can reuse it |
| `spokenDate` | timestamptz | |
| `speakerName` | text, nullable | First and last name joined |
| `series` | text, nullable | |
| `passage` | text, nullable | |
| `s3AudioPath` | text, nullable | Normalized (decoded, no leading slash). The join key to transcripts |
| `isPublished` | boolean | A field on the Sanity document |
| `deletedAt` | timestamptz, nullable | Set when Sanity reports a delete. Cleared if the same `_id` comes back |
| `sanityUpdatedAt` | timestamptz | Sanity `_updatedAt` at the last write. Kept for the reconcile, not used for ordering |
| `syncedAt` | timestamptz | When Postgres last wrote the row |

Not unique on `s3AudioPath`, because two sermons can share one file. Not unique on `slug`.

### `sermon_transcript`

| Column | Type | Note |
| --- | --- | --- |
| `id` | text, cuid | |
| `s3Key` | text | Normalized S3 key from the manifest. Joins to `sermon.s3AudioPath` |
| `version` | int | 1, 2, 3 per `s3Key`. A new version only for a new audio file or a new model |
| `isCurrent` | boolean | One current row per `s3Key` |
| `audioSha256` | text | Matches `audio.sha256` in the JSON |
| `durationSeconds` | float | |
| `model` | text | For example `large-v3-turbo` |
| `wordCount` | int | |
| `wordsPath` | text, nullable | Where the word-level JSON lives (see Hit Behavior) |
| `fixesCommit` | text, nullable | Git commit of the fix list last applied. Updated in place |
| `generatedAt` | timestamptz | |

Unique on (`s3Key`, `version`). A partial unique index on (`s3Key`) where `isCurrent` keeps one current transcript per file. There is no foreign key to `sermon`, so deleting a sermon never touches a transcript. A transcript whose `s3Key` matches no live sermon is an orphan, and the reconcile report lists it.

A sermon with no transcript is simply a sermon whose `s3AudioPath` matches no current transcript. No flag is stored.

### `sermon_paragraph`

| Column | Type | Note |
| --- | --- | --- |
| `id` | text, cuid | |
| `transcriptId` | text, foreign key | Cascades with its transcript only |
| `paragraphId` | text | `p001` and so on |
| `position` | int | Order in the sermon |
| `startMs`, `endMs` | int | From the raw layer, never edited |
| `textRaw` | text | Exactly as transcribed |
| `textEdited` | text | After the fix list. Equals `textRaw` when there are no edits |
| `edits` | jsonb, nullable | The edit list: rule, word IDs, old, new |
| `avgConfidence` | float | |

A fix-list change overwrites `textEdited` and `edits` in place and updates `fixesCommit`. It does not create a transcript version. Analysis findings (DT-273) point at raw paragraph and word IDs, which never change.

Unique on (`transcriptId`, `paragraphId`). 25,311 rows in all, about 37 per sermon. Raw text is about 24 MB in total, and so is the edited text.

## Indexes

- Full-text: a GIN expression index on `to_tsvector('english', "textEdited")`. There is no stored search column. A query must use the same expression to hit the index: `WHERE to_tsvector('english', "textEdited") @@ websearch_to_tsquery('english', $1)`. A generated column was tried and dropped, because Prisma tries to drop its default on the next migration, which Postgres rejects.
- Lookups: `sermon(spokenDate)`, `sermon(s3AudioPath)`, `sermon_paragraph(transcriptId, position)`.

Prisma cannot express a partial unique index or an expression index. These go in the migration as hand-written SQL, in the same file as the table creation. Before the first run, use `prisma migrate diff` against a scratch database, so a later `migrate dev` does not try to drop what Prisma does not know.

## Extensions

None in the first migration. Full-text search needs no extension. At 25,000 rows an unindexed `ILIKE` for a name should take tens of milliseconds, so the trigram index and `unaccent` wait until a search is measured slow. Add `vector` only when embeddings start. It needs a decision on the embedding model and its size, and an `embedding` table keyed on paragraph.

## Sync

Sanity is the only source. Postgres never writes back.

1. **Webhook.** The only automatic sync. The existing route `frontend/app/api/sanity-revalidate/route.ts` is a signed, GROQ-powered publish webhook that today only maps a changed document to cache tags. The mirror hooks into it. Each event upserts one sermon row. A repeated delivery does no harm. Whether the Sanity webhook filter includes sermons and fires on delete is set in Sanity's manage page and is not yet verified.
2. **Ordering.** No ordering guard in the first version. Sermons change about once a week, so out-of-order delivery is rare, and rows are keyed on `_id`, so a late delete of an old `_id` cannot undo a newer sermon. A guard on `_updatedAt` is wrong for deletes if a delete delivery carries the last `_updatedAt`, so add one only after checking what a delete delivery contains. Do not order by `_rev`, which is an opaque ID.
3. **Deletes are reversible.** A delete sets `deletedAt` and keeps the row. A later write for the same `_id` always clears `deletedAt`. `isPublished` is a separate field on the document. How the Studio's Unpublish action reaches the webhook is not yet verified. If it arrives as a delete, this rule already handles it.
4. **Recreated sermons.** A deleted sermon and its recreated copy have different `_id` values and the same `s3AudioPath`. Both rows may exist for a while. Readers use rows where `deletedAt` is null.
5. **Weekly flow.** The `sermon audio` step already talks to Sanity for the new sermon. It refreshes that one row then, at no extra cost.
6. **No scheduled reconcile.** A nightly job would add Sanity bandwidth for a rare failure. Instead, `sermon reconcile` is a command run by hand when something looks off, such as after bulk edits. It uses one fresh export and reports: sermons missing from Postgres, rows that changed, transcripts with no live sermon, and sermons whose file has no transcript.
7. **Staleness from Postgres alone.** A check on `syncedAt` and on orphaned transcripts needs no Sanity call.

A missed webhook can go unnoticed until someone looks at that sermon or runs the reconcile. The copied fields (date, speaker, series, passage, S3 path) change rarely, so this is acceptable.

## Import (DT-252)

1. Upsert a `sermon` row for every sermon in the Sanity export, all 760, guest speakers and unpublished included. Guest sermons are linked the same way as any other if a transcript exists for their audio. Today only the 692 have one.
2. For each transcript on disk, read its S3 key from the manifest (matched by sermon ID), normalize it, and insert one `sermon_transcript` and its paragraphs in one transaction.
3. A rerun is safe. A transcript with the same `s3Key` and `audioSha256` is updated in place: paragraphs' `textEdited`, `edits` and `fixesCommit` are rewritten. A new audio hash or model inserts a new version and flips `isCurrent`.
4. Batch inserts on one connection. The limit is 60 and the site needs headroom.
5. Normalizing: the manifest S3 path has `%20` for spaces and a leading slash. Sanity stores `/2026/2026-10-18.mp3`. Both sides are decoded and stripped before they are stored or joined.
6. Report: sermons with no transcript, transcripts with no sermon, date mismatches.

The shared file (2012-08-26 and 2012-09-02) has one transcript. Both sermons join to it by S3 key, so the import report names this pair.

## Hit Behavior

A hit is a paragraph. Showing it needs `textEdited`, the sermon's title and slug, and `startMs`. That is all in Postgres.

Playing from the matched words needs word-level times, which are not in Postgres. When a hit is opened, the page reads that one transcript's word-level JSON from `wordsPath` and finds the paragraph by `paragraphId`. This needs the word-level files somewhere the site can reach, for example a private S3 prefix. Edited words map back to raw words through the edit list's word IDs, so timing stays exact (see the edited-layer rules in `transcript-format.md`). Uploading the 692 word-level files is its own step, before Center City search.

## Size

| Item | Estimate |
| --- | --- |
| `sermon` | under 1 MB |
| `sermon_paragraph` text, raw and edited | about 48 MB |
| Full-text index | about 10 to 30 MB (rough guess, measure after the first import) |
| Total | about 60 to 80 MB |

This is several times the current 14 MB database, so check the Supabase plan limit before the import. Free is 500 MB, which still fits. Word-level JSON stays out, which is what keeps it small.

## Open Decisions

- Store edited text, or compute it from raw plus edits on read? This draft stores both. It costs about 24 MB and keeps search simple.
- Staff-only access. These tables hold full sermon text. Decide who can read them through the site before any page exposes them.
- Embeddings: model, size and when. Later.
- Whether to transcribe the 36 published guest-speaker sermons. They get rows and link automatically if a transcript is ever added.
- Where the word-level files live, and who can read them, before Center City search.

## Not Yet Verified

- The Sanity webhook's filter, projection and triggers (Sanity's manage page): that it includes sermons and fires on delete, and what a delete delivery carries.
- How the Studio's Unpublish action reaches the webhook.
- That Sanity `_rev` cannot be ordered. The design avoids `_rev` either way.
