import json
import os
import re
import subprocess

from app.data_models.pipeline_data import PipelineData
from app.utils.paths import audio_codec_for

LOUDNORM = "loudnorm=I=-16:TP=-1:LRA=11:linear=true"
_TIMESTAMP = re.compile(r"^(\d+):([0-5]\d):([0-5]\d(?:\.\d+)?)$")
# Allow the configured end time to overshoot the real duration by this much,
# since durations from ffprobe and wall-clock timestamps rarely agree exactly.
_END_TOLERANCE_SECONDS = 1.0


def parse_timestamp(value):
    """Converts "HH:MM:SS" (optionally with fractional seconds) to seconds."""
    match = _TIMESTAMP.match(str(value).strip())
    if not match:
        raise ValueError(f"Invalid timestamp '{value}'. Expected HH:MM:SS.")
    hours, minutes, seconds = match.groups()
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def probe_audio_duration(path):
    """
    Returns the duration in seconds of the first audio stream's container.

    Raises a ValueError with a readable message if the file is missing, is not
    something ffprobe can read, or has no audio stream. This is the early check
    that catches a bad drop-in file before any slow processing starts.
    """
    if not path or not os.path.exists(path):
        raise ValueError(f"Audio file not found: {path}")

    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "a:0",
            "-show_entries",
            "stream=codec_type:format=duration",
            "-of",
            "json",
            path,
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise ValueError(
            f"ffprobe could not read '{path}'. It may be corrupt or not an audio "
            f"file. ffprobe said: {result.stderr.strip() or 'no details'}"
        )

    info = json.loads(result.stdout or "{}")
    if not info.get("streams"):
        raise ValueError(f"'{path}' has no audio stream.")

    try:
        return float(info["format"]["duration"])
    except (KeyError, TypeError, ValueError):
        raise ValueError(f"Could not determine the duration of '{path}'.")


def _segment_filter(label_in, label_out, sample_rate, fade=None):
    """Filter chain for one segment: optional fade, loudness, uniform format."""
    chain = []
    if fade:
        fade_duration, length = fade
        chain.append(f"afade=t=in:st=0:d={fade_duration}")
        chain.append(f"afade=t=out:st={length - fade_duration:.3f}:d={fade_duration}")
    chain.append(LOUDNORM)
    # loudnorm internally resamples to 192 kHz, so resample *after* it.
    chain.append(f"aresample={sample_rate}")
    chain.append("aformat=channel_layouts=stereo")
    return f"[{label_in}]{','.join(chain)}[{label_out}]"


def render_audio_step(
    data: PipelineData,
    start_time=None,
    end_time=None,
    output_format="wav",
    fade_duration=1,
    sample_rate=44100,
    ffmpeg_loglevel="info",
    ffmpeg_hide_banner=True,
):
    """
    Trims the main audio, fades it in and out, loudness-normalizes every
    segment, and joins intro + main + outro, all in a single ffmpeg run.

    Replaces the old trim -> fade -> normalize x3 -> concat chain. There are no
    intermediate files, so a failed run cannot leave behind anything that
    poisons the next run, and the input can be any container ffmpeg can read
    (wav, mp3, m4a, ...).

    Intro and outro are optional. If `start_time`/`end_time` are omitted the
    whole file is used.

    The result is written next to the main file as `<name>_rendered.<format>`
    and becomes the pipeline's active file.
    """
    main_path = data.active_file_path
    main_duration = probe_audio_duration(main_path)

    start = parse_timestamp(start_time) if start_time else 0.0
    end = parse_timestamp(end_time) if end_time else main_duration

    if end <= start:
        raise ValueError(
            f"Trim end ({end_time}) must be after trim start ({start_time})."
        )
    if end > main_duration + _END_TOLERANCE_SECONDS:
        raise ValueError(
            f"Trim end {end_time} is past the end of '{main_path}' "
            f"({main_duration:.1f}s long). Check the trim times in the config."
        )
    end = min(end, main_duration)
    length = end - start
    fade = min(float(fade_duration), length / 2)

    main_index = 1 if data.intro_file_path else 0
    segments = []  # (path, input_options)
    if data.intro_file_path:
        probe_audio_duration(data.intro_file_path)
        segments.append((data.intro_file_path, []))
    segments.append((main_path, ["-ss", f"{start:.3f}", "-t", f"{length:.3f}"]))
    if data.outro_file_path:
        probe_audio_duration(data.outro_file_path)
        segments.append((data.outro_file_path, []))

    command = ["ffmpeg", "-y", "-loglevel", ffmpeg_loglevel]
    if ffmpeg_hide_banner:
        command.append("-hide_banner")

    filters = []
    for index, (path, input_options) in enumerate(segments):
        command.extend(input_options + ["-i", os.path.abspath(path)])
        filters.append(
            _segment_filter(
                f"{index}:a",
                f"s{index}",
                sample_rate,
                fade=(fade, length) if index == main_index else None,
            )
        )
    joined = "".join(f"[s{i}]" for i in range(len(segments)))
    filters.append(f"{joined}concat=n={len(segments)}:v=0:a=1[out]")

    codec, bitrate = audio_codec_for(f".{output_format}")
    command.extend(
        ["-filter_complex", ";".join(filters), "-map", "[out]", "-vn", "-c:a", codec]
    )
    if bitrate:
        command.extend(["-b:a", bitrate])
    command.extend(["-ar", str(sample_rate), "-ac", "2"])

    base = os.path.splitext(main_path)[0]
    output_file = f"{base}_rendered.{output_format}"
    partial_file = f"{base}_rendered.partial.{output_format}"
    command.append(partial_file)

    print(
        f"Rendering {os.path.basename(main_path)} "
        f"[{start:.0f}s-{end:.0f}s] with {len(segments) - 1} intro/outro "
        f"segment(s) -> {output_file}"
    )
    try:
        subprocess.run(command, check=True)
        os.replace(partial_file, output_file)  # only a finished file gets the real name
    finally:
        if os.path.exists(partial_file):
            os.remove(partial_file)

    data.active_file_path = output_file
    return data
