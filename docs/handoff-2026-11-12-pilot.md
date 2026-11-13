# Transcription Pilot Handoff (12 Nov 2026)

Findings from the DT-246 pilot, the YouTube caption check and the vocabulary
test. Read after `docs/handoff-2026-11-05.md`, which covers the `sermon audio`
tool and the overall plan. The pilot files are committed in `pilot/`. The
built tools are in `app/` (see "Built Since The Pilot").

## Start Here

**Status.** The 10-sermon pilot ran `small.en` and `medium.en` (CPU) and
`large-v3-turbo` (Apple GPU, `mlx-whisper`). Paul marked the 80-spot review
sheet. **Paul chose `large-v3-turbo` via `mlx-whisper` for the full run on 12
Nov 2026** for its balance of speed (about 21x realtime) and accuracy (about as
good as `medium.en`, better on 2012 to 2017 files). Full `large-v3` was started
and stopped by Paul's decision, not run. See "GPU Run With mlx-whisper".

**Linear.** Project "Sermon Transcripts and Search" (P-DT-16). Related issues:
DT-243 (decision, comment posted), DT-245 (manifest), DT-246 (this pilot),
DT-247 (export), DT-248 (batch mode), DT-249 (vocabulary and fix list),
DT-251 (full run), DT-272 (intake page), DT-273 (analysis table). A comment on
the project lists the order of work after the pilot.

## Decisions Made

| Decision | Detail |
| --- | --- |
| Where sermons live (DT-243) | Sanity stays the editor. Postgres mirrors it. Join on the published Sanity `_id` with any `drafts.` prefix removed. Slug is a second, non-authoritative column |
| Weekly flow | Option A: the `sermon audio` CLI gets a final step (upload to S3, set `s3AudioPath`, transcribe, import). The transcript always matches the exact file at `s3AudioPath`. A cloud trigger (option B) is a fallback only |
| Mirror trigger | Hang it off the signed webhook route `/api/sanity-revalidate`, plus a one-time backfill. No polling |
| Center City role | Intake hub (DT-272). Pre-fills from the Sunday plan sheet (`bulletins/sundayPlan.ts`), not from bulletin PDFs |
| Analysis | One generic re-runnable table (DT-273). Every finding quotes the transcript and rows reference a transcript version. FCF and gospel thread rows are staff-only suggestions until reviewed |
| Prompting Whisper | Do not use it (see "Vocabulary Test") |

## Pilot Setup

- **Sermons.** 10 published sermons from leadership speakers, one each from
  2012, 2014, 2016, 2017, 2019, 2020, 2022, 2023, 2025 and 2026. 6.5 hours of
  audio in total.
- **Audio.** Bucket `metrophilly-sermons` (us-east-2). Not
  `metrophilly-center-city-dev`, which `frontend/.env.local` names.
- **Files.** `pilot/manifest.json`, `pilot/inventory.json` (all 701 sermons
  with an `s3AudioPath`), `pilot/audio/` (about 300 MB, should be gitignored),
  `pilot/results/DATE.MODEL.json` (words, times, confidence),
  `pilot/run_pilot.py` (resumable), `pilot/compare.py`.
- **Run settings.** `faster-whisper`, CPU, `int8`, word timestamps on, no VAD
  filter, audio decoded with our own ffmpeg.

## Speed And Agreement

| | `small.en` | `medium.en` |
| --- | --- | --- |
| Speed on full sermons | 9.4x realtime (8.3x to 11.2x) | 2.6x (2.2x to 3.1x) |
| The 10 sermons | 42 min | 2.5 hours |
| Estimate for 700 sermons | about 49 hours | about 178 hours |

- The earlier 14x for `small.en` came from a 6 minute slice. Use 9.4x.
- The two models agree on 97.5% to 99.2% of words per sermon. This is
  agreement, not an error rate.
- Older files (2012 to 2017) agree slightly less (97.6% to 97.8%) than 2022 to
  2026 (98.7% to 99.2%).
- 862 disagreement spots in total. In a sample of 16, about half were
  formatting ("gonna" vs "going to", "1" vs "one"). Some were real fixes by
  `medium.en` ("cymbals", "no ifs, ands"). One was unclear.
- Low-confidence words (probability under 0.5): 2% to 6% per sermon. The
  highest were the short 2019 file and the 2020 file.
- No problem year stands out. Mono vs stereo made no visible difference.
- Not tried: `mlx-whisper`, `whisper.cpp` (Mac GPU). They could cut the
  `medium.en` time a lot.

## Review Sheet

`pilot/review.html` lists 80 spots (8 per sermon) picked from 399 substantive
disagreements. Formatting-only and filler-only differences are removed. Each
card has a "Play 12s" button, radio buttons (small, medium, both fine,
neither) and an optional "what was actually said" box. Answers save in the
browser. "Copy results as JSON" copies them. Open it in a normal browser from
the `pilot/` folder so the relative `audio/` path works. The page script was
syntax-checked only. Audio playback and saving were not tested in a browser.

`pilot/build_sheet.py` rebuilds it. `pilot/diffs.py` lists all disagreements.

## Review Sheet Results

Paul marked all 80 spots on 12 Nov. Raw answers: `pilot/review_results.json`.

| Answer | Count |
| --- | --- |
| `medium.en` right | 45 |
| `small.en` right | 29 |
| Both fine | 4 |
| Neither | 2 |

- Of the 74 decisive spots, `medium.en` won 61%. These spots are the places
  the models differ (about 1% to 2.5% of words), so the real gap in word
  accuracy is small, roughly half a percentage point. The sample favoured name
  and multi-word differences, so treat this as a rough figure.
- **By era.** 2019 to 2026: `medium.en` won 36 of 46 decisive spots (78%).
  2012 to 2017: `small.en` won 19 of 28 (68%). So `medium.en` is not clearly
  better on the older recordings.
- **Why `small.en` wins on older files: `medium.en` drops speech.** Across all
  862 disagreements, `medium.en` dropped 3 or more words that `small.en` kept
  in 34 places (302 words), 26 of them in 2012 to 2017. `small.en` dropped
  stretches that `medium.en` kept in 18 places (113 words). Seven of Paul's
  "small wins" were real speech that `medium.en` omitted. Dropped sentences
  hurt search and the quote check, so this matters more than a single wrong
  word.
- **Where `medium.en` wins:** content words (heir/air, cymbals/symbols,
  planter/planner, obeying, Goliath/life, Pangloss/Panglos).
- **Where `small.en` wins:** literal wording (it's vs it is, you're vs you
  are) and the dropped stretches above. Contractions are a style choice and
  need a normalization rule (see below).
- **Not a model problem, add to the fix list (DT-249):**
  - The speaker says "second" or "first" for a book number. The text should
    read "2 Samuel" and "1 Samuel". Normalize spoken ordinals before book
    names.
  - Greek transliterations are wrong in both models (`makrothumia`).
  - A scripture quote was misheard by both ("Christ is head of").
  - A repeated phrase ("one of the one of the") is real speech. Keep one
    instance when deduplicating.
- **Untested idea:** `medium.en` drops text partly because of context carried
  from the previous window. Rerun `medium.en` on 2012-08-05 and 2017-07-02
  with `condition_on_previous_text=False` and count the dropped stretches
  again.

## GPU Run With mlx-whisper (Large-V3-Turbo)

Same 10 files on the Apple GPU (M1 Max) with `mlx-whisper`, model
`mlx-community/whisper-large-v3-turbo`, word timestamps on, English,
`condition_on_previous_text=False`. Scripts: `pilot/run_mlx.py` (run),
`pilot/score_models.py` (score). Virtualenv: `pilot/.venv-mlx`.

- **Speed: 20x to 24x realtime** (20.2x to 23.9x per file), 6.5 hours of audio
  in about 18 minutes. `medium.en` on CPU was 2.6x. At 21x the full archive
  (about 583 hours) would take about 28 hours of GPU time. One machine, ten
  files, so treat the archive figure as a rough estimate.
- **Word timestamps:** present on every word.
- **Agreement:** 97.0% to 99.4% with each of the other models, per sermon.
- **Scored against Paul's 80 marks** (74 decisive spots):

| Model | Correct | Of which 2012 to 2017 | Of which 2019 to 2026 | Dropped windows (words) |
| --- | --- | --- | --- | --- |
| `small.en` | 23 (31%) | 15 of 28 | 8 of 46 | 1 (27) |
| `medium.en` | 43 (58%) | 9 of 28 | 34 of 46 | 4 (101) |
| `large-v3-turbo` | 47 (64%) | 18 of 28 | 29 of 46 | 2 (73) |

- **How to read the table.**
  - The scoring script matches each model's words near the marked time against
    the two readings Paul saw. Paul's own counts for the two original models
    were 29 and 45 correct, so the script undercounts a few spots as ties (7
    for `small.en`, 1 for `medium.en`, 5 for turbo). Compare models by ranking
    only.
  - The 80 spots were picked from places where `small.en` and `medium.en`
    differ. A third model that reads a spot a third way counts as wrong. Its
    errors outside those spots are untested.
  - 47 against 43 is within noise on 74 spots.
  - A dropped window is a 10 second window where the model has 30% or fewer of
    the words of the best other model.
- **Findings.**
  - Turbo is about as accurate as `medium.en` at roughly 8 times the speed.
  - Turbo does best on the 2012 to 2017 files (18 of 28), where `medium.en`
    fails (9 of 28). On the newer files `medium.en` is ahead (34 vs 29 of 46).
  - Turbo still drops some speech (2 windows, 73 words) even with
    `condition_on_previous_text=False`, less than `medium.en` (4, 101) and
    more than `small.en` (1, 27).
- **Model downloads were slow on 12 Nov** (0.2 MB/s, then back to about 3
  MB/s). A stalled download is fixed with a direct `curl -C -` resume into the
  Hugging Face cache blob, then a SHA-256 check against the blob file name.

## YouTube Captions

- Only **130 of 701** sermons have a `youtubeVideoID` in Sanity, all from 2024
  to 2026. None of 2012 to 2023 are linked. Older videos may exist on the
  channel but are not linked in Sanity.
- `yt-dlp --skip-download --write-auto-subs --sub-format json3` fetched the
  captions for the two pilot sermons with an ID (2025-07-06, 2026-06-07) with
  no bot check on 12 Nov. The earlier flakiness note still stands for bulk use.
  Files are in `pilot/yt/`.
- YouTube text agrees with each Whisper model on about 96% of words
  (`small.en` vs `medium.en` is 98.7% to 99%). It keeps fillers ("um", "uh").
  It has no punctuation or casing worth trusting.
- It got some things right where `medium.en` was wrong: "who sinned" beat
  "whose sin" in a John 9 passage.
- The video is about 55 seconds longer than the audio, so the timelines differ.
- **Conclusion.** Do not use YouTube as the base transcript (coverage 19%,
  timeline mismatch). Use it as a free third vote on the sermons that have it:
  where YouTube disagrees with both Whisper models, flag the spot for review.
  The official YouTube API with the channel owner's login is the clean way to
  get captions at scale. It was not tried.
- Paul chose not to add this to Linear.

## Vocabulary Test

Question: does giving Whisper a list of Bible names, Metro names and
theology terms improve `small.en`?

- Catalog: `pilot/vocab.json` (66 books, 40 characters, 27 places, 8 groups,
  15 theology terms, 5 Metro terms, 17 leadership names, 92 series titles).
  `pilot/vocab.py` builds a per-sermon string of about 60 terms within a 200
  token budget (Whisper's limit is about 223 tokens). It puts the books from
  the sermon's passage first.
- Test: `small.en` on 2012-08-05, 2014-07-27 and 2017-07-02 with
  `hotwords` and with `initial_prompt` (`pilot/run_vocab_test.py`,
  `pilot/vocab_compare.py`).
- **`hotwords` broke the transcript.** Only 40% to 45% of the words came out
  (2,713 of 6,299 in 2012). The cause was not diagnosed.
- **`initial_prompt` had almost no effect.** It agreed with the baseline on
  97% to 99% of words and the count of correct Bible names stayed the same. It
  pushed a few words the wrong way ("son" became "Sun" in the 2014 Luke 20
  sermon).
- A scan of all 20 transcripts for near-misspellings of catalog terms found
  none. Every near-miss was a real word ("Psalm", "Abraham's", "Nathan",
  "here's"). Both models spell Bible names correctly in these 10 sermons. The
  "Refodym" error from the earlier handoff came from `base.en`.
- **Conclusion.** Do not prompt Whisper. Use `vocab.json` as a fix list after
  transcription (DT-249): flag words close to a catalog term but not equal, and
  seed a find-and-replace list from errors Paul marks in the review sheet.
- **Not covered.** Metro leader names, Korean names and Metro jargon. They
  appear mostly in announcements and greetings, not in the sermon body. Adding
  the speaker's name to each sermon's list needs one more Sanity query (the
  `speaker` reference).

## Data Problems Found In Sanity And S3

- **2020 paths.** All 52 published 2020 sermons had an `s3AudioPath` of the
  form `/2020/DATE/<file>.mp3`. Those keys did not exist. The files sit at
  `/2020/DATE.mp3`. A separate session reported writing
  `studio/scripts/fix-sermon-audio-paths.mjs`, but **that file is not on disk
  or in git history** (checked 12 Nov). The Sanity paths themselves were fixed:
  the manifest run on 12 Nov found no sermon needing a path correction and
  `2020-07-05` now stores `/2020/2020-07-05.mp3`. Treat the script as lost.
- **9 sermons are blocked** (see "Manifest"). Decide for each whether to find
  the file or leave it out.
- **2019-07-07** is only 21 minutes. It is probably truncated or not a full
  sermon.
- **Duplicate slugs.** The 701 inventory had none. The full check, including
  unpublished and guest-speaker sermons, is still open.
- The `speaker` name did not come back from the first inventory query
  (`speaker->name` is not a field). Speakers have `firstName` and `lastName`.

## Manifest (DT-245, Built 12 Nov 2026)

`python3 sermon manifest --env-file ../metrophilly/frontend/.env.local` (the
read token can also come from `SANITY_API_READ_TOKEN`). One published-perspective
Sanity query, saved to `output/archive/sanity_sermons.json` (reruns reuse it;
`--refresh` queries again), then one HEAD request per file in the public bucket.
Writes `output/archive/manifest.json` (one row per sermon, keyed on the published
Sanity `_id`) and `report.txt`. Code: `app/archive/manifest.py`; tests:
`tests/utils/test_archive_manifest.py` (9 pass). The path stored in Sanity is
checked exactly as stored, never silently replaced.

- 760 sermons in Sanity: **702 eligible** (published, leadership speaker), 36 guest
  speakers and 22 unpublished excluded. **693 are ready**, 9 are blocked.
- Blocked: 8 sermons from early 2020 whose stored file (`Ch 19.mp3`) does not exist
  anywhere, and 1 sermon (2024-12-15) with no audio path and a second sermon on the
  same date.
- Warnings (still ready, need a look): 6 date mismatches between `spokenDate` and
  the date in the file path (2019-02-24, 2020-10-05, 2022-12-14, 2024-08-04,
  2024-08-11, 2026-08-02), 2 sermons sharing one file (2012-08-26 and 2012-09-02,
  "Identity, Genesis 32"; de-duplicate by `s3_key` before a batch run), 2 sermons on
  one date (2024-12-15).
- 131 rows have a YouTube ID. All 10 pilot sermons are ready.
- Not yet checked: that every file is a full sermon (the 2019-07-07 file is 21
  minutes), and duplicate slugs across all 760 documents.

## Built Since The Pilot

All committed and pushed to `main`. Format and usage are in
`docs/transcript-format.md`.

| Issue | What | Command |
| --- | --- | --- |
| DT-245 | Manifest of 702 sermons, S3 existence check, problems list | `sermon manifest` |
| DT-247 | Transcript JSON (raw layer, stable IDs) and VTT | `sermon transcribe` |
| DT-248 | Resumable batch, newest first, Ctrl+C safe, failure report | `sermon batch` |
| DT-249 | Shared fix list, edited layer, raw never changed | `sermon fixes` |

The batch ran for real on 6 sermons (2 to 2.5 minutes each). A real Ctrl+C was
tested and resumed. The 6 outputs are in `output/archive/transcripts/` (not in
git).

## Still Open

- [ ] Run the full archive (DT-251), about 25 hours on the M1 Max for 693
  sermons. The M4 Pro can take half the years (see the second-machine doc).
  Not started.
- [ ] Dropped speech. Turbo still dropped 2 windows (73 words) in the pilot. The
  batch lists sparse 20 second windows as a hint. It is not proof.
- [ ] Fix list: only 3 kinds of rule so far (web address, hyphen, spoken
  numbers before books). Grow it after the full run. Names and Greek words from
  `pilot/vocab.json` showed no repeat errors in the 6 recent transcripts. Older
  sermons (2012 to 2017) are the likely place for them.
- [ ] Prompting the engine with vocabulary does not help (see "Vocabulary
  Test"). DT-249's first done-when ("fewer errors with vocabulary on") is not
  met and will not be.
- [ ] Data problems: 9 blocked sermons (8 `Ch 19.mp3`, 1 with no path), 6 date
  mismatches, 2 sermons sharing one file (2012-08-26, 2012-09-02), 2 sermons on
  2024-12-15, and a 21 minute file on 2019-07-07.
- [ ] Postgres import (DT-252, DT-253) and the mirror (DT-244).
- [ ] DT-243 checks: Supabase `pgvector` and `pg_trgm`, duplicate slug query,
  coordination with the Sermons Expansion project, Sunday plan sheet columns.
- [ ] A partial 0.9 GB `large-v3` download is in `~/.cache/huggingface/hub`.
  Delete it to free space.

## Next Steps In Order

1. Run the full archive (DT-251): `sermon batch --dry-run`, then `sermon batch`.
2. Run `sermon fixes output/archive/transcripts` and review the edits.
3. Import into Postgres (DT-252, DT-253).
