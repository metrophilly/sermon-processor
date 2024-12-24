import os
import shutil
from app.pipelines.base_pipeline import PipelineStep
from app.utils.paths import relative_path, ensure_dir_exists


class MoveStep(PipelineStep):
    def __init__(self, source_key, output_filename, destination_dir_key="output"):
        """
        Args:
            source_key (str): Key in `data` where the source file path is stored.
            destination_dir_key (str): Key in `data` for the destination directory base.
            output_filename (str): Final filename to save in the destination directory.
        """
        self.source_key = source_key
        self.destination_dir_key = destination_dir_key
        self.output_filename = output_filename

    def process(self, data):
        """
        Moves the file to the desired output directory.

        Args:
            data (dict): Pipeline data object.

        Returns:
            dict: Updated pipeline data with the new output path.
        """
        source_path = relative_path(data.get(self.source_key))
        if not source_path or not os.path.exists(source_path):
            raise ValueError(
                f"Source file not found for {self.source_key}: {source_path}"
            )

        # Get destination directory from data, defaulting to "output"
        destination_base = data.get(self.destination_dir_key, "output")
        destination_dir = os.path.join(
            destination_base, os.path.dirname(self.output_filename)
        )
        ensure_dir_exists(destination_dir)

        # Final destination path
        destination_path = os.path.join(
            destination_dir, os.path.basename(self.output_filename)
        )

        # Move the file
        print(f"Moving file from {source_path} to {destination_path}...")
        shutil.move(source_path, destination_path)

        # Store relative paths in the data object
        relative_destination_path = os.path.relpath(destination_path, start=os.getcwd())
        data["final_output_path"] = relative_destination_path

        return data
