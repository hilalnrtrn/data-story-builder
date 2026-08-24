from enum import Enum
import math
from typing import Any

from app.config.insight_config_loader import load_insight_config
from app.models.business_relevance import (
    BusinessImpactDirection,
    BusinessRelevanceComponent,
    BusinessRelevanceEvaluation,
    BusinessRelevanceResult,
    PriorityEvaluation,
    PriorityLevel,
    RankedInsight,
)
from app.models.insight import Insight
from app.models.relationship import Relationship


def resolve_business_metric_metadata(
    metric: str,
    metadata: dict[str, Any],
) -> dict[str, Any] | None:
    for section_name in ("columns", "derivedMetrics"):
        section = metadata.get(section_name)
        if not isinstance(section, dict):
            continue

        metric_metadata = section.get(metric)
        if (
            isinstance(metric_metadata, dict)
            and metric_metadata.get("role") == "METRIC"
        ):
            return metric_metadata

    return None


def resolve_business_priority(
    metric: str,
    metadata: dict[str, Any],
) -> float | None:
    metric_metadata = resolve_business_metric_metadata(metric, metadata)
    if metric_metadata is None:
        return None

    priority = metric_metadata.get("businessPriority")
    if isinstance(priority, bool) or not isinstance(priority, (int, float)):
        return None

    normalized_priority = float(priority)
    if (
        not math.isfinite(normalized_priority)
        or not 0.0 <= normalized_priority <= 1.0
    ):
        return None

    return normalized_priority


def resolve_metric_directionality(
    metric: str,
    metadata: dict[str, Any],
) -> str | None:
    metric_metadata = resolve_business_metric_metadata(metric, metadata)
    if metric_metadata is None:
        return None

    directionality = metric_metadata.get("directionality")
    if directionality not in {
        "HIGHER_IS_BETTER",
        "LOWER_IS_BETTER",
        "CONTEXT_DEPENDENT",
    }:
        return None

    return directionality


def resolve_business_impact_direction(
    insight: Insight,
    metadata: dict[str, Any],
) -> BusinessImpactDirection | None:
    directionality = resolve_metric_directionality(
        insight.metric,
        metadata,
    )
    if directionality is None:
        return None

    analytical_direction = _enum_value(insight.direction)

    if analytical_direction == "STABLE":
        return BusinessImpactDirection.NEUTRAL

    if analytical_direction not in {"UP", "DOWN", "HIGH", "LOW"}:
        return None

    if directionality == "CONTEXT_DEPENDENT":
        return BusinessImpactDirection.CONTEXT_DEPENDENT

    favorable_direction = analytical_direction in {"UP", "HIGH"}
    if directionality == "HIGHER_IS_BETTER":
        return (
            BusinessImpactDirection.POSITIVE
            if favorable_direction
            else BusinessImpactDirection.NEGATIVE
        )

    if directionality == "LOWER_IS_BETTER":
        return (
            BusinessImpactDirection.NEGATIVE
            if favorable_direction
            else BusinessImpactDirection.POSITIVE
        )

    return None


def build_business_impact_reason(
    insight: Insight,
    metadata: dict[str, Any],
) -> str | None:
    directionality = resolve_metric_directionality(
        insight.metric,
        metadata,
    )
    impact_direction = resolve_business_impact_direction(
        insight,
        metadata,
    )
    if directionality is None or impact_direction is None:
        return None

    analytical_direction = _enum_value(insight.direction)

    return (
        f"{insight.metric} moved {analytical_direction} and is configured "
        f"as {directionality}."
    )


def build_metric_criticality_component(
    insight: Insight,
    metadata: dict[str, Any],
) -> BusinessRelevanceComponent | None:
    priority = resolve_business_priority(insight.metric, metadata)
    if priority is None:
        return None

    return BusinessRelevanceComponent(
        name="metricCriticality",
        score=priority,
        reason=(
            f"{insight.metric} has configured business priority "
            f"{priority:.2f}."
        ),
    )


def build_direction_impact_component(
    insight: Insight,
    metadata: dict[str, Any],
) -> BusinessRelevanceComponent | None:
    impact_direction = resolve_business_impact_direction(
        insight,
        metadata,
    )
    reason = build_business_impact_reason(insight, metadata)
    if impact_direction is None or reason is None:
        return None

    impact_scores = {
        BusinessImpactDirection.POSITIVE: 1.0,
        BusinessImpactDirection.NEGATIVE: 1.0,
        BusinessImpactDirection.MIXED: 0.75,
        BusinessImpactDirection.CONTEXT_DEPENDENT: 0.5,
        BusinessImpactDirection.NEUTRAL: 0.25,
    }

    return BusinessRelevanceComponent(
        name="directionImpact",
        score=impact_scores[impact_direction],
        reason=reason,
    )


def build_business_relevance_components(
    insight: Insight,
    metadata: dict[str, Any],
    relationships: list[Relationship] | None = None,
) -> list[BusinessRelevanceComponent]:
    components: list[BusinessRelevanceComponent] = []
    component_names: set[str] = set()

    candidate_components = [
        build_metric_criticality_component(insight, metadata),
        build_direction_impact_component(insight, metadata),
    ]
    if relationships is not None:
        candidate_components.append(
            build_relationship_context_component(insight, relationships)
        )

    for component in candidate_components:
        if component is None or component.name in component_names:
            continue

        components.append(component)
        component_names.add(component.name)

    return components


def build_relationship_context_component(
    insight: Insight,
    relationships: list[Relationship],
    config: dict[str, Any] | None = None,
) -> BusinessRelevanceComponent | None:
    resolved_config = load_insight_config() if config is None else config
    if not isinstance(resolved_config, dict):
        return None

    business_relevance = resolved_config.get("businessRelevance")
    if not isinstance(business_relevance, dict):
        return None

    relationship_context = business_relevance.get("relationshipContext")
    if not isinstance(relationship_context, dict):
        return None

    type_weights = relationship_context.get("typeWeights")
    if not isinstance(type_weights, dict) or not type_weights:
        return None

    normalized_weights: dict[str, float] = {}
    for relationship_type, weight in type_weights.items():
        if (
            not isinstance(relationship_type, str)
            or isinstance(weight, bool)
            or not isinstance(weight, (int, float))
        ):
            return None

        normalized_weight = float(weight)
        if (
            not math.isfinite(normalized_weight)
            or not 0.0 <= normalized_weight <= 1.0
        ):
            return None
        normalized_weights[relationship_type] = normalized_weight

    if not math.isclose(
        sum(normalized_weights.values()),
        1.0,
        rel_tol=1e-9,
        abs_tol=1e-9,
    ):
        return None

    maximum_evidence: dict[str, float] = {}
    for relationship in relationships:
        if relationship.analysis_id != insight.analysis_id:
            continue
        if insight.id not in {
            relationship.source_insight_id,
            relationship.target_insight_id,
        }:
            continue

        relationship_type = _enum_value(relationship.type)
        if relationship_type not in normalized_weights:
            continue

        edge_evidence = relationship.strength * relationship.confidence
        maximum_evidence[relationship_type] = max(
            edge_evidence,
            maximum_evidence.get(relationship_type, 0.0),
        )

    contributing_types = [
        relationship_type
        for relationship_type in normalized_weights
        if relationship_type in maximum_evidence
    ]
    if not contributing_types:
        return None

    available_weight = sum(
        normalized_weights[relationship_type]
        for relationship_type in contributing_types
    )
    if available_weight == 0.0:
        return None

    weighted_evidence = sum(
        maximum_evidence[relationship_type]
        * normalized_weights[relationship_type]
        for relationship_type in contributing_types
    )
    score = round(weighted_evidence / available_weight, 6)
    reason = (
        "Relationship context supported by "
        f"{', '.join(contributing_types)}."
    )

    return BusinessRelevanceComponent(
        name="relationshipContext",
        score=score,
        reason=reason,
    )


def calculate_business_relevance_score(
    components: list[BusinessRelevanceComponent],
    config: dict[str, Any] | None = None,
) -> float | None:
    if not components:
        return None

    resolved_config = load_insight_config() if config is None else config
    if not isinstance(resolved_config, dict):
        return None

    business_relevance = resolved_config.get("businessRelevance")
    if not isinstance(business_relevance, dict):
        return None

    weights = business_relevance.get("weights")
    if not isinstance(weights, dict) or not weights:
        return None

    normalized_weights: dict[str, float] = {}
    for name, weight in weights.items():
        if (
            not isinstance(name, str)
            or isinstance(weight, bool)
            or not isinstance(weight, (int, float))
        ):
            return None

        normalized_weight = float(weight)
        if (
            not math.isfinite(normalized_weight)
            or not 0.0 <= normalized_weight <= 1.0
        ):
            return None
        normalized_weights[name] = normalized_weight

    if not math.isclose(
        sum(normalized_weights.values()),
        1.0,
        rel_tol=1e-9,
        abs_tol=1e-9,
    ):
        return None

    available_components = [
        component
        for component in components
        if component.name in normalized_weights
    ]
    if not available_components:
        return None

    available_weight = sum(
        normalized_weights[component.name]
        for component in available_components
    )
    if available_weight == 0.0:
        return None

    weighted_score = sum(
        component.score * normalized_weights[component.name]
        for component in available_components
    )
    return round(weighted_score / available_weight, 6)


def evaluate_business_relevance(
    insight: Insight,
    metadata: dict[str, Any],
    config: dict[str, Any] | None = None,
    relationships: list[Relationship] | None = None,
) -> BusinessRelevanceEvaluation | None:
    components = build_business_relevance_components(
        insight,
        metadata,
        relationships,
    )
    business_relevance = calculate_business_relevance_score(
        components,
        config,
    )
    impact_direction = resolve_business_impact_direction(insight, metadata)
    if business_relevance is None or impact_direction is None:
        return None

    reasons: list[str] = []
    for component in components:
        if component.reason not in reasons:
            reasons.append(component.reason)

    return BusinessRelevanceEvaluation(
        insightId=insight.id,
        businessRelevance=business_relevance,
        impactDirection=impact_direction,
        components=components,
        reasons=reasons,
    )


def calculate_priority_score(
    insight: Insight,
    business_relevance: BusinessRelevanceEvaluation,
    config: dict[str, Any] | None = None,
) -> float | None:
    importance = _unit_float(insight.importance)
    relevance = _unit_float(business_relevance.business_relevance)
    confidence = _unit_float(insight.confidence)
    if importance is None or relevance is None or confidence is None:
        return None

    resolved_config = load_insight_config() if config is None else config
    if not isinstance(resolved_config, dict):
        return None

    business_relevance_config = resolved_config.get("businessRelevance")
    if not isinstance(business_relevance_config, dict):
        return None

    priority = business_relevance_config.get("priority")
    if not isinstance(priority, dict):
        return None

    weights = priority.get("weights")
    required_keys = {
        "importance",
        "businessRelevance",
        "confidence",
    }
    if not isinstance(weights, dict) or set(weights) != required_keys:
        return None

    normalized_weights: dict[str, float] = {}
    for name, weight in weights.items():
        normalized_weight = _unit_float(weight)
        if normalized_weight is None:
            return None
        normalized_weights[name] = normalized_weight

    if not math.isclose(
        sum(normalized_weights.values()),
        1.0,
        rel_tol=1e-9,
        abs_tol=1e-9,
    ):
        return None

    score = (
        importance * normalized_weights["importance"]
        + relevance * normalized_weights["businessRelevance"]
        + confidence * normalized_weights["confidence"]
    )
    return round(score, 6)


def resolve_priority_level(
    priority_score: float,
    config: dict[str, Any] | None = None,
) -> PriorityLevel | None:
    normalized_score = _unit_float(priority_score)
    if normalized_score is None:
        return None

    resolved_config = load_insight_config() if config is None else config
    if not isinstance(resolved_config, dict):
        return None

    business_relevance = resolved_config.get("businessRelevance")
    if not isinstance(business_relevance, dict):
        return None

    priority = business_relevance.get("priority")
    if not isinstance(priority, dict):
        return None

    thresholds = priority.get("thresholds")
    if not isinstance(thresholds, dict):
        return None

    normalized_thresholds: dict[str, float] = {}
    for name in ("critical", "high", "medium"):
        threshold = _unit_float(thresholds.get(name))
        if threshold is None:
            return None
        normalized_thresholds[name] = threshold

    if not (
        normalized_thresholds["critical"]
        > normalized_thresholds["high"]
        > normalized_thresholds["medium"]
    ):
        return None

    if normalized_score >= normalized_thresholds["critical"]:
        return PriorityLevel.CRITICAL
    if normalized_score >= normalized_thresholds["high"]:
        return PriorityLevel.HIGH
    if normalized_score >= normalized_thresholds["medium"]:
        return PriorityLevel.MEDIUM
    return PriorityLevel.LOW


def evaluate_priority(
    insight: Insight,
    business_relevance: BusinessRelevanceEvaluation,
    config: dict[str, Any] | None = None,
) -> PriorityEvaluation | None:
    if business_relevance.insight_id != insight.id:
        return None

    priority_score = calculate_priority_score(
        insight,
        business_relevance,
        config,
    )
    if priority_score is None:
        return None

    priority_level = resolve_priority_level(priority_score, config)
    if priority_level is None:
        return None

    importance = _unit_float(insight.importance)
    relevance = _unit_float(business_relevance.business_relevance)
    confidence = _unit_float(insight.confidence)
    if importance is None or relevance is None or confidence is None:
        return None

    level_value = _enum_value(priority_level)
    return PriorityEvaluation(
        insightId=insight.id,
        priorityScore=priority_score,
        priorityLevel=priority_level,
        breakdown={
            "importance": importance,
            "businessRelevance": relevance,
            "confidence": confidence,
        },
        reasons=[
            f"Analytical importance: {importance:.2f}.",
            f"Business relevance: {relevance:.2f}.",
            f"Confidence: {confidence:.2f}.",
            (
                f"Priority score {priority_score:.2f} maps to "
                f"{level_value}."
            ),
        ],
    )


def rank_insights(
    insights: list[Insight],
    business_evaluations: list[BusinessRelevanceEvaluation],
    priority_evaluations: list[PriorityEvaluation],
) -> list[RankedInsight]:
    business_by_insight_id = {
        evaluation.insight_id: evaluation
        for evaluation in business_evaluations
    }
    priority_by_insight_id = {
        evaluation.insight_id: evaluation
        for evaluation in priority_evaluations
    }

    candidates: list[
        tuple[
            str,
            PriorityEvaluation,
            BusinessRelevanceEvaluation,
            float,
            float,
        ]
    ] = []
    for insight in insights:
        business_evaluation = business_by_insight_id.get(insight.id)
        priority_evaluation = priority_by_insight_id.get(insight.id)
        if business_evaluation is None or priority_evaluation is None:
            continue

        importance = _unit_float(
            priority_evaluation.breakdown.get("importance")
        )
        confidence = _unit_float(
            priority_evaluation.breakdown.get("confidence")
        )
        if importance is None or confidence is None:
            continue

        candidates.append(
            (
                insight.id,
                priority_evaluation,
                business_evaluation,
                importance,
                confidence,
            )
        )

    candidates.sort(
        key=lambda candidate: (
            -candidate[1].priority_score,
            -candidate[2].business_relevance,
            -candidate[3],
            -candidate[4],
            candidate[0],
        )
    )

    return [
        RankedInsight(
            rank=rank,
            insightId=insight_id,
            priority=priority,
            businessRelevance=business_relevance,
        )
        for rank, (
            insight_id,
            priority,
            business_relevance,
            _,
            _,
        ) in enumerate(candidates, start=1)
    ]


def select_top_ranked_insights(
    ranked_insights: list[RankedInsight],
    *,
    top_n: int,
) -> list[RankedInsight]:
    if isinstance(top_n, bool) or not isinstance(top_n, int) or top_n <= 0:
        return []

    return ranked_insights[:top_n]


def build_ranking_reason(ranked: RankedInsight) -> str:
    priority = ranked.priority
    business_relevance = ranked.business_relevance
    importance = priority.breakdown["importance"]
    confidence = priority.breakdown["confidence"]
    priority_level = _enum_value(priority.priority_level)

    return (
        f"Rank #{ranked.rank} with {priority_level} priority "
        f"({priority.priority_score:.2f}): business relevance "
        f"{business_relevance.business_relevance:.2f}, analytical "
        f"importance {importance:.2f}, confidence {confidence:.2f}."
    )


def analyze_business_relevance(
    insights: list[Insight],
    relationships: list[Relationship],
    metadata: dict[str, Any],
    *,
    top_n: int = 5,
    config: dict[str, Any] | None = None,
) -> BusinessRelevanceResult:
    business_evaluations: list[BusinessRelevanceEvaluation] = []
    priority_evaluations: list[PriorityEvaluation] = []

    for insight in insights:
        business_evaluation = evaluate_business_relevance(
            insight,
            metadata,
            config,
            relationships,
        )
        if business_evaluation is None:
            continue
        business_evaluations.append(business_evaluation)

        priority_evaluation = evaluate_priority(
            insight,
            business_evaluation,
            config,
        )
        if priority_evaluation is not None:
            priority_evaluations.append(priority_evaluation)

    ranked_insights = rank_insights(
        insights,
        business_evaluations,
        priority_evaluations,
    )
    top_ranked_insights = select_top_ranked_insights(
        ranked_insights,
        top_n=top_n,
    )

    return BusinessRelevanceResult(
        businessEvaluations=business_evaluations,
        priorityEvaluations=priority_evaluations,
        rankedInsights=ranked_insights,
        topRankedInsights=top_ranked_insights,
    )


def _unit_float(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None

    normalized_value = float(value)
    if (
        not math.isfinite(normalized_value)
        or not 0.0 <= normalized_value <= 1.0
    ):
        return None

    return normalized_value


def _enum_value(value: str | Enum) -> str:
    if isinstance(value, Enum):
        return str(value.value)

    return value
