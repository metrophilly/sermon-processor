from datetime import datetime
from app.constants import PipelineKeys
from app.downloaders.youtube_downloader import YouTubeDownloader
from app.downloaders.s3_downloader import S3Downloader
from app.downloaders.downloader_proxy import DownloaderProxy
from app.steps.delete_files_step import delete_files_step
from app.steps.download_step import download_step
from app.steps.fade_in_out_step import fade_in_out_step
from app.steps.trim_step import trim_step
from app.steps.merge_audio_step import merge_audio_step
from app.steps.move_step import move_step
from app.utils.youtube import get_youtube_upload_date


def create_audio_pipeline(config):
    """
    Builds the pipeline to process audio files using functional chaining.
    """
    stream_id = config.get("stream_id", "default-audio-stream")
    audio_conf = config.get("audio", {})

    youtube_url = config.get("youtube_url")
    if youtube_url:
        date = get_youtube_upload_date(youtube_url)
        if not date:
            print("Failed to fetch upload date. Falling back to the current date.")
            date = datetime.now().strftime("%Y-%m-%d")
    else:
        date = datetime.now().strftime("%Y-%m-%d")

    # build proxies
    audio_proxy = DownloaderProxy(
        real_downloader=YouTubeDownloader(audio_only=True),
        cache_dir="cache/audio",
    )
    s3_proxy = DownloaderProxy(real_downloader=S3Downloader(), cache_dir="cache/s3")

    # build pipeline steps
    steps = [
        (
            "Download intro audio",
            lambda data: (
                download_step(
                    data,
                    downloader=s3_proxy,
                    url=audio_conf.get("intro_url"),
                    filename="audio_intro.wav",
                    key=PipelineKeys.INTRO_FILE_PATH,
                )
                if audio_conf.get("intro_url")
                else data
            ),
        ),
        (
            "Download outro audio",
            lambda data: (
                download_step(
                    data,
                    downloader=s3_proxy,
                    url=audio_conf.get("outro_url"),
                    filename="audio_outro.wav",
                    key=PipelineKeys.OUTRO_FILE_PATH,
                )
                if audio_conf.get("outro_url")
                else data
            ),
        ),
        (
            "Download YouTube audio",
            lambda data: download_step(
                data,
                downloader=audio_proxy,
                url=config.get("youtube_url"),
                filename="audio.%(ext)s",
                key=PipelineKeys.MAIN_FILE_PATH,
                date=date,
                stream_id=stream_id,
            ),
        ),
        (
            "Trim audio",
            lambda data: (
                trim_step(
                    data,
                    start_time=audio_conf.get("trim", {}).get("start_time"),
                    end_time=audio_conf.get("trim", {}).get("end_time"),
                    ffmpeg_hide_banner=True,
                )
                if "trim" in audio_conf
                else data
            ),
        ),
        (
            "Apply fade-in/out",
            lambda data: fade_in_out_step(
                data, fade_duration=1, ffmpeg_loglevel="info", is_video=False
            ),
        ),
        (
            "Merge audio",
            lambda data: merge_audio_step(data, output_format="wav"),
        ),
        (
            "Move final audio",
            lambda data: move_step(
                data,
                source_key=PipelineKeys.ACTIVE_FILE_PATH,
                output_filename=f"output/{stream_id}/{date}.wav",
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

    return steps
