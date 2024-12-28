import os
import subprocess

from app.constants import PipelineKeys
from app.data_models.pipeline_data import PipelineData
from app.utils.paths import file_ext


def fade_in_out_step(
    data: PipelineData,
    fade_duration: int = 2,
    ffmpeg_loglevel="info",
    is_video=False,
):
    """
    Adds fade-in and fade-out effects to a video file.

    Args:
        fade_duration (int): Duration of the fade-in and fade-out in seconds (default: 2).
    """

    file_key = PipelineKeys.ACTIVE_FILE_PATH
    input_path = getattr(data, file_key, None)

    if not input_path:
        raise ValueError(f"No input file found for {file_key}")

    ext = file_ext(input_path)
    output_path = input_path.replace(ext, f"_faded{ext}")

    # Get the video duration
    probe_command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        input_path,
    ]
    result = subprocess.run(probe_command, capture_output=True, text=True, check=True)
    total_duration = float(result.stdout.strip())

    # Calculate the start time for the fade-out
    fade_out_start = total_duration - fade_duration

    # fading the audio
    command = [
        "ffmpeg",
        "-loglevel",
        ffmpeg_loglevel,
        "-hide_banner",
        "-i",
        input_path,
        "-af",
        f"afade=t=in:st=0:d={fade_duration},afade=t=out:st={fade_out_start}:d={fade_duration}",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
    ]

    # just fading the video
    if is_video:
        command.extend(
            [
                "-vf",
                f"fade=t=in:st=0:d={fade_duration},fade=t=out:st={fade_out_start}:d={fade_duration}",
                "-c:v",
                "libx264",
                "-crf",
                "16",
                "-preset",
                "ultrafast",
            ]
        )

    command.extend(
        [
            output_path,
        ]
    )

    print(f"Applying fade-in and fade-out to {input_path}, saving to {output_path}...")
    subprocess.run(command, check=True)

    data.active_file_path = output_path

    return data
