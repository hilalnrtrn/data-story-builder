from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)

SAMPLE_DATA_DIR = (
    Path(__file__).resolve().parents[2]
    / "sample-data"
)


def test_prepare_endpoint_returns_day4_profile_fields():
    file_path = SAMPLE_DATA_DIR / "sales_demo_dirty.csv"

    with file_path.open("rb") as file_stream:
        response = client.post(
            "/datasets/prepare",
            data={
                "analysis_id": "test-analysis-id",
            },
            files={
                "file": (
                    file_path.name,
                    file_stream,
                    "text/csv",
                )
            },
        )

    assert response.status_code == 200

    body = response.json()

    assert body["analysisId"] == "test-analysis-id"

    assert "datasetProfile" in body
    assert "semanticRoles" in body
    assert "integrity" in body
    assert "dataQuality" in body

    assert body["datasetProfile"]["columnCount"] == 14

    assert body["dataQuality"]["basis"] == "PREPARED_DATA"
    assert body["dataQuality"]["score"] < 100.0

def test_prepare_endpoint_matches_day4_golden_counts():
    file_path = SAMPLE_DATA_DIR / "sales_demo_dirty.csv"

    with file_path.open("rb") as file_stream:
        response = client.post(
            "/datasets/prepare",
            data={
                "analysis_id": "golden-day4-test",
            },
            files={
                "file": (
                    file_path.name,
                    file_stream,
                    "text/csv",
                )
            },
        )

    assert response.status_code == 200

    body = response.json()

    findings = body["integrity"]["findings"]

    product_category = next(
        item
        for item in findings
        if item["code"] == "PRODUCT_CATEGORY_INCONSISTENCY"
    )

    invalid_discount = next(
        item
        for item in findings
        if (
            item["code"] == "VALUE_ABOVE_MAXIMUM"
            and item["column"] == "Discount"
        )
    )

    negative_orders = next(
        item
        for item in findings
        if (
            item["code"] == "VALUE_BELOW_MINIMUM"
            and item["column"] == "Orders"
        )
    )

    returns_quantity = next(
        item
        for item in findings
        if item["code"] == "RETURNS_NOT_GREATER_THAN_QUANTITY"
    )

    assert product_category["affectedRowCount"] == 3
    assert invalid_discount["affectedRowCount"] == 2
    assert negative_orders["affectedRowCount"] == 2
    assert returns_quantity["affectedRowCount"] == 2

    columns = {
        column["name"]: column
        for column in body["datasetProfile"]["columns"]
    }

    assert columns["StockLevel"]["missingCount"] == 50
    assert columns["Date"]["missingCount"] == 2

def test_prepare_endpoint_clean_dataset_has_expected_profile():
    file_path = SAMPLE_DATA_DIR / "sales_demo_clean.csv"

    with file_path.open("rb") as file_stream:
        response = client.post(
            "/datasets/prepare",
            data={
                "analysis_id": "clean-day4-test",
            },
            files={
                "file": (
                    file_path.name,
                    file_stream,
                    "text/csv",
                )
            },
        )

    assert response.status_code == 200

    body = response.json()

    assert body["datasetProfile"]["rowCount"] == 43800
    assert body["datasetProfile"]["columnCount"] == 14

    columns = {
        column["name"]: column
        for column in body["datasetProfile"]["columns"]
    }

    assert columns["Date"]["missingCount"] == 0
    assert columns["StockLevel"]["missingCount"] == 0

    assert len(body["semanticRoles"]["metrics"]) == 8
    assert len(body["semanticRoles"]["dimensions"]) == 5
    assert len(body["semanticRoles"]["temporal"]) == 1

    assert body["integrity"]["status"] == "PASS"
    assert body["integrity"]["findingCount"] == 0
    assert body["integrity"]["errorCount"] == 0
    assert body["integrity"]["warningCount"] == 0

    assert body["dataQuality"]["completeness"] == 100.0
    assert body["dataQuality"]["validity"] == 100.0
    assert body["dataQuality"]["consistency"] == 100.0
    assert body["dataQuality"]["uniqueness"] == 100.0
    assert body["dataQuality"]["score"] == 100.0