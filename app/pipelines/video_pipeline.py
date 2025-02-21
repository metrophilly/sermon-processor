from datetime import datetime
import os
from app.constants import PipelineKeys
from app.downloaders.youtube_downloader import YouTubeDownloader
from app.downloaders.s3_downloader import S3Downloader
from app.downloaders.downloader_proxy import DownloaderProxy
from app.steps.delete_files_step import delete_files_step
from app.steps.download_step import download_step
from app.steps.fade_in_out_step import fade_in_out_step
from app.steps.manual_load_step import manual_load_step
from app.steps.merge_video_step import merge_video_step
from app.steps.move_step import move_step
from app.steps.trim_step import trim_step
from app.utils.youtube import get_youtube_upload_date


def create_video_pipeline(config):
    """
    Builds the pipeline to process audio files using functional chaining.
    """
    stream_id = config.get("stream_id", "default-audio-stream")
    video_conf = config.get("video", {})
    IS_MANUAL_DOWNLOAD = config.get("manual_download", False)

    youtube_url = config.get("youtube_url")
    if youtube_url:
        date = get_youtube_upload_date(youtube_url)
        if not date:
            print("Failed to fetch upload date. Falling back to the current date.")
            date = datetime.now().strftime("%Y-%m-%d")
    else:
        date = datetime.now().strftime("%Y-%m-%d")

    # build proxies
    video_proxy = DownloaderProxy(
        real_downloader=YouTubeDownloader(quiet=True),
        cache_dir="cache/video",
    )
    s3_proxy = DownloaderProxy(real_downloader=S3Downloader(), cache_dir="cache/s3")

    # build pipeline steps
    steps = [
        (
            "Download intro video",
            lambda data: (
                download_step(
                    data,
                    downloader=s3_proxy,
                    url=video_conf.get("intro_url"),
                    filename="video_intro.mp4",
                    key=PipelineKeys.INTRO_FILE_PATH,
                )
                if video_conf.get("intro_url")
                else data
            ),
        ),
        (
            "Download outro video",
            lambda data: (
                download_step(
                    data,
                    downloader=s3_proxy,
                    url=video_conf.get("outro_url"),
                    filename="video_outro.mp4",
                    key=PipelineKeys.OUTRO_FILE_PATH,
                )
                if video_conf.get("outro_url")
                else data
            ),
        ),
    ]

    if IS_MANUAL_DOWNLOAD:
        manual_path = video_conf.get("manual_path")
        steps.append(
            (
                "Load manually downloaded audio",
                lambda data: manual_load_step(data, manual_path=manual_path),
            )
        )
    else:
        steps.append(
            (
                "Download YouTube video",
                lambda data: download_step(
                    data,
                    downloader=video_proxy,
                    url=config.get("youtube_url"),
                    filename="video.%(ext)s",
                    key=PipelineKeys.MAIN_FILE_PATH,
                    date=date,
                    stream_id=stream_id,
                ),
            ),
        )

    steps.extend(
        [
            (
                "Trim video",
                lambda data: (
                    trim_step(
                        data,
                        start_time=video_conf.get("trim", {}).get("start_time"),
                        end_time=video_conf.get("trim", {}).get("end_time"),
                        ffmpeg_loglevel="info",
                        ffmpeg_hide_banner=True,
                    )
                    if "trim" in video_conf
                    else data
                ),
            ),
            (
                "Apply fade-in/out",
                lambda data: fade_in_out_step(
                    data, fade_duration=1, ffmpeg_loglevel="info", is_video=True
                ),
            ),
            (
                "Merge clips",
                lambda data: merge_video_step(
                    data,
                    output_format="mp4",
                    ffmpeg_loglevel="info",
                    ffmpeg_hide_banner=True,
                ),
            ),
            (
                "Move final video to output dir",
                lambda data: move_step(
                    data,
                    source_key=PipelineKeys.ACTIVE_FILE_PATH,
                    output_filename=f"output/{stream_id}/{date}.mp4",
                ),
            ),
            (
                "Delete intermediate files",
                lambda data: delete_files_step(
                    data,
                    file_keys=[
                        PipelineKeys.INTERMEDIATE_FILES,
                    ],
                ),
            ),
        ]
    )

    return steps
