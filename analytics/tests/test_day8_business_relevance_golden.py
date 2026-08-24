import json
from pathlib import Path

from app.config.metadata_loader import load_dataset_metadata
from app.services.business_relevance import (
    build_ranking_reason,
    evaluate_business_relevance,
    evaluate_priority,
    rank_insights,
)
from app.services.ingestion import read_dataset
from app.services.insight_engine import generate_insights
from app.services.preparation import prepare_dataset
from app.services.relationship_engine import generate_relationships


ROOT_DIR = Path(__file__).resolve().parents[2]
SAMPLE_DATA_PATH = ROOT_DIR / "sample-data" / "sales_demo_clean.csv"
GOLDEN_TRUTH_PATH = ROOT_DIR / "tests" / "golden" / "expected_results.json"
ANALYSIS_ID = "DAY8-BUSINESS-RELEVANCE-GOLDEN"
SEPTEMBER_PERIOD = {"previous": "2025-08", "current": "2025-09"}


def _find_september_change(insights, metric):
    matches = [
        insight
        for insight in insights
        if insight.type == "CHANGE"
        and insight.metric == metric
        and insight.dimension is None
        and insight.segment is None
        and insight.period == SEPTEMBER_PERIOD
        and insight.direction == "UP"
    ]
    assert len(matches) == 1
    return matches[0]


def test_golden_return_rate_ranks_above_discount() -> None:
    with GOLDEN_TRUTH_PATH.open("r", encoding="utf-8") as golden_file:
        golden_truth = json.load(golden_file)

    expected_ranking = golden_truth.get("expectedBusinessRanking")
    assert expected_ranking
    assert expected_ranking[0]["requiredOrdering"] is True

    dataframe = read_dataset(
        file_bytes=SAMPLE_DATA_PATH.read_bytes(),
        file_name=SAMPLE_DATA_PATH.name,
    )
    prepared_dataframe, _ = prepare_dataset(dataframe)
    insights = generate_insights(
        prepared_dataframe,
        analysis_id=ANALYSIS_ID,
        file_name=SAMPLE_DATA_PATH.name,
        data_quality={"score": 100},
    )
    relationships = generate_relationships(insights)
    metadata = load_dataset_metadata()

    business_evaluations = []
    priority_evaluations = []
    for insight in insights:
        business_evaluation = evaluate_business_relevance(
            insight,
            metadata,
            relationships=relationships,
        )
        if business_evaluation is None:
            continue
        business_evaluations.append(business_evaluation)

        priority_evaluation = evaluate_priority(
            insight,
            business_evaluation,
        )
        if priority_evaluation is not None:
            priority_evaluations.append(priority_evaluation)

    return_rate = _find_september_change(insights, "ReturnRate")
    discount = _find_september_change(insights, "Discount")
    business_by_id = {
        evaluation.insight_id: evaluation
        for evaluation in business_evaluations
    }
    priority_by_id = {
        evaluation.insight_id: evaluation
        for evaluation in priority_evaluations
    }

    return_rate_business = business_by_id[return_rate.id]
    discount_business = business_by_id[discount.id]
    assert return_rate_business.impact_direction == "NEGATIVE"
    assert discount_business.impact_direction == "CONTEXT_DEPENDENT"

    assert [
        component.name for component in return_rate_business.components
    ] == ["metricCriticality", "directionImpact"]
    return_rate_components = {
        component.name: component.score
        for component in return_rate_business.components
    }
    assert return_rate_components == {
        "metricCriticality": 0.90,
        "directionImpact": 1.00,
    }

    discount_components = {
        component.name: component.score
        for component in discount_business.components
    }
    assert discount_components["metricCriticality"] == 0.55
    assert discount_components["directionImpact"] == 0.50

    assert return_rate.id in priority_by_id
    assert discount.id in priority_by_id
    assert set(priority_by_id[return_rate.id].breakdown) == {
        "importance",
        "businessRelevance",
        "confidence",
    }
    assert set(priority_by_id[discount.id].breakdown) == {
        "importance",
        "businessRelevance",
        "confidence",
    }
    assert (
        priority_by_id[return_rate.id].priority_score
        > priority_by_id[discount.id].priority_score
    )

    ranked = rank_insights(
        insights,
        business_evaluations,
        priority_evaluations,
    )
    rank_by_id = {item.insight_id: item.rank for item in ranked}
    ranked_by_id = {item.insight_id: item for item in ranked}

    assert return_rate.id in rank_by_id
    assert discount.id in rank_by_id
    assert rank_by_id[return_rate.id] < rank_by_id[discount.id]

    for insight_id in (return_rate.id, discount.id):
        ranked_insight = ranked_by_id[insight_id]
        reason = build_ranking_reason(ranked_insight)
        priority_level = str(ranked_insight.priority.priority_level)

        assert reason
        assert f"Rank #{ranked_insight.rank}" in reason
        assert priority_level in reason
        assert "business relevance" in reason
        assert "analytical importance" in reason
        assert "confidence" in reason
        assert all(
            forbidden not in reason.lower()
            for forbidden in (
                "because",
                "caused",
                "drives",
                "leads to",
                "results in",
            )
        )

    golden_reason = expected_ranking[0].get("reason")
    if golden_reason:
        normalized_reason = golden_reason.lower()
        assert "returnrate" in normalized_reason
        assert "negative directionality" in normalized_reason
        assert "higher business criticality" in normalized_reason
        assert "discount" in normalized_reason
        assert "context-dependent" in normalized_reason
