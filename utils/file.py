import os
import sys
from utils.constants import OUTPUT_BASE_DIR


def is_valid_audio_file(file_path):
    return os.path.exists(file_path) and os.path.getsize(file_path) > 1000

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


def create_and_change_directory(upload_date):
    output_dir = os.path.join(OUTPUT_BASE_DIR, upload_date)
    os.makedirs(output_dir, exist_ok=True)
    return output_dir