import os
import subprocess
from datetime import datetime
from moviepy.editor import AudioFileClip, concatenate_audioclips, AudioClip
from pydub import AudioSegment


def format_time(time_str):
    return time_str if time_str else "00:00:00"


youtube_url = input("Enter the YouTube URL: ")
start_time_input = input(
    "Enter the start timestamp (HH:MM:SS or MM:SS or SS), or press Enter to use the full audio: ")
end_time_input = input(
    "Enter the end timestamp (HH:MM:SS or MM:SS or SS), or press Enter to use the full audio: ")

start_time_formatted = format_time(start_time_input)
end_time_formatted = format_time(end_time_input)

current_datetime = datetime.now().strftime("%Y%m%d_%H%M%S")
output_template = f"downloaded_audio_{current_datetime}.%(ext)s"

# Ensure the postprocessor arguments are correctly formatted
postprocessor_args = f"-ss {start_time_formatted} -to {end_time_formatted}" if start_time_input or end_time_input else ""

try:
    os.makedirs(datetime.now().strftime("%Y-%m-%d"), exist_ok=True)
    os.chdir(datetime.now().strftime("%Y-%m-%d"))
except Exception as e:
    print(f"Error in directory handling: {e}")
    exit(1)

subprocess.run([
    "yt-dlp",
    "--progress",
    "-x",
    "--audio-format", "mp3",
    "-o", output_template,
    "--postprocessor-args", postprocessor_args,
    youtube_url
], check=True)

downloaded_audio_filename = f"downloaded_audio_{current_datetime}.mp3"

# Checking for file existence and reasonable size
if not os.path.exists(downloaded_audio_filename) or os.path.getsize(downloaded_audio_filename) < 1000:
    print(f"The file {downloaded_audio_filename} was not created or is too small. Please check for errors in the yt-dlp command.")
    exit(1)

# Proceed with moviepy processing only if the audio file is valid
try:
    trimmed_clip = AudioFileClip(downloaded_audio_filename)

    # Assuming prepend_audio_path and append_audio_path are defined earlier in your script
    prepend_audio_path = '../extras/intro.wav'
    append_audio_path = '../extras/outro.wav'

    prepend_clip = AudioFileClip(prepend_audio_path) if os.path.exists(
        prepend_audio_path) else None
    append_clip = AudioFileClip(append_audio_path) if os.path.exists(
        append_audio_path) else None
    silent_clip = AudioClip(lambda _: [0, 0], duration=1.5, fps=44100)

    clips_to_concatenate = [prepend_clip, silent_clip, trimmed_clip, silent_clip,
                            append_clip] if prepend_clip and append_clip else [trimmed_clip]

    final_clip = concatenate_audioclips(clips_to_concatenate)
    output_file_path = f"{datetime.now().strftime('%Y-%m-%d')}_final.mp3"
    final_clip.write_audiofile(output_file_path, codec='libmp3lame')

    print(f"Your file has been processed and saved to {output_file_path}")

except Exception as e:
    print(f"An error occurred during audio processing: {e}")
    exit(1)
