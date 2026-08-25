import pytest
from pydantic import ValidationError

from app.models.causality import (
    AllowedCausalityConcept,
    CausalEvidence,
    CausalEvidenceType,
    CausalityEvaluation,
    CausalityResult,
    CausalityStatus,
    ClaimType,
    ForbiddenCausalityConcept,
)


def _evaluation_values() -> dict:
    return {
        "sourceInsightId": "INSIGHT-001",
        "targetInsightId": "INSIGHT-002",
        "relationshipId": "REL-001",
        "sourceMetric": "MarketingSpend",
        "targetMetric": "Revenue",
        "associationPresent": True,
        "causalityEstablished": False,
        "status": CausalityStatus.ASSOCIATION_ONLY,
    }


def test_causality_evaluation_accepts_camel_case_aliases():
    evaluation = CausalityEvaluation(
        **_evaluation_values(),
        allowedConcepts=[AllowedCausalityConcept.ASSOCIATED_WITH],
        forbiddenConcepts=[ForbiddenCausalityConcept.CAUSED],
        reasons=["The relationship shows co-movement only."],
    )

    assert evaluation.model_dump(by_alias=True) == {
        "sourceInsightId": "INSIGHT-001",
        "targetInsightId": "INSIGHT-002",
        "relationshipId": "REL-001",
        "sourceMetric": "MarketingSpend",
        "targetMetric": "Revenue",
        "associationPresent": True,
        "causalityEstablished": False,
        "status": "ASSOCIATION_ONLY",
        "causalEvidence": [],
        "allowedConcepts": ["ASSOCIATED_WITH"],
        "forbiddenConcepts": ["CAUSED"],
        "reasons": ["The relationship shows co-movement only."],
    }


def test_causality_evaluation_accepts_python_field_names():
    evaluation = CausalityEvaluation(
        source_insight_id="INSIGHT-001",
        target_insight_id="INSIGHT-002",
        relationship_id="REL-001",
        source_metric="MarketingSpend",
        target_metric="Revenue",
        association_present=False,
        causality_established=False,
        status=CausalityStatus.NOT_APPLICABLE,
    )

    assert evaluation.source_insight_id == "INSIGHT-001"
    assert evaluation.target_insight_id == "INSIGHT-002"
    assert evaluation.relationship_id == "REL-001"


@pytest.mark.parametrize("status", list(CausalityStatus))
def test_causality_status_serializes_to_controlled_value(status):
    values = _evaluation_values()
    values["status"] = status
    evaluation = CausalityEvaluation(**values)

    assert evaluation.model_dump()["status"] == status.value


def test_allowed_causality_concepts_serialize_to_controlled_values():
    values = _evaluation_values()
    values["allowedConcepts"] = list(AllowedCausalityConcept)
    evaluation = CausalityEvaluation(**values)

    assert evaluation.model_dump()["allowed_concepts"] == [
        concept.value for concept in AllowedCausalityConcept
    ]


def test_forbidden_causality_concepts_serialize_to_controlled_values():
    values = _evaluation_values()
    values["forbiddenConcepts"] = list(ForbiddenCausalityConcept)
    evaluation = CausalityEvaluation(**values)

    assert evaluation.model_dump()["forbidden_concepts"] == [
        concept.value for concept in ForbiddenCausalityConcept
    ]


def test_claim_types_have_exact_serialized_vocabulary():
    assert [claim_type.value for claim_type in ClaimType] == [
        "DESCRIPTIVE",
        "COMPARATIVE",
        "CORRELATIONAL",
        "CAUSAL",
    ]


def test_causal_evidence_types_have_exact_serialized_vocabulary():
    assert [evidence_type.value for evidence_type in CausalEvidenceType] == [
        "CONTROLLED_EXPERIMENT",
        "AB_TEST",
        "RANDOMIZED_INTERVENTION",
        "EXPLICIT_CAUSAL_MODEL",
        "EXTERNAL_CAUSAL_EVIDENCE",
    ]


def test_causal_evidence_accepts_valid_values():
    evidence = CausalEvidence(
        type=CausalEvidenceType.AB_TEST,
        source="Experiment EXP-001",
        description="Random assignment measured incremental revenue.",
    )

    assert evidence.model_dump() == {
        "type": "AB_TEST",
        "source": "Experiment EXP-001",
        "description": "Random assignment measured incremental revenue.",
    }


@pytest.mark.parametrize("invalid_value", ["", "   ", "\t", " \n"])
def test_causal_evidence_rejects_empty_or_whitespace_source(invalid_value):
    with pytest.raises(ValidationError):
        CausalEvidence(
            type=CausalEvidenceType.CONTROLLED_EXPERIMENT,
            source=invalid_value,
            description="A valid evidence description.",
        )


@pytest.mark.parametrize("invalid_value", ["", "   ", "\t", " \n"])
def test_causal_evidence_rejects_empty_or_whitespace_description(invalid_value):
    with pytest.raises(ValidationError):
        CausalEvidence(
            type=CausalEvidenceType.CONTROLLED_EXPERIMENT,
            source="Experiment EXP-001",
            description=invalid_value,
        )


def test_causality_evaluation_causal_evidence_defaults_to_empty_list():
    evaluation = CausalityEvaluation(**_evaluation_values())

    assert evaluation.causal_evidence == []
    assert evaluation.model_dump(by_alias=True)["causalEvidence"] == []


def test_causality_result_evaluations_default_is_empty():
    assert CausalityResult().evaluations == []


@pytest.mark.parametrize(
    "identifier",
    ["sourceInsightId", "targetInsightId", "relationshipId"],
)
def test_causality_evaluation_requires_identifiers(identifier):
    values = _evaluation_values()
    del values[identifier]

    with pytest.raises(ValidationError):
        CausalityEvaluation(**values)


@pytest.mark.parametrize(
    ("identifier", "invalid_value"),
    [
        ("sourceInsightId", ""),
        ("targetInsightId", ""),
        ("relationshipId", ""),
        ("sourceInsightId", "   "),
        ("targetInsightId", "\t"),
        ("relationshipId", " \n"),
    ],
)
def test_causality_evaluation_rejects_empty_or_whitespace_identifiers(
    identifier,
    invalid_value,
):
    values = _evaluation_values()
    values[identifier] = invalid_value

    with pytest.raises(ValidationError):
        CausalityEvaluation(**values)
