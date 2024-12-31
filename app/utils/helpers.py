from app.constants import PipelineKeys
from app.data_models.pipeline_data import PipelineData


def add_intermediate_filepath(data: PipelineData, file_path: str):
    """
    Adds a file path to the `intermediate_files` attribute of the `PipelineData` object.

    Args:
        data (PipelineData): The pipeline data object.
        file_path (str): The file path to be added.

    Returns:
        PipelineData: Updated pipeline data object.
    """
    if not hasattr(data, PipelineKeys.INTERMEDIATE_FILES):
        # Initialize if it doesn't exist
        setattr(data, PipelineKeys.INTERMEDIATE_FILES, [])
    if file_path and file_path not in data.intermediate_files:
        data.intermediate_files.append(file_path)
        print(f"Added intermediate file: {file_path}")
    else:
        print(f"File already tracked or invalid: {file_path}")

    return data
