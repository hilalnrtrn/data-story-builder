from copy import deepcopy

import pytest

from app.models.causality import CausalityStatus
from app.models.hypothesis import (
    Hypothesis,
    HypothesisEvidenceReference,
    HypothesisMissingContextReference,
    HypothesisStatus,
)
from app.models.insight import InsightDirection
from app.models.insight_integrity import CounterEvidenceItem
from app.models.missing_context import MissingContextItem, MissingContextStatus
from app.services.hypothesis_tracker import (
    is_hypothesis_transition_allowed,
    transition_hypothesis_status,
)


def _hypothesis(
    status: HypothesisStatus = HypothesisStatus.OPEN,
    confidence: float = 0.69,
) -> Hypothesis:
    return Hypothesis(
        id="HYPOTHESIS-MarketingSpend-Revenue",
        analysisId="550e8400-e29b-41d4-a716-446655440000",
        statement=(
            "The observed change in MarketingSpend may be associated with "
            "the observed change in Revenue."
        ),
        status=status,
        confidence=confidence,
        sourceInsightIds=["marketing-insight", "revenue-insight"],
        sourceRelationshipIds=["marketing-revenue-relationship"],
        supportingEvidence=[
            HypothesisEvidenceReference(
                insightId="marketing-insight",
                evidenceCode="CHANGE",
            )
        ],
        counterEvidence=[
            CounterEvidenceItem(
                insightId="orders-insight",
                relationshipId="orders-revenue-relationship",
                metric="Orders",
                direction=InsightDirection.DOWN,
                reasons=["Orders moved in the opposite direction."],
            )
        ],
        missingContext=[
            HypothesisMissingContextReference(
                sourceInsightId="revenue-insight",
                item=MissingContextItem(
                    field="CompetitorPrice",
                    status=MissingContextStatus.NOT_AVAILABLE,
                    isDataQualityError=False,
                    reason="Competitor pricing context is unavailable.",
                ),
            )
        ],
        causalityStatus=CausalityStatus.CAUSALITY_NOT_ESTABLISHED,
        reasons=["Causality is not established."],
        trackerVersion="day16-v1",
    )


@pytest.mark.parametrize(
    "current_status, target_status",
    [
        (HypothesisStatus.OPEN, HypothesisStatus.SUPPORTED),
        (HypothesisStatus.OPEN, HypothesisStatus.REJECTED),
        (HypothesisStatus.SUPPORTED, HypothesisStatus.CONFIRMED),
        (HypothesisStatus.SUPPORTED, HypothesisStatus.REJECTED),
    ],
)
def test_locked_transitions_are_allowed(current_status, target_status):
    original = _hypothesis(current_status)

    transitioned = transition_hypothesis_status(original, target_status)

    assert transitioned.status == target_status.value
    assert is_hypothesis_transition_allowed(current_status, target_status)


@pytest.mark.parametrize(
    "current_status, target_status",
    [
        (HypothesisStatus.OPEN, HypothesisStatus.CONFIRMED),
        (HypothesisStatus.SUPPORTED, HypothesisStatus.OPEN),
        (HypothesisStatus.CONFIRMED, HypothesisStatus.OPEN),
        (HypothesisStatus.CONFIRMED, HypothesisStatus.SUPPORTED),
        (HypothesisStatus.CONFIRMED, HypothesisStatus.REJECTED),
        (HypothesisStatus.REJECTED, HypothesisStatus.OPEN),
        (HypothesisStatus.REJECTED, HypothesisStatus.SUPPORTED),
        (HypothesisStatus.REJECTED, HypothesisStatus.CONFIRMED),
    ],
)
def test_all_other_cross_state_transitions_are_rejected(
    current_status,
    target_status,
):
    assert not is_hypothesis_transition_allowed(current_status, target_status)

    with pytest.raises(ValueError, match="is not allowed"):
        transition_hypothesis_status(
            _hypothesis(current_status),
            target_status,
        )


@pytest.mark.parametrize("status", list(HypothesisStatus))
def test_same_state_transition_is_explicitly_rejected(status):
    assert not is_hypothesis_transition_allowed(status, status)

    with pytest.raises(ValueError, match="is not allowed"):
        transition_hypothesis_status(_hypothesis(status), status)


@pytest.mark.parametrize("confidence", [0.0, 1.0])
def test_confidence_does_not_automatically_change_open_status(confidence):
    hypothesis = _hypothesis(confidence=confidence)

    assert hypothesis.status == "OPEN"


def test_counter_evidence_missing_context_and_causality_do_not_change_status():
    hypothesis = _hypothesis()

    assert hypothesis.counter_evidence
    assert hypothesis.missing_context
    assert hypothesis.causality_status == "CAUSALITY_NOT_ESTABLISHED"
    assert hypothesis.status == "OPEN"


def test_valid_transition_changes_only_status_and_appends_lifecycle_reason():
    hypothesis = _hypothesis()
    transitioned = transition_hypothesis_status(
        hypothesis,
        HypothesisStatus.SUPPORTED,
    )

    original = hypothesis.model_dump()
    changed = transitioned.model_dump()
    assert changed.pop("status") == "SUPPORTED"
    reasons = changed.pop("reasons")
    assert original.pop("status") == "OPEN"
    original_reasons = original.pop("reasons")
    assert reasons == [
        *original_reasons,
        "Hypothesis status changed from OPEN to SUPPORTED.",
    ]
    assert changed == original


def test_transition_preserves_all_analytical_fields_exactly():
    hypothesis = _hypothesis(confidence=0.73456789)
    transitioned = transition_hypothesis_status(
        hypothesis,
        HypothesisStatus.REJECTED,
    )

    assert transitioned.id == hypothesis.id
    assert transitioned.analysis_id == hypothesis.analysis_id
    assert transitioned.statement == hypothesis.statement
    assert transitioned.confidence == hypothesis.confidence
    assert transitioned.source_insight_ids == hypothesis.source_insight_ids
    assert (
        transitioned.source_relationship_ids
        == hypothesis.source_relationship_ids
    )
    assert transitioned.supporting_evidence == hypothesis.supporting_evidence
    assert transitioned.counter_evidence == hypothesis.counter_evidence
    assert transitioned.missing_context == hypothesis.missing_context
    assert transitioned.causality_status == hypothesis.causality_status
    assert transitioned.tracker_version == hypothesis.tracker_version


def test_input_hypothesis_is_not_mutated():
    hypothesis = _hypothesis()
    before = deepcopy(hypothesis)

    transitioned = transition_hypothesis_status(
        hypothesis,
        HypothesisStatus.SUPPORTED,
    )

    assert transitioned is not hypothesis
    assert hypothesis == before


def test_repeated_transition_from_same_original_is_deterministic():
    hypothesis = _hypothesis()

    assert transition_hypothesis_status(
        hypothesis,
        HypothesisStatus.SUPPORTED,
    ) == transition_hypothesis_status(
        hypothesis,
        HypothesisStatus.SUPPORTED,
    )
