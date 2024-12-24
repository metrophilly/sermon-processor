from datetime import datetime

from app.pipelines.base_pipeline import Pipeline
from app.steps.video_download_step import VideoDownloadStep
from app.steps.download_step import DownloadStep

# If you have a VideoTrimStep, VideoMergeStep, etc., import them

from app.downloaders.youtube_video_downloader import YouTubeVideoDownloader
from app.downloaders.s3_downloader import S3Downloader
from app.downloaders.downloader_proxy import DownloaderProxy


def create_video_pipeline(config):
    """
    Creates a pipeline to process the video portion of a sermon:
    1) Download video+audio from YouTube URL.
    2) Download a video intro and outro from S3.
    3) Trim or merge if needed.

    Example config:
    {
      "youtube_url": "...",
      "stream_id": "...",
      "video": {
        "intro_url": "...",
        "outro_url": "...",
        "trim": {
          "start_time": "00:01:00",
          "end_time": "00:10:00"
        }
      }
    }
    """
    pipeline = Pipeline()
    date = datetime.now().strftime("%Y-%m-%d")
    stream_id = config.get("stream_id", "default-stream")

    # Build specialized proxies
    video_proxy = DownloaderProxy(
        real_downloader=YouTubeVideoDownloader(),
        cache_dir="cache/video",  # separate cache for video+audio
    )
    s3_proxy = DownloaderProxy(real_downloader=S3Downloader(), cache_dir="cache/s3")

    # Required: The main YouTube URL
    youtube_url = config["youtube_url"]

    # 1) Download Video+Audio
    pipeline.add_step(
        VideoDownloadStep(
            video_downloader=video_proxy,
            url=youtube_url,
            date=date,
            stream_id=f"{stream_id}-video",
            filename="video.mp4",
        )
    )

    # 2) Download Intro/Outro
    video_conf = config.get("video", {})
    video_intro = video_conf.get("intro_url")
    video_outro = video_conf.get("outro_url")

    if video_intro:
        pipeline.add_step(
            DownloadStep(
                downloader=s3_proxy,
                url=video_intro,
                date=date,
                stream_id=f"{stream_id}-video",
                filename="video_intro.mp4",
            )
        )

    if video_outro:
        pipeline.add_step(
            DownloadStep(
                downloader=s3_proxy,
                url=video_outro,
                date=date,
                stream_id=f"{stream_id}-video",
                filename="video_outro.mp4",
            )
        )

    # 3) Optional Trim, Merge, etc.
    # if "trim" in video_conf:
    #     pipeline.add_step(TrimStep(
    #         start_time=video_conf["trim"]["start_time"],
    #         end_time=video_conf["trim"]["end_time"]
    #     ))
    # if you have a step to merge intro/outro for video, add it here.

    return pipeline
