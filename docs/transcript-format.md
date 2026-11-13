# Transcript Export Format

What `sermon transcribe` writes (DT-247). The machine-readable schema is
`config/transcript_schema.json` (JSON Schema draft 7, schema version 1). The
command validates every file against it before writing.

## Command

```bash
python3 sermon transcribe <audio file> --date YYYY-MM-DD [--sermon-id ID] [--output-dir DIR]
```

- Needs Apple Silicon and `mlx-whisper` (`python3 sermon setup` installs it).
- Model: `whisper-large-v3-turbo`, English, word timestamps, no carried-over
  context (the DT-246 pilot choice).
- Default output folder: `output/transcripts/`. Files: `DATE.transcript.json`
  and `DATE.vtt`.
- `--sermon-id` is the published Sanity `_id` (no `drafts.` prefix). It defaults
  to the date. The manifest (`sermon manifest`) lists the IDs.
- `--from-raw FILE` builds from a pilot results file instead of running the
  engine. Used for tests and re-exports.
- The JSON file is written last. A transcript file that exists is a finished one.

## The JSON File

Layer `raw`: the machine text, never edited after export. Corrections live in a
separate layer (DT-256) that points at the word IDs.

| Field | Meaning |
| --- | --- |
| `schema_version` | `1` |
| `layer` | `"raw"` |
| `sermon_id`, `date` | Sanity `_id` and `YYYY-MM-DD` |
| `audio` | `file`, `sha256`, `duration_seconds` of the audio the times belong to |
| `model` | `engine`, `name`, `settings` |
| `word_count` | Total words |
| `paragraphs[]` | `id` (`p001`), `index`, `start_ms`, `end_ms`, `text`, `word_count`, `avg_confidence`, `min_confidence`, `words[]` |
| `words[]` | `id` (`w000001`), `start_ms`, `end_ms`, `text`, `confidence` (0 to 1) |

All times are whole milliseconds from the start of the audio file named in
`audio`. They are not valid for a different cut of the recording or for the
YouTube video.

## Paragraphs

About 150 to 250 words. A paragraph ends at a sentence end after a pause of 0.6
seconds or more once it has 150 words, at any sentence end once it has 200, and
at 250 at the latest. A last paragraph under 50 words joins the one before it.

## Stable IDs

Word IDs count up from `w000001` in order, and paragraph IDs from `p001`.
Rebuilding from the same raw words gives the same IDs. Two real GPU runs of the
same file gave the same words and times within 10 ms (checked on one 21 minute
sermon). The `audio.sha256` shows if the audio file changed, in which case the
IDs mean nothing for the new file.

## The VTT File

WebVTT captions made from the word list. A cue ends at a sentence end when it
has 40 characters or more, and never runs past 84 characters or 7 seconds. Cue
times never overlap. ffmpeg parses the output.

## Known Limits

- Confidence is the engine's per-word probability. It is not a measured error
  rate.
- The engine can drop stretches of speech. The pilot saw a few 10 second
  windows. The batch report lists sparse stretches as a hint (see "Batch Mode").
- Times next to music can be off by about a second.

## Batch Mode (DT-248)

```bash
python3 sermon manifest --env-file <file with the Sanity token>   # once, and after Sanity changes
python3 sermon batch --dry-run                                     # what would happen
python3 sermon batch                                               # the full archive
```

- Reads `output/archive/manifest.json`. Only sermons with status `ready` run.
  Blocked sermons are listed in the report, never transcribed.
- Order: newest first. For each sermon: download from the public bucket to
  `cache/archive/`, transcribe, write the export, delete the download.
- Output: `output/archive/transcripts/<sermon_id>/DATE.transcript.json` and
  `DATE.vtt`. A sermon is done when its transcript JSON exists.
- State and report: `output/archive/batch_state.json` (per sermon: status,
  attempts, seconds, words, warnings) and `batch_report.txt`.
- **Stopping.** Press Ctrl+C at any time. The sermon in progress is not saved and
  its download is removed. Run the same command to continue. Finished sermons are
  skipped, so a second run on a finished archive does nothing.
- **Failures.** A failed sermon is logged with its error and the batch carries
  on. The next run retries it. After 3 failures it is skipped until you pass
  `--retry-failed`.
- **Shared files.** If two sermons store the same audio file, only the newer one
  is transcribed and the other is skipped with the reason `shared_file`. Decide
  which sermon the file belongs to in Sanity.
- **Sparse stretches.** After each sermon the batch counts words in 20 second
  windows (skipping the first and last 90 seconds). A window with under 15
  words (the pilot median was 55) is listed in the report as a possible dropped
  stretch. It can also be silence or music. It is a hint, not proof.
- Options: `--limit N`, `--only ID_OR_DATE ...`, `--years 2020 2021`, `--redo ID ...`,
  `--retry-failed`, `--manifest PATH`, `--dry-run`.
- Time: about 2 minutes per 40 minute sermon on an M1 Max in the pilot. The
  progress line shows an estimate from the sermons done in this run.

## Fix List (DT-249)

```bash
python3 sermon fixes output/archive/transcripts --dry-run   # show the edits
python3 sermon fixes output/archive/transcripts             # write DATE.edited.json next to each transcript
```

- The list is `config/transcript_fixes.json`. Anyone can edit it. Each rule has an
  `id`, `find` (words in order, case ignored) and `replace`. Add a rule when the
  same mistake shows up in more than one sermon.
- Output is the `edited` layer: a list of edits that point at word IDs, plus the
  edited paragraph text. The raw `DATE.transcript.json` is never opened for
  writing. A test checks its SHA-256 before and after.
- A rule does not match across punctuation. "first, John said" is left alone.
  "first John" becomes "1 John". Punctuation after the last word is kept.
- First rules, from real output: the web address split ("MetroPhilly .org"), the
  space before a hyphen ("gospel -centered") and spoken numbers before book
  names. The 6 batch transcripts have 22 fixes in total.
- Vocabulary prompting is not used. The pilot found it did not help (see the
  pilot handoff). `pilot/vocab.json` stays as reference for spotting errors.
