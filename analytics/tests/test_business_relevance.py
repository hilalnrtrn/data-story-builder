import copy
import math

import pytest
from pydantic import ValidationError

from app.config.insight_config_loader import load_insight_config
from app.config.metadata_loader import load_dataset_metadata
from app.models.business_relevance import (
    BusinessImpactDirection,
    BusinessRelevanceComponent,
    BusinessRelevanceEvaluation,
    BusinessRelevanceResult,
    PriorityEvaluation,
    PriorityLevel,
    RankedInsight,
)
from app.models.insight import (
    Insight,
    InsightDirection,
    InsightType,
    PeriodGranularity,
)
from app.models.relationship import Relationship, RelationshipType
from app.services.business_relevance import (
    analyze_business_relevance,
    build_business_impact_reason,
    build_business_relevance_components,
    build_direction_impact_component,
    build_metric_criticality_component,
    build_ranking_reason,
    build_relationship_context_component,
    calculate_business_relevance_score,
    calculate_priority_score,
    evaluate_business_relevance,
    evaluate_priority,
    resolve_business_impact_direction,
    resolve_business_metric_metadata,
    resolve_business_priority,
    resolve_metric_directionality,
    resolve_priority_level,
    rank_insights,
    select_top_ranked_insights,
)


def _insight(
    metric: str,
    direction: InsightDirection | str,
) -> Insight:
    return Insight(
        id=f"CHANGE-{metric}",
        analysisId="analysis-business-relevance",
        type=InsightType.CHANGE,
        metric=metric,
        periodGranularity=PeriodGranularity.MONTH,
        period={"previous": "2025-08", "current": "2025-09"},
        direction=direction,
    )


def _relationship(
    relationship_type: RelationshipType,
    *,
    strength: float = 1.0,
    confidence: float = 1.0,
    analysis_id: str = "analysis-business-relevance",
    source_insight_id: str = "CHANGE-Revenue",
    target_insight_id: str = "CHANGE-Orders",
) -> Relationship:
    return Relationship(
        id=(
            f"{relationship_type.value}-{source_insight_id}-"
            f"{target_insight_id}"
        ),
        analysisId=analysis_id,
        sourceInsightId=source_insight_id,
        targetInsightId=target_insight_id,
        type=relationship_type,
        strength=strength,
        confidence=confidence,
    )


@pytest.mark.parametrize(
    ("metric", "direction", "expected"),
    [
        ("Revenue", InsightDirection.UP, BusinessImpactDirection.POSITIVE),
        ("Orders", InsightDirection.DOWN, BusinessImpactDirection.NEGATIVE),
        ("Returns", InsightDirection.UP, BusinessImpactDirection.NEGATIVE),
        ("Returns", InsightDirection.DOWN, BusinessImpactDirection.POSITIVE),
        ("ReturnRate", InsightDirection.UP, BusinessImpactDirection.NEGATIVE),
        (
            "Discount",
            InsightDirection.UP,
            BusinessImpactDirection.CONTEXT_DEPENDENT,
        ),
        ("Discount", InsightDirection.STABLE, BusinessImpactDirection.NEUTRAL),
    ],
)
def test_resolves_business_impact_direction(
    metric: str,
    direction: InsightDirection,
    expected: BusinessImpactDirection,
) -> None:
    metadata = load_dataset_metadata()

    assert resolve_business_impact_direction(
        _insight(metric, direction),
        metadata,
    ) == expected


def test_resolves_raw_metric_business_metadata() -> None:
    metadata = load_dataset_metadata()

    revenue = resolve_business_metric_metadata("Revenue", metadata)

    assert revenue is metadata["columns"]["Revenue"]
    assert revenue["businessPriority"] == 0.95


def test_resolves_derived_metric_business_metadata() -> None:
    metadata = load_dataset_metadata()

    return_rate = resolve_business_metric_metadata("ReturnRate", metadata)

    assert "ReturnRate" not in metadata["columns"]
    assert return_rate is metadata["derivedMetrics"]["ReturnRate"]
    assert return_rate["businessPriority"] == 0.90


def test_unknown_or_non_metric_metadata_returns_none() -> None:
    metadata = load_dataset_metadata()

    assert resolve_business_metric_metadata("UnknownMetric", metadata) is None
    assert resolve_business_metric_metadata("Region", metadata) is None


@pytest.mark.parametrize(
    "metric_metadata",
    [
        {"role": "METRIC"},
        {"role": "METRIC", "directionality": "UNSUPPORTED"},
    ],
    ids=["missing", "unsupported"],
)
def test_missing_or_unsupported_directionality_returns_none(
    metric_metadata: dict,
) -> None:
    metadata = {"columns": {"Metric": metric_metadata}}

    assert resolve_business_impact_direction(
        _insight("Metric", InsightDirection.UP),
        metadata,
    ) is None


def test_unsupported_analytical_direction_returns_none() -> None:
    metadata = {
        "columns": {
            "Metric": {
                "role": "METRIC",
                "directionality": "HIGHER_IS_BETTER",
            }
        }
    }
    insight = _insight("Metric", InsightDirection.UP)
    insight.direction = "UNSUPPORTED"

    assert resolve_business_impact_direction(insight, metadata) is None


@pytest.mark.parametrize(
    ("metric", "expected"),
    [
        ("Revenue", 0.95),
        ("ReturnRate", 0.90),
        ("Discount", 0.55),
        ("UnknownMetric", None),
    ],
)
def test_resolves_business_priority(
    metric: str,
    expected: float | None,
) -> None:
    metadata = load_dataset_metadata()

    assert resolve_business_priority(metric, metadata) == expected


@pytest.mark.parametrize(
    "priority",
    [None, -0.01, 1.01, True],
    ids=["missing", "below-zero", "above-one", "boolean"],
)
def test_invalid_business_priority_returns_none(priority: object) -> None:
    metric_metadata = {"role": "METRIC"}
    if priority is not None:
        metric_metadata["businessPriority"] = priority
    metadata = {"columns": {"Metric": metric_metadata}}

    assert resolve_business_priority("Metric", metadata) is None


@pytest.mark.parametrize(
    ("metric", "expected"),
    [
        ("Revenue", "HIGHER_IS_BETTER"),
        ("ReturnRate", "LOWER_IS_BETTER"),
        ("Discount", "CONTEXT_DEPENDENT"),
    ],
)
def test_resolves_metric_directionality(metric: str, expected: str) -> None:
    metadata = load_dataset_metadata()

    assert resolve_metric_directionality(metric, metadata) == expected


def test_unsupported_metric_directionality_returns_none() -> None:
    metadata = {
        "columns": {
            "Metric": {
                "role": "METRIC",
                "directionality": "UNSUPPORTED",
            }
        }
    }

    assert resolve_metric_directionality("Metric", metadata) is None


@pytest.mark.parametrize(
    ("metric", "direction", "expected"),
    [
        (
            "Revenue",
            InsightDirection.UP,
            "Revenue moved UP and is configured as HIGHER_IS_BETTER.",
        ),
        (
            "Orders",
            InsightDirection.DOWN,
            "Orders moved DOWN and is configured as HIGHER_IS_BETTER.",
        ),
        (
            "ReturnRate",
            InsightDirection.UP,
            "ReturnRate moved UP and is configured as LOWER_IS_BETTER.",
        ),
        (
            "Returns",
            InsightDirection.DOWN,
            "Returns moved DOWN and is configured as LOWER_IS_BETTER.",
        ),
        (
            "Discount",
            InsightDirection.UP,
            "Discount moved UP and is configured as CONTEXT_DEPENDENT.",
        ),
        (
            "Discount",
            InsightDirection.STABLE,
            "Discount moved STABLE and is configured as CONTEXT_DEPENDENT.",
        ),
    ],
)
def test_builds_deterministic_business_impact_reason(
    metric: str,
    direction: InsightDirection,
    expected: str,
) -> None:
    metadata = load_dataset_metadata()

    reason = build_business_impact_reason(
        _insight(metric, direction),
        metadata,
    )

    assert reason == expected
    assert "caused" not in reason.lower()
    assert "because" not in reason.lower()


def test_business_impact_reason_returns_none_for_unknown_metric() -> None:
    metadata = load_dataset_metadata()

    assert build_business_impact_reason(
        _insight("UnknownMetric", InsightDirection.UP),
        metadata,
    ) is None


def test_business_impact_reason_rejects_unsupported_directionality() -> None:
    metadata = {
        "columns": {
            "Metric": {
                "role": "METRIC",
                "directionality": "UNSUPPORTED",
            }
        }
    }

    assert build_business_impact_reason(
        _insight("Metric", InsightDirection.UP),
        metadata,
    ) is None


def test_builds_revenue_metric_criticality_component() -> None:
    metadata = load_dataset_metadata()

    component = build_metric_criticality_component(
        _insight("Revenue", InsightDirection.UP),
        metadata,
    )

    assert component is not None
    assert component.name == "metricCriticality"
    assert component.score == 0.95
    assert component.reason == (
        "Revenue has configured business priority 0.95."
    )


@pytest.mark.parametrize(
    ("metric", "expected_score", "expected_reason"),
    [
        (
            "ReturnRate",
            0.90,
            "ReturnRate has configured business priority 0.90.",
        ),
        (
            "Discount",
            0.55,
            "Discount has configured business priority 0.55.",
        ),
    ],
)
def test_builds_metric_criticality_from_configured_priority(
    metric: str,
    expected_score: float,
    expected_reason: str,
) -> None:
    metadata = load_dataset_metadata()

    component = build_metric_criticality_component(
        _insight(metric, InsightDirection.UP),
        metadata,
    )

    assert component is not None
    assert component.score == expected_score
    assert component.reason == expected_reason


def test_metric_criticality_returns_none_for_unknown_metric() -> None:
    metadata = load_dataset_metadata()

    assert build_metric_criticality_component(
        _insight("UnknownMetric", InsightDirection.UP),
        metadata,
    ) is None


@pytest.mark.parametrize(
    "priority",
    [None, -0.01, 1.01, True],
    ids=["missing", "below-zero", "above-one", "boolean"],
)
def test_metric_criticality_returns_none_for_invalid_priority(
    priority: object,
) -> None:
    metric_metadata = {"role": "METRIC"}
    if priority is not None:
        metric_metadata["businessPriority"] = priority
    metadata = {"columns": {"Metric": metric_metadata}}

    assert build_metric_criticality_component(
        _insight("Metric", InsightDirection.UP),
        metadata,
    ) is None


@pytest.mark.parametrize("score", [-0.01, 1.01])
def test_business_relevance_component_rejects_out_of_range_score(
    score: float,
) -> None:
    with pytest.raises(ValidationError):
        BusinessRelevanceComponent(
            name="metricCriticality",
            score=score,
            reason="Configured priority.",
        )


@pytest.mark.parametrize(
    ("metric", "direction", "expected_score"),
    [
        ("Revenue", InsightDirection.UP, 1.0),
        ("Orders", InsightDirection.DOWN, 1.0),
        ("ReturnRate", InsightDirection.UP, 1.0),
        ("Returns", InsightDirection.DOWN, 1.0),
        ("Discount", InsightDirection.UP, 0.5),
        ("Discount", InsightDirection.STABLE, 0.25),
    ],
)
def test_builds_direction_impact_component(
    metric: str,
    direction: InsightDirection,
    expected_score: float,
) -> None:
    metadata = load_dataset_metadata()
    insight = _insight(metric, direction)

    component = build_direction_impact_component(insight, metadata)

    assert component is not None
    assert component.name == "directionImpact"
    assert component.score == expected_score
    assert component.reason == build_business_impact_reason(
        insight,
        metadata,
    )


def test_direction_impact_returns_none_for_unknown_metric() -> None:
    metadata = load_dataset_metadata()

    assert build_direction_impact_component(
        _insight("UnknownMetric", InsightDirection.UP),
        metadata,
    ) is None


def test_direction_impact_rejects_unsupported_directionality() -> None:
    metadata = {
        "columns": {
            "Metric": {
                "role": "METRIC",
                "directionality": "UNSUPPORTED",
            }
        }
    }

    assert build_direction_impact_component(
        _insight("Metric", InsightDirection.UP),
        metadata,
    ) is None


@pytest.mark.parametrize(
    ("metric", "direction"),
    [
        ("Revenue", InsightDirection.UP),
        ("ReturnRate", InsightDirection.UP),
        ("Discount", InsightDirection.UP),
    ],
)
def test_collects_business_relevance_components_in_deterministic_order(
    metric: str,
    direction: InsightDirection,
) -> None:
    metadata = load_dataset_metadata()
    insight = _insight(metric, direction)

    components = build_business_relevance_components(insight, metadata)
    metric_component = build_metric_criticality_component(insight, metadata)
    direction_component = build_direction_impact_component(insight, metadata)

    assert [component.name for component in components] == [
        "metricCriticality",
        "directionImpact",
    ]
    assert metric_component is not None
    assert direction_component is not None
    assert [component.score for component in components] == [
        metric_component.score,
        direction_component.score,
    ]
    assert [component.reason for component in components] == [
        metric_component.reason,
        direction_component.reason,
    ]
    assert len({component.name for component in components}) == len(components)


def test_component_collection_returns_empty_for_unknown_metric() -> None:
    metadata = load_dataset_metadata()

    assert build_business_relevance_components(
        _insight("UnknownMetric", InsightDirection.UP),
        metadata,
    ) == []


def test_component_collection_excludes_unresolved_metric_criticality() -> None:
    metadata = {
        "columns": {
            "Metric": {
                "role": "METRIC",
                "directionality": "HIGHER_IS_BETTER",
            }
        }
    }

    components = build_business_relevance_components(
        _insight("Metric", InsightDirection.UP),
        metadata,
    )

    assert [component.name for component in components] == [
        "directionImpact"
    ]


def test_component_collection_excludes_unresolved_direction_impact() -> None:
    metadata = {
        "columns": {
            "Metric": {
                "role": "METRIC",
                "businessPriority": 0.8,
            }
        }
    }

    components = build_business_relevance_components(
        _insight("Metric", InsightDirection.UP),
        metadata,
    )

    assert [component.name for component in components] == [
        "metricCriticality"
    ]


def test_business_relevance_component_weights_are_valid() -> None:
    config = load_insight_config()

    assert "businessRelevance" in config
    assert "weights" in config["businessRelevance"]

    weights = config["businessRelevance"]["weights"]
    assert weights == {
        "metricCriticality": 0.50,
        "directionImpact": 0.30,
        "relationshipContext": 0.20,
    }
    assert all(
        not isinstance(weight, bool)
        and isinstance(weight, (int, float))
        and math.isfinite(float(weight))
        and 0.0 <= float(weight) <= 1.0
        for weight in weights.values()
    )
    assert sum(weights.values()) == pytest.approx(1.0)


@pytest.mark.parametrize(
    ("metric", "direction", "expected"),
    [
        ("ReturnRate", InsightDirection.UP, 0.9375),
        (
            "Revenue",
            InsightDirection.UP,
            (0.95 * 0.50 + 1.00 * 0.30) / 0.80,
        ),
        (
            "Discount",
            InsightDirection.UP,
            (0.55 * 0.50 + 0.50 * 0.30) / 0.80,
        ),
    ],
)
def test_calculates_normalized_business_relevance_score(
    metric: str,
    direction: InsightDirection,
    expected: float,
) -> None:
    components = build_business_relevance_components(
        _insight(metric, direction),
        load_dataset_metadata(),
    )

    assert calculate_business_relevance_score(components) == pytest.approx(
        expected
    )


@pytest.mark.parametrize(
    ("name", "score"),
    [
        ("metricCriticality", 0.72),
        ("directionImpact", 0.63),
    ],
)
def test_single_available_component_returns_its_score(
    name: str,
    score: float,
) -> None:
    component = BusinessRelevanceComponent(
        name=name,
        score=score,
        reason="Available evidence.",
    )

    assert calculate_business_relevance_score([component]) == score


def test_missing_relationship_context_does_not_reduce_score() -> None:
    components = [
        BusinessRelevanceComponent(
            name="metricCriticality",
            score=0.90,
            reason="Configured priority.",
        ),
        BusinessRelevanceComponent(
            name="directionImpact",
            score=1.00,
            reason="Configured direction.",
        ),
    ]

    assert calculate_business_relevance_score(components) == 0.9375


def test_empty_business_relevance_components_return_none() -> None:
    assert calculate_business_relevance_score([]) is None


def test_unconfigured_components_are_ignored() -> None:
    configured = BusinessRelevanceComponent(
        name="metricCriticality",
        score=0.8,
        reason="Configured priority.",
    )
    unknown = BusinessRelevanceComponent(
        name="unknownComponent",
        score=0.1,
        reason="Unknown evidence.",
    )

    assert calculate_business_relevance_score([configured, unknown]) == 0.8
    assert calculate_business_relevance_score([unknown]) is None


@pytest.mark.parametrize(
    "config",
    [
        {},
        {"businessRelevance": {}},
        {"businessRelevance": {"weights": "invalid"}},
        {
            "businessRelevance": {
                "weights": {
                    "metricCriticality": "0.5",
                    "directionImpact": 0.3,
                    "relationshipContext": 0.2,
                }
            }
        },
        {
            "businessRelevance": {
                "weights": {
                    "metricCriticality": True,
                    "directionImpact": 0.3,
                    "relationshipContext": 0.2,
                }
            }
        },
        {
            "businessRelevance": {
                "weights": {
                    "metricCriticality": -0.1,
                    "directionImpact": 0.9,
                    "relationshipContext": 0.2,
                }
            }
        },
        {
            "businessRelevance": {
                "weights": {
                    "metricCriticality": 1.1,
                    "directionImpact": 0.0,
                    "relationshipContext": -0.1,
                }
            }
        },
        {
            "businessRelevance": {
                "weights": {
                    "metricCriticality": float("inf"),
                    "directionImpact": 0.3,
                    "relationshipContext": 0.2,
                }
            }
        },
        {
            "businessRelevance": {
                "weights": {
                    "metricCriticality": 0.4,
                    "directionImpact": 0.3,
                    "relationshipContext": 0.2,
                }
            }
        },
    ],
    ids=[
        "missing-section",
        "missing-weights",
        "weights-not-mapping",
        "non-numeric",
        "boolean",
        "negative",
        "above-one",
        "non-finite",
        "total-not-one",
    ],
)
def test_invalid_business_relevance_weight_config_returns_none(
    config: dict,
) -> None:
    component = BusinessRelevanceComponent(
        name="metricCriticality",
        score=0.9,
        reason="Configured priority.",
    )

    assert calculate_business_relevance_score([component], config) is None


def test_zero_available_component_weight_returns_none() -> None:
    config = {
        "businessRelevance": {
            "weights": {
                "metricCriticality": 0.0,
                "directionImpact": 0.0,
                "relationshipContext": 1.0,
            }
        }
    }
    component = BusinessRelevanceComponent(
        name="metricCriticality",
        score=0.9,
        reason="Configured priority.",
    )

    assert calculate_business_relevance_score([component], config) is None


@pytest.mark.parametrize(
    ("metric", "direction", "expected_score", "expected_impact"),
    [
        (
            "ReturnRate",
            InsightDirection.UP,
            0.9375,
            BusinessImpactDirection.NEGATIVE,
        ),
        (
            "Revenue",
            InsightDirection.UP,
            0.96875,
            BusinessImpactDirection.POSITIVE,
        ),
        (
            "Discount",
            InsightDirection.UP,
            0.53125,
            BusinessImpactDirection.CONTEXT_DEPENDENT,
        ),
    ],
)
def test_evaluates_business_relevance_deterministically(
    metric: str,
    direction: InsightDirection,
    expected_score: float,
    expected_impact: BusinessImpactDirection,
) -> None:
    insight = _insight(metric, direction)
    original_insight = insight.model_dump()

    evaluation = evaluate_business_relevance(
        insight,
        load_dataset_metadata(),
    )

    assert evaluation is not None
    assert evaluation.insight_id == insight.id
    assert evaluation.business_relevance == expected_score
    assert evaluation.impact_direction == expected_impact
    assert [component.name for component in evaluation.components] == [
        "metricCriticality",
        "directionImpact",
    ]
    assert evaluation.reasons == [
        component.reason for component in evaluation.components
    ]
    assert len(evaluation.reasons) == len(set(evaluation.reasons))
    assert insight.model_dump() == original_insight


def test_business_relevance_evaluation_returns_none_for_unknown_metric() -> None:
    assert evaluate_business_relevance(
        _insight("UnknownMetric", InsightDirection.UP),
        load_dataset_metadata(),
    ) is None


def test_evaluation_uses_remaining_component_for_invalid_priority() -> None:
    metadata = {
        "columns": {
            "Metric": {
                "role": "METRIC",
                "businessPriority": True,
                "directionality": "HIGHER_IS_BETTER",
            }
        }
    }

    evaluation = evaluate_business_relevance(
        _insight("Metric", InsightDirection.UP),
        metadata,
    )

    assert evaluation is not None
    assert evaluation.business_relevance == 1.0
    assert [component.name for component in evaluation.components] == [
        "directionImpact"
    ]


def test_evaluation_returns_none_for_unsupported_directionality() -> None:
    metadata = {
        "columns": {
            "Metric": {
                "role": "METRIC",
                "businessPriority": 0.8,
                "directionality": "UNSUPPORTED",
            }
        }
    }

    assert evaluate_business_relevance(
        _insight("Metric", InsightDirection.UP),
        metadata,
    ) is None


@pytest.mark.parametrize("score", [-0.01, 1.01])
def test_business_relevance_evaluation_rejects_out_of_range_score(
    score: float,
) -> None:
    with pytest.raises(ValidationError):
        BusinessRelevanceEvaluation(
            insightId="CHANGE-Revenue",
            businessRelevance=score,
            impactDirection=BusinessImpactDirection.POSITIVE,
        )


def test_business_relevance_evaluation_serializes_with_aliases() -> None:
    evaluation = BusinessRelevanceEvaluation(
        insight_id="CHANGE-Revenue",
        business_relevance=0.9,
        impact_direction=BusinessImpactDirection.POSITIVE,
    )

    assert evaluation.model_dump(by_alias=True) == {
        "insightId": "CHANGE-Revenue",
        "businessRelevance": 0.9,
        "impactDirection": "POSITIVE",
        "components": [],
        "reasons": [],
    }


def test_relationship_context_type_weights_are_valid() -> None:
    type_weights = load_insight_config()["businessRelevance"][
        "relationshipContext"
    ]["typeWeights"]

    assert type_weights == {
        "COUNTER_SIGNAL": 0.35,
        "CONTRIBUTES_TO": 0.30,
        "RELATED_ANOMALY": 0.20,
        "CO_MOVES_WITH": 0.15,
    }
    assert "DRILLDOWN_OF" not in type_weights
    assert sum(type_weights.values()) == pytest.approx(1.0)


def test_single_relationship_context_uses_edge_evidence() -> None:
    component = build_relationship_context_component(
        _insight("Revenue", InsightDirection.UP),
        [
            _relationship(
                RelationshipType.CONTRIBUTES_TO,
                strength=0.8,
                confidence=0.75,
            )
        ],
    )

    assert component is not None
    assert component.name == "relationshipContext"
    assert component.score == 0.6
    assert component.reason == (
        "Relationship context supported by CONTRIBUTES_TO."
    )


def test_relationship_count_does_not_increase_context_score() -> None:
    strongest = _relationship(
        RelationshipType.CONTRIBUTES_TO,
        strength=0.9,
        confidence=0.8,
    )
    component = build_relationship_context_component(
        _insight("Revenue", InsightDirection.UP),
        [
            _relationship(
                RelationshipType.CONTRIBUTES_TO,
                strength=0.4,
                confidence=0.5,
                target_insight_id="CHANGE-Customers",
            ),
            strongest,
        ],
    )

    assert component is not None
    assert component.score == 0.72


def test_relationship_context_normalizes_over_present_types() -> None:
    component = build_relationship_context_component(
        _insight("Revenue", InsightDirection.UP),
        [
            _relationship(
                RelationshipType.COUNTER_SIGNAL,
                strength=0.8,
                confidence=1.0,
            ),
            _relationship(
                RelationshipType.CONTRIBUTES_TO,
                strength=0.5,
                confidence=1.0,
                target_insight_id="CHANGE-Customers",
            ),
        ],
    )

    assert component is not None
    assert component.score == round(
        (0.8 * 0.35 + 0.5 * 0.30) / (0.35 + 0.30),
        6,
    )
    assert component.reason == (
        "Relationship context supported by COUNTER_SIGNAL, "
        "CONTRIBUTES_TO."
    )


def test_all_relationship_context_types_with_full_evidence_score_one() -> None:
    relationships = [
        _relationship(
            relationship_type,
            target_insight_id=f"CHANGE-{relationship_type.value}",
        )
        for relationship_type in (
            RelationshipType.COUNTER_SIGNAL,
            RelationshipType.CONTRIBUTES_TO,
            RelationshipType.RELATED_ANOMALY,
            RelationshipType.CO_MOVES_WITH,
        )
    ]

    component = build_relationship_context_component(
        _insight("Revenue", InsightDirection.UP),
        relationships,
    )

    assert component is not None
    assert component.score == 1.0
    assert component.reason == (
        "Relationship context supported by COUNTER_SIGNAL, "
        "CONTRIBUTES_TO, RELATED_ANOMALY, CO_MOVES_WITH."
    )
    assert all(
        forbidden not in component.reason.lower()
        for forbidden in ("caused", "because", "drives", "leads to", "results in")
    )


def test_relationship_context_considers_insight_as_target() -> None:
    component = build_relationship_context_component(
        _insight("Orders", InsightDirection.UP),
        [_relationship(RelationshipType.CONTRIBUTES_TO)],
    )

    assert component is not None
    assert component.score == 1.0


@pytest.mark.parametrize(
    "relationship",
    [
        _relationship(
            RelationshipType.CONTRIBUTES_TO,
            analysis_id="another-analysis",
        ),
        _relationship(
            RelationshipType.CONTRIBUTES_TO,
            source_insight_id="CHANGE-Returns",
            target_insight_id="CHANGE-Orders",
        ),
        _relationship(RelationshipType.DRILLDOWN_OF),
    ],
    ids=["different-analysis", "unconnected", "unsupported-type"],
)
def test_relationship_context_ignores_unusable_relationships(
    relationship: Relationship,
) -> None:
    assert build_relationship_context_component(
        _insight("Revenue", InsightDirection.UP),
        [relationship],
    ) is None


@pytest.mark.parametrize(
    "config",
    [
        {},
        {"businessRelevance": {}},
        {"businessRelevance": {"relationshipContext": {}}},
        {
            "businessRelevance": {
                "relationshipContext": {"typeWeights": "invalid"}
            }
        },
        {
            "businessRelevance": {
                "relationshipContext": {
                    "typeWeights": {"CONTRIBUTES_TO": "1.0"}
                }
            }
        },
        {
            "businessRelevance": {
                "relationshipContext": {
                    "typeWeights": {"CONTRIBUTES_TO": True}
                }
            }
        },
        {
            "businessRelevance": {
                "relationshipContext": {
                    "typeWeights": {
                        "CONTRIBUTES_TO": -0.1,
                        "COUNTER_SIGNAL": 1.1,
                    }
                }
            }
        },
        {
            "businessRelevance": {
                "relationshipContext": {
                    "typeWeights": {"CONTRIBUTES_TO": float("nan")}
                }
            }
        },
        {
            "businessRelevance": {
                "relationshipContext": {
                    "typeWeights": {"CONTRIBUTES_TO": 0.9}
                }
            }
        },
        {
            "businessRelevance": {
                "relationshipContext": {
                    "typeWeights": {
                        "CONTRIBUTES_TO": 0.0,
                        "COUNTER_SIGNAL": 1.0,
                    }
                }
            }
        },
    ],
    ids=[
        "missing-business-relevance",
        "missing-context",
        "missing-type-weights",
        "weights-not-mapping",
        "non-numeric",
        "boolean",
        "out-of-range",
        "non-finite",
        "total-not-one",
        "available-weight-zero",
    ],
)
def test_invalid_relationship_context_config_returns_none(
    config: dict,
) -> None:
    assert build_relationship_context_component(
        _insight("Revenue", InsightDirection.UP),
        [_relationship(RelationshipType.CONTRIBUTES_TO)],
        config,
    ) is None


@pytest.mark.parametrize("relationships", [None, []])
def test_evaluation_without_relationship_evidence_is_unchanged(
    relationships: list[Relationship] | None,
) -> None:
    evaluation = evaluate_business_relevance(
        _insight("ReturnRate", InsightDirection.UP),
        load_dataset_metadata(),
        relationships=relationships,
    )

    assert evaluation is not None
    assert evaluation.business_relevance == 0.9375
    assert [component.name for component in evaluation.components] == [
        "metricCriticality",
        "directionImpact",
    ]


def test_relationship_context_is_third_evaluation_component() -> None:
    insight = _insight("Revenue", InsightDirection.UP)
    relationship = _relationship(RelationshipType.CONTRIBUTES_TO)

    evaluation = evaluate_business_relevance(
        insight,
        load_dataset_metadata(),
        relationships=[relationship],
    )

    assert evaluation is not None
    assert evaluation.business_relevance == 0.975
    assert [component.name for component in evaluation.components] == [
        "metricCriticality",
        "directionImpact",
        "relationshipContext",
    ]
    assert evaluation.reasons == [
        component.reason for component in evaluation.components
    ]
    assert evaluation.reasons[-1] == (
        "Relationship context supported by CONTRIBUTES_TO."
    )


def test_lower_relationship_evidence_affects_evaluation_score() -> None:
    evaluation = evaluate_business_relevance(
        _insight("Revenue", InsightDirection.UP),
        load_dataset_metadata(),
        relationships=[
            _relationship(
                RelationshipType.CONTRIBUTES_TO,
                strength=0.5,
                confidence=1.0,
            )
        ],
    )

    assert evaluation is not None
    assert evaluation.business_relevance == 0.875


def test_relationship_count_does_not_inflate_evaluation_score() -> None:
    insight = _insight("Revenue", InsightDirection.UP)
    strongest = _relationship(
        RelationshipType.CONTRIBUTES_TO,
        strength=0.9,
        confidence=0.8,
    )
    weaker = _relationship(
        RelationshipType.CONTRIBUTES_TO,
        strength=0.4,
        confidence=0.5,
        target_insight_id="CHANGE-Customers",
    )

    one_relationship = evaluate_business_relevance(
        insight,
        load_dataset_metadata(),
        relationships=[strongest],
    )
    two_relationships = evaluate_business_relevance(
        insight,
        load_dataset_metadata(),
        relationships=[weaker, strongest],
    )

    assert one_relationship is not None
    assert two_relationships is not None
    assert two_relationships.business_relevance == (
        one_relationship.business_relevance
    )


@pytest.mark.parametrize(
    "relationship",
    [
        _relationship(
            RelationshipType.CONTRIBUTES_TO,
            source_insight_id="CHANGE-Returns",
            target_insight_id="CHANGE-Orders",
        ),
        _relationship(RelationshipType.DRILLDOWN_OF),
        _relationship(
            RelationshipType.CONTRIBUTES_TO,
            analysis_id="another-analysis",
        ),
    ],
    ids=["unconnected", "unsupported", "different-analysis"],
)
def test_unusable_relationship_does_not_change_evaluation(
    relationship: Relationship,
) -> None:
    insight = _insight("Revenue", InsightDirection.UP)
    without_relationships = evaluate_business_relevance(
        insight,
        load_dataset_metadata(),
    )
    with_relationship = evaluate_business_relevance(
        insight,
        load_dataset_metadata(),
        relationships=[relationship],
    )

    assert without_relationships is not None
    assert with_relationship is not None
    assert with_relationship == without_relationships


def test_relationship_evaluation_does_not_mutate_inputs() -> None:
    insight = _insight("Revenue", InsightDirection.UP)
    relationship = _relationship(RelationshipType.CONTRIBUTES_TO)
    original_insight = insight.model_dump()
    original_relationship = relationship.model_dump()

    evaluate_business_relevance(
        insight,
        load_dataset_metadata(),
        relationships=[relationship],
    )

    assert insight.model_dump() == original_insight
    assert relationship.model_dump() == original_relationship


def test_priority_configuration_is_valid() -> None:
    priority = load_insight_config()["businessRelevance"]["priority"]
    weights = priority["weights"]
    thresholds = priority["thresholds"]

    assert weights == {
        "importance": 0.40,
        "businessRelevance": 0.40,
        "confidence": 0.20,
    }
    assert all(
        not isinstance(weight, bool)
        and isinstance(weight, (int, float))
        and math.isfinite(float(weight))
        and 0.0 <= float(weight) <= 1.0
        for weight in weights.values()
    )
    assert sum(weights.values()) == pytest.approx(1.0)

    assert thresholds == {
        "critical": 0.80,
        "high": 0.60,
        "medium": 0.40,
    }
    assert all(
        not isinstance(threshold, bool)
        and isinstance(threshold, (int, float))
        and math.isfinite(float(threshold))
        and 0.0 <= float(threshold) <= 1.0
        for threshold in thresholds.values()
    )
    assert (
        1.0
        >= thresholds["critical"]
        > thresholds["high"]
        > thresholds["medium"]
        >= 0.0
    )
    assert "low" not in thresholds


def test_priority_level_has_exact_vocabulary() -> None:
    assert [level.value for level in PriorityLevel] == [
        "CRITICAL",
        "HIGH",
        "MEDIUM",
        "LOW",
    ]


def test_priority_evaluation_serializes_with_aliases() -> None:
    evaluation = PriorityEvaluation(
        insight_id="CHANGE-Revenue",
        priority_score=0.9,
        priority_level=PriorityLevel.CRITICAL,
        breakdown={"importance": 0.4},
        reasons=["Deterministic priority evidence."],
    )

    assert evaluation.model_dump(by_alias=True) == {
        "insightId": "CHANGE-Revenue",
        "priorityScore": 0.9,
        "priorityLevel": "CRITICAL",
        "breakdown": {"importance": 0.4},
        "reasons": ["Deterministic priority evidence."],
    }


@pytest.mark.parametrize("score", [-0.01, 1.01])
def test_priority_evaluation_rejects_out_of_range_score(
    score: float,
) -> None:
    with pytest.raises(ValidationError):
        PriorityEvaluation(
            insightId="CHANGE-Revenue",
            priorityScore=score,
            priorityLevel=PriorityLevel.HIGH,
        )


def test_priority_evaluation_mutable_defaults_are_isolated() -> None:
    first = PriorityEvaluation(
        insightId="CHANGE-Revenue",
        priorityScore=0.8,
        priorityLevel=PriorityLevel.CRITICAL,
    )
    second = PriorityEvaluation(
        insightId="CHANGE-Orders",
        priorityScore=0.6,
        priorityLevel=PriorityLevel.HIGH,
    )

    first.breakdown["importance"] = 0.4
    first.reasons.append("Deterministic priority evidence.")

    assert second.breakdown == {}
    assert second.reasons == []


def _business_relevance_evaluation(
    insight_id: str = "CHANGE-Revenue",
    score: float = 0.8,
) -> BusinessRelevanceEvaluation:
    return BusinessRelevanceEvaluation(
        insightId=insight_id,
        businessRelevance=score,
        impactDirection=BusinessImpactDirection.POSITIVE,
    )


def test_calculates_exact_priority_score() -> None:
    insight = _insight("Revenue", InsightDirection.UP)
    insight.importance = 0.9
    insight.confidence = 1.0

    assert calculate_priority_score(
        insight,
        _business_relevance_evaluation(),
    ) == 0.88


@pytest.mark.parametrize(
    ("importance", "confidence"),
    [(None, 0.8), (0.8, None)],
    ids=["missing-importance", "missing-confidence"],
)
def test_priority_score_requires_importance_and_confidence(
    importance: float | None,
    confidence: float | None,
) -> None:
    insight = _insight("Revenue", InsightDirection.UP)
    insight.importance = importance
    insight.confidence = confidence

    assert calculate_priority_score(
        insight,
        _business_relevance_evaluation(),
    ) is None


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("importance", -0.01),
        ("importance", 1.01),
        ("importance", True),
        ("confidence", float("inf")),
    ],
)
def test_priority_score_rejects_invalid_inputs(
    field: str,
    value: object,
) -> None:
    insight = _insight("Revenue", InsightDirection.UP)
    insight.importance = 0.8
    insight.confidence = 0.8
    setattr(insight, field, value)

    assert calculate_priority_score(
        insight,
        _business_relevance_evaluation(),
    ) is None


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (0.80, PriorityLevel.CRITICAL),
        (0.60, PriorityLevel.HIGH),
        (0.40, PriorityLevel.MEDIUM),
        (0.39, PriorityLevel.LOW),
        (0.799999, PriorityLevel.HIGH),
        (0.599999, PriorityLevel.MEDIUM),
        (0.399999, PriorityLevel.LOW),
    ],
)
def test_resolves_priority_level_boundaries(
    score: float,
    expected: PriorityLevel,
) -> None:
    assert resolve_priority_level(score) == expected


@pytest.mark.parametrize(
    "weights",
    [
        {},
        {
            "importance": 0.4,
            "businessRelevance": 0.4,
        },
        {
            "importance": 0.4,
            "businessRelevance": 0.4,
            "confidence": 0.2,
            "extra": 0.0,
        },
        {
            "importance": True,
            "businessRelevance": 0.4,
            "confidence": 0.2,
        },
        {
            "importance": -0.1,
            "businessRelevance": 0.9,
            "confidence": 0.2,
        },
        {
            "importance": float("nan"),
            "businessRelevance": 0.4,
            "confidence": 0.2,
        },
        {
            "importance": 0.3,
            "businessRelevance": 0.4,
            "confidence": 0.2,
        },
    ],
    ids=[
        "empty",
        "missing-key",
        "extra-key",
        "boolean",
        "out-of-range",
        "non-finite",
        "total-not-one",
    ],
)
def test_invalid_priority_weights_return_none(weights: dict) -> None:
    insight = _insight("Revenue", InsightDirection.UP)
    insight.importance = 0.9
    insight.confidence = 1.0
    config = {
        "businessRelevance": {
            "priority": {
                "weights": weights,
            }
        }
    }

    assert calculate_priority_score(
        insight,
        _business_relevance_evaluation(),
        config,
    ) is None


@pytest.mark.parametrize(
    "thresholds",
    [
        {},
        {"critical": 0.8, "high": 0.6},
        {"critical": True, "high": 0.6, "medium": 0.4},
        {"critical": 1.01, "high": 0.6, "medium": 0.4},
        {"critical": float("inf"), "high": 0.6, "medium": 0.4},
        {"critical": 0.8, "high": 0.8, "medium": 0.4},
        {"critical": 0.8, "high": 0.6, "medium": 0.6},
    ],
    ids=[
        "empty",
        "missing",
        "boolean",
        "out-of-range",
        "non-finite",
        "critical-not-greater",
        "high-not-greater",
    ],
)
def test_invalid_priority_thresholds_return_none(
    thresholds: dict,
) -> None:
    config = {
        "businessRelevance": {
            "priority": {
                "thresholds": thresholds,
            }
        }
    }

    assert resolve_priority_level(0.8, config) is None


def test_builds_deterministic_priority_evaluation() -> None:
    insight = _insight("Revenue", InsightDirection.UP)
    insight.importance = 0.9
    insight.confidence = 1.0
    relevance = _business_relevance_evaluation()

    evaluation = evaluate_priority(insight, relevance)

    assert evaluation is not None
    assert evaluation.insight_id == insight.id
    assert evaluation.priority_score == 0.88
    assert evaluation.priority_level == PriorityLevel.CRITICAL
    assert evaluation.breakdown == {
        "importance": 0.9,
        "businessRelevance": 0.8,
        "confidence": 1.0,
    }
    assert evaluation.reasons == [
        "Analytical importance: 0.90.",
        "Business relevance: 0.80.",
        "Confidence: 1.00.",
        "Priority score 0.88 maps to CRITICAL.",
    ]
    assert all(
        forbidden not in " ".join(evaluation.reasons).lower()
        for forbidden in ("caused", "because", "drives", "leads to")
    )


def test_priority_evaluation_rejects_mismatched_insight_id() -> None:
    insight = _insight("Revenue", InsightDirection.UP)
    insight.importance = 0.9
    insight.confidence = 1.0

    assert evaluate_priority(
        insight,
        _business_relevance_evaluation(insight_id="CHANGE-Orders"),
    ) is None


def test_priority_calculation_does_not_mutate_inputs() -> None:
    insight = _insight("Revenue", InsightDirection.UP)
    insight.importance = 0.9
    insight.confidence = 1.0
    relevance = _business_relevance_evaluation()
    original_insight = insight.model_dump()
    original_relevance = relevance.model_dump()

    evaluate_priority(insight, relevance)

    assert insight.model_dump() == original_insight
    assert relevance.model_dump() == original_relevance


def _ranking_records(
    insight_id: str,
    *,
    priority_score: float,
    business_relevance: float,
    importance: float,
    confidence: float,
) -> tuple[Insight, BusinessRelevanceEvaluation, PriorityEvaluation]:
    insight = _insight(insight_id, InsightDirection.UP)
    insight.id = insight_id
    business_evaluation = BusinessRelevanceEvaluation(
        insightId=insight_id,
        businessRelevance=business_relevance,
        impactDirection=BusinessImpactDirection.POSITIVE,
    )
    priority_evaluation = PriorityEvaluation(
        insightId=insight_id,
        priorityScore=priority_score,
        priorityLevel=PriorityLevel.HIGH,
        breakdown={
            "importance": importance,
            "businessRelevance": business_relevance,
            "confidence": confidence,
        },
    )
    return insight, business_evaluation, priority_evaluation


def test_ranks_by_complete_deterministic_sort_contract() -> None:
    records = [
        _ranking_records(
            "priority-lower",
            priority_score=0.8,
            business_relevance=1.0,
            importance=1.0,
            confidence=1.0,
        ),
        _ranking_records(
            "relevance-lower",
            priority_score=0.9,
            business_relevance=0.7,
            importance=1.0,
            confidence=1.0,
        ),
        _ranking_records(
            "importance-lower",
            priority_score=0.9,
            business_relevance=0.8,
            importance=0.7,
            confidence=1.0,
        ),
        _ranking_records(
            "confidence-lower",
            priority_score=0.9,
            business_relevance=0.8,
            importance=0.8,
            confidence=0.7,
        ),
        _ranking_records(
            "tie-b",
            priority_score=0.9,
            business_relevance=0.8,
            importance=0.8,
            confidence=0.8,
        ),
        _ranking_records(
            "tie-a",
            priority_score=0.9,
            business_relevance=0.8,
            importance=0.8,
            confidence=0.8,
        ),
    ]

    ranked = rank_insights(
        [record[0] for record in records],
        [record[1] for record in records],
        [record[2] for record in records],
    )

    assert [item.insight_id for item in ranked] == [
        "tie-a",
        "tie-b",
        "confidence-lower",
        "importance-lower",
        "relevance-lower",
        "priority-lower",
    ]
    assert [item.rank for item in ranked] == [1, 2, 3, 4, 5, 6]


def test_ranking_excludes_incomplete_and_mismatched_records() -> None:
    complete = _ranking_records(
        "complete",
        priority_score=0.8,
        business_relevance=0.8,
        importance=0.8,
        confidence=0.8,
    )
    missing_business = _ranking_records(
        "missing-business",
        priority_score=0.8,
        business_relevance=0.8,
        importance=0.8,
        confidence=0.8,
    )
    missing_priority = _ranking_records(
        "missing-priority",
        priority_score=0.8,
        business_relevance=0.8,
        importance=0.8,
        confidence=0.8,
    )
    mismatch = _ranking_records(
        "mismatch",
        priority_score=0.8,
        business_relevance=0.8,
        importance=0.8,
        confidence=0.8,
    )
    mismatched_priority = mismatch[2].model_copy(
        update={"insight_id": "different-id"}
    )

    ranked = rank_insights(
        [record[0] for record in (
            complete,
            missing_business,
            missing_priority,
            mismatch,
        )],
        [complete[1], missing_priority[1], mismatch[1]],
        [complete[2], missing_business[2], mismatched_priority],
    )

    assert [item.insight_id for item in ranked] == ["complete"]


@pytest.mark.parametrize(
    ("breakdown_key", "breakdown_value"),
    [
        ("importance", None),
        ("importance", -0.01),
        ("importance", True),
        ("confidence", float("nan")),
    ],
)
def test_ranking_excludes_invalid_tie_break_values(
    breakdown_key: str,
    breakdown_value: object,
) -> None:
    insight, business_evaluation, priority_evaluation = _ranking_records(
        "invalid",
        priority_score=0.8,
        business_relevance=0.8,
        importance=0.8,
        confidence=0.8,
    )
    if breakdown_value is None:
        priority_evaluation.breakdown.pop(breakdown_key)
    else:
        priority_evaluation.breakdown[breakdown_key] = breakdown_value

    assert rank_insights(
        [insight],
        [business_evaluation],
        [priority_evaluation],
    ) == []


def test_input_order_does_not_change_ranking() -> None:
    first = _ranking_records(
        "first",
        priority_score=0.9,
        business_relevance=0.8,
        importance=0.8,
        confidence=0.8,
    )
    second = _ranking_records(
        "second",
        priority_score=0.8,
        business_relevance=0.9,
        importance=0.9,
        confidence=0.9,
    )

    forward = rank_insights(
        [first[0], second[0]],
        [first[1], second[1]],
        [first[2], second[2]],
    )
    reverse = rank_insights(
        [second[0], first[0]],
        [second[1], first[1]],
        [second[2], first[2]],
    )

    assert forward == reverse


def test_ranking_does_not_mutate_inputs() -> None:
    record = _ranking_records(
        "unchanged",
        priority_score=0.8,
        business_relevance=0.8,
        importance=0.8,
        confidence=0.8,
    )
    snapshots = [item.model_dump() for item in record]

    rank_insights([record[0]], [record[1]], [record[2]])

    assert [item.model_dump() for item in record] == snapshots


def test_ranked_insight_serializes_with_aliases() -> None:
    insight, business_evaluation, priority_evaluation = _ranking_records(
        "CHANGE-Revenue",
        priority_score=0.8,
        business_relevance=0.7,
        importance=0.9,
        confidence=0.8,
    )

    ranked = rank_insights(
        [insight],
        [business_evaluation],
        [priority_evaluation],
    )[0]
    serialized = ranked.model_dump(by_alias=True)

    assert serialized["rank"] == 1
    assert serialized["insightId"] == "CHANGE-Revenue"
    assert serialized["priority"]["insightId"] == "CHANGE-Revenue"
    assert serialized["businessRelevance"]["insightId"] == (
        "CHANGE-Revenue"
    )


def test_ranked_insight_rejects_rank_below_one() -> None:
    _, business_evaluation, priority_evaluation = _ranking_records(
        "CHANGE-Revenue",
        priority_score=0.8,
        business_relevance=0.7,
        importance=0.9,
        confidence=0.8,
    )

    with pytest.raises(ValidationError):
        RankedInsight(
            rank=0,
            insightId="CHANGE-Revenue",
            priority=priority_evaluation,
            businessRelevance=business_evaluation,
        )


def _ranked_insights_for_selection() -> list[RankedInsight]:
    ranked: list[RankedInsight] = []
    for rank, insight_id in enumerate(("first", "second", "third"), start=1):
        _, business_evaluation, priority_evaluation = _ranking_records(
            insight_id,
            priority_score=0.9 - rank * 0.1,
            business_relevance=0.8,
            importance=0.9,
            confidence=0.8,
        )
        ranked.append(
            RankedInsight(
                rank=rank,
                insightId=insight_id,
                priority=priority_evaluation,
                businessRelevance=business_evaluation,
            )
        )
    return ranked


@pytest.mark.parametrize(
    ("top_n", "expected_ids"),
    [
        (1, ["first"]),
        (2, ["first", "second"]),
        (5, ["first", "second", "third"]),
        (0, []),
        (-1, []),
        (True, []),
    ],
)
def test_selects_top_ranked_insights_without_reranking(
    top_n: object,
    expected_ids: list[str],
) -> None:
    ranked = _ranked_insights_for_selection()

    selected = select_top_ranked_insights(ranked, top_n=top_n)

    assert [item.insight_id for item in selected] == expected_ids


def test_top_ranked_selection_does_not_mutate_source() -> None:
    ranked = _ranked_insights_for_selection()
    original = [item.model_dump() for item in ranked]

    selected = select_top_ranked_insights(ranked, top_n=1)

    assert [item.model_dump() for item in ranked] == original
    assert len(ranked) == 3
    assert selected[0] is ranked[0]


def test_builds_exact_deterministic_ranking_reason_without_mutation() -> None:
    _, business_evaluation, priority_evaluation = _ranking_records(
        "CHANGE-Revenue",
        priority_score=0.95,
        business_relevance=0.94,
        importance=1.0,
        confidence=1.0,
    )
    priority_evaluation.priority_level = PriorityLevel.CRITICAL
    ranked = RankedInsight(
        rank=1,
        insightId="CHANGE-Revenue",
        priority=priority_evaluation,
        businessRelevance=business_evaluation,
    )
    original = ranked.model_dump()

    reason = build_ranking_reason(ranked)

    assert reason == (
        "Rank #1 with CRITICAL priority (0.95): business relevance 0.94, "
        "analytical importance 1.00, confidence 1.00."
    )
    assert all(
        forbidden not in reason.lower()
        for forbidden in ("caused", "because", "drives", "leads to")
    )
    assert ranked.model_dump() == original


def _scored_insight(
    metric: str,
    *,
    importance: float | None = 1.0,
    confidence: float | None = 1.0,
) -> Insight:
    insight = _insight(metric, InsightDirection.UP)
    insight.importance = importance
    insight.confidence = confidence
    return insight


def test_business_relevance_orchestration_handles_empty_insights() -> None:
    result = analyze_business_relevance(
        [],
        [],
        load_dataset_metadata(),
    )

    assert result == BusinessRelevanceResult()


def test_orchestrates_one_valid_scored_insight() -> None:
    result = analyze_business_relevance(
        [_scored_insight("Revenue")],
        [],
        load_dataset_metadata(),
    )

    assert len(result.business_evaluations) == 1
    assert len(result.priority_evaluations) == 1
    assert len(result.ranked_insights) == 1
    assert len(result.top_ranked_insights) == 1


def test_orchestration_preserves_evaluation_order_and_ranks_normally() -> None:
    insights = [
        _scored_insight("Discount"),
        _scored_insight("ReturnRate"),
    ]

    result = analyze_business_relevance(
        insights,
        [],
        load_dataset_metadata(),
    )

    assert [
        evaluation.insight_id
        for evaluation in result.business_evaluations
    ] == [insight.id for insight in insights]
    assert [
        evaluation.insight_id
        for evaluation in result.priority_evaluations
    ] == [insight.id for insight in insights]
    assert [item.insight_id for item in result.ranked_insights] == [
        "CHANGE-ReturnRate",
        "CHANGE-Discount",
    ]


@pytest.mark.parametrize(
    ("top_n", "expected_count"),
    [(1, 1), (5, 2), (0, 0), (True, 0)],
)
def test_orchestration_delegates_top_n_selection(
    top_n: object,
    expected_count: int,
) -> None:
    result = analyze_business_relevance(
        [
            _scored_insight("Discount"),
            _scored_insight("ReturnRate"),
        ],
        [],
        load_dataset_metadata(),
        top_n=top_n,
    )

    assert len(result.ranked_insights) == 2
    assert len(result.top_ranked_insights) == expected_count


def test_orchestration_keeps_business_evaluation_without_priority() -> None:
    insight = _scored_insight(
        "Revenue",
        importance=None,
        confidence=None,
    )

    result = analyze_business_relevance(
        [insight],
        [],
        load_dataset_metadata(),
    )

    assert [
        evaluation.insight_id
        for evaluation in result.business_evaluations
    ] == [insight.id]
    assert result.priority_evaluations == []
    assert result.ranked_insights == []
    assert result.top_ranked_insights == []


def test_orchestration_skips_unknown_metric_safely() -> None:
    result = analyze_business_relevance(
        [_scored_insight("UnknownMetric")],
        [],
        load_dataset_metadata(),
    )

    assert result == BusinessRelevanceResult()


def test_relationship_evidence_flows_through_orchestration() -> None:
    relationship = _relationship(RelationshipType.CONTRIBUTES_TO)

    result = analyze_business_relevance(
        [_scored_insight("Revenue")],
        [relationship],
        load_dataset_metadata(),
    )

    assert len(result.business_evaluations) == 1
    assert [
        component.name
        for component in result.business_evaluations[0].components
    ] == [
        "metricCriticality",
        "directionImpact",
        "relationshipContext",
    ]


def test_business_relevance_orchestration_does_not_mutate_inputs() -> None:
    insights = [_scored_insight("Revenue")]
    relationships = [_relationship(RelationshipType.CONTRIBUTES_TO)]
    metadata = load_dataset_metadata()
    config = load_insight_config()
    insight_snapshot = [insight.model_dump() for insight in insights]
    relationship_snapshot = [
        relationship.model_dump() for relationship in relationships
    ]
    metadata_snapshot = copy.deepcopy(metadata)
    config_snapshot = copy.deepcopy(config)

    analyze_business_relevance(
        insights,
        relationships,
        metadata,
        config=config,
    )

    assert [insight.model_dump() for insight in insights] == insight_snapshot
    assert [
        relationship.model_dump() for relationship in relationships
    ] == relationship_snapshot
    assert metadata == metadata_snapshot
    assert config == config_snapshot


def test_business_relevance_result_serializes_with_aliases() -> None:
    assert BusinessRelevanceResult().model_dump(by_alias=True) == {
        "businessEvaluations": [],
        "priorityEvaluations": [],
        "rankedInsights": [],
        "topRankedInsights": [],
    }


def test_business_relevance_result_defaults_are_isolated() -> None:
    first = BusinessRelevanceResult()
    second = BusinessRelevanceResult()
    _, business_evaluation, _ = _ranking_records(
        "CHANGE-Revenue",
        priority_score=0.8,
        business_relevance=0.8,
        importance=0.8,
        confidence=0.8,
    )

    first.business_evaluations.append(business_evaluation)

    assert second.business_evaluations == []
    assert second.priority_evaluations == []
    assert second.ranked_insights == []
    assert second.top_ranked_insights == []
