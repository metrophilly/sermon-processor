from app.pipelines.base_pipeline import BasePipelineBuilder
from app.steps.merge_audio_step import merge_audio_step


class AudioPipelineBuilder(BasePipelineBuilder):
    """
    Builder for audio processing pipelines.
    """

    def __init__(self):
        super().__init__("audio")

    def build_pipeline(self, config):
        """
        Builds the pipeline to process audio files using functional chaining.
        """
        stream_id = config.get("stream_id", "default-audio-stream")
        audio_conf = config.get("audio", {})
        is_manual_download = config.get("manual_download", False)

        # Get date and create downloader proxies
        date = self._get_date_from_config(config)
        audio_proxy, s3_proxy = self._create_downloader_proxies(config)

        # Build pipeline steps
        steps = [
            self._create_intro_download_step(audio_conf, s3_proxy, "audio_intro.wav"),
            self._create_outro_download_step(audio_conf, s3_proxy, "audio_outro.wav"),
        ]

        # Add main content download step
        if is_manual_download:
            steps.append(self._create_manual_load_step(audio_conf))
        else:
            steps.append(
                self._create_main_download_step(
                    config, audio_proxy, date, stream_id, "audio.%(ext)s"
                )
            )

        # Add processing steps
        steps.extend(
            [
                self._create_trim_step(audio_conf, ffmpeg_hide_banner=True),
                self._create_fade_step(
                    fade_duration=1, ffmpeg_loglevel="info", is_video=False
                ),
                (
                    "Merge audio",
                    lambda data: merge_audio_step(data, output_format="wav"),
                ),
                self._create_move_step(stream_id, date, "wav"),
                self._create_cleanup_step(),
            ]
        )

        return steps


def create_audio_pipeline(config):
    """
    Builds the pipeline to process audio files using functional chaining.
    """
    builder = AudioPipelineBuilder()
    return builder.build_pipeline(config)
