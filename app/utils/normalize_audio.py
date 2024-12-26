import subprocess


def normalize_audio(input_path, output_path, codec="pcm_s16le", sample_rate=44100):
    # command = [
    #     "ffmpeg",
    #     "-i",
    #     input_path,
    #     "-acodec",
    #     codec,
    #     "-ar",
    #     str(sample_rate),
    #     output_path,
    # ]

    command = [
        "ffmpeg",
        "-i",
        input_path,
        "-acodec",
        codec,
        "-ar",
        str(sample_rate),
        # Add these parameters for consistent output
        "-ac",
        "2",  # stereo output
        "-b:a",
        "192k",  # consistent bitrate
        output_path,
    ]

    print(f"Normalizing audio file: {input_path} -> {output_path}")
    subprocess.run(command, check=True)
