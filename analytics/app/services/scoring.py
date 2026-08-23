import math
from typing import Any

from app.config.insight_config_loader import load_insight_config
from app.models.insight import Insight


_CONFIDENCE_COMPONENTS = (
    "dataQuality",
    "sampleSufficiency",
    "signalStrength",
    "consistency",
)

_SUPPORTED_INSIGHT_TYPES = {
    "CHANGE",
    "TREND",
    "ANOMALY",
    "CONTRIBUTION",
    "CONTRAST",
}


def apply_confidence_score(
    insight: Insight,
    *,
    data_quality: dict[str, Any],
) -> Insight:
    config = load_insight_config()

    try:
        confidence_weights = config["confidence"]["weights"]
    except (KeyError, TypeError) as error:
        raise ValueError(
            "Confidence weights are missing"
        ) from error

    weights = _validate_confidence_weights(
        confidence_weights
    )
    insight_type = _get_insight_type(insight)

    if insight_type not in _SUPPORTED_INSIGHT_TYPES:
        raise ValueError(
            f"Unsupported insight type: {insight_type}"
        )

    data_quality_score = _require_number(
        data_quality,
        "score",
        "data quality score",
    )
    data_quality_component = _clamp(
        data_quality_score / 100.0
    )

    sample_sufficiency = _sample_sufficiency(
        insight,
        insight_type=insight_type,
        config=config,
    )
    signal_strength = _signal_strength(
        insight,
        insight_type=insight_type,
    )
    consistency = _consistency(
        insight,
        insight_type=insight_type,
    )

    breakdown = {
        "dataQuality": round(data_quality_component, 6),
        "sampleSufficiency": round(
            _clamp(sample_sufficiency),
            6,
        ),
        "signalStrength": round(
            _clamp(signal_strength),
            6,
        ),
        "consistency": round(
            _clamp(consistency),
            6,
        ),
    }

    confidence = sum(
        breakdown[component] * weights[component]
        for component in _CONFIDENCE_COMPONENTS
    )

    insight.confidence = round(
        _clamp(confidence),
        6,
    )
    insight.confidence_breakdown = breakdown

    return insight


def apply_importance_score(
    insight: Insight,
) -> Insight:
    insight_type = _get_insight_type(insight)

    if insight_type not in _SUPPORTED_INSIGHT_TYPES:
        raise ValueError(
            f"Unsupported insight type: {insight_type}"
        )

    if insight_type == "CHANGE":
        percentage_change = _require_number(
            insight.values,
            "percentageChange",
            "change percentage",
        )
        minimum_change = _require_positive_number(
            insight.detection,
            "minimumPercentageChange",
            "minimum percentage change",
        )
        magnitude = _clamp(
            abs(percentage_change) / (4 * minimum_change)
        )
        breakdown = {
            "magnitude": round(magnitude, 6),
        }
        importance = breakdown["magnitude"]

    elif insight_type == "TREND":
        start_value = _require_number(
            insight.values,
            "startValue",
            "trend start value",
        )
        end_value = _require_number(
            insight.values,
            "endValue",
            "trend end value",
        )
        persistence = _clamp(
            _require_number(
                insight.detection,
                "persistenceRatio",
                "trend persistence ratio",
            )
        )

        if start_value == 0:
            raise ValueError(
                "Trend start value must not be zero"
            )

        config = load_insight_config()

        try:
            change_config = config["change"]
        except (KeyError, TypeError) as error:
            raise ValueError(
                "Change configuration is missing"
            ) from error

        minimum_change = _require_positive_number(
            change_config,
            "minimumPercentageChange",
            "minimum percentage change",
        )
        trend_magnitude_percent = (
            abs(end_value - start_value)
            / abs(start_value)
        ) * 100
        magnitude = _clamp(
            trend_magnitude_percent
            / (4 * minimum_change)
        )
        breakdown = {
            "magnitude": round(magnitude, 6),
            "persistence": round(persistence, 6),
        }
        importance = (
            0.60 * breakdown["magnitude"]
            + 0.40 * breakdown["persistence"]
        )

    elif insight_type == "ANOMALY":
        observed = _require_number(
            insight.values,
            "observed",
            "anomaly observed value",
        )
        lower_bound = _require_number(
            insight.values,
            "lowerBound",
            "anomaly lower bound",
        )
        upper_bound = _require_number(
            insight.values,
            "upperBound",
            "anomaly upper bound",
        )
        iqr = _require_positive_number(
            insight.values,
            "iqr",
            "anomaly IQR",
        )

        if insight.direction == "HIGH":
            excess = observed - upper_bound
        elif insight.direction == "LOW":
            excess = lower_bound - observed
        else:
            raise ValueError(
                "Anomaly direction must be HIGH or LOW"
            )

        deviation_strength = _clamp(excess / iqr)
        breakdown = {
            "deviationStrength": round(
                deviation_strength,
                6,
            ),
        }
        importance = breakdown["deviationStrength"]

    elif insight_type == "CONTRIBUTION":
        contribution_share = _require_number(
            insight.values,
            "contributionShare",
            "contribution share",
        )
        contribution_strength = _clamp(
            abs(contribution_share)
        )
        breakdown = {
            "contributionStrength": round(
                contribution_strength,
                6,
            ),
        }
        importance = breakdown["contributionStrength"]

    else:
        difference = _require_number(
            insight.values,
            "differencePercentagePoints",
            "contrast percentage-point difference",
        )
        minimum_gap = _require_positive_number(
            insight.detection,
            "minimumPercentagePointGap",
            "minimum percentage-point gap",
        )
        gap_strength = _clamp(
            abs(difference) / (4 * minimum_gap)
        )
        breakdown = {
            "gapStrength": round(gap_strength, 6),
        }
        importance = breakdown["gapStrength"]

    insight.importance = round(
        _clamp(importance),
        6,
    )
    insight.importance_breakdown = breakdown

    return insight


def _validate_confidence_weights(
    weights: Any,
) -> dict[str, float]:
    if not isinstance(weights, dict):
        raise ValueError("Confidence weights must be a mapping")

    validated = {}

    for component in _CONFIDENCE_COMPONENTS:
        value = _require_number(
            weights,
            component,
            f"confidence weight {component}",
        )

        if value < 0 or value > 1:
            raise ValueError(
                f"Invalid confidence weight: {component}"
            )

        validated[component] = value

    if not math.isclose(
        sum(validated.values()),
        1.0,
        rel_tol=0.0,
        abs_tol=1e-9,
    ):
        raise ValueError("Confidence weights must sum to 1.0")

    return validated


def _sample_sufficiency(
    insight: Insight,
    *,
    insight_type: str,
    config: dict[str, Any],
) -> float:
    if insight_type != "TREND":
        return 1.0

    period_count = _require_number(
        insight.values,
        "periodCount",
        "trend period count",
    )

    try:
        minimum_periods = float(
            config["trend"]["minimumPeriods"]
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(
            "Invalid trend minimum periods"
        ) from error

    if not math.isfinite(minimum_periods) or minimum_periods <= 0:
        raise ValueError("Invalid trend minimum periods")

    return _clamp(period_count / minimum_periods)


def _signal_strength(
    insight: Insight,
    *,
    insight_type: str,
) -> float:
    if insight_type == "CHANGE":
        percentage_change = _require_number(
            insight.values,
            "percentageChange",
            "change percentage",
        )
        minimum_change = _require_positive_number(
            insight.detection,
            "minimumPercentageChange",
            "minimum percentage change",
        )

        return min(
            abs(percentage_change) / (2 * minimum_change),
            1.0,
        )

    if insight_type == "TREND":
        return _clamp(
            _require_number(
                insight.detection,
                "persistenceRatio",
                "trend persistence ratio",
            )
        )

    if insight_type == "ANOMALY":
        observed = _require_number(
            insight.values,
            "observed",
            "anomaly observed value",
        )
        lower_bound = _require_number(
            insight.values,
            "lowerBound",
            "anomaly lower bound",
        )
        upper_bound = _require_number(
            insight.values,
            "upperBound",
            "anomaly upper bound",
        )
        iqr = _require_positive_number(
            insight.values,
            "iqr",
            "anomaly IQR",
        )

        if insight.direction == "HIGH":
            excess = observed - upper_bound
        elif insight.direction == "LOW":
            excess = lower_bound - observed
        else:
            raise ValueError(
                "Anomaly direction must be HIGH or LOW"
            )

        return _clamp(excess / iqr)

    if insight_type == "CONTRIBUTION":
        contribution_share = _require_number(
            insight.values,
            "contributionShare",
            "contribution share",
        )

        return _clamp(abs(contribution_share))

    difference = _require_number(
        insight.values,
        "differencePercentagePoints",
        "contrast percentage-point difference",
    )
    minimum_gap = _require_positive_number(
        insight.detection,
        "minimumPercentagePointGap",
        "minimum percentage-point gap",
    )

    return min(
        abs(difference) / (2 * minimum_gap),
        1.0,
    )


def _consistency(
    insight: Insight,
    *,
    insight_type: str,
) -> float:
    if insight_type != "TREND":
        return 1.0

    return _clamp(
        _require_number(
            insight.detection,
            "persistenceRatio",
            "trend persistence ratio",
        )
    )


def _get_insight_type(insight: Insight) -> str:
    insight_type = insight.type

    if hasattr(insight_type, "value"):
        return str(insight_type.value)

    return str(insight_type)


def _require_positive_number(
    values: dict[str, Any],
    key: str,
    label: str,
) -> float:
    value = _require_number(values, key, label)

    if value <= 0:
        raise ValueError(f"{label} must be greater than zero")

    return value


def _require_number(
    values: dict[str, Any],
    key: str,
    label: str,
) -> float:
    if key not in values:
        raise ValueError(f"Missing {label}")

    value = values[key]

    if isinstance(value, bool) or not isinstance(
        value,
        (int, float),
    ):
        raise ValueError(f"Invalid {label}")

    numeric_value = float(value)

    if not math.isfinite(numeric_value):
        raise ValueError(f"Invalid {label}")

    return numeric_value


def _clamp(value: float) -> float:
    return max(0.0, min(value, 1.0))
