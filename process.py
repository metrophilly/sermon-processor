import os
import subprocess
from datetime import datetime
from moviepy.editor import AudioFileClip, concatenate_audioclips, AudioClip


def get_formatted_time(time_input):
    """Formats the time input to HH:MM:SS format or defaults to zero."""
    return time_input if time_input else "00:00:00"


def create_and_change_directory():
    """Creates a new directory based on the current date and changes the working directory to it."""
    date_directory = datetime.now().strftime("%Y-%m-%d")
    os.makedirs(date_directory, exist_ok=True)
    os.chdir(date_directory)


def download_audio_from_youtube(youtube_url, start_time, end_time):
    """Downloads audio from a YouTube URL with optional start and end timestamps."""
    download_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    audio_filename = f"downloaded_audio_{download_time}.mp3"

    postprocessor_args = f"-ss {start_time} -to {end_time}" if start_time or end_time else ""
    subprocess.run([
        "yt-dlp", "--progress", "-x", "--audio-format", "mp3",
        "-o", f"downloaded_audio_{download_time}.%(ext)s",
        "--postprocessor-args", postprocessor_args,
        youtube_url
    ], check=True)

    return audio_filename


def is_valid_audio_file(file_path):
    """Checks if the audio file exists and has a reasonable size."""
    return os.path.exists(file_path) and os.path.getsize(file_path) > 1000


def process_audio_file(audio_filename):
    """Processes the audio file by trimming, and adding intro, outro, and silence."""
    output_file_name = f"{datetime.now().strftime('%Y-%m-%d')}_final.mp3"

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


def main():
    try:
        youtube_url = input("Enter the YouTube URL: ")
        start_time = get_formatted_time(input(
            "Enter the start timestamp (HH:MM:SS/MM:SS/SS), or press Enter for full audio: "))
        end_time = get_formatted_time(input(
            "Enter the end timestamp (HH:MM:SS/MM:SS/SS), or press Enter for full audio: "))
        create_and_change_directory()

        downloaded_audio_file = download_audio_from_youtube(
            youtube_url, start_time, end_time)

        if not is_valid_audio_file(downloaded_audio_file):
            print(
                f"The file {downloaded_audio_file} was not created or is too small. Please check for errors.")
            exit(1)

        try:
            final_output_file = process_audio_file(downloaded_audio_file)
            print(
                f"Your file has been processed and saved to {final_output_file}")
        except Exception as error:
            print(f"An error occurred during audio processing: {error}")
            exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    main()
