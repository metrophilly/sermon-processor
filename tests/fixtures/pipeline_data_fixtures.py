import pytest
from app.data_models.pipeline_data import PipelineData


@pytest.fixture
def pipeline_data():
    return PipelineData(
        intro_file_path="cache/s3/audio_intro.wav",
        outro_file_path="cache/s3/audio_outro.wav",
        active_file_path="cache/audio/audio_trimmed.wav",
        downloaded_files=[
            "cache/s3/audio_intro.wav",
            "cache/audio/audio_trimmed.wav",
            "cache/s3/audio_outro.wav",
        ],
    )
