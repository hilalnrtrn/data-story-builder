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


def detect_contribution(
    dataframe: pd.DataFrame,
    *,
    analysis_id: str,
    file_name: str,
    metric: str,
    dimension: str,
    segment: str,
    aggregation: str,
    previous_period: str,
    current_period: str,
) -> Insight | None:
    if aggregation.upper() != "SUM":
        return None

    if "Date" not in dataframe.columns:
        return None

    if metric not in dataframe.columns:
        return None

    if dimension not in dataframe.columns:
        return None

    if pd.isna(segment):
        return None

    config = load_insight_config()

    minimum_share = float(
        config["contribution"][
            "minimumAbsoluteContributionShare"
        ]
    )

    dimension_data = dataframe.loc[
        dataframe[dimension].notna()
    ]

    total_previous_value = _aggregate_month(
        dataframe,
        metric=metric,
        period=previous_period,
    )
    total_current_value = _aggregate_month(
        dataframe,
        metric=metric,
        period=current_period,
    )

    if (
        total_previous_value is None
        or total_current_value is None
    ):
        return None

    segment_data = dimension_data.loc[
        dimension_data[dimension] == segment
    ]

    segment_previous_value = (
        _aggregate_month(
            segment_data,
            metric=metric,
            period=previous_period,
        )
        or 0.0
    )
    segment_current_value = (
        _aggregate_month(
            segment_data,
            metric=metric,
            period=current_period,
        )
        or 0.0
    )

    total_absolute_change = (
        total_current_value - total_previous_value
    )

    if total_absolute_change == 0:
        return None

    segment_absolute_change = (
        segment_current_value - segment_previous_value
    )
    contribution_share = (
        segment_absolute_change / total_absolute_change
    )

    if abs(contribution_share) < minimum_share:
        return None

    direction = (
        InsightDirection.UP
        if segment_absolute_change > 0
        else InsightDirection.DOWN
        if segment_absolute_change < 0
        else InsightDirection.STABLE
    )

    contributor_role = _get_contributor_role(
        total_absolute_change=total_absolute_change,
        segment_absolute_change=segment_absolute_change,
    )

    rounded_share = round(contribution_share, 6)

    return Insight(
        id=(
            f"CONTRIBUTION-{metric}-{dimension}-"
            f"{segment}-{previous_period}-{current_period}"
        ),
        analysisId=analysis_id,
        type=InsightType.CONTRIBUTION,
        metric=metric,
        dimension=dimension,
        segment=segment,
        periodGranularity=PeriodGranularity.MONTH,
        period={
            "previous": previous_period,
            "current": current_period,
        },
        direction=direction,
        values={
            "segmentPreviousValue": _round_number(
                segment_previous_value
            ),
            "segmentCurrentValue": _round_number(
                segment_current_value
            ),
            "segmentAbsoluteChange": _round_number(
                segment_absolute_change
            ),
            "totalPreviousValue": _round_number(
                total_previous_value
            ),
            "totalCurrentValue": _round_number(
                total_current_value
            ),
            "totalAbsoluteChange": _round_number(
                total_absolute_change
            ),
            "contributionShare": rounded_share,
            "contributorRole": contributor_role,
        },
        detection={
            "method": "SEGMENT_CHANGE_OVER_TOTAL_CHANGE",
            "aggregation": "SUM",
            "minimumAbsoluteContributionShare": minimum_share,
        },
        evidence=[
            Evidence(
                code="SEGMENT_PREVIOUS_VALUE",
                label="Segment previous period value",
                value=_round_number(segment_previous_value),
            ),
            Evidence(
                code="SEGMENT_CURRENT_VALUE",
                label="Segment current period value",
                value=_round_number(segment_current_value),
            ),
            Evidence(
                code="SEGMENT_ABSOLUTE_CHANGE",
                label="Segment absolute change",
                value=_round_number(segment_absolute_change),
            ),
            Evidence(
                code="TOTAL_ABSOLUTE_CHANGE",
                label="Total absolute change",
                value=_round_number(total_absolute_change),
            ),
            Evidence(
                code="CONTRIBUTION_SHARE",
                label="Contribution share",
                value=rounded_share,
                unit="RATIO",
            ),
            Evidence(
                code="CONTRIBUTOR_ROLE",
                label="Contributor role",
                value=contributor_role,
            ),
        ],
        source=InsightSource(
            fileName=file_name,
            rowCount=len(dataframe),
        ),
    )


def detect_contributions(
    dataframe: pd.DataFrame,
    *,
    analysis_id: str,
    file_name: str,
    metric: str,
    dimension: str,
    aggregation: str,
    previous_period: str,
    current_period: str,
) -> list[Insight]:
    if dimension not in dataframe.columns:
        return []

    segments = sorted(
        dataframe[dimension]
        .dropna()
        .astype(str)
        .unique()
    )

    insights = []

    for segment in segments:
        insight = detect_contribution(
            dataframe,
            analysis_id=analysis_id,
            file_name=file_name,
            metric=metric,
            dimension=dimension,
            segment=segment,
            aggregation=aggregation,
            previous_period=previous_period,
            current_period=current_period,
        )

        if insight is not None:
            insights.append(insight)

    _promote_primary_contributor(insights)

    return sorted(
        insights,
        key=lambda insight: (
            -abs(insight.values["contributionShare"]),
            str(insight.segment),
        ),
    )


def _promote_primary_contributor(
    insights: list[Insight],
) -> None:
    if not insights:
        return

    total_absolute_change = insights[0].values[
        "totalAbsoluteChange"
    ]

    if total_absolute_change > 0:
        candidate_role = "POSITIVE_CONTRIBUTOR"
        primary_role = "PRIMARY_POSITIVE_CONTRIBUTOR"
    else:
        candidate_role = "NEGATIVE_CONTRIBUTOR"
        primary_role = "PRIMARY_NEGATIVE_CONTRIBUTOR"

    candidates = [
        insight
        for insight in insights
        if insight.values["contributorRole"] == candidate_role
    ]

    if not candidates:
        return

    primary = sorted(
        candidates,
        key=lambda insight: (
            -insight.values["contributionShare"],
            str(insight.segment),
        ),
    )[0]

    primary.values["contributorRole"] = primary_role

    for evidence in primary.evidence:
        if evidence.code == "CONTRIBUTOR_ROLE":
            evidence.value = primary_role
            break


def _aggregate_month(
    dataframe: pd.DataFrame,
    *,
    metric: str,
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

    return float(period_values.sum())


def _get_contributor_role(
    *,
    total_absolute_change: float,
    segment_absolute_change: float,
) -> str:
    if total_absolute_change > 0:
        if segment_absolute_change > 0:
            return "POSITIVE_CONTRIBUTOR"

        return "NEGATIVE_OFFSET"

    if segment_absolute_change < 0:
        return "NEGATIVE_CONTRIBUTOR"

    return "POSITIVE_OFFSET"


def _round_number(
    value: Any,
) -> int | float:
    numeric_value = float(value)

    if numeric_value.is_integer():
        return int(numeric_value)

    return round(numeric_value, 6)
