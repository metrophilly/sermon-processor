import subprocess
from app.pipelines.base_pipeline import PipelineStep
from app.utils.paths import relative_path


class TrimStep(PipelineStep):
    def __init__(self, start_time, end_time, is_audio=False):
        self.start_time = start_time
        self.end_time = end_time
        self.is_audio = is_audio

    def process(self, data):
        """
        Expects data["audio_file_path"] (if is_audio=True)
        or data["video_file_path"] (if is_audio=False).
        """
        file_key = "audio_file_path" if self.is_audio else "video_file_path"
        input_file = data.get(file_key)
        if not input_file:
            raise ValueError(f"No input file found in {file_key}")

        output_file = (
            input_file.replace(".mp3", "_trimmed.mp3")
            if self.is_audio
            else input_file.replace(".mp4", "_trimmed.mp4")
        )

        command = [
            "ffmpeg",
            "-i",
            input_file,
            "-ss",
            self.start_time,
            "-to",
            self.end_time,
            "-c",
            "copy",
            output_file,
        ]

        print(
            f"Trimming file from {self.start_time} to {self.end_time}: {input_file} -> {output_file}"
        )
        subprocess.run(command, check=True)

        # Update the pipeline data to point to the trimmed file
        data[file_key] = relative_path(output_file)
        return data
