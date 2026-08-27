from copy import deepcopy

from app.models.causality import CausalityStatus
from app.models.hypothesis import Hypothesis, HypothesisEvidenceReference
from app.models.insight import InsightDirection
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
from app.services.hypothesis_tracker import (
    attach_counter_evidence_and_missing_context,
)


ANALYSIS_ID = "550e8400-e29b-41d4-a716-446655440000"
MARKETING_ID = "CHANGE-MarketingSpend-2025-05-2025-06"
REVENUE_ID = "CHANGE-Revenue-2025-05-2025-06"


def _hypothesis(source_ids: list[str] | None = None) -> Hypothesis:
    return Hypothesis(
        id="HYPOTHESIS-MarketingSpend-Revenue",
        analysisId=ANALYSIS_ID,
        statement=(
            "The observed change in MarketingSpend may be associated with "
            "the observed change in Revenue."
        ),
        status="OPEN",
        confidence=0.0,
        sourceInsightIds=source_ids or [MARKETING_ID, REVENUE_ID],
        sourceRelationshipIds=["CO_MOVES_WITH-MarketingSpend-Revenue"],
        supportingEvidence=[
            HypothesisEvidenceReference(
                insightId=MARKETING_ID,
                evidenceCode="CHANGE",
            )
        ],
        causalityStatus=CausalityStatus.CAUSALITY_NOT_ESTABLISHED,
        reasons=["Causality is not established."],
        trackerVersion="day16-v1",
    )


def _counter(
    insight_id: str,
    relationship_id: str,
    metric: str,
    reason: str,
) -> CounterEvidenceItem:
    return CounterEvidenceItem(
        insightId=insight_id,
        relationshipId=relationship_id,
        metric=metric,
        direction=InsightDirection.DOWN,
        reasons=[reason],
    )


def _integrity(
    insight_id: str,
    counter_evidence: list[CounterEvidenceItem],
) -> InsightIntegrityEvaluation:
    return InsightIntegrityEvaluation(
        insightId=insight_id,
        status=IntegrityStatus.PASS_WITH_WARNINGS,
        counterEvidence=counter_evidence,
        integrityScore=0.8,
        storyEligible=True,
        requiresQualification=bool(counter_evidence),
    )


def _missing_item(
    field: str,
    reason: str,
    is_data_quality_error: bool = False,
) -> MissingContextItem:
    return MissingContextItem(
        field=field,
        status=MissingContextStatus.NOT_AVAILABLE,
        isDataQualityError=is_data_quality_error,
        reason=reason,
    )


def _missing(
    insight_id: str,
    items: list[MissingContextItem],
) -> MissingContextEvaluation:
    return MissingContextEvaluation(
        insightId=insight_id,
        missingContext=items,
        interpretationLimited=bool(items),
        reasons=(
            ["Interpretation is limited by unavailable context."]
            if items
            else []
        ),
    )


def _structured_outputs():
    first_counter = _counter(
        "CHANGE-Orders-2025-05-2025-06",
        "COUNTER_SIGNAL-Orders-MarketingSpend",
        "Orders",
        "Orders moved in the opposite direction.",
    )
    second_counter = _counter(
        "CHANGE-Customers-2025-05-2025-06",
        "COUNTER_SIGNAL-Customers-Revenue",
        "Customers",
        "Customers moved in the opposite direction.",
    )
    integrity = [
        _integrity(MARKETING_ID, [first_counter]),
        _integrity(REVENUE_ID, [second_counter]),
    ]
    missing = [
        _missing(
            MARKETING_ID,
            [_missing_item("CampaignType", "Campaign type is unavailable.")],
        ),
        _missing(
            REVENUE_ID,
            [
                _missing_item(
                    "CompetitorPrice",
                    "Competitor pricing context is unavailable.",
                ),
                _missing_item(
                    "UnitPrice",
                    "Individual selling prices are unavailable.",
                ),
            ],
        ),
    ]
    return integrity, missing


def test_counter_evidence_from_both_source_insights_is_attached_in_order():
    integrity, missing = _structured_outputs()

    linked = attach_counter_evidence_and_missing_context(
        _hypothesis(), integrity, missing
    )

    assert [item.metric for item in linked.counter_evidence] == [
        "Orders",
        "Customers",
    ]


def test_source_order_precedes_upstream_counter_evidence_order():
    first = _counter("counter-1", "relationship-1", "First", "First reason")
    second = _counter(
        "counter-2", "relationship-2", "Second", "Second reason"
    )
    third = _counter("counter-3", "relationship-3", "Third", "Third reason")
    integrity = [
        _integrity(MARKETING_ID, [first, second]),
        _integrity(REVENUE_ID, [third]),
    ]

    linked = attach_counter_evidence_and_missing_context(
        _hypothesis(), integrity, []
    )

    assert [item.metric for item in linked.counter_evidence] == [
        "First",
        "Second",
        "Third",
    ]


def test_unrelated_integrity_evaluation_is_ignored():
    integrity, missing = _structured_outputs()
    integrity.append(
        _integrity(
            "unrelated-insight",
            [_counter("other", "other-rel", "Unrelated", "Ignore this")],
        )
    )

    linked = attach_counter_evidence_and_missing_context(
        _hypothesis(), integrity, missing
    )

    assert all(item.metric != "Unrelated" for item in linked.counter_evidence)


def test_identical_counter_evidence_is_deduplicated():
    duplicate = _counter(
        "counter-insight",
        "counter-relationship",
        "Orders",
        "Orders moved in the opposite direction.",
    )
    integrity = [_integrity(MARKETING_ID, [duplicate, duplicate.model_copy()])]

    linked = attach_counter_evidence_and_missing_context(
        _hypothesis(), integrity, []
    )

    assert len(linked.counter_evidence) == 1


def test_missing_context_from_both_sources_preserves_provenance_and_order():
    integrity, missing = _structured_outputs()

    linked = attach_counter_evidence_and_missing_context(
        _hypothesis(), integrity, missing
    )

    assert [
        (reference.source_insight_id, reference.item.field)
        for reference in linked.missing_context
    ] == [
        (MARKETING_ID, "CampaignType"),
        (REVENUE_ID, "CompetitorPrice"),
        (REVENUE_ID, "UnitPrice"),
    ]


def test_unrelated_missing_context_evaluation_is_ignored():
    integrity, missing = _structured_outputs()
    missing.append(
        _missing(
            "unrelated-insight",
            [_missing_item("UnrelatedField", "Ignore this field.")],
        )
    )

    linked = attach_counter_evidence_and_missing_context(
        _hypothesis(), integrity, missing
    )

    assert all(
        reference.item.field != "UnrelatedField"
        for reference in linked.missing_context
    )


def test_duplicate_missing_context_is_deduplicated_by_source_and_field():
    first = _missing_item("CompetitorPrice", "First authoritative reason.")
    duplicate = _missing_item(
        "CompetitorPrice", "Duplicate upstream reason."
    )
    missing = [_missing(REVENUE_ID, [first, duplicate])]

    linked = attach_counter_evidence_and_missing_context(
        _hypothesis(), [], missing
    )

    assert len(linked.missing_context) == 1
    assert linked.missing_context[0].item.reason == "First authoritative reason."


def test_missing_context_item_semantics_are_preserved_exactly():
    item = _missing_item(
        "CompetitorPrice",
        "Competitor pricing context is unavailable.",
        is_data_quality_error=False,
    )

    linked = attach_counter_evidence_and_missing_context(
        _hypothesis(), [], [_missing(REVENUE_ID, [item])]
    )
    preserved = linked.missing_context[0].item

    assert preserved == item
    assert preserved.status == "NOT_AVAILABLE"
    assert preserved.is_data_quality_error is False
    assert preserved.reason == item.reason


def test_no_new_missing_context_fields_are_invented():
    _, missing = _structured_outputs()

    linked = attach_counter_evidence_and_missing_context(
        _hypothesis(), [], missing
    )

    assert {reference.item.field for reference in linked.missing_context} == {
        "CampaignType",
        "CompetitorPrice",
        "UnitPrice",
    }


def test_absent_evaluations_contribute_empty_collections():
    linked = attach_counter_evidence_and_missing_context(
        _hypothesis(), [], []
    )

    assert linked.counter_evidence == []
    assert linked.missing_context == []


def test_non_stage_g_fields_remain_unchanged():
    hypothesis = _hypothesis()
    integrity, missing = _structured_outputs()

    linked = attach_counter_evidence_and_missing_context(
        hypothesis, integrity, missing
    )

    assert linked.status == hypothesis.status == "OPEN"
    assert linked.confidence == hypothesis.confidence == 0.0
    assert linked.statement == hypothesis.statement
    assert linked.supporting_evidence == hypothesis.supporting_evidence


def test_input_hypothesis_is_not_mutated():
    hypothesis = _hypothesis()
    integrity, missing = _structured_outputs()

    linked = attach_counter_evidence_and_missing_context(
        hypothesis, integrity, missing
    )

    assert linked is not hypothesis
    assert hypothesis.counter_evidence == []
    assert hypothesis.missing_context == []


def test_input_evaluation_objects_are_not_mutated():
    integrity, missing = _structured_outputs()
    before = deepcopy((integrity, missing))

    attach_counter_evidence_and_missing_context(
        _hypothesis(), integrity, missing
    )

    assert (integrity, missing) == before


def test_repeated_call_is_structurally_identical():
    integrity, missing = _structured_outputs()

    assert attach_counter_evidence_and_missing_context(
        _hypothesis(), integrity, missing
    ) == attach_counter_evidence_and_missing_context(
        _hypothesis(), integrity, missing
    )
