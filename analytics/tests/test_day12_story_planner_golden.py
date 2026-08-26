import json
from pathlib import Path

import pytest

from app.config.insight_config_loader import load_insight_config
from app.config.metadata_loader import load_dataset_metadata
from app.services.business_relevance import analyze_business_relevance
from app.services.data_quality import calculate_data_quality
from app.services.day10_analysis import analyze_causality_and_context
from app.services.ingestion import read_dataset
from app.services.insight_clustering import build_insight_clusters
from app.services.insight_engine import generate_insights
from app.services.insight_integrity import analyze_insight_integrity
from app.services.integrity import validate_integrity
from app.services.preparation import prepare_dataset
from app.services.relationship_engine import generate_relationships
from app.services.story_planner import build_story_plan


ROOT_DIR = Path(__file__).resolve().parents[2]
SAMPLE_DATA_PATH = ROOT_DIR / "sample-data" / "sales_demo_clean.csv"
GOLDEN_TRUTH_PATH = ROOT_DIR / "tests" / "golden" / "expected_results.json"
ANALYSIS_ID = "DAY12-STORY-PLANNER-GOLDEN"


@pytest.fixture(scope="module")
def golden_story_pipeline() -> dict:
    golden_bytes = GOLDEN_TRUTH_PATH.read_bytes()
    golden = json.loads(golden_bytes.decode("utf-8"))
    dataframe = read_dataset(
        file_bytes=SAMPLE_DATA_PATH.read_bytes(),
        file_name=SAMPLE_DATA_PATH.name,
    )
    prepared_dataframe, _ = prepare_dataset(dataframe)
    data_integrity = validate_integrity(prepared_dataframe)
    data_quality = calculate_data_quality(prepared_dataframe, data_integrity)
    insights = generate_insights(
        prepared_dataframe,
        analysis_id=ANALYSIS_ID,
        file_name=SAMPLE_DATA_PATH.name,
        data_quality=data_quality,
    )
    relationships = generate_relationships(insights)
    clusters = build_insight_clusters(insights, relationships)
    metadata = load_dataset_metadata()
    config = load_insight_config()
    business = analyze_business_relevance(
        insights,
        relationships,
        metadata,
        config=config,
    )
    integrity = analyze_insight_integrity(
        insights,
        relationships,
        prepared_dataframe,
        metadata,
        config=config,
    )
    causality, missing_context, context_summaries = (
        analyze_causality_and_context(
            insights,
            relationships,
            metadata,
            config=config,
        )
    )
    planner_inputs = (
        insights,
        relationships,
        clusters,
        business.ranked_insights,
        integrity.evaluations,
        causality.evaluations,
        missing_context.evaluations,
        context_summaries.summaries,
    )
    plan = build_story_plan(*planner_inputs)

    assert GOLDEN_TRUTH_PATH.read_bytes() == golden_bytes
    return {
        "golden": golden,
        "insights": insights,
        "relationships": relationships,
        "plan": plan,
        "planner_inputs": planner_inputs,
    }


def _source_insight(pipeline: dict, item):
    return next(
        insight
        for insight in pipeline["insights"]
        if insight.id == item.insight_id
    )


def test_golden_story_core_findings(golden_story_pipeline) -> None:
    pipeline = golden_story_pipeline
    golden = pipeline["golden"]
    plan = pipeline["plan"]
    revenue_expected = next(
        item
        for item in golden["requiredInsights"]
        if item["metric"] == "Revenue"
    )
    revenue = _source_insight(pipeline, plan.main_outcome)

    assert plan.main_outcome.role == "MAIN_OUTCOME"
    assert revenue.type == revenue_expected["type"]
    assert revenue.metric == revenue_expected["metric"]
    assert revenue.dimension is None and revenue.segment is None
    assert revenue.period == {
        "previous": revenue_expected["previousPeriod"],
        "current": revenue_expected["currentPeriod"],
    }
    assert revenue.direction == revenue_expected["expectedDirection"]
    assert revenue.values["previous"] == pytest.approx(
        revenue_expected["expectedPreviousValue"],
        abs=revenue_expected["tolerance"],
    )
    assert revenue.values["current"] == pytest.approx(
        revenue_expected["expectedCurrentValue"],
        abs=revenue_expected["tolerance"],
    )
    assert revenue.values["percentageChange"] == pytest.approx(
        revenue_expected["expectedPercentageChange"],
        abs=revenue_expected["tolerance"],
    )

    contribution_expected = golden["expectedContributions"][0]
    assert plan.contributors
    contributor_item = plan.contributors[0]
    contributor = _source_insight(pipeline, contributor_item)
    assert contributor_item.role == "PRIMARY_CONTRIBUTOR"
    assert contributor.type == "CONTRIBUTION"
    assert contributor.metric == contribution_expected["metric"]
    assert contributor.dimension == contribution_expected["dimension"]
    assert contributor.segment == contribution_expected["segment"]
    for actual_key, expected_key in (
        ("segmentPreviousValue", "segmentPreviousValue"),
        ("segmentCurrentValue", "segmentCurrentValue"),
        ("segmentAbsoluteChange", "segmentAbsoluteChange"),
        ("totalAbsoluteChange", "totalAbsoluteChange"),
        ("contributionShare", "expectedContributionShare"),
    ):
        assert contributor.values[actual_key] == pytest.approx(
            contribution_expected[expected_key],
            abs=contribution_expected["tolerance"],
        )
    relationship = next(
        item
        for item in pipeline["relationships"]
        if item.id == contributor_item.relationship_id
    )
    assert relationship.type == "CONTRIBUTES_TO"
    assert relationship.source_insight_id == contributor.id
    assert relationship.target_insight_id == revenue.id


def test_golden_counter_and_associated_signals(golden_story_pipeline) -> None:
    pipeline = golden_story_pipeline
    golden = pipeline["golden"]
    plan = pipeline["plan"]
    required = {
        item["metric"]: item for item in golden["requiredInsights"]
    }
    counter_insights = [
        _source_insight(pipeline, item) for item in plan.counter_signals
    ]
    assert {item.metric for item in counter_insights} == {
        "Customers",
        "Orders",
    }
    for insight in counter_insights:
        expected = required[insight.metric]
        assert insight.direction == expected["expectedDirection"]
        assert insight.values["percentageChange"] == pytest.approx(
            expected["expectedPercentageChange"], abs=expected["tolerance"]
        )
    assert all(item.role == "COUNTER_SIGNAL" for item in plan.counter_signals)

    assert len(plan.associated_signals) == 1
    associated_item = plan.associated_signals[0]
    associated = _source_insight(pipeline, associated_item)
    expected = required["MarketingSpend"]
    assert associated_item.role == "ASSOCIATED_SIGNAL"
    assert associated.metric == expected["metric"]
    assert associated.direction == expected["expectedDirection"]
    assert associated.values["percentageChange"] == pytest.approx(
        expected["expectedPercentageChange"], abs=expected["tolerance"]
    )

    constraint = next(
        item
        for item in plan.causality_constraints
        if item.relationship_id == associated_item.relationship_id
    )
    causality_expected = golden["expectedCausalityChecks"][0]
    assert constraint.association_present is True
    assert constraint.causality_established is False
    assert constraint.claim_type == "CORRELATIONAL"
    assert constraint.status == causality_expected["expectedStatus"]
    assert constraint.forbidden_concepts == causality_expected[
        "forbiddenConcepts"
    ]


def test_golden_context_evidence_redundancy_budget_and_outline(
    golden_story_pipeline,
) -> None:
    pipeline = golden_story_pipeline
    golden = pipeline["golden"]
    plan = pipeline["plan"]
    expected_context = {
        item["field"]: item for item in golden["expectedMissingContext"]
    }
    actual_context = {item.field: item for item in plan.missing_context}

    assert {"CompetitorPrice", "UnitPrice"} <= set(actual_context)
    for field, item in actual_context.items():
        assert item.status == expected_context[field]["expectedStatus"]
        assert item.is_data_quality_error is False
        assert item.reason == expected_context[field]["reason"]
    assert plan.interpretation_limited is True

    selected_items = [
        plan.main_outcome,
        *plan.contributors,
        *plan.secondary_findings,
        *plan.counter_signals,
        *plan.associated_signals,
        *plan.risks,
    ]
    assert plan.main_outcome.evidence_codes
    assert all(item.evidence_codes for item in plan.contributors)
    assert all(item.evidence_codes for item in plan.counter_signals)
    assert all(item.evidence_codes for item in plan.associated_signals)
    selected_insight_ids = [item.insight_id for item in selected_items]
    assert len(selected_insight_ids) == len(set(selected_insight_ids))
    assert len(plan.contributors) <= 2
    assert len(plan.secondary_findings) <= 1
    assert len(plan.counter_signals) <= 2
    assert len(plan.associated_signals) <= 1
    assert len(plan.risks) <= 1
    assert len(plan.missing_context) <= 2

    expected_section_order = []
    if plan.context:
        expected_section_order.append("CONTEXT")
    expected_section_order.append("OUTCOME")
    if plan.contributors:
        expected_section_order.append("CONTRIBUTION")
    if plan.secondary_findings:
        expected_section_order.append("SECONDARY_FINDINGS")
    if plan.counter_signals:
        expected_section_order.append("COUNTER_SIGNALS")
    if plan.associated_signals:
        expected_section_order.append("ASSOCIATED_SIGNALS")
    if plan.risks:
        expected_section_order.append("RISKS")
    if plan.missing_context:
        expected_section_order.append("LIMITATIONS")
    assert [section.type for section in plan.outline] == expected_section_order
    assert [section.order for section in plan.outline] == list(
        range(1, len(plan.outline) + 1)
    )


def test_golden_story_plan_is_deterministic_and_has_no_llm_output(
    golden_story_pipeline,
) -> None:
    first = golden_story_pipeline["plan"]
    second = build_story_plan(*golden_story_pipeline["planner_inputs"])

    assert first.model_dump(by_alias=True) == second.model_dump(by_alias=True)
    assert not (
        {"narrative", "textFact", "generatedStory", "executiveStory"}
        & set(first.model_dump(by_alias=True))
    )
