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

        initial_path = self._get_cache_path(date, stream_id, filename)

        if os.path.exists(initial_path):
            print(f"Using cached file for {url}: {initial_path}")
            return initial_path

        print(f"Downloading {url} to cache...")
        final_path = self.real_downloader.download(url, initial_path)
        print(f"Downloaded and cached: {final_path}")
        return final_path
