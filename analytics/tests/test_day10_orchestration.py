from copy import deepcopy

from app.config.insight_config_loader import load_insight_config
from app.config.metadata_loader import load_dataset_metadata
from app.models.insight import (
    Insight,
    InsightDirection,
    InsightType,
    PeriodGranularity,
)
from app.models.relationship import Relationship, RelationshipType
from app.services.day10_analysis import analyze_causality_and_context


def _insight(**overrides) -> Insight:
    values = {
        "id": "CHANGE-Revenue-2025-05-2025-06",
        "analysisId": "ANALYSIS-001",
        "type": InsightType.CHANGE,
        "metric": "Revenue",
        "periodGranularity": PeriodGranularity.MONTH,
        "period": {"previous": "2025-05", "current": "2025-06"},
        "direction": InsightDirection.UP,
    }
    values.update(overrides)
    return Insight(**values)


def _insights() -> list[Insight]:
    return [
        _insight(),
        _insight(
            id="CHANGE-MarketingSpend-2025-05-2025-06",
            metric="MarketingSpend",
        ),
    ]


def _relationship(**overrides) -> Relationship:
    values = {
        "id": "CO_MOVES_WITH-MARKETINGSPEND-REVENUE",
        "analysisId": "ANALYSIS-001",
        "sourceInsightId": "CHANGE-MarketingSpend-2025-05-2025-06",
        "targetInsightId": "CHANGE-Revenue-2025-05-2025-06",
        "type": RelationshipType.CO_MOVES_WITH,
        "strength": 1.0,
        "confidence": 0.9,
    }
    values.update(overrides)
    return Relationship(**values)


def test_orchestration_collects_ordered_day10_results():
    insights = _insights()
    relationships = [
        _relationship(
            id="CONTRIBUTES-MARKETINGSPEND-REVENUE",
            type=RelationshipType.CONTRIBUTES_TO,
        ),
        _relationship(),
        _relationship(
            id="UNRESOLVED-RELATIONSHIP",
            targetInsightId="MISSING-INSIGHT",
        ),
    ]

    causality, missing_context, context_summary = (
        analyze_causality_and_context(
            insights,
            relationships,
            load_dataset_metadata(),
        )
    )

    assert [item.relationship_id for item in causality.evaluations] == [
        "CONTRIBUTES-MARKETINGSPEND-REVENUE",
        "CO_MOVES_WITH-MARKETINGSPEND-REVENUE",
    ]
    assert [item.status for item in causality.evaluations] == [
        "NOT_APPLICABLE",
        "CAUSALITY_NOT_ESTABLISHED",
    ]
    assert causality.evaluations[0].association_present is False
    assert causality.evaluations[0].causality_established is False
    assert causality.evaluations[0].causal_evidence == []
    assert causality.evaluations[1].association_present is True
    assert causality.evaluations[1].causality_established is False

    assert [item.insight_id for item in missing_context.evaluations] == [
        insight.id for insight in insights
    ]
    assert [
        item.field
        for item in missing_context.evaluations[0].missing_context
    ] == [
        "CompetitorPrice",
        "UnitPrice",
        "PricingChange",
    ]
    assert missing_context.evaluations[1].missing_context == []

    assert [item.insight_id for item in context_summary.summaries] == [
        insight.id for insight in insights
    ]
    revenue_unknown_codes = [
        item.code for item in context_summary.summaries[0].unknown
    ]
    assert revenue_unknown_codes == [
        "CAUSALITY_NOT_ESTABLISHED",
        "COMPETITORPRICE_UNAVAILABLE",
        "UNITPRICE_UNAVAILABLE",
        "PRICINGCHANGE_UNAVAILABLE",
    ]


def test_orchestration_preserves_reversed_input_order():
    insights = list(reversed(_insights()))
    relationships = [
        _relationship(),
        _relationship(
            id="COUNTER-MARKETINGSPEND-REVENUE",
            type=RelationshipType.COUNTER_SIGNAL,
        ),
    ]

    causality, missing_context, context_summary = (
        analyze_causality_and_context(
            insights,
            relationships,
            load_dataset_metadata(),
        )
    )

    assert [item.relationship_id for item in causality.evaluations] == [
        relationship.id for relationship in relationships
    ]
    assert [item.insight_id for item in missing_context.evaluations] == [
        insight.id for insight in insights
    ]
    assert [item.insight_id for item in context_summary.summaries] == [
        insight.id for insight in insights
    ]


def test_orchestration_does_not_mutate_inputs():
    insights = _insights()
    relationships = [_relationship()]
    metadata = load_dataset_metadata()
    config = load_insight_config()
    insights_before = deepcopy(insights)
    relationships_before = deepcopy(relationships)
    metadata_before = deepcopy(metadata)
    config_before = deepcopy(config)

    analyze_causality_and_context(
        insights,
        relationships,
        metadata,
        config=config,
    )

    assert insights == insights_before
    assert relationships == relationships_before
    assert metadata == metadata_before
    assert config == config_before
