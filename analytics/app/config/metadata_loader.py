import json
from pathlib import Path
from typing import Any


_METADATA_PATH = Path(__file__).with_name("dataset_metadata.json")


def load_dataset_metadata() -> dict[str, Any]:
    with _METADATA_PATH.open(
        "r",
        encoding="utf-8",
    ) as metadata_file:
        return json.load(metadata_file)