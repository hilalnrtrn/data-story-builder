from pathlib import Path

import pytest

from app.services.ingestion import read_dataset
from app.services.insight_engine import generate_insights
from app.services.preparation import prepare_dataset


ROOT_DIR = Path(__file__).resolve().parents[2]
SAMPLE_DATA_PATH = ROOT_DIR / "sample-data" / "sales_demo_clean.csv"


def test_pipeline_generates_both_controlled_discount_changes() -> None:
    dataframe = read_dataset(
        file_bytes=SAMPLE_DATA_PATH.read_bytes(),
        file_name=SAMPLE_DATA_PATH.name,
    )
    prepared_dataframe, _ = prepare_dataset(dataframe)
    insights = generate_insights(
        prepared_dataframe,
        analysis_id="DAY8-BUSINESS-RELEVANCE-PREREQUISITE",
        file_name=SAMPLE_DATA_PATH.name,
        data_quality={"score": 100},
    )

    discount_changes = [
        insight
        for insight in insights
        if insight.metric == "Discount"
        and insight.type == "CHANGE"
        and insight.dimension is None
        and insight.segment is None
    ]
    discount_by_period = {
        (
            insight.period.get("previous"),
            insight.period.get("current"),
        ): insight
        for insight in discount_changes
    }

    assert len(discount_changes) == 2
    assert set(discount_by_period) == {
        ("2025-05", "2025-06"),
        ("2025-08", "2025-09"),
    }

    september_change = discount_by_period[("2025-08", "2025-09")]
    assert september_change.values["previous"] == pytest.approx(0.10)
    assert september_change.values["current"] == pytest.approx(0.18)
    assert september_change.values["absoluteChange"] == pytest.approx(0.08)
    assert september_change.values["percentageChange"] == pytest.approx(80.0)
    assert september_change.direction == "UP"
    assert september_change.detection["aggregation"] == "AVG"
    assert september_change.confidence is not None
    assert 0.0 <= september_change.confidence <= 1.0
    assert september_change.importance is not None
    assert 0.0 <= september_change.importance <= 1.0
