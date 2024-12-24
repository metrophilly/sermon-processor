from datetime import datetime
from app.downloaders.youtube_downloader import YouTubeDownloader
from app.pipelines.base_pipeline import Pipeline
from app.steps.download_step import DownloadStep
from app.steps.move_step import MoveStep
from app.steps.trim_step import TrimStep
from app.steps.merge_step import MergeStep
from app.downloaders.s3_downloader import S3Downloader
from app.downloaders.downloader_proxy import DownloaderProxy


def create_audio_pipeline(config):
    """
    Builds a pipeline to handle audio-only processing.

    Returns:
        Pipeline: a Pipeline instance ready for execution.
    """
    pipeline = Pipeline()
    date = datetime.now().strftime("%Y-%m-%d")

    # Extract config
    youtube_url = config["youtube_url"]
    stream_id = config.get("stream_id", "default-audio-stream")
    audio_conf = config.get("audio", {})
    audio_downloader = YouTubeDownloader(audio_only=True)

    # Build proxies
    audio_proxy = DownloaderProxy(
        real_downloader=audio_downloader,
        cache_dir="cache/audio",
    )
    s3_proxy = DownloaderProxy(real_downloader=S3Downloader(), cache_dir="cache/s3")

    # 1) Download main YouTube audio
    pipeline.add_step(
        DownloadStep(
            downloader=audio_proxy,
            url=youtube_url,
            date=date,
            stream_id=f"{stream_id}",
            filename="audio.%(ext)s",
            data_key="audio_file_path",
        )
    )

    # 2) Download intro/outro from S3
    audio_intro_url = audio_conf.get("intro_url")
    if audio_intro_url:
        pipeline.add_step(
            DownloadStep(
                downloader=s3_proxy,
                url=audio_intro_url,
                filename="audio_intro.mp3",
                data_key="audio_intro_path",
            )
        )

    audio_outro_url = audio_conf.get("outro_url")
    if audio_outro_url:
        pipeline.add_step(
            DownloadStep(
                downloader=s3_proxy,
                url=audio_outro_url,
                filename="audio_outro.mp3",
                data_key="audio_outro_path",
            )
        )

    # 3) Trim the audio
    if "trim" in audio_conf:
        start_time = audio_conf["trim"]["start_time"]
        end_time = audio_conf["trim"]["end_time"]
        pipeline.add_step(
            TrimStep(
                start_time=start_time,
                end_time=end_time,
                is_audio=True,
            )
        )

    # 4) Merge intro/outro to trimmed audio
    pipeline.add_step(MergeStep(is_audio=True))

    pipeline.add_step(
        MoveStep(
            source_key="merged_audio_file_path",  # This is set by the MergeStep
            output_filename=f"{stream_id}/{date}.mp3",  # Use stream ID for the final file name
        )
    )

    return pipeline
