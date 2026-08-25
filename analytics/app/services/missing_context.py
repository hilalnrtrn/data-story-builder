from app.config.insight_config_loader import load_insight_config
from app.models.insight import Insight
from app.models.missing_context import (
    MissingContextEvaluation,
    MissingContextItem,
    MissingContextStatus,
)


def evaluate_missing_context(
    insight: Insight,
    metadata: dict,
    config: dict | None = None,
) -> MissingContextEvaluation:
    resolved_config = load_insight_config() if config is None else config
    requirements = (
        resolved_config.get("missingContext", {})
        .get("requirementsByMetric", {})
        .get(insight.metric, [])
    )

    available_fields = set(metadata.get("columns", {}))
    available_fields.update(metadata.get("derivedMetrics", {}))

    missing_context = [
        MissingContextItem(
            field=requirement["field"],
            status=MissingContextStatus.NOT_AVAILABLE,
            isDataQualityError=False,
            reason=requirement["reason"],
        )
        for requirement in requirements
        if requirement["field"] not in available_fields
    ]
    interpretation_limited = bool(missing_context)

    return MissingContextEvaluation(
        insightId=insight.id,
        missingContext=missing_context,
        interpretationLimited=interpretation_limited,
        reasons=(
            ["Interpretation is limited by unavailable context."]
            if interpretation_limited
            else []
        ),
    )
