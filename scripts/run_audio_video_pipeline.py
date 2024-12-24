import sys

from scripts.config_loader import load_and_validate_config
from app.pipelines.audio_pipeline_factory import create_audio_pipeline
from app.pipelines.video_pipeline_factory import create_video_pipeline


def main(
    config_path="config/pipeline_config.json", schema_path="config/pipeline_schema.json"
):
    """
    Loads the config, validates it, then creates both the audio and video pipelines, and executes them.
    """
    # Load + validate config
    config = load_and_validate_config(config_file=config_path, schema_file=schema_path)

    # Audio pipeline
    audio_pipeline = create_audio_pipeline(config)
    audio_result = audio_pipeline.execute({})
    print("Audio pipeline execution complete:", audio_result)

    # Video pipeline
    video_pipeline = create_video_pipeline(config)
    video_result = video_pipeline.execute({})
    print("Video pipeline execution complete:", video_result)


if __name__ == "__main__":
    # Accept optional command-line arguments for config and schema
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    else:
        config_path = "config/pipeline_config.json"

    if len(sys.argv) > 2:
        schema_path = sys.argv[2]
    else:
        schema_path = "config/pipeline_schema.json"

    main(config_path, schema_path)
