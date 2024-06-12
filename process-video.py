import os
import time
from utils.config import parse_video_parameters
from utils.constants import OUTPUT_BASE_DIR
from utils.file import (
    create_and_change_directory,
    delete_dir,
    ensure_dir_exists,
    is_valid_file,
)
from utils.helpers import print_error, print_info, print_success
from utils.media import (
    check_and_download,
    crossfade_videos_with_pymovie,
    download_media_from_youtube,
    get_video_upload_date,
)
from utils.time import format_seconds_to_readable
from utils.ui import confirm_parameters


def main() -> None:
    warmup_perfcounter = time.perf_counter()

    print_info("Processing video...")

    ensure_dir_exists("tmp")
    ensure_dir_exists("data")

    youtube_url, start_time, end_time, intro_url, outro_url = parse_video_parameters()

    confirm_parameters(
        {
            "URL": youtube_url,
            "Start": start_time,
            "End": end_time,
        }
    )

    try:
        start_perfcounter = time.perf_counter()

        # set the config vars and paths
        upload_date = get_video_upload_date(youtube_url)
        output_dir = create_and_change_directory(upload_date)

        intro_clip_path = os.path.join(OUTPUT_BASE_DIR, "intro.mp4")
        outro_clip_path = os.path.join(OUTPUT_BASE_DIR, "outro.mp4")
        final_path = os.path.join(output_dir, f"{upload_date}_final.mp4")

        # download the video clips
        check_and_download(intro_url, intro_clip_path)
        check_and_download(outro_url, outro_clip_path)
        downloaded_video_file = download_media_from_youtube(
            youtube_url, start_time, end_time, "video"
        )

        if not is_valid_file(downloaded_video_file):
            raise ValueError(
                f"The file {downloaded_video_file} was not created or is too small. Please check for errors."
            )

        downloading_perfcounter = time.perf_counter()

        # stitch the clips together
        crossfade_videos_with_pymovie(
            [
                intro_clip_path,
                downloaded_video_file,
                outro_clip_path,
            ],
            1,
            final_path,
        )
        crossfade_perfcounter = time.perf_counter()

        print_success("Video processing complete.")

        end_perfcounter = time.perf_counter()

        # print the performance timing
        print_success(
            f"Downloading took  : {format_seconds_to_readable(downloading_perfcounter - start_perfcounter)} seconds."
        )
        print_success(
            f"Crossfading took  : {format_seconds_to_readable(crossfade_perfcounter - downloading_perfcounter)} seconds."
        )
        print_success(
            f"Total process took: {format_seconds_to_readable(end_perfcounter - start_perfcounter)} seconds."
        )

    except ValueError as ve:
        print_error(f"File validation error: {ve}")
    except Exception as e:
        print_error(f"An unexpected error occurred: {e}")
    finally:
        delete_dir("tmp")


if __name__ == "__main__":
    main()
