from typing import Any

import pandas as pd


def profile_dataset(dataframe: pd.DataFrame) -> dict[str, Any]:
    column_profiles = [
        profile_column(dataframe[column])
        for column in dataframe.columns
    ]

    return {
        "rowCount": len(dataframe),
        "columnCount": len(dataframe.columns),
        "columns": column_profiles,
    }


def profile_column(series: pd.Series) -> dict[str, Any]:
    row_count = len(series)
    missing_count = int(series.isna().sum())
    non_null_count = row_count - missing_count

    missing_percentage = (
        (missing_count / row_count) * 100
        if row_count > 0
        else 0.0
    )

    data_type = _detect_data_type(series)

    profile = {
        "name": str(series.name),
        "dataType": data_type,
        "count": non_null_count,
        "missingCount": missing_count,
        "missingPercentage": round(missing_percentage, 4),
        "uniqueCount": int(series.nunique(dropna=True)),
    }

    if data_type == "numeric":
        profile.update(_profile_numeric(series))

    elif data_type == "categorical":
        profile.update(_profile_categorical(series))

    elif data_type == "datetime":
        profile.update(_profile_datetime(series))

    return profile


def _profile_numeric(series: pd.Series) -> dict[str, Any]:
    non_null = series.dropna()

    if non_null.empty:
        return {
            "min": None,
            "max": None,
            "mean": None,
            "median": None,
            "std": None,
            "q1": None,
            "q3": None,
        }

    return {
        "min": _to_python_number(non_null.min()),
        "max": _to_python_number(non_null.max()),
        "mean": _round_number(non_null.mean()),
        "median": _round_number(non_null.median()),
        "std": _round_number(non_null.std()),
        "q1": _round_number(non_null.quantile(0.25)),
        "q3": _round_number(non_null.quantile(0.75)),
    }

def _profile_categorical(series: pd.Series) -> dict[str, Any]:
    non_null = series.dropna()

    if non_null.empty:
        return {
            "topValues": [],
        }

    value_counts = non_null.value_counts().head(5)

    top_values = [
        {
            "value": str(value),
            "count": int(count),
        }
        for value, count in value_counts.items()
    ]

    return {
        "topValues": top_values,
    }

def _profile_datetime(series: pd.Series) -> dict[str, Any]:
    non_null = series.dropna().sort_values()

    if non_null.empty:
        return {
            "minDate": None,
            "maxDate": None,
            "uniquePeriodCount": 0,
            "frequencyEstimate": "UNKNOWN",
        }

    return {
        "minDate": non_null.min().date().isoformat(),
        "maxDate": non_null.max().date().isoformat(),
        "uniquePeriodCount": int(non_null.nunique()),
        "frequencyEstimate": _estimate_frequency(non_null),
    }


def _estimate_frequency(series: pd.Series) -> str:
    unique_dates = (
        pd.Series(series.drop_duplicates())
        .sort_values()
        .reset_index(drop=True)
    )

    if len(unique_dates) < 2:
        return "UNKNOWN"

    day_differences = (
        unique_dates.diff()
        .dropna()
        .dt.total_seconds()
        .div(86400)
    )

    if day_differences.empty:
        return "UNKNOWN"

    if (day_differences == 1).all():
        return "DAILY"

    if day_differences.between(6, 8).all():
        return "WEEKLY"

    if day_differences.between(28, 31).all():
        return "MONTHLY"

    return "IRREGULAR"

def _detect_data_type(series: pd.Series) -> str:
    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"

    if pd.api.types.is_numeric_dtype(series):
        return "numeric"

    if pd.api.types.is_bool_dtype(series):
        return "boolean"

    return "categorical"


def _round_number(value: Any) -> float | None:
    if pd.isna(value):
        return None

    return round(float(value), 4)


def _to_python_number(value: Any) -> int | float | None:
    if pd.isna(value):
        return None

    if isinstance(value, int):
        return value

    numeric_value = float(value)

    if numeric_value.is_integer():
        return int(numeric_value)

    return round(numeric_value, 4)