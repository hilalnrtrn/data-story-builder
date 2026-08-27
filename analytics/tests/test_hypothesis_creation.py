from copy import deepcopy

import pytest

from app.models.causality import CausalityEvaluation, CausalityStatus
from app.models.hypothesis import Hypothesis
from app.models.insight import (
    Insight,
    InsightDirection,
    InsightType,
    PeriodGranularity,
)
from app.models.relationship import Relationship, RelationshipType
from app.services.hypothesis_tracker import (
    HypothesisCandidate,
    create_hypothesis_from_candidate,
)


ANALYSIS_ID = "550e8400-e29b-41d4-a716-446655440000"
MARKETING_ID = "CHANGE-MarketingSpend-2025-05-2025-06"
REVENUE_ID = "CHANGE-Revenue-2025-05-2025-06"
RELATIONSHIP_ID = "CO_MOVES_WITH-MarketingSpend-Revenue"
FORBIDDEN_CAUSAL_TERMS = (
    "caused",
    "causes",
    "led to",
    "resulted in",
    "drove",
    "because of",
    "responsible for",
    "explains",
    "produced",
)


def _insight(
    insight_id: str,
    metric: str,
    analysis_id: str = ANALYSIS_ID,
) -> Insight:
    return Insight(
        id=insight_id,
        analysisId=analysis_id,
        type=InsightType.CHANGE,
        metric=metric,
        periodGranularity=PeriodGranularity.MONTH,
        period={"previous": "2025-05", "current": "2025-06"},
        direction=InsightDirection.UP,
    )


def _relationship(
    *,
    relationship_id: str = RELATIONSHIP_ID,
    source_id: str = MARKETING_ID,
    target_id: str = REVENUE_ID,
    analysis_id: str = ANALYSIS_ID,
    relationship_type: RelationshipType = RelationshipType.CO_MOVES_WITH,
) -> Relationship:
    return Relationship(
        id=relationship_id,
        analysisId=analysis_id,
        sourceInsightId=source_id,
        targetInsightId=target_id,
        type=relationship_type,
        strength=0.8,
        confidence=0.75,
    )


def _evaluation(
    relationship: Relationship,
    *,
    established: bool = False,
) -> CausalityEvaluation:
    return CausalityEvaluation(
        relationshipId=relationship.id,
        sourceInsightId=relationship.source_insight_id,
        targetInsightId=relationship.target_insight_id,
        sourceMetric="MarketingSpend",
        targetMetric="Revenue",
        associationPresent=True,
        causalityEstablished=established,
        status=(
            CausalityStatus.CAUSALITY_ESTABLISHED
            if established
            else CausalityStatus.CAUSALITY_NOT_ESTABLISHED
        ),
    )


def _inputs():
    relationship = _relationship()
    return (
        HypothesisCandidate(RELATIONSHIP_ID, MARKETING_ID, REVENUE_ID),
        [
            _insight(MARKETING_ID, "MarketingSpend"),
            _insight(REVENUE_ID, "Revenue"),
        ],
        [relationship],
        [_evaluation(relationship)],
    )


def _create() -> Hypothesis:
    return create_hypothesis_from_candidate(*_inputs())


def test_golden_style_candidate_creates_open_hypothesis():
    hypothesis = _create()

    assert isinstance(hypothesis, Hypothesis)
    assert hypothesis.status == "OPEN"


def test_statement_uses_exact_safe_association_template():
    assert _create().statement == (
        "The observed change in MarketingSpend may be associated with "
        "the observed change in Revenue."
    )


def test_statement_contains_no_forbidden_causal_terms():
    statement = _create().statement.casefold()

    assert all(term not in statement for term in FORBIDDEN_CAUSAL_TERMS)


def test_same_inputs_produce_same_deterministic_id():
    assert _create().id == _create().id


def test_different_candidate_produces_different_deterministic_id():
    first = _create()
    candidate, insights, _, _ = _inputs()
    relationship = _relationship(
        relationship_id="CO_MOVES_WITH-Revenue-MarketingSpend",
        source_id=REVENUE_ID,
        target_id=MARKETING_ID,
    )
    different = create_hypothesis_from_candidate(
        HypothesisCandidate(
            relationship.id,
            relationship.source_insight_id,
            relationship.target_insight_id,
        ),
        insights,
        [relationship],
        [_evaluation(relationship)],
    )

    assert first.id != different.id
    assert candidate != HypothesisCandidate(
        relationship.id,
        relationship.source_insight_id,
        relationship.target_insight_id,
    )


def test_source_identifiers_and_causality_status_are_preserved():
    hypothesis = _create()

    assert hypothesis.source_insight_ids == [MARKETING_ID, REVENUE_ID]
    assert hypothesis.source_relationship_ids == [RELATIONSHIP_ID]
    assert hypothesis.causality_status == "CAUSALITY_NOT_ESTABLISHED"


def test_later_stage_collections_are_empty():
    hypothesis = _create()

    assert hypothesis.supporting_evidence == []
    assert hypothesis.counter_evidence == []
    assert hypothesis.missing_context == []


def test_confidence_is_explicitly_unscored_stage_e_placeholder():
    assert _create().confidence == 0.0


@pytest.mark.parametrize("missing_id", [MARKETING_ID, REVENUE_ID])
def test_unresolved_candidate_insight_is_rejected(missing_id):
    candidate, insights, relationships, evaluations = _inputs()
    insights = [item for item in insights if item.id != missing_id]

    with pytest.raises(ValueError, match="insight could not be resolved"):
        create_hypothesis_from_candidate(
            candidate, insights, relationships, evaluations
        )


def test_unresolved_relationship_is_rejected():
    candidate, insights, _, evaluations = _inputs()

    with pytest.raises(ValueError, match="relationship could not be resolved"):
        create_hypothesis_from_candidate(candidate, insights, [], evaluations)


def test_candidate_relationship_endpoint_mismatch_is_rejected():
    candidate, insights, relationships, evaluations = _inputs()
    mismatched = HypothesisCandidate(
        candidate.relationship_id,
        candidate.target_insight_id,
        candidate.source_insight_id,
    )

    with pytest.raises(ValueError, match="endpoints do not match"):
        create_hypothesis_from_candidate(
            mismatched, insights, relationships, evaluations
        )


def test_non_co_movement_relationship_is_rejected():
    candidate, insights, _, _ = _inputs()
    relationship = _relationship(
        relationship_type=RelationshipType.CONTRIBUTES_TO
    )

    with pytest.raises(ValueError, match="must be CO_MOVES_WITH"):
        create_hypothesis_from_candidate(
            candidate,
            insights,
            [relationship],
            [_evaluation(relationship)],
        )


def test_missing_matching_causality_evaluation_is_rejected():
    candidate, insights, relationships, _ = _inputs()

    with pytest.raises(ValueError, match="evaluation could not be resolved"):
        create_hypothesis_from_candidate(
            candidate, insights, relationships, []
        )


def test_established_causality_is_rejected():
    candidate, insights, relationships, _ = _inputs()

    with pytest.raises(ValueError, match="Established causality"):
        create_hypothesis_from_candidate(
            candidate,
            insights,
            relationships,
            [_evaluation(relationships[0], established=True)],
        )


def test_cross_analysis_insight_resolution_is_rejected():
    candidate, insights, _, evaluations = _inputs()
    relationship = _relationship(analysis_id="another-analysis")

    with pytest.raises(ValueError, match="insight could not be resolved"):
        create_hypothesis_from_candidate(
            candidate, insights, [relationship], evaluations
        )


def test_input_objects_and_collections_are_not_mutated():
    inputs = _inputs()
    before = deepcopy(inputs)

    create_hypothesis_from_candidate(*inputs)

    assert inputs == before


def test_repeated_call_produces_structurally_identical_result():
    assert _create() == _create()


def test_creation_has_no_external_or_llm_dependency():
    candidate, insights, relationships, evaluations = _inputs()

    result = create_hypothesis_from_candidate(
        candidate,
        insights,
        relationships,
        evaluations,
    )

    assert result.tracker_version == "day16-v1"
