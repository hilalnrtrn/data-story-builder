import pandas as pd

from app.services.integrity import validate_integrity


def test_negative_orders_creates_error_finding():
    dataframe = pd.DataFrame(
        {
            "Orders": [10, -4, 20, -1],
        }
    )

    integrity = validate_integrity(dataframe)

    finding = next(
        item
        for item in integrity["findings"]
        if item["column"] == "Orders"
    )

    assert finding["code"] == "VALUE_BELOW_MINIMUM"
    assert finding["severity"] == "ERROR"
    assert finding["affectedRowCount"] == 2
    assert integrity["status"] == "FAILED"


def test_discount_above_maximum_creates_error_finding():
    dataframe = pd.DataFrame(
        {
            "Discount": [
                0.10,
                0.25,
                1.20,
                0.80,
            ],
        }
    )

    integrity = validate_integrity(dataframe)

    finding = next(
        item
        for item in integrity["findings"]
        if item["column"] == "Discount"
    )

    assert finding["code"] == "VALUE_ABOVE_MAXIMUM"
    assert finding["severity"] == "ERROR"
    assert finding["affectedRowCount"] == 2
    assert integrity["status"] == "FAILED"


def test_valid_known_metric_creates_no_integrity_error():
    dataframe = pd.DataFrame(
        {
            "Revenue": [
                100.0,
                200.0,
                300.0,
            ],
        }
    )

    integrity = validate_integrity(dataframe)

    assert integrity["status"] == "PASS"
    assert integrity["errorCount"] == 0
    assert integrity["findingCount"] == 0

def test_returns_greater_than_quantity_creates_error_finding():
    dataframe = pd.DataFrame(
        {
            "Quantity": [10, 5, 20, 7],
            "Returns": [1, 8, 2, 9],
        }
    )

    integrity = validate_integrity(dataframe)

    finding = next(
        item
        for item in integrity["findings"]
        if item["code"] == "RETURNS_NOT_GREATER_THAN_QUANTITY"
    )

    assert finding["severity"] == "ERROR"
    assert finding["columns"] == [
        "Returns",
        "Quantity",
    ]
    assert finding["affectedRowCount"] == 2
    assert finding["rule"] == "Returns <= Quantity"
    assert integrity["status"] == "FAILED"


def test_valid_returns_quantity_relationship_creates_no_error():
    dataframe = pd.DataFrame(
        {
            "Quantity": [10, 5, 20],
            "Returns": [1, 5, 0],
        }
    )

    integrity = validate_integrity(dataframe)

    matching_findings = [
        item
        for item in integrity["findings"]
        if item["code"] == "RETURNS_NOT_GREATER_THAN_QUANTITY"
    ]

    assert matching_findings == []


def test_cross_column_rule_ignores_missing_values():
    dataframe = pd.DataFrame(
        {
            "Quantity": [10, None, 20],
            "Returns": [1, 50, None],
        }
    )

    integrity = validate_integrity(dataframe)

    matching_findings = [
        item
        for item in integrity["findings"]
        if item["code"] == "RETURNS_NOT_GREATER_THAN_QUANTITY"
    ]

    assert matching_findings == []

def test_invalid_product_category_mapping_creates_error_finding():
    dataframe = pd.DataFrame(
        {
            "Product": [
                "Smart Watch",
                "Coffee Machine",
                "Office Chair",
                "Webcam",
            ],
            "Category": [
                "Home",
                "Home",
                "Electronics",
                "Office",
            ],
        }
    )

    integrity = validate_integrity(dataframe)

    finding = next(
        item
        for item in integrity["findings"]
        if item["code"] == "PRODUCT_CATEGORY_INCONSISTENCY"
    )

    assert finding["severity"] == "ERROR"
    assert finding["columns"] == [
        "Product",
        "Category",
    ]
    assert finding["affectedRowCount"] == 2
    assert integrity["status"] == "FAILED"


def test_valid_product_category_mapping_creates_no_error():
    dataframe = pd.DataFrame(
        {
            "Product": [
                "Smart Watch",
                "Coffee Machine",
                "Office Chair",
            ],
            "Category": [
                "Electronics",
                "Home",
                "Office",
            ],
        }
    )

    integrity = validate_integrity(dataframe)

    matching_findings = [
        item
        for item in integrity["findings"]
        if item["code"] == "PRODUCT_CATEGORY_INCONSISTENCY"
    ]

    assert matching_findings == []


def test_unknown_product_does_not_create_false_consistency_error():
    dataframe = pd.DataFrame(
        {
            "Product": [
                "Unknown Product",
            ],
            "Category": [
                "Electronics",
            ],
        }
    )

    integrity = validate_integrity(dataframe)

    matching_findings = [
        item
        for item in integrity["findings"]
        if item["code"] == "PRODUCT_CATEGORY_INCONSISTENCY"
    ]

    assert matching_findings == []

def test_integrity_summary_counts_findings_and_affected_rows():
    dataframe = pd.DataFrame(
        {
            "Orders": [10, -4, -1],
            "Discount": [0.10, 1.20, 0.80],
        }
    )

    integrity = validate_integrity(dataframe)

    assert integrity["status"] == "FAILED"
    assert integrity["findingCount"] == 2
    assert integrity["errorCount"] == 2
    assert integrity["warningCount"] == 0
    assert integrity["affectedRowCount"] == 4


def test_integrity_summary_returns_warning_status_for_warning_only():
    dataframe = pd.DataFrame(
        {
            "Profit": [100.0, 120.0, 140.0],
        }
    )

    integrity = validate_integrity(dataframe)

    assert integrity["status"] == "WARNING"
    assert integrity["findingCount"] == 1
    assert integrity["errorCount"] == 0
    assert integrity["warningCount"] == 1
    assert integrity["affectedRowCount"] == 0