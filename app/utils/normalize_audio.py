import subprocess


def normalize_audio(
    input_path,
    output_path,
    codec="pcm_s16le",
    sample_rate=44100,
    ffmpeg_loglevel="info",
):
    """
    Normalize audio file with consistent loudness, sample rate, and format.

    Args:
        input_path (str): Path to input audio file
        output_path (str): Path for output audio file
        codec (str): Audio codec to use (default: pcm_s16le)
        sample_rate (int): Sample rate in Hz (default: 44100)
    """

    # Add loudnorm filter to normalize perceived loudness
    filter_chain = [
        "loudnorm=I=-16:TP=-1:LRA=11:linear=true"  # Target -16 lu's, prevent true peaks above -1dB
    ]

    command = [
        "ffmpeg",
        "-loglevel",
        ffmpeg_loglevel,
        "-i",
        input_path,
        "-acodec",
        codec,
        "-ar",
        str(sample_rate),
        "-ac",
        "2",  # stereo output
        "-b:a",
        "192k",  # consistent bitrate
        "-af",
        ",".join(filter_chain),  # apply the filter chain
        output_path,
    ]

    print(f"Normalizing audio file: {input_path} -> {output_path}")
    subprocess.run(command, check=True)
