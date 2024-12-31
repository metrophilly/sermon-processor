import os
from app.data_models.pipeline_data import PipelineData


def delete_files_step(data: PipelineData, file_keys=None):
    """
    Deletes files specified by the given keys in the pipeline data.

    Args:
        data (PipelineData): Current pipeline data object.
        file_keys (list[str]): List of attribute keys in PipelineData pointing to file paths or lists of file paths.

    Returns:
        PipelineData: Updated pipeline data object.
    """
    if not file_keys:
        raise ValueError("No file keys provided for deletion.")

    for key in file_keys:
        # Get the value from the data object
        file_or_files = getattr(data, key, None)
        if not file_or_files:
            print(f"Skipping deletion for '{key}': No file(s) found.")
            continue

        # Handle single file path or list of file paths
        if isinstance(file_or_files, str):  # Single file
            file_paths = [file_or_files]
        elif isinstance(file_or_files, list):  # List of files
            file_paths = file_or_files
        else:
            print(
                f"Invalid type for '{key}': {type(file_or_files)}. Skipping deletion."
            )
            continue

        # Delete each file
        for file_path in file_paths:
            if os.path.exists(file_path):
                print(f"Deleting file: {file_path}")
                os.remove(file_path)
            else:
                print(f"File not found, skipping: {file_path}")

    return data
