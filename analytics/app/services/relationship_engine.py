from enum import Enum
import math
from numbers import Real
from typing import Any

from app.config.insight_config_loader import load_insight_config
from app.models.insight import Insight
from app.models.relationship import Relationship, RelationshipType


def generate_relationships(
    insights: list[Insight],
    config: dict[str, Any] | None = None,
) -> list[Relationship]:
    insight_ids: set[str] = set()
    for insight in insights:
        if insight.id in insight_ids:
            raise ValueError(f"Duplicate Insight ID: {insight.id}")
        insight_ids.add(insight.id)

    analysis_ids = {insight.analysis_id for insight in insights}
    if len(analysis_ids) > 1:
        raise ValueError("Insights must belong to the same analysis")

    if len(insights) < 2:
        return []

    ordered_insights = sorted(insights, key=lambda insight: insight.id)
    change_targets = [
        insight
        for insight in ordered_insights
        if _enum_value(insight.type) == "CHANGE"
    ]

    relationship_config = config
    if len(change_targets) > 1 and relationship_config is None:
        relationship_config = load_insight_config()

    relationships_by_id: dict[str, Relationship] = {}

    def collect(relationship: Relationship | None) -> None:
        if relationship is None:
            return

        existing = relationships_by_id.get(relationship.id)
        if existing is None:
            relationships_by_id[relationship.id] = relationship
            return

        if existing.model_dump(by_alias=True) != relationship.model_dump(
            by_alias=True
        ):
            raise ValueError(
                f"Conflicting generated Relationship ID: {relationship.id}"
            )

    for source in ordered_insights:
        source_type = _enum_value(source.type)
        if source_type not in {"CONTRIBUTION", "ANOMALY", "CHANGE"}:
            continue

        for target in change_targets:
            if source.id == target.id:
                continue

            if source_type == "CONTRIBUTION":
                collect(build_contributes_to_relationship(source, target))
            elif source_type == "ANOMALY":
                collect(build_related_anomaly_relationship(source, target))
            else:
                change_config = (
                    relationship_config
                    if relationship_config is not None
                    else {}
                )
                collect(
                    build_counter_signal_relationship(
                        source,
                        target,
                        change_config,
                    )
                )
                collect(
                    build_co_moves_with_relationship(
                        source,
                        target,
                        change_config,
                    )
                )

    return sorted(relationships_by_id.values(), key=lambda item: item.id)


def same_analysis(source: Insight, target: Insight) -> bool:
    return source.analysis_id == target.analysis_id


def same_period(source: Insight, target: Insight) -> bool:
    return (
        _enum_value(source.period_granularity)
        == _enum_value(target.period_granularity)
        and source.period == target.period
    )


def anomaly_matches_change_period(
    anomaly: Insight,
    change: Insight,
) -> bool:
    if (
        _enum_value(anomaly.period_granularity)
        != _enum_value(change.period_granularity)
        or not isinstance(anomaly.period, dict)
        or not isinstance(change.period, dict)
    ):
        return False

    anomaly_current = anomaly.period.get("current")
    change_current = change.period.get("current")

    return (
        anomaly_current is not None
        and change_current is not None
        and anomaly_current == change_current
    )


def anomaly_direction_matches_change(
    anomaly: Insight,
    change: Insight,
) -> bool:
    anomaly_direction = _enum_value(anomaly.direction)
    change_direction = _enum_value(change.direction)

    return (
        anomaly_direction == "HIGH"
        and change_direction == "UP"
    ) or (
        anomaly_direction == "LOW"
        and change_direction == "DOWN"
    )


def same_metric(source: Insight, target: Insight) -> bool:
    return source.metric == target.metric


def is_related_anomaly(
    source: Insight,
    target: Insight,
) -> bool:
    return (
        source.id != target.id
        and same_analysis(source, target)
        and _enum_value(source.type) == "ANOMALY"
        and _enum_value(target.type) == "CHANGE"
        and same_metric(source, target)
        and source.dimension is not None
        and source.segment is not None
        and target.dimension is None
        and target.segment is None
        and anomaly_matches_change_period(source, target)
        and anomaly_direction_matches_change(source, target)
    )


def build_related_anomaly_relationship(
    source: Insight,
    target: Insight,
) -> Relationship | None:
    if not is_related_anomaly(source, target):
        return None

    strength_breakdown = {
        "temporalCompatibility": 1.0,
        "metricCompatibility": 1.0,
        "directionalCompatibility": 1.0,
        "structuralCompatibility": 1.0,
    }
    strength = sum(strength_breakdown.values()) / len(strength_breakdown)

    confidence_breakdown = {
        "sourceInsightConfidence": _unit_confidence(source.confidence),
        "targetInsightConfidence": _unit_confidence(target.confidence),
        "semanticCompatibility": 1.0,
    }
    confidence = sum(confidence_breakdown.values()) / len(confidence_breakdown)

    anomaly_direction = _enum_value(source.direction)
    change_direction = _enum_value(target.direction)
    current_period = source.period["current"]

    return Relationship(
        id=f"RELATED_ANOMALY-{source.id}-{target.id}",
        analysisId=source.analysis_id,
        sourceInsightId=source.id,
        targetInsightId=target.id,
        type=RelationshipType.RELATED_ANOMALY,
        strength=strength,
        confidence=confidence,
        strengthBreakdown=strength_breakdown,
        confidenceBreakdown=confidence_breakdown,
        reasons=[
            f"Same metric: {source.metric}",
            (
                f"Anomaly current period {current_period} matches "
                "company-level change current period"
            ),
            (
                f"Segment anomaly direction {anomaly_direction} is compatible "
                f"with company-level change direction {change_direction}"
            ),
        ],
        metadata={
            "metric": source.metric,
            "dimension": source.dimension,
            "segment": source.segment,
            "anomalyDirection": anomaly_direction,
            "changeDirection": change_direction,
            "currentPeriod": current_period,
        },
    )


def same_dimension(source: Insight, target: Insight) -> bool:
    return (
        source.dimension is not None
        and target.dimension is not None
        and source.dimension == target.dimension
    )


def same_segment(source: Insight, target: Insight) -> bool:
    return (
        source.segment is not None
        and target.segment is not None
        and source.segment == target.segment
    )


def same_direction(source: Insight, target: Insight) -> bool:
    source_direction = _enum_value(source.direction)
    target_direction = _enum_value(target.direction)

    return (
        source_direction in {"UP", "DOWN"}
        and source_direction == target_direction
    )


def opposite_direction(source: Insight, target: Insight) -> bool:
    directions = {
        _enum_value(source.direction),
        _enum_value(target.direction),
    }

    return directions == {"UP", "DOWN"}


def metrics_are_compatible(
    source: Insight,
    target: Insight,
    relationship_type: RelationshipType | str,
    config: dict[str, Any],
) -> bool:
    relationship_config = config.get("relationship")
    if not isinstance(relationship_config, dict):
        return False

    metric_compatibility = relationship_config.get("metricCompatibility")
    if not isinstance(metric_compatibility, dict):
        return False

    configured_pairs = metric_compatibility.get(
        _enum_value(relationship_type)
    )
    if not isinstance(configured_pairs, list):
        return False

    return any(
        isinstance(pair, dict)
        and pair.get("sourceMetric") == source.metric
        and pair.get("targetMetric") == target.metric
        for pair in configured_pairs
    )


def is_co_moves_with(
    source: Insight,
    target: Insight,
    config: dict[str, Any],
) -> bool:
    return (
        source.id != target.id
        and same_analysis(source, target)
        and _enum_value(source.type) == "CHANGE"
        and _enum_value(target.type) == "CHANGE"
        and source.dimension is None
        and source.segment is None
        and target.dimension is None
        and target.segment is None
        and same_period(source, target)
        and metrics_are_compatible(
            source,
            target,
            RelationshipType.CO_MOVES_WITH,
            config,
        )
        and same_direction(source, target)
    )


def build_co_moves_with_relationship(
    source: Insight,
    target: Insight,
    config: dict[str, Any],
) -> Relationship | None:
    if not is_co_moves_with(source, target, config):
        return None

    strength_breakdown = {
        "temporalCompatibility": 1.0,
        "metricCompatibility": 1.0,
        "directionalAlignment": 1.0,
        "structuralCompatibility": 1.0,
    }
    strength = sum(strength_breakdown.values()) / len(strength_breakdown)

    confidence_breakdown = {
        "sourceInsightConfidence": _unit_confidence(source.confidence),
        "targetInsightConfidence": _unit_confidence(target.confidence),
        "semanticCompatibility": 1.0,
    }
    confidence = sum(confidence_breakdown.values()) / len(confidence_breakdown)

    source_direction = _enum_value(source.direction)
    target_direction = _enum_value(target.direction)

    return Relationship(
        id=f"CO_MOVES_WITH-{source.id}-{target.id}",
        analysisId=source.analysis_id,
        sourceInsightId=source.id,
        targetInsightId=target.id,
        type=RelationshipType.CO_MOVES_WITH,
        strength=strength,
        confidence=confidence,
        strengthBreakdown=strength_breakdown,
        confidenceBreakdown=confidence_breakdown,
        reasons=[
            _comparison_period_reason(source),
            (
                "Configured CO_MOVES_WITH metric pair: "
                f"{source.metric} -> {target.metric}"
            ),
            (
                f"{source.metric} and {target.metric} both moved "
                f"{source_direction}"
            ),
        ],
        metadata={
            "sourceMetric": source.metric,
            "targetMetric": target.metric,
            "sourceDirection": source_direction,
            "targetDirection": target_direction,
        },
    )


def is_counter_signal(
    source: Insight,
    target: Insight,
    config: dict[str, Any],
) -> bool:
    return (
        source.id != target.id
        and same_analysis(source, target)
        and _enum_value(source.type) == "CHANGE"
        and _enum_value(target.type) == "CHANGE"
        and source.dimension is None
        and source.segment is None
        and target.dimension is None
        and target.segment is None
        and same_period(source, target)
        and metrics_are_compatible(
            source,
            target,
            RelationshipType.COUNTER_SIGNAL,
            config,
        )
        and opposite_direction(source, target)
    )


def build_counter_signal_relationship(
    source: Insight,
    target: Insight,
    config: dict[str, Any],
) -> Relationship | None:
    if not is_counter_signal(source, target, config):
        return None

    strength_breakdown = {
        "temporalCompatibility": 1.0,
        "metricCompatibility": 1.0,
        "directionalOpposition": 1.0,
        "structuralCompatibility": 1.0,
    }
    strength = sum(strength_breakdown.values()) / len(strength_breakdown)

    confidence_breakdown = {
        "sourceInsightConfidence": _unit_confidence(source.confidence),
        "targetInsightConfidence": _unit_confidence(target.confidence),
        "semanticCompatibility": 1.0,
    }
    confidence = sum(confidence_breakdown.values()) / len(confidence_breakdown)

    source_direction = _enum_value(source.direction)
    target_direction = _enum_value(target.direction)

    return Relationship(
        id=f"COUNTER_SIGNAL-{source.id}-{target.id}",
        analysisId=source.analysis_id,
        sourceInsightId=source.id,
        targetInsightId=target.id,
        type=RelationshipType.COUNTER_SIGNAL,
        strength=strength,
        confidence=confidence,
        strengthBreakdown=strength_breakdown,
        confidenceBreakdown=confidence_breakdown,
        reasons=[
            _comparison_period_reason(source),
            (
                "Configured COUNTER_SIGNAL metric pair: "
                f"{source.metric} -> {target.metric}"
            ),
            (
                f"{source.metric} moved {source_direction} while "
                f"{target.metric} moved {target_direction}"
            ),
        ],
        metadata={
            "sourceMetric": source.metric,
            "targetMetric": target.metric,
            "sourceDirection": source_direction,
            "targetDirection": target_direction,
        },
    )


def is_contributes_to(source: Insight, target: Insight) -> bool:
    if (
        source.id == target.id
        or not same_analysis(source, target)
        or _enum_value(source.type) != "CONTRIBUTION"
        or _enum_value(target.type) != "CHANGE"
        or not same_metric(source, target)
        or not same_period(source, target)
        or source.dimension is None
        or source.segment is None
        or target.dimension is not None
        or target.segment is not None
    ):
        return False

    return all(
        _numbers_match(source.values.get(source_key), target.values.get(target_key))
        for source_key, target_key in (
            ("totalPreviousValue", "previous"),
            ("totalCurrentValue", "current"),
            ("totalAbsoluteChange", "absoluteChange"),
        )
    )


def build_contributes_to_relationship(
    source: Insight,
    target: Insight,
) -> Relationship | None:
    if not is_contributes_to(source, target):
        return None

    strength_breakdown = {
        "temporalCompatibility": 1.0,
        "metricCompatibility": 1.0,
        "structuralCompatibility": 1.0,
        "arithmeticCompatibility": 1.0,
    }
    strength = sum(strength_breakdown.values()) / len(strength_breakdown)

    confidence_breakdown = {
        "sourceInsightConfidence": _unit_confidence(source.confidence),
        "targetInsightConfidence": _unit_confidence(target.confidence),
        "arithmeticVerification": 1.0,
    }
    confidence = sum(confidence_breakdown.values()) / len(confidence_breakdown)

    reasons = [
        f"Same metric: {source.metric}",
        _comparison_period_reason(source),
        f"Contribution totals match the company-level {target.metric} change",
    ]
    metadata = {
        "dimension": source.dimension,
        "segment": source.segment,
    }

    contribution_share = source.values.get("contributionShare")
    if _is_finite_number(contribution_share):
        numeric_share = float(contribution_share)
        metadata["contributionShare"] = numeric_share
        reasons.append(
            f"{source.segment} contributed {numeric_share:.1%} "
            f"of the total {target.metric} change"
        )

    return Relationship(
        id=f"CONTRIBUTES_TO-{source.id}-{target.id}",
        analysisId=source.analysis_id,
        sourceInsightId=source.id,
        targetInsightId=target.id,
        type=RelationshipType.CONTRIBUTES_TO,
        strength=strength,
        confidence=confidence,
        strengthBreakdown=strength_breakdown,
        confidenceBreakdown=confidence_breakdown,
        reasons=reasons,
        metadata=metadata,
    )


def _numbers_match(left: object, right: object) -> bool:
    if (
        isinstance(left, bool)
        or isinstance(right, bool)
        or not isinstance(left, Real)
        or not isinstance(right, Real)
    ):
        return False

    left_value = float(left)
    right_value = float(right)

    return (
        math.isfinite(left_value)
        and math.isfinite(right_value)
        and math.isclose(left_value, right_value, rel_tol=0.0, abs_tol=1e-9)
    )


def _unit_confidence(value: object) -> float:
    if not _is_finite_number(value):
        return 0.5

    numeric_value = float(value)
    if not 0.0 <= numeric_value <= 1.0:
        return 0.5

    return numeric_value


def _is_finite_number(value: object) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, Real)
        and math.isfinite(float(value))
    )


def _comparison_period_reason(insight: Insight) -> str:
    previous = insight.period.get("previous")
    current = insight.period.get("current")

    if previous is not None and current is not None:
        return f"Same comparison period: {previous} to {current}"

    return f"Same comparison period: {insight.period}"


def _enum_value(value: str | Enum) -> str:
    if isinstance(value, Enum):
        return str(value.value)

    return value
