from utils.config import parse_video_parameters, read_config_file
from utils.file import ensure_dir_exists, ensure_file_exists
from utils.media import (
    apply_video_compression,
    crossfade_videos,
    download_video,
    get_video_settings,
)
from utils.types import PathsDict


def main() -> None:
    ensure_dir_exists("tmp")
    ensure_dir_exists("output")
    ensure_file_exists("config/base.mp4")

    # parse preset params
    config_file_path = "config/config.txt"
    config = read_config_file(config_file_path)
    intro_url, outro_url = parse_video_parameters(config)

    download_video(intro_url, "./tmp/intro.mp4")
    download_video(outro_url, "./tmp/outro.mp4")

    paths: PathsDict = {
        "intro": {
            "raw": "./tmp/intro.mp4",
            "compressed": "./tmp/01-intro_compressed.mp4",
            "crossfaded": "./tmp/04-intro-base_crossfaded.mp4",
        },
        "base": {
            "raw": "./config/base.mp4",
            "compressed": "./tmp/02-base_compressed.mp4",
            "crossfaded": "./tmp/05-base-output_crossfaded.mp4",
        },
        "outro": {
            "raw": "./tmp/outro.mp4",
            "compressed": "./tmp/03-outro_compressed.mp4",
        },
    }

    final_path: str = "./data/FINAL_full-compressed.mp4"

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


if __name__ == "__main__":
    main()
