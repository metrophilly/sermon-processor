import subprocess
import os
import json
import sys
from typing import TypedDict, Optional

from utils.helpers import download_video, parse_video_parameters, read_config_file


def run_command(command, capture_output=False):
    """Run a command and optionally capture its output."""
    print(f"Executing command: {' '.join(command)}")
    process = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )

    output = ""
    while True:
        line = process.stdout.readline()
        if line == "" and process.poll() is not None:
            break
        if line:
            print(line.strip())
            if capture_output:
                output += line

    exit_code = process.poll()
    if exit_code != 0:
        raise Exception(
            f"Command {' '.join(command)} failed with exit code {exit_code}"
        )
    print("Command executed successfully.")
    return output if capture_output else None


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


def ensure_dir_exists(path: str):
    directory = os.path.join(".", path)
    os.makedirs(directory, exist_ok=True)
    return directory



def ensure_file_exists(filename):
    if not os.path.exists(filename):
        print(f"Error: The file '{filename}' does not exist.")
        sys.exit(1)
    else:
        print(f"The file '{filename}' exists.")


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


def get_video_duration(video_path):
    video_info = get_video_info(video_path)
    return float(video_info["format"]["duration"])


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
            "-b:a",
            audio_bitrate,
            "-r",
            str(frame_rate),  # Explicitly set the frame rate for the output
            output_path,
        ]
    )


def apply_compression(input_path, output_path):
    compressor_threshold = -28  # in dB
    ratio = 2
    knee = 2.5  # in dB
    attack = 5  # in ms
    release = 50  # in ms
    makeup = 2  # in dB

    filter_complex = f"[0:a]loudnorm,acompressor=threshold={compressor_threshold}dB:ratio={ratio}:knee={knee}:attack={attack}:release={release}:makeup={makeup}[a]"

    subprocess.run(
        [
            "ffmpeg",
            "-i",
            input_path,
            "-filter_complex",
            filter_complex,
            "-map",
            "0:v",
            "-map",
            "[a]",
            "-c:v",
            "copy",
            "-y",
            output_path,
        ],
        check=True,
    )

    return output_path


class VideoPaths(TypedDict):
    raw: str
    compressed: str
    crossfaded: Optional[str]


class PathsDict(TypedDict, total=False):
    intro: VideoPaths
    base: VideoPaths
    outro: VideoPaths


def main() -> None:
    ensure_dir_exists("tmp")
    ensure_dir_exists("output")
    ensure_file_exists("config/base.mp4")

    # parse preset params
    config_file_path = 'config/config.txt'
    config = read_config_file(config_file_path)
    intro_url, outro_url = parse_video_parameters(config)

    download_video(intro_url, './tmp/intro.mp4')
    download_video(outro_url, './tmp/outro.mp4')

    paths: PathsDict = {
        "intro": {
            "raw": "./tmp/intro.mp4",
            "compressed": "./tmp/01-intro_compressed.mp4",
            "crossfaded": "./tmp/04-intro-base_crossfaded.mp4",
        },
        "base": {
            "raw": "./config/base.mp4",
            "compressed": "./tmp/02-base_compressed.mp4",
            "crossfaded": "./tmp/05-base-output_crossfaded.mp4",
        },
        "outro": {
            "raw": "./tmp/outro.mp4",
            "compressed": "./tmp/03-outro_compressed.mp4",
        },
    }

    final_path: str = "./data/FINAL_full-compressed.mp4"

    # apply "standard loudness" to all clips individually
    for key in paths.keys():
        apply_compression(paths[key]["raw"], paths[key]["compressed"])

    base_settings = get_video_settings(paths["base"]["compressed"])

    # crossfade the intro to base
    crossfade_videos(
        paths["intro"]["compressed"],
        paths["base"]["compressed"],
        1,
        paths["intro"]["crossfaded"],
        base_settings,
    )

    # crossfade the intro/base result to outro
    crossfade_videos(
        paths["intro"]["crossfaded"],
        paths["outro"]["compressed"],
        1,
        final_path,
        base_settings,
    )

    print("Video processing complete.")


if __name__ == "__main__":
    main()
