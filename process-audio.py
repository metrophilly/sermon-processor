from utils.config import parse_audio_parameters, read_config_file
from utils.file import create_and_change_directory, is_valid_audio_file
from utils.media import (
    apply_audio_compression,
    download_audio_from_youtube,
    get_video_upload_date,
    process_audio_file,
)
from utils.ui import confirm_parameters, confirmation_printout


def main():

    # parse preset params
    config_file_path = "config/config.txt"
    config = read_config_file(config_file_path)
    youtube_url, start_time, end_time = parse_audio_parameters(config)

    confirm_parameters(youtube_url, start_time, end_time)

    try:
        upload_date = get_video_upload_date(youtube_url)
        output_dir = create_and_change_directory(upload_date)
        downloaded_audio_file = download_audio_from_youtube(
            youtube_url, start_time, end_time, output_dir
        )

        if not is_valid_audio_file(downloaded_audio_file):
            print(
                f"The file {downloaded_audio_file} was not created or is too small. Please check for errors."
            )
            exit(1)

        # audio processing and compressions
        processed_file_name = process_audio_file(downloaded_audio_file, output_dir)
        apply_audio_compression(processed_file_name, upload_date, output_dir)
        # transcribe_audio(processed_file_name, upload_date, output_dir)

        # final printouts
        confirmation_printout(output_dir)

    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    main()
