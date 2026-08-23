from typing import Any

import numpy as np
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


def detect_trend(
    dataframe: pd.DataFrame,
    *,
    analysis_id: str,
    file_name: str,
    metric: str,
    dimension: str,
    segment: str,
    aggregation: str,
    period_start: str,
    period_end: str,
) -> Insight | None:
    config = load_insight_config()

    minimum_periods = int(
        config["trend"]["minimumPeriods"]
    )

    minimum_persistence = float(
        config["trend"]["minimumPersistenceThreshold"]
    )

    high_persistence = float(
        config["trend"]["highPersistenceThreshold"]
    )

    series = _build_monthly_series(
        dataframe,
        metric=metric,
        dimension=dimension,
        segment=segment,
        aggregation=aggregation,
        period_start=period_start,
        period_end=period_end,
    )

    if len(series) < minimum_periods:
        return None

    values = series["value"].to_numpy(dtype=float)

    slope = calculate_slope(values)

    if slope == 0:
        return None

    direction = (
        InsightDirection.UP
        if slope > 0
        else InsightDirection.DOWN
    )

    persistence_ratio = calculate_persistence(
        values,
        direction=direction,
    )

    if persistence_ratio < minimum_persistence:
        return None

    monotonic_movement = is_monotonic(
        values,
        direction=direction,
    )

    persistence_level = (
        "HIGH"
        if persistence_ratio >= high_persistence
        else "MEDIUM"
    )

    return Insight(
        id=(
            f"TREND-{metric}-{dimension}-"
            f"{segment}-{period_start}-{period_end}"
        ),
        analysisId=analysis_id,
        type=InsightType.TREND,
        metric=metric,
        dimension=dimension,
        segment=segment,
        periodGranularity=PeriodGranularity.MONTH,
        period={
            "start": period_start,
            "end": period_end,
        },
        direction=direction,
        values={
            "periodCount": len(series),
            "startValue": _round_number(values[0]),
            "endValue": _round_number(values[-1]),
        },
        detection={
            "method": "LINEAR_SLOPE_AND_DIRECTION_CONSISTENCY",
            "slope": round(float(slope), 6),
            "persistenceRatio": round(
                persistence_ratio,
                6,
            ),
            "persistenceLevel": persistence_level,
            "monotonicMovement": monotonic_movement,
            "minimumPersistenceThreshold": minimum_persistence,
        },
        evidence=[
            Evidence(
                code="TREND_SLOPE",
                label="Linear trend slope",
                value=round(float(slope), 6),
            ),
            Evidence(
                code="PERSISTENCE_RATIO",
                label="Directional persistence ratio",
                value=round(
                    persistence_ratio,
                    6,
                ),
            ),
            Evidence(
                code="MONOTONIC_MOVEMENT",
                label="Monotonic movement",
                value=monotonic_movement,
            ),
            Evidence(
                code="PERIOD_COUNT",
                label="Periods analyzed",
                value=len(series),
            ),
        ],
        source=InsightSource(
            fileName=file_name,
            rowCount=len(dataframe),
        ),
    )


def calculate_slope(
    values: np.ndarray,
) -> float:
    if len(values) < 2:
        return 0.0

    x_values = np.arange(len(values), dtype=float)

    slope, _ = np.polyfit(
        x_values,
        values,
        1,
    )

    return float(slope)


def calculate_persistence(
    values: np.ndarray,
    *,
    direction: InsightDirection,
) -> float:
    if len(values) < 2:
        return 0.0

    differences = np.diff(values)

    if direction == InsightDirection.UP:
        matching_movements = differences > 0

    elif direction == InsightDirection.DOWN:
        matching_movements = differences < 0

    else:
        return 0.0

    return float(
        matching_movements.sum()
        / len(differences)
    )


def is_monotonic(
    values: np.ndarray,
    *,
    direction: InsightDirection,
) -> bool:
    if len(values) < 2:
        return False

    differences = np.diff(values)

    if direction == InsightDirection.UP:
        return bool((differences > 0).all())

    if direction == InsightDirection.DOWN:
        return bool((differences < 0).all())

    return False


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

    monthly = monthly.rename(
        columns={
            metric: "value",
        }
    )

    return monthly.sort_values(
        "period"
    ).reset_index(drop=True)


def _round_number(
    value: Any,
) -> int | float:
    numeric_value = float(value)

    if numeric_value.is_integer():
        return int(numeric_value)

    return round(numeric_value, 6)