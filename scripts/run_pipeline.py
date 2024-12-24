from app.pipelines.base_pipeline import Pipeline
from app.steps.download_step import DownloadStep
from app.downloaders.youtube_downloader import YouTubeDownloader
from app.downloaders.s3_downloader import S3Downloader
from app.downloaders.downloader_proxy import DownloaderProxy
from datetime import datetime

from scripts.config_loader import load_and_validate_config

def create_pipeline(config):
    """
    Create a pipeline based on the provided configuration.

    Args:
        config: Dictionary with configuration details.

    Returns:
        A fully constructed pipeline.
    """
    pipeline = Pipeline()

    # Initialize downloaders & proxies
    youtube_downloader = YouTubeDownloader()
    youtube_proxy = DownloaderProxy(youtube_downloader, cache_dir="cache/youtube")

    s3_downloader = S3Downloader()
    s3_proxy = DownloaderProxy(s3_downloader, cache_dir="cache/s3")

    # Add download steps
    for stream in config["streams"]:
        stream_id = stream.get("custom_name", "default-id")
        date = datetime.now().strftime("%Y-%m-%d")

        # Add YouTube download step
        pipeline.add_step(DownloadStep(
            downloader=youtube_proxy,
            url=stream["youtube_url"],
            date=date,
            stream_id=stream_id,
            filename="video.mp4"
        ))

        # Add intro and outro download steps if applicable
        if stream.get("intro_url"):
            pipeline.add_step(DownloadStep(
                downloader=s3_proxy,
                url=stream["intro_url"],
                date=date,
                stream_id=stream_id,
                filename="intro.mp4"
            ))

        if stream.get("outro_url"):
            pipeline.add_step(DownloadStep(
                downloader=s3_proxy,
                url=stream["outro_url"],
                date=date,
                stream_id=stream_id,
                filename="outro.mp4"
            ))

    return pipeline

if __name__ == "__main__":
    config = load_and_validate_config("../config/main_config.json")

    pipeline = create_pipeline(config)
    result = pipeline.execute({"downloaded_files": []})
    print(f"Pipeline Result: {result}")