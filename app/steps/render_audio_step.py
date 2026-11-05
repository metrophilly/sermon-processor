import json
import os
import subprocess

from app.data_models.pipeline_data import PipelineData
from app.utils.ffmpeg_progress import run_ffmpeg
from app.utils.paths import audio_codec_for
from app.utils.timestamps import parse_timestamp  # noqa: F401  (re-exported)

LOUDNORM = "loudnorm=I=-16:TP=-1:LRA=11:linear=true"
# Silence between the intro and the sermon, and between the sermon and the outro.
DEFAULT_GAP_SECONDS = 2.5
# Allow the configured end time to overshoot the real duration by this much,
# since durations from ffprobe and wall-clock timestamps rarely agree exactly.
_END_TOLERANCE_SECONDS = 1.0


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
    ffmpeg_loglevel="error",
    ffmpeg_hide_banner=True,
    output_path=None,
    gap_seconds=DEFAULT_GAP_SECONDS,
    extra_output_path=None,
):
    """
    Trims the main audio, fades it in and out, loudness-normalizes every
    segment, and joins intro + main + outro, all in a single ffmpeg run.

    `gap_seconds` of digital silence is placed between the intro and the sermon
    and between the sermon and the outro (0 for none). It is added on top of the
    sermon's own short lead-in and tail, which are already inside the trim.

    Replaces the old trim -> fade -> normalize x3 -> concat chain. There are no
    intermediate files, so a failed run cannot leave behind anything that
    poisons the next run, and the input can be any container ffmpeg can read
    (wav, mp3, m4a, ...).

    Intro and outro are optional. If `start_time`/`end_time` are omitted the
    whole file is used.

    The result is written to `output_path` if given, otherwise next to the main
    file as `<name>_rendered.<format>`, and becomes the pipeline's active file.
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

    gap = max(0.0, float(gap_seconds))
    total_seconds = length
    segments = []  # (kind, path, input_options); kind is "clip" or "silence"
    if data.intro_file_path:
        total_seconds += probe_audio_duration(data.intro_file_path)
        segments.append(("clip", data.intro_file_path, []))
        if gap:
            segments.append(("silence", None, []))  # intro | silence | sermon
            total_seconds += gap
    main_index = len(segments)
    segments.append(("clip", main_path, ["-ss", f"{start:.3f}", "-t", f"{length:.3f}"]))
    if data.outro_file_path:
        if gap:
            segments.append(("silence", None, []))  # sermon | silence | outro
            total_seconds += gap
        total_seconds += probe_audio_duration(data.outro_file_path)
        segments.append(("clip", data.outro_file_path, []))

    command = ["ffmpeg", "-y", "-loglevel", ffmpeg_loglevel]
    if ffmpeg_hide_banner:
        command.append("-hide_banner")

    filters = []
    for index, (kind, path, input_options) in enumerate(segments):
        if kind == "silence":
            command.extend(
                ["-f", "lavfi", "-t", f"{gap:.3f}", "-i", f"anullsrc=r={sample_rate}:cl=stereo"]
            )
            filters.append(f"[{index}:a]aformat=channel_layouts=stereo[s{index}]")
            continue
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
    primary_label, extra_label = "[out]", None
    if extra_output_path:
        # ffmpeg can't map one filter output to two files, so split it first.
        filters.append("[out]asplit=2[out_a][out_b]")
        primary_label, extra_label = "[out_a]", "[out_b]"

    codec, bitrate = audio_codec_for(f".{output_format}")
    command.extend(
        ["-filter_complex", ";".join(filters), "-map", primary_label, "-vn", "-c:a", codec]
    )
    if bitrate:
        command.extend(["-b:a", bitrate])
    command.extend(["-ar", str(sample_rate), "-ac", "2"])

    if output_path:
        output_file = output_path
        os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
    else:
        output_file = f"{os.path.splitext(main_path)[0]}_rendered.{output_format}"
    partial_file = f"{os.path.splitext(output_file)[0]}.partial.{output_format}"
    command.append(partial_file)

    # An optional second file (e.g. an mp3 beside the wav) from the same pass:
    # the audio is only processed once, and both files are the same sermon.
    extra_partial = None
    if extra_output_path:
        extra_base, extra_ext = os.path.splitext(extra_output_path)
        extra_codec, extra_bitrate = audio_codec_for(extra_ext)
        os.makedirs(os.path.dirname(os.path.abspath(extra_output_path)), exist_ok=True)
        extra_partial = f"{extra_base}.partial{extra_ext}"
        command.extend(["-map", extra_label, "-vn", "-c:a", extra_codec])
        if extra_bitrate:
            command.extend(["-b:a", extra_bitrate])
        command.extend(["-ar", str(sample_rate), "-ac", "2", extra_partial])

    clips = sum(1 for kind, _, _ in segments if kind == "clip")
    print(
        f"Rendering {os.path.basename(main_path)} "
        f"[{start:.0f}s-{end:.0f}s] with {clips - 1} intro/outro "
        f"segment(s) -> {output_file}"
    )
    try:
        run_ffmpeg(command, total_seconds)
        os.replace(partial_file, output_file)  # only a finished file gets the real name
        if extra_partial:
            os.replace(extra_partial, extra_output_path)
    finally:
        for leftover in (partial_file, extra_partial):
            if leftover and os.path.exists(leftover):
                os.remove(leftover)

    data.active_file_path = output_file
    return data
