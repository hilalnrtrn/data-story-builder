from app.models.causality import (
    AllowedCausalityConcept,
    CausalClaimGuardResult,
    CausalClaimStatus,
    CausalEvidence,
    CausalityEvaluation,
    CausalityStatus,
    ForbiddenCausalityConcept,
)
from app.models.insight import Insight
from app.models.relationship import Relationship, RelationshipType


_FORBIDDEN_CAUSAL_PHRASES = {
    ForbiddenCausalityConcept.CAUSED: "caused",
    ForbiddenCausalityConcept.LED_TO: "led to",
    ForbiddenCausalityConcept.BECAUSE_OF: "because of",
    ForbiddenCausalityConcept.RESULTED_IN: "resulted in",
    ForbiddenCausalityConcept.DRIVEN_BY: "driven by",
}


def guard_causal_claim(
    claim: str,
    evaluation: CausalityEvaluation,
) -> CausalClaimGuardResult:
    normalized_claim = claim.casefold()
    matched_concepts = [
        concept
        for concept, phrase in _FORBIDDEN_CAUSAL_PHRASES.items()
        if phrase in normalized_claim
    ]

    if evaluation.causality_established or not matched_concepts:
        return CausalClaimGuardResult(
            originalClaim=claim,
            status=CausalClaimStatus.ALLOWED,
        )

    return CausalClaimGuardResult(
        originalClaim=claim,
        status=CausalClaimStatus.BLOCKED,
        blockedConcepts=matched_concepts,
        reasons=[
            "Available evidence does not establish causality for this claim."
        ],
        safeRewrite=(
            f"{evaluation.source_metric} and {evaluation.target_metric} moved "
            "alongside each other during the same period; the available "
            "evidence does not establish causality."
        ),
    )


def evaluate_relationship_causality(
    relationship: Relationship,
    insights: list[Insight],
    causal_evidence: list[CausalEvidence] | None = None,
) -> CausalityEvaluation | None:
    source = next(
        (
            insight
            for insight in insights
            if insight.analysis_id == relationship.analysis_id
            and insight.id == relationship.source_insight_id
        ),
        None,
    )
    target = next(
        (
            insight
            for insight in insights
            if insight.analysis_id == relationship.analysis_id
            and insight.id == relationship.target_insight_id
        ),
        None,
    )

    if source is None or target is None:
        return None

    if relationship.type != RelationshipType.CO_MOVES_WITH:
        return CausalityEvaluation(
            sourceInsightId=source.id,
            targetInsightId=target.id,
            relationshipId=relationship.id,
            sourceMetric=source.metric,
            targetMetric=target.metric,
            associationPresent=False,
            causalityEstablished=False,
            status=CausalityStatus.NOT_APPLICABLE,
            causalEvidence=[],
            reasons=[
                (
                    f"{relationship.type} is not evaluated as causal by "
                    "this causality guard rule."
                )
            ],
        )

    supplied_evidence = list(causal_evidence or [])
    causality_established = bool(supplied_evidence)

    reasons = [
        (
            "CO_MOVES_WITH is association evidence and does not establish "
            "causality on its own."
        )
    ]
    if causality_established:
        reasons.append("Causality is established by explicitly supplied evidence.")

    return CausalityEvaluation(
        sourceInsightId=source.id,
        targetInsightId=target.id,
        relationshipId=relationship.id,
        sourceMetric=source.metric,
        targetMetric=target.metric,
        associationPresent=True,
        causalityEstablished=causality_established,
        status=(
            CausalityStatus.CAUSALITY_ESTABLISHED
            if causality_established
            else CausalityStatus.CAUSALITY_NOT_ESTABLISHED
        ),
        causalEvidence=supplied_evidence,
        allowedConcepts=[
            AllowedCausalityConcept.ASSOCIATED_WITH,
            AllowedCausalityConcept.COINCIDED_WITH,
            AllowedCausalityConcept.MOVED_ALONGSIDE,
        ],
        forbiddenConcepts=(
            []
            if causality_established
            else [
                ForbiddenCausalityConcept.CAUSED,
                ForbiddenCausalityConcept.LED_TO,
                ForbiddenCausalityConcept.BECAUSE_OF,
                ForbiddenCausalityConcept.RESULTED_IN,
                ForbiddenCausalityConcept.DRIVEN_BY,
            ]
        ),
        reasons=reasons,
    )
