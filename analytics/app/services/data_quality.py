from typing import Any
from app.config.metadata_loader import load_dataset_metadata

import pandas as pd


def calculate_data_quality(
    dataframe: pd.DataFrame,
    integrity: dict[str, Any],
) -> dict[str, Any]:
    completeness = _calculate_completeness(dataframe)
    validity = _calculate_validity(dataframe, integrity)
    consistency = _calculate_consistency(dataframe, integrity)
    uniqueness = _calculate_uniqueness(dataframe)

    score = round(
        (
            completeness
            + validity
            + consistency
            + uniqueness
        )
        / 4,
        2,
    )

    return {
        "score": score,
        "completeness": completeness,
        "validity": validity,
        "consistency": consistency,
        "uniqueness": uniqueness,
        "basis": "PREPARED_DATA",
    }


def _calculate_completeness(
    dataframe: pd.DataFrame,
) -> float:
    metadata = load_dataset_metadata()
    column_metadata = metadata.get("columns", {})

    required_columns = [
        column
        for column in dataframe.columns
        if not (
            column in column_metadata
            and column_metadata[column].get(
                "nullable",
                True,
            )
        )
    ]

    if not required_columns:
        return 100.0

    total_required_cells = (
        len(dataframe)
        * len(required_columns)
    )

    if total_required_cells == 0:
        return 100.0

    missing_required_cells = int(
        dataframe[required_columns]
        .isna()
        .sum()
        .sum()
    )

    return round(
        (
            1
            - (
                missing_required_cells
                / total_required_cells
            )
        )
        * 100,
        4,
    )


def _calculate_validity(
    dataframe: pd.DataFrame,
    integrity: dict[str, Any],
) -> float:
    row_count = len(dataframe)

    if row_count == 0:
        return 100.0

    validity_codes = {
        "VALUE_BELOW_MINIMUM",
        "VALUE_ABOVE_MAXIMUM",
    }

    invalid_rows = sum(
        int(finding.get("affectedRowCount", 0))
        for finding in integrity["findings"]
        if finding["code"] in validity_codes
    )

    invalid_ratio = min(
        invalid_rows / row_count,
        1.0,
    )

    return round(
        (1 - invalid_ratio) * 100,
        4,
    )


def _calculate_consistency(
    dataframe: pd.DataFrame,
    integrity: dict[str, Any],
) -> float:
    row_count = len(dataframe)

    if row_count == 0:
        return 100.0

    consistency_codes = {
        "RETURNS_NOT_GREATER_THAN_QUANTITY",
        "PRODUCT_CATEGORY_INCONSISTENCY",
    }

    inconsistent_rows = sum(
        int(finding.get("affectedRowCount", 0))
        for finding in integrity["findings"]
        if finding["code"] in consistency_codes
    )

    inconsistency_ratio = min(
        inconsistent_rows / row_count,
        1.0,
    )

    return round(
        (1 - inconsistency_ratio) * 100,
        4,
    )


def _calculate_uniqueness(
    dataframe: pd.DataFrame,
) -> float:
    row_count = len(dataframe)

    if row_count == 0:
        return 100.0

    duplicate_rows = int(
        dataframe.duplicated().sum()
    )

    return round(
        (
            1
            - (duplicate_rows / row_count)
        )
        * 100,
        4,
    )