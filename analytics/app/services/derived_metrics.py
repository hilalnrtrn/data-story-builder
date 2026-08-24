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


def calculate_return_rate(
    dataframe: pd.DataFrame,
    *,
    period: str,
) -> float | None:
    required_columns = {"Date", "Returns", "Quantity"}
    if not required_columns.issubset(dataframe.columns):
        return None

    period_mask = (
        dataframe["Date"]
        .dt.to_period("M")
        .astype(str)
        == period
    )
    period_rows = dataframe.loc[period_mask]

    if period_rows.empty:
        return None

    total_quantity = float(period_rows["Quantity"].sum())
    if total_quantity == 0:
        return None

    total_returns = float(period_rows["Returns"].sum())

    return total_returns / total_quantity


def build_return_rate_change_insight(
    dataframe: pd.DataFrame,
    *,
    analysis_id: str,
    file_name: str,
    previous_period: str,
    current_period: str,
) -> Insight | None:
    config = load_insight_config()
    minimum_change = float(
        config["change"]["minimumPercentageChange"]
    )

    previous_value = calculate_return_rate(
        dataframe,
        period=previous_period,
    )
    current_value = calculate_return_rate(
        dataframe,
        period=current_period,
    )

    if previous_value is None or current_value is None:
        return None

    if previous_value == 0:
        return None

    absolute_change = current_value - previous_value
    percentage_change = (
        absolute_change / previous_value
    ) * 100

    if abs(percentage_change) < minimum_change:
        return None

    percentage_point_change = absolute_change * 100

    direction = (
        InsightDirection.UP
        if percentage_change > 0
        else InsightDirection.DOWN
        if percentage_change < 0
        else InsightDirection.STABLE
    )

    previous_value = round(previous_value, 6)
    current_value = round(current_value, 6)
    absolute_change = round(absolute_change, 6)
    percentage_change = round(percentage_change, 6)
    percentage_point_change = round(percentage_point_change, 6)

    return Insight(
        id=(
            f"CHANGE-ReturnRate-{previous_period}-{current_period}"
        ),
        analysisId=analysis_id,
        type=InsightType.CHANGE,
        metric="ReturnRate",
        periodGranularity=PeriodGranularity.MONTH,
        period={
            "previous": previous_period,
            "current": current_period,
        },
        direction=direction,
        values={
            "previous": previous_value,
            "current": current_value,
            "absoluteChange": absolute_change,
            "percentageChange": percentage_change,
            "percentagePointChange": percentage_point_change,
        },
        detection={
            "method": "DERIVED_RATIO_OF_SUMS_PERIOD_COMPARISON",
            "formula": "SUM(Returns) / SUM(Quantity)",
            "numerator": "Returns",
            "denominator": "Quantity",
            "aggregation": "RATIO_OF_SUMS",
            "minimumPercentageChange": minimum_change,
        },
        evidence=[
            Evidence(
                code="PREVIOUS_RETURN_RATE",
                label="Previous ReturnRate",
                value=previous_value,
                unit="RATIO",
            ),
            Evidence(
                code="CURRENT_RETURN_RATE",
                label="Current ReturnRate",
                value=current_value,
                unit="RATIO",
            ),
            Evidence(
                code="PERCENTAGE_CHANGE",
                label="Relative percentage change",
                value=percentage_change,
                unit="PERCENT",
            ),
            Evidence(
                code="PERCENTAGE_POINT_CHANGE",
                label="Percentage-point change",
                value=percentage_point_change,
                unit="PERCENTAGE_POINTS",
            ),
        ],
        source=InsightSource(
            fileName=file_name,
            rowCount=len(dataframe),
        ),
    )
