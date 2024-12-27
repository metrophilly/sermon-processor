# app/steps/trim_step.py
import os
import subprocess
from app.data_models.pipeline_data import PipelineData
from app.constants import PipelineKeys
from app.utils.paths import file_ext


def trim_step(
    data: PipelineData,
    start_time,
    end_time,
    ffmpeg_loglevel="info",
    ffmpeg_hide_banner=False,
    overwrite=False,
):

    file_key = PipelineKeys.ACTIVE_FILE_PATH
    input_file = getattr(data, file_key, None)

    if not input_file:
        raise ValueError(f"No input file found for {file_key}")

    ext = file_ext(input_file)
    output_file = input_file.replace(ext, f"_trimmed{ext}")

    if os.path.exists(output_file) and not overwrite:
        print(f"Output file already exists: {output_file}. Skipping trim step.")
        setattr(data, file_key, output_file)
        return data

    command = ["ffmpeg", "-loglevel", ffmpeg_loglevel]
    if ffmpeg_hide_banner:
        command.extend(["-hide_banner"])

    command.extend(
        [
            "-i",
            input_file,
            "-ss",
            start_time,
            "-to",
            end_time,
            "-c",
            "copy",
            output_file,
        ]
    )

    print(
        f"Trimming file from {start_time} to {end_time}: {input_file} -> {output_file}"
    )
    subprocess.run(command, check=True)
    setattr(data, file_key, output_file)

    return data
