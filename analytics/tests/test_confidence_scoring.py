import pytest

from app.models.insight import (
    Insight,
    InsightDirection,
    InsightType,
    PeriodGranularity,
)
from app.services.scoring import (
    _validate_confidence_weights,
    apply_confidence_score,
)


def _insight(
    insight_type: InsightType,
    *,
    values: dict,
    detection: dict,
    direction: InsightDirection = InsightDirection.UP,
) -> Insight:
    return Insight(
        id=f"CONFIDENCE-{insight_type.value}",
        analysisId="DAY6-CONFIDENCE",
        type=insight_type,
        metric="Revenue",
        periodGranularity=PeriodGranularity.MONTH,
        period={"current": "2025-06"},
        direction=direction,
        values=values,
        detection=detection,
    )


def test_scores_contribution_example():
    insight = _insight(
        InsightType.CONTRIBUTION,
        values={"contributionShare": 0.7},
        detection={},
    )

    result = apply_confidence_score(
        insight,
        data_quality={"score": 100},
    )

    assert result is insight
    assert result.confidence_breakdown == {
        "dataQuality": 1.0,
        "sampleSufficiency": 1.0,
        "signalStrength": 0.7,
        "consistency": 1.0,
    }
    assert result.confidence == 0.91


def test_lower_data_quality_lowers_confidence():
    insight = _insight(
        InsightType.CONTRIBUTION,
        values={"contributionShare": 0.7},
        detection={},
    )

    result = apply_confidence_score(
        insight,
        data_quality={"score": 50},
    )

    assert result.confidence_breakdown["dataQuality"] == 0.5
    assert result.confidence == 0.76


def test_clamps_contribution_signal_above_one():
    insight = _insight(
        InsightType.CONTRIBUTION,
        values={"contributionShare": 1.4},
        detection={},
    )

    result = apply_confidence_score(
        insight,
        data_quality={"score": 100},
    )

    assert result.confidence_breakdown["signalStrength"] == 1.0
    assert result.confidence == 1.0


def test_scores_change_relative_to_detection_threshold():
    insight = _insight(
        InsightType.CHANGE,
        values={"percentageChange": -5.0},
        detection={"minimumPercentageChange": 5.0},
        direction=InsightDirection.DOWN,
    )

    result = apply_confidence_score(
        insight,
        data_quality={"score": 100},
    )

    assert result.confidence_breakdown["signalStrength"] == 0.5
    assert result.confidence == 0.85


def test_scores_trend_sample_and_persistence_components():
    insight = _insight(
        InsightType.TREND,
        values={"periodCount": 3},
        detection={"persistenceRatio": 0.75},
    )

    result = apply_confidence_score(
        insight,
        data_quality={"score": 100},
    )

    assert result.confidence_breakdown == {
        "dataQuality": 1.0,
        "sampleSufficiency": 0.5,
        "signalStrength": 0.75,
        "consistency": 0.75,
    }
    assert result.confidence == 0.775


def test_scores_high_anomaly_excess_relative_to_iqr():
    insight = _insight(
        InsightType.ANOMALY,
        values={
            "observed": 150,
            "lowerBound": 50,
            "upperBound": 130,
            "iqr": 40,
        },
        detection={},
        direction=InsightDirection.HIGH,
    )

    result = apply_confidence_score(
        insight,
        data_quality={"score": 100},
    )

    assert result.confidence_breakdown["signalStrength"] == 0.5
    assert result.confidence == 0.85


def test_scores_low_anomaly_excess_relative_to_iqr():
    insight = _insight(
        InsightType.ANOMALY,
        values={
            "observed": 70,
            "lowerBound": 90,
            "upperBound": 170,
            "iqr": 40,
        },
        detection={},
        direction=InsightDirection.LOW,
    )

    result = apply_confidence_score(
        insight,
        data_quality={"score": 100},
    )

    assert result.confidence_breakdown["signalStrength"] == 0.5
    assert result.confidence == 0.85


def test_scores_contrast_relative_to_detection_threshold():
    insight = _insight(
        InsightType.CONTRAST,
        values={"differencePercentagePoints": 10.0},
        detection={"minimumPercentagePointGap": 10.0},
    )

    result = apply_confidence_score(
        insight,
        data_quality={"score": 100},
    )

    assert result.confidence_breakdown["signalStrength"] == 0.5
    assert result.confidence == 0.85


def test_all_outputs_remain_within_unit_interval():
    insight = _insight(
        InsightType.CONTRIBUTION,
        values={"contributionShare": -2.0},
        detection={},
    )

    result = apply_confidence_score(
        insight,
        data_quality={"score": 150},
    )

    assert all(
        0.0 <= value <= 1.0
        for value in result.confidence_breakdown.values()
    )
    assert 0.0 <= result.confidence <= 1.0


@pytest.mark.parametrize(
    "data_quality",
    [
        {},
        {"score": "100"},
    ],
)
def test_rejects_missing_or_non_numeric_data_quality(data_quality):
    insight = _insight(
        InsightType.CONTRIBUTION,
        values={"contributionShare": 0.7},
        detection={},
    )

    with pytest.raises(ValueError):
        apply_confidence_score(
            insight,
            data_quality=data_quality,
        )


@pytest.mark.parametrize(
    "weights",
    [
        {
            "dataQuality": 0.3,
            "sampleSufficiency": 0.2,
            "signalStrength": 0.3,
        },
        {
            "dataQuality": 0.3,
            "sampleSufficiency": 0.2,
            "signalStrength": 0.3,
            "consistency": 0.3,
        },
        {
            "dataQuality": 0.3,
            "sampleSufficiency": 0.2,
            "signalStrength": "0.3",
            "consistency": 0.2,
        },
    ],
)
def test_rejects_invalid_confidence_weights(weights):
    with pytest.raises(ValueError):
        _validate_confidence_weights(weights)


def test_rejects_unsupported_insight_type():
    insight = Insight.model_construct(
        id="CONFIDENCE-UNSUPPORTED",
        analysis_id="DAY6-CONFIDENCE",
        type="UNSUPPORTED",
        metric="Revenue",
        period_granularity="MONTH",
        period={"current": "2025-06"},
        direction="UP",
        values={},
        detection={},
        evidence=[],
    )

    with pytest.raises(ValueError):
        apply_confidence_score(
            insight,
            data_quality={"score": 100},
        )
