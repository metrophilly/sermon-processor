import sys
from scripts.config_loader import load_and_validate_config
from app.pipelines.audio_pipeline_factory import create_audio_pipeline


def main(
    config_path="config/pipeline_config.json", schema_path="config/pipeline_schema.json"
):
    config = load_and_validate_config(config_file=config_path, schema_file=schema_path)
    pipeline = create_audio_pipeline(config)
    data = pipeline.execute({})
    print("Audio pipeline complete:", data)


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
