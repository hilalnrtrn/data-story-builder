from dataclasses import dataclass
from hashlib import sha256
from math import isfinite

from app.models.causality import CausalityEvaluation, CausalityStatus
from app.models.hypothesis import (
    Hypothesis,
    HypothesisEvidenceReference,
    HypothesisMissingContextReference,
    HypothesisStatus,
)
from app.models.insight import Insight
from app.models.insight_integrity import (
    CounterEvidenceItem,
    InsightIntegrityEvaluation,
)
from app.models.missing_context import MissingContextEvaluation
from app.models.relationship import Relationship, RelationshipType


_UNESTABLISHED_ASSOCIATION_STATUSES = {
    CausalityStatus.ASSOCIATION_ONLY,
    CausalityStatus.CAUSALITY_NOT_ESTABLISHED,
}
_TRACKER_VERSION = "day16-v1"
# Stage H replaces this explicitly unscored creation placeholder.
_STAGE_E_UNSCORED_CONFIDENCE = 0.0
_CONFIDENCE_REASON_PREFIXES = (
    "Supporting evidence coverage:",
    "Relationship confidence:",
    "Causality safety signal:",
    "Counter evidence penalty:",
    "Missing context penalty:",
    "Hypothesis confidence:",
)
_ALLOWED_STATUS_TRANSITIONS = {
    (HypothesisStatus.OPEN, HypothesisStatus.SUPPORTED),
    (HypothesisStatus.OPEN, HypothesisStatus.REJECTED),
    (HypothesisStatus.SUPPORTED, HypothesisStatus.CONFIRMED),
    (HypothesisStatus.SUPPORTED, HypothesisStatus.REJECTED),
}


@dataclass(frozen=True)
class HypothesisCandidate:
    relationship_id: str
    source_insight_id: str
    target_insight_id: str


def find_hypothesis_candidates(
    insights: list[Insight],
    relationships: list[Relationship],
    causality_evaluations: list[CausalityEvaluation],
) -> list[HypothesisCandidate]:
    insights_by_key = {
        (insight.analysis_id, insight.id): insight for insight in insights
    }
    eligible_evaluation_keys = {
        (
            evaluation.relationship_id,
            evaluation.source_insight_id,
            evaluation.target_insight_id,
        )
        for evaluation in causality_evaluations
        if evaluation.association_present
        and not evaluation.causality_established
        and evaluation.status in _UNESTABLISHED_ASSOCIATION_STATUSES
    }

    candidates: set[HypothesisCandidate] = set()
    for relationship in relationships:
        if relationship.type != RelationshipType.CO_MOVES_WITH:
            continue
        if relationship.source_insight_id == relationship.target_insight_id:
            continue

        source = insights_by_key.get(
            (relationship.analysis_id, relationship.source_insight_id)
        )
        target = insights_by_key.get(
            (relationship.analysis_id, relationship.target_insight_id)
        )
        if source is None or target is None:
            continue

        evaluation_key = (
            relationship.id,
            relationship.source_insight_id,
            relationship.target_insight_id,
        )
        if evaluation_key not in eligible_evaluation_keys:
            continue

        candidates.add(
            HypothesisCandidate(
                relationship_id=relationship.id,
                source_insight_id=relationship.source_insight_id,
                target_insight_id=relationship.target_insight_id,
            )
        )

    return sorted(
        candidates,
        key=lambda candidate: (
            candidate.relationship_id,
            candidate.source_insight_id,
            candidate.target_insight_id,
        ),
    )


def create_hypothesis_from_candidate(
    candidate: HypothesisCandidate,
    insights: list[Insight],
    relationships: list[Relationship],
    causality_evaluations: list[CausalityEvaluation],
) -> Hypothesis:
    relationship = next(
        (
            item
            for item in relationships
            if item.id == candidate.relationship_id
        ),
        None,
    )
    if relationship is None:
        raise ValueError("Candidate relationship could not be resolved")
    if (
        relationship.source_insight_id != candidate.source_insight_id
        or relationship.target_insight_id != candidate.target_insight_id
    ):
        raise ValueError("Candidate and relationship endpoints do not match")
    if relationship.type != RelationshipType.CO_MOVES_WITH:
        raise ValueError("Candidate relationship must be CO_MOVES_WITH")
    if candidate.source_insight_id == candidate.target_insight_id:
        raise ValueError("Candidate source and target insights must differ")

    source = _resolve_insight(
        insights,
        relationship.analysis_id,
        candidate.source_insight_id,
        "source",
    )
    target = _resolve_insight(
        insights,
        relationship.analysis_id,
        candidate.target_insight_id,
        "target",
    )

    evaluation = next(
        (
            item
            for item in causality_evaluations
            if item.relationship_id == candidate.relationship_id
            and item.source_insight_id == candidate.source_insight_id
            and item.target_insight_id == candidate.target_insight_id
        ),
        None,
    )
    if evaluation is None:
        raise ValueError("Matching causality evaluation could not be resolved")
    if evaluation.causality_established:
        raise ValueError("Established causality is not a hypothesis candidate")
    if not evaluation.association_present:
        raise ValueError("Candidate must have association evidence")
    if evaluation.status not in _UNESTABLISHED_ASSOCIATION_STATUSES:
        raise ValueError("Candidate must have unestablished causality")

    statement = (
        f"The observed change in {source.metric} may be associated with "
        f"the observed change in {target.metric}."
    )

    return Hypothesis(
        id=_build_hypothesis_id(
            relationship.analysis_id,
            candidate,
        ),
        analysisId=relationship.analysis_id,
        statement=statement,
        status=HypothesisStatus.OPEN,
        confidence=_STAGE_E_UNSCORED_CONFIDENCE,
        sourceInsightIds=[source.id, target.id],
        sourceRelationshipIds=[relationship.id],
        supportingEvidence=[],
        counterEvidence=[],
        missingContext=[],
        causalityStatus=evaluation.status,
        reasons=[
            "CO_MOVES_WITH association detected.",
            "Causality is not established.",
        ],
        trackerVersion=_TRACKER_VERSION,
    )


def attach_supporting_evidence(
    hypothesis: Hypothesis,
    insights: list[Insight],
) -> Hypothesis:
    references: list[HypothesisEvidenceReference] = []
    seen: set[tuple[str, str]] = set()

    for insight_id in hypothesis.source_insight_ids:
        matching_id = [item for item in insights if item.id == insight_id]
        if not matching_id:
            raise ValueError(
                f"Hypothesis source insight '{insight_id}' could not be resolved"
            )

        insight = next(
            (
                item
                for item in matching_id
                if item.analysis_id == hypothesis.analysis_id
            ),
            None,
        )
        if insight is None:
            raise ValueError(
                f"Hypothesis source insight '{insight_id}' belongs to "
                "a different analysis"
            )

        for evidence in insight.evidence:
            key = (insight.id, evidence.code)
            if key in seen:
                continue

            references.append(
                HypothesisEvidenceReference(
                    insightId=insight.id,
                    evidenceCode=evidence.code,
                )
            )
            seen.add(key)

    return hypothesis.model_copy(
        update={"supporting_evidence": references},
        deep=True,
    )


def attach_counter_evidence_and_missing_context(
    hypothesis: Hypothesis,
    integrity_evaluations: list[InsightIntegrityEvaluation],
    missing_context_evaluations: list[MissingContextEvaluation],
) -> Hypothesis:
    counter_evidence: list[CounterEvidenceItem] = []
    counter_keys: set[tuple[object, ...]] = set()
    missing_context: list[HypothesisMissingContextReference] = []
    missing_context_keys: set[tuple[str, str]] = set()

    for source_insight_id in hypothesis.source_insight_ids:
        for evaluation in integrity_evaluations:
            if evaluation.insight_id != source_insight_id:
                continue

            for item in evaluation.counter_evidence:
                key = (
                    item.insight_id,
                    item.relationship_id,
                    item.metric,
                    item.direction,
                    tuple(item.reasons),
                )
                if key in counter_keys:
                    continue

                counter_evidence.append(item.model_copy(deep=True))
                counter_keys.add(key)

        for evaluation in missing_context_evaluations:
            if evaluation.insight_id != source_insight_id:
                continue

            for item in evaluation.missing_context:
                key = (source_insight_id, item.field)
                if key in missing_context_keys:
                    continue

                missing_context.append(
                    HypothesisMissingContextReference(
                        sourceInsightId=source_insight_id,
                        item=item.model_copy(deep=True),
                    )
                )
                missing_context_keys.add(key)

    return hypothesis.model_copy(
        update={
            "counter_evidence": counter_evidence,
            "missing_context": missing_context,
        },
        deep=True,
    )


def calculate_hypothesis_confidence(
    hypothesis: Hypothesis,
    relationships: list[Relationship],
    causality_evaluations: list[CausalityEvaluation],
) -> Hypothesis:
    source_insight_ids = hypothesis.source_insight_ids
    if not source_insight_ids:
        raise ValueError("Hypothesis must reference at least one source insight")
    if len(hypothesis.source_relationship_ids) != 1:
        raise ValueError(
            "Hypothesis must reference exactly one source relationship"
        )

    relationship_id = hypothesis.source_relationship_ids[0]
    relationship = next(
        (item for item in relationships if item.id == relationship_id),
        None,
    )
    if relationship is None:
        raise ValueError("Hypothesis source relationship could not be resolved")
    if relationship.type != RelationshipType.CO_MOVES_WITH:
        raise ValueError("Hypothesis relationship must be CO_MOVES_WITH")
    if relationship.analysis_id != hypothesis.analysis_id:
        raise ValueError("Hypothesis and relationship analyses do not match")
    if (
        relationship.source_insight_id not in source_insight_ids
        or relationship.target_insight_id not in source_insight_ids
    ):
        raise ValueError(
            "Relationship does not correspond to hypothesis source insights"
        )
    if (
        not isfinite(relationship.confidence)
        or not 0.0 <= relationship.confidence <= 1.0
    ):
        raise ValueError("Relationship confidence must be finite and in [0, 1]")

    evaluation = next(
        (
            item
            for item in causality_evaluations
            if item.relationship_id == relationship.id
            and item.source_insight_id == relationship.source_insight_id
            and item.target_insight_id == relationship.target_insight_id
        ),
        None,
    )
    if evaluation is None:
        raise ValueError("Matching causality evaluation could not be resolved")
    if not evaluation.association_present:
        raise ValueError("Causality evaluation must contain association evidence")
    if evaluation.causality_established:
        raise ValueError("Established causality cannot be scored as a hypothesis")
    if evaluation.status not in _UNESTABLISHED_ASSOCIATION_STATUSES:
        raise ValueError("Causality evaluation is not an unestablished association")

    covered_insight_ids = {
        reference.insight_id
        for reference in hypothesis.supporting_evidence
        if reference.insight_id in source_insight_ids
    }
    covered_count = len(covered_insight_ids)
    source_count = len(source_insight_ids)
    support_coverage = covered_count / source_count
    causality_safety = 1.0
    counter_penalty = 0.15 if hypothesis.counter_evidence else 0.0
    missing_context_penalty = min(
        0.20,
        0.05 * len(hypothesis.missing_context),
    )
    score = (
        0.50 * support_coverage
        + 0.30 * relationship.confidence
        + 0.20 * causality_safety
        - counter_penalty
        - missing_context_penalty
    )
    confidence = min(1.0, max(0.0, score))

    existing_reasons = [
        reason
        for reason in hypothesis.reasons
        if not reason.startswith(_CONFIDENCE_REASON_PREFIXES)
    ]
    scoring_reasons = [
        f"Supporting evidence coverage: {covered_count}/{source_count}.",
        f"Relationship confidence: {relationship.confidence:g}.",
        f"Causality safety signal: {causality_safety:g}.",
        f"Counter evidence penalty: {counter_penalty:.2f}.",
        f"Missing context penalty: {missing_context_penalty:.2f}.",
        f"Hypothesis confidence: {confidence:g}.",
    ]

    return hypothesis.model_copy(
        update={
            "confidence": confidence,
            "reasons": [*existing_reasons, *scoring_reasons],
        },
        deep=True,
    )


def is_hypothesis_transition_allowed(
    current_status: HypothesisStatus,
    target_status: HypothesisStatus,
) -> bool:
    return (current_status, target_status) in _ALLOWED_STATUS_TRANSITIONS


def transition_hypothesis_status(
    hypothesis: Hypothesis,
    target_status: HypothesisStatus,
) -> Hypothesis:
    current_status = HypothesisStatus(hypothesis.status)
    resolved_target = HypothesisStatus(target_status)
    if not is_hypothesis_transition_allowed(
        current_status,
        resolved_target,
    ):
        raise ValueError(
            "Hypothesis status transition from "
            f"{current_status.value} to {resolved_target.value} is not allowed"
        )

    reason = (
        f"Hypothesis status changed from {current_status.value} "
        f"to {resolved_target.value}."
    )
    return hypothesis.model_copy(
        update={
            "status": resolved_target.value,
            "reasons": [*hypothesis.reasons, reason],
        },
        deep=True,
    )


def track_hypotheses(
    insights: list[Insight],
    relationships: list[Relationship],
    integrity_evaluations: list[InsightIntegrityEvaluation],
    causality_evaluations: list[CausalityEvaluation],
    missing_context_evaluations: list[MissingContextEvaluation],
) -> list[Hypothesis]:
    candidates = find_hypothesis_candidates(
        insights,
        relationships,
        causality_evaluations,
    )
    hypotheses: list[Hypothesis] = []

    for candidate in candidates:
        hypothesis = create_hypothesis_from_candidate(
            candidate,
            insights,
            relationships,
            causality_evaluations,
        )
        hypothesis = attach_supporting_evidence(hypothesis, insights)
        hypothesis = attach_counter_evidence_and_missing_context(
            hypothesis,
            integrity_evaluations,
            missing_context_evaluations,
        )
        hypothesis = calculate_hypothesis_confidence(
            hypothesis,
            relationships,
            causality_evaluations,
        )
        hypotheses.append(hypothesis)

    return hypotheses


def _resolve_insight(
    insights: list[Insight],
    analysis_id: str,
    insight_id: str,
    endpoint: str,
) -> Insight:
    insight = next(
        (
            item
            for item in insights
            if item.analysis_id == analysis_id and item.id == insight_id
        ),
        None,
    )
    if insight is None:
        raise ValueError(f"Candidate {endpoint} insight could not be resolved")

    return insight


def _build_hypothesis_id(
    analysis_id: str,
    candidate: HypothesisCandidate,
) -> str:
    identity = "|".join(
        (
            analysis_id,
            candidate.relationship_id,
            candidate.source_insight_id,
            candidate.target_insight_id,
        )
    )
    digest = sha256(identity.encode("utf-8")).hexdigest()
    return f"HYPOTHESIS-{digest}"
