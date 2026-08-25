import json
import math
from pathlib import Path

from app.config.insight_config_loader import load_insight_config
from app.services.ingestion import read_dataset
from app.services.insight_engine import generate_insights
from app.services.insight_integrity import check_one_off_effect
from app.services.preparation import prepare_dataset


ROOT_DIR = Path(__file__).resolve().parents[2]
SAMPLE_DATA_PATH = ROOT_DIR / "sample-data" / "sales_demo_clean.csv"
GOLDEN_TRUTH_PATH = ROOT_DIR / "tests" / "golden" / "expected_results.json"
ANALYSIS_ID = "DAY9-ONE-OFF-GOLDEN"


def test_smart_watch_anomaly_has_golden_high_one_off_risk() -> None:
    with GOLDEN_TRUTH_PATH.open("r", encoding="utf-8") as golden_file:
        golden_truth = json.load(golden_file)

    expected = next(
        finding
        for finding in golden_truth["expectedIntegrityFindings"]
        if finding["type"] == "ONE_OFF_EFFECT"
        and finding["metric"] == "Revenue"
        and finding["dimension"] == "Product"
        and finding["segment"] == "Smart Watch"
    )

    dataframe = read_dataset(
        file_bytes=SAMPLE_DATA_PATH.read_bytes(),
        file_name=SAMPLE_DATA_PATH.name,
    )
    prepared_dataframe, _ = prepare_dataset(dataframe)
    insights = generate_insights(
        prepared_dataframe,
        analysis_id=ANALYSIS_ID,
        file_name=SAMPLE_DATA_PATH.name,
    )

    anomaly_matches = [
        insight
        for insight in insights
        if insight.type == "ANOMALY"
        and insight.metric == expected["metric"]
        and insight.dimension == expected["dimension"]
        and insight.segment == expected["segment"]
        and insight.period.get("current") == expected["eventPeriod"]
    ]
    assert len(anomaly_matches) == 1
    smart_watch_anomaly = anomaly_matches[0]
    assert smart_watch_anomaly.direction == "HIGH"

    result = check_one_off_effect(
        smart_watch_anomaly,
        prepared_dataframe,
        aggregation="SUM",
    )

    assert result is not None
    assert result.event_period == expected["eventPeriod"]
    assert result.next_period == "2025-07"
    assert result.risk == expected["expectedOneOffRisk"] == "HIGH"
    assert result.reversion_ratio is not None
    assert math.isfinite(result.reversion_ratio)

    config = load_insight_config()
    high_threshold = config["insightIntegrity"]["oneOffEffect"][
        "highReversionRatio"
    ]
    assert result.reversion_ratio >= high_threshold

    assert result.baseline_value is not None
    assert result.event_value is not None
    assert result.next_value is not None
    assert math.isfinite(result.baseline_value)
    assert math.isfinite(result.event_value)
    assert math.isfinite(result.next_value)
    assert result.event_value > result.baseline_value
    assert abs(result.next_value - result.baseline_value) < abs(
        result.event_value - result.baseline_value
    )
    assert expected["expectedSustainedTrend"] is False
