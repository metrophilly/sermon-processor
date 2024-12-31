import requests
import os
from app.downloaders.base_downloader import Downloader


class S3Downloader(Downloader):

    def download(self, url, destination):
        """
        Download a file from an S3 URL.

        Args:
            url (str): S3 file URL (e.g., https://s3.amazonaws.com/bucket/intro.mp4).
            destination (str): Local file path to save the file.
        """
        os.makedirs(os.path.dirname(destination) or ".", exist_ok=True)
        print(f"Downloading S3 file from {url}...")
        response = requests.get(url, stream=True)
        response.raise_for_status()
        with open(destination, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"Downloaded S3 file to {destination}")
        return destination
