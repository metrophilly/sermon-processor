import os
import subprocess
from datetime import datetime
from moviepy.editor import AudioFileClip, concatenate_audioclips, AudioClip


def get_video_upload_date(youtube_url):
    command = [
        "yt-dlp",
        "--skip-download",
        "--get-filename",
        "-o", "%(upload_date)s",
        youtube_url
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, check=True)
    upload_date = result.stdout.decode('utf-8').strip()
    return datetime.strptime(upload_date, '%Y%m%d').strftime("%Y-%m-%d")


def get_formatted_time(time_input):
    return time_input if time_input else "00:00:00"


def create_and_change_directory(upload_date):
    os.makedirs(upload_date, exist_ok=True)
    os.chdir(upload_date)


def download_audio_from_youtube(youtube_url, start_time, end_time, upload_date):
    audio_filename = f"downloaded_audio_{upload_date}.mp3"

    postprocessor_args = []
    if start_time != "00:00:00":
        postprocessor_args.extend(["-ss", start_time])
    if end_time != "00:00:00":
        postprocessor_args.extend(["-to", end_time])

    command = [
        "yt-dlp", "--progress", "-x", "--audio-format", "mp3",
        "-o", audio_filename, youtube_url
    ]

    if postprocessor_args:
        command.extend(["--postprocessor-args", " ".join(postprocessor_args)])

    subprocess.run(command, check=True)

    return audio_filename


def is_valid_audio_file(file_path):
    return os.path.exists(file_path) and os.path.getsize(file_path) > 1000


def process_audio_file(audio_filename, upload_date):
    output_file_name = f"{upload_date}_processed.mp3"

    trimmed_audio = AudioFileClip(audio_filename)
    intro_audio_path = '../extras/intro.wav'
    outro_audio_path = '../extras/outro.wav'

    intro_audio = AudioFileClip(intro_audio_path) if os.path.exists(
        intro_audio_path) else None
    outro_audio = AudioFileClip(outro_audio_path) if os.path.exists(
        outro_audio_path) else None
    silence_audio = AudioClip(lambda _: [0, 0], duration=1.5, fps=44100)

    audio_clips = [clip for clip in [intro_audio, silence_audio,
                                     trimmed_audio, silence_audio, outro_audio] if clip]
    final_audio = concatenate_audioclips(audio_clips)
    final_audio.write_audiofile(output_file_name, codec='libmp3lame')

    return output_file_name


def apply_default_compression(input_file_name, upload_date):
    compressed_file_name = f"{upload_date}_compressed.mp3"
    knee = 2.5  # in dB
    attack = 5  # in milliseconds
    release = 50  # in milliseconds
    makeup = 4  # in dB

    subprocess.run([
        'ffmpeg',
        '-i', input_file_name,
        '-filter_complex',
        f'acompressor=threshold=-32dB:ratio=2:knee={knee}:attack={attack}:release={release}:makeup={makeup}',
        '-y', compressed_file_name
    ], check=True)

    return compressed_file_name


def is_audacity_installed():
    try:
        result = subprocess.run(
            ["mdfind", "kMDItemCFBundleIdentifier == 'org.audacityteam.audacity'"], stdout=subprocess.PIPE)
        return bool(result.stdout.strip())
    except subprocess.CalledProcessError:
        return False


def main():
    try:
        # pre-checks
        if not is_audacity_installed():
            print("Audacity does not appear to be installed on this machine. Please install Audacity and try again.")
            exit(1)

        # user inputs
        youtube_url = input("Enter the YouTube URL: ")
        start_time = get_formatted_time(input(
            "Enter the start timestamp (HH:MM:SS/MM:SS/SS), or press Enter for full audio: "))
        end_time = get_formatted_time(input(
            "Enter the end timestamp (HH:MM:SS/MM:SS/SS), or press Enter for full audio: "))

        upload_date = get_video_upload_date(youtube_url)

        create_and_change_directory(upload_date)

        downloaded_audio_file = download_audio_from_youtube(
            youtube_url, start_time, end_time, upload_date)

        if not is_valid_audio_file(downloaded_audio_file):
            print(
                f"The file {downloaded_audio_file} was not created or is too small. Please check for errors.")
            exit(1)

        # audio processing and compressions
        processed_output_file = process_audio_file(
            downloaded_audio_file, upload_date)
        compressed_output_file = apply_default_compression(
            processed_output_file, upload_date)

        print(
            f"Your file has been processed and saved to {compressed_output_file}")

        # kick off final manual edits and helper text
        subprocess.run(["open", "-a", "Audacity",
                       compressed_output_file], check=True)

        helper_text_file = os.path.join(
            '..', 'extras', 'final_process_walkthrough.md')
        subprocess.run(['open', helper_text_file])

    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    main()
