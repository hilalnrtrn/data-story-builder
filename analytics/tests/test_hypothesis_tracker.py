from copy import deepcopy

import pytest

import app.services.hypothesis_tracker as tracker_module
from app.models.causality import CausalityEvaluation, CausalityStatus
from app.models.insight import (
    Evidence,
    Insight,
    InsightDirection,
    InsightType,
    PeriodGranularity,
)
from app.models.insight_integrity import (
    CounterEvidenceItem,
    InsightIntegrityEvaluation,
    IntegrityStatus,
)
from app.models.missing_context import (
    MissingContextEvaluation,
    MissingContextItem,
    MissingContextStatus,
)
from app.models.relationship import Relationship, RelationshipType
from app.services.hypothesis_tracker import track_hypotheses


ANALYSIS_ID = "550e8400-e29b-41d4-a716-446655440000"
MARKETING_ID = "CHANGE-MarketingSpend-2025-05-2025-06"
REVENUE_ID = "CHANGE-Revenue-2025-05-2025-06"
RELATIONSHIP_ID = "CO_MOVES_WITH-MarketingSpend-Revenue"


def _insight(
    insight_id: str,
    metric: str,
    relative_change: float,
) -> Insight:
    return Insight(
        id=insight_id,
        analysisId=ANALYSIS_ID,
        type=InsightType.CHANGE,
        metric=metric,
        periodGranularity=PeriodGranularity.MONTH,
        period={"previous": "2025-05", "current": "2025-06"},
        direction=InsightDirection.UP,
        values={"relativeChange": relative_change},
        evidence=[
            Evidence(
                code="RELATIVE_CHANGE",
                label="Relative change",
                value=relative_change,
                unit="PERCENT",
            )
        ],
    )


def _relationship(
    relationship_id: str = RELATIONSHIP_ID,
    source_id: str = MARKETING_ID,
    target_id: str = REVENUE_ID,
    relationship_type: RelationshipType = RelationshipType.CO_MOVES_WITH,
    confidence: float = 0.8,
) -> Relationship:
    return Relationship(
        id=relationship_id,
        analysisId=ANALYSIS_ID,
        sourceInsightId=source_id,
        targetInsightId=target_id,
        type=relationship_type,
        strength=0.85,
        confidence=confidence,
    )


def _causality(
    relationship: Relationship,
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


def _integrity() -> list[InsightIntegrityEvaluation]:
    counter = CounterEvidenceItem(
        insightId="CHANGE-Orders-2025-05-2025-06",
        relationshipId="COUNTER_SIGNAL-Orders-Revenue",
        metric="Orders",
        direction=InsightDirection.DOWN,
        reasons=["Orders moved in the opposite direction."],
    )
    return [
        InsightIntegrityEvaluation(
            insightId=MARKETING_ID,
            status=IntegrityStatus.PASS,
            integrityScore=0.9,
            storyEligible=True,
            requiresQualification=False,
        ),
        InsightIntegrityEvaluation(
            insightId=REVENUE_ID,
            status=IntegrityStatus.PASS_WITH_WARNINGS,
            counterEvidence=[counter],
            integrityScore=0.8,
            storyEligible=True,
            requiresQualification=True,
        ),
    ]


def _missing_context() -> list[MissingContextEvaluation]:
    items = [
        MissingContextItem(
            field=field,
            status=MissingContextStatus.NOT_AVAILABLE,
            isDataQualityError=False,
            reason=f"{field} is unavailable.",
        )
        for field in ("CompetitorPrice", "UnitPrice", "PricingChange")
    ]
    return [
        MissingContextEvaluation(
            insightId=MARKETING_ID,
            missingContext=[],
            interpretationLimited=False,
        ),
        MissingContextEvaluation(
            insightId=REVENUE_ID,
            missingContext=items,
            interpretationLimited=True,
            reasons=["Interpretation is limited by unavailable context."],
        ),
    ]


def _inputs():
    insights = [
        _insight(MARKETING_ID, "MarketingSpend", 20),
        _insight(REVENUE_ID, "Revenue", 30),
    ]
    relationship = _relationship()
    return (
        insights,
        [relationship],
        _integrity(),
        [_causality(relationship)],
        _missing_context(),
    )


def test_golden_style_inputs_produce_one_fully_linked_open_hypothesis():
    hypotheses = track_hypotheses(*_inputs())

    assert len(hypotheses) == 1
    hypothesis = hypotheses[0]
    assert hypothesis.status == "OPEN"
    assert hypothesis.statement == (
        "The observed change in MarketingSpend may be associated with "
        "the observed change in Revenue."
    )
    assert [
        (item.insight_id, item.evidence_code)
        for item in hypothesis.supporting_evidence
    ] == [
        (MARKETING_ID, "RELATIVE_CHANGE"),
        (REVENUE_ID, "RELATIVE_CHANGE"),
    ]
    assert [item.metric for item in hypothesis.counter_evidence] == ["Orders"]
    assert [item.item.field for item in hypothesis.missing_context] == [
        "CompetitorPrice",
        "UnitPrice",
        "PricingChange",
    ]
    assert all(
        item.source_insight_id == REVENUE_ID
        for item in hypothesis.missing_context
    )
    assert hypothesis.confidence == pytest.approx(0.64)
    assert hypothesis.causality_status == "CAUSALITY_NOT_ESTABLISHED"
    assert hypothesis.source_insight_ids == [MARKETING_ID, REVENUE_ID]
    assert hypothesis.source_relationship_ids == [RELATIONSHIP_ID]
    assert hypothesis.id.startswith("HYPOTHESIS-")
    assert len(hypothesis.id) == len("HYPOTHESIS-") + 64
    assert hypothesis.reasons[:2] == [
        "CO_MOVES_WITH association detected.",
        "Causality is not established.",
    ]
    assert "Supporting evidence coverage: 2/2." in hypothesis.reasons
    assert "Hypothesis confidence: 0.64." in hypothesis.reasons


def test_no_eligible_candidate_returns_empty_list():
    insights, _, integrity, _, missing = _inputs()

    assert track_hypotheses(insights, [], integrity, [], missing) == []


@pytest.mark.parametrize(
    "relationship_type",
    [RelationshipType.CONTRIBUTES_TO, RelationshipType.COUNTER_SIGNAL],
)
def test_non_co_movement_relationship_does_not_create_hypothesis(
    relationship_type,
):
    insights, _, integrity, _, missing = _inputs()
    relationship = _relationship(relationship_type=relationship_type)

    assert track_hypotheses(
        insights,
        [relationship],
        integrity,
        [_causality(relationship)],
        missing,
    ) == []


def test_established_causality_does_not_create_hypothesis():
    insights, relationships, integrity, _, missing = _inputs()

    assert track_hypotheses(
        insights,
        relationships,
        integrity,
        [_causality(relationships[0], established=True)],
        missing,
    ) == []


def test_unrelated_integrity_and_missing_context_do_not_affect_output():
    inputs = list(_inputs())
    baseline = track_hypotheses(*inputs)
    inputs[2].append(
        InsightIntegrityEvaluation(
            insightId="unrelated-insight",
            status=IntegrityStatus.FAIL,
            counterEvidence=[
                CounterEvidenceItem(
                    insightId="other",
                    relationshipId="other-relationship",
                    metric="Unrelated",
                    direction=InsightDirection.DOWN,
                )
            ],
            storyEligible=False,
            requiresQualification=True,
        )
    )
    inputs[4].append(
        MissingContextEvaluation(
            insightId="unrelated-insight",
            missingContext=[
                MissingContextItem(
                    field="UnrelatedField",
                    status=MissingContextStatus.NOT_AVAILABLE,
                    isDataQualityError=False,
                    reason="Unrelated context.",
                )
            ],
            interpretationLimited=True,
        )
    )

    assert track_hypotheses(*inputs) == baseline


def test_unrelated_causality_evaluation_does_not_create_hypothesis():
    inputs = list(_inputs())
    unrelated_relationship = _relationship(
        relationship_id="unrelated-relationship"
    )
    inputs[3].append(_causality(unrelated_relationship))

    assert track_hypotheses(*inputs) == track_hypotheses(*_inputs())


def test_multiple_candidates_follow_stage_d_deterministic_order():
    insights, relationships, integrity, evaluations, missing = _inputs()
    orders_id = "CHANGE-Orders-2025-05-2025-06"
    insights.append(_insight(orders_id, "Orders", 15))
    integrity.append(
        InsightIntegrityEvaluation(
            insightId=orders_id,
            status=IntegrityStatus.PASS,
            integrityScore=0.9,
            storyEligible=True,
            requiresQualification=False,
        )
    )
    second = _relationship(
        relationship_id="A-CO_MOVES_WITH-Orders-Revenue",
        source_id=orders_id,
        target_id=REVENUE_ID,
    )
    relationships.insert(0, second)
    evaluations.insert(0, _causality(second))

    hypotheses = track_hypotheses(
        insights,
        relationships,
        integrity,
        evaluations,
        missing,
    )

    assert [item.source_relationship_ids[0] for item in hypotheses] == [
        "A-CO_MOVES_WITH-Orders-Revenue",
        RELATIONSHIP_ID,
    ]


def test_duplicate_logical_candidate_produces_one_hypothesis():
    insights, relationships, integrity, evaluations, missing = _inputs()

    hypotheses = track_hypotheses(
        insights,
        [relationships[0], relationships[0].model_copy(deep=True)],
        integrity,
        [evaluations[0], evaluations[0].model_copy(deep=True)],
        missing,
    )

    assert len(hypotheses) == 1


def test_repeated_tracker_call_is_structurally_identical():
    assert track_hypotheses(*_inputs()) == track_hypotheses(*_inputs())


def test_all_input_collections_and_models_are_not_mutated():
    inputs = _inputs()
    before = deepcopy(inputs)

    track_hypotheses(*inputs)

    assert inputs == before


def test_confidence_and_adverse_signals_do_not_change_open_status():
    hypotheses = track_hypotheses(*_inputs())

    assert hypotheses[0].confidence > 0.0
    assert hypotheses[0].counter_evidence
    assert hypotheses[0].missing_context
    assert hypotheses[0].status == "OPEN"


def test_tracker_never_invokes_status_transition_helper(monkeypatch):
    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("Automatic tracking must not transition status")

    monkeypatch.setattr(
        tracker_module,
        "transition_hypothesis_status",
        fail_if_called,
    )

    assert track_hypotheses(*_inputs())[0].status == "OPEN"
