from datetime import datetime
from typing import Dict, List, Tuple, Callable, Any
from app.constants import PipelineKeys
from app.downloaders.youtube_downloader import YouTubeDownloader
from app.downloaders.s3_downloader import S3Downloader
from app.downloaders.downloader_proxy import DownloaderProxy
from app.steps.delete_files_step import delete_files_step
from app.steps.download_step import download_step
from app.steps.fade_in_out_step import fade_in_out_step
from app.steps.manual_load_step import manual_load_step
from app.steps.trim_step import trim_step
from app.steps.move_step import move_step
from app.utils.youtube import get_youtube_upload_date


class BasePipelineBuilder:
    """
    Base class for building media processing pipelines with shared logic.
    """

    def __init__(self, media_type: str):
        """
        Initialize the pipeline builder.

        Args:
            media_type: Type of media being processed ("audio" or "video")
        """
        self.media_type = media_type
        self._validate_media_type()

    def _validate_media_type(self):
        """Validate that media_type is supported."""
        if self.media_type not in ["audio", "video"]:
            raise ValueError(f"Unsupported media type: {self.media_type}")

    def _get_date_from_config(self, config: Dict[str, Any]) -> str:
        """
        Extract date from config, either from YouTube URL or current date.

        Args:
            config: Pipeline configuration

        Returns:
            str: Date string in YYYY-MM-DD format
        """
        youtube_url = config.get("youtube_url")
        if youtube_url:
            date = get_youtube_upload_date(youtube_url)
            if not date:
                print("Failed to fetch upload date. Falling back to the current date.")
                date = datetime.now().strftime("%Y-%m-%d")
        else:
            date = datetime.now().strftime("%Y-%m-%d")
        return date

    def _create_downloader_proxies(
        self, config: Dict[str, Any]
    ) -> Tuple[DownloaderProxy, DownloaderProxy]:
        """
        Create downloader proxies for YouTube and S3 downloads.

        Args:
            config: Pipeline configuration

        Returns:
            Tuple of (main_downloader_proxy, s3_downloader_proxy)
        """
        if self.media_type == "audio":
            main_downloader = YouTubeDownloader(audio_only=True)
            cache_dir = "cache/audio"
        else:  # video
            main_downloader = YouTubeDownloader(quiet=True)
            cache_dir = "cache/video"

        main_proxy = DownloaderProxy(
            real_downloader=main_downloader, cache_dir=cache_dir
        )
        s3_proxy = DownloaderProxy(real_downloader=S3Downloader(), cache_dir="cache/s3")

        return main_proxy, s3_proxy

    def _create_intro_download_step(
        self, media_conf: Dict[str, Any], s3_proxy: DownloaderProxy, filename: str
    ) -> Tuple[str, Callable]:
        """
        Create intro download step.

        Args:
            media_conf: Media-specific configuration (audio or video)
            s3_proxy: S3 downloader proxy
            filename: Filename for the intro file

        Returns:
            Tuple of (step_description, step_function)
        """
        return (
            f"Download intro {self.media_type}",
            lambda data: (
                download_step(
                    data,
                    downloader=s3_proxy,
                    url=media_conf.get("intro_url"),
                    filename=filename,
                    key=PipelineKeys.INTRO_FILE_PATH,
                )
                if media_conf.get("intro_url")
                else data
            ),
        )

    def _create_outro_download_step(
        self, media_conf: Dict[str, Any], s3_proxy: DownloaderProxy, filename: str
    ) -> Tuple[str, Callable]:
        """
        Create outro download step.

        Args:
            media_conf: Media-specific configuration (audio or video)
            s3_proxy: S3 downloader proxy
            filename: Filename for the outro file

        Returns:
            Tuple of (step_description, step_function)
        """
        return (
            f"Download outro {self.media_type}",
            lambda data: (
                download_step(
                    data,
                    downloader=s3_proxy,
                    url=media_conf.get("outro_url"),
                    filename=filename,
                    key=PipelineKeys.OUTRO_FILE_PATH,
                )
                if media_conf.get("outro_url")
                else data
            ),
        )

    def _create_main_download_step(
        self,
        config: Dict[str, Any],
        main_proxy: DownloaderProxy,
        date: str,
        stream_id: str,
        filename: str,
    ) -> Tuple[str, Callable]:
        """
        Create main content download step.

        Args:
            config: Pipeline configuration
            main_proxy: Main downloader proxy
            date: Date string
            stream_id: Stream identifier
            filename: Filename pattern for the main file

        Returns:
            Tuple of (step_description, step_function)
        """
        return (
            f"Download YouTube {self.media_type}",
            lambda data: download_step(
                data,
                downloader=main_proxy,
                url=config.get("youtube_url"),
                filename=filename,
                key=PipelineKeys.MAIN_FILE_PATH,
                date=date,
                stream_id=stream_id,
            ),
        )

    def _create_manual_load_step(
        self, media_conf: Dict[str, Any]
    ) -> Tuple[str, Callable]:
        """
        Create manual load step.

        Args:
            media_conf: Media-specific configuration (audio or video)

        Returns:
            Tuple of (step_description, step_function)
        """
        manual_path = media_conf.get("manual_path")
        return (
            f"Load manually downloaded {self.media_type}",
            lambda data: manual_load_step(data, manual_path=manual_path),
        )

    def _create_trim_step(
        self, media_conf: Dict[str, Any], **kwargs
    ) -> Tuple[str, Callable]:
        """
        Create trim step.

        Args:
            media_conf: Media-specific configuration (audio or video)
            **kwargs: Additional arguments for trim_step

        Returns:
            Tuple of (step_description, step_function)
        """
        return (
            f"Trim {self.media_type}",
            lambda data: (
                trim_step(
                    data,
                    start_time=media_conf.get("trim", {}).get("start_time"),
                    end_time=media_conf.get("trim", {}).get("end_time"),
                    **kwargs,
                )
                if "trim" in media_conf
                else data
            ),
        )

    def _create_fade_step(self, **kwargs) -> Tuple[str, Callable]:
        """
        Create fade-in/out step.

        Args:
            **kwargs: Additional arguments for fade_in_out_step

        Returns:
            Tuple of (step_description, step_function)
        """
        return (
            "Apply fade-in/out",
            lambda data: fade_in_out_step(data, **kwargs),
        )

    def _create_move_step(
        self, stream_id: str, date: str, file_extension: str
    ) -> Tuple[str, Callable]:
        """
        Create move to output directory step.

        Args:
            stream_id: Stream identifier
            date: Date string
            file_extension: Output file extension

        Returns:
            Tuple of (step_description, step_function)
        """
        return (
            f"Move final {self.media_type}",
            lambda data: move_step(
                data,
                source_key=PipelineKeys.ACTIVE_FILE_PATH,
                output_filename=f"output/{stream_id}/{date}.{file_extension}",
            ),
        )

    def _create_cleanup_step(self) -> Tuple[str, Callable]:
        """
        Create cleanup step for intermediate files.

        Returns:
            Tuple of (step_description, step_function)
        """
        return (
            "Delete intermediate files",
            lambda data: delete_files_step(
                data,
                file_keys=[PipelineKeys.INTERMEDIATE_FILES],
            ),
        )

    def build_pipeline(self, config: Dict[str, Any]) -> List[Tuple[str, Callable]]:
        """
        Build the complete pipeline. Must be implemented by subclasses.

        Args:
            config: Pipeline configuration

        Returns:
            List of pipeline steps as (description, function) tuples
        """
        raise NotImplementedError("Subclasses must implement build_pipeline method")
