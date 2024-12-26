# 🎛️ Metro Sermons Processor

**BREAKING CHANGES FROM DEC 2024 REFACTOR!**

## tl;dr

1. set `config/pipeline_config.json`
2. run `make run`
3. check `output/` for processed files

## Configuration

`config/pipeline_config.json` is the main config file needed to run this thing.

- run the following to copy the example config to get the structure:
  - `cp config/pipeline_config.json.example config/pipeline_config.json`
- then update file with actual configurations (ask paul for now—will add to
  bitwarden vault when done)

## Running

Run scripts are based out of the `Makefile` (make sure you have Docker running
in the background)

- to run:
  - `make run`

## Testing

All tests are held in `tests/`, and are run through `pytest`

- to run all tests:
  - `make test`
- to run a single test:
  - `make test TEST_FILE=test_filename.py`

## 🌊 General flow

### Startup & Docker

1. Running `make run` looks in the `Makefile` and runs the `run` command
2. `make run` kicks off `docker-compose`, which builds a container based of the
   `Dockerfile`
3. The running container calls the startup script at `scripts/startup.py`

### Audio Processing

Selecting to process the audio kicks off `scripts/run_audio_pipeline.py`, which:

1. Validates that the config file is correct which builds the main audio
2. Creates the PipeLineData dataclass, which is the main object that tracks the
   paths of the different intermediate steps of the pipeline
3. Calls `app/pipelines/audio_pipeline.py` which is the meat of the
   processing—`create_audio_pipeline()` composes and returns a pipeline made of
   discrete "steps" (found in `app/steps/`) that will iteratively run and
   process the piece of content as we need.

### DownloaderProxy & Caching

One problem that we had was re-running the script, only to download the same
files we already had all over again. In order to solve this, we created
`app/downloaders/downloader_proxy.py`. What this does is, during the downloading
step, before we actually download the file, we predict what the resulting output
filepath is going to be, and if it already exists, we just use that filepath,
and skip the download. This should save us a bunch of time on script re-runs.

`app/cache/` holds the downloaded and intermediary files.

### Output

After the pipeline runs, check the `output/{stream_id}/` dir for the finished
file (`stream_id` is whatever you set in the config file)
