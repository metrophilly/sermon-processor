import subprocess
from colorama import Fore, Style


def normalize_video(
    input_path,
    output_path,
    codec="libx264",
    resolution="1920x1080",
    frame_rate=30,
    audio_codec="aac",
    audio_sample_rate=44100,
    audio_channels=2,
    audio_bitrate="192k",
    ffmpeg_loglevel="info",
):
    """
    Normalize video file to consistent resolution, frame rate, and audio settings.

    Args:
        input_path (str): Path to input video file.
        output_path (str): Path for output video file.
        codec (str): Video codec to use (default: libx264).
        resolution (str): Target resolution for the output video (default: 1920x1080).
        frame_rate (int): Target frame rate for the output video (default: 30).
        audio_codec (str): Audio codec to use (default: aac).
        audio_sample_rate (int): Target audio sample rate (default: 44100 Hz).
        audio_channels (int): Number of audio channels (default: 2 for stereo).
        audio_bitrate (str): Target audio bitrate (default: 192k).
    """

    # Construct the ffmpeg command
    command = [
        "ffmpeg",
        "-loglevel",
        ffmpeg_loglevel,
        "-hide_banner",
        "-i",
        input_path,
        "-vf",
        f"scale={resolution},fps={frame_rate}",
        "-crf",
        "16",
        "-preset",
        "ultrafast",
        "-c:v",
        codec,
        "-c:a",
        audio_codec,
        "-ar",
        str(audio_sample_rate),
        "-ac",
        str(audio_channels),
        "-b:a",
        audio_bitrate,
        output_path,
    ]

    print(
        Fore.GREEN
        + f"Normalizing video file: {input_path} -> {output_path}"
        + Style.RESET_ALL
    )
    subprocess.run(command, check=True)
