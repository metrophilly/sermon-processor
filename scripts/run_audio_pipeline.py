import sys
from app.data_models.pipeline_data import PipelineData
from scripts.config_loader import load_and_validate_config
from app.pipelines.audio_pipeline import create_audio_pipeline


def main(
    config_path="config/pipeline_config.json", schema_path="config/pipeline_schema.json"
):
    config = load_and_validate_config(config_file=config_path, schema_file=schema_path)
    data = PipelineData()

    pipeline = create_audio_pipeline(config)

    # Execute the pipeline
    for description, step_fn in pipeline:
        print(f"Starting step: {description}")
        data = step_fn(data)
        print(f"Completed step: {description}")

    print("Audio pipeline complete:", data)
    return data


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
