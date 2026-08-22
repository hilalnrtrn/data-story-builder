import pandas as pd

from app.services.semantic_roles import detect_semantic_roles


def test_known_columns_use_metadata_roles():
    dataframe = pd.DataFrame(
        {
            "Date": pd.to_datetime(
                ["2025-01-01", "2025-01-02"]
            ),
            "Region": ["Marmara", "Ege"],
            "Revenue": [100.0, 200.0],
        }
    )

    roles = detect_semantic_roles(dataframe)

    assert roles["temporal"] == [
        {
            "name": "Date",
            "role": "TEMPORAL",
            "source": "METADATA",
            "hasMetadata": True,

        }
    ]

    assert roles["dimensions"] == [
        {
            "name": "Region",
            "role": "DIMENSION",
            "source": "METADATA",
            "hasMetadata": True,
        }
    ]

    assert roles["metrics"] == [
        {
            "name": "Revenue",
            "role": "METRIC",
            "source": "METADATA",
            "hasMetadata": True,
        }
    ]


def test_unknown_numeric_column_is_inferred_as_metric():
    dataframe = pd.DataFrame(
        {
            "Profit": [100.0, 120.0, 140.0],
        }
    )

    roles = detect_semantic_roles(dataframe)

    assert roles["metrics"] == [
        {
            "name": "Profit",
            "role": "METRIC",
            "source": "INFERRED",
            "hasMetadata": False,

        }
    ]


def test_unknown_text_column_is_inferred_as_dimension():
    dataframe = pd.DataFrame(
        {
            "Department": [
                "Sales",
                "Finance",
                "Sales",
            ]
        }
    )

    roles = detect_semantic_roles(dataframe)

    assert roles["dimensions"] == [
        {
            "name": "Department",
            "role": "DIMENSION",
            "source": "INFERRED",
            "hasMetadata": False,
        }
    ]


def test_identifier_like_numeric_column_is_not_metric():
    dataframe = pd.DataFrame(
        {
            "CustomerId": [1001, 1002, 1003],
        }
    )

    roles = detect_semantic_roles(dataframe)

    assert roles["metrics"] == []

    assert roles["dimensions"] == [
        {
            "name": "CustomerId",
            "role": "DIMENSION",
            "source": "INFERRED",
            "hasMetadata": False,
        }
    ]


def test_unknown_datetime_column_is_temporal():
    dataframe = pd.DataFrame(
        {
            "CreatedAt": pd.to_datetime(
                [
                    "2025-01-01",
                    "2025-01-02",
                ]
            )
        }
    )

    roles = detect_semantic_roles(dataframe)

    assert roles["temporal"] == [
        {
            "name": "CreatedAt",
            "role": "TEMPORAL",
            "source": "INFERRED",
            "hasMetadata": False,
        }
    ]

from app.services.semantic_roles import (
    detect_semantic_roles,
    find_missing_metric_definitions,
)


def test_inferred_metric_without_metadata_creates_warning():
    dataframe = pd.DataFrame(
        {
            "Profit": [100.0, 120.0, 140.0],
        }
    )

    roles = detect_semantic_roles(dataframe)
    findings = find_missing_metric_definitions(roles)

    assert findings == [
        {
            "code": "METRIC_DEFINITION_MISSING",
            "severity": "WARNING",
            "column": "Profit",
            "message": "Metric semantic definition is missing for Profit.",
        }
    ]


def test_known_metric_does_not_create_missing_definition_warning():
    dataframe = pd.DataFrame(
        {
            "Revenue": [100.0, 120.0, 140.0],
        }
    )

    roles = detect_semantic_roles(dataframe)
    findings = find_missing_metric_definitions(roles)

    assert findings == []