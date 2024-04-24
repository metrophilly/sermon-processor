import json
import os
import subprocess
from datetime import datetime
import whisper
from moviepy.editor import AudioFileClip, concatenate_audioclips, AudioClip
from utils.helpers import (
    confirm_parameters,
    is_valid_time,
    is_valid_audio_file,
    SCRIPT_DIR,
    OUTPUT_BASE_DIR,
    confirmation_printout,
    parse_parameters,
    read_config_file,
)


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


def create_and_change_directory(upload_date):
    output_dir = os.path.join(OUTPUT_BASE_DIR, upload_date)
    os.makedirs(output_dir, exist_ok=True)
    return output_dir


def download_audio_from_youtube(youtube_url, start_time, end_time, output_dir):
    if not is_valid_time(start_time) or not is_valid_time(end_time):
        raise ValueError("Invalid time format")

    audio_filename = os.path.join(output_dir, "_01_downloaded_raw.mp3")

    postprocessor_args = []
    if start_time != "00:00:00":
        postprocessor_args.extend(["-ss", start_time])
    if end_time != "00:00:00":
        postprocessor_args.extend(["-to", end_time])

    command = [
        "yt-dlp",
        "--progress",
        "-x",
        "--audio-format",
        "mp3",
        "-o",
        audio_filename,
        youtube_url,
    ]

    if postprocessor_args:
        command.extend(["--postprocessor-args", " ".join(postprocessor_args)])

    subprocess.run(command, check=True)

    return audio_filename


def process_audio_file(audio_filename, output_dir):
    output_file_name = os.path.join(output_dir, "_02_trimmed_raw.mp3")

    intro_audio_path = os.path.join(SCRIPT_DIR, "extras", "intro.wav")
    outro_audio_path = os.path.join(SCRIPT_DIR, "extras", "outro.wav")

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


def apply_compression(input_file_name, upload_date, output_dir):
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


def transcribe_audio(audio_file_path, upload_date, output_dir):
    model = whisper.load_model("base")

    options = {
        "language": "en",
        "verbose": True,
    }

    # Transcribe the audio file with the specified language
    transcribed_text = model.transcribe(audio_file_path, **options)

    # Construct the output file path for only txt
    output_file_name = os.path.join(output_dir, f"{upload_date}_transcribed.txt")

    # Construct the output file path for segments
    segment_file_name = os.path.join(
        output_dir, f"{upload_date}_transcribed_segments.txt"
    )

    result = {
        "transcribed_text": transcribed_text,
        "output_file_name": output_file_name,
        "segment_file_name": segment_file_name,
    }

    # Write the transcribed text to the output file
    with open(result["output_file_name"], "w") as f:
        f.write(result["transcribed_text"]["text"])
    with open(result["segment_file_name"], "w") as f:
        for segment in result["transcribed_text"]["segments"]:
            f.write(json.dumps(segment) + "\n")

    return result


def main():
    
    # parse preset params
    config_file_path = 'config.txt'
    config = read_config_file(config_file_path)
    youtube_url, start_time, end_time = parse_parameters(config)

    confirm_parameters(youtube_url, start_time, end_time)

    try:
        upload_date = get_video_upload_date(youtube_url)
        output_dir = create_and_change_directory(upload_date)
        downloaded_audio_file = download_audio_from_youtube(youtube_url, start_time, end_time, output_dir)

        if not is_valid_audio_file(downloaded_audio_file):
            print(
                f"The file {downloaded_audio_file} was not created or is too small. Please check for errors."
            )
            exit(1)

        # audio processing and compressions
        processed_file_name = process_audio_file(downloaded_audio_file, output_dir)
        apply_compression(processed_file_name, upload_date, output_dir)
        # transcribe_audio(processed_file_name, upload_date, output_dir)

        # final printouts
        confirmation_printout(output_dir)

    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    main()
