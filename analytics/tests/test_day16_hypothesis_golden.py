import json
import math
from pathlib import Path

import pytest

from app.config.insight_config_loader import load_insight_config
from app.config.metadata_loader import load_dataset_metadata
from app.services.day10_analysis import analyze_causality_and_context
from app.services.hypothesis_tracker import track_hypotheses
from app.services.ingestion import read_dataset
from app.services.insight_engine import generate_insights
from app.services.insight_integrity import analyze_insight_integrity
from app.services.preparation import prepare_dataset
from app.services.relationship_engine import generate_relationships


ROOT_DIR = Path(__file__).resolve().parents[2]
SAMPLE_DATA_PATH = ROOT_DIR / "sample-data" / "sales_demo_clean.csv"
GOLDEN_TRUTH_PATH = ROOT_DIR / "tests" / "golden" / "expected_results.json"
ANALYSIS_ID = "DAY16-GOLDEN"
FORBIDDEN_CAUSAL_WORDING = (
    "caused",
    "led to",
    "resulted in",
    "drove",
    "because of",
    "responsible for",
)


@pytest.fixture(scope="module")
def golden_hypothesis_pipeline() -> dict:
    golden = json.loads(GOLDEN_TRUTH_PATH.read_text(encoding="utf-8"))
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
    metadata = load_dataset_metadata()
    config = load_insight_config()
    integrity = analyze_insight_integrity(
        insights,
        relationships,
        prepared_dataframe,
        metadata,
        config=config,
    )
    causality, missing_context, _ = analyze_causality_and_context(
        insights,
        relationships,
        metadata,
        config=config,
    )
    tracker_inputs = (
        insights,
        relationships,
        integrity.evaluations,
        causality.evaluations,
        missing_context.evaluations,
    )

    return {
        "golden": golden,
        "insights": insights,
        "hypotheses": track_hypotheses(*tracker_inputs),
        "repeated": track_hypotheses(*tracker_inputs),
    }


def test_real_golden_hypothesis_matches_expected_contract(
    golden_hypothesis_pipeline,
) -> None:
    expected = golden_hypothesis_pipeline["golden"]["expectedHypotheses"][0]
    hypotheses = golden_hypothesis_pipeline["hypotheses"]
    matches = [
        hypothesis
        for hypothesis in hypotheses
        if hypothesis.source_insight_ids == expected["sourceInsightIds"]
        and hypothesis.source_relationship_ids
        == expected["sourceRelationshipIds"]
    ]

    assert len(hypotheses) == 1
    assert len(matches) == 1
    hypothesis = matches[0]
    assert hypothesis.status == expected["status"] == "OPEN"
    assert hypothesis.statement == expected["statement"]
    assert "may be associated with" in hypothesis.statement
    assert not any(
        phrase in hypothesis.statement.lower()
        for phrase in FORBIDDEN_CAUSAL_WORDING
    )
    assert hypothesis.causality_status == expected["causalityStatus"]
    assert hypothesis.tracker_version == expected["trackerVersion"]
    assert hypothesis.confidence == pytest.approx(expected["confidence"])
    assert math.isfinite(hypothesis.confidence)
    assert 0.0 <= hypothesis.confidence <= 1.0
    assert hypothesis.reasons == expected["reasons"]
    assert all(item.status == "OPEN" for item in hypotheses)


def test_golden_hypothesis_identity_and_evidence_are_deterministic(
    golden_hypothesis_pipeline,
) -> None:
    expected = golden_hypothesis_pipeline["golden"]["expectedHypotheses"][0]
    hypothesis = golden_hypothesis_pipeline["hypotheses"][0]
    repeated = golden_hypothesis_pipeline["repeated"][0]

    assert hypothesis == repeated
    assert hypothesis.id == repeated.id == expected["expectedHypothesisId"]
    assert hypothesis.id.startswith("HYPOTHESIS-")
    assert len(hypothesis.id) == len("HYPOTHESIS-") + 64
    assert hypothesis.source_insight_ids == expected["sourceInsightIds"]
    assert hypothesis.source_relationship_ids == expected["sourceRelationshipIds"]

    references_by_insight = {
        insight_id: [
            reference.evidence_code
            for reference in hypothesis.supporting_evidence
            if reference.insight_id == insight_id
        ]
        for insight_id in expected["sourceInsightIds"]
    }
    assert references_by_insight == {
        insight_id: expected["supportingEvidenceCodes"]
        for insight_id in expected["sourceInsightIds"]
    }
    assert set(hypothesis.supporting_evidence[0].model_dump()) == {
        "insight_id",
        "evidence_code",
    }


def test_golden_adverse_context_preserves_upstream_traceability(
    golden_hypothesis_pipeline,
) -> None:
    expected = golden_hypothesis_pipeline["golden"]["expectedHypotheses"][0]
    hypothesis = golden_hypothesis_pipeline["hypotheses"][0]
    revenue_id = expected["sourceInsightIds"][1]

    assert [item.metric for item in hypothesis.counter_evidence] == expected[
        "counterEvidenceMetrics"
    ]
    assert [item.item.field for item in hypothesis.missing_context] == expected[
        "missingContextFields"
    ]
    assert all(
        item.source_insight_id == revenue_id
        for item in hypothesis.missing_context
    )
    assert all(
        item.item.status == "NOT_AVAILABLE"
        and item.item.is_data_quality_error is False
        for item in hypothesis.missing_context
    )
    assert not any(
        "probability" in reason.lower() for reason in hypothesis.reasons
    )
