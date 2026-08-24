import json
from collections import Counter
from pathlib import Path

import pytest

from app.config.insight_config_loader import load_insight_config
from app.services.ingestion import read_dataset
from app.services.insight_clustering import build_insight_clusters
from app.services.insight_engine import generate_insights
from app.services.preparation import prepare_dataset
from app.services.relationship_engine import (
    build_co_moves_with_relationship,
    build_contributes_to_relationship,
    build_counter_signal_relationship,
    build_related_anomaly_relationship,
)


ROOT_DIR = Path(__file__).resolve().parents[2]
SAMPLE_DATA_PATH = ROOT_DIR / "sample-data" / "sales_demo_clean.csv"
GOLDEN_TRUTH_PATH = ROOT_DIR / "tests" / "golden" / "expected_results.json"
ANALYSIS_ID = "DAY7-CLUSTERING-GOLDEN"


def _load_golden_truth() -> dict:
    with GOLDEN_TRUTH_PATH.open("r", encoding="utf-8") as golden_file:
        return json.load(golden_file)


@pytest.fixture(scope="module")
def golden_insights():
    dataframe = read_dataset(
        file_bytes=SAMPLE_DATA_PATH.read_bytes(),
        file_name=SAMPLE_DATA_PATH.name,
    )
    prepared_dataframe, _ = prepare_dataset(dataframe)

    return generate_insights(
        prepared_dataframe,
        analysis_id=ANALYSIS_ID,
        file_name=SAMPLE_DATA_PATH.name,
    )


def _find_change(insights, metric):
    return next(
        insight
        for insight in insights
        if insight.type == "CHANGE"
        and insight.metric == metric
        and insight.dimension is None
        and insight.segment is None
        and insight.period == {
            "previous": "2025-05",
            "current": "2025-06",
        }
    )


def _find_marmara_contribution(insights):
    return next(
        insight
        for insight in insights
        if insight.type == "CONTRIBUTION"
        and insight.metric == "Revenue"
        and insight.dimension == "Region"
        and insight.segment == "Marmara"
        and insight.period == {
            "previous": "2025-05",
            "current": "2025-06",
        }
    )


def _find_smart_watch_anomaly(insights):
    return next(
        insight
        for insight in insights
        if insight.type == "ANOMALY"
        and insight.metric == "Revenue"
        and insight.dimension == "Product"
        and insight.segment == "Smart Watch"
        and insight.period == {"current": "2025-06"}
    )


def _canonical_insights(insights):
    revenue = _find_change(insights, "Revenue")
    orders = _find_change(insights, "Orders")
    customers = _find_change(insights, "Customers")
    marketing_spend = _find_change(insights, "MarketingSpend")
    marmara = _find_marmara_contribution(insights)
    smart_watch = _find_smart_watch_anomaly(insights)

    return revenue, orders, customers, marketing_spend, marmara, smart_watch


def _build_golden_relationships(canonical_insights):
    revenue, orders, customers, marketing_spend, marmara, smart_watch = (
        canonical_insights
    )
    config = load_insight_config()
    relationships = [
        build_contributes_to_relationship(marmara, revenue),
        build_counter_signal_relationship(orders, revenue, config),
        build_counter_signal_relationship(customers, revenue, config),
        build_co_moves_with_relationship(
            marketing_spend,
            revenue,
            config,
        ),
        build_related_anomaly_relationship(smart_watch, revenue),
    ]

    assert all(relationship is not None for relationship in relationships)

    return relationships


def test_real_golden_insights_match_required_contracts(golden_insights):
    golden = _load_golden_truth()
    revenue, orders, customers, marketing_spend, marmara, smart_watch = (
        _canonical_insights(golden_insights)
    )
    changes = {
        insight.metric: insight
        for insight in (revenue, orders, customers, marketing_spend)
    }

    for expected in golden["requiredInsights"]:
        insight = changes[expected["metric"]]
        tolerance = expected["tolerance"]

        assert insight.direction == expected["expectedDirection"]
        assert insight.values["previous"] == pytest.approx(
            expected["expectedPreviousValue"],
            abs=tolerance,
        )
        assert insight.values["current"] == pytest.approx(
            expected["expectedCurrentValue"],
            abs=tolerance,
        )
        assert insight.values["absoluteChange"] == pytest.approx(
            expected["expectedAbsoluteChange"],
            abs=tolerance,
        )
        assert insight.values["percentageChange"] == pytest.approx(
            expected["expectedPercentageChange"],
            abs=tolerance,
        )

    expected_contribution = golden["expectedContributions"][0]
    assert marmara.values["contributionShare"] == pytest.approx(
        expected_contribution["expectedContributionShare"],
        abs=expected_contribution["tolerance"],
    )
    assert marmara.values["segmentAbsoluteChange"] == pytest.approx(
        expected_contribution["segmentAbsoluteChange"],
        abs=expected_contribution["tolerance"],
    )

    expected_anomaly = golden["expectedAnomalies"][0]
    assert smart_watch.direction == expected_anomaly["expectedDirection"]
    assert smart_watch.period["current"] == expected_anomaly["period"]


def test_builds_canonical_golden_revenue_cluster(golden_insights):
    canonical_insights = _canonical_insights(golden_insights)
    revenue, orders, customers, marketing_spend, marmara, smart_watch = (
        canonical_insights
    )
    relationships = _build_golden_relationships(canonical_insights)
    expected_member_ids = sorted(
        [
            marmara.id,
            orders.id,
            customers.id,
            marketing_spend.id,
            smart_watch.id,
        ]
    )
    expected_relationship_ids = sorted(
        relationship.id for relationship in relationships
    )

    clusters = build_insight_clusters(
        list(canonical_insights),
        relationships,
    )

    assert len(clusters) == 1
    cluster = clusters[0]
    assert cluster.id == f"CLUSTER-{revenue.id}"
    assert cluster.analysis_id == ANALYSIS_ID
    assert cluster.anchor_insight_id == revenue.id
    assert cluster.member_insight_ids == expected_member_ids
    assert cluster.relationship_ids == expected_relationship_ids
    assert revenue.id not in cluster.member_insight_ids
    assert len(cluster.member_insight_ids) == len(
        set(cluster.member_insight_ids)
    )

    expected_member_id_set = set(expected_member_ids)
    assert all(
        relationship.analysis_id == ANALYSIS_ID
        and relationship.target_insight_id == revenue.id
        and relationship.source_insight_id in expected_member_id_set
        for relationship in relationships
    )
    assert Counter(relationship.type for relationship in relationships) == {
        "CONTRIBUTES_TO": 1,
        "COUNTER_SIGNAL": 2,
        "CO_MOVES_WITH": 1,
        "RELATED_ANOMALY": 1,
    }

    causal_types = {
        "CAUSES",
        "CAUSED_BY",
        "LED_TO",
        "RESULTS_IN",
        "DRIVEN_BY",
    }
    assert causal_types.isdisjoint(
        relationship.type for relationship in relationships
    )

    reversed_clusters = build_insight_clusters(
        list(reversed(canonical_insights)),
        list(reversed(relationships)),
    )
    assert [cluster.model_dump(by_alias=True) for cluster in clusters] == [
        cluster.model_dump(by_alias=True) for cluster in reversed_clusters
    ]
