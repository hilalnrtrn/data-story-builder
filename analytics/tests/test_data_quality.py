import pandas as pd

from app.services.data_quality import calculate_data_quality
from app.services.ingestion import read_dataset
from app.services.integrity import validate_integrity
from app.services.preparation import prepare_dataset


def test_perfect_dataset_returns_full_quality_score():
    dataframe = pd.DataFrame(
        {
            "Orders": [10, 20],
            "Discount": [0.10, 0.20],
            "Quantity": [5, 8],
            "Returns": [1, 2],
        }
    )

    integrity = validate_integrity(dataframe)
    quality = calculate_data_quality(
        dataframe,
        integrity,
    )

    assert quality["score"] == 100.0
    assert quality["completeness"] == 100.0
    assert quality["validity"] == 100.0
    assert quality["consistency"] == 100.0
    assert quality["uniqueness"] == 100.0
    assert quality["basis"] == "PREPARED_DATA"


def test_missing_values_reduce_completeness():
    dataframe = pd.DataFrame(
        {
            "A": [1, None],
            "B": [1, 2],
        }
    )

    integrity = validate_integrity(dataframe)
    quality = calculate_data_quality(
        dataframe,
        integrity,
    )

    assert quality["completeness"] == 75.0


def test_invalid_values_reduce_validity():
    dataframe = pd.DataFrame(
        {
            "Orders": [10, -1],
        }
    )

    integrity = validate_integrity(dataframe)
    quality = calculate_data_quality(
        dataframe,
        integrity,
    )

    assert quality["validity"] == 50.0


def test_consistency_errors_reduce_consistency():
    dataframe = pd.DataFrame(
        {
            "Quantity": [10, 5],
            "Returns": [1, 9],
        }
    )

    integrity = validate_integrity(dataframe)
    quality = calculate_data_quality(
        dataframe,
        integrity,
    )

    assert quality["consistency"] == 50.0


def test_duplicate_rows_reduce_uniqueness():
    dataframe = pd.DataFrame(
        {
            "Orders": [10, 10, 20],
            "Discount": [0.1, 0.1, 0.2],
        }
    )

    integrity = validate_integrity(dataframe)
    quality = calculate_data_quality(
        dataframe,
        integrity,
    )

    assert quality["uniqueness"] == 66.6667

from pathlib import Path

from app.services.ingestion import read_dataset
from app.services.preparation import prepare_dataset


SAMPLE_DATA_DIR = (
    Path(__file__).resolve().parents[2]
    / "sample-data"
)


def test_prepared_dirty_dataset_quality_reflects_remaining_issues():
    file_path = SAMPLE_DATA_DIR / "sales_demo_dirty.csv"

    dataframe = read_dataset(
        file_bytes=file_path.read_bytes(),
        file_name=file_path.name,
    )

    prepared_dataframe, _ = prepare_dataset(dataframe)

    integrity = validate_integrity(prepared_dataframe)

    quality = calculate_data_quality(
        prepared_dataframe,
        integrity,
    )

    assert quality["basis"] == "PREPARED_DATA"

    assert quality["uniqueness"] == 100.0

    assert quality["completeness"] < 100.0
    assert quality["validity"] < 100.0
    assert quality["consistency"] < 100.0

    assert quality["score"] < 100.0

def test_nullable_metadata_column_does_not_reduce_completeness():
    dataframe = pd.DataFrame(
        {
            "Revenue": [100.0, 200.0],
            "StockLevel": [50.0, None],
        }
    )

    integrity = validate_integrity(dataframe)

    quality = calculate_data_quality(
        dataframe,
        integrity,
    )

    assert quality["completeness"] == 100.0

def test_missing_required_metadata_column_reduces_completeness():
    dataframe = pd.DataFrame(
        {
            "Revenue": [100.0, None],
            "StockLevel": [50.0, None],
        }
    )

    integrity = validate_integrity(dataframe)

    quality = calculate_data_quality(
        dataframe,
        integrity,
    )

    assert quality["completeness"] == 50.0