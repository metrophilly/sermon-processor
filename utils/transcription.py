import json
import os
import whisper


def transcribe_audio(audio_file_path, upload_date, output_dir):
    model = whisper.load_model("base")

    options = {
        "language": "en",
        "verbose": True,
    }

    # Transcribe the audio file with the specified language
    transcribed_text = model.transcribe(audio_file_path, **options)

    # Construct the output file path for only txt
    output_file_name = os.path.join(output_dir, f"{upload_date}_transcribed.txt")

    # Construct the output file path for segments
    segment_file_name = os.path.join(
        output_dir, f"{upload_date}_transcribed_segments.txt"
    )

    result = {
        "transcribed_text": transcribed_text,
        "output_file_name": output_file_name,
        "segment_file_name": segment_file_name,
    }

    # Write the transcribed text to the output file
    with open(result["output_file_name"], "w") as f:
        f.write(result["transcribed_text"]["text"])
    with open(result["segment_file_name"], "w") as f:
        for segment in result["transcribed_text"]["segments"]:
            f.write(json.dumps(segment) + "\n")

    return result
