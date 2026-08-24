import json
from collections import Counter
from pathlib import Path

import pytest

from app.services.ingestion import read_dataset
from app.services.insight_engine import generate_insights
from app.services.preparation import prepare_dataset


ROOT_DIR = Path(__file__).resolve().parents[2]

SAMPLE_DATA_PATH = (
    ROOT_DIR
    / "sample-data"
    / "sales_demo_clean.csv"
)

DATASET_METADATA_PATH = (
    ROOT_DIR
    / "analytics"
    / "app"
    / "config"
    / "dataset_metadata.json"
)

GOLDEN_TRUTH_PATH = (
    ROOT_DIR
    / "tests"
    / "golden"
    / "expected_results.json"
)


def _load_json(path: Path) -> dict:
    with path.open(
        "r",
        encoding="utf-8",
    ) as json_file:
        return json.load(json_file)


@pytest.fixture(scope="module")
def prepared_dataframe():
    dataframe = read_dataset(
        file_bytes=SAMPLE_DATA_PATH.read_bytes(),
        file_name=SAMPLE_DATA_PATH.name,
    )

    prepared, _ = prepare_dataset(dataframe)

    return prepared


@pytest.fixture(scope="module")
def unscored_insights(prepared_dataframe):
    return generate_insights(
        prepared_dataframe,
        analysis_id="DAY6-UNSCORED",
        file_name=SAMPLE_DATA_PATH.name,
    )


@pytest.fixture(scope="module")
def scored_insights(prepared_dataframe):
    return generate_insights(
        prepared_dataframe,
        analysis_id="DAY6-SCORED",
        file_name=SAMPLE_DATA_PATH.name,
        data_quality={"score": 100},
    )


def test_generate_insights_remains_backward_compatible(
    unscored_insights,
):
    assert unscored_insights
    assert any(
        insight.type == "CHANGE"
        for insight in unscored_insights
    )


def test_integrated_output_contains_all_five_types(
    scored_insights,
):
    counts = Counter(
        insight.type
        for insight in scored_insights
    )

    print()
    print("=" * 72)
    print("DAY 6 INTEGRATED INSIGHT COUNTS")
    print("=" * 72)

    for insight_type in (
        "CHANGE",
        "TREND",
        "ANOMALY",
        "CONTRIBUTION",
        "CONTRAST",
    ):
        print(f"{insight_type}: {counts[insight_type]}")

    print(f"TOTAL: {len(scored_insights)}")
    print("=" * 72)

    assert set(counts) == {
        "CHANGE",
        "TREND",
        "ANOMALY",
        "CONTRIBUTION",
        "CONTRAST",
    }
    assert all(counts[insight_type] > 0 for insight_type in counts)


def test_data_quality_applies_both_scores(scored_insights):
    assert all(
        insight.confidence is not None
        and insight.importance is not None
        and insight.confidence_breakdown
        and insight.importance_breakdown
        for insight in scored_insights
    )


def test_integrates_scored_return_rate_change(scored_insights):
    return_rate_insights = [
        insight
        for insight in scored_insights
        if insight.metric == "ReturnRate"
    ]

    assert len(return_rate_insights) == 1
    insight = return_rate_insights[0]
    assert insight.type == "CHANGE"
    assert insight.period == {
        "previous": "2025-08",
        "current": "2025-09",
    }
    assert insight.values["previous"] == pytest.approx(0.02)
    assert insight.values["current"] == pytest.approx(0.035)
    assert insight.values["percentageChange"] == pytest.approx(75.0)
    assert insight.values["percentagePointChange"] == pytest.approx(1.5)
    assert insight.confidence is not None
    assert insight.importance is not None
    assert 0.0 <= insight.confidence <= 1.0
    assert 0.0 <= insight.importance <= 1.0


def test_missing_data_quality_leaves_scores_empty(
    unscored_insights,
):
    assert all(
        insight.confidence is None
        and insight.importance is None
        and insight.confidence_breakdown == {}
        and insight.importance_breakdown == {}
        for insight in unscored_insights
    )


def test_integrates_required_marmara_contribution(
    scored_insights,
):
    insight = next(
        candidate
        for candidate in scored_insights
        if candidate.type == "CONTRIBUTION"
        and candidate.metric == "Revenue"
        and candidate.dimension == "Region"
        and candidate.segment == "Marmara"
    )

    assert insight.values["contributionShare"] == 0.7
    assert (
        insight.values["contributorRole"]
        == "PRIMARY_POSITIVE_CONTRIBUTOR"
    )


def test_revenue_still_generates_contribution(scored_insights):
    assert any(
        insight.type == "CONTRIBUTION"
        and insight.metric == "Revenue"
        for insight in scored_insights
    )


def test_integrates_required_region_contrast(scored_insights):
    expected = _load_json(GOLDEN_TRUTH_PATH)[
        "expectedContrasts"
    ][0]

    insight = next(
        candidate
        for candidate in scored_insights
        if candidate.type == "CONTRAST"
        and candidate.metric == "Revenue"
        and candidate.dimension == "Region"
    )

    assert insight.values["subject"] == "Marmara"
    assert insight.values["comparison"] == expected["comparison"]
    assert insight.values["comparisonResult"] == "OUTPERFORMS"


@pytest.mark.parametrize(
    "ineligible_metric",
    ["Returns", "Discount", "StockLevel"],
)
def test_excludes_ineligible_contribution_metrics(
    scored_insights,
    ineligible_metric,
):
    assert not any(
        insight.type == "CONTRIBUTION"
        and insight.metric == ineligible_metric
        for insight in scored_insights
    )


def test_contrast_is_not_parent_change_gated(scored_insights):
    assert not any(
        insight.type == "CHANGE"
        and insight.metric == "Returns"
        for insight in scored_insights
    )
    assert any(
        insight.type == "CONTRAST"
        and insight.metric == "Returns"
        for insight in scored_insights
    )


def test_uses_only_single_metadata_dimensions(scored_insights):
    metadata = _load_json(DATASET_METADATA_PATH)
    dimensions = {
        column_name
        for column_name, column_metadata
        in metadata["columns"].items()
        if column_metadata.get("role") == "DIMENSION"
    }

    assert all(
        insight.dimension is None
        or insight.dimension in dimensions
        for insight in scored_insights
    )
