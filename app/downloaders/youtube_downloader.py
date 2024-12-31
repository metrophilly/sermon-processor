import os
from yt_dlp import YoutubeDL
from app.downloaders.base_downloader import Downloader


class YouTubeDownloader(Downloader):
    def __init__(self, audio_only=False, quiet=False):
        self.audio_only = audio_only
        self.quiet = quiet

    def get_output_path(self, url, destination):
        """
        Simulates the final output path based on yt-dlp's output template.

        Args:
            url (str): The URL of the YouTube video.
            destination (str): The desired output directory or file name.

        Returns:
            str: The calculated output file path.
        """
        format_str = "bestaudio/best" if self.audio_only else "bestvideo+bestaudio/best"
        ydl_opts = {
            "format": format_str,
            "outtmpl": destination,
            "quiet": self.quiet,
            "simulate": True,  # Prevent actual downloading
        }

        with YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            resolved_path = ydl.prepare_filename(info_dict)
            return resolved_path

    def download(self, url, destination):
        """
        Downloads a YouTube video or audio.

        Args:
            url (str): The URL of the YouTube video.
            destination (str): The desired output directory or file name.

        Returns:
            str: The path to the downloaded file.
        """
        format_str = "bestaudio/best" if self.audio_only else "bestvideo+bestaudio/best"
        ydl_opts = {
            "format": format_str,
            "outtmpl": destination,
            "quiet": self.quiet,
        }

        with YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url)
            resolved_path = ydl.prepare_filename(info_dict)  # Get resolved output path
            print(f"Downloaded file: {resolved_path}")
            return resolved_path
