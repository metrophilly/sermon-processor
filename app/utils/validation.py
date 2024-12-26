import os
import subprocess


def validate_audio_file(file_path):
    """
    Checks if the file exists and is a valid audio file.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    command = ["ffprobe", "-v", "error", "-show_format", "-show_streams", file_path]
    try:
        subprocess.run(
            command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        print(f"Validation passed for: {file_path}")
    except subprocess.CalledProcessError as e:
        print(f"Validation failed for: {file_path} | Error: {e}")
        raise ValueError(f"Invalid or unsupported audio file: {file_path}")
