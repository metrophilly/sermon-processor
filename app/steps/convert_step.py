import os
import subprocess
from app.data_models.pipeline_data import PipelineData
from app.utils.validation import validate_audio_file


def convert_step(data: PipelineData, source_key, output_format="mp3", key=None):
    source_path = getattr(data, source_key, None)
    if not source_path or not os.path.exists(source_path):
        raise FileNotFoundError(
            f"Source file not found for {source_key}: {source_path}"
        )

    try:
        # Validate the source file
        validate_audio_file(source_path)
    except ValueError as e:
        print(f"Warning: {e}. Attempting forced conversion.")

    # Prepare output file path
    base, _ = os.path.splitext(source_path)
    output_path = f"{base}.{output_format}"

    if source_path.endswith(f".{output_format}"):
        print(f"File already in {output_format} format: {source_path}")
        if key:
            setattr(data, key, source_path)
        return data

    command = [
        "ffmpeg",
        "-i",
        source_path,
        "-c:a",
        "libmp3lame" if output_format == "mp3" else "copy",
        "-b:a",
        "192k",
        output_path,
    ]

    try:
        print(f"Converting {source_path} to {output_path}...")
        subprocess.run(command, check=True)
        print(f"Conversion successful: {output_path}")
    except subprocess.CalledProcessError:
        raise RuntimeError(f"Conversion failed for file: {source_path}")

    if key:
        setattr(data, key, output_path)
    else:
        setattr(data, source_key, output_path)

    return data
