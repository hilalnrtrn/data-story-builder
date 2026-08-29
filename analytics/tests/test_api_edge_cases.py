from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app, raise_server_exceptions=False)

INSUFFICIENT_DETAIL = (
    "The dataset does not contain the required analytical structure or "
    "enough valid findings to produce an analysis story."
)


def _post_file(file_name: str, content: bytes, content_type: str = "text/csv"):
    return client.post(
        "/datasets/prepare",
        data={"analysis_id": f"edge-{file_name}"},
        files={"file": (file_name, content, content_type)},
    )


def test_empty_csv_returns_controlled_client_error():
    response = _post_file("empty.csv", b"")

    assert response.status_code == 400
    assert response.json() == {"detail": "The uploaded file is empty."}


def test_header_only_csv_returns_controlled_insufficient_data_error():
    response = _post_file(
        "header.csv",
        b"Date,Revenue,Orders,Customers,Product,Region,Channel\n",
    )

    assert response.status_code == 422
    assert response.json() == {"detail": INSUFFICIENT_DETAIL}


def test_unsupported_extension_returns_controlled_client_error():
    response = _post_file(
        "dataset.txt",
        b"Date,Revenue\n2025-01-01,100\n",
        "text/plain",
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Unsupported file type. Only CSV and XLSX files are supported."
    }


def test_malformed_csv_returns_controlled_client_error():
    malformed = b"Date,Revenue\n" + bytes([34]) + b"unterminated,100\n"

    response = _post_file("malformed.csv", malformed)

    assert response.status_code == 400
    assert response.json() == {"detail": "Unable to parse CSV file."}


def test_malformed_xlsx_returns_controlled_client_error():
    response = _post_file(
        "malformed.xlsx",
        b"not-an-xlsx-workbook",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Unable to parse XLSX file."}


def test_missing_date_returns_controlled_insufficient_data_error():
    response = _post_file(
        "missing-date.csv",
        b"Revenue,Orders,Customers,Product,Region,Channel\n"
        b"100,1,1,Product A,Marmara,Online\n",
    )

    assert response.status_code == 422
    assert response.json() == {"detail": INSUFFICIENT_DETAIL}


def test_missing_revenue_returns_controlled_insufficient_data_error():
    response = _post_file(
        "missing-revenue.csv",
        b"Date,Orders,Customers,Product,Region,Channel\n"
        b"2025-05-01,1,1,Product A,Marmara,Online\n",
    )

    assert response.status_code == 422
    assert response.json() == {"detail": INSUFFICIENT_DETAIL}


def test_small_dataset_without_story_eligible_findings_returns_controlled_error():
    response = _post_file(
        "small.csv",
        b"Date,Region,Category,Product,Channel,Campaign,Revenue,Orders,"
        b"Customers,Quantity,MarketingSpend,StockLevel,Discount,Returns\n"
        b"2025-05-01,Marmara,Electronics,Product A,Online,None,100,1,1,"
        b"1,10,5,0.1,0\n",
    )

    assert response.status_code == 422
    assert response.json() == {"detail": INSUFFICIENT_DETAIL}
