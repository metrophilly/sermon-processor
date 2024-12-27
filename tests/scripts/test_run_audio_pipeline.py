import pytest
from unittest.mock import patch, Mock
from scripts.run_audio_pipeline import main
from app.data_models.pipeline_data import PipelineData


@patch("scripts.run_audio_pipeline.load_and_validate_config")
@patch("scripts.run_audio_pipeline.create_audio_pipeline")
@patch("scripts.run_audio_pipeline.PipelineData")
def test_main_script_happy_path(
    mock_pipeline_data, mock_create_pipeline, mock_config_loader
):
    # Mock configuration loading
    mock_config_loader.return_value = {
        "stream_id": "test_stream",
        "youtube_url": "https://youtube.com/video",
        "audio": {
            "intro_url": "https://s3.com/intro.wav",
            "outro_url": "https://s3.com/outro.wav",
            "trim": {"start_time": "00:00:10", "end_time": "00:01:00"},
        },
    }

    # Mock pipeline
    mock_pipeline_data.return_value = PipelineData()
    mock_create_pipeline.return_value = [
        ("Step 1", lambda data: data),
        ("Step 2", lambda data: data),
    ]

    # Execute main script
    data = main()

    # Validate execution and output
    assert isinstance(data, PipelineData)
    mock_config_loader.assert_called_once_with(
        config_file="config/pipeline_config.json",
        schema_file="config/pipeline_schema.json",
    )
    mock_create_pipeline.assert_called_once()
    assert len(mock_create_pipeline.return_value) == 2


@patch(
    "scripts.run_audio_pipeline.load_and_validate_config",
    side_effect=FileNotFoundError("Config not found"),
)
def test_main_script_missing_config(mock_config_loader):
    with pytest.raises(FileNotFoundError, match="Config not found"):
        main()


@patch(
    "scripts.run_audio_pipeline.create_audio_pipeline",
    side_effect=ValueError("Pipeline creation failed"),
)
def test_main_script_pipeline_creation_error(mock_create_pipeline):
    with pytest.raises(ValueError, match="Pipeline creation failed"):
        main()


@patch("scripts.run_audio_pipeline.create_audio_pipeline")
@patch("scripts.run_audio_pipeline.PipelineData")
def test_main_script_step_execution(mock_pipeline_data, mock_create_pipeline):
    # Simulate step functions and data flow
    data_mock = Mock()
    mock_pipeline_data.return_value = data_mock

    def mock_step(data):
        data.processed = True
        return data

    mock_create_pipeline.return_value = [("Step 1", mock_step)]

    data = main()

    # Ensure data flow through steps
    assert data.processed is True
    mock_create_pipeline.assert_called_once()
