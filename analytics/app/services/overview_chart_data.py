from typing import Any

import pandas as pd

from app.config.metadata_loader import load_dataset_metadata


def build_overview_chart_data(
    dataframe: pd.DataFrame,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    dataset_metadata = metadata or load_dataset_metadata()
    return {
        "revenueOverTime": _build_revenue_over_time(
            dataframe,
            dataset_metadata,
        ),
        "revenueByRegion": _build_revenue_by_region(
            dataframe,
            dataset_metadata,
        ),
    }


def _build_revenue_over_time(
    dataframe: pd.DataFrame,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    base = {
        "status": "UNAVAILABLE",
        "metric": "Revenue",
        "aggregation": "SUM",
        "granularity": "MONTH",
        "periodStart": None,
        "periodEnd": None,
        "points": [],
        "unavailableReason": None,
    }

    if "Revenue" not in dataframe.columns:
        return {
            **base,
            "unavailableReason": "Revenue column is unavailable.",
        }

    if "Date" not in dataframe.columns:
        return {
            **base,
            "unavailableReason": "Date column is unavailable.",
        }

    revenue_metadata = metadata.get("columns", {}).get("Revenue", {})
    if str(revenue_metadata.get("aggregation", "")).upper() != "SUM":
        return {
            **base,
            "unavailableReason": "Revenue SUM aggregation is unavailable.",
        }

    if not pd.api.types.is_datetime64_any_dtype(dataframe["Date"]):
        return {
            **base,
            "unavailableReason": "Prepared Date values are not datetime values.",
        }

    if not pd.api.types.is_numeric_dtype(dataframe["Revenue"]):
        return {
            **base,
            "unavailableReason": "Prepared Revenue values are not numeric.",
        }

    valid_rows = dataframe.loc[
        dataframe["Date"].notna() & dataframe["Revenue"].notna(),
        ["Date", "Revenue"],
    ].copy()

    if valid_rows.empty:
        return {
            **base,
            "unavailableReason": "No prepared Revenue values have a valid Date.",
        }

    valid_rows["period"] = (
        valid_rows["Date"].dt.to_period("M").astype(str)
    )
    monthly = (
        valid_rows.groupby("period", as_index=False, sort=True)["Revenue"]
        .sum()
        .sort_values("period")
    )
    points = [
        {
            "period": str(row.period),
            "value": _to_number(row.Revenue),
        }
        for row in monthly.itertuples(index=False)
    ]

    return {
        **base,
        "status": "READY",
        "periodStart": points[0]["period"],
        "periodEnd": points[-1]["period"],
        "points": points,
        "unavailableReason": None,
    }


def _build_revenue_by_region(
    dataframe: pd.DataFrame,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    base = {
        "status": "UNAVAILABLE",
        "metric": "Revenue",
        "dimension": "Region",
        "aggregation": "SUM",
        "periodStart": None,
        "periodEnd": None,
        "points": [],
        "unavailableReason": None,
    }

    if "Revenue" not in dataframe.columns:
        return {
            **base,
            "unavailableReason": "Revenue column is unavailable.",
        }

    if "Region" not in dataframe.columns:
        return {
            **base,
            "unavailableReason": "Region column is unavailable.",
        }

    revenue_metadata = metadata.get("columns", {}).get("Revenue", {})
    if str(revenue_metadata.get("aggregation", "")).upper() != "SUM":
        return {
            **base,
            "unavailableReason": "Revenue SUM aggregation is unavailable.",
        }

    if not pd.api.types.is_numeric_dtype(dataframe["Revenue"]):
        return {
            **base,
            "unavailableReason": "Prepared Revenue values are not numeric.",
        }

    valid_rows = dataframe.loc[
        dataframe["Region"].notna() & dataframe["Revenue"].notna(),
        ["Region", "Revenue"],
    ].copy()
    valid_rows["Region"] = valid_rows["Region"].astype(str).str.strip()
    valid_rows = valid_rows.loc[valid_rows["Region"] != ""]

    if valid_rows.empty:
        return {
            **base,
            "unavailableReason": "No prepared Revenue values have a valid Region.",
        }

    regional = (
        valid_rows.groupby("Region", as_index=False, sort=False)["Revenue"]
        .sum()
        .sort_values(
            ["Revenue", "Region"],
            ascending=[False, True],
            kind="stable",
        )
    )
    points = [
        {
            "segment": str(row.Region),
            "value": _to_number(row.Revenue),
        }
        for row in regional.itertuples(index=False)
    ]
    period_start, period_end = _prepared_date_range(dataframe)

    return {
        **base,
        "status": "READY",
        "periodStart": period_start,
        "periodEnd": period_end,
        "points": points,
        "unavailableReason": None,
    }


def _prepared_date_range(
    dataframe: pd.DataFrame,
) -> tuple[str | None, str | None]:
    if (
        "Date" not in dataframe.columns
        or not pd.api.types.is_datetime64_any_dtype(dataframe["Date"])
    ):
        return None, None

    valid_dates = dataframe["Date"].dropna()
    if valid_dates.empty:
        return None, None

    return (
        valid_dates.min().date().isoformat(),
        valid_dates.max().date().isoformat(),
    )


def _to_number(value: Any) -> int | float:
    numeric_value = float(value)
    if numeric_value.is_integer():
        return int(numeric_value)
    return round(numeric_value, 6)
