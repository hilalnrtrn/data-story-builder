from copy import deepcopy

import pytest

from app.models.causality import CausalityEvaluation, CausalityStatus
from app.models.hypothesis import (
    Hypothesis,
    HypothesisEvidenceReference,
    HypothesisMissingContextReference,
)
from app.models.insight import InsightDirection
from app.models.insight_integrity import CounterEvidenceItem
from app.models.missing_context import MissingContextItem, MissingContextStatus
from app.models.relationship import Relationship, RelationshipType
from app.services.hypothesis_tracker import calculate_hypothesis_confidence


ANALYSIS_ID = "550e8400-e29b-41d4-a716-446655440000"
MARKETING_ID = "CHANGE-MarketingSpend-2025-05-2025-06"
REVENUE_ID = "CHANGE-Revenue-2025-05-2025-06"
RELATIONSHIP_ID = "CO_MOVES_WITH-MarketingSpend-Revenue"


def _counter(index: int = 1) -> CounterEvidenceItem:
    return CounterEvidenceItem(
        insightId=f"counter-insight-{index}",
        relationshipId=f"counter-relationship-{index}",
        metric="Orders",
        direction=InsightDirection.DOWN,
        reasons=["Counter evidence is present."],
    )


def _missing(index: int) -> HypothesisMissingContextReference:
    return HypothesisMissingContextReference(
        sourceInsightId=REVENUE_ID,
        item=MissingContextItem(
            field=f"MissingField{index}",
            status=MissingContextStatus.NOT_AVAILABLE,
            isDataQualityError=False,
            reason=f"MissingField{index} is unavailable.",
        ),
    )


def _hypothesis(
    *,
    covered_source_ids: list[str] | None = None,
    counter_count: int = 0,
    missing_count: int = 0,
    source_ids: list[str] | None = None,
    relationship_ids: list[str] | None = None,
) -> Hypothesis:
    covered = (
        [MARKETING_ID, REVENUE_ID]
        if covered_source_ids is None
        else covered_source_ids
    )
    return Hypothesis(
        id="HYPOTHESIS-MarketingSpend-Revenue",
        analysisId=ANALYSIS_ID,
        statement=(
            "The observed change in MarketingSpend may be associated with "
            "the observed change in Revenue."
        ),
        status="OPEN",
        confidence=0.0,
        sourceInsightIds=(
            [MARKETING_ID, REVENUE_ID]
            if source_ids is None
            else source_ids
        ),
        sourceRelationshipIds=(
            [RELATIONSHIP_ID]
            if relationship_ids is None
            else relationship_ids
        ),
        supportingEvidence=[
            HypothesisEvidenceReference(
                insightId=insight_id,
                evidenceCode="CHANGE",
            )
            for insight_id in covered
        ],
        counterEvidence=[_counter(index) for index in range(counter_count)],
        missingContext=[_missing(index) for index in range(missing_count)],
        causalityStatus=CausalityStatus.CAUSALITY_NOT_ESTABLISHED,
        reasons=[
            "CO_MOVES_WITH association detected.",
            "Causality is not established.",
        ],
        trackerVersion="day16-v1",
    )


def _relationship(
    confidence: float = 0.8,
    relationship_type: RelationshipType = RelationshipType.CO_MOVES_WITH,
) -> Relationship:
    return Relationship(
        id=RELATIONSHIP_ID,
        analysisId=ANALYSIS_ID,
        sourceInsightId=MARKETING_ID,
        targetInsightId=REVENUE_ID,
        type=relationship_type,
        strength=0.9,
        confidence=confidence,
    )


def _evaluation(
    *,
    association_present: bool = True,
    causality_established: bool = False,
    status: CausalityStatus = CausalityStatus.CAUSALITY_NOT_ESTABLISHED,
) -> CausalityEvaluation:
    return CausalityEvaluation(
        relationshipId=RELATIONSHIP_ID,
        sourceInsightId=MARKETING_ID,
        targetInsightId=REVENUE_ID,
        sourceMetric="MarketingSpend",
        targetMetric="Revenue",
        associationPresent=association_present,
        causalityEstablished=causality_established,
        status=status,
    )


def _score(
    hypothesis: Hypothesis,
    relationship: Relationship | None = None,
    evaluation: CausalityEvaluation | None = None,
) -> Hypothesis:
    return calculate_hypothesis_confidence(
        hypothesis,
        [_relationship() if relationship is None else relationship],
        [_evaluation() if evaluation is None else evaluation],
    )


def test_full_coverage_high_relationship_confidence_without_penalties():
    assert _score(_hypothesis()).confidence == pytest.approx(0.94)


@pytest.mark.parametrize(
    "covered_source_ids, expected",
    [([MARKETING_ID], 0.69), ([], 0.44)],
)
def test_reduced_supporting_evidence_coverage_lowers_score(
    covered_source_ids,
    expected,
):
    assert _score(
        _hypothesis(covered_source_ids=covered_source_ids)
    ).confidence == pytest.approx(expected)


@pytest.mark.parametrize("counter_count", [1, 3])
def test_counter_evidence_applies_one_fixed_penalty(counter_count):
    assert _score(
        _hypothesis(counter_count=counter_count)
    ).confidence == pytest.approx(0.79)


@pytest.mark.parametrize(
    "missing_count, expected_penalty",
    [(1, 0.05), (4, 0.20), (6, 0.20)],
)
def test_missing_context_penalty_is_linear_and_capped(
    missing_count,
    expected_penalty,
):
    scored = _score(_hypothesis(missing_count=missing_count))

    assert scored.confidence == pytest.approx(0.94 - expected_penalty)


def test_combined_penalties_produce_expected_golden_style_score():
    scored = _score(_hypothesis(counter_count=1, missing_count=2))

    assert scored.confidence == pytest.approx(0.69)


def test_final_score_is_clamped_to_zero():
    scored = _score(
        _hypothesis(
            covered_source_ids=[],
            counter_count=1,
            missing_count=5,
        ),
        relationship=_relationship(confidence=0.0),
    )

    assert scored.confidence == 0.0


def test_final_score_never_exceeds_one():
    assert _score(
        _hypothesis(), relationship=_relationship(confidence=1.0)
    ).confidence == 1.0


def test_relationship_confidence_has_weight_point_three():
    low = _score(
        _hypothesis(), relationship=_relationship(confidence=0.2)
    ).confidence
    high = _score(
        _hypothesis(), relationship=_relationship(confidence=0.8)
    ).confidence

    assert high - low == pytest.approx(0.30 * (0.8 - 0.2))


def test_causality_safety_contributes_exactly_point_two():
    score_without_other_components = _score(
        _hypothesis(covered_source_ids=[]),
        relationship=_relationship(confidence=0.0),
    ).confidence

    assert score_without_other_components == pytest.approx(0.20)


def test_unrelated_supporting_evidence_does_not_count():
    hypothesis = _hypothesis(covered_source_ids=["unrelated-insight"])

    assert _score(hypothesis).confidence == pytest.approx(0.44)


def test_zero_source_insights_is_rejected():
    with pytest.raises(ValueError, match="at least one source insight"):
        _score(_hypothesis(source_ids=[]))


@pytest.mark.parametrize("relationship_ids", [[], ["first", "second"]])
def test_non_single_source_relationship_is_rejected(relationship_ids):
    with pytest.raises(ValueError, match="exactly one"):
        _score(_hypothesis(relationship_ids=relationship_ids))


def test_unresolved_relationship_is_rejected():
    with pytest.raises(ValueError, match="could not be resolved"):
        calculate_hypothesis_confidence(_hypothesis(), [], [_evaluation()])


def test_relationship_not_corresponding_to_source_pair_is_rejected():
    relationship = _relationship().model_copy(
        update={"target_insight_id": "unrelated-insight"}
    )

    with pytest.raises(ValueError, match="does not correspond"):
        _score(_hypothesis(), relationship=relationship)


def test_non_co_movement_relationship_is_rejected():
    with pytest.raises(ValueError, match="must be CO_MOVES_WITH"):
        _score(
            _hypothesis(),
            relationship=_relationship(
                relationship_type=RelationshipType.CONTRIBUTES_TO
            ),
        )


def test_missing_causality_evaluation_is_rejected():
    with pytest.raises(ValueError, match="evaluation could not be resolved"):
        calculate_hypothesis_confidence(_hypothesis(), [_relationship()], [])


def test_absent_association_is_rejected():
    with pytest.raises(ValueError, match="association evidence"):
        _score(_hypothesis(), evaluation=_evaluation(association_present=False))


def test_established_causality_is_rejected():
    with pytest.raises(ValueError, match="Established causality"):
        _score(
            _hypothesis(),
            evaluation=_evaluation(
                causality_established=True,
                status=CausalityStatus.CAUSALITY_ESTABLISHED,
            ),
        )


@pytest.mark.parametrize("confidence", [-0.1, 1.1, float("nan")])
def test_malformed_relationship_confidence_is_rejected(confidence):
    relationship = Relationship.model_construct(
        id=RELATIONSHIP_ID,
        analysis_id=ANALYSIS_ID,
        source_insight_id=MARKETING_ID,
        target_insight_id=REVENUE_ID,
        type=RelationshipType.CO_MOVES_WITH,
        strength=0.8,
        confidence=confidence,
        strength_breakdown={},
        confidence_breakdown={},
        reasons=[],
        metadata={},
    )

    with pytest.raises(ValueError, match="finite and in"):
        _score(_hypothesis(), relationship=relationship)


def test_scoring_changes_only_confidence_and_appends_reasons():
    hypothesis = _hypothesis(counter_count=1, missing_count=1)
    scored = _score(hypothesis)

    assert scored.status == hypothesis.status == "OPEN"
    assert scored.statement == hypothesis.statement
    assert scored.supporting_evidence == hypothesis.supporting_evidence
    assert scored.counter_evidence == hypothesis.counter_evidence
    assert scored.missing_context == hypothesis.missing_context
    assert scored.reasons[:2] == hypothesis.reasons
    assert "Supporting evidence coverage: 2/2." in scored.reasons
    assert "Relationship confidence: 0.8." in scored.reasons
    assert "Counter evidence penalty: 0.15." in scored.reasons
    assert "Missing context penalty: 0.05." in scored.reasons
    assert "Hypothesis confidence: 0.74." in scored.reasons


def test_repeated_scoring_is_structurally_identical():
    first = _score(_hypothesis(counter_count=1, missing_count=2))
    second = _score(first)

    assert second == first


def test_input_objects_are_not_mutated():
    hypothesis = _hypothesis(counter_count=1, missing_count=2)
    relationships = [_relationship()]
    evaluations = [_evaluation()]
    before = deepcopy((hypothesis, relationships, evaluations))

    calculate_hypothesis_confidence(
        hypothesis,
        relationships,
        evaluations,
    )

    assert (hypothesis, relationships, evaluations) == before
