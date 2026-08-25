import json
import math
from pathlib import Path

import pytest

from app.config.insight_config_loader import load_insight_config
from app.services.ingestion import read_dataset
from app.services.insight_engine import generate_insights
from app.services.insight_integrity import (
    build_counter_evidence,
    build_insight_contradictions,
    build_integrity_evaluation,
    build_semantic_contradictions,
    check_change_total_consistency,
)
from app.services.preparation import prepare_dataset
from app.services.relationship_engine import generate_relationships


ROOT_DIR = Path(__file__).resolve().parents[2]
SAMPLE_DATA_PATH = ROOT_DIR / "sample-data" / "sales_demo_clean.csv"
GOLDEN_TRUTH_PATH = ROOT_DIR / "tests" / "golden" / "expected_results.json"
ANALYSIS_ID = "DAY9-INTEGRITY-EVALUATION-GOLDEN"


def test_revenue_integrity_evaluation_matches_golden_truth() -> None:
    golden_bytes = GOLDEN_TRUTH_PATH.read_bytes()
    golden_truth = json.loads(golden_bytes.decode("utf-8"))
    expected_counter = golden_truth["expectedCounterEvidence"]
    assert len(expected_counter) == 1
    expected_counter = expected_counter[0]
    expected_revenue = next(
        insight
        for insight in golden_truth["requiredInsights"]
        if insight["id"] == expected_counter["primaryInsightRef"]
    )

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

    revenue_matches = [
        insight
        for insight in insights
        if insight.type == "CHANGE"
        and insight.metric == expected_revenue["metric"]
        and insight.dimension is None
        and insight.segment is None
        and insight.period.get("previous") == expected_revenue["previousPeriod"]
        and insight.period.get("current") == expected_revenue["currentPeriod"]
    ]
    assert len(revenue_matches) == 1
    revenue_change = revenue_matches[0]

    counter_evidence = build_counter_evidence(
        revenue_change,
        insights,
        relationships,
    )
    expected_signals = {
        signal["metric"]: signal
        for signal in expected_counter["expectedSignals"]
    }
    actual_counter = {
        evidence.metric: evidence for evidence in counter_evidence
    }
    assert set(actual_counter) == set(expected_signals) == {
        "Orders",
        "Customers",
    }

    insights_by_id = {insight.id: insight for insight in insights}
    for metric, expected_signal in expected_signals.items():
        evidence = actual_counter[metric]
        related_insight = insights_by_id[evidence.insight_id]
        assert evidence.direction == expected_signal["direction"]
        assert related_insight.values["percentageChange"] == pytest.approx(
            expected_signal["expectedChangePercent"],
            abs=0.01,
        )

    insight_contradictions = build_insight_contradictions(
        revenue_change,
        insights,
    )
    semantic_contradictions = build_semantic_contradictions(revenue_change)
    contradictions = insight_contradictions + semantic_contradictions
    assert contradictions == []

    consistency = check_change_total_consistency(
        revenue_change,
        prepared_dataframe,
        dimension="Region",
        aggregation="SUM",
    )
    assert consistency is not None
    assert consistency.status == "PASS"

    evaluation = build_integrity_evaluation(
        revenue_change,
        counter_evidence=counter_evidence,
        contradictions=contradictions,
        consistency_checks=[consistency],
    )
    repeated_evaluation = build_integrity_evaluation(
        revenue_change,
        counter_evidence=counter_evidence,
        contradictions=contradictions,
        consistency_checks=[consistency],
    )

    assert expected_counter["expectedIntegrityStatus"] == (
        "PASS_WITH_WARNINGS"
    )
    assert expected_counter["requiresQualification"] is True
    assert evaluation.insight_id == revenue_change.id
    assert evaluation.status == expected_counter["expectedIntegrityStatus"]
    assert evaluation.story_eligible is True
    assert evaluation.requires_qualification is expected_counter[
        "requiresQualification"
    ]
    assert evaluation.integrity_score is not None
    assert math.isfinite(evaluation.integrity_score)
    assert 0.0 <= evaluation.integrity_score <= 1.0
    assert set(evaluation.integrity_breakdown) == {
        "consistency",
        "contradictionSafety",
        "counterEvidence",
    }
    assert evaluation.integrity_breakdown["consistency"] == pytest.approx(1.0)
    assert evaluation.integrity_breakdown[
        "contradictionSafety"
    ] == pytest.approx(1.0)
    assert evaluation.integrity_breakdown["counterEvidence"] == pytest.approx(
        0.85
    )

    score_weights = load_insight_config()["insightIntegrity"]["score"][
        "weights"
    ]
    applicable_weights = {
        name: score_weights[name]
        for name in evaluation.integrity_breakdown
    }
    weighted_numerator = sum(
        evaluation.integrity_breakdown[name] * weight
        for name, weight in applicable_weights.items()
    )
    available_weight = sum(applicable_weights.values())
    expected_score = weighted_numerator / available_weight
    assert evaluation.integrity_score == pytest.approx(expected_score)
    assert {item.metric for item in evaluation.counter_evidence} == {
        "Orders",
        "Customers",
    }
    assert evaluation.contradictions == []
    assert len(evaluation.consistency_checks) == 1
    assert evaluation.consistency_checks[0].status == "PASS"
    assert evaluation.outlier_check is None
    assert evaluation.one_off_check is None
    assert evaluation.reasons
    assert evaluation.integrity_score == repeated_evaluation.integrity_score
    assert evaluation.integrity_breakdown == (
        repeated_evaluation.integrity_breakdown
    )
    assert evaluation.reasons == repeated_evaluation.reasons
    assert len(evaluation.reasons) == len(set(evaluation.reasons))

    contradiction_ids = {
        finding.related_insight_id
        for finding in evaluation.contradictions
        if finding.related_insight_id is not None
    }
    counter_ids = {
        evidence.insight_id for evidence in evaluation.counter_evidence
    }
    assert counter_ids.isdisjoint(contradiction_ids)
    assert GOLDEN_TRUTH_PATH.read_bytes() == golden_bytes
