from utils.time import get_formatted_time


def read_config_file(config_file_path):
    """Read configuration from a file and return a dictionary of parameters."""
    config = {}
    try:
        with open(config_file_path, "r") as file:
            for line in file:
                key, value = line.strip().split("=", 1)
                config[key.strip().lower()] = value.strip()
    except FileNotFoundError:
        print(f"Configuration file not found: {config_file_path}")
        print(
            f"Please run `cp config.example.txt config.txt` and adjust the config parameters"
        )
        exit(1)
    except ValueError:
        print("Configuration file format error, should be 'key=value'")
        exit(1)
    return config


def parse_audio_parameters(config):
    """Parse and format parameters from the configuration dictionary."""
    try:
        youtube_url = config["url"]
        start_time = get_formatted_time(config["start"])
        end_time = get_formatted_time(config["end"])
    except KeyError as e:
        print(f"Missing necessary configuration parameter: {e}")
        exit(1)
    return youtube_url, start_time, end_time


def parse_video_parameters(config):
    """Parse and format parameters from the configuration dictionary."""
    try:
        youtube_url = config["url"]
        start_time = get_formatted_time(config["start"])
        end_time = get_formatted_time(config["end"])
        intro_url = config["video_intro"]
        outro_url = config["video_outro"]
    except KeyError as e:
        print(f"Missing necessary configuration parameter: {e}")
        exit(1)
    return youtube_url, start_time, end_time, intro_url, outro_url
