from app.pipelines.base_pipeline import BasePipelineBuilder
from app.steps.render_audio_step import render_audio_step


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

        # Add processing steps: one ffmpeg run does trim + fade + normalize + join
        trim = config.get("trim", {})
        output_format = audio_conf.get("output_format", "wav")
        steps.extend(
            [
                (
                    "Render audio (trim, fade, normalize, add intro/outro)",
                    lambda data: render_audio_step(
                        data,
                        start_time=trim.get("start_time"),
                        end_time=trim.get("end_time"),
                        output_format=output_format,
                        fade_duration=1,
                    ),
                ),
                self._create_move_step(stream_id, date, output_format),
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
