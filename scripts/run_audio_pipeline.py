from datetime import datetime
import sys
from app.data_models.pipeline_data import PipelineData
from scripts.config_loader import load_and_validate_config
from app.pipelines.audio_pipeline import create_audio_pipeline
from colorama import Fore, Style


def main(
    config_path="config/pipeline_config.json", schema_path="config/pipeline_schema.json"
):
    config = load_and_validate_config(config_file=config_path, schema_file=schema_path)
    data = PipelineData()

    pipeline = create_audio_pipeline(config)
    start_time = datetime.now()

    for description, step_fn in pipeline:
        step_start_time = datetime.now()
        print(Fore.YELLOW + "===")
        print(f"Starting step: " + Fore.GREEN + f"{description}" + Style.RESET_ALL)

        # execute the pipeline step
        data = step_fn(data)

        step_end_time = datetime.now()
        step_elapsed_time = step_end_time - step_start_time
        print(Fore.YELLOW + f"Completed step: " + Fore.GREEN + f"{description}")
        print(Fore.GREEN + f"Step elapsed time: {step_elapsed_time}" + Fore.YELLOW)
        print("===" + Style.RESET_ALL)

    end_time = datetime.now()
    elapsed_time = end_time - start_time

    print(Fore.YELLOW + f"Audio pipeline complete: {data}")
    print(Fore.GREEN + f"Total elapsed time: {elapsed_time}" + Style.RESET_ALL)

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
