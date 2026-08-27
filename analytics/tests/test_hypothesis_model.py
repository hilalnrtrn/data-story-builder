from copy import deepcopy

import pytest
from pydantic import ValidationError

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


def _evidence_reference() -> HypothesisEvidenceReference:
    return HypothesisEvidenceReference(
        insightId="CHANGE-MarketingSpend-2025-05-2025-06",
        evidenceCode="RELATIVE_CHANGE",
    )


def _missing_context_reference() -> HypothesisMissingContextReference:
    return HypothesisMissingContextReference(
        sourceInsightId="CHANGE-Revenue-2025-05-2025-06",
        item=MissingContextItem(
            field="CompetitorPrice",
            status=MissingContextStatus.NOT_AVAILABLE,
            isDataQualityError=False,
            reason="Competitor pricing context is unavailable.",
        ),
    )


def _hypothesis_values() -> dict:
    return {
        "id": "HYPOTHESIS-MarketingSpend-Revenue-2025-05-2025-06",
        "analysisId": "550e8400-e29b-41d4-a716-446655440000",
        "statement": (
            "MarketingSpend may be associated with the Revenue movement."
        ),
        "status": HypothesisStatus.OPEN,
        "confidence": 0.6,
        "sourceInsightIds": [
            "CHANGE-MarketingSpend-2025-05-2025-06",
            "CHANGE-Revenue-2025-05-2025-06",
        ],
        "sourceRelationshipIds": ["RELATIONSHIP-MarketingSpend-Revenue"],
        "supportingEvidence": [_evidence_reference()],
        "counterEvidence": [],
        "missingContext": [_missing_context_reference()],
        "causalityStatus": CausalityStatus.CAUSALITY_NOT_ESTABLISHED,
        "reasons": ["Association evidence does not establish causality."],
        "trackerVersion": "day16-v1",
    }


def test_valid_open_hypothesis_serializes_with_camel_case_aliases():
    dumped = Hypothesis(**_hypothesis_values()).model_dump(by_alias=True)

    assert dumped["analysisId"] == "550e8400-e29b-41d4-a716-446655440000"
    assert dumped["status"] == "OPEN"
    assert dumped["sourceInsightIds"][0].startswith("CHANGE-MarketingSpend")
    assert dumped["supportingEvidence"] == [
        {
            "insightId": "CHANGE-MarketingSpend-2025-05-2025-06",
            "evidenceCode": "RELATIVE_CHANGE",
        }
    ]
    assert dumped["missingContext"][0]["sourceInsightId"].startswith(
        "CHANGE-Revenue"
    )
    assert dumped["causalityStatus"] == "CAUSALITY_NOT_ESTABLISHED"
    assert dumped["trackerVersion"] == "day16-v1"


def test_all_hypothesis_status_values_are_controlled():
    assert [status.value for status in HypothesisStatus] == [
        "OPEN",
        "SUPPORTED",
        "CONFIRMED",
        "REJECTED",
    ]


@pytest.mark.parametrize(
    "field, alias",
    [
        ("id", "id"),
        ("analysisId", "analysisId"),
        ("statement", "statement"),
        ("trackerVersion", "trackerVersion"),
    ],
)
@pytest.mark.parametrize("blank", ["", "   ", "\t", " \n"])
def test_required_text_fields_reject_blank_values(field, alias, blank):
    values = _hypothesis_values()
    values[alias] = blank

    with pytest.raises(ValidationError):
        Hypothesis(**values)


@pytest.mark.parametrize("confidence", [-0.01, 1.01, float("nan")])
def test_confidence_rejects_out_of_range_or_nan_values(confidence):
    values = _hypothesis_values()
    values["confidence"] = confidence

    with pytest.raises(ValidationError):
        Hypothesis(**values)


@pytest.mark.parametrize("confidence", [float("inf"), float("-inf")])
def test_confidence_rejects_infinite_values(confidence):
    values = _hypothesis_values()
    values["confidence"] = confidence

    with pytest.raises(ValidationError):
        Hypothesis(**values)


def test_confidence_rejects_boolean():
    values = _hypothesis_values()
    values["confidence"] = True

    with pytest.raises(ValidationError):
        Hypothesis(**values)


@pytest.mark.parametrize(
    "field",
    ["sourceInsightIds", "sourceRelationshipIds"],
)
def test_source_identifier_lists_reject_duplicates(field):
    values = _hypothesis_values()
    values[field] = ["duplicate-id", "duplicate-id"]

    with pytest.raises(ValidationError):
        Hypothesis(**values)


@pytest.mark.parametrize(
    "field",
    ["sourceInsightIds", "sourceRelationshipIds"],
)
@pytest.mark.parametrize("blank", ["", "   "])
def test_source_identifier_lists_reject_blank_values(field, blank):
    values = _hypothesis_values()
    values[field] = [blank]

    with pytest.raises(ValidationError):
        Hypothesis(**values)


def test_duplicate_supporting_evidence_references_are_rejected():
    values = _hypothesis_values()
    values["supportingEvidence"] = [
        _evidence_reference(),
        _evidence_reference(),
    ]

    with pytest.raises(ValidationError):
        Hypothesis(**values)


@pytest.mark.parametrize("missing_field", ["insightId", "evidenceCode"])
def test_supporting_evidence_requires_both_identifiers(missing_field):
    values = {
        "insightId": "CHANGE-MarketingSpend-2025-05-2025-06",
        "evidenceCode": "RELATIVE_CHANGE",
    }
    values.pop(missing_field)

    with pytest.raises(ValidationError):
        HypothesisEvidenceReference(**values)


def test_missing_context_reference_preserves_provenance_and_existing_item():
    reference = _missing_context_reference()

    assert reference.source_insight_id == "CHANGE-Revenue-2025-05-2025-06"
    assert isinstance(reference.item, MissingContextItem)
    assert reference.item.field == "CompetitorPrice"
    assert reference.item.is_data_quality_error is False


def test_duplicate_missing_context_references_are_rejected():
    values = _hypothesis_values()
    values["missingContext"] = [
        _missing_context_reference(),
        _missing_context_reference(),
    ]

    with pytest.raises(ValidationError):
        Hypothesis(**values)


def test_existing_counter_evidence_item_can_be_embedded():
    values = _hypothesis_values()
    counter = CounterEvidenceItem(
        insightId="CHANGE-Orders-2025-05-2025-06",
        relationshipId="RELATIONSHIP-Orders-Revenue",
        metric="Orders",
        direction=InsightDirection.DOWN,
        reasons=["Orders moved in the opposite direction."],
    )
    values["counterEvidence"] = [counter]

    hypothesis = Hypothesis(**values)

    assert hypothesis.counter_evidence == [counter]


def test_existing_causality_status_can_be_embedded():
    hypothesis = Hypothesis(**_hypothesis_values())

    assert hypothesis.causality_status == "CAUSALITY_NOT_ESTABLISHED"


def test_default_collections_are_independent_and_inputs_are_not_mutated():
    first_values = _hypothesis_values()
    second_values = _hypothesis_values()
    for values in (first_values, second_values):
        values["sourceInsightIds"] = []
        values["sourceRelationshipIds"] = []
        values["supportingEvidence"] = []
        values["missingContext"] = []
        values["reasons"] = []
    original = deepcopy(first_values)

    first = Hypothesis(**first_values)
    second = Hypothesis(**second_values)
    first.reasons.append("Only the first instance changes.")

    assert second.reasons == []
    assert first_values == original
