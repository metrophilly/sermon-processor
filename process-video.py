import os
from utils.config import parse_video_parameters, read_config_file
from utils.file import (
    create_and_change_directory,
    ensure_dir_exists,
    ensure_file_exists,
    is_valid_file,
)
from utils.media import (
    apply_video_compression,
    check_and_download,
    crossfade_videos,
    download_media_from_youtube,
    get_video_settings,
    get_video_upload_date,
)
from utils.types import PathsDict
from utils.ui import confirm_parameters


def main() -> None:
    ensure_dir_exists("tmp")
    ensure_dir_exists("data")

    # parse preset params
    config_file_path = "config.txt"
    config = read_config_file(config_file_path)
    youtube_url, start_time, end_time, intro_url, outro_url = parse_video_parameters(
        config
    )

    confirm_parameters(youtube_url, start_time, end_time)

    try:
        check_and_download(intro_url, "./tmp/intro.mp4")
        check_and_download(outro_url, "./tmp/outro.mp4")

        upload_date = get_video_upload_date(youtube_url)
        output_dir = create_and_change_directory(upload_date)
        downloaded_video_file = download_media_from_youtube(
            youtube_url, start_time, end_time, upload_date, "video"
        )

        paths: PathsDict = {
            "intro": {
                "raw": "./tmp/intro.mp4",
                "compressed": "./tmp/01-intro_compressed.mp4",
                "crossfaded": "./tmp/04-intro-base_crossfaded.mp4",
            },
            "base": {
                "raw": f"./tmp/{upload_date}_base_downloaded_raw.mp4",
                "compressed": "./tmp/02-base_compressed.mp4",
                "crossfaded": "./tmp/05-base-output_crossfaded.mp4",
            },
            "outro": {
                "raw": "./tmp/outro.mp4",
                "compressed": "./tmp/03-outro_compressed.mp4",
            },
        }
        final_path = os.path.join(output_dir, f"{upload_date}_final.mp4")

        if not is_valid_file(downloaded_video_file):
            raise ValueError(
                f"The file {downloaded_video_file} was not created or is too small. Please check for errors."
            )

        # apply "standard loudness" to all clips individually
        for key in paths.keys():
            apply_video_compression(paths[key]["raw"], paths[key]["compressed"])

        base_settings = get_video_settings(paths["base"]["compressed"])

        # crossfade the intro to base
        crossfade_videos(
            paths["intro"]["compressed"],
            paths["base"]["compressed"],
            1,
            paths["intro"]["crossfaded"],
            base_settings,
        )

        # crossfade the intro/base result to outro
        crossfade_videos(
            paths["intro"]["crossfaded"],
            paths["outro"]["compressed"],
            1,
            final_path,
            base_settings,
        )

        print("Video processing complete.")

    except ValueError as ve:
        print(f"File validation error: {ve}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    main()
