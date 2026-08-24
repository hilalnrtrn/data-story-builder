from pathlib import Path

import pandas as pd
import pytest

from app.services.derived_metrics import (
    build_return_rate_change_insight,
    calculate_return_rate,
)
from app.services.ingestion import read_dataset
from app.services.preparation import prepare_dataset


ROOT_DIR = Path(__file__).resolve().parents[2]
SAMPLE_DATA_PATH = ROOT_DIR / "sample-data" / "sales_demo_clean.csv"


def _dataframe(**overrides) -> pd.DataFrame:
    data = {
        "Date": pd.to_datetime(["2025-08-01", "2025-08-02"]),
        "Returns": [1, 9],
        "Quantity": [10, 30],
    }
    data.update(overrides)
    return pd.DataFrame(data)


def test_calculates_return_rate_as_ratio_of_sums() -> None:
    dataframe = _dataframe()

    result = calculate_return_rate(dataframe, period="2025-08")

    assert result == pytest.approx((1 + 9) / (10 + 30))


def test_does_not_average_row_level_return_rates() -> None:
    dataframe = _dataframe()
    row_level_average = (
        dataframe["Returns"] / dataframe["Quantity"]
    ).mean()

    result = calculate_return_rate(dataframe, period="2025-08")

    assert result == pytest.approx(0.25)
    assert result != pytest.approx(row_level_average)


@pytest.mark.parametrize("missing_column", ["Date", "Returns", "Quantity"])
def test_missing_required_column_returns_none(missing_column: str) -> None:
    dataframe = _dataframe().drop(columns=[missing_column])

    assert calculate_return_rate(dataframe, period="2025-08") is None


def test_period_without_rows_returns_none() -> None:
    assert calculate_return_rate(_dataframe(), period="2025-09") is None


def test_zero_quantity_sum_returns_none() -> None:
    dataframe = _dataframe(Quantity=[10, -10])

    assert calculate_return_rate(dataframe, period="2025-08") is None


def test_real_novaretail_return_rates() -> None:
    dataframe = read_dataset(
        file_bytes=SAMPLE_DATA_PATH.read_bytes(),
        file_name=SAMPLE_DATA_PATH.name,
    )
    prepared_dataframe, _ = prepare_dataset(dataframe)

    assert calculate_return_rate(
        prepared_dataframe,
        period="2025-08",
    ) == pytest.approx(0.02)
    assert calculate_return_rate(
        prepared_dataframe,
        period="2025-09",
    ) == pytest.approx(0.035)


def test_builds_real_novaretail_return_rate_change_insight() -> None:
    dataframe = read_dataset(
        file_bytes=SAMPLE_DATA_PATH.read_bytes(),
        file_name=SAMPLE_DATA_PATH.name,
    )
    prepared_dataframe, _ = prepare_dataset(dataframe)

    insight = build_return_rate_change_insight(
        prepared_dataframe,
        analysis_id="analysis-return-rate",
        file_name=SAMPLE_DATA_PATH.name,
        previous_period="2025-08",
        current_period="2025-09",
    )

    assert insight is not None
    assert insight.id == "CHANGE-ReturnRate-2025-08-2025-09"
    assert insight.analysis_id == "analysis-return-rate"
    assert insight.type == "CHANGE"
    assert insight.metric == "ReturnRate"
    assert insight.period_granularity == "MONTH"
    assert insight.period == {
        "previous": "2025-08",
        "current": "2025-09",
    }
    assert insight.direction == "UP"
    assert insight.values == {
        "previous": 0.02,
        "current": 0.035,
        "absoluteChange": 0.015,
        "percentageChange": 75.0,
        "percentagePointChange": 1.5,
    }
    assert insight.detection == {
        "method": "DERIVED_RATIO_OF_SUMS_PERIOD_COMPARISON",
        "formula": "SUM(Returns) / SUM(Quantity)",
        "numerator": "Returns",
        "denominator": "Quantity",
        "aggregation": "RATIO_OF_SUMS",
        "minimumPercentageChange": 5.0,
    }
    assert insight.detection["minimumPercentageChange"] == 5.0
    assert [evidence.code for evidence in insight.evidence] == [
        "PREVIOUS_RETURN_RATE",
        "CURRENT_RETURN_RATE",
        "PERCENTAGE_CHANGE",
        "PERCENTAGE_POINT_CHANGE",
    ]
    assert insight.source is not None
    assert insight.source.file_name == SAMPLE_DATA_PATH.name
    assert insight.source.row_count == len(prepared_dataframe)
    assert insight.confidence is None
    assert insight.importance is None


@pytest.mark.parametrize(
    ("previous_period", "current_period"),
    [
        ("2025-07", "2025-08"),
        ("2025-08", "2025-09"),
    ],
    ids=["missing-previous", "missing-current"],
)
def test_return_rate_change_requires_both_periods(
    previous_period: str,
    current_period: str,
) -> None:
    dataframe = _dataframe()

    assert build_return_rate_change_insight(
        dataframe,
        analysis_id="analysis-return-rate",
        file_name="returns.csv",
        previous_period=previous_period,
        current_period=current_period,
    ) is None


def test_return_rate_change_rejects_zero_previous_rate() -> None:
    dataframe = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2025-08-01", "2025-09-01"]),
            "Returns": [0, 1],
            "Quantity": [10, 10],
        }
    )

    assert build_return_rate_change_insight(
        dataframe,
        analysis_id="analysis-return-rate",
        file_name="returns.csv",
        previous_period="2025-08",
        current_period="2025-09",
    ) is None


def test_return_rate_change_below_configured_threshold_returns_none() -> None:
    dataframe = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2025-08-01", "2025-09-01"]),
            "Returns": [100, 104],
            "Quantity": [100, 100],
        }
    )

    assert build_return_rate_change_insight(
        dataframe,
        analysis_id="analysis-return-rate",
        file_name="returns.csv",
        previous_period="2025-08",
        current_period="2025-09",
    ) is None


def test_return_rate_change_at_configured_threshold_is_eligible() -> None:
    dataframe = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2025-08-01", "2025-09-01"]),
            "Returns": [100, 105],
            "Quantity": [100, 100],
        }
    )

    insight = build_return_rate_change_insight(
        dataframe,
        analysis_id="analysis-return-rate",
        file_name="returns.csv",
        previous_period="2025-08",
        current_period="2025-09",
    )

    assert insight is not None
    assert insight.values["percentageChange"] == pytest.approx(5.0)
