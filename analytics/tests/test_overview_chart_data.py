import pandas as pd

from app.services.overview_chart_data import build_overview_chart_data


METADATA = {
    "columns": {
        "Revenue": {
            "aggregation": "SUM",
        }
    }
}


def _chart(dataframe: pd.DataFrame) -> dict:
    return build_overview_chart_data(dataframe, METADATA)[
        "revenueOverTime"
    ]


def _region_chart(dataframe: pd.DataFrame) -> dict:
    return build_overview_chart_data(dataframe, METADATA)[
        "revenueByRegion"
    ]


def test_revenue_over_time_is_ready_and_sorted_by_month():
    dataframe = pd.DataFrame(
        {
            "Date": pd.to_datetime(
                ["2026-03-02", "2026-01-10", "2026-02-04"]
            ),
            "Revenue": [30.5, 10.25, 20.75],
        }
    )

    chart = _chart(dataframe)

    assert chart == {
        "status": "READY",
        "metric": "Revenue",
        "aggregation": "SUM",
        "granularity": "MONTH",
        "periodStart": "2026-01",
        "periodEnd": "2026-03",
        "points": [
            {"period": "2026-01", "value": 10.25},
            {"period": "2026-02", "value": 20.75},
            {"period": "2026-03", "value": 30.5},
        ],
        "unavailableReason": None,
    }


def test_revenue_over_time_uses_sum_for_each_month():
    dataframe = pd.DataFrame(
        {
            "Date": pd.to_datetime(
                ["2024-07-01", "2024-07-15", "2024-08-01"]
            ),
            "Revenue": [11.2, 8.8, 7.5],
        }
    )

    assert _chart(dataframe)["points"] == [
        {"period": "2024-07", "value": 20},
        {"period": "2024-08", "value": 7.5},
    ]


def test_revenue_over_time_is_unavailable_without_revenue():
    chart = _chart(
        pd.DataFrame({"Date": pd.to_datetime(["2024-01-01"])})
    )

    assert chart["status"] == "UNAVAILABLE"
    assert chart["points"] == []
    assert chart["periodStart"] is None
    assert chart["periodEnd"] is None
    assert chart["unavailableReason"] == "Revenue column is unavailable."


def test_revenue_over_time_is_unavailable_without_date():
    chart = _chart(pd.DataFrame({"Revenue": [123.45]}))

    assert chart["status"] == "UNAVAILABLE"
    assert chart["points"] == []
    assert chart["unavailableReason"] == "Date column is unavailable."


def test_revenue_over_time_does_not_depend_on_demo_values():
    dataframe = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2031-11-03", "2031-11-20"]),
            "Revenue": [1.125, 2.25],
        }
    )

    assert _chart(dataframe)["points"] == [
        {"period": "2031-11", "value": 3.375}
    ]


def test_revenue_over_time_output_is_deterministic():
    dataframe = pd.DataFrame(
        {
            "Date": pd.to_datetime(
                ["2027-02-01", "2027-01-02", "2027-02-12"]
            ),
            "Revenue": [4, 3, 2],
        }
    )

    assert _chart(dataframe) == _chart(dataframe.copy())


def test_revenue_by_region_is_ready_and_includes_every_valid_region():
    dataframe = pd.DataFrame(
        {
            "Date": pd.to_datetime(
                ["2030-04-03", "2030-04-09", "2030-05-01", None]
            ),
            "Region": ["North", "South", "North", "West"],
            "Revenue": [10.25, 8, 4.75, 3],
        }
    )

    assert _region_chart(dataframe) == {
        "status": "READY",
        "metric": "Revenue",
        "dimension": "Region",
        "aggregation": "SUM",
        "periodStart": "2030-04-03",
        "periodEnd": "2030-05-01",
        "points": [
            {"segment": "North", "value": 15},
            {"segment": "South", "value": 8},
            {"segment": "West", "value": 3},
        ],
        "unavailableReason": None,
    }


def test_revenue_by_region_uses_sum_and_deterministic_tie_breaker():
    dataframe = pd.DataFrame(
        {
            "Region": ["Zeta", "Alpha", "Zeta", "Beta"],
            "Revenue": [4, 10, 6, 10],
        }
    )

    assert _region_chart(dataframe)["points"] == [
        {"segment": "Alpha", "value": 10},
        {"segment": "Beta", "value": 10},
        {"segment": "Zeta", "value": 10},
    ]


def test_revenue_by_region_is_unavailable_without_revenue():
    chart = _region_chart(pd.DataFrame({"Region": ["North"]}))

    assert chart["status"] == "UNAVAILABLE"
    assert chart["points"] == []
    assert chart["unavailableReason"] == "Revenue column is unavailable."


def test_revenue_by_region_is_unavailable_without_region():
    chart = _region_chart(pd.DataFrame({"Revenue": [12.5]}))

    assert chart["status"] == "UNAVAILABLE"
    assert chart["points"] == []
    assert chart["unavailableReason"] == "Region column is unavailable."


def test_revenue_by_region_remains_ready_without_date():
    chart = _region_chart(
        pd.DataFrame(
            {
                "Region": ["Custom East", "Custom West"],
                "Revenue": [1.25, 2.5],
            }
        )
    )

    assert chart["status"] == "READY"
    assert chart["periodStart"] is None
    assert chart["periodEnd"] is None
    assert chart["points"] == [
        {"segment": "Custom West", "value": 2.5},
        {"segment": "Custom East", "value": 1.25},
    ]


def test_revenue_by_region_output_is_deterministic():
    dataframe = pd.DataFrame(
        {
            "Region": ["Gamma", "Alpha", "Beta"],
            "Revenue": [2, 3, 1],
        }
    )

    assert _region_chart(dataframe) == _region_chart(dataframe.copy())
