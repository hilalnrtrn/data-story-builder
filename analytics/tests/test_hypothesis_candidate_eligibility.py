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
    find_hypothesis_candidates,
)


ANALYSIS_ID = "550e8400-e29b-41d4-a716-446655440000"
MARKETING_ID = "CHANGE-MarketingSpend-2025-05-2025-06"
REVENUE_ID = "CHANGE-Revenue-2025-05-2025-06"


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
    relationship_id: str = "CO_MOVES_WITH-MarketingSpend-Revenue",
    relationship_type: RelationshipType = RelationshipType.CO_MOVES_WITH,
    source_id: str = MARKETING_ID,
    target_id: str = REVENUE_ID,
    analysis_id: str = ANALYSIS_ID,
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


def _causality(
    relationship: Relationship,
    *,
    association_present: bool = True,
    causality_established: bool = False,
    status: CausalityStatus = CausalityStatus.CAUSALITY_NOT_ESTABLISHED,
) -> CausalityEvaluation:
    return CausalityEvaluation(
        sourceInsightId=relationship.source_insight_id,
        targetInsightId=relationship.target_insight_id,
        relationshipId=relationship.id,
        sourceMetric="MarketingSpend",
        targetMetric="Revenue",
        associationPresent=association_present,
        causalityEstablished=causality_established,
        status=status,
    )


def _insights() -> list[Insight]:
    return [
        _insight(MARKETING_ID, "MarketingSpend"),
        _insight(REVENUE_ID, "Revenue"),
    ]


def test_golden_style_unestablished_co_movement_is_eligible():
    relationship = _relationship()

    assert find_hypothesis_candidates(
        _insights(),
        [relationship],
        [_causality(relationship)],
    ) == [
        HypothesisCandidate(
            relationship.id,
            MARKETING_ID,
            REVENUE_ID,
        )
    ]


@pytest.mark.parametrize(
    "relationship_type",
    [
        RelationshipType.CONTRIBUTES_TO,
        RelationshipType.COUNTER_SIGNAL,
        RelationshipType.RELATED_ANOMALY,
        RelationshipType.DRILLDOWN_OF,
    ],
)
def test_non_co_movement_relationship_is_not_eligible(relationship_type):
    relationship = _relationship(relationship_type=relationship_type)

    assert find_hypothesis_candidates(
        _insights(), [relationship], [_causality(relationship)]
    ) == []


@pytest.mark.parametrize("missing_id", [MARKETING_ID, REVENUE_ID])
def test_unknown_relationship_endpoint_is_rejected(missing_id):
    relationship = _relationship()
    insights = [item for item in _insights() if item.id != missing_id]

    assert find_hypothesis_candidates(
        insights, [relationship], [_causality(relationship)]
    ) == []


def test_missing_causality_evaluation_is_rejected():
    assert find_hypothesis_candidates(_insights(), [_relationship()], []) == []


def test_established_causality_is_rejected():
    relationship = _relationship()

    assert find_hypothesis_candidates(
        _insights(),
        [relationship],
        [
            _causality(
                relationship,
                causality_established=True,
                status=CausalityStatus.CAUSALITY_ESTABLISHED,
            )
        ],
    ) == []


def test_absent_association_is_rejected():
    relationship = _relationship()

    assert find_hypothesis_candidates(
        _insights(),
        [relationship],
        [_causality(relationship, association_present=False)],
    ) == []


@pytest.mark.parametrize(
    "status",
    [CausalityStatus.NOT_APPLICABLE, CausalityStatus.CAUSALITY_ESTABLISHED],
)
def test_non_association_causality_status_is_rejected(status):
    relationship = _relationship()

    assert find_hypothesis_candidates(
        _insights(), [relationship], [_causality(relationship, status=status)]
    ) == []


def test_association_only_status_is_an_allowed_unestablished_state():
    relationship = _relationship()

    assert len(
        find_hypothesis_candidates(
            _insights(),
            [relationship],
            [
                _causality(
                    relationship,
                    status=CausalityStatus.ASSOCIATION_ONLY,
                )
            ],
        )
    ) == 1


def test_cross_analysis_endpoint_resolution_is_rejected():
    relationship = _relationship(analysis_id="another-analysis")

    assert find_hypothesis_candidates(
        _insights(), [relationship], [_causality(relationship)]
    ) == []


def test_defensive_self_relationship_rejection():
    relationship = Relationship.model_construct(
        id="self-edge",
        analysis_id=ANALYSIS_ID,
        source_insight_id=MARKETING_ID,
        target_insight_id=MARKETING_ID,
        type=RelationshipType.CO_MOVES_WITH,
        strength=0.8,
        confidence=0.75,
        strength_breakdown={},
        confidence_breakdown={},
        reasons=[],
        metadata={},
    )

    assert find_hypothesis_candidates(
        _insights(), [relationship], [_causality(relationship)]
    ) == []


def test_duplicate_logical_candidate_is_deduplicated():
    relationship = _relationship()
    evaluation = _causality(relationship)

    candidates = find_hypothesis_candidates(
        _insights(),
        [relationship, relationship.model_copy(deep=True)],
        [evaluation, evaluation.model_copy(deep=True)],
    )

    assert len(candidates) == 1


def test_reversed_relationship_remains_a_distinct_directed_candidate():
    forward = _relationship(relationship_id="relationship-forward")
    reverse = _relationship(
        relationship_id="relationship-reverse",
        source_id=REVENUE_ID,
        target_id=MARKETING_ID,
    )

    candidates = find_hypothesis_candidates(
        _insights(),
        [reverse, forward],
        [_causality(reverse), _causality(forward)],
    )

    assert candidates == [
        HypothesisCandidate("relationship-forward", MARKETING_ID, REVENUE_ID),
        HypothesisCandidate("relationship-reverse", REVENUE_ID, MARKETING_ID),
    ]


def test_output_order_is_deterministic():
    second = _relationship(relationship_id="relationship-b")
    first = _relationship(relationship_id="relationship-a")

    candidates = find_hypothesis_candidates(
        _insights(),
        [second, first],
        [_causality(second), _causality(first)],
    )

    assert [candidate.relationship_id for candidate in candidates] == [
        "relationship-a",
        "relationship-b",
    ]


def test_inputs_are_not_mutated():
    insights = _insights()
    relationships = [_relationship()]
    evaluations = [_causality(relationships[0])]
    before = deepcopy((insights, relationships, evaluations))

    find_hypothesis_candidates(insights, relationships, evaluations)

    assert (insights, relationships, evaluations) == before


def test_stage_d_candidate_is_not_a_hypothesis_and_has_no_statement():
    relationship = _relationship()
    candidate = find_hypothesis_candidates(
        _insights(), [relationship], [_causality(relationship)]
    )[0]

    assert not isinstance(candidate, Hypothesis)
    assert not hasattr(candidate, "statement")
