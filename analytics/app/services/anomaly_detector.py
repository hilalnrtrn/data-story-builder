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


def detect_anomaly(
    dataframe: pd.DataFrame,
    *,
    analysis_id: str,
    file_name: str,
    metric: str,
    dimension: str,
    segment: str,
    aggregation: str,
    period: str,
    history_start: str,
    history_end: str,
) -> Insight | None:
    config = load_insight_config()

    anomaly_config = config["anomaly"]

    minimum_periods = int(
        anomaly_config["minimumPeriods"]
    )

    iqr_multiplier = float(
        anomaly_config["iqrMultiplier"]
    )

    series = _build_monthly_series(
        dataframe,
        metric=metric,
        dimension=dimension,
        segment=segment,
        aggregation=aggregation,
        period_start=history_start,
        period_end=history_end,
    )

    if len(series) < minimum_periods:
        return None

    target_rows = series.loc[
        series["period"] == period
    ]

    if target_rows.empty:
        return None

    observed_value = float(
        target_rows.iloc[0]["value"]
    )

    baseline = series.loc[
        series["period"] != period,
        "value",
    ].astype(float)

    if len(baseline) < minimum_periods - 1:
        return None

    q1 = float(baseline.quantile(0.25))
    q3 = float(baseline.quantile(0.75))
    iqr = q3 - q1

    if iqr == 0:
        return None

    lower_bound = q1 - (
        iqr_multiplier * iqr
    )

    upper_bound = q3 + (
        iqr_multiplier * iqr
    )

    if observed_value > upper_bound:
        direction = InsightDirection.HIGH

    elif observed_value < lower_bound:
        direction = InsightDirection.LOW

    else:
        return None

    return Insight(
        id=(
            f"ANOMALY-{metric}-{dimension}-"
            f"{segment}-{period}"
        ),
        analysisId=analysis_id,
        type=InsightType.ANOMALY,
        metric=metric,
        dimension=dimension,
        segment=segment,
        periodGranularity=PeriodGranularity.MONTH,
        period={
            "current": period,
        },
        direction=direction,
        values={
            "observed": _round_number(
                observed_value
            ),
            "q1": _round_number(q1),
            "q3": _round_number(q3),
            "iqr": _round_number(iqr),
            "lowerBound": _round_number(
                lower_bound
            ),
            "upperBound": _round_number(
                upper_bound
            ),
        },
        detection={
            "method": "IQR",
            "iqrMultiplier": iqr_multiplier,
            "minimumPeriods": minimum_periods,
        },
        evidence=[
            Evidence(
                code="OBSERVED_VALUE",
                label="Observed period value",
                value=_round_number(
                    observed_value
                ),
            ),
            Evidence(
                code="IQR_Q1",
                label="Historical first quartile",
                value=_round_number(q1),
            ),
            Evidence(
                code="IQR_Q3",
                label="Historical third quartile",
                value=_round_number(q3),
            ),
            Evidence(
                code="IQR_LOWER_BOUND",
                label="Lower anomaly bound",
                value=_round_number(
                    lower_bound
                ),
            ),
            Evidence(
                code="IQR_UPPER_BOUND",
                label="Upper anomaly bound",
                value=_round_number(
                    upper_bound
                ),
            ),
        ],
        source=InsightSource(
            fileName=file_name,
            rowCount=len(dataframe),
        ),
    )


def _build_monthly_series(
    dataframe: pd.DataFrame,
    *,
    metric: str,
    dimension: str,
    segment: str,
    aggregation: str,
    period_start: str,
    period_end: str,
) -> pd.DataFrame:
    if "Date" not in dataframe.columns:
        return pd.DataFrame(
            columns=["period", "value"]
        )

    if metric not in dataframe.columns:
        return pd.DataFrame(
            columns=["period", "value"]
        )

    if dimension not in dataframe.columns:
        return pd.DataFrame(
            columns=["period", "value"]
        )

    segment_data = dataframe.loc[
        dataframe[dimension] == segment
    ].copy()

    if segment_data.empty:
        return pd.DataFrame(
            columns=["period", "value"]
        )

    segment_data["period"] = (
        segment_data["Date"]
        .dt.to_period("M")
        .astype(str)
    )

    segment_data = segment_data.loc[
        segment_data["period"].between(
            period_start,
            period_end,
        )
    ]

    aggregation = aggregation.upper()

    if aggregation == "SUM":
        monthly = (
            segment_data
            .groupby(
                "period",
                as_index=False,
            )[metric]
            .sum()
        )

    elif aggregation == "AVG":
        monthly = (
            segment_data
            .groupby(
                "period",
                as_index=False,
            )[metric]
            .mean()
        )

    else:
        return pd.DataFrame(
            columns=["period", "value"]
        )

    return (
        monthly.rename(
            columns={
                metric: "value",
            }
        )
        .sort_values("period")
        .reset_index(drop=True)
    )


def _round_number(
    value: Any,
) -> int | float:
    numeric_value = float(value)

    if numeric_value.is_integer():
        return int(numeric_value)

    return round(numeric_value, 6)