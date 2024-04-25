from datetime import datetime
import json
import subprocess
import requests
import os
from moviepy.editor import AudioFileClip, concatenate_audioclips, AudioClip
from typing import Literal

from utils.file import ensure_dir_exists
from utils.helpers import run_command
from utils.time import is_valid_time
from utils.constants import SCRIPT_DIR


def ensure_audio(video_path, base_settings):
    # Ensure tmp directory exists and get its path
    tmp_dir = ensure_dir_exists("tmp")

    # Construct path for the silent audio file within the tmp directory
    silent_audio_path = os.path.join(tmp_dir, "silent_audio.aac")

    # Generate silent audio with settings from base_settings
    run_command(
        [
            "ffmpeg",
            "-y",
            "-v",
            "verbose",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r="
            + base_settings["sample_rate"]
            + ":cl=stereo",  # Use sample rate from base_settings
            "-t",
            str(get_video_duration(video_path)),
            "-c:a",
            base_settings["acodec"],  # Use audio codec from base_settings
            "-b:a",
            base_settings["abitrate"],  # Use audio bitrate from base_settings
            silent_audio_path,
        ]
    )

    # Generate new video path with audio in the tmp directory
    tmp_video_path = os.path.join(
        tmp_dir, f"{os.path.basename(video_path).split('.')[0]}_with_audio.mp4"
    )

    # Combine video with the generated silent audio file
    run_command(
        [
            "ffmpeg",
            "-y",
            "-v",
            "verbose",
            "-i",
            video_path,
            "-i",
            silent_audio_path,
            "-c:v",
            "copy",  # Keep video codec as is
            "-c:a",
            base_settings[
                "acodec"
            ],  # Use audio codec from base_settings for consistency
            "-ar",
            base_settings[
                "sample_rate"
            ],  # Ensure sample rate is consistent with base_settings
            # "-shortest",  # Ensure output duration matches the shortest of video or audio streams
            tmp_video_path,
        ]
    )

    # Clean up by removing the silent audio file after use
    os.remove(silent_audio_path)
    return tmp_video_path


def download_media_from_youtube(
    youtube_url: str,
    start_time: str,
    end_time: str,
    upload_date: str,
    media_type: Literal["audio", "video"] = "audio",
) -> str:
    if not is_valid_time(start_time) or not is_valid_time(end_time):
        raise ValueError("Invalid time format")

    # Define filename based on media type
    media_filename = os.path.join(
        "tmp",
        f"{upload_date}_base_downloaded_raw.{'mp3' if media_type == 'audio' else 'mp4'}",
    )

    # Configuring command for different media types
    if media_type == "audio":
        command = [
            "yt-dlp",
            "--progress",
            "-x",
            "--audio-format",
            "mp3",
            "-o",
            media_filename,
            youtube_url,
        ]
    elif media_type == "video":
        command = [
            "yt-dlp",
            "--progress",
            "--format",
            "bestvideo+bestaudio",
            "--merge-output-format",
            "mp4",
            "-o",
            media_filename,
            youtube_url,
        ]
    else:
        raise ValueError("Invalid media type specified")

    # Apply trimming if necessary
    if start_time != "00:00:00" or end_time != "00:00:00":
        command.extend(
            ["--postprocessor-args", f"ffmpeg:-ss {start_time} -to {end_time}"]
        )

    # Execute download command
    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error downloading media: {e}")
        raise

    return media_filename


def process_audio_file(audio_filename):
    output_file_name = os.path.join("tmp", "_02_trimmed_raw.mp3")

    intro_audio_path = os.path.join(SCRIPT_DIR, "extras", "audio", "intro.wav")
    outro_audio_path = os.path.join(SCRIPT_DIR, "extras", "audio", "outro.wav")

    trimmed_audio = AudioFileClip(audio_filename)

    intro_audio = (
        AudioFileClip(intro_audio_path) if os.path.exists(intro_audio_path) else None
    )
    outro_audio = (
        AudioFileClip(outro_audio_path) if os.path.exists(outro_audio_path) else None
    )
    silence_audio = AudioClip(lambda _: [0, 0], duration=1.5, fps=44100)

    audio_clips = [
        clip
        for clip in [
            intro_audio,
            silence_audio,
            trimmed_audio,
            silence_audio,
            outro_audio,
        ]
        if clip
    ]
    final_audio = concatenate_audioclips(audio_clips)
    final_audio.write_audiofile(output_file_name, codec="libmp3lame")

    return output_file_name


def get_video_settings(video_path):
    video_info = get_video_info(video_path)
    audio_stream = next(
        (stream for stream in video_info["streams"] if stream["codec_type"] == "audio"),
        None,
    )
    video_stream = next(
        (stream for stream in video_info["streams"] if stream["codec_type"] == "video"),
        None,
    )
    frame_rate = (
        eval(video_stream["r_frame_rate"]) if "r_frame_rate" in video_stream else 30
    )

    return {
        "frame_rate": frame_rate,
        "acodec": audio_stream["codec_name"] if audio_stream else "aac",
        "sample_rate": audio_stream["sample_rate"] if audio_stream else "48000",
        "abitrate": "128k",
    }


def get_video_upload_date(youtube_url):
    command = [
        "yt-dlp",
        "--skip-download",
        "--get-filename",
        "-o",
        "%(upload_date)s",
        youtube_url,
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, check=True)
    upload_date = result.stdout.decode("utf-8").strip()
    return datetime.strptime(upload_date, "%Y%m%d").strftime("%Y-%m-%d")


def extract_segments_for_crossfade(video_path, segment_duration):
    """Extracts the first and last segments of the video for crossfading."""
    tmp_dir = ensure_dir_exists("tmp")

    video_duration = get_video_duration(video_path)
    start_segment = os.path.join(
        tmp_dir, f"{os.path.splitext(os.path.basename(video_path))[0]}_start.mp4"
    )
    end_segment = os.path.join(
        tmp_dir, f"{os.path.splitext(os.path.basename(video_path))[0]}_end.mp4"
    )

    # Extract the first segment
    run_command(
        [
            "ffmpeg",
            "-y",
            "-v",
            "verbose",
            "-i",
            video_path,
            "-ss",
            "0",
            "-t",
            str(segment_duration),
            "-c",
            "copy",
            start_segment,
        ]
    )
    # Extract the last segment
    run_command(
        [
            "ffmpeg",
            "-y",
            "-v",
            "verbose",
            "-i",
            video_path,
            "-ss",
            str(video_duration - segment_duration),
            "-t",
            str(segment_duration),
            "-c",
            "copy",
            end_segment,
        ]
    )
    return start_segment, end_segment


def get_video_duration(video_path):
    video_info = get_video_info(video_path)
    return float(video_info["format"]["duration"])


def get_video_info(video_path):
    """Get video information using ffprobe."""
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        video_path,
    ]
    output = run_command(cmd, capture_output=True)
    if not output:
        raise ValueError(
            f"No output returned from ffprobe for video path: {video_path}"
        )
    return json.loads(output)  # Directly parse the output from `run_command`.


def crossfade_videos(
    video1_path, video2_path, crossfade_duration, output_path, base_settings
):
    frame_rate = base_settings["frame_rate"]
    audio_codec = base_settings["acodec"]
    audio_bitrate = base_settings["abitrate"]
    offset = get_video_duration(video1_path) - crossfade_duration
    filter_complex = f"[0:v]scale=1920:1080,fps=fps={frame_rate},format=yuv420p[v0];[1:v]scale=1920:1080,fps=fps={frame_rate},format=yuv420p[v1];[v0][v1]xfade=transition=fade:duration={crossfade_duration}:offset={offset}[v];[0:a][1:a]acrossfade=d={crossfade_duration}[a]"
    run_command(
        [
            "ffmpeg",
            "-y",
            "-v",
            "verbose",
            "-i",
            video1_path,
            "-i",
            video2_path,
            "-filter_complex",
            filter_complex,
            "-map",
            "[v]",
            "-map",
            "[a]",
            "-c:a",
            audio_codec,
            "-ar",
            "44100",  # Ensure consistent audio sample rate
            "-b:a",
            audio_bitrate,
            "-r",
            str(frame_rate),
            output_path,
        ]
    )


def trim_base_video(video_path, segment_duration, base_settings):
    tmp_dir = ensure_dir_exists("tmp")

    trimmed_video_path = os.path.join(
        tmp_dir, f"{os.path.splitext(os.path.basename(video_path))[0]}_trimmed.mp4"
    )
    video_duration = get_video_duration(video_path)

    run_command(
        [
            "ffmpeg",
            "-y",
            "-v",
            "verbose",
            "-ss",
            str(segment_duration),
            "-i",
            video_path,
            "-to",
            str(
                video_duration - segment_duration * 2
            ),  # Adjusted to account for duration after initial skip
            "-c:v",
            "libx264",
            "-c:a",
            "aac",  # Example re-encode to ensure accuracy
            "-preset",
            "fast",  # Optional: Adjust encoding speed/quality
            "-r",
            str(base_settings["frame_rate"]),
            trimmed_video_path,
        ]
    )

    return trimmed_video_path


def apply_video_compression(input_path, output_path):
    compressor_threshold = -28  # in dB
    ratio = 2
    knee = 2.5  # in dB
    attack = 5  # in ms
    release = 50  # in ms
    makeup = 2  # in dB

    # filter_complex = f"[0:a]loudnorm,acompressor=threshold={compressor_threshold}dB:ratio={ratio}:knee={knee}:attack={attack}:release={release}:makeup={makeup}[a]"

    video_bitrate = "5000k"  # Example bitrate
    audio_sample_rate = 48000  # in Hz
    frame_rate = 30  # Example frame rate
    resolution = "1920x1080"  # Example resolution

    filter_complex = f"[0:v]fps=fps={frame_rate},scale={resolution},format=yuv420p[v];[0:a]loudnorm,acompressor=threshold={compressor_threshold}dB:ratio={ratio}:knee={knee}:attack={attack}:release={release}:makeup={makeup}[a]"

    subprocess.run(
        [
            "ffmpeg",
            "-i",
            input_path,
            "-filter_complex",
            filter_complex,
            "-map",
            "[v]",
            "-map",
            "[a]",
            "-c:v",
            "libx264",
            "-b:v",
            video_bitrate,
            "-r",
            str(frame_rate),
            "-ar",
            str(audio_sample_rate),
            "-y",
            output_path,
        ],
        check=True,
    )

    return output_path


def apply_audio_compression(input_file_name, upload_date, output_dir):
    output_file_name = os.path.join(output_dir, f"{upload_date}_ready_to_scrub.mp3")
    knee = 2.5  # in dB
    attack = 5  # in milliseconds
    release = 50  # in milliseconds
    makeup = 4  # in dB

    subprocess.run(
        [
            "ffmpeg",
            "-i",
            input_file_name,
            "-filter_complex",
            f"acompressor=threshold=-32dB:ratio=2:knee={knee}:attack={attack}:release={release}:makeup={makeup}",
            "-y",
            output_file_name,
        ],
        check=True,
    )

    return output_file_name


def download_video(s3_url, local_path):
    # Ensure the local directory exists
    os.makedirs(os.path.dirname(local_path), exist_ok=True)

    # Send a GET request to the S3 URL
    response = requests.get(s3_url, stream=True)
    response.raise_for_status()  # Raises stored HTTPError, if one occurred

    # Stream the video content into the local file
    with open(local_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:  # filter out keep-alive new chunks
                f.write(chunk)

    print(f"Video downloaded successfully to {local_path}")


def check_and_download(video_url, file_path):
    if not os.path.exists(file_path):
        download_video(video_url, file_path)
    else:
        print(f"File {file_path} already exists. Skipping download.")
