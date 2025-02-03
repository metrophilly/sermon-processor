import os

from app.constants import PipelineKeys
from app.data_models.pipeline_data import PipelineData


def manual_load_step(data: PipelineData, manual_path: str):
    """
    Loads a manually downloaded file from disk.
    Expects that the file exists at `manual_path` and then sets the
    pipeline data keys to point to this file.
    """
    if os.path.exists(manual_path):
        print(f"Loaded manual file from {manual_path}")
        setattr(data, PipelineKeys.MAIN_FILE_PATH, manual_path)
        setattr(data, PipelineKeys.ACTIVE_FILE_PATH, manual_path)
        return data
    else:
        raise FileNotFoundError(f"Manual file not found at {manual_path}")
