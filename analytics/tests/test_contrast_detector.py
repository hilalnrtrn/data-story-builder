import pandas as pd

from app.services.contrast_detector import (
    detect_top_bottom_contrast,
)


def _dataframe(rows: list[tuple[str, str, float]]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Date": pd.Timestamp(date),
                "Region": segment,
                "Revenue": value,
            }
            for date, segment, value in rows
        ]
    )


def _detect(
    dataframe: pd.DataFrame,
    *,
    aggregation: str = "SUM",
):
    return detect_top_bottom_contrast(
        dataframe,
        analysis_id="DAY6-CONTRAST",
        file_name="contrast.csv",
        metric="Revenue",
        dimension="Region",
        aggregation=aggregation,
        previous_period="2025-05",
        current_period="2025-06",
    )


def test_detects_clear_top_bottom_contrast():
    dataframe = _dataframe(
        [
            ("2025-05-01", "A", 100),
            ("2025-06-01", "A", 130),
            ("2025-05-01", "B", 100),
            ("2025-06-01", "B", 90),
        ]
    )

    insight = _detect(dataframe)

    assert insight is not None
    assert insight.type == "CONTRAST"
    assert insight.segment == "A"
    assert insight.direction == "UP"
    assert insight.values["subject"] == "A"
    assert insight.values["comparison"] == "B"
    assert insight.values["subjectChangePercent"] == 30
    assert insight.values["comparisonChangePercent"] == -10
    assert insight.values["differencePercentagePoints"] == 40
    assert insight.values["comparisonResult"] == "OUTPERFORMS"


def test_returns_none_for_gap_below_threshold():
    dataframe = _dataframe(
        [
            ("2025-05-01", "A", 100),
            ("2025-06-01", "A", 105),
            ("2025-05-01", "B", 100),
            ("2025-06-01", "B", 100),
        ]
    )

    assert _detect(dataframe) is None


def test_excludes_segment_with_zero_previous_value():
    dataframe = _dataframe(
        [
            ("2025-05-01", "A", 0),
            ("2025-06-01", "A", 100),
            ("2025-05-01", "B", 100),
            ("2025-06-01", "B", 130),
            ("2025-05-01", "C", 100),
            ("2025-06-01", "C", 90),
        ]
    )

    insight = _detect(dataframe)

    assert insight is not None
    assert insight.values["subject"] == "B"
    assert insight.values["comparison"] == "C"


def test_returns_none_with_fewer_than_two_valid_segments():
    dataframe = _dataframe(
        [
            ("2025-05-01", "A", 0),
            ("2025-06-01", "A", 100),
            ("2025-05-01", "B", 100),
            ("2025-06-01", "B", 130),
        ]
    )

    assert _detect(dataframe) is None


def test_returns_none_for_unsupported_aggregation():
    dataframe = _dataframe(
        [
            ("2025-05-01", "A", 100),
            ("2025-06-01", "A", 130),
            ("2025-05-01", "B", 100),
            ("2025-06-01", "B", 90),
        ]
    )

    assert _detect(dataframe, aggregation="MEDIAN") is None


def test_supports_avg_aggregation():
    dataframe = _dataframe(
        [
            ("2025-05-01", "A", 10),
            ("2025-05-02", "A", 20),
            ("2025-06-01", "A", 20),
            ("2025-06-02", "A", 40),
            ("2025-05-01", "B", 20),
            ("2025-05-02", "B", 40),
            ("2025-06-01", "B", 20),
            ("2025-06-02", "B", 40),
        ]
    )

    insight = _detect(dataframe, aggregation="AVG")

    assert insight is not None
    assert insight.values["subject"] == "A"
    assert insight.values["subjectPreviousValue"] == 15
    assert insight.values["subjectCurrentValue"] == 30
    assert insight.values["subjectChangePercent"] == 100
    assert insight.values["comparison"] == "B"
    assert insight.values["comparisonChangePercent"] == 0


def test_breaks_change_ties_by_segment_name():
    dataframe = _dataframe(
        [
            ("2025-05-01", "B", 100),
            ("2025-06-01", "B", 130),
            ("2025-05-01", "A", 100),
            ("2025-06-01", "A", 130),
            ("2025-05-01", "D", 100),
            ("2025-06-01", "D", 90),
            ("2025-05-01", "C", 100),
            ("2025-06-01", "C", 90),
        ]
    )

    insight = _detect(dataframe)

    assert insight is not None
    assert insight.values["subject"] == "A"
    assert insight.values["comparison"] == "C"


def test_serializes_evidence_and_source_with_aliases():
    dataframe = _dataframe(
        [
            ("2025-05-01", "A", 100),
            ("2025-06-01", "A", 130),
            ("2025-05-01", "B", 100),
            ("2025-06-01", "B", 90),
        ]
    )

    insight = _detect(dataframe)

    assert insight is not None

    serialized = insight.model_dump(by_alias=True)

    assert serialized["source"] == {
        "fileName": "contrast.csv",
        "rowCount": 4,
    }

    evidence = {
        item["code"]: item
        for item in serialized["evidence"]
    }

    assert evidence["SUBJECT_CHANGE_PERCENT"]["unit"] == "PERCENT"
    assert (
        evidence["COMPARISON_CHANGE_PERCENT"]["unit"]
        == "PERCENT"
    )
    assert (
        evidence["DIFFERENCE_PERCENTAGE_POINTS"]["unit"]
        == "PERCENTAGE_POINTS"
    )
    assert evidence["COMPARISON_RESULT"]["value"] == "OUTPERFORMS"
