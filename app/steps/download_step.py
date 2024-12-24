from app.pipelines.base_pipeline import PipelineStep
from app.utils.paths import relative_path


class DownloadStep(PipelineStep):
    def __init__(
        self, downloader, url, filename, stream_id=None, date=None, data_key=None
    ):
        self.downloader = downloader
        self.url = url
        self.stream_id = stream_id
        self.filename = filename
        self.date = date
        self.data_key = data_key

    def process(self, data):
        path = self.downloader.download(
            url=self.url,
            date=self.date,
            stream_id=self.stream_id,
            filename=self.filename,
        )

        if self.data_key is not None:
            data[self.data_key] = relative_path(path)
        else:
            if "downloaded_files" not in data:
                data["downloaded_files"] = []
            data["downloaded_files"].append(path)

        return data
