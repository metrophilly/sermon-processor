import os
import subprocess
from app.data_models.pipeline_data import PipelineData
from app.utils.normalize_video import normalize_video


def merge_video_step(
    data: PipelineData,
    output_format="mp4",
    resolution="1920x1080",
    frame_rate=30,
    ffmpeg_loglevel="info",
    ffmpeg_hide_banner=False,
):
    """
    Merges intro, main, and outro video files into a single output file.

    Args:
        data (PipelineData): The pipeline data object.
        output_format (str): Desired output format (default: "mp4").
        resolution (str): Target resolution for the output video.
        frame_rate (int): Target frame rate for the output video.

    Returns:
        PipelineData: Updated data object with the merged video path.
    """
    intro_path = os.path.abspath(data.intro_file_path)
    main_path = os.path.abspath(data.active_file_path)
    outro_path = os.path.abspath(data.outro_file_path)

    if not all([intro_path, main_path, outro_path]):
        raise ValueError("Missing one or more required video file paths.")

    # Normalize all files to consistent format
    normalized_paths = []
    for path in [intro_path, main_path, outro_path]:

        base, _ = os.path.splitext(path)
        normalized_path = f"{base}_normalized.{output_format}"

        normalize_video(
            input_path=path,
            output_path=normalized_path,
            ffmpeg_loglevel=ffmpeg_loglevel,
        )

        normalized_paths.append(normalized_path)

    # Create the file list for `ffmpeg`
    base, _ = os.path.splitext(main_path)
    file_list_path = f"{base}_file_list.txt"
    with open(file_list_path, "w") as f:
        for normalized_path in normalized_paths:
            f.write(f"file '{normalized_path}'\n")

    # Determine output file name dynamically
    output_file = f"{base}_merged.{output_format}"

    command = ["ffmpeg", "-loglevel", ffmpeg_loglevel]
    if ffmpeg_hide_banner:
        command.append("-hide_banner")
    command.extend(
        [
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            file_list_path,
            "-c:v",
            "copy",  # Copy video stream without re-encoding, we already normalized
            "-c:a",
            "aac",  # Re-encode audio for consistency
            output_file,
        ]
    )

    # Run `ffmpeg` command
    print(f"Merging files into {output_file}...")
    subprocess.run(command, check=True)

    # Clean up temporary files
    if os.path.exists(file_list_path):
        os.remove(file_list_path)
    for path in normalized_paths:
        if os.path.exists(path):
            os.remove(path)

    # Update pipeline data with the merged file path
    data.active_file_path = output_file

    return data
