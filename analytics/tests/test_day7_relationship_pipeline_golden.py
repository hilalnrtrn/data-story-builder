import json
from collections import Counter
from pathlib import Path

import pytest

from app.services.ingestion import read_dataset
from app.services.insight_clustering import build_insight_clusters
from app.services.insight_engine import generate_insights
from app.services.preparation import prepare_dataset
from app.services.relationship_engine import generate_relationships


ROOT_DIR = Path(__file__).resolve().parents[2]
SAMPLE_DATA_PATH = ROOT_DIR / "sample-data" / "sales_demo_clean.csv"
GOLDEN_TRUTH_PATH = ROOT_DIR / "tests" / "golden" / "expected_results.json"
ANALYSIS_ID = "DAY7-RELATIONSHIP-PIPELINE-GOLDEN"
CHANGE_PERIOD = {"previous": "2025-05", "current": "2025-06"}
DAY8_CHANGE_PERIOD = {"previous": "2025-08", "current": "2025-09"}


def _load_golden_truth() -> dict:
    with GOLDEN_TRUTH_PATH.open("r", encoding="utf-8") as golden_file:
        return json.load(golden_file)


@pytest.fixture(scope="module")
def pipeline_output() -> dict:
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
    insight_snapshot = [
        insight.model_dump(by_alias=True) for insight in insights
    ]
    relationships = generate_relationships(insights)
    clusters = build_insight_clusters(insights, relationships)

    return {
        "insights": insights,
        "insight_snapshot": insight_snapshot,
        "relationships": relationships,
        "clusters": clusters,
    }


def _find_change(insights, metric):
    return next(
        insight
        for insight in insights
        if insight.type == "CHANGE"
        and insight.metric == metric
        and insight.dimension is None
        and insight.segment is None
        and insight.period == CHANGE_PERIOD
    )


def _canonical_insights(insights) -> dict:
    return {
        "revenue": _find_change(insights, "Revenue"),
        "orders": _find_change(insights, "Orders"),
        "customers": _find_change(insights, "Customers"),
        "marketing": _find_change(insights, "MarketingSpend"),
        "marmara": next(
            insight
            for insight in insights
            if insight.type == "CONTRIBUTION"
            and insight.metric == "Revenue"
            and insight.dimension == "Region"
            and insight.segment == "Marmara"
            and insight.period == CHANGE_PERIOD
        ),
        "smart_watch": next(
            insight
            for insight in insights
            if insight.type == "ANOMALY"
            and insight.metric == "Revenue"
            and insight.dimension == "Product"
            and insight.segment == "Smart Watch"
            and insight.period == {"current": "2025-06"}
        ),
    }


def test_real_pipeline_generates_expected_relationships(pipeline_output) -> None:
    golden = _load_golden_truth()
    insights = pipeline_output["insights"]
    relationships = pipeline_output["relationships"]
    canonical = _canonical_insights(insights)

    assert len(insights) == 87
    assert len(relationships) == 48
    assert Counter(relationship.type for relationship in relationships) == {
        "CONTRIBUTES_TO": 44,
        "COUNTER_SIGNAL": 2,
        "CO_MOVES_WITH": 1,
        "RELATED_ANOMALY": 1,
    }

    changes = {
        insight.metric: insight
        for insight in (
            canonical["revenue"],
            canonical["orders"],
            canonical["customers"],
            canonical["marketing"],
        )
    }
    for expected in golden["requiredInsights"]:
        insight = changes[expected["metric"]]
        tolerance = expected["tolerance"]
        assert insight.direction == expected["expectedDirection"]
        assert insight.values["previous"] == pytest.approx(
            expected["expectedPreviousValue"], abs=tolerance
        )
        assert insight.values["current"] == pytest.approx(
            expected["expectedCurrentValue"], abs=tolerance
        )
        assert insight.values["absoluteChange"] == pytest.approx(
            expected["expectedAbsoluteChange"], abs=tolerance
        )
        assert insight.values["percentageChange"] == pytest.approx(
            expected["expectedPercentageChange"], abs=tolerance
        )

    expected_contribution = golden["expectedContributions"][0]
    assert canonical["marmara"].values["contributionShare"] == pytest.approx(
        expected_contribution["expectedContributionShare"],
        abs=expected_contribution["tolerance"],
    )
    expected_anomaly = golden["expectedAnomalies"][0]
    assert canonical["smart_watch"].direction == expected_anomaly[
        "expectedDirection"
    ]

    expected_edges = {
        (
            canonical["marmara"].id,
            canonical["revenue"].id,
            "CONTRIBUTES_TO",
        ),
        (
            canonical["orders"].id,
            canonical["revenue"].id,
            "COUNTER_SIGNAL",
        ),
        (
            canonical["customers"].id,
            canonical["revenue"].id,
            "COUNTER_SIGNAL",
        ),
        (
            canonical["marketing"].id,
            canonical["revenue"].id,
            "CO_MOVES_WITH",
        ),
        (
            canonical["smart_watch"].id,
            canonical["revenue"].id,
            "RELATED_ANOMALY",
        ),
    }
    actual_edges = [
        (
            relationship.source_insight_id,
            relationship.target_insight_id,
            relationship.type,
        )
        for relationship in relationships
    ]
    assert expected_edges <= set(actual_edges)
    for expected_edge in expected_edges:
        assert sum(edge == expected_edge for edge in actual_edges) == 1


def test_real_pipeline_builds_canonical_revenue_cluster(pipeline_output) -> None:
    insights = pipeline_output["insights"]
    relationships = pipeline_output["relationships"]
    clusters = pipeline_output["clusters"]
    canonical = _canonical_insights(insights)
    canonical_member_ids = {
        canonical[key].id
        for key in ("orders", "customers", "marketing", "marmara", "smart_watch")
    }

    revenue_cluster = next(
        cluster
        for cluster in clusters
        if cluster.anchor_insight_id == canonical["revenue"].id
    )
    assert len(clusters) == 42
    assert sum(bool(cluster.relationship_ids) for cluster in clusters) == 5
    assert sum(not cluster.relationship_ids for cluster in clusters) == 37
    assert len(revenue_cluster.member_insight_ids) == 13
    assert canonical_member_ids <= set(revenue_cluster.member_insight_ids)

    additional_members = set(revenue_cluster.member_insight_ids) - canonical_member_ids
    assert additional_members == {
        "CONTRIBUTION-Revenue-Campaign-None-2025-05-2025-06",
        "CONTRIBUTION-Revenue-Campaign-Summer Sale-2025-05-2025-06",
        "CONTRIBUTION-Revenue-Category-Electronics-2025-05-2025-06",
        "CONTRIBUTION-Revenue-Category-Home-2025-05-2025-06",
        "CONTRIBUTION-Revenue-Category-Office-2025-05-2025-06",
        "CONTRIBUTION-Revenue-Channel-Online-2025-05-2025-06",
        "CONTRIBUTION-Revenue-Channel-Store-2025-05-2025-06",
        "CONTRIBUTION-Revenue-Product-Smart Watch-2025-05-2025-06",
    }

    relationship_lookup = {
        relationship.id: relationship for relationship in relationships
    }
    for member_id in canonical_member_ids:
        direct_relationships = [
            relationship_lookup[relationship_id]
            for relationship_id in revenue_cluster.relationship_ids
            if relationship_lookup[relationship_id].source_insight_id == member_id
            and relationship_lookup[relationship_id].target_insight_id
            == canonical["revenue"].id
        ]
        assert direct_relationships


def test_day8_changes_are_unrelated_singleton_clusters(pipeline_output) -> None:
    insights = pipeline_output["insights"]
    relationships = pipeline_output["relationships"]
    clusters = pipeline_output["clusters"]

    day8_changes = {}
    for metric in ("ReturnRate", "Discount"):
        matches = [
            insight
            for insight in insights
            if insight.type == "CHANGE"
            and insight.metric == metric
            and insight.dimension is None
            and insight.segment is None
            and insight.period == DAY8_CHANGE_PERIOD
        ]
        assert len(matches) == 1
        day8_changes[metric] = matches[0]

    day8_insight_ids = {
        insight.id for insight in day8_changes.values()
    }
    assert all(
        relationship.source_insight_id not in day8_insight_ids
        and relationship.target_insight_id not in day8_insight_ids
        for relationship in relationships
    )

    clusters_by_anchor = {
        cluster.anchor_insight_id: cluster for cluster in clusters
    }
    for insight_id in day8_insight_ids:
        cluster = clusters_by_anchor[insight_id]
        assert cluster.anchor_insight_id == insight_id
        assert cluster.member_insight_ids == []
        assert cluster.relationship_ids == []


def test_real_pipeline_is_deterministic_and_reference_safe(pipeline_output) -> None:
    insights = pipeline_output["insights"]
    relationships = pipeline_output["relationships"]
    clusters = pipeline_output["clusters"]
    insight_ids = {insight.id for insight in insights}
    relationship_ids = {relationship.id for relationship in relationships}

    reversed_relationships = generate_relationships(list(reversed(insights)))
    reversed_clusters = build_insight_clusters(
        list(reversed(insights)),
        reversed_relationships,
    )
    assert [
        relationship.model_dump(by_alias=True)
        for relationship in relationships
    ] == [
        relationship.model_dump(by_alias=True)
        for relationship in reversed_relationships
    ]
    assert [cluster.model_dump(by_alias=True) for cluster in clusters] == [
        cluster.model_dump(by_alias=True) for cluster in reversed_clusters
    ]

    assert all(
        relationship.source_insight_id in insight_ids
        and relationship.target_insight_id in insight_ids
        and relationship.analysis_id == ANALYSIS_ID
        for relationship in relationships
    )
    assert all(
        cluster.anchor_insight_id in insight_ids
        and set(cluster.member_insight_ids) <= insight_ids
        and set(cluster.relationship_ids) <= relationship_ids
        and cluster.analysis_id == ANALYSIS_ID
        for cluster in clusters
    )
    assert all(insight.analysis_id == ANALYSIS_ID for insight in insights)
    assert [
        insight.model_dump(by_alias=True) for insight in insights
    ] == pipeline_output["insight_snapshot"]


def test_real_pipeline_preserves_unsupported_insights_and_causality_boundary(
    pipeline_output,
) -> None:
    insights = pipeline_output["insights"]
    relationships = pipeline_output["relationships"]
    clusters = pipeline_output["clusters"]
    unsupported = [
        insight for insight in insights if insight.type in {"TREND", "CONTRAST"}
    ]
    singleton_anchors = {
        cluster.anchor_insight_id
        for cluster in clusters
        if not cluster.member_insight_ids and not cluster.relationship_ids
    }

    assert Counter(insight.type for insight in unsupported) == {
        "TREND": 10,
        "CONTRAST": 23,
    }
    assert all(insight.id in singleton_anchors for insight in unsupported)
    assert all(relationship.type != "DRILLDOWN_OF" for relationship in relationships)
    causal_types = {"CAUSES", "CAUSED_BY", "LED_TO", "RESULTS_IN", "DRIVEN_BY"}
    assert causal_types.isdisjoint(
        relationship.type for relationship in relationships
    )
