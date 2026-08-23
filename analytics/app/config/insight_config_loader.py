import json
from pathlib import Path
from typing import Any


_INSIGHT_CONFIG_PATH = Path(__file__).with_name(
    "insight_config.json"
)


def load_insight_config() -> dict[str, Any]:
    with _INSIGHT_CONFIG_PATH.open(
        "r",
        encoding="utf-8",
    ) as config_file:
        return json.load(config_file)