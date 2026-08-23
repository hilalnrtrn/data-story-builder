from typing import Any

import pandas as pd

from app.config.insight_config_loader import load_insight_config
from app.models.insight import (
    Evidence,
    Insight,
    InsightDirection,
    InsightSource,
    InsightType,
    PeriodGranularity,
)


def calculate_percentage_change(
    previous_value: float,
    current_value: float,
) -> float | None:
    if previous_value == 0:
        return None

    return (
        (current_value - previous_value)
        / previous_value
    ) * 100


def detect_change(
    dataframe: pd.DataFrame,
    *,
    analysis_id: str,
    file_name: str,
    metric: str,
    aggregation: str,
    previous_period: str,
    current_period: str,
) -> Insight | None:
    config = load_insight_config()

    minimum_change = float(
        config["change"]["minimumPercentageChange"]
    )

    previous_value = _aggregate_month(
        dataframe,
        metric=metric,
        aggregation=aggregation,
        period=previous_period,
    )

    current_value = _aggregate_month(
        dataframe,
        metric=metric,
        aggregation=aggregation,
        period=current_period,
    )

    if previous_value is None or current_value is None:
        return None

    percentage_change = calculate_percentage_change(
        previous_value,
        current_value,
    )

    if percentage_change is None:
        return None

    if abs(percentage_change) < minimum_change:
        return None

    absolute_change = current_value - previous_value

    direction = (
        InsightDirection.UP
        if percentage_change > 0
        else InsightDirection.DOWN
        if percentage_change < 0
        else InsightDirection.STABLE
    )

    return Insight(
        id=f"CHANGE-{metric}-{previous_period}-{current_period}",
        analysisId=analysis_id,
        type=InsightType.CHANGE,
        metric=metric,
        periodGranularity=PeriodGranularity.MONTH,
        period={
            "previous": previous_period,
            "current": current_period,
        },
        direction=direction,
        values={
            "previous": _round_number(previous_value),
            "current": _round_number(current_value),
            "absoluteChange": _round_number(absolute_change),
            "percentageChange": round(
                percentage_change,
                6,
            ),
        },
        detection={
            "method": "PERIOD_COMPARISON",
            "aggregation": aggregation,
            "minimumPercentageChange": minimum_change,
        },
        evidence=[
            Evidence(
                code="PREVIOUS_PERIOD_VALUE",
                label="Previous period value",
                value=_round_number(previous_value),
            ),
            Evidence(
                code="CURRENT_PERIOD_VALUE",
                label="Current period value",
                value=_round_number(current_value),
            ),
            Evidence(
                code="ABSOLUTE_CHANGE",
                label="Absolute change",
                value=_round_number(absolute_change),
            ),
            Evidence(
                code="PERCENTAGE_CHANGE",
                label="Percentage change",
                value=round(percentage_change, 6),
                unit="PERCENT",
            ),
        ],
        source=InsightSource(
            fileName=file_name,
            rowCount=len(dataframe),
        ),
    )


def _aggregate_month(
    dataframe: pd.DataFrame,
    *,
    metric: str,
    aggregation: str,
    period: str,
) -> float | None:
    if "Date" not in dataframe.columns:
        return None

    if metric not in dataframe.columns:
        return None

    period_mask = (
        dataframe["Date"]
        .dt.to_period("M")
        .astype(str)
        == period
    )

    period_values = dataframe.loc[
        period_mask,
        metric,
    ].dropna()

    if period_values.empty:
        return None

    aggregation = aggregation.upper()

    if aggregation == "SUM":
        return float(period_values.sum())

    if aggregation == "AVG":
        return float(period_values.mean())

    return None


def _round_number(
    value: float,
) -> int | float:
    if float(value).is_integer():
        return int(value)

    return round(float(value), 6)