import json
from pathlib import Path

import pytest

from app.services.ingestion import read_dataset
from app.services.insight_engine import generate_insights
from app.services.insight_integrity import build_counter_evidence
from app.services.preparation import prepare_dataset
from app.services.relationship_engine import generate_relationships


ROOT_DIR = Path(__file__).resolve().parents[2]
SAMPLE_DATA_PATH = ROOT_DIR / "sample-data" / "sales_demo_clean.csv"
GOLDEN_TRUTH_PATH = ROOT_DIR / "tests" / "golden" / "expected_results.json"
ANALYSIS_ID = "DAY9-COUNTER-EVIDENCE-GOLDEN"


def test_revenue_counter_evidence_matches_golden_truth() -> None:
    with GOLDEN_TRUTH_PATH.open("r", encoding="utf-8") as golden_file:
        golden_truth = json.load(golden_file)

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
    relationships = generate_relationships(insights)

    expected_counter = golden_truth["expectedCounterEvidence"]
    assert len(expected_counter) == 1
    expected_counter = expected_counter[0]

    primary_spec = next(
        insight
        for insight in golden_truth["requiredInsights"]
        if insight["id"] == expected_counter["primaryInsightRef"]
    )
    primary_matches = [
        insight
        for insight in insights
        if insight.type == primary_spec["type"]
        and insight.metric == primary_spec["metric"]
        and insight.dimension is None
        and insight.segment is None
        and insight.period.get("previous") == primary_spec["previousPeriod"]
        and insight.period.get("current") == primary_spec["currentPeriod"]
    ]
    assert len(primary_matches) == 1
    revenue = primary_matches[0]

    counter_evidence = build_counter_evidence(
        revenue,
        insights,
        relationships,
    )
    expected_by_metric = {
        signal["metric"]: signal
        for signal in expected_counter["expectedSignals"]
    }
    actual_by_metric = {
        evidence.metric: evidence for evidence in counter_evidence
    }

    assert set(actual_by_metric) == set(expected_by_metric) == {
        "Orders",
        "Customers",
    }

    insights_by_id = {insight.id: insight for insight in insights}
    relationships_by_id = {
        relationship.id: relationship for relationship in relationships
    }
    for metric, expected in expected_by_metric.items():
        evidence = actual_by_metric[metric]
        related_insight = insights_by_id[evidence.insight_id]
        relationship = relationships_by_id[evidence.relationship_id]

        assert evidence.direction == expected["direction"] == "DOWN"
        assert related_insight.metric == metric
        assert related_insight.values["percentageChange"] == pytest.approx(
            expected["expectedChangePercent"],
            abs=0.01,
        )
        assert relationship.type == "COUNTER_SIGNAL"
        assert revenue.id in {
            relationship.source_insight_id,
            relationship.target_insight_id,
        }
        assert evidence.insight_id in {
            relationship.source_insight_id,
            relationship.target_insight_id,
        }

    non_counter_relationship_ids = {
        relationship.id
        for relationship in relationships
        if relationship.type != "COUNTER_SIGNAL"
    }
    assert {
        evidence.relationship_id for evidence in counter_evidence
    }.isdisjoint(non_counter_relationship_ids)

    reversed_evidence = build_counter_evidence(
        revenue,
        list(reversed(insights)),
        list(reversed(relationships)),
    )
    assert [
        evidence.model_dump(by_alias=True) for evidence in counter_evidence
    ] == [
        evidence.model_dump(by_alias=True) for evidence in reversed_evidence
    ]
