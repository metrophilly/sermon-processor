import os


class DownloaderProxy:
    def __init__(self, real_downloader, cache_dir="cache"):
        self.real_downloader = real_downloader
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)

    def _get_cache_path(self, date, stream_id, filename):

        if stream_id is None:
            sub_dir = self.cache_dir
        else:
            if date is None:
                sub_dir = os.path.join(self.cache_dir, stream_id)
            else:
                sub_dir = os.path.join(self.cache_dir, date, stream_id)

        os.makedirs(sub_dir, exist_ok=True)
        return os.path.join(sub_dir, filename)

    def download(self, url, date, stream_id, filename):
        cache_path = self._get_cache_path(date, stream_id, filename)

        # If the downloader has a `get_output_path` method, use it to predict the output path
        if hasattr(self.real_downloader, "get_output_path"):
            expected_path = self.real_downloader.get_output_path(url, cache_path)
        else:
            # Fallback to the base cache path if `get_output_path` is not available
            expected_path = cache_path

        # If the file already exists, just use that filepath...
        if os.path.exists(expected_path):
            print(f"Using cached file for {url}: {expected_path}")
            return expected_path

        # ...but if it doesn't, then actually download the file
        print(f"Downloading {url} to cache...")
        downloaded_path = self.real_downloader.download(url, cache_path)
        print(f"Downloaded and cached: {downloaded_path}")
        return downloaded_path
