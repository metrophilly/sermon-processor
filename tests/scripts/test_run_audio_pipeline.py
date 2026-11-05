import pytest
from unittest.mock import patch
from scripts.run_audio_pipeline import main
from app.data_models.pipeline_data import PipelineData

# `main()` delegates to app.core.pipeline_runner, which owns config loading and
# PipelineData creation, so those are the names to patch. Every test patches the
# config loader so it never reads the real config/pipeline_config.json.
LOADER = "app.core.pipeline_runner.load_and_validate_config"
FACTORY = "scripts.run_audio_pipeline.create_audio_pipeline"

CONFIG = {
    "stream_id": "test_stream",
    "youtube_url": "https://youtube.com/video",
    "manual_download": False,
    "audio": {
        "intro_url": "https://s3.com/intro.wav",
        "outro_url": "https://s3.com/outro.wav",
        "trim": {"start_time": "00:00:10", "end_time": "00:01:00"},
    },
}


@patch(FACTORY)
@patch(LOADER, return_value=CONFIG)
def test_main_script_happy_path(mock_config_loader, mock_create_pipeline):
    mock_create_pipeline.return_value = [
        ("Step 1", lambda data: data),
        ("Step 2", lambda data: data),
    ]

    data = main()

    assert isinstance(data, PipelineData)
    mock_config_loader.assert_called_once_with(
        config_file="config/pipeline_config.json",
        schema_file="config/pipeline_schema.json",
    )
    mock_create_pipeline.assert_called_once_with(CONFIG)


@patch(LOADER, side_effect=FileNotFoundError("Config not found"))
def test_main_script_missing_config(mock_config_loader):
    with pytest.raises(FileNotFoundError, match="Config not found"):
        main()


@patch(FACTORY, side_effect=ValueError("Pipeline creation failed"))
@patch(LOADER, return_value=CONFIG)
def test_main_script_pipeline_creation_error(mock_config_loader, mock_create_pipeline):
    with pytest.raises(ValueError, match="Pipeline creation failed"):
        main()


@patch(FACTORY)
@patch(LOADER, return_value=CONFIG)
def test_main_script_step_execution(mock_config_loader, mock_create_pipeline):
    def mock_step(data):
        data.processed = True
        return data

    mock_create_pipeline.return_value = [("Step 1", mock_step)]

    data = main()

    assert data.processed is True
    mock_create_pipeline.assert_called_once()
