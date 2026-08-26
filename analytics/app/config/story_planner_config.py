import json
from pathlib import Path
from typing import Any


_STORY_PLANNER_CONFIG_PATH = Path(__file__).with_name(
    "story_planner_config.json"
)


def load_story_planner_config() -> dict[str, Any]:
    with _STORY_PLANNER_CONFIG_PATH.open(
        "r",
        encoding="utf-8",
    ) as config_file:
        return json.load(config_file)
