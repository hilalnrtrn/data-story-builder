import json
from pathlib import Path

from app.config.insight_config_loader import load_insight_config


EXPECTED_REVENUE_REQUIREMENTS = [
    {
        "field": "CompetitorPrice",
        "reason": (
            "Competitor pricing may affect interpretation of Revenue "
            "movements."
        ),
    },
    {
        "field": "UnitPrice",
        "reason": (
            "AverageOrderValue growth does not establish that individual "
            "selling prices increased."
        ),
    },
    {
        "field": "PricingChange",
        "reason": "Explicit pricing policy changes are unavailable.",
    },
]


def test_missing_context_config_has_exact_revenue_requirements():
    config = load_insight_config()

    assert "missingContext" in config
    assert "requirementsByMetric" in config["missingContext"]

    requirements_by_metric = config["missingContext"][
        "requirementsByMetric"
    ]
    assert list(requirements_by_metric) == ["Revenue"]
    assert requirements_by_metric["Revenue"] == (
        EXPECTED_REVENUE_REQUIREMENTS
    )
    assert len(requirements_by_metric["Revenue"]) == 3
    assert [
        requirement["field"]
        for requirement in requirements_by_metric["Revenue"]
    ] == [
        "CompetitorPrice",
        "UnitPrice",
        "PricingChange",
    ]


def test_missing_context_requirements_are_not_in_dataset_metadata():
    metadata_path = (
        Path(__file__).parents[1]
        / "app"
        / "config"
        / "dataset_metadata.json"
    )
    with metadata_path.open("r", encoding="utf-8") as metadata_file:
        metadata = json.load(metadata_file)

    assert "missingContext" not in metadata
    assert "requirementsByMetric" not in metadata
