import pytest
from pydantic import ValidationError

from app.models.causality import (
    CausalClaimGuardResult,
    CausalClaimStatus,
    CausalEvidence,
    CausalEvidenceType,
    CausalityStatus,
)
from app.models.insight import (
    Insight,
    InsightDirection,
    InsightType,
    PeriodGranularity,
)
from app.models.relationship import Relationship, RelationshipType
from app.services.causality_guard import (
    evaluate_relationship_causality,
    guard_causal_claim,
)


EXPECTED_SAFE_REWRITE = (
    "MarketingSpend and Revenue moved alongside each other during the same "
    "period; the available evidence does not establish causality."
)


def _insight(**overrides) -> Insight:
    values = {
        "id": "CHANGE-MarketingSpend-2025-05-2025-06",
        "analysisId": "ANALYSIS-001",
        "type": InsightType.CHANGE,
        "metric": "MarketingSpend",
        "periodGranularity": PeriodGranularity.MONTH,
        "period": {"previous": "2025-05", "current": "2025-06"},
        "direction": InsightDirection.UP,
    }
    values.update(overrides)
    return Insight(**values)


def _relationship(**overrides) -> Relationship:
    values = {
        "id": "CO_MOVES_WITH-MARKETINGSPEND-REVENUE",
        "analysisId": "ANALYSIS-001",
        "sourceInsightId": "CHANGE-MarketingSpend-2025-05-2025-06",
        "targetInsightId": "CHANGE-Revenue-2025-05-2025-06",
        "type": RelationshipType.CO_MOVES_WITH,
        "strength": 1.0,
        "confidence": 0.9,
    }
    values.update(overrides)
    return Relationship(**values)


def _insights() -> list[Insight]:
    return [
        _insight(),
        _insight(
            id="CHANGE-Revenue-2025-05-2025-06",
            metric="Revenue",
        ),
    ]


def test_co_moves_with_is_association_without_established_causality():
    evaluation = evaluate_relationship_causality(
        _relationship(),
        _insights(),
    )

    assert evaluation is not None
    assert evaluation.status == "CAUSALITY_NOT_ESTABLISHED"
    assert evaluation.association_present is True
    assert evaluation.causality_established is False
    assert evaluation.causal_evidence == []
    assert evaluation.allowed_concepts == [
        "ASSOCIATED_WITH",
        "COINCIDED_WITH",
        "MOVED_ALONGSIDE",
    ]
    assert evaluation.forbidden_concepts == [
        "CAUSED",
        "LED_TO",
        "BECAUSE_OF",
        "RESULTED_IN",
        "DRIVEN_BY",
    ]
    assert evaluation.source_insight_id == (
        "CHANGE-MarketingSpend-2025-05-2025-06"
    )
    assert evaluation.target_insight_id == "CHANGE-Revenue-2025-05-2025-06"
    assert evaluation.source_metric == "MarketingSpend"
    assert evaluation.target_metric == "Revenue"
    assert any(
        "association evidence" in reason
        and "does not establish causality" in reason
        for reason in evaluation.reasons
    )


def test_explicit_causal_evidence_establishes_causality():
    evidence = CausalEvidence(
        type=CausalEvidenceType.AB_TEST,
        source="Experiment EXP-001",
        description="Random assignment measured incremental revenue.",
    )

    evaluation = evaluate_relationship_causality(
        _relationship(),
        _insights(),
        causal_evidence=[evidence],
    )

    assert evaluation is not None
    assert evaluation.status == CausalityStatus.CAUSALITY_ESTABLISHED
    assert evaluation.association_present is True
    assert evaluation.causality_established is True
    assert evaluation.causal_evidence == [evidence]
    assert evaluation.allowed_concepts == [
        "ASSOCIATED_WITH",
        "COINCIDED_WITH",
        "MOVED_ALONGSIDE",
    ]
    assert evaluation.forbidden_concepts == []


@pytest.mark.parametrize(
    "relationship_type",
    [
        RelationshipType.CONTRIBUTES_TO,
        RelationshipType.COUNTER_SIGNAL,
        RelationshipType.RELATED_ANOMALY,
        RelationshipType.DRILLDOWN_OF,
    ],
)
def test_non_association_relationship_is_not_applicable_and_not_causal(
    relationship_type,
):
    evidence = CausalEvidence(
        type=CausalEvidenceType.EXTERNAL_CAUSAL_EVIDENCE,
        source="External study",
        description="Evidence supplied for a separate causal question.",
    )
    relationship = _relationship(type=relationship_type)

    evaluation = evaluate_relationship_causality(
        relationship,
        _insights(),
        causal_evidence=[evidence],
    )

    assert evaluation is not None
    assert evaluation.status == "NOT_APPLICABLE"
    assert evaluation.association_present is False
    assert evaluation.causality_established is False
    assert evaluation.causal_evidence == []
    assert evaluation.allowed_concepts == []
    assert evaluation.forbidden_concepts == []


def test_relationship_types_contain_no_causal_relationship_names():
    causal_relationship_names = {
        "CAUSES",
        "CAUSED_BY",
        "DRIVES",
        "RESULTS_IN",
    }

    assert causal_relationship_names.isdisjoint(
        relationship_type.value for relationship_type in RelationshipType
    )


def test_unresolved_insight_returns_none():
    assert evaluate_relationship_causality(
        _relationship(targetInsightId="MISSING-INSIGHT"),
        _insights(),
    ) is None


def test_relationship_analysis_mismatch_does_not_resolve_other_analysis():
    insights = _insights()
    insights[0] = insights[0].model_copy(
        update={"analysis_id": "ANALYSIS-002"}
    )

    assert evaluate_relationship_causality(
        _relationship(),
        insights,
    ) is None


@pytest.mark.parametrize(
    ("claim", "expected_concept"),
    [
        ("MarketingSpend caused Revenue growth.", "CAUSED"),
        ("MarketingSpend led to Revenue growth.", "LED_TO"),
        ("Revenue increased because of MarketingSpend.", "BECAUSE_OF"),
        ("MarketingSpend resulted in Revenue growth.", "RESULTED_IN"),
        ("Revenue growth was driven by MarketingSpend.", "DRIVEN_BY"),
    ],
)
def test_unsupported_causal_phrase_is_blocked(claim, expected_concept):
    evaluation = evaluate_relationship_causality(_relationship(), _insights())

    assert evaluation is not None
    result = guard_causal_claim(claim, evaluation)

    assert result.status == "BLOCKED"
    assert result.blocked_concepts == [expected_concept]
    assert result.safe_rewrite == EXPECTED_SAFE_REWRITE
    assert any(
        "does not establish causality" in reason for reason in result.reasons
    )


def test_causal_phrase_detection_is_case_insensitive():
    evaluation = evaluate_relationship_causality(_relationship(), _insights())

    assert evaluation is not None
    result = guard_causal_claim(
        "MarketingSpend LED TO Revenue growth.",
        evaluation,
    )

    assert result.status == "BLOCKED"
    assert result.blocked_concepts == ["LED_TO"]


def test_multiple_unsupported_causal_phrases_are_all_blocked():
    evaluation = evaluate_relationship_causality(_relationship(), _insights())

    assert evaluation is not None
    result = guard_causal_claim(
        "MarketingSpend caused growth because of increased reach.",
        evaluation,
    )

    assert result.status == "BLOCKED"
    assert result.blocked_concepts == ["CAUSED", "BECAUSE_OF"]
    assert result.safe_rewrite == EXPECTED_SAFE_REWRITE


def test_non_causal_association_claim_is_allowed():
    evaluation = evaluate_relationship_causality(_relationship(), _insights())

    assert evaluation is not None
    result = guard_causal_claim(
        "MarketingSpend moved alongside Revenue growth.",
        evaluation,
    )

    assert result.status == "ALLOWED"
    assert result.blocked_concepts == []
    assert result.safe_rewrite is None


def test_causal_claim_is_allowed_when_causality_is_established():
    evidence = CausalEvidence(
        type=CausalEvidenceType.AB_TEST,
        source="Experiment EXP-001",
        description="Random assignment measured incremental revenue.",
    )
    evaluation = evaluate_relationship_causality(
        _relationship(),
        _insights(),
        causal_evidence=[evidence],
    )

    assert evaluation is not None
    result = guard_causal_claim(
        "MarketingSpend caused Revenue growth.",
        evaluation,
    )

    assert result.status == "ALLOWED"
    assert result.blocked_concepts == []
    assert result.safe_rewrite is None


def test_safe_rewrite_uses_camel_case_alias_and_has_no_forbidden_phrases():
    evaluation = evaluate_relationship_causality(_relationship(), _insights())

    assert evaluation is not None
    result = guard_causal_claim(
        "MarketingSpend caused Revenue growth.",
        evaluation,
    )

    assert result.model_dump(by_alias=True)["safeRewrite"] == (
        EXPECTED_SAFE_REWRITE
    )
    normalized_rewrite = result.safe_rewrite.casefold()
    assert all(
        phrase not in normalized_rewrite
        for phrase in [
            "caused",
            "led to",
            "because of",
            "resulted in",
            "driven by",
        ]
    )


def test_causal_claim_guard_does_not_mutate_evaluation():
    evaluation = evaluate_relationship_causality(_relationship(), _insights())

    assert evaluation is not None
    evaluation_before = evaluation.model_dump()
    guard_causal_claim("MarketingSpend caused Revenue growth.", evaluation)

    assert evaluation.model_dump() == evaluation_before


@pytest.mark.parametrize("original_claim", ["", "   ", "\t", " \n"])
def test_causal_claim_guard_result_rejects_blank_original_claim(original_claim):
    with pytest.raises(ValidationError):
        CausalClaimGuardResult(
            originalClaim=original_claim,
            status=CausalClaimStatus.ALLOWED,
        )
