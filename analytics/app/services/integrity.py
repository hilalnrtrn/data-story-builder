from typing import Any

import pandas as pd

from app.config.metadata_loader import load_dataset_metadata
from app.services.semantic_roles import (
    detect_semantic_roles,
    find_missing_metric_definitions,
)


def validate_integrity(
    dataframe: pd.DataFrame,
) -> dict[str, Any]:
    metadata = load_dataset_metadata()

    findings = []

    findings.extend(
        _validate_column_rules(
            dataframe=dataframe,
            metadata=metadata,
        )
    )

    findings.extend(
        _validate_cross_column_rules(
            dataframe=dataframe,
            metadata=metadata,
        )
    )

    findings.extend(
        _validate_product_category_mapping(
            dataframe=dataframe,
            metadata=metadata,
        )
    )

    semantic_roles = detect_semantic_roles(dataframe)

    findings.extend(
        find_missing_metric_definitions(
            semantic_roles
        )
    )

    return _build_integrity_summary(findings)


def _validate_column_rules(
    dataframe: pd.DataFrame,
    metadata: dict[str, Any],
) -> list[dict[str, Any]]:
    findings = []

    column_metadata = metadata.get("columns", {})

    for column_name, rules in column_metadata.items():
        if column_name not in dataframe.columns:
            continue

        series = dataframe[column_name]

        findings.extend(
            _validate_numeric_bounds(
                column_name=column_name,
                series=series,
                rules=rules,
            )
        )

    return findings


def _validate_numeric_bounds(
    column_name: str,
    series: pd.Series,
    rules: dict[str, Any],
) -> list[dict[str, Any]]:
    findings = []

    if not pd.api.types.is_numeric_dtype(series):
        return findings

    if "min" in rules:
        invalid_min = series.notna() & (
            series < rules["min"]
        )

        invalid_count = int(invalid_min.sum())

        if invalid_count > 0:
            findings.append(
                {
                    "code": "VALUE_BELOW_MINIMUM",
                    "severity": "ERROR",
                    "column": column_name,
                    "affectedRowCount": invalid_count,
                    "rule": (
                        f"{column_name} >= "
                        f"{rules['min']}"
                    ),
                }
            )

    if "max" in rules:
        invalid_max = series.notna() & (
            series > rules["max"]
        )

        invalid_count = int(invalid_max.sum())

        if invalid_count > 0:
            findings.append(
                {
                    "code": "VALUE_ABOVE_MAXIMUM",
                    "severity": "ERROR",
                    "column": column_name,
                    "affectedRowCount": invalid_count,
                    "rule": (
                        f"{column_name} <= "
                        f"{rules['max']}"
                    ),
                }
            )

    return findings

def _validate_cross_column_rules(
    dataframe: pd.DataFrame,
    metadata: dict[str, Any],
) -> list[dict[str, Any]]:
    findings = []

    rules = metadata.get("crossColumnRules", [])

    for rule in rules:
        left_column = rule.get("leftColumn")
        right_column = rule.get("rightColumn")
        operator = rule.get("operator")

        if (
            left_column not in dataframe.columns
            or right_column not in dataframe.columns
        ):
            continue

        if operator == "<=":
            finding = _validate_less_than_or_equal_rule(
                dataframe=dataframe,
                left_column=left_column,
                right_column=right_column,
                rule=rule,
            )

            if finding is not None:
                findings.append(finding)

    return findings


def _validate_less_than_or_equal_rule(
    dataframe: pd.DataFrame,
    left_column: str,
    right_column: str,
    rule: dict[str, Any],
) -> dict[str, Any] | None:
    left = dataframe[left_column]
    right = dataframe[right_column]

    comparable = left.notna() & right.notna()

    invalid = comparable & (left > right)

    affected_row_count = int(invalid.sum())

    if affected_row_count == 0:
        return None

    return {
        "code": rule["code"],
        "severity": "ERROR",
        "columns": [
            left_column,
            right_column,
        ],
        "affectedRowCount": affected_row_count,
        "rule": (
            f"{left_column} <= "
            f"{right_column}"
        ),
    }


def _build_integrity_summary(
    findings: list[dict[str, Any]],
) -> dict[str, Any]:
    error_count = sum(
        1
        for finding in findings
        if finding["severity"] == "ERROR"
    )

    warning_count = sum(
        1
        for finding in findings
        if finding["severity"] == "WARNING"
    )

    affected_row_count = sum(
        int(finding.get("affectedRowCount", 0))
        for finding in findings
    )

    if error_count > 0:
        status = "FAILED"
    elif warning_count > 0:
        status = "WARNING"
    else:
        status = "PASS"

    return {
        "status": status,
        "findingCount": len(findings),
        "errorCount": error_count,
        "warningCount": warning_count,
        "affectedRowCount": affected_row_count,
        "findings": findings,
    }

def _validate_product_category_mapping(
    dataframe: pd.DataFrame,
    metadata: dict[str, Any],
) -> list[dict[str, Any]]:
    if (
        "Product" not in dataframe.columns
        or "Category" not in dataframe.columns
    ):
        return []

    mapping = (
        metadata
        .get("relationships", {})
        .get("productCategoryMapping", {})
    )

    if not mapping:
        return []

    product = dataframe["Product"]
    category = dataframe["Category"]

    comparable = product.notna() & category.notna()

    expected_category = product.map(mapping)

    known_product = expected_category.notna()

    invalid = (
        comparable
        & known_product
        & (category != expected_category)
    )

    affected_row_count = int(invalid.sum())

    if affected_row_count == 0:
        return []

    return [
        {
            "code": "PRODUCT_CATEGORY_INCONSISTENCY",
            "severity": "ERROR",
            "columns": [
                "Product",
                "Category",
            ],
            "affectedRowCount": affected_row_count,
            "rule": "Product must map to its canonical Category.",
        }
    ]