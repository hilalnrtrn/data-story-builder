import pandas as pd

from app.services.profiler import profile_dataset


def test_profile_dataset_returns_basic_dataset_information():
    dataframe = pd.DataFrame(
        {
            "Revenue": [100.0, 200.0, None],
            "Region": ["Marmara", "Ege", "Marmara"],
        }
    )

    profile = profile_dataset(dataframe)

    assert profile["rowCount"] == 3
    assert profile["columnCount"] == 2


def test_profile_column_returns_common_statistics():
    dataframe = pd.DataFrame(
        {
            "Revenue": [100.0, 200.0, None],
        }
    )

    profile = profile_dataset(dataframe)
    revenue = profile["columns"][0]

    assert revenue["name"] == "Revenue"
    assert revenue["dataType"] == "numeric"
    assert revenue["count"] == 2
    assert revenue["missingCount"] == 1
    assert revenue["missingPercentage"] == 33.3333
    assert revenue["uniqueCount"] == 2


def test_profile_detects_categorical_column():
    dataframe = pd.DataFrame(
        {
            "Region": ["Marmara", "Ege", "Marmara"],
        }
    )

    profile = profile_dataset(dataframe)
    region = profile["columns"][0]

    assert region["dataType"] == "categorical"
    assert region["uniqueCount"] == 2


def test_profile_detects_datetime_column():
    dataframe = pd.DataFrame(
        {
            "Date": pd.to_datetime(
                [
                    "2025-01-01",
                    "2025-01-02",
                ]
            )
        }
    )

    profile = profile_dataset(dataframe)
    date = profile["columns"][0]

    assert date["dataType"] == "datetime"

def test_numeric_profile_returns_descriptive_statistics():
    dataframe = pd.DataFrame(
        {
            "Revenue": [100.0, 200.0, 300.0, 400.0],
        }
    )

    profile = profile_dataset(dataframe)
    revenue = profile["columns"][0]

    assert revenue["min"] == 100
    assert revenue["max"] == 400
    assert revenue["mean"] == 250.0
    assert revenue["median"] == 250.0
    assert revenue["std"] == 129.0994
    assert revenue["q1"] == 175.0
    assert revenue["q3"] == 325.0


def test_numeric_profile_ignores_missing_values_in_statistics():
    dataframe = pd.DataFrame(
        {
            "Orders": [10, 20, None, 30],
        }
    )

    profile = profile_dataset(dataframe)
    orders = profile["columns"][0]

    assert orders["count"] == 3
    assert orders["missingCount"] == 1
    assert orders["min"] == 10
    assert orders["max"] == 30
    assert orders["mean"] == 20.0
    assert orders["median"] == 20.0


def test_numeric_profile_handles_all_missing_column():
    dataframe = pd.DataFrame(
        {
            "StockLevel": pd.Series(
                [None, None],
                dtype="float64",
            )
        }
    )

    profile = profile_dataset(dataframe)
    stock = profile["columns"][0]

    assert stock["dataType"] == "numeric"
    assert stock["count"] == 0
    assert stock["missingCount"] == 2
    assert stock["min"] is None
    assert stock["max"] is None
    assert stock["mean"] is None
    assert stock["median"] is None
    assert stock["std"] is None
    assert stock["q1"] is None
    assert stock["q3"] is None

def test_categorical_profile_returns_top_values():
    dataframe = pd.DataFrame(
        {
            "Region": [
                "Marmara",
                "Ege",
                "Marmara",
                "Akdeniz",
                "Marmara",
                "Ege",
            ]
        }
    )

    profile = profile_dataset(dataframe)
    region = profile["columns"][0]

    assert region["topValues"] == [
        {
            "value": "Marmara",
            "count": 3,
        },
        {
            "value": "Ege",
            "count": 2,
        },
        {
            "value": "Akdeniz",
            "count": 1,
        },
    ]


def test_categorical_profile_ignores_missing_values():
    dataframe = pd.DataFrame(
        {
            "Campaign": [
                "None",
                None,
                "Summer Sale",
                "None",
            ]
        }
    )

    profile = profile_dataset(dataframe)
    campaign = profile["columns"][0]

    assert campaign["count"] == 3
    assert campaign["missingCount"] == 1

    assert campaign["topValues"] == [
        {
            "value": "None",
            "count": 2,
        },
        {
            "value": "Summer Sale",
            "count": 1,
        },
    ]


def test_categorical_profile_returns_empty_top_values_when_all_missing():
    dataframe = pd.DataFrame(
        {
            "Region": pd.Series(
                [None, None],
                dtype="object",
            )
        }
    )

    profile = profile_dataset(dataframe)
    region = profile["columns"][0]

    assert region["dataType"] == "categorical"
    assert region["topValues"] == []

def test_datetime_profile_returns_date_range_and_period_count():
    dataframe = pd.DataFrame(
        {
            "Date": pd.to_datetime(
                [
                    "2025-01-01",
                    "2025-01-02",
                    "2025-01-03",
                    None,
                ]
            )
        }
    )

    profile = profile_dataset(dataframe)
    date = profile["columns"][0]

    assert date["minDate"] == "2025-01-01"
    assert date["maxDate"] == "2025-01-03"
    assert date["uniquePeriodCount"] == 3
    assert date["frequencyEstimate"] == "DAILY"
    assert date["missingCount"] == 1


def test_datetime_profile_handles_repeated_dates():
    dataframe = pd.DataFrame(
        {
            "Date": pd.to_datetime(
                [
                    "2025-01-01",
                    "2025-01-01",
                    "2025-01-02",
                    "2025-01-02",
                    "2025-01-03",
                ]
            )
        }
    )

    profile = profile_dataset(dataframe)
    date = profile["columns"][0]

    assert date["uniquePeriodCount"] == 3
    assert date["frequencyEstimate"] == "DAILY"


def test_datetime_profile_detects_weekly_frequency():
    dataframe = pd.DataFrame(
        {
            "Date": pd.to_datetime(
                [
                    "2025-01-01",
                    "2025-01-08",
                    "2025-01-15",
                ]
            )
        }
    )

    profile = profile_dataset(dataframe)
    date = profile["columns"][0]

    assert date["frequencyEstimate"] == "WEEKLY"


def test_datetime_profile_detects_irregular_frequency():
    dataframe = pd.DataFrame(
        {
            "Date": pd.to_datetime(
                [
                    "2025-01-01",
                    "2025-01-02",
                    "2025-01-10",
                ]
            )
        }
    )

    profile = profile_dataset(dataframe)
    date = profile["columns"][0]

    assert date["frequencyEstimate"] == "IRREGULAR"


def test_datetime_profile_handles_all_missing_values():
    dataframe = pd.DataFrame(
        {
            "Date": pd.Series(
                [pd.NaT, pd.NaT],
                dtype="datetime64[ns]",
            )
        }
    )

    profile = profile_dataset(dataframe)
    date = profile["columns"][0]

    assert date["minDate"] is None
    assert date["maxDate"] is None
    assert date["uniquePeriodCount"] == 0
    assert date["frequencyEstimate"] == "UNKNOWN"