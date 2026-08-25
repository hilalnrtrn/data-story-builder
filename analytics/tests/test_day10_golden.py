import json
from pathlib import Path

import pytest

from app.config.insight_config_loader import load_insight_config
from app.config.metadata_loader import load_dataset_metadata
from app.services.causality_guard import guard_causal_claim
from app.services.day10_analysis import analyze_causality_and_context
from app.services.ingestion import read_dataset
from app.services.insight_engine import generate_insights
from app.services.preparation import prepare_dataset
from app.services.relationship_engine import generate_relationships


ROOT_DIR = Path(__file__).resolve().parents[2]
SAMPLE_DATA_PATH = ROOT_DIR / "sample-data" / "sales_demo_clean.csv"
GOLDEN_TRUTH_PATH = ROOT_DIR / "tests" / "golden" / "expected_results.json"
ANALYSIS_ID = "DAY10-GOLDEN"


def _find_change(insights, expected):
    return next(
        insight
        for insight in insights
        if insight.type == "CHANGE"
        and insight.metric == expected["metric"]
        and insight.dimension is None
        and insight.segment is None
        and insight.period.get("previous") == expected["previousPeriod"]
        and insight.period.get("current") == expected["currentPeriod"]
    )


@pytest.fixture(scope="module")
def golden_pipeline() -> dict:
    with GOLDEN_TRUTH_PATH.open("r", encoding="utf-8") as golden_file:
        golden = json.load(golden_file)

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
    causality, missing_context, context_summary = (
        analyze_causality_and_context(
            insights,
            relationships,
            metadata,
            config=config,
        )
    )

    required_changes = {
        expected["metric"]: expected
        for expected in golden["requiredInsights"]
    }
    revenue = _find_change(insights, required_changes["Revenue"])
    marketing = _find_change(insights, required_changes["MarketingSpend"])
    relationship = next(
        relationship
        for relationship in relationships
        if relationship.type == "CO_MOVES_WITH"
        and relationship.source_insight_id == marketing.id
        and relationship.target_insight_id == revenue.id
    )
    causality_evaluation = next(
        evaluation
        for evaluation in causality.evaluations
        if evaluation.relationship_id == relationship.id
    )
    revenue_missing_context = next(
        evaluation
        for evaluation in missing_context.evaluations
        if evaluation.insight_id == revenue.id
    )
    revenue_summary = next(
        summary
        for summary in context_summary.summaries
        if summary.insight_id == revenue.id
    )

    return {
        "golden": golden,
        "relationship": relationship,
        "causality": causality,
        "causality_evaluation": causality_evaluation,
        "missing_context": missing_context,
        "revenue_missing_context": revenue_missing_context,
        "context_summary": context_summary,
        "revenue_summary": revenue_summary,
    }


def test_real_causality_pipeline_matches_golden(golden_pipeline) -> None:
    golden = golden_pipeline["golden"]
    expected = golden["expectedCausalityChecks"][0]
    relationship = golden_pipeline["relationship"]
    evaluation = golden_pipeline["causality_evaluation"]

    assert relationship.type == "CO_MOVES_WITH"
    assert evaluation.source_metric == expected["sourceMetric"]
    assert evaluation.target_metric == expected["targetMetric"]
    assert evaluation.association_present is expected["associationExpected"]
    assert (
        evaluation.causality_established
        is expected["causalityEstablished"]
    )
    assert evaluation.status == expected["expectedStatus"]
    assert evaluation.allowed_concepts == expected["allowedConcepts"]
    assert evaluation.forbidden_concepts == expected["forbiddenConcepts"]
    assert evaluation.causal_evidence == []


def test_real_causal_claim_is_blocked_and_safely_rewritten(
    golden_pipeline,
) -> None:
    expected = golden_pipeline["golden"]["expectedCausalityChecks"][0]
    result = guard_causal_claim(
        "MarketingSpend caused Revenue growth.",
        golden_pipeline["causality_evaluation"],
    )

    assert result.status == "BLOCKED"
    assert "CAUSED" in result.blocked_concepts
    assert result.safe_rewrite is not None
    normalized_rewrite = result.safe_rewrite.casefold()
    forbidden_phrases = [
        concept.casefold().replace("_", " ")
        for concept in expected["forbiddenConcepts"]
    ]
    assert all(
        phrase not in normalized_rewrite for phrase in forbidden_phrases
    )
    assert "does not establish causality" in normalized_rewrite


def test_real_revenue_missing_context_matches_golden(golden_pipeline) -> None:
    golden = golden_pipeline["golden"]
    expected_items = golden["expectedMissingContext"]
    evaluation = golden_pipeline["revenue_missing_context"]
    actual_items = [
        {
            "field": item.field,
            "expectedStatus": item.status,
            "isDataQualityError": item.is_data_quality_error,
            "reason": item.reason,
        }
        for item in evaluation.missing_context
    ]

    assert actual_items == [
        {
            key: value
            for key, value in expected.items()
            if key != "id"
        }
        for expected in expected_items
    ]
    assert evaluation.interpretation_limited is True


def test_price_inference_remains_unknown_and_is_not_produced(
    golden_pipeline,
) -> None:
    golden = golden_pipeline["golden"]
    forbidden_price_claim = next(
        item
        for item in golden["forbiddenClaims"]
        if item["concept"] == "PRICE_INCREASE_OCCURRED"
    )
    expected_missing_fields = {
        item["field"]
        for item in golden["expectedMissingContext"]
        if item["field"] in forbidden_price_claim["reason"]
    }
    missing_fields = {
        item.field
        for item in golden_pipeline["revenue_missing_context"].missing_context
    }
    day10_statement_codes = {
        statement.code
        for summary in golden_pipeline["context_summary"].summaries
        for statement in summary.known + summary.unknown
    }

    assert expected_missing_fields == {"UnitPrice", "PricingChange"}
    assert expected_missing_fields <= missing_fields
    assert forbidden_price_claim["concept"] not in day10_statement_codes


def test_revenue_known_unknown_summary_matches_day10_safety(
    golden_pipeline,
) -> None:
    golden = golden_pipeline["golden"]
    expected_causality = golden["expectedCausalityChecks"][0]
    expected_missing_codes = [
        f"{item['field'].upper()}_UNAVAILABLE"
        for item in golden["expectedMissingContext"]
    ]
    summary = golden_pipeline["revenue_summary"]

    assert "ASSOCIATION_PRESENT" in [item.code for item in summary.known]
    assert [item.code for item in summary.unknown] == [
        expected_causality["expectedStatus"],
        *expected_missing_codes,
    ]
    assert summary.interpretation_limited is True
