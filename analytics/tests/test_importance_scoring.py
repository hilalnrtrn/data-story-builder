import pytest

from app.models.insight import (
    Insight,
    InsightDirection,
    InsightType,
    PeriodGranularity,
)
from app.services.scoring import apply_importance_score


def _insight(
    insight_type: InsightType,
    *,
    values: dict,
    detection: dict,
    direction: InsightDirection = InsightDirection.UP,
) -> Insight:
    return Insight(
        id=f"IMPORTANCE-{insight_type.value}",
        analysisId="DAY6-IMPORTANCE",
        type=insight_type,
        metric="Revenue",
        periodGranularity=PeriodGranularity.MONTH,
        period={"current": "2025-06"},
        direction=direction,
        values=values,
        detection=detection,
    )


def test_scores_change_magnitude():
    insight = _insight(
        InsightType.CHANGE,
        values={"percentageChange": 10.0},
        detection={"minimumPercentageChange": 5.0},
    )

    result = apply_importance_score(insight)

    assert result is insight
    assert result.importance_breakdown == {"magnitude": 0.5}
    assert result.importance == 0.5


def test_clamps_large_change_at_one():
    insight = _insight(
        InsightType.CHANGE,
        values={"percentageChange": -25.0},
        detection={"minimumPercentageChange": 5.0},
    )

    result = apply_importance_score(insight)

    assert result.importance_breakdown["magnitude"] == 1.0
    assert result.importance == 1.0


def test_scores_trend_magnitude_and_persistence():
    insight = _insight(
        InsightType.TREND,
        values={"startValue": 100, "endValue": 120},
        detection={"persistenceRatio": 0.5},
    )

    result = apply_importance_score(insight)

    assert result.importance_breakdown == {
        "magnitude": 1.0,
        "persistence": 0.5,
    }
    assert result.importance == 0.8


def test_rejects_zero_trend_start_value():
    insight = _insight(
        InsightType.TREND,
        values={"startValue": 0, "endValue": 100},
        detection={"persistenceRatio": 0.8},
    )

    with pytest.raises(ValueError):
        apply_importance_score(insight)


def test_scores_high_anomaly():
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

    result = apply_importance_score(insight)

    assert result.importance_breakdown == {
        "deviationStrength": 0.5,
    }
    assert result.importance == 0.5


def test_scores_low_anomaly():
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

    result = apply_importance_score(insight)

    assert result.importance_breakdown == {
        "deviationStrength": 0.5,
    }
    assert result.importance == 0.5


def test_scores_contribution_strength():
    insight = _insight(
        InsightType.CONTRIBUTION,
        values={"contributionShare": 0.7},
        detection={},
    )

    result = apply_importance_score(insight)

    assert result.importance_breakdown == {
        "contributionStrength": 0.7,
    }
    assert result.importance == 0.7


def test_clamps_contribution_without_mutating_source_share():
    insight = _insight(
        InsightType.CONTRIBUTION,
        values={"contributionShare": 1.4},
        detection={},
    )

    result = apply_importance_score(insight)

    assert result.importance == 1.0
    assert result.values["contributionShare"] == 1.4


def test_scores_contrast_gap_strength():
    insight = _insight(
        InsightType.CONTRAST,
        values={"differencePercentagePoints": 20.0},
        detection={"minimumPercentagePointGap": 10.0},
    )

    result = apply_importance_score(insight)

    assert result.importance_breakdown == {
        "gapStrength": 0.5,
    }
    assert result.importance == 0.5


def test_clamps_large_contrast_at_one():
    insight = _insight(
        InsightType.CONTRAST,
        values={"differencePercentagePoints": 50.0},
        detection={"minimumPercentagePointGap": 10.0},
    )

    result = apply_importance_score(insight)

    assert result.importance_breakdown["gapStrength"] == 1.0
    assert result.importance == 1.0


def test_all_components_remain_within_unit_interval():
    insight = _insight(
        InsightType.CONTRIBUTION,
        values={"contributionShare": -2.0},
        detection={},
    )

    result = apply_importance_score(insight)

    assert all(
        0.0 <= value <= 1.0
        for value in result.importance_breakdown.values()
    )
    assert 0.0 <= result.importance <= 1.0


def test_rejects_unsupported_insight_type():
    insight = Insight.model_construct(
        id="IMPORTANCE-UNSUPPORTED",
        analysis_id="DAY6-IMPORTANCE",
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
        apply_importance_score(insight)


def test_does_not_change_existing_confidence_fields():
    insight = _insight(
        InsightType.CONTRIBUTION,
        values={"contributionShare": 0.7},
        detection={},
    )
    insight.confidence = 0.91
    insight.confidence_breakdown = {
        "dataQuality": 1.0,
        "sampleSufficiency": 1.0,
        "signalStrength": 0.7,
        "consistency": 1.0,
    }

    apply_importance_score(insight)

    assert insight.confidence == 0.91
    assert insight.confidence_breakdown == {
        "dataQuality": 1.0,
        "sampleSufficiency": 1.0,
        "signalStrength": 0.7,
        "consistency": 1.0,
    }
