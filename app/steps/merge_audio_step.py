import os
import subprocess
from app.constants import PipelineKeys
from app.data_models.pipeline_data import PipelineData
from app.utils.helpers import add_intermediate_filepath
from app.utils.normalize_audio import normalize_audio


def merge_audio_step(data: PipelineData, output_format="mp3"):
    """
    Merges intro, main, and outro audio files into a single output file.

    Args:
        data (PipelineData): The pipeline data object.
        output_format (str): The desired output format (default: "mp3").

    Returns:
        PipelineData: Updated data object with the merged audio path.
    """
    intro_path = os.path.abspath(data.intro_file_path)
    main_path = os.path.abspath(data.active_file_path)
    outro_path = os.path.abspath(data.outro_file_path)

    if not all([intro_path, main_path, outro_path]):
        raise ValueError("Missing one or more required audio file paths.")

    # Normalize all files to a consistent format (e.g., WAV)
    normalized_paths = []
    for path in [intro_path, main_path, outro_path]:
        base, ext = os.path.splitext(path)
        normalized_path = f"{base}_normalized.{output_format}"
        normalize_audio(
            str(path),
            str(normalized_path),
            codec="pcm_s16le",
            sample_rate=44100,
        )

        normalized_paths.append(normalized_path)

    # Create the file list for `ffmpeg`
    base, _ = os.path.splitext(main_path)
    file_list_path = f"{base}_file_list.txt"
    with open(file_list_path, "w") as f:
        for normalized_path in normalized_paths:
            f.write(f"file '{normalized_path}'\n")

    # Determine output file name dynamically
    output_file = f"{base}_merged.{output_format}"

    command = [
        "ffmpeg",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(file_list_path),
        "-c:a",
        "pcm_s16le" if output_format == "wav" else "libmp3lame",
        # These parameters should match normalization
        "-ar",
        "44100",
        "-ac",
        "2",
        "-b:a",
        "192k",
        output_file,
    ]

    # Run `ffmpeg` command
    print(f"Merging files into {output_file}...")
    subprocess.run(command, check=True)

    # Clean up temporary files
    if os.path.exists(file_list_path):
        os.remove(file_list_path)
    for path in normalized_paths:
        if os.path.exists(path):
            os.remove(path)

    # Update pipeline data with the merged file path
    data.active_file_path = output_file

    data = add_intermediate_filepath(data, output_file)

    return data
