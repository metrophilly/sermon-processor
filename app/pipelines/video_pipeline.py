from app.pipelines.base_pipeline import BasePipelineBuilder
from app.steps.merge_video_step import merge_video_step


class VideoPipelineBuilder(BasePipelineBuilder):
    """
    Builder for video processing pipelines.
    """

    def __init__(self):
        super().__init__("video")

    def build_pipeline(self, config):
        """
        Builds the pipeline to process video files using functional chaining.
        """
        stream_id = config.get("stream_id", "default-video-stream")
        video_conf = config.get("video", {})
        is_manual_download = config.get("manual_download", False)

        # Get date and create downloader proxies
        date = self._get_date_from_config(config)
        video_proxy, s3_proxy = self._create_downloader_proxies(config)

        # Build pipeline steps
        steps = [
            self._create_intro_download_step(video_conf, s3_proxy, "video_intro.mp4"),
            self._create_outro_download_step(video_conf, s3_proxy, "video_outro.mp4"),
        ]

        # Add main content download step
        if is_manual_download:
            steps.append(self._create_manual_load_step(video_conf))
        else:
            steps.append(
                self._create_main_download_step(
                    config, video_proxy, date, stream_id, "video.%(ext)s"
                )
            )

        # Add processing steps
        steps.extend(
            [
                self._create_trim_step(
                    video_conf, ffmpeg_loglevel="info", ffmpeg_hide_banner=True
                ),
                self._create_fade_step(
                    fade_duration=1, ffmpeg_loglevel="info", is_video=True
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
                self._create_move_step(stream_id, date, "mp4"),
                self._create_cleanup_step(),
            ]
        )

        return steps


def create_video_pipeline(config):
    """
    Builds the pipeline to process video files using functional chaining.
    """
    builder = VideoPipelineBuilder()
    return builder.build_pipeline(config)
