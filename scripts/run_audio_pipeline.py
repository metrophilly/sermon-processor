import sys
from app.core import run_pipeline
from app.pipelines.audio_pipeline import create_audio_pipeline


def main(
    config_path="config/pipeline_config.json", schema_path="config/pipeline_schema.json"
):
    """
    Run the audio processing pipeline.

    Args:
        config_path: Path to the configuration file
        schema_path: Path to the configuration schema file

    Returns:
        PipelineData: The final pipeline data after execution
    """
    return run_pipeline(
        pipeline_factory=create_audio_pipeline,
        config_path=config_path,
        schema_path=schema_path,
    )


if __name__ == "__main__":
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    else:
        config_path = "config/pipeline_config.json"

    if len(sys.argv) > 2:
        schema_path = sys.argv[2]
    else:
        schema_path = "config/pipeline_schema.json"

    main(config_path, schema_path)
