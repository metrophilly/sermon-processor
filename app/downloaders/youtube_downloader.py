import os
from yt_dlp import YoutubeDL
from app.downloaders.base_downloader import Downloader


class YouTubeDownloader(Downloader):
    def __init__(self, audio_only=False, quiet=False):
        self.audio_only = audio_only
        self.quiet = quiet

    def download(self, url, destination):
        """
        Download a file from a YouTube URL.

        Args:
            url (str): YouTube URL
            destination (str): Local file path to save the file.
        """
        output_dir = os.path.dirname(destination) or "."
        output_filename = os.path.basename(destination)
        os.makedirs(output_dir, exist_ok=True)

        format_str = "bestaudio/best" if self.audio_only else "bestvideo+bestaudio/best"
        ydl_opts = {
            "format": format_str,
            "outtmpl": os.path.join(output_dir, output_filename),
            "quiet": self.quiet,
        }

        if self.audio_only:
            ydl_opts["postprocessors"] = [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                    "nopostoverwrites": False,
                }
            ]

        with YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            final_path = ydl.prepare_filename(info_dict)

            downloads = info_dict.get("requested_downloads")
            if downloads and len(downloads) > 0:
                real_final_path = downloads[0].get("filepath")
                if real_final_path:
                    final_path = real_final_path

        print(f"Downloaded to {final_path}")
        return final_path
