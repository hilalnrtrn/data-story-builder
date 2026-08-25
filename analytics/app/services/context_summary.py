from app.models.causality import CausalityEvaluation, CausalityStatus
from app.models.context_summary import (
    ContextStatement,
    KnownUnknownContextSummary,
)
from app.models.insight import Insight
from app.models.missing_context import MissingContextEvaluation


def build_known_unknown_summary(
    insight: Insight,
    causality_evaluations: list[CausalityEvaluation],
    missing_context_evaluation: MissingContextEvaluation | None = None,
) -> KnownUnknownContextSummary:
    known = [
        ContextStatement(
            code="INSIGHT_OBSERVED",
            statement=(
                f"The insight for {insight.metric} is an observed "
                "analytical finding."
            ),
        )
    ]
    unknown: list[ContextStatement] = []
    known_keys = {(known[0].code, known[0].statement)}
    unknown_keys: set[tuple[str, str]] = set()

    for evaluation in causality_evaluations:
        if insight.id not in {
            evaluation.source_insight_id,
            evaluation.target_insight_id,
        }:
            continue

        if evaluation.association_present:
            association = ContextStatement(
                code="ASSOCIATION_PRESENT",
                statement=(
                    "Association evidence is present between "
                    f"{evaluation.source_metric} and "
                    f"{evaluation.target_metric}."
                ),
            )
            association_key = (association.code, association.statement)
            if association_key not in known_keys:
                known.append(association)
                known_keys.add(association_key)

        if (
            not evaluation.causality_established
            and evaluation.status
            == CausalityStatus.CAUSALITY_NOT_ESTABLISHED
        ):
            causality_unknown = ContextStatement(
                code="CAUSALITY_NOT_ESTABLISHED",
                statement=(
                    f"Causality between {evaluation.source_metric} and "
                    f"{evaluation.target_metric} is not established."
                ),
            )
            causality_key = (
                causality_unknown.code,
                causality_unknown.statement,
            )
            if causality_key not in unknown_keys:
                unknown.append(causality_unknown)
                unknown_keys.add(causality_key)

    matching_missing_context = (
        missing_context_evaluation
        if missing_context_evaluation is not None
        and missing_context_evaluation.insight_id == insight.id
        else None
    )
    if matching_missing_context is not None:
        for item in matching_missing_context.missing_context:
            unknown.append(
                ContextStatement(
                    code=f"{item.field.upper()}_UNAVAILABLE",
                    statement=(
                        f"{item.field} is unavailable as contextual "
                        "information."
                    ),
                )
            )

    interpretation_limited = bool(unknown) or (
        matching_missing_context is not None
        and matching_missing_context.interpretation_limited
    )

    return KnownUnknownContextSummary(
        insightId=insight.id,
        known=known,
        unknown=unknown,
        interpretationLimited=interpretation_limited,
    )
