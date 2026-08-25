import copy

import pytest
import pandas as pd
from pandas.testing import assert_frame_equal
from pydantic import ValidationError

from app.config.insight_config_loader import load_insight_config
from app.models.insight import (
    Insight,
    InsightDirection,
    InsightType,
    PeriodGranularity,
)
from app.models.insight_integrity import (
    ConsistencyCheck,
    ContradictionFinding,
    ContradictionType,
    CounterEvidenceItem,
    InsightIntegrityEvaluation,
    IntegrityCheckStatus,
    IntegrityRiskLevel,
    IntegrityStatus,
    OneOffEffectCheck,
    OutlierDependencyCheck,
)
from app.models.relationship import Relationship, RelationshipType
from app.services.insight_integrity import (
    analyze_insight_integrity,
    build_counter_evidence,
    build_integrity_evaluation,
    build_insight_contradictions,
    build_semantic_contradictions,
    calculate_integrity_score,
    check_change_total_consistency,
    check_contribution_consistency,
    check_one_off_effect,
    check_trend_outlier_dependency,
)


def _insight(
    insight_id: str,
    metric: str,
    direction: InsightDirection,
    *,
    analysis_id: str = "analysis-integrity",
    insight_type: InsightType = InsightType.CHANGE,
    dimension: str | None = None,
    segment: str | None = None,
    period: dict[str, str] | None = None,
    values: dict | None = None,
) -> Insight:
    return Insight(
        id=insight_id,
        analysisId=analysis_id,
        type=insight_type,
        metric=metric,
        dimension=dimension,
        segment=segment,
        periodGranularity=PeriodGranularity.MONTH,
        period=period or {"previous": "2025-08", "current": "2025-09"},
        direction=direction,
        values=values or {},
    )


def _relationship(
    relationship_id: str,
    source_id: str,
    target_id: str,
    *,
    relationship_type: RelationshipType = RelationshipType.COUNTER_SIGNAL,
    reasons: list[str] | None = None,
) -> Relationship:
    return Relationship(
        id=relationship_id,
        analysisId="analysis-integrity",
        sourceInsightId=source_id,
        targetInsightId=target_id,
        type=relationship_type,
        strength=1.0,
        confidence=1.0,
        reasons=reasons or [],
    )


def test_counter_signal_with_primary_source_becomes_counter_evidence() -> None:
    revenue = _insight("revenue", "Revenue", InsightDirection.UP)
    orders = _insight("orders", "Orders", InsightDirection.DOWN)
    relationship = _relationship("counter-1", revenue.id, orders.id)

    evidence = build_counter_evidence(
        revenue,
        [revenue, orders],
        [relationship],
    )

    assert [item.insight_id for item in evidence] == [orders.id]


def test_primary_participation_on_both_relationship_sides_is_handled() -> None:
    revenue = _insight("revenue", "Revenue", InsightDirection.UP)
    orders = _insight("orders", "Orders", InsightDirection.DOWN)
    customers = _insight("customers", "Customers", InsightDirection.DOWN)

    evidence = build_counter_evidence(
        revenue,
        [revenue, orders, customers],
        [
            _relationship("counter-orders", revenue.id, orders.id),
            _relationship("counter-customers", customers.id, revenue.id),
        ],
    )

    assert [item.insight_id for item in evidence] == ["customers", "orders"]


def test_unrelated_relationship_type_is_ignored() -> None:
    revenue = _insight("revenue", "Revenue", InsightDirection.UP)
    orders = _insight("orders", "Orders", InsightDirection.DOWN)

    evidence = build_counter_evidence(
        revenue,
        [revenue, orders],
        [
            _relationship(
                "co-moves-1",
                revenue.id,
                orders.id,
                relationship_type=RelationshipType.CO_MOVES_WITH,
            )
        ],
    )

    assert evidence == []


def test_counter_signal_not_involving_primary_is_ignored() -> None:
    revenue = _insight("revenue", "Revenue", InsightDirection.UP)
    orders = _insight("orders", "Orders", InsightDirection.DOWN)
    customers = _insight("customers", "Customers", InsightDirection.DOWN)

    evidence = build_counter_evidence(
        revenue,
        [revenue, orders, customers],
        [_relationship("counter-1", orders.id, customers.id)],
    )

    assert evidence == []


def test_missing_related_insight_is_ignored_safely() -> None:
    revenue = _insight("revenue", "Revenue", InsightDirection.UP)

    evidence = build_counter_evidence(
        revenue,
        [revenue],
        [_relationship("counter-1", revenue.id, "missing")],
    )

    assert evidence == []


def test_duplicate_relationship_evidence_is_not_returned() -> None:
    revenue = _insight("revenue", "Revenue", InsightDirection.UP)
    orders = _insight("orders", "Orders", InsightDirection.DOWN)
    relationship = _relationship("counter-1", revenue.id, orders.id)

    evidence = build_counter_evidence(
        revenue,
        [revenue, orders],
        [relationship, relationship.model_copy(deep=True)],
    )

    assert len(evidence) == 1


def test_counter_evidence_preserves_required_relationship_and_insight_data() -> None:
    revenue = _insight("revenue", "Revenue", InsightDirection.UP)
    orders = _insight("orders", "Orders", InsightDirection.DOWN)
    reasons = ["Same period", "Opposite movement"]
    relationship = _relationship(
        "counter-1",
        revenue.id,
        orders.id,
        reasons=reasons,
    )

    evidence = build_counter_evidence(
        revenue,
        [revenue, orders],
        [relationship],
    )

    assert evidence[0].model_dump(by_alias=True) == {
        "insightId": orders.id,
        "relationshipId": relationship.id,
        "metric": orders.metric,
        "direction": "DOWN",
        "reasons": reasons,
    }


def test_integrity_evaluation_serializes_with_agreed_aliases() -> None:
    evaluation = InsightIntegrityEvaluation(
        insightId="revenue",
        status=IntegrityStatus.PASS_WITH_WARNINGS,
        counterEvidence=[
            CounterEvidenceItem(
                insightId="orders",
                relationshipId="counter-1",
                metric="Orders",
                direction=InsightDirection.DOWN,
                reasons=["Opposite movement"],
            )
        ],
        contradictions=[
            ContradictionFinding(
                type=ContradictionType.INSIGHT_CONTRADICTION,
                code="CONTRADICTION",
                relatedInsightId="orders",
                reason="Conflicting finding.",
            )
        ],
        outlierCheck=OutlierDependencyCheck(
            level=IntegrityRiskLevel.LOW,
            detected=False,
            statisticName=None,
            originalStatistic=None,
            adjustedStatistic=None,
            outlierPeriod=None,
            reason=None,
        ),
        oneOffCheck=OneOffEffectCheck(
            risk=IntegrityRiskLevel.NONE,
            eventPeriod=None,
            nextPeriod=None,
            baselineValue=None,
            eventValue=None,
            nextValue=None,
            reversionRatio=None,
            reason=None,
        ),
        consistencyChecks=[
            ConsistencyCheck(
                code="TOTAL_MATCH",
                status=IntegrityCheckStatus.PASS,
                expectedValue=10.0,
                actualValue=10.0,
                difference=0.0,
                tolerance=0.01,
                reason="Values match.",
            )
        ],
        integrityScore=0.8,
        storyEligible=True,
        requiresQualification=True,
        reasons=["Counter evidence requires qualification."],
    )

    assert evaluation.model_dump(by_alias=True) == {
        "insightId": "revenue",
        "status": "PASS_WITH_WARNINGS",
        "counterEvidence": [
            {
                "insightId": "orders",
                "relationshipId": "counter-1",
                "metric": "Orders",
                "direction": "DOWN",
                "reasons": ["Opposite movement"],
            }
        ],
        "contradictions": [
            {
                "type": "INSIGHT_CONTRADICTION",
                "code": "CONTRADICTION",
                "relatedInsightId": "orders",
                "reason": "Conflicting finding.",
            }
        ],
        "outlierCheck": {
            "level": "LOW",
            "detected": False,
            "statisticName": None,
            "originalStatistic": None,
            "adjustedStatistic": None,
            "outlierPeriod": None,
            "reason": None,
        },
        "oneOffCheck": {
            "risk": "NONE",
            "eventPeriod": None,
            "nextPeriod": None,
            "baselineValue": None,
            "eventValue": None,
            "nextValue": None,
            "reversionRatio": None,
            "reason": None,
        },
        "consistencyChecks": [
            {
                "code": "TOTAL_MATCH",
                "status": "PASS",
                "expectedValue": 10.0,
                "actualValue": 10.0,
                "difference": 0.0,
                "tolerance": 0.01,
                "reason": "Values match.",
            }
        ],
        "integrityScore": 0.8,
        "integrityBreakdown": {},
        "storyEligible": True,
        "requiresQualification": True,
        "reasons": ["Counter evidence requires qualification."],
    }


@pytest.mark.parametrize("score", [-0.01, 1.01, float("nan")])
def test_integrity_evaluation_rejects_invalid_score(score: float) -> None:
    with pytest.raises(ValidationError):
        InsightIntegrityEvaluation(
            insightId="revenue",
            status=IntegrityStatus.PASS,
            integrityScore=score,
            storyEligible=True,
            requiresQualification=False,
        )


@pytest.mark.parametrize(
    ("primary_direction", "related_direction"),
    [
        (InsightDirection.UP, InsightDirection.DOWN),
        (InsightDirection.HIGH, InsightDirection.LOW),
    ],
)
def test_same_claim_with_opposing_direction_is_insight_contradiction(
    primary_direction: InsightDirection,
    related_direction: InsightDirection,
) -> None:
    primary = _insight("primary", "Revenue", primary_direction)
    related = _insight("related", "Revenue", related_direction)

    findings = build_insight_contradictions(primary, [primary, related])

    assert [finding.model_dump(by_alias=True) for finding in findings] == [
        {
            "type": "INSIGHT_CONTRADICTION",
            "code": "OPPOSING_INSIGHT_DIRECTION",
            "relatedInsightId": "related",
            "reason": (
                f"Insight related reports direction {related_direction.value}, "
                "opposing primary insight primary direction "
                f"{primary_direction.value} for the same claim."
            ),
        }
    ]


def test_opposite_directions_on_different_metrics_are_not_contradiction() -> None:
    primary = _insight("revenue", "Revenue", InsightDirection.UP)
    orders = _insight("orders", "Orders", InsightDirection.DOWN)

    assert build_insight_contradictions(primary, [orders]) == []


def test_opposite_directions_in_different_periods_are_not_contradiction() -> None:
    primary = _insight("primary", "Revenue", InsightDirection.UP)
    related = _insight(
        "related",
        "Revenue",
        InsightDirection.DOWN,
        period={"previous": "2025-07", "current": "2025-08"},
    )

    assert build_insight_contradictions(primary, [related]) == []


def test_different_insight_types_are_not_contradiction() -> None:
    primary = _insight("primary", "Revenue", InsightDirection.UP)
    related = _insight(
        "related",
        "Revenue",
        InsightDirection.DOWN,
        insight_type=InsightType.TREND,
    )

    assert build_insight_contradictions(primary, [related]) == []


@pytest.mark.parametrize(
    ("dimension", "segment"),
    [("Region", None), ("Region", "Marmara")],
)
def test_different_scope_or_segment_is_not_contradiction(
    dimension: str,
    segment: str | None,
) -> None:
    primary = _insight("primary", "Revenue", InsightDirection.UP)
    related = _insight(
        "related",
        "Revenue",
        InsightDirection.DOWN,
        dimension=dimension,
        segment=segment,
    )

    assert build_insight_contradictions(primary, [related]) == []


def test_insight_contradictions_are_deterministic_and_duplicate_free() -> None:
    primary = _insight("primary", "Revenue", InsightDirection.UP)
    first = _insight("a-related", "Revenue", InsightDirection.DOWN)
    second = _insight("b-related", "Revenue", InsightDirection.DOWN)

    findings = build_insight_contradictions(
        primary,
        [second, first, second.model_copy(deep=True), primary],
    )

    assert [finding.related_insight_id for finding in findings] == [
        "a-related",
        "b-related",
    ]


@pytest.mark.parametrize(
    ("percentage_change", "direction"),
    [(10.0, InsightDirection.DOWN), (-10.0, InsightDirection.UP)],
)
def test_change_direction_value_mismatch_is_semantic_contradiction(
    percentage_change: float,
    direction: InsightDirection,
) -> None:
    insight = _insight(
        "change",
        "Revenue",
        direction,
        values={"percentageChange": percentage_change},
    )

    findings = build_semantic_contradictions(insight)

    assert len(findings) == 1
    assert findings[0].type == "SEMANTIC_CONTRADICTION"
    assert findings[0].code == "CHANGE_DIRECTION_VALUE_MISMATCH"
    assert findings[0].related_insight_id is None


@pytest.mark.parametrize(
    ("percentage_change", "direction"),
    [(10.0, InsightDirection.UP), (-10.0, InsightDirection.DOWN)],
)
def test_matching_change_direction_is_not_semantic_contradiction(
    percentage_change: float,
    direction: InsightDirection,
) -> None:
    insight = _insight(
        "change",
        "Revenue",
        direction,
        values={"percentageChange": percentage_change},
    )

    assert build_semantic_contradictions(insight) == []


@pytest.mark.parametrize(
    ("percentage_change", "direction", "insight_type"),
    [
        (0.0, InsightDirection.DOWN, InsightType.CHANGE),
        (10.0, InsightDirection.STABLE, InsightType.CHANGE),
        (10.0, InsightDirection.DOWN, InsightType.TREND),
    ],
)
def test_zero_stable_and_non_change_inputs_are_not_semantic_contradictions(
    percentage_change: float,
    direction: InsightDirection,
    insight_type: InsightType,
) -> None:
    insight = _insight(
        "insight",
        "Revenue",
        direction,
        insight_type=insight_type,
        values={"percentageChange": percentage_change},
    )

    assert build_semantic_contradictions(insight) == []


@pytest.mark.parametrize(
    "percentage_change",
    [None, "10", float("nan"), float("inf"), float("-inf")],
)
def test_missing_invalid_or_non_finite_percentage_change_is_ignored(
    percentage_change: object,
) -> None:
    values = (
        {}
        if percentage_change is None
        else {"percentageChange": percentage_change}
    )
    insight = _insight(
        "change",
        "Revenue",
        InsightDirection.DOWN,
        values=values,
    )

    assert build_semantic_contradictions(insight) == []


def _trend_insight(
    direction: InsightDirection = InsightDirection.UP,
    *,
    period_end: str = "2025-06",
) -> Insight:
    return _insight(
        "trend",
        "Revenue",
        direction,
        insight_type=InsightType.TREND,
        dimension="Product",
        segment="Widget",
        period={"start": "2025-01", "end": period_end},
    )


def _monthly_dataframe(values: list[float]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Date": pd.date_range("2025-01-01", periods=len(values), freq="MS"),
            "Product": ["Widget"] * len(values),
            "Revenue": values,
        }
    )


def test_outlier_dependency_is_not_applicable_to_non_trend() -> None:
    insight = _insight(
        "change",
        "Revenue",
        InsightDirection.UP,
        dimension="Product",
        segment="Widget",
    )

    assert check_trend_outlier_dependency(
        insight,
        _monthly_dataframe([10, 11, 12, 13, 14, 100]),
        "SUM",
    ) is None


def test_strong_single_outlier_creating_apparent_trend_is_high_risk() -> None:
    result = check_trend_outlier_dependency(
        _trend_insight(),
        _monthly_dataframe([10, 11, 10, 11, 10, 100]),
        "SUM",
    )

    assert result is not None
    assert result.detected is True
    assert result.level == "HIGH"
    assert result.outlier_period == "2025-06"


def test_persistent_trend_without_outlier_has_no_dependency() -> None:
    result = check_trend_outlier_dependency(
        _trend_insight(),
        _monthly_dataframe([10, 11, 12, 13, 14, 15]),
        "AVG",
    )

    assert result is not None
    assert result.detected is False
    assert result.level == "NONE"
    assert result.original_statistic == pytest.approx(1.0)
    assert result.adjusted_statistic == pytest.approx(1.0)


def test_detected_outlier_with_limited_slope_impact_is_low_risk() -> None:
    result = check_trend_outlier_dependency(
        _trend_insight(),
        _monthly_dataframe([10, 11, 12, 13, 23, 15]),
        "SUM",
    )

    assert result is not None
    assert result.detected is True
    assert result.level == "LOW"
    assert result.outlier_period == "2025-05"


def test_zero_iqr_is_handled_safely() -> None:
    result = check_trend_outlier_dependency(
        _trend_insight(),
        _monthly_dataframe([10, 10, 10, 10, 10, 10]),
        "SUM",
    )

    assert result is not None
    assert result.detected is False
    assert result.level == "NONE"
    assert result.original_statistic == pytest.approx(0.0)
    assert result.adjusted_statistic == pytest.approx(0.0)


def test_dominant_outlier_selection_is_deterministic() -> None:
    values = [100, 11, 12, 13, 14, 15, 16, 17, 18, 200]
    dataframe = _monthly_dataframe(values)
    insight = _trend_insight(period_end="2025-10")

    first = check_trend_outlier_dependency(insight, dataframe, "SUM")
    second = check_trend_outlier_dependency(insight, dataframe, "SUM")

    assert first is not None
    assert second is not None
    assert first.outlier_period == "2025-10"
    assert first == second


def test_outlier_dependency_does_not_mutate_dataframe() -> None:
    dataframe = _monthly_dataframe([10, 11, 12, 13, 23, 15])
    original = dataframe.copy(deep=True)

    check_trend_outlier_dependency(_trend_insight(), dataframe, "SUM")

    assert_frame_equal(dataframe, original)


def test_outlier_dependency_preserves_statistics_and_aliases() -> None:
    result = check_trend_outlier_dependency(
        _trend_insight(),
        _monthly_dataframe([10, 11, 12, 13, 23, 15]),
        "SUM",
    )

    assert result is not None
    serialized = result.model_dump(by_alias=True)
    assert serialized["level"] == "LOW"
    assert serialized["detected"] is True
    assert serialized["statisticName"] == "TREND_SLOPE"
    assert serialized["originalStatistic"] == pytest.approx(1.7714285714)
    assert serialized["adjustedStatistic"] == pytest.approx(1.2)
    assert serialized["outlierPeriod"] == "2025-05"
    assert serialized["reason"]


def _anomaly_insight() -> Insight:
    return _insight(
        "anomaly",
        "Revenue",
        InsightDirection.HIGH,
        insight_type=InsightType.ANOMALY,
        dimension="Product",
        segment="Widget",
        period={"current": "2025-06"},
    )


def _repeated_monthly_dataframe(values: list[float]) -> pd.DataFrame:
    dates = pd.date_range("2025-01-01", periods=len(values), freq="MS")
    return pd.DataFrame(
        {
            "Date": [date for date in dates for _ in range(2)],
            "Product": ["Widget"] * (len(values) * 2),
            "Revenue": [value for value in values for _ in range(2)],
        }
    )


def test_one_off_effect_is_not_applicable_to_non_anomaly() -> None:
    assert check_one_off_effect(
        _trend_insight(),
        _monthly_dataframe([10, 10, 10, 10, 10, 100, 10]),
        "SUM",
    ) is None


def test_strong_spike_returning_to_baseline_is_high_one_off_risk() -> None:
    result = check_one_off_effect(
        _anomaly_insight(),
        _monthly_dataframe([10, 10, 10, 10, 10, 100, 11]),
        "SUM",
    )

    assert result is not None
    assert result.risk == "HIGH"
    assert result.reversion_ratio == pytest.approx(89 / 90)


def test_sustained_elevated_level_has_no_one_off_risk() -> None:
    result = check_one_off_effect(
        _anomaly_insight(),
        _monthly_dataframe([10, 10, 10, 10, 10, 100, 95]),
        "SUM",
    )

    assert result is not None
    assert result.risk == "NONE"
    assert result.reversion_ratio == pytest.approx(5 / 90)


def test_partial_reversion_has_medium_one_off_risk() -> None:
    result = check_one_off_effect(
        _anomaly_insight(),
        _monthly_dataframe([10, 10, 10, 10, 10, 100, 46]),
        "SUM",
    )

    assert result is not None
    assert result.risk == "MEDIUM"
    assert result.reversion_ratio == pytest.approx(0.6)


def test_one_off_effect_requires_next_period() -> None:
    assert check_one_off_effect(
        _anomaly_insight(),
        _monthly_dataframe([10, 10, 10, 10, 10, 100]),
        "SUM",
    ) is None


def test_zero_event_deviation_is_handled_safely() -> None:
    result = check_one_off_effect(
        _anomaly_insight(),
        _monthly_dataframe([10, 10, 10, 10, 10, 10, 20]),
        "SUM",
    )

    assert result is not None
    assert result.risk == "NONE"
    assert result.reversion_ratio == 0.0


@pytest.mark.parametrize(
    ("aggregation", "expected_baseline", "expected_event", "expected_next"),
    [
        ("SUM", 20.0, 200.0, 20.0),
        ("AVG", 10.0, 100.0, 10.0),
    ],
)
def test_one_off_effect_supports_sum_and_avg(
    aggregation: str,
    expected_baseline: float,
    expected_event: float,
    expected_next: float,
) -> None:
    result = check_one_off_effect(
        _anomaly_insight(),
        _repeated_monthly_dataframe([10, 10, 10, 10, 10, 100, 10]),
        aggregation,
    )

    assert result is not None
    assert result.risk == "HIGH"
    assert result.baseline_value == expected_baseline
    assert result.event_value == expected_event
    assert result.next_value == expected_next


def test_one_off_effect_does_not_mutate_dataframe() -> None:
    dataframe = _monthly_dataframe([10, 10, 10, 10, 10, 100, 10])
    original = dataframe.copy(deep=True)

    check_one_off_effect(_anomaly_insight(), dataframe, "SUM")

    assert_frame_equal(dataframe, original)


def test_one_off_effect_preserves_fields_and_aliases() -> None:
    result = check_one_off_effect(
        _anomaly_insight(),
        _monthly_dataframe([10, 10, 10, 10, 10, 100, 11]),
        "SUM",
    )

    assert result is not None
    assert result.model_dump(by_alias=True) == {
        "risk": "HIGH",
        "eventPeriod": "2025-06",
        "nextPeriod": "2025-07",
        "baselineValue": 10.0,
        "eventValue": 100.0,
        "nextValue": 11.0,
        "reversionRatio": pytest.approx(89 / 90),
        "reason": result.reason,
    }


def _change_insight(**overrides) -> Insight:
    values = {
        "previous": 30.0,
        "current": 40.0,
        "absoluteChange": 10.0,
        "percentageChange": 33.333333,
    }
    values.update(overrides.pop("values", {}))
    return _insight(
        "change-total",
        overrides.pop("metric", "Revenue"),
        InsightDirection.UP,
        analysis_id=overrides.pop("analysis_id", "analysis-integrity"),
        period=overrides.pop(
            "period",
            {"previous": "2025-01", "current": "2025-02"},
        ),
        values=values,
        **overrides,
    )


def _contribution_insight(**value_overrides) -> Insight:
    values = {
        "totalPreviousValue": 30.0,
        "totalCurrentValue": 40.0,
        "totalAbsoluteChange": 10.0,
        "contributionShare": 0.5,
    }
    values.update(value_overrides)
    return _insight(
        "contribution",
        "Revenue",
        InsightDirection.UP,
        insight_type=InsightType.CONTRIBUTION,
        dimension="Region",
        segment="North",
        period={"previous": "2025-01", "current": "2025-02"},
        values=values,
    )


def _reconciliation_dataframe(
    *,
    ungrouped_value: float | None = None,
) -> pd.DataFrame:
    rows = [
        ("2025-01-01", "North", 10.0),
        ("2025-01-02", "South", 20.0),
        ("2025-02-01", "North", 15.0),
        ("2025-02-02", "South", 25.0),
    ]
    if ungrouped_value is not None:
        rows.append(("2025-02-03", None, ungrouped_value))
    return pd.DataFrame(rows, columns=["Date", "Region", "Revenue"]).assign(
        Date=lambda frame: pd.to_datetime(frame["Date"])
    )


def test_exact_change_total_vs_region_reconciliation_passes() -> None:
    result = check_change_total_consistency(
        _change_insight(),
        _reconciliation_dataframe(),
        dimension="Region",
        aggregation="SUM",
    )

    assert result is not None
    assert result.model_dump(by_alias=True) == {
        "code": "TOTAL_VS_DIMENSION_RECONCILIATION",
        "status": "PASS",
        "expectedValue": 40.0,
        "actualValue": 40.0,
        "difference": 0.0,
        "tolerance": 1e-6,
        "reason": result.reason,
    }


def test_change_total_difference_inside_tolerance_passes() -> None:
    result = check_change_total_consistency(
        _change_insight(),
        _reconciliation_dataframe(ungrouped_value=5e-7),
        dimension="Region",
        aggregation="SUM",
    )

    assert result is not None
    assert result.status == "PASS"
    assert result.difference == pytest.approx(-5e-7)


def test_meaningful_change_total_mismatch_fails() -> None:
    result = check_change_total_consistency(
        _change_insight(),
        _reconciliation_dataframe(ungrouped_value=5.0),
        dimension="Region",
        aggregation="SUM",
    )

    assert result is not None
    assert result.status == "FAIL"
    assert result.expected_value == 45.0
    assert result.actual_value == 40.0
    assert result.difference == -5.0


def test_change_total_consistency_is_not_applicable_to_non_change() -> None:
    assert check_change_total_consistency(
        _contribution_insight(),
        _reconciliation_dataframe(),
        dimension="Region",
        aggregation="SUM",
    ) is None


def test_change_total_consistency_rejects_unsupported_aggregation() -> None:
    assert check_change_total_consistency(
        _change_insight(),
        _reconciliation_dataframe(),
        dimension="Region",
        aggregation="AVG",
    ) is None


def test_valid_contribution_totals_pass() -> None:
    result = check_contribution_consistency(
        _contribution_insight(),
        _change_insight(),
    )

    assert result is not None
    assert result.status == "PASS"
    assert result.code == "CONTRIBUTION_TOTAL_RECONCILIATION"


@pytest.mark.parametrize(
    "field",
    ["totalPreviousValue", "totalCurrentValue", "totalAbsoluteChange"],
)
def test_mismatched_contribution_total_fails(field: str) -> None:
    result = check_contribution_consistency(
        _contribution_insight(**{field: 999.0}),
        _change_insight(),
    )

    assert result is not None
    assert result.status == "FAIL"


def test_contribution_share_above_one_with_correct_totals_passes() -> None:
    result = check_contribution_consistency(
        _contribution_insight(contributionShare=1.5),
        _change_insight(),
    )

    assert result is not None
    assert result.status == "PASS"


@pytest.mark.parametrize("mismatch", ["analysis", "metric", "period"])
def test_incompatible_contribution_and_change_return_none(mismatch: str) -> None:
    target = _change_insight()
    if mismatch == "analysis":
        target.analysis_id = "other-analysis"
    elif mismatch == "metric":
        target.metric = "Orders"
    else:
        target.period = {"previous": "2025-02", "current": "2025-03"}

    assert check_contribution_consistency(
        _contribution_insight(),
        target,
    ) is None


def test_consistency_checks_do_not_mutate_inputs() -> None:
    dataframe = _reconciliation_dataframe()
    change = _change_insight()
    contribution = _contribution_insight()
    dataframe_snapshot = dataframe.copy(deep=True)
    change_snapshot = change.model_dump()
    contribution_snapshot = contribution.model_dump()

    check_change_total_consistency(
        change,
        dataframe,
        dimension="Region",
        aggregation="SUM",
    )
    check_contribution_consistency(contribution, change)

    assert_frame_equal(dataframe, dataframe_snapshot)
    assert change.model_dump() == change_snapshot
    assert contribution.model_dump() == contribution_snapshot


def _counter_evidence_item() -> CounterEvidenceItem:
    return CounterEvidenceItem(
        insightId="counter",
        relationshipId="counter-relationship",
        metric="Orders",
        direction=InsightDirection.DOWN,
        reasons=["Opposing business signal."],
    )


def _contradiction(
    contradiction_type: ContradictionType,
) -> ContradictionFinding:
    return ContradictionFinding(
        type=contradiction_type,
        code=f"{contradiction_type.value}_CODE",
        relatedInsightId="related",
        reason="Synthetic contradiction.",
    )


def _outlier_check(level: IntegrityRiskLevel) -> OutlierDependencyCheck:
    return OutlierDependencyCheck(
        level=level,
        detected=level != IntegrityRiskLevel.NONE,
        statisticName="TREND_SLOPE",
        originalStatistic=2.0,
        adjustedStatistic=1.0,
        outlierPeriod="2025-06" if level != IntegrityRiskLevel.NONE else None,
        reason="Synthetic outlier check.",
    )


def _one_off_check(risk: IntegrityRiskLevel) -> OneOffEffectCheck:
    return OneOffEffectCheck(
        risk=risk,
        eventPeriod="2025-06",
        nextPeriod="2025-07",
        baselineValue=10.0,
        eventValue=20.0,
        nextValue=11.0,
        reversionRatio=0.9,
        reason="Synthetic one-off check.",
    )


def _consistency_check(
    status: IntegrityCheckStatus,
) -> ConsistencyCheck:
    return ConsistencyCheck(
        code="RECONCILIATION",
        status=status,
        expectedValue=10.0,
        actualValue=9.0 if status == IntegrityCheckStatus.FAIL else 10.0,
        difference=-1.0 if status == IntegrityCheckStatus.FAIL else 0.0,
        tolerance=0.01,
        reason="Synthetic consistency check.",
    )


def test_integrity_policy_passes_when_no_findings_exist() -> None:
    result = build_integrity_evaluation(_change_insight())

    assert result.status == "PASS"
    assert result.story_eligible is True
    assert result.requires_qualification is False
    assert result.integrity_score == 1.0
    assert result.integrity_breakdown == {
        "contradictionSafety": 1.0,
        "counterEvidence": 1.0,
    }


def test_counter_evidence_produces_qualified_warning() -> None:
    result = build_integrity_evaluation(
        _change_insight(),
        counter_evidence=[_counter_evidence_item()],
    )

    assert result.status == "PASS_WITH_WARNINGS"
    assert result.story_eligible is True
    assert result.requires_qualification is True


@pytest.mark.parametrize(
    "risk",
    [IntegrityRiskLevel.LOW, IntegrityRiskLevel.MEDIUM],
)
def test_low_or_medium_outlier_produces_qualified_warning(
    risk: IntegrityRiskLevel,
) -> None:
    result = build_integrity_evaluation(
        _trend_insight(),
        outlier_check=_outlier_check(risk),
    )

    assert result.status == "PASS_WITH_WARNINGS"
    assert result.story_eligible is True
    assert result.requires_qualification is True


def test_high_outlier_requires_review_but_remains_eligible() -> None:
    result = build_integrity_evaluation(
        _trend_insight(),
        outlier_check=_outlier_check(IntegrityRiskLevel.HIGH),
    )

    assert result.status == "REVIEW_REQUIRED"
    assert result.story_eligible is True
    assert result.requires_qualification is True


def test_high_one_off_requires_review_but_remains_eligible() -> None:
    result = build_integrity_evaluation(
        _anomaly_insight(),
        one_off_check=_one_off_check(IntegrityRiskLevel.HIGH),
    )

    assert result.status == "REVIEW_REQUIRED"
    assert result.story_eligible is True
    assert result.requires_qualification is True


def test_insight_contradiction_requires_review_and_blocks_eligibility() -> None:
    result = build_integrity_evaluation(
        _change_insight(),
        contradictions=[
            _contradiction(ContradictionType.INSIGHT_CONTRADICTION)
        ],
    )

    assert result.status == "REVIEW_REQUIRED"
    assert result.story_eligible is False
    assert result.requires_qualification is True


@pytest.mark.parametrize(
    "contradiction_type",
    [
        ContradictionType.SEMANTIC_CONTRADICTION,
        ContradictionType.DATA_CONTRADICTION,
    ],
)
def test_unsafe_contradiction_fails_and_blocks_eligibility(
    contradiction_type: ContradictionType,
) -> None:
    result = build_integrity_evaluation(
        _change_insight(),
        contradictions=[_contradiction(contradiction_type)],
    )

    assert result.status == "FAIL"
    assert result.story_eligible is False
    assert result.requires_qualification is True


def test_failed_consistency_fails_and_blocks_eligibility() -> None:
    result = build_integrity_evaluation(
        _change_insight(),
        consistency_checks=[_consistency_check(IntegrityCheckStatus.FAIL)],
    )

    assert result.status == "FAIL"
    assert result.story_eligible is False
    assert result.requires_qualification is True


def test_counter_evidence_plus_high_one_off_requires_review() -> None:
    result = build_integrity_evaluation(
        _anomaly_insight(),
        counter_evidence=[_counter_evidence_item()],
        one_off_check=_one_off_check(IntegrityRiskLevel.HIGH),
    )

    assert result.status == "REVIEW_REQUIRED"
    assert result.story_eligible is True


def test_failed_consistency_overrides_counter_evidence() -> None:
    result = build_integrity_evaluation(
        _change_insight(),
        counter_evidence=[_counter_evidence_item()],
        consistency_checks=[_consistency_check(IntegrityCheckStatus.FAIL)],
    )

    assert result.status == "FAIL"
    assert result.story_eligible is False


def test_insight_contradiction_blocks_eligibility_with_high_outlier() -> None:
    result = build_integrity_evaluation(
        _trend_insight(),
        contradictions=[
            _contradiction(ContradictionType.INSIGHT_CONTRADICTION)
        ],
        outlier_check=_outlier_check(IntegrityRiskLevel.HIGH),
    )

    assert result.status == "REVIEW_REQUIRED"
    assert result.story_eligible is False
    assert result.requires_qualification is True


def test_none_risks_do_not_create_warnings() -> None:
    result = build_integrity_evaluation(
        _change_insight(),
        outlier_check=_outlier_check(IntegrityRiskLevel.NONE),
        one_off_check=_one_off_check(IntegrityRiskLevel.NONE),
    )

    assert result.status == "PASS"
    assert result.requires_qualification is False


def test_integrity_policy_does_not_mutate_evidence_inputs() -> None:
    insight = _change_insight()
    counter_evidence = [_counter_evidence_item()]
    contradictions = [
        _contradiction(ContradictionType.INSIGHT_CONTRADICTION)
    ]
    outlier = _outlier_check(IntegrityRiskLevel.LOW)
    one_off = _one_off_check(IntegrityRiskLevel.MEDIUM)
    consistency = [_consistency_check(IntegrityCheckStatus.PASS)]
    snapshots = [
        insight.model_dump(),
        [item.model_dump() for item in counter_evidence],
        [item.model_dump() for item in contradictions],
        outlier.model_dump(),
        one_off.model_dump(),
        [item.model_dump() for item in consistency],
    ]

    build_integrity_evaluation(
        insight,
        counter_evidence=counter_evidence,
        contradictions=contradictions,
        outlier_check=outlier,
        one_off_check=one_off,
        consistency_checks=consistency,
    )

    assert snapshots == [
        insight.model_dump(),
        [item.model_dump() for item in counter_evidence],
        [item.model_dump() for item in contradictions],
        outlier.model_dump(),
        one_off.model_dump(),
        [item.model_dump() for item in consistency],
    ]


def test_integrity_policy_reasons_are_deterministic_and_unique() -> None:
    arguments = {
        "counter_evidence": [_counter_evidence_item()],
        "contradictions": [
            _contradiction(ContradictionType.INSIGHT_CONTRADICTION),
            _contradiction(ContradictionType.INSIGHT_CONTRADICTION),
        ],
        "outlier_check": _outlier_check(IntegrityRiskLevel.HIGH),
        "one_off_check": _one_off_check(IntegrityRiskLevel.MEDIUM),
    }

    first = build_integrity_evaluation(_change_insight(), **arguments)
    second = build_integrity_evaluation(_change_insight(), **arguments)

    assert first.reasons == second.reasons
    assert len(first.reasons) == len(set(first.reasons))
    assert first.integrity_score == second.integrity_score
    assert first.integrity_breakdown == second.integrity_breakdown


def _integrity_score_config() -> dict:
    return copy.deepcopy(load_insight_config())


def test_clean_applicable_integrity_evidence_scores_one() -> None:
    result = calculate_integrity_score(
        consistency_checks=[_consistency_check(IntegrityCheckStatus.PASS)],
    )

    assert result == (
        1.0,
        {
            "consistency": 1.0,
            "contradictionSafety": 1.0,
            "counterEvidence": 1.0,
        },
    )


def test_counter_evidence_lowers_only_its_component() -> None:
    result = calculate_integrity_score(
        counter_evidence=[_counter_evidence_item()],
    )

    assert result == (
        0.9625,
        {"contradictionSafety": 1.0, "counterEvidence": 0.85},
    )


def test_high_outlier_lowers_outlier_robustness() -> None:
    result = calculate_integrity_score(
        outlier_check=_outlier_check(IntegrityRiskLevel.HIGH),
    )

    assert result is not None
    score, breakdown = result
    assert score == pytest.approx(0.795455)
    assert breakdown["outlierRobustness"] == 0.25


def test_high_one_off_lowers_one_off_robustness() -> None:
    result = calculate_integrity_score(
        one_off_check=_one_off_check(IntegrityRiskLevel.HIGH),
    )

    assert result is not None
    score, breakdown = result
    assert score == pytest.approx(0.795455)
    assert breakdown["oneOffRobustness"] == 0.25


def test_failed_consistency_scores_zero_for_component() -> None:
    result = calculate_integrity_score(
        consistency_checks=[_consistency_check(IntegrityCheckStatus.FAIL)],
    )

    assert result is not None
    _, breakdown = result
    assert breakdown["consistency"] == 0.0


@pytest.mark.parametrize(
    ("contradiction_type", "expected_score"),
    [
        (ContradictionType.INSIGHT_CONTRADICTION, 0.40),
        (ContradictionType.SEMANTIC_CONTRADICTION, 0.0),
        (ContradictionType.DATA_CONTRADICTION, 0.0),
    ],
)
def test_contradiction_safety_uses_configured_score(
    contradiction_type: ContradictionType,
    expected_score: float,
) -> None:
    result = calculate_integrity_score(
        contradictions=[_contradiction(contradiction_type)],
    )

    assert result is not None
    _, breakdown = result
    assert breakdown["contradictionSafety"] == expected_score


def test_non_applicable_robustness_components_are_omitted() -> None:
    result = calculate_integrity_score()

    assert result == (
        1.0,
        {"contradictionSafety": 1.0, "counterEvidence": 1.0},
    )


def test_available_weight_normalization_uses_participating_components() -> None:
    result = calculate_integrity_score(
        counter_evidence=[_counter_evidence_item()],
        consistency_checks=[_consistency_check(IntegrityCheckStatus.PASS)],
    )

    assert result is not None
    score, breakdown = result
    assert score == pytest.approx((0.30 + 0.30 + 0.10 * 0.85) / 0.70)
    assert set(breakdown) == {
        "consistency",
        "contradictionSafety",
        "counterEvidence",
    }


def test_integrity_score_and_breakdown_stay_in_unit_interval() -> None:
    result = calculate_integrity_score(
        counter_evidence=[_counter_evidence_item()],
        contradictions=[
            _contradiction(ContradictionType.INSIGHT_CONTRADICTION)
        ],
        outlier_check=_outlier_check(IntegrityRiskLevel.HIGH),
        one_off_check=_one_off_check(IntegrityRiskLevel.MEDIUM),
        consistency_checks=[_consistency_check(IntegrityCheckStatus.WARNING)],
    )

    assert result is not None
    score, breakdown = result
    assert 0.0 <= score <= 1.0
    assert all(0.0 <= value <= 1.0 for value in breakdown.values())


@pytest.mark.parametrize(
    "invalid_weight",
    [-0.1, 1.1, True, float("nan"), float("inf")],
)
def test_invalid_integrity_weight_config_is_handled_safely(
    invalid_weight: object,
) -> None:
    config = _integrity_score_config()
    config["insightIntegrity"]["score"]["weights"]["consistency"] = (
        invalid_weight
    )

    assert calculate_integrity_score(config=config) is None


def test_integrity_weights_must_sum_to_one() -> None:
    config = _integrity_score_config()
    config["insightIntegrity"]["score"]["weights"]["consistency"] = 0.20

    assert calculate_integrity_score(config=config) is None


@pytest.mark.parametrize(
    "invalid_score",
    [-0.1, 1.1, True, float("nan"), float("inf")],
)
def test_invalid_integrity_mapping_config_is_handled_safely(
    invalid_score: object,
) -> None:
    config = _integrity_score_config()
    config["insightIntegrity"]["score"]["riskScores"]["HIGH"] = (
        invalid_score
    )

    assert calculate_integrity_score(config=config) is None


def test_integrity_evaluation_populates_score_without_changing_policy() -> None:
    result = build_integrity_evaluation(
        _trend_insight(),
        outlier_check=_outlier_check(IntegrityRiskLevel.HIGH),
    )

    assert result.status == "REVIEW_REQUIRED"
    assert result.story_eligible is True
    assert result.requires_qualification is True
    assert result.integrity_score == pytest.approx(0.795455)
    assert result.integrity_breakdown["outlierRobustness"] == 0.25


def test_integrity_score_is_deterministic_and_does_not_mutate_inputs() -> None:
    counter = [_counter_evidence_item()]
    contradictions = [
        _contradiction(ContradictionType.INSIGHT_CONTRADICTION)
    ]
    outlier = _outlier_check(IntegrityRiskLevel.LOW)
    one_off = _one_off_check(IntegrityRiskLevel.MEDIUM)
    consistency = [_consistency_check(IntegrityCheckStatus.WARNING)]
    snapshots = [
        [item.model_dump() for item in counter],
        [item.model_dump() for item in contradictions],
        outlier.model_dump(),
        one_off.model_dump(),
        [item.model_dump() for item in consistency],
    ]
    arguments = {
        "counter_evidence": counter,
        "contradictions": contradictions,
        "outlier_check": outlier,
        "one_off_check": one_off,
        "consistency_checks": consistency,
    }

    first = calculate_integrity_score(**arguments)
    second = calculate_integrity_score(**arguments)

    assert first == second
    assert snapshots == [
        [item.model_dump() for item in counter],
        [item.model_dump() for item in contradictions],
        outlier.model_dump(),
        one_off.model_dump(),
        [item.model_dump() for item in consistency],
    ]


def _orchestration_metadata(aggregation: str = "SUM") -> dict:
    return {
        "columns": {
            "Region": {"role": "DIMENSION"},
            "Product": {"role": "DIMENSION"},
            "Revenue": {"role": "METRIC", "aggregation": aggregation},
            "Orders": {"role": "METRIC", "aggregation": "SUM"},
        }
    }


def _orchestration_dataframe() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Date": pd.date_range("2025-01-01", periods=7, freq="MS"),
            "Region": ["North"] * 7,
            "Product": ["Widget"] * 7,
            "Revenue": [10.0, 11.0, 10.0, 11.0, 10.0, 100.0, 10.0],
            "Orders": [20.0, 18.0, 20.0, 20.0, 20.0, 20.0, 20.0],
        }
    )


def _orchestration_insights() -> list[Insight]:
    return [
        _insight(
            "z-revenue-change",
            "Revenue",
            InsightDirection.UP,
            period={"previous": "2025-01", "current": "2025-02"},
            values={
                "previous": 10.0,
                "current": 11.0,
                "absoluteChange": 1.0,
                "percentageChange": 10.0,
            },
        ),
        _insight(
            "y-orders-change",
            "Orders",
            InsightDirection.DOWN,
            period={"previous": "2025-01", "current": "2025-02"},
            values={"percentageChange": -10.0},
        ),
        _insight(
            "b-trend",
            "Revenue",
            InsightDirection.UP,
            insight_type=InsightType.TREND,
            dimension="Product",
            segment="Widget",
            period={"start": "2025-01", "end": "2025-06"},
        ),
        _insight(
            "a-anomaly",
            "Revenue",
            InsightDirection.HIGH,
            insight_type=InsightType.ANOMALY,
            dimension="Product",
            segment="Widget",
            period={"current": "2025-06"},
        ),
        _insight(
            "c-contribution",
            "Revenue",
            InsightDirection.UP,
            insight_type=InsightType.CONTRIBUTION,
            dimension="Region",
            segment="North",
            period={"previous": "2025-01", "current": "2025-02"},
            values={
                "totalPreviousValue": 10.0,
                "totalCurrentValue": 11.0,
                "totalAbsoluteChange": 1.0,
                "contributionShare": 1.0,
            },
        ),
        _insight(
            "d-contrast",
            "Revenue",
            InsightDirection.UP,
            insight_type=InsightType.CONTRAST,
            dimension="Region",
            segment="North",
            period={"previous": "2025-01", "current": "2025-02"},
        ),
    ]


def _orchestration_relationship() -> Relationship:
    return _relationship(
        "counter-orders-revenue",
        "y-orders-change",
        "z-revenue-change",
    )


def test_integrity_orchestration_returns_empty_result() -> None:
    result = analyze_insight_integrity(
        [],
        [],
        _orchestration_dataframe(),
        _orchestration_metadata(),
    )

    assert result.evaluations == []


def test_integrity_orchestration_rejects_duplicate_insight_ids() -> None:
    insight = _change_insight()

    with pytest.raises(ValueError, match="Duplicate Insight ID"):
        analyze_insight_integrity(
            [insight, insight.model_copy(deep=True)],
            [],
            _orchestration_dataframe(),
            _orchestration_metadata(),
        )


def test_integrity_orchestration_rejects_mixed_analysis_ids() -> None:
    first = _change_insight()
    second = _change_insight()
    second.id = "other"
    second.analysis_id = "other-analysis"

    with pytest.raises(ValueError, match="same analysis"):
        analyze_insight_integrity(
            [first, second],
            [],
            _orchestration_dataframe(),
            _orchestration_metadata(),
        )


def test_integrity_orchestration_applies_type_aware_check_matrix() -> None:
    insights = _orchestration_insights()
    result = analyze_insight_integrity(
        insights,
        [_orchestration_relationship()],
        _orchestration_dataframe(),
        _orchestration_metadata(),
    )

    assert len(result.evaluations) == len(insights)
    assert [item.insight_id for item in result.evaluations] == sorted(
        insight.id for insight in insights
    )
    by_id = {item.insight_id: item for item in result.evaluations}

    revenue = by_id["z-revenue-change"]
    assert [item.metric for item in revenue.counter_evidence] == ["Orders"]
    assert revenue.contradictions == []
    assert [check.status for check in revenue.consistency_checks] == ["PASS"]
    assert revenue.outlier_check is None
    assert revenue.one_off_check is None

    trend = by_id["b-trend"]
    assert trend.outlier_check is not None
    assert trend.one_off_check is None
    assert trend.counter_evidence == []
    assert trend.consistency_checks == []

    anomaly = by_id["a-anomaly"]
    assert anomaly.one_off_check is not None
    assert anomaly.outlier_check is None
    assert anomaly.counter_evidence == []
    assert anomaly.consistency_checks == []

    contribution = by_id["c-contribution"]
    assert [check.status for check in contribution.consistency_checks] == [
        "PASS"
    ]
    assert contribution.counter_evidence == []
    assert contribution.outlier_check is None
    assert contribution.one_off_check is None

    contrast = by_id["d-contrast"]
    assert contrast.counter_evidence == []
    assert contrast.consistency_checks == []
    assert contrast.outlier_check is None
    assert contrast.one_off_check is None

    assert all(item.integrity_score is not None for item in result.evaluations)
    assert all(item.integrity_breakdown for item in result.evaluations)


def test_orchestration_runs_semantic_check_for_change() -> None:
    change = _insight(
        "semantic-change",
        "Revenue",
        InsightDirection.DOWN,
        values={"percentageChange": 10.0},
    )

    result = analyze_insight_integrity(
        [change],
        [],
        _orchestration_dataframe(),
        _orchestration_metadata("UNSUPPORTED"),
    ).evaluations[0]

    assert [finding.type for finding in result.contradictions] == [
        "SEMANTIC_CONTRADICTION"
    ]
    assert result.status == "FAIL"
    assert result.consistency_checks == []


def test_segment_change_does_not_get_total_consistency() -> None:
    change = _insight(
        "segment-change",
        "Revenue",
        InsightDirection.UP,
        dimension="Product",
        segment="Widget",
        values={"percentageChange": 10.0},
    )

    evaluation = analyze_insight_integrity(
        [change],
        [],
        _orchestration_dataframe(),
        _orchestration_metadata(),
    ).evaluations[0]

    assert evaluation.consistency_checks == []


def test_contribution_without_matching_change_does_not_invent_failure() -> None:
    contribution = next(
        insight
        for insight in _orchestration_insights()
        if insight.type == "CONTRIBUTION"
    )

    evaluation = analyze_insight_integrity(
        [contribution],
        [],
        _orchestration_dataframe(),
        _orchestration_metadata(),
    ).evaluations[0]

    assert evaluation.consistency_checks == []
    assert evaluation.status == "PASS"


def test_contrast_receives_only_contradiction_evaluation() -> None:
    first = _insight(
        "contrast-a",
        "Revenue",
        InsightDirection.UP,
        insight_type=InsightType.CONTRAST,
        dimension="Region",
        segment="North",
    )
    second = first.model_copy(
        deep=True,
        update={"id": "contrast-b", "direction": "DOWN"},
    )

    result = analyze_insight_integrity(
        [second, first],
        [],
        _orchestration_dataframe(),
        _orchestration_metadata(),
    )

    assert all(
        [finding.type for finding in item.contradictions]
        == ["INSIGHT_CONTRADICTION"]
        for item in result.evaluations
    )
    assert all(item.counter_evidence == [] for item in result.evaluations)
    assert all(item.consistency_checks == [] for item in result.evaluations)
    assert all(item.outlier_check is None for item in result.evaluations)
    assert all(item.one_off_check is None for item in result.evaluations)


def test_orchestration_uses_metadata_aggregation() -> None:
    dates = pd.date_range("2025-01-01", periods=7, freq="MS")
    dataframe = pd.DataFrame(
        {
            "Date": [date for date in dates for _ in range(2)],
            "Product": ["Widget"] * 14,
            "Revenue": [
                value
                for pair in (
                    (10, 20),
                    (10, 20),
                    (10, 20),
                    (10, 20),
                    (10, 20),
                    (100, 200),
                    (10, 20),
                )
                for value in pair
            ],
        }
    )
    anomaly = _anomaly_insight()

    evaluation = analyze_insight_integrity(
        [anomaly],
        [],
        dataframe,
        {
            "columns": {
                "Product": {"role": "DIMENSION"},
                "Revenue": {"role": "METRIC", "aggregation": "AVG"},
            }
        },
    ).evaluations[0]

    assert evaluation.one_off_check is not None
    assert evaluation.one_off_check.baseline_value == 15.0
    assert evaluation.one_off_check.event_value == 150.0
    assert evaluation.one_off_check.next_value == 15.0


def test_unsupported_aggregation_skips_only_dependent_checks() -> None:
    trend = _trend_insight()
    anomaly = _anomaly_insight()

    result = analyze_insight_integrity(
        [trend, anomaly],
        [],
        _orchestration_dataframe(),
        _orchestration_metadata("RATIO_OF_SUMS"),
    )

    assert all(item.outlier_check is None for item in result.evaluations)
    assert all(item.one_off_check is None for item in result.evaluations)
    assert all(item.integrity_score == 1.0 for item in result.evaluations)
    assert all(
        item.integrity_breakdown
        == {"contradictionSafety": 1.0, "counterEvidence": 1.0}
        for item in result.evaluations
    )


def test_integrity_orchestration_is_deterministic_and_does_not_mutate_inputs() -> None:
    insights = _orchestration_insights()
    relationships = [_orchestration_relationship()]
    dataframe = _orchestration_dataframe()
    metadata = _orchestration_metadata()
    config = _integrity_score_config()
    snapshots = {
        "insights": [item.model_dump() for item in insights],
        "relationships": [item.model_dump() for item in relationships],
        "dataframe": dataframe.copy(deep=True),
        "metadata": copy.deepcopy(metadata),
        "config": copy.deepcopy(config),
    }

    first = analyze_insight_integrity(
        insights,
        relationships,
        dataframe,
        metadata,
        config,
    )
    second = analyze_insight_integrity(
        list(reversed(insights)),
        list(reversed(relationships)),
        dataframe,
        metadata,
        config,
    )

    assert first.model_dump(by_alias=True) == second.model_dump(by_alias=True)
    assert [item.model_dump() for item in insights] == snapshots["insights"]
    assert [item.model_dump() for item in relationships] == snapshots[
        "relationships"
    ]
    assert_frame_equal(dataframe, snapshots["dataframe"])
    assert metadata == snapshots["metadata"]
    assert config == snapshots["config"]
