import json

import pytest

from scripts.config_loader import load_and_validate_config

SCHEMA = "config/pipeline_schema.json"


def _write(tmp_path, config):
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config))
    return str(path)


BASE = {"youtube_url": "https://www.youtube.com/watch?v=x", "manual_download": False}


def test_one_top_level_trim_is_accepted_with_flexible_times(tmp_path):
    path = _write(tmp_path, {**BASE, "trim": {"start_time": "0:43:40", "end_time": "01:17:24"}})
    assert load_and_validate_config(path, SCHEMA)["trim"]["start_time"] == "0:43:40"


@pytest.mark.parametrize("media", ["audio", "video"])
def test_old_per_media_trim_gets_a_clear_message(tmp_path, media):
    path = _write(tmp_path, {**BASE, media: {"trim": {"start_time": "0:00:10", "end_time": "0:00:20"}}})
    with pytest.raises(ValueError, match="top-level 'trim'"):
        load_and_validate_config(path, SCHEMA)


def test_the_example_config_is_valid():
    assert load_and_validate_config("config/pipeline_config.json.example", SCHEMA)["trim"]


def test_audio_pipeline_and_video_pipeline_read_the_shared_trim():
    from app.pipelines.audio_pipeline import create_audio_pipeline  # noqa: F401
    from app.pipelines.base_pipeline import BasePipelineBuilder

    builder = BasePipelineBuilder("video")
    description, step = builder._create_trim_step(
        {"trim": {"start_time": "0:00:10", "end_time": "0:00:20"}}
    )
    assert description == "Trim video"
    _, no_trim_step = builder._create_trim_step({})
    sentinel = object()
    assert no_trim_step(sentinel) is sentinel  # no trim configured -> pass-through
