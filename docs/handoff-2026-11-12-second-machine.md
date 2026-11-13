# Running The Pilot On A Second Mac (12 Nov 2026)

How to run the transcription pilot scripts on another Mac and bring the results
back. Read `docs/handoff-2026-11-12-pilot.md` first for what the pilot found and
why. This doc is only about setup and running.

## Start Here

**Machines.**

| | Machine A (where the pilot ran) | Machine B (second Mac) |
| --- | --- | --- |
| Chip | M1 Max, 10 core CPU, 24 core GPU | M4 Pro |
| RAM | 32 GB | 24 GB |
| Hostname | `MacBookPro` | unknown |

Both have enough memory for large-v3 (about 3 GB). Speed on B is untested.
Expect it to be within about 20% of A, not clearly faster.

**What is in GitHub.** The `pilot/` scripts, the handoff docs and the built tools
(`sermon manifest`, `transcribe`, `batch`, `fixes`) are all on `main` in
`metrophilly/sermon-processor`. Not in GitHub: `pilot/audio/`, virtual
environments and `output/`.

**What you do not need.** No AWS login. The sermon audio is public by URL.
No Replicate account. No Sanity token. Everything here is free.

## Setup On Machine B

1. Install tools (once):

```bash
brew install ffmpeg python@3.12
```

2. Get the code.

```bash
git clone https://github.com/metrophilly/sermon-processor.git ~/src/METRO/sermon-processor
cd ~/src/METRO/sermon-processor
```

   For a split archive run, use `sermon batch --years 2012 2013 ...` on each
   machine so the two never do the same sermon. Each machine needs its own
   `output/archive/manifest.json` (`sermon manifest --env-file ...`).

3. Create the GPU environment and check the audio URLs:

```bash
bash pilot/setup_new_machine.sh
```

   This installs `mlx-whisper` into `pilot/.venv-mlx` (it pulls PyTorch, so it
   takes a few minutes) and prints `GPU device: Device(gpu, 0)` if the Apple GPU
   is visible. Add `WITH_CPU_ENV=1` in front of the command to also build a
   `faster-whisper` environment for `small.en` and `medium.en`.

4. Download the 10 audio files (about 300 MB):

```bash
python3 pilot/fetch_audio.py
```

   It reads `pilot/manifest.json` and tries the path stored in Sanity first,
   then `/YEAR/DATE.mp3`. All 10 resolved on 12 Nov (the 2020 file only through
   the fallback).

## Running The Scripts

Run from the `sermon-processor` folder. All scripts skip files that already have
a result, so they are safe to stop and restart. Keep the Mac awake with
`caffeinate -i`. Results go to `pilot/results/DATE.MODEL.json`.

| Task | Command |
| --- | --- |
| GPU, both large models, all 10 files | `caffeinate -i pilot/.venv-mlx/bin/python pilot/run_mlx.py` (full `mlx-large` was not run; Paul chose turbo, so prefer the next row) |
| GPU, turbo only | `MLX_ONLY=mlx-turbo caffeinate -i pilot/.venv-mlx/bin/python pilot/run_mlx.py` |
| GPU, one file | `MLX_ONLY=mlx-turbo pilot/.venv-mlx/bin/python pilot/run_mlx.py 2019-07-07` |
| CPU `small.en` and `medium.en` | `caffeinate -i pilot/.venv-cpu/bin/python pilot/run_pilot.py` (needs `WITH_CPU_ENV=1` setup) |

`run_mlx.py` uses `mlx-community/whisper-large-v3-turbo` ("mlx-turbo") and
`mlx-community/whisper-large-v3-mlx` ("mlx-large"), word timestamps on,
`condition_on_previous_text=False`, English. The first run downloads the model
from Hugging Face (about 1.6 GB for turbo, about 3 GB for large). No login
needed. The script prints one line per finished file with the speed.

## Splitting Work Between The Two Macs

Pass dates to run only some files, and set `MLX_ONLY` to pick the model. For
example, machine A runs turbo and machine B runs large-v3 on the same ten
files:

```bash
# machine A
MLX_ONLY=mlx-turbo caffeinate -i pilot/.venv-mlx/bin/python pilot/run_mlx.py
# machine B
MLX_ONLY=mlx-large caffeinate -i pilot/.venv-mlx/bin/python pilot/run_mlx.py
```

Never run the same model on the same file on both machines at once. Compare
speed only between runs of the same model and file.

## Bringing Results Back

Machine A scores the results because the review marks and compare scripts are
there. Zip the new results on machine B and send them to A:

```bash
cd ~/src/METRO/sermon-processor
tar czf ~/Downloads/results-machine-b.tgz pilot/results
```

On machine A, extract over the existing folder (file names differ per model, so
nothing is overwritten):

```bash
cd ~/src/METRO/sermon-processor && tar xzf ~/Downloads/results-machine-b.tgz
```

Also note the chip in the message, because the speed column depends on it.

## What To Check After A Run

1. **Speed.** Read the log lines. Record the chip next to every number.
2. **Dropped speech.** Compare word counts per sermon with
   `small.en` and `medium.en`. A model that returns noticeably fewer words is
   dropping text. `medium.en` dropped 3 or more words in 34 places that
   `small.en` kept.
3. **Quality.** Score against Paul's 80 marks in `pilot/review_results.json`.
   At each marked spot, check whether the new text matches the model Paul
   picked. The scoring script for the new models is not written yet.
4. **Word timestamps.** Spot-check three words by listening, especially next to
   music.

## Known Caveats

- `mlx-whisper` uses the original Whisper decoding code, so it can still drop
  speech even with `condition_on_previous_text=False`.
- **Model downloads were very slow on machine A on 12 Nov** (about 0.2 MB/s
  from Hugging Face, and about 0.3 MB/s from S3 at the same time). The turbo
  model (about 1.6 GB) sat at 1.07 GB for over 40 minutes, so no `mlx-whisper`
  timing exists yet. If a download stalls, stop the run, then resume with
  `HF_HUB_DISABLE_XET=1 pilot/.venv-mlx/bin/python -c "from huggingface_hub import snapshot_download as s; s('mlx-community/whisper-large-v3-turbo')"`.
  The partial file resumes. Models are cached in `~/.cache/huggingface/hub`, so
  a finished download is reused. Machine B on a faster connection may be the
  quickest way to get the first timing.
- Turbo results for all 10 files exist (`pilot/results/*.mlx-turbo.json`, 21x to
  24x realtime on the M1 Max). Paul chose turbo for the full run on 12 Nov.
  `mlx-large` was not run. Score any new results with
  `.venv/bin/python pilot/score_models.py small.en medium.en mlx-turbo`
  (needs a `faster-whisper` environment or any Python 3, standard library
  only).
- The speed estimates here are expectations, not measurements.
- `pilot/audio/` is not in GitHub. Audio comes from `fetch_audio.py`.

## Files

| Path | Purpose |
| --- | --- |
| `pilot/run_mlx.py` | GPU run, resumable, `MLX_ONLY` picks the model |
| `pilot/run_pilot.py` | CPU `small.en` and `medium.en` |
| `pilot/fetch_audio.py` | Downloads the 10 files from public URLs |
| `pilot/setup_new_machine.sh` | One-time environment setup |
| `pilot/manifest.json` | The 10 pilot sermons |
| `pilot/results/` | Transcripts with word timings and confidence |
| `pilot/review_results.json` | Paul's 80 marks |
| `pilot/compare.py`, `diffs.py`, `build_sheet.py` | Analysis and the review sheet |
