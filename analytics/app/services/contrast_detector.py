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


def detect_top_bottom_contrast(
    dataframe: pd.DataFrame,
    *,
    analysis_id: str,
    file_name: str,
    metric: str,
    dimension: str,
    aggregation: str,
    previous_period: str,
    current_period: str,
) -> Insight | None:
    aggregation = aggregation.upper()

    if aggregation not in {"SUM", "AVG"}:
        return None

    if "Date" not in dataframe.columns:
        return None

    if metric not in dataframe.columns:
        return None

    if dimension not in dataframe.columns:
        return None

    segments = sorted(
        dataframe[dimension]
        .dropna()
        .astype(str)
        .unique()
    )

    if len(segments) < 2:
        return None

    segment_changes = []

    for segment in segments:
        segment_data = dataframe.loc[
            dataframe[dimension] == segment
        ]

        previous_value = _aggregate_month(
            segment_data,
            metric=metric,
            aggregation=aggregation,
            period=previous_period,
        )
        current_value = _aggregate_month(
            segment_data,
            metric=metric,
            aggregation=aggregation,
            period=current_period,
        )

        if previous_value is None or current_value is None:
            continue

        if previous_value == 0:
            continue

        change_percent = (
            (current_value - previous_value)
            / previous_value
        ) * 100

        segment_changes.append(
            {
                "segment": segment,
                "previousValue": previous_value,
                "currentValue": current_value,
                "changePercent": change_percent,
            }
        )

    if len(segment_changes) < 2:
        return None

    subject = sorted(
        segment_changes,
        key=lambda item: (
            -item["changePercent"],
            item["segment"],
        ),
    )[0]
    comparison = sorted(
        segment_changes,
        key=lambda item: (
            item["changePercent"],
            item["segment"],
        ),
    )[0]

    difference_percentage_points = (
        subject["changePercent"]
        - comparison["changePercent"]
    )

    config = load_insight_config()

    minimum_gap = float(
        config["contrast"]["minimumPercentagePointGap"]
    )

    if abs(difference_percentage_points) < minimum_gap:
        return None

    direction = (
        InsightDirection.UP
        if subject["changePercent"] > 0
        else InsightDirection.DOWN
        if subject["changePercent"] < 0
        else InsightDirection.STABLE
    )

    subject_change = round(
        subject["changePercent"],
        6,
    )
    comparison_change = round(
        comparison["changePercent"],
        6,
    )
    rounded_difference = round(
        difference_percentage_points,
        6,
    )
    comparison_result = "OUTPERFORMS"

    return Insight(
        id=(
            f"CONTRAST-{metric}-{dimension}-"
            f"{subject['segment']}-{comparison['segment']}-"
            f"{previous_period}-{current_period}"
        ),
        analysisId=analysis_id,
        type=InsightType.CONTRAST,
        metric=metric,
        dimension=dimension,
        segment=subject["segment"],
        periodGranularity=PeriodGranularity.MONTH,
        period={
            "previous": previous_period,
            "current": current_period,
        },
        direction=direction,
        values={
            "subject": subject["segment"],
            "comparison": comparison["segment"],
            "subjectPreviousValue": _round_number(
                subject["previousValue"]
            ),
            "subjectCurrentValue": _round_number(
                subject["currentValue"]
            ),
            "subjectChangePercent": subject_change,
            "comparisonPreviousValue": _round_number(
                comparison["previousValue"]
            ),
            "comparisonCurrentValue": _round_number(
                comparison["currentValue"]
            ),
            "comparisonChangePercent": comparison_change,
            "differencePercentagePoints": rounded_difference,
            "comparisonResult": comparison_result,
        },
        detection={
            "method": "TOP_VS_BOTTOM_PERCENTAGE_CHANGE",
            "aggregation": aggregation,
            "minimumPercentagePointGap": minimum_gap,
        },
        evidence=[
            Evidence(
                code="SUBJECT_PREVIOUS_VALUE",
                label="Subject previous period value",
                value=_round_number(subject["previousValue"]),
            ),
            Evidence(
                code="SUBJECT_CURRENT_VALUE",
                label="Subject current period value",
                value=_round_number(subject["currentValue"]),
            ),
            Evidence(
                code="SUBJECT_CHANGE_PERCENT",
                label="Subject percentage change",
                value=subject_change,
                unit="PERCENT",
            ),
            Evidence(
                code="COMPARISON_PREVIOUS_VALUE",
                label="Comparison previous period value",
                value=_round_number(
                    comparison["previousValue"]
                ),
            ),
            Evidence(
                code="COMPARISON_CURRENT_VALUE",
                label="Comparison current period value",
                value=_round_number(
                    comparison["currentValue"]
                ),
            ),
            Evidence(
                code="COMPARISON_CHANGE_PERCENT",
                label="Comparison percentage change",
                value=comparison_change,
                unit="PERCENT",
            ),
            Evidence(
                code="DIFFERENCE_PERCENTAGE_POINTS",
                label="Percentage-point difference",
                value=rounded_difference,
                unit="PERCENTAGE_POINTS",
            ),
            Evidence(
                code="COMPARISON_RESULT",
                label="Comparison result",
                value=comparison_result,
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

    if aggregation == "SUM":
        return float(period_values.sum())

    return float(period_values.mean())


def _round_number(
    value: Any,
) -> int | float:
    numeric_value = float(value)

    if numeric_value.is_integer():
        return int(numeric_value)

    return round(numeric_value, 6)
