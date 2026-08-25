from app.models.causality import CausalityResult
from app.models.context_summary import KnownUnknownContextResult
from app.models.insight import Insight
from app.models.missing_context import MissingContextResult
from app.models.relationship import Relationship
from app.services.causality_guard import evaluate_relationship_causality
from app.services.context_summary import build_known_unknown_summary
from app.services.missing_context import evaluate_missing_context


def analyze_causality_and_context(
    insights: list[Insight],
    relationships: list[Relationship],
    metadata: dict,
    config: dict | None = None,
) -> tuple[
    CausalityResult,
    MissingContextResult,
    KnownUnknownContextResult,
]:
    causality_evaluations = []
    for relationship in relationships:
        evaluation = evaluate_relationship_causality(
            relationship,
            insights,
        )
        if evaluation is not None:
            causality_evaluations.append(evaluation)

    missing_context_evaluations = [
        evaluate_missing_context(insight, metadata, config=config)
        for insight in insights
    ]

    summaries = [
        build_known_unknown_summary(
            insight,
            causality_evaluations,
            missing_context_evaluation,
        )
        for insight, missing_context_evaluation in zip(
            insights,
            missing_context_evaluations,
        )
    ]

    return (
        CausalityResult(evaluations=causality_evaluations),
        MissingContextResult(evaluations=missing_context_evaluations),
        KnownUnknownContextResult(summaries=summaries),
    )
