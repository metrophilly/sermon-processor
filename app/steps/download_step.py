import os
from app.data_models.pipeline_data import PipelineData
from app.constants import PipelineKeys
from app.utils.paths import file_ext


def download_step(
    data: PipelineData, downloader, url, filename, key, date=None, stream_id=None
):
    path = downloader.download(url, date=date, stream_id=stream_id, filename=filename)
    if not path or not os.path.exists(path):
        raise FileNotFoundError(f"Downloaded file not found: {path}")

    setattr(data, key, path)
    setattr(data, PipelineKeys.ACTIVE_FILE_PATH, path)

    extension = file_ext(path)
    if not extension:
        raise ValueError(f"Invalid file extension detected: {path}")

    data.downloaded_files.append(path)
    return data
