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
  windows (DT-248 adds a check).
- Times next to music can be off by about a second.
