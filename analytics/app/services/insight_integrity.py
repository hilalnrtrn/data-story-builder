import math
from numbers import Real
from typing import Any

import pandas as pd

from app.config.insight_config_loader import load_insight_config
from app.models.insight import Insight, InsightDirection
from app.models.insight_integrity import (
    ConsistencyCheck,
    ContradictionFinding,
    ContradictionType,
    CounterEvidenceItem,
    IntegrityCheckStatus,
    IntegrityRiskLevel,
    IntegrityStatus,
    InsightIntegrityEvaluation,
    InsightIntegrityResult,
    OneOffEffectCheck,
    OutlierDependencyCheck,
)
from app.models.relationship import Relationship, RelationshipType
from app.services.trend_detector import calculate_persistence, calculate_slope


def build_counter_evidence(
    primary_insight: Insight,
    insights: list[Insight],
    relationships: list[Relationship],
) -> list[CounterEvidenceItem]:
    insights_by_id = {
        insight.id: insight
        for insight in insights
        if insight.analysis_id == primary_insight.analysis_id
    }
    evidence_by_key: dict[tuple[str, str], CounterEvidenceItem] = {}

    for relationship in relationships:
        if (
            relationship.type != RelationshipType.COUNTER_SIGNAL
            or relationship.analysis_id != primary_insight.analysis_id
        ):
            continue

        if relationship.source_insight_id == primary_insight.id:
            related_insight_id = relationship.target_insight_id
        elif relationship.target_insight_id == primary_insight.id:
            related_insight_id = relationship.source_insight_id
        else:
            continue

        related_insight = insights_by_id.get(related_insight_id)
        if related_insight is None:
            continue

        key = (related_insight.id, relationship.id)
        if key in evidence_by_key:
            continue

        evidence_by_key[key] = CounterEvidenceItem(
            insightId=related_insight.id,
            relationshipId=relationship.id,
            metric=related_insight.metric,
            direction=related_insight.direction,
            reasons=list(relationship.reasons),
        )

    return [evidence_by_key[key] for key in sorted(evidence_by_key)]


def build_insight_contradictions(
    primary_insight: Insight,
    insights: list[Insight],
) -> list[ContradictionFinding]:
    findings_by_insight_id: dict[str, ContradictionFinding] = {}

    for related_insight in insights:
        if (
            related_insight.id == primary_insight.id
            or related_insight.analysis_id != primary_insight.analysis_id
            or related_insight.metric != primary_insight.metric
            or related_insight.dimension != primary_insight.dimension
            or related_insight.segment != primary_insight.segment
            or related_insight.period_granularity
            != primary_insight.period_granularity
            or related_insight.period != primary_insight.period
            or related_insight.type != primary_insight.type
            or not _directions_oppose(
                primary_insight.direction,
                related_insight.direction,
            )
        ):
            continue

        findings_by_insight_id.setdefault(
            related_insight.id,
            ContradictionFinding(
                type=ContradictionType.INSIGHT_CONTRADICTION,
                code="OPPOSING_INSIGHT_DIRECTION",
                relatedInsightId=related_insight.id,
                reason=(
                    f"Insight {related_insight.id} reports direction "
                    f"{related_insight.direction}, opposing primary insight "
                    f"{primary_insight.id} direction "
                    f"{primary_insight.direction} for the same claim."
                ),
            ),
        )

    return [
        findings_by_insight_id[insight_id]
        for insight_id in sorted(findings_by_insight_id)
    ]


def build_semantic_contradictions(
    insight: Insight,
) -> list[ContradictionFinding]:
    if insight.type != "CHANGE":
        return []

    percentage_change = insight.values.get("percentageChange")
    if (
        isinstance(percentage_change, bool)
        or not isinstance(percentage_change, Real)
        or not math.isfinite(float(percentage_change))
        or percentage_change == 0
    ):
        return []

    mismatch = (
        percentage_change > 0 and insight.direction == "DOWN"
    ) or (
        percentage_change < 0 and insight.direction == "UP"
    )
    if not mismatch:
        return []

    return [
        ContradictionFinding(
            type=ContradictionType.SEMANTIC_CONTRADICTION,
            code="CHANGE_DIRECTION_VALUE_MISMATCH",
            relatedInsightId=None,
            reason=(
                f"Insight {insight.id} reports direction {insight.direction} "
                f"but percentageChange is {percentage_change}."
            ),
        )
    ]


def check_trend_outlier_dependency(
    insight: Insight,
    dataframe: pd.DataFrame,
    aggregation: str,
    config: dict[str, Any] | None = None,
) -> OutlierDependencyCheck | None:
    if (
        insight.type != "TREND"
        or insight.dimension is None
        or insight.segment is None
    ):
        return None

    period_start = insight.period.get("start")
    period_end = insight.period.get("end")
    if period_start is None or period_end is None:
        return None

    return check_trend_candidate_outlier_dependency(
        dataframe,
        metric=insight.metric,
        dimension=insight.dimension,
        segment=insight.segment,
        aggregation=aggregation,
        period_start=period_start,
        period_end=period_end,
        expected_direction=insight.direction,
        config=config,
    )


def check_trend_candidate_outlier_dependency(
    dataframe: pd.DataFrame,
    *,
    metric: str,
    dimension: str,
    segment: str,
    aggregation: str,
    period_start: str,
    period_end: str,
    expected_direction: InsightDirection | str | None = None,
    config: dict[str, Any] | None = None,
) -> OutlierDependencyCheck | None:
    if (
        "Date" not in dataframe.columns
        or metric not in dataframe.columns
        or dimension not in dataframe.columns
        or aggregation.upper() not in {"SUM", "AVG"}
    ):
        return None

    series = _build_trend_monthly_series(
        dataframe,
        metric=metric,
        dimension=dimension,
        segment=segment,
        aggregation=aggregation,
        period_start=period_start,
        period_end=period_end,
    )
    if len(series) < 2:
        return None

    values = series["value"].to_numpy(dtype=float)
    original_slope = calculate_slope(values)
    if expected_direction is None:
        if original_slope > 0:
            candidate_direction = InsightDirection.UP
        elif original_slope < 0:
            candidate_direction = InsightDirection.DOWN
        else:
            return _no_material_outlier_check(
                original_slope,
                "No directional trend was found because the slope is zero.",
            )
    else:
        try:
            candidate_direction = InsightDirection(expected_direction)
        except ValueError:
            return None

    q1 = float(series["value"].quantile(0.25))
    q3 = float(series["value"].quantile(0.75))
    iqr = q3 - q1

    if iqr == 0:
        return _no_material_outlier_check(
            original_slope,
            "No material outlier was found because the trend series IQR is zero.",
        )

    effective_config = config if config is not None else load_insight_config()
    iqr_multiplier = float(effective_config["anomaly"]["iqrMultiplier"])
    lower_bound = q1 - iqr_multiplier * iqr
    upper_bound = q3 + iqr_multiplier * iqr
    outlier_candidates: list[tuple[float, str, int]] = []

    for index, row in series.iterrows():
        value = float(row["value"])
        if value < lower_bound:
            normalized_distance = (lower_bound - value) / iqr
        elif value > upper_bound:
            normalized_distance = (value - upper_bound) / iqr
        else:
            continue
        outlier_candidates.append(
            (normalized_distance, str(row["period"]), int(index))
        )

    if not outlier_candidates:
        return _no_material_outlier_check(
            original_slope,
            "No material outlier was found in the trend period.",
        )

    _, outlier_period, outlier_index = sorted(
        outlier_candidates,
        key=lambda candidate: (-candidate[0], candidate[1]),
    )[0]
    adjusted_values = series.drop(index=outlier_index)["value"].to_numpy(
        dtype=float
    )
    adjusted_slope = calculate_slope(adjusted_values)
    adjusted_persistence = calculate_persistence(
        adjusted_values,
        direction=candidate_direction,
    )
    minimum_persistence = float(
        effective_config["trend"]["minimumPersistenceThreshold"]
    )
    direction_still_matches = (
        candidate_direction == InsightDirection.UP and adjusted_slope > 0
    ) or (
        candidate_direction == InsightDirection.DOWN and adjusted_slope < 0
    )
    slope_reduction = _calculate_slope_reduction(
        original_slope,
        adjusted_slope,
    )
    thresholds = effective_config["insightIntegrity"]["outlierDependency"]

    if (
        not direction_still_matches
        or adjusted_persistence < minimum_persistence
        or slope_reduction >= float(thresholds["highSlopeReduction"])
    ):
        level = IntegrityRiskLevel.HIGH
    elif slope_reduction >= float(thresholds["mediumSlopeReduction"]):
        level = IntegrityRiskLevel.MEDIUM
    elif slope_reduction >= float(thresholds["lowSlopeReduction"]):
        level = IntegrityRiskLevel.LOW
    else:
        level = IntegrityRiskLevel.NONE

    return OutlierDependencyCheck(
        level=level,
        detected=True,
        statisticName="TREND_SLOPE",
        originalStatistic=original_slope,
        adjustedStatistic=adjusted_slope,
        outlierPeriod=outlier_period,
        reason=(
            f"Removing dominant outlier period {outlier_period} changed the "
            f"trend slope from {original_slope:.6f} to "
            f"{adjusted_slope:.6f}; slope magnitude reduction was "
            f"{slope_reduction:.6f} and adjusted persistence was "
            f"{adjusted_persistence:.6f}."
        ),
    )


def check_one_off_effect(
    insight: Insight,
    dataframe: pd.DataFrame,
    aggregation: str,
    config: dict[str, Any] | None = None,
) -> OneOffEffectCheck | None:
    if (
        insight.type != "ANOMALY"
        or insight.dimension is None
        or insight.segment is None
        or "Date" not in dataframe.columns
        or insight.metric not in dataframe.columns
        or insight.dimension not in dataframe.columns
        or aggregation.upper() not in {"SUM", "AVG"}
    ):
        return None

    event_period = insight.period.get("current")
    valid_dates = dataframe["Date"].dropna()
    if event_period is None or valid_dates.empty:
        return None

    series = _build_trend_monthly_series(
        dataframe,
        metric=insight.metric,
        dimension=insight.dimension,
        segment=insight.segment,
        aggregation=aggregation,
        period_start=str(valid_dates.min().to_period("M")),
        period_end=str(valid_dates.max().to_period("M")),
    )
    event_rows = series.loc[series["period"] == event_period]
    next_rows = series.loc[series["period"] > event_period]
    if event_rows.empty or next_rows.empty:
        return None

    effective_config = config if config is not None else load_insight_config()
    minimum_baseline_periods = max(
        int(effective_config["anomaly"]["minimumPeriods"]) - 1,
        1,
    )
    baseline = series.loc[series["period"] < event_period, "value"].astype(
        float
    )
    if len(baseline) < minimum_baseline_periods:
        return None

    baseline_value = float(baseline.median())
    event_value = float(event_rows.iloc[0]["value"])
    next_row = next_rows.iloc[0]
    next_period = str(next_row["period"])
    next_value = float(next_row["value"])
    event_deviation = abs(event_value - baseline_value)

    if event_deviation == 0:
        return OneOffEffectCheck(
            risk=IntegrityRiskLevel.NONE,
            eventPeriod=event_period,
            nextPeriod=next_period,
            baselineValue=baseline_value,
            eventValue=event_value,
            nextValue=next_value,
            reversionRatio=0.0,
            reason=(
                f"Event period {event_period} does not deviate from the "
                "historical baseline, so no one-off effect was found."
            ),
        )

    remaining_deviation = abs(next_value - baseline_value)
    reversion_ratio = min(
        1.0,
        max(0.0, 1.0 - remaining_deviation / event_deviation),
    )
    thresholds = effective_config["insightIntegrity"]["oneOffEffect"]

    if reversion_ratio >= float(thresholds["highReversionRatio"]):
        risk = IntegrityRiskLevel.HIGH
    elif reversion_ratio >= float(thresholds["mediumReversionRatio"]):
        risk = IntegrityRiskLevel.MEDIUM
    elif reversion_ratio >= float(thresholds["lowReversionRatio"]):
        risk = IntegrityRiskLevel.LOW
    else:
        risk = IntegrityRiskLevel.NONE

    return OneOffEffectCheck(
        risk=risk,
        eventPeriod=event_period,
        nextPeriod=next_period,
        baselineValue=baseline_value,
        eventValue=event_value,
        nextValue=next_value,
        reversionRatio=reversion_ratio,
        reason=(
            f"Event period {event_period} moved from baseline "
            f"{baseline_value:.6f} to {event_value:.6f}; next period "
            f"{next_period} was {next_value:.6f}, producing reversion ratio "
            f"{reversion_ratio:.6f}."
        ),
    )


def check_change_total_consistency(
    insight: Insight,
    dataframe: pd.DataFrame,
    *,
    dimension: str,
    aggregation: str,
    tolerance: float = 1e-6,
) -> ConsistencyCheck | None:
    if (
        insight.type != "CHANGE"
        or insight.dimension is not None
        or insight.segment is not None
        or aggregation.upper() != "SUM"
        or "Date" not in dataframe.columns
        or insight.metric not in dataframe.columns
        or dimension not in dataframe.columns
        or not _valid_tolerance(tolerance)
    ):
        return None

    previous_period = insight.period.get("previous")
    current_period = insight.period.get("current")
    if previous_period is None or current_period is None:
        return None

    previous_totals = _reconciliation_totals(
        dataframe,
        metric=insight.metric,
        dimension=dimension,
        period=previous_period,
    )
    current_totals = _reconciliation_totals(
        dataframe,
        metric=insight.metric,
        dimension=dimension,
        period=current_period,
    )
    if previous_totals is None or current_totals is None:
        return None

    previous_whole, previous_grouped = previous_totals
    current_whole, current_grouped = current_totals
    previous_difference = previous_grouped - previous_whole
    current_difference = current_grouped - current_whole
    passed = (
        abs(previous_difference) <= tolerance
        and abs(current_difference) <= tolerance
    )

    return ConsistencyCheck(
        code="TOTAL_VS_DIMENSION_RECONCILIATION",
        status=(
            IntegrityCheckStatus.PASS
            if passed
            else IntegrityCheckStatus.FAIL
        ),
        expectedValue=current_whole,
        actualValue=current_grouped,
        difference=current_difference,
        tolerance=tolerance,
        reason=(
            f"Previous period {previous_period}: whole total "
            f"{previous_whole:.6f}, summed {dimension} total "
            f"{previous_grouped:.6f}, difference "
            f"{previous_difference:.6f}. Current period {current_period}: "
            f"whole total {current_whole:.6f}, summed {dimension} total "
            f"{current_grouped:.6f}, difference {current_difference:.6f}."
        ),
    )


def check_contribution_consistency(
    contribution_insight: Insight,
    target_change_insight: Insight,
    *,
    tolerance: float = 1e-6,
) -> ConsistencyCheck | None:
    if (
        contribution_insight.type != "CONTRIBUTION"
        or target_change_insight.type != "CHANGE"
        or contribution_insight.analysis_id
        != target_change_insight.analysis_id
        or contribution_insight.metric != target_change_insight.metric
        or contribution_insight.period != target_change_insight.period
        or not _valid_tolerance(tolerance)
    ):
        return None

    comparisons = (
        (
            "previous",
            target_change_insight.values.get("previous"),
            contribution_insight.values.get("totalPreviousValue"),
        ),
        (
            "current",
            target_change_insight.values.get("current"),
            contribution_insight.values.get("totalCurrentValue"),
        ),
        (
            "absolute change",
            target_change_insight.values.get("absoluteChange"),
            contribution_insight.values.get("totalAbsoluteChange"),
        ),
    )
    if any(
        not _is_finite_number(expected) or not _is_finite_number(actual)
        for _, expected, actual in comparisons
    ):
        return None

    numeric_comparisons = [
        (label, float(expected), float(actual))
        for label, expected, actual in comparisons
    ]
    passed = all(
        abs(actual - expected) <= tolerance
        for _, expected, actual in numeric_comparisons
    )
    _, expected_change, actual_change = numeric_comparisons[-1]

    details = "; ".join(
        (
            f"{label}: expected {expected:.6f}, actual {actual:.6f}, "
            f"difference {actual - expected:.6f}"
        )
        for label, expected, actual in numeric_comparisons
    )
    return ConsistencyCheck(
        code="CONTRIBUTION_TOTAL_RECONCILIATION",
        status=(
            IntegrityCheckStatus.PASS
            if passed
            else IntegrityCheckStatus.FAIL
        ),
        expectedValue=expected_change,
        actualValue=actual_change,
        difference=actual_change - expected_change,
        tolerance=tolerance,
        reason=f"Contribution total reconciliation: {details}.",
    )


def build_integrity_evaluation(
    insight: Insight,
    *,
    counter_evidence: list[CounterEvidenceItem] | None = None,
    contradictions: list[ContradictionFinding] | None = None,
    outlier_check: OutlierDependencyCheck | None = None,
    one_off_check: OneOffEffectCheck | None = None,
    consistency_checks: list[ConsistencyCheck] | None = None,
    config: dict[str, Any] | None = None,
) -> InsightIntegrityEvaluation:
    counter_items = list(counter_evidence or [])
    contradiction_items = list(contradictions or [])
    consistency_items = list(consistency_checks or [])

    has_failed_consistency = any(
        check.status == "FAIL" for check in consistency_items
    )
    has_data_contradiction = any(
        finding.type == "DATA_CONTRADICTION"
        for finding in contradiction_items
    )
    has_semantic_contradiction = any(
        finding.type == "SEMANTIC_CONTRADICTION"
        for finding in contradiction_items
    )
    has_insight_contradiction = any(
        finding.type == "INSIGHT_CONTRADICTION"
        for finding in contradiction_items
    )
    outlier_risk = outlier_check.level if outlier_check is not None else "NONE"
    one_off_risk = one_off_check.risk if one_off_check is not None else "NONE"
    has_high_risk = outlier_risk == "HIGH" or one_off_risk == "HIGH"
    has_warning_risk = outlier_risk in {"LOW", "MEDIUM"} or one_off_risk in {
        "LOW",
        "MEDIUM",
    }

    has_fail = (
        has_failed_consistency
        or has_data_contradiction
        or has_semantic_contradiction
    )
    if has_fail:
        status = IntegrityStatus.FAIL
    elif has_insight_contradiction or has_high_risk:
        status = IntegrityStatus.REVIEW_REQUIRED
    elif counter_items or has_warning_risk:
        status = IntegrityStatus.PASS_WITH_WARNINGS
    else:
        status = IntegrityStatus.PASS

    story_eligible = not has_fail and not has_insight_contradiction
    requires_qualification = status != IntegrityStatus.PASS
    reasons: list[str] = []

    def add_reason(reason: str) -> None:
        if reason not in reasons:
            reasons.append(reason)

    if has_failed_consistency:
        add_reason("A failed consistency reconciliation blocks narration.")
    if has_data_contradiction:
        add_reason("A data contradiction blocks narration.")
    if has_semantic_contradiction:
        add_reason("A semantic contradiction blocks narration.")
    if has_insight_contradiction:
        add_reason(
            "An insight contradiction requires review and blocks narration."
        )
    if counter_items:
        add_reason("Counter evidence is present and requires qualification.")
    if outlier_risk == "HIGH":
        add_reason(
            "High outlier dependency requires review and qualification."
        )
    elif outlier_risk in {"LOW", "MEDIUM"}:
        add_reason(
            f"{outlier_risk.title()} outlier dependency requires "
            "qualification."
        )
    if one_off_risk == "HIGH":
        add_reason("High one-off risk requires review and qualification.")
    elif one_off_risk in {"LOW", "MEDIUM"}:
        add_reason(
            f"{one_off_risk.title()} one-off risk requires qualification."
        )
    if story_eligible and requires_qualification:
        add_reason("The insight remains story eligible with qualification.")
    if status == IntegrityStatus.PASS:
        add_reason("No integrity findings require qualification.")

    score_result = calculate_integrity_score(
        counter_evidence=counter_items,
        contradictions=contradiction_items,
        outlier_check=outlier_check,
        one_off_check=one_off_check,
        consistency_checks=consistency_items,
        config=config,
    )
    if score_result is None:
        integrity_score = None
        integrity_breakdown: dict[str, float] = {}
    else:
        integrity_score, integrity_breakdown = score_result

    return InsightIntegrityEvaluation(
        insightId=insight.id,
        status=status,
        counterEvidence=counter_items,
        contradictions=contradiction_items,
        outlierCheck=outlier_check,
        oneOffCheck=one_off_check,
        consistencyChecks=consistency_items,
        integrityScore=integrity_score,
        integrityBreakdown=integrity_breakdown,
        storyEligible=story_eligible,
        requiresQualification=requires_qualification,
        reasons=reasons,
    )


def calculate_integrity_score(
    *,
    counter_evidence: list[CounterEvidenceItem] | None = None,
    contradictions: list[ContradictionFinding] | None = None,
    outlier_check: OutlierDependencyCheck | None = None,
    one_off_check: OneOffEffectCheck | None = None,
    consistency_checks: list[ConsistencyCheck] | None = None,
    config: dict[str, Any] | None = None,
) -> tuple[float, dict[str, float]] | None:
    effective_config = config if config is not None else load_insight_config()
    score_config = effective_config.get("insightIntegrity", {}).get("score")
    if not isinstance(score_config, dict):
        return None

    weights = score_config.get("weights")
    risk_scores = score_config.get("riskScores")
    consistency_scores = score_config.get("consistencyScores")
    contradiction_scores = score_config.get("contradictionScores")
    counter_scores = score_config.get("counterEvidenceScores")
    expected_weights = {
        "consistency",
        "contradictionSafety",
        "outlierRobustness",
        "oneOffRobustness",
        "counterEvidence",
    }
    if (
        not _valid_score_mapping(weights, expected_weights)
        or not math.isclose(
            sum(float(value) for value in weights.values()),
            1.0,
            rel_tol=0.0,
            abs_tol=1e-9,
        )
        or not _valid_score_mapping(
            risk_scores,
            {"NONE", "LOW", "MEDIUM", "HIGH"},
        )
        or not _valid_score_mapping(
            consistency_scores,
            {"PASS", "WARNING", "FAIL"},
        )
        or not _valid_score_mapping(
            contradiction_scores,
            {
                "NONE",
                "INSIGHT_CONTRADICTION",
                "DATA_CONTRADICTION",
                "SEMANTIC_CONTRADICTION",
            },
        )
        or not _valid_score_mapping(
            counter_scores,
            {"ABSENT", "PRESENT"},
        )
    ):
        return None

    counter_items = counter_evidence or []
    contradiction_items = contradictions or []
    consistency_items = consistency_checks or []
    breakdown: dict[str, float] = {}

    if consistency_items:
        statuses = {check.status for check in consistency_items}
        consistency_status = (
            "FAIL"
            if "FAIL" in statuses
            else "WARNING"
            if "WARNING" in statuses
            else "PASS"
        )
        breakdown["consistency"] = float(
            consistency_scores[consistency_status]
        )

    contradiction_types = {
        finding.type for finding in contradiction_items
    }
    if contradiction_types & {
        "DATA_CONTRADICTION",
        "SEMANTIC_CONTRADICTION",
    }:
        contradiction_level = next(
            level
            for level in ("DATA_CONTRADICTION", "SEMANTIC_CONTRADICTION")
            if level in contradiction_types
        )
    elif "INSIGHT_CONTRADICTION" in contradiction_types:
        contradiction_level = "INSIGHT_CONTRADICTION"
    else:
        contradiction_level = "NONE"
    breakdown["contradictionSafety"] = float(
        contradiction_scores[contradiction_level]
    )

    if outlier_check is not None:
        breakdown["outlierRobustness"] = float(
            risk_scores[outlier_check.level]
        )
    if one_off_check is not None:
        breakdown["oneOffRobustness"] = float(
            risk_scores[one_off_check.risk]
        )

    counter_level = "PRESENT" if counter_items else "ABSENT"
    breakdown["counterEvidence"] = float(counter_scores[counter_level])

    available_weight = sum(float(weights[name]) for name in breakdown)
    if available_weight <= 0:
        return None

    weighted_score = sum(
        float(weights[name]) * component_score
        for name, component_score in breakdown.items()
    ) / available_weight
    return round(weighted_score, 6), breakdown


def analyze_insight_integrity(
    insights: list[Insight],
    relationships: list[Relationship],
    dataframe: pd.DataFrame,
    metadata: dict[str, Any],
    config: dict[str, Any] | None = None,
) -> InsightIntegrityResult:
    insight_ids: set[str] = set()
    for insight in insights:
        if insight.id in insight_ids:
            raise ValueError(f"Duplicate Insight ID: {insight.id}")
        insight_ids.add(insight.id)

    analysis_ids = {insight.analysis_id for insight in insights}
    if len(analysis_ids) > 1:
        raise ValueError("Insights must belong to the same analysis")
    if not insights:
        return InsightIntegrityResult()

    effective_config = config if config is not None else load_insight_config()
    reconciliation_dimension = _resolve_reconciliation_dimension(
        metadata,
        dataframe,
    )
    ordered_insights = sorted(insights, key=lambda item: item.id)
    evaluations: list[InsightIntegrityEvaluation] = []

    for insight in ordered_insights:
        insight_type = str(insight.type)
        aggregation = _resolve_integrity_aggregation(insight.metric, metadata)
        counter_evidence: list[CounterEvidenceItem] = []
        contradictions = build_insight_contradictions(insight, insights)
        outlier_check: OutlierDependencyCheck | None = None
        one_off_check: OneOffEffectCheck | None = None
        consistency_checks: list[ConsistencyCheck] = []

        if insight_type == "CHANGE":
            counter_evidence = build_counter_evidence(
                insight,
                insights,
                relationships,
            )
            contradictions.extend(build_semantic_contradictions(insight))
            if (
                insight.dimension is None
                and insight.segment is None
                and aggregation == "SUM"
                and reconciliation_dimension is not None
            ):
                consistency_check = check_change_total_consistency(
                    insight,
                    dataframe,
                    dimension=reconciliation_dimension,
                    aggregation=aggregation,
                )
                if consistency_check is not None:
                    consistency_checks.append(consistency_check)

        elif insight_type == "TREND":
            contradictions.extend(build_semantic_contradictions(insight))
            if aggregation is not None:
                outlier_check = check_trend_outlier_dependency(
                    insight,
                    dataframe,
                    aggregation,
                    config=effective_config,
                )

        elif insight_type == "ANOMALY":
            if aggregation is not None:
                one_off_check = check_one_off_effect(
                    insight,
                    dataframe,
                    aggregation,
                    config=effective_config,
                )

        elif insight_type == "CONTRIBUTION":
            target = next(
                (
                    candidate
                    for candidate in ordered_insights
                    if candidate.type == "CHANGE"
                    and candidate.analysis_id == insight.analysis_id
                    and candidate.metric == insight.metric
                    and candidate.period == insight.period
                    and candidate.dimension is None
                    and candidate.segment is None
                ),
                None,
            )
            if target is not None:
                consistency_check = check_contribution_consistency(
                    insight,
                    target,
                )
                if consistency_check is not None:
                    consistency_checks.append(consistency_check)

        evaluations.append(
            build_integrity_evaluation(
                insight,
                counter_evidence=counter_evidence,
                contradictions=contradictions,
                outlier_check=outlier_check,
                one_off_check=one_off_check,
                consistency_checks=consistency_checks,
                config=effective_config,
            )
        )

    return InsightIntegrityResult(evaluations=evaluations)


def _resolve_integrity_aggregation(
    metric: str,
    metadata: dict[str, Any],
) -> str | None:
    for section_name in ("columns", "derivedMetrics"):
        section = metadata.get(section_name)
        if not isinstance(section, dict):
            continue
        metric_metadata = section.get(metric)
        if not isinstance(metric_metadata, dict):
            continue
        aggregation = str(metric_metadata.get("aggregation", "")).upper()
        return aggregation if aggregation in {"SUM", "AVG"} else None
    return None


def _resolve_reconciliation_dimension(
    metadata: dict[str, Any],
    dataframe: pd.DataFrame,
) -> str | None:
    columns = metadata.get("columns")
    if not isinstance(columns, dict):
        return None

    dimensions = sorted(
        name
        for name, column_metadata in columns.items()
        if isinstance(column_metadata, dict)
        and column_metadata.get("role") == "DIMENSION"
        and name in dataframe.columns
    )
    if "Region" in dimensions:
        return "Region"
    return dimensions[0] if dimensions else None


def _valid_score_mapping(
    mapping: object,
    expected_keys: set[str],
) -> bool:
    return (
        isinstance(mapping, dict)
        and set(mapping) == expected_keys
        and all(
            _is_finite_number(value) and 0.0 <= float(value) <= 1.0
            for value in mapping.values()
        )
    )


def _reconciliation_totals(
    dataframe: pd.DataFrame,
    *,
    metric: str,
    dimension: str,
    period: str,
) -> tuple[float, float] | None:
    period_mask = dataframe["Date"].dt.to_period("M").astype(str) == period
    period_data = dataframe.loc[period_mask, [dimension, metric]]
    metric_values = period_data[metric].dropna()
    if metric_values.empty:
        return None

    whole_total = float(metric_values.sum())
    grouped_total = float(
        period_data.groupby(dimension, dropna=True)[metric].sum().sum()
    )
    return whole_total, grouped_total


def _valid_tolerance(tolerance: object) -> bool:
    return (
        _is_finite_number(tolerance)
        and float(tolerance) >= 0
    )


def _is_finite_number(value: object) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, Real)
        and math.isfinite(float(value))
    )


def _build_trend_monthly_series(
    dataframe: pd.DataFrame,
    *,
    metric: str,
    dimension: str,
    segment: str,
    aggregation: str,
    period_start: str,
    period_end: str,
) -> pd.DataFrame:
    segment_data = dataframe.loc[dataframe[dimension] == segment].copy()
    if segment_data.empty:
        return pd.DataFrame(columns=["period", "value"])

    segment_data["period"] = (
        segment_data["Date"].dt.to_period("M").astype(str)
    )
    segment_data = segment_data.loc[
        segment_data["period"].between(period_start, period_end)
    ]
    grouped = segment_data.groupby("period", as_index=False)[metric]
    if aggregation.upper() == "SUM":
        monthly = grouped.sum()
    else:
        monthly = grouped.mean()

    return (
        monthly.rename(columns={metric: "value"})
        .sort_values("period")
        .reset_index(drop=True)
    )


def _calculate_slope_reduction(
    original_slope: float,
    adjusted_slope: float,
) -> float:
    original_magnitude = abs(original_slope)
    if original_magnitude == 0:
        return 0.0

    return max(
        0.0,
        (original_magnitude - abs(adjusted_slope)) / original_magnitude,
    )


def _no_material_outlier_check(
    original_slope: float,
    reason: str,
) -> OutlierDependencyCheck:
    return OutlierDependencyCheck(
        level=IntegrityRiskLevel.NONE,
        detected=False,
        statisticName="TREND_SLOPE",
        originalStatistic=original_slope,
        adjustedStatistic=original_slope,
        outlierPeriod=None,
        reason=reason,
    )


def _directions_oppose(left: str, right: str) -> bool:
    return {left, right} in ({"UP", "DOWN"}, {"HIGH", "LOW"})
