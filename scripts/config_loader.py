import json
from jsonschema import validate


def load_and_validate_config(
    config_file="config/pipeline_config.json", schema_file="config/pipeline_schema.json"
):
    with open(schema_file, "r") as sf:
        schema = json.load(sf)
    with open(config_file, "r") as cf:
        config = json.load(cf)

    validate(instance=config, schema=schema)
    return config
