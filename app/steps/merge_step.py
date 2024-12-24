import subprocess
import os
from app.pipelines.base_pipeline import PipelineStep
from app.utils.paths import absolute_path, ensure_dir_exists


class MergeStep(PipelineStep):
    def __init__(self, is_audio=False):
        self.is_audio = is_audio

    def process(self, data):
        if self.is_audio:
            # Get absolute paths for intro, main, and outro
            intro_path = absolute_path(data.get("audio_intro_path"))
            main_path = absolute_path(data.get("audio_file_path"))
            outro_path = absolute_path(data.get("audio_outro_path"))

            if not all([intro_path, main_path, outro_path]):
                raise ValueError("Missing required audio paths in data.")

            # Ensure output directory exists
            output_dir = os.path.dirname(main_path)
            ensure_dir_exists(output_dir)

            # Output file and merge list paths
            output_file = os.path.join(output_dir, "merged_audio.mp3")
            file_list_path = os.path.join(output_dir, "merge_list.txt")

            # Generate the merge list file with absolute paths
            with open(file_list_path, "w") as f:
                f.write(f"file '{intro_path}'\n")
                f.write(f"file '{main_path}'\n")
                f.write(f"file '{outro_path}'\n")

            # FFmpeg command to concatenate the files
            command = [
                "ffmpeg",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                file_list_path,
                "-c",
                "copy",
                output_file,
            ]

            print(f"Merging files into {output_file}...")
            subprocess.run(command, check=True)

            # Clean up the temporary merge list file
            os.remove(file_list_path)

            # Store the merged file path in the data dictionary
            data["merged_audio_file_path"] = output_file

        return data
