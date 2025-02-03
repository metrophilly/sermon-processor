# 🎛️ Metro Sermons Processor

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
- to run just audio processing:
  - `make run-audio`
- to run just video processing:
  - `make run-video`
- to run both sequentially:
  - `make run-both`

## Bypassing the Youtube downloader

There are times when the script will fail at the 'Downloading Youtube' step. In
order to sidestep this, follow these steps:

1. Download the audio and videofile on your own, and add it to the `cache`
   folder.

   - Helper scripts:
     - my audio download one-liner:
       `yt-dlp -f "bestaudio" -x --audio-format m4a -o "%(upload_date>%Y-%m-%d)s.%(ext)s" "https://youtube.com/live/g0jKUy1hV4w"`
     - my video download one-liner:
       `yt-dlp -f "bestvideo+bestaudio/best" -o "%(upload_date>%Y-%m-%d)s.mp4" --merge-output-format mp4 "https://youtube.com/live/g0jKUy1hV4w"`

2. In `config/pipeline_config.json`, flip the `manual_download` boolean to
   `true`, and add in the appropriate paths to the files to the `manual_path`
   fields.

   - eg: In `config/pipeline_config.json`:

     ```
     {
         ...
         "manual_download": false,
         ...
         "audio": {
             "manual_path": "cache/audio/2025-02-02.m4a",
             ...
         },
         "video": {
             "manual_path": "cache/video/2025-02-02.mp4",
             ...
         }
     }
     ```

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

### `ffmpeg` Flag Notes

`ffmpeg` is the main file processing engine. To run it in the different steps,
we construct a string array of commands and flags, then call it directly as a
system subprocess. In the constructed flags the following are useful to know:

- `-crf` - Constant Rate Factor
  - usually set to: 16
  - "The range of the quantizer scale is 0-51: where 0 is lossless, 23 is
    default, and 51 is worst possible. A lower value is a higher quality and a
    subjectively sane range is 18-28. Consider 18 to be visually lossless or
    nearly so: it should look the same or nearly the same as the input but it
    isn't technically lossless."
- `-preset`
  - usually set to: ultrafast
  - "These presets affect the encoding speed. Using a slower preset gives you
    better compression, or quality per filesize, whereas faster presets give you
    worse compression. In general, you should just use the preset you can afford
    to wait for. Presets can be ultrafast, superfast, veryfast, faster, fast,
    medium (default), slow and veryslow."

We've set the default to `crf=16` and `preset=ultrafast` because we're ok with
the larger resultant filesize, as we're generally just going to upload it to
youtube and then delete it.

### Output

After the pipeline runs, check the `output/{stream_id}/` dir for the finished
file (`stream_id` is whatever you set in the config file)
