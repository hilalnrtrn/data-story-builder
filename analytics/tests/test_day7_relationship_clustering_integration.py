from collections import Counter
from copy import deepcopy

from app.models.insight import (
    Insight,
    InsightDirection,
    InsightType,
    PeriodGranularity,
)
from app.models.relationship import RelationshipType
from app.services.insight_clustering import build_insight_clusters
from app.services.relationship_engine import generate_relationships


ANALYSIS_ID = "analysis-integration"
CHANGE_PERIOD = {"previous": "2025-05", "current": "2025-06"}


def _insight(
    insight_id: str,
    insight_type: InsightType,
    metric: str,
    *,
    direction: InsightDirection,
    dimension: str | None = None,
    segment: str | None = None,
    period: dict[str, str] | None = None,
    values: dict[str, float] | None = None,
) -> Insight:
    return Insight(
        id=insight_id,
        analysisId=ANALYSIS_ID,
        type=insight_type,
        metric=metric,
        dimension=dimension,
        segment=segment,
        periodGranularity=PeriodGranularity.MONTH,
        period=period or CHANGE_PERIOD,
        values=values or {},
        direction=direction,
        confidence=0.9,
        importance=0.8,
    )


def _fixture() -> tuple[list[Insight], dict]:
    insights = [
        _insight(
            "change-revenue",
            InsightType.CHANGE,
            "Revenue",
            direction=InsightDirection.UP,
            values={
                "previous": 100.0,
                "current": 130.0,
                "absoluteChange": 30.0,
            },
        ),
        _insight(
            "change-orders",
            InsightType.CHANGE,
            "Orders",
            direction=InsightDirection.DOWN,
        ),
        _insight(
            "change-customers",
            InsightType.CHANGE,
            "Customers",
            direction=InsightDirection.DOWN,
        ),
        _insight(
            "change-marketing",
            InsightType.CHANGE,
            "MarketingSpend",
            direction=InsightDirection.UP,
        ),
        _insight(
            "contribution-revenue-marmara",
            InsightType.CONTRIBUTION,
            "Revenue",
            direction=InsightDirection.UP,
            dimension="Region",
            segment="Marmara",
            values={
                "totalPreviousValue": 100.0,
                "totalCurrentValue": 130.0,
                "totalAbsoluteChange": 30.0,
                "contributionShare": 0.70,
            },
        ),
        _insight(
            "anomaly-revenue-smart-watch",
            InsightType.ANOMALY,
            "Revenue",
            direction=InsightDirection.HIGH,
            dimension="Product",
            segment="Smart Watch",
            period={"current": "2025-06"},
        ),
    ]
    config = {
        "relationship": {
            "metricCompatibility": {
                "COUNTER_SIGNAL": [
                    {"sourceMetric": "Orders", "targetMetric": "Revenue"},
                    {
                        "sourceMetric": "Customers",
                        "targetMetric": "Revenue",
                    },
                ],
                "CO_MOVES_WITH": [
                    {
                        "sourceMetric": "MarketingSpend",
                        "targetMetric": "Revenue",
                    }
                ],
            }
        }
    }
    return insights, config


def _pipeline_dumps(insights: list[Insight], config: dict) -> list[dict]:
    relationships = generate_relationships(insights, config)
    return [
        cluster.model_dump(by_alias=True)
        for cluster in build_insight_clusters(insights, relationships)
    ]


def test_relationship_output_composes_directly_into_revenue_cluster() -> None:
    insights, config = _fixture()
    insight_ids = {insight.id for insight in insights}
    insight_snapshot = [insight.model_dump(by_alias=True) for insight in insights]
    config_snapshot = deepcopy(config)

    relationships = generate_relationships(insights, config)
    relationship_snapshot = [
        relationship.model_dump(by_alias=True)
        for relationship in relationships
    ]

    assert len(relationships) == 5
    assert Counter(relationship.type for relationship in relationships) == {
        RelationshipType.CONTRIBUTES_TO.value: 1,
        RelationshipType.COUNTER_SIGNAL.value: 2,
        RelationshipType.CO_MOVES_WITH.value: 1,
        RelationshipType.RELATED_ANOMALY.value: 1,
    }
    assert all(
        relationship.type != RelationshipType.DRILLDOWN_OF.value
        for relationship in relationships
    )
    causal_types = {"CAUSES", "CAUSED_BY", "LED_TO", "RESULTS_IN", "DRIVEN_BY"}
    assert causal_types.isdisjoint(
        relationship.type for relationship in relationships
    )

    clusters = build_insight_clusters(insights, relationships)

    assert len(clusters) == 1
    revenue_cluster = clusters[0]
    assert revenue_cluster.id == "CLUSTER-change-revenue"
    assert revenue_cluster.analysis_id == ANALYSIS_ID
    assert revenue_cluster.anchor_insight_id == "change-revenue"
    assert revenue_cluster.member_insight_ids == [
        "anomaly-revenue-smart-watch",
        "change-customers",
        "change-marketing",
        "change-orders",
        "contribution-revenue-marmara",
    ]
    assert revenue_cluster.relationship_ids == sorted(
        relationship.id for relationship in relationships
    )
    assert all(
        relationship.source_insight_id in revenue_cluster.member_insight_ids
        and relationship.target_insight_id == revenue_cluster.anchor_insight_id
        for relationship in relationships
    )

    relationship_ids = {relationship.id for relationship in relationships}
    assert revenue_cluster.anchor_insight_id in insight_ids
    assert set(revenue_cluster.member_insight_ids) <= insight_ids
    assert set(revenue_cluster.relationship_ids) == relationship_ids
    assert [
        relationship.model_dump(by_alias=True)
        for relationship in relationships
    ] == relationship_snapshot
    assert [insight.model_dump(by_alias=True) for insight in insights] == insight_snapshot
    assert config == config_snapshot


def test_two_stage_pipeline_is_deterministic_for_reversed_insights() -> None:
    insights, config = _fixture()

    assert _pipeline_dumps(insights, config) == _pipeline_dumps(
        list(reversed(insights)),
        config,
    )


def test_empty_and_single_insight_pipeline_contracts() -> None:
    assert generate_relationships([]) == []
    assert build_insight_clusters([], []) == []

    revenue = _fixture()[0][0]
    relationships = generate_relationships([revenue])
    clusters = build_insight_clusters([revenue], relationships)

    assert relationships == []
    assert [cluster.model_dump(by_alias=True) for cluster in clusters] == [
        {
            "id": "CLUSTER-change-revenue",
            "analysisId": ANALYSIS_ID,
            "anchorInsightId": "change-revenue",
            "memberInsightIds": [],
            "relationshipIds": [],
        }
    ]


def test_unsupported_insight_is_preserved_as_a_singleton() -> None:
    revenue = _fixture()[0][0]
    trend = _insight(
        "trend-revenue",
        InsightType.TREND,
        "Revenue",
        direction=InsightDirection.UP,
    )

    relationships = generate_relationships([revenue, trend], {})
    clusters = build_insight_clusters([revenue, trend], relationships)

    assert relationships == []
    assert [cluster.anchor_insight_id for cluster in clusters] == [
        "change-revenue",
        "trend-revenue",
    ]
    assert all(cluster.member_insight_ids == [] for cluster in clusters)
    assert all(cluster.relationship_ids == [] for cluster in clusters)
