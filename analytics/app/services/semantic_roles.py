from typing import Any

import pandas as pd

from app.config.metadata_loader import load_dataset_metadata


def detect_semantic_roles(
    dataframe: pd.DataFrame,
) -> dict[str, list[dict[str, Any]]]:
    metadata = load_dataset_metadata()
    column_metadata = metadata.get("columns", {})

    metrics = []
    dimensions = []
    temporal = []

    for column in dataframe.columns:
        role = detect_column_role(
            column_name=str(column),
            series=dataframe[column],
            column_metadata=column_metadata,
        )

        item = {
            "name": str(column),
            "role": role,
            "source": (
                "METADATA"
                if column in column_metadata
                else "INFERRED"
            ),
            "hasMetadata": column in column_metadata,
        }

        if role == "METRIC":
            metrics.append(item)

        elif role == "TEMPORAL":
            temporal.append(item)

        else:
            dimensions.append(item)

    return {
        "metrics": metrics,
        "dimensions": dimensions,
        "temporal": temporal,
    }


def detect_column_role(
    column_name: str,
    series: pd.Series,
    column_metadata: dict[str, Any],
) -> str:
    metadata = column_metadata.get(column_name)

    if metadata is not None:
        metadata_role = metadata.get("role")

        if metadata_role in {
            "METRIC",
            "DIMENSION",
            "TEMPORAL",
        }:
            return metadata_role

    return _infer_column_role(
        column_name=column_name,
        series=series,
    )


def _infer_column_role(
    column_name: str,
    series: pd.Series,
) -> str:
    normalized_name = column_name.strip().casefold()

    if pd.api.types.is_datetime64_any_dtype(series):
        return "TEMPORAL"

    if normalized_name in {
        "date",
        "datetime",
        "timestamp",
        "time",
    }:
        return "TEMPORAL"

    if _looks_like_identifier(
        column_name=column_name,
        series=series,
    ):
        return "DIMENSION"

    if pd.api.types.is_numeric_dtype(series):
        return "METRIC"

    return "DIMENSION"


def _looks_like_identifier(
    column_name: str,
    series: pd.Series,
) -> bool:
    normalized_name = (
        column_name
        .replace("_", "")
        .replace("-", "")
        .strip()
        .casefold()
    )

    identifier_name = (
        normalized_name == "id"
        or normalized_name.endswith("id")
    )

    if not identifier_name:
        return False

    non_null = series.dropna()

    if non_null.empty:
        return True

    uniqueness_ratio = (
        non_null.nunique(dropna=True)
        / len(non_null)
    )

    return uniqueness_ratio >= 0.90

def find_missing_metric_definitions(
    semantic_roles: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    findings = []

    for metric in semantic_roles["metrics"]:
        if metric["hasMetadata"]:
            continue

        findings.append(
            {
                "code": "METRIC_DEFINITION_MISSING",
                "severity": "WARNING",
                "column": metric["name"],
                "message": (
                    f"Metric semantic definition is missing for "
                    f"{metric['name']}."
                ),
            }
        )

    return findings