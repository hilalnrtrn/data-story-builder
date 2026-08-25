import json
import math
from pathlib import Path

from app.services.ingestion import read_dataset
from app.services.insight_engine import generate_insights
from app.services.insight_integrity import (
    check_trend_candidate_outlier_dependency,
)
from app.services.preparation import prepare_dataset


ROOT_DIR = Path(__file__).resolve().parents[2]
SAMPLE_DATA_PATH = ROOT_DIR / "sample-data" / "sales_demo_clean.csv"
GOLDEN_TRUTH_PATH = ROOT_DIR / "tests" / "golden" / "expected_results.json"
ANALYSIS_ID = "DAY9-OUTLIER-GOLDEN"


def test_bluetooth_speaker_outlier_dependency_guards_against_false_trend() -> None:
    with GOLDEN_TRUTH_PATH.open("r", encoding="utf-8") as golden_file:
        golden_truth = json.load(golden_file)

    expected = next(
        finding
        for finding in golden_truth["expectedIntegrityFindings"]
        if finding["type"] == "OUTLIER_DEPENDENCY"
        and finding["metric"] == "Revenue"
        and finding["dimension"] == "Product"
        and finding["segment"] == "Bluetooth Speaker"
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

    bluetooth_trends = [
        insight
        for insight in insights
        if insight.type == "TREND"
        and insight.metric == expected["metric"]
        and insight.dimension == expected["dimension"]
        and insight.segment == expected["segment"]
    ]
    assert bluetooth_trends == []

    bluetooth_anomalies = [
        insight
        for insight in insights
        if insight.type == "ANOMALY"
        and insight.metric == expected["metric"]
        and insight.dimension == expected["dimension"]
        and insight.segment == expected["segment"]
        and insight.period.get("current") == expected["expectedOutlierPeriod"]
        and insight.direction == "HIGH"
    ]
    assert len(bluetooth_anomalies) == 1

    result = check_trend_candidate_outlier_dependency(
        prepared_dataframe,
        metric=expected["metric"],
        dimension=expected["dimension"],
        segment=expected["segment"],
        aggregation="SUM",
        period_start="2025-01",
        period_end="2025-12",
    )

    assert result is not None
    assert result.detected is expected["outlierExpected"] is True
    assert result.outlier_period == expected["expectedOutlierPeriod"]
    assert result.level == expected["expectedOutlierDependency"] == "HIGH"
    assert result.original_statistic is not None
    assert result.adjusted_statistic is not None
    assert math.isfinite(result.original_statistic)
    assert math.isfinite(result.adjusted_statistic)
    assert abs(result.adjusted_statistic) < abs(result.original_statistic)
    assert expected["expectedSustainedTrend"] is False
    assert bluetooth_trends == []
