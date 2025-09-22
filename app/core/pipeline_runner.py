from datetime import datetime
from typing import Callable, Any
from app.data_models.pipeline_data import PipelineData
from scripts.config_loader import load_and_validate_config
from colorama import Fore, Style


class PipelineRunner:
    """
    Shared pipeline execution logic for both audio and video processing.
    """

    def __init__(self, pipeline_factory: Callable[[dict], list]):
        """
        Initialize the pipeline runner with a pipeline factory function.

        Args:
            pipeline_factory: Function that takes config and returns pipeline steps
        """
        self.pipeline_factory = pipeline_factory

    def run(
        self,
        config_path: str = "config/pipeline_config.json",
        schema_path: str = "config/pipeline_schema.json",
    ) -> PipelineData:
        """
        Execute the pipeline with the given configuration.

        Args:
            config_path: Path to the configuration file
            schema_path: Path to the configuration schema file

        Returns:
            PipelineData: The final pipeline data after execution
        """
        config = load_and_validate_config(
            config_file=config_path, schema_file=schema_path
        )
        data = PipelineData()

        pipeline = self.pipeline_factory(config)
        start_time = datetime.now()

        for description, step_fn in pipeline:
            step_start_time = datetime.now()
            print(Fore.YELLOW + "===")
            print(f"Starting step: " + Fore.GREEN + f"{description}" + Style.RESET_ALL)

            # Execute the pipeline step
            data = step_fn(data)

            step_end_time = datetime.now()
            step_elapsed_time = step_end_time - step_start_time
            print(Fore.YELLOW + f"Completed step: " + Fore.GREEN + f"{description}")
            print(Fore.GREEN + f"Step elapsed time: {step_elapsed_time}" + Fore.YELLOW)
            print("===" + Style.RESET_ALL)

        end_time = datetime.now()
        elapsed_time = end_time - start_time

        print(Fore.YELLOW + f"Pipeline complete: {data}")
        print(Fore.GREEN + f"Total elapsed time: {elapsed_time}" + Style.RESET_ALL)

        return data


def run_pipeline(
    pipeline_factory: Callable[[dict], list],
    config_path: str = "config/pipeline_config.json",
    schema_path: str = "config/pipeline_schema.json",
) -> PipelineData:
    """
    Convenience function to run a pipeline with a factory function.

    Args:
        pipeline_factory: Function that takes config and returns pipeline steps
        config_path: Path to the configuration file
        schema_path: Path to the configuration schema file

    Returns:
        PipelineData: The final pipeline data after execution
    """
    runner = PipelineRunner(pipeline_factory)
    return runner.run(config_path, schema_path)
