import json
from jsonschema import validate


def _check_for_old_trim(config):
    """Trim used to live under audio and video separately. It is now shared."""
    old = [name for name in ("audio", "video") if "trim" in config.get(name, {})]
    if old:
        raise ValueError(
            "Trim times are now shared by audio and video. Move "
            + " and ".join(f"'{name}.trim'" for name in old)
            + " to a single top-level 'trim' block, e.g.\n"
            + '  "trim": {"start_time": "0:43:40", "end_time": "1:17:24"}'
        )


def load_and_validate_config(
    config_file="config/pipeline_config.json", schema_file="config/pipeline_schema.json"
):
    with open(schema_file, "r") as sf:
        schema = json.load(sf)
    with open(config_file, "r") as cf:
        config = json.load(cf)

    _check_for_old_trim(config)
    validate(instance=config, schema=schema)
    return config
