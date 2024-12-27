import os
import shutil
from app.data_models.pipeline_data import PipelineData


def move_step(data: PipelineData, source_key=None, output_filename=None):
    """
    Moves the file from the source to the final output directory.

    Args:
        data (PipelineData): Current pipeline data object.
        source_key (str): Optional key in `PipelineData` where the source file path is stored.
        output_filename (str): Final file name and path for the destination.

    Returns:
        PipelineData: Updated data object with the final output path.
    """
    source_path = getattr(data, source_key) if source_key else data.active_file_path

    if not source_path or not os.path.exists(source_path):
        raise ValueError(f"Source file does not exist: {source_path}")

    # Ensure output directory exists
    if not output_filename:
        raise ValueError("Output filename must be specified.")
    output_dir = os.path.dirname(output_filename)
    os.makedirs(output_dir, exist_ok=True)

    # Construct the full destination path
    destination_path = os.path.join(output_dir, os.path.basename(output_filename))

    # Move the file
    print(f"Moving file from {source_path} to {destination_path}...")
    shutil.move(source_path, destination_path)

    # Update the data object with the final path
    data.final_output_path = destination_path

    return data
