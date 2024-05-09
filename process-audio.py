from utils.config import parse_audio_parameters
from utils.file import create_and_change_directory, is_valid_file
from utils.helpers import print_error, print_info
from utils.media import (
    apply_audio_compression,
    download_media_from_youtube,
    get_video_upload_date,
    process_audio_file,
)
from utils.ui import confirm_parameters, confirmation_printout


def main():
    print_info("Processing audio...")

    youtube_url, start_time, end_time = parse_audio_parameters()

    confirm_parameters(
        {
            "URL": youtube_url,
            "Start": start_time,
            "End": end_time,
        }
    )

    try:
        upload_date = get_video_upload_date(youtube_url)
        output_dir = create_and_change_directory(upload_date)
        downloaded_audio_file = download_media_from_youtube(
            youtube_url, start_time, end_time, upload_date, "audio"
        )

        if not is_valid_file(downloaded_audio_file):
            raise ValueError(
                f"The file {downloaded_audio_file} was not created or is too small. Please check for errors."
            )

        # audio processing and compressions
        processed_file_name = process_audio_file(downloaded_audio_file)
        apply_audio_compression(processed_file_name, upload_date, output_dir)
        # transcribe_audio(processed_file_name, upload_date, output_dir)

        # final printout
        confirmation_printout(upload_date)

    except ValueError as ve:
        print_error(f"File validation error: {ve}")
    except Exception as e:
        print_error(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    main()
