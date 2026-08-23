import pandas as pd
import pytest

from app.services.contribution_detector import (
    detect_contribution,
    detect_contributions,
)


def _dataframe(
    previous_values: dict[str, float],
    current_values: dict[str, float],
) -> pd.DataFrame:
    rows = []

    for segment, value in previous_values.items():
        rows.append(
            {
                "Date": pd.Timestamp("2025-05-01"),
                "Product": segment,
                "Revenue": value,
            }
        )

    for segment, value in current_values.items():
        rows.append(
            {
                "Date": pd.Timestamp("2025-06-01"),
                "Product": segment,
                "Revenue": value,
            }
        )

    return pd.DataFrame(rows)


def _detect(
    dataframe: pd.DataFrame,
    *,
    segment: str = "A",
    aggregation: str = "SUM",
):
    return detect_contribution(
        dataframe,
        analysis_id="DAY6-CONTRIBUTION",
        file_name="contribution.csv",
        metric="Revenue",
        dimension="Product",
        segment=segment,
        aggregation=aggregation,
        previous_period="2025-05",
        current_period="2025-06",
    )


def _detect_all(dataframe: pd.DataFrame):
    return detect_contributions(
        dataframe,
        analysis_id="DAY6-CONTRIBUTIONS",
        file_name="contributions.csv",
        metric="Revenue",
        dimension="Product",
        aggregation="SUM",
        previous_period="2025-05",
        current_period="2025-06",
    )


def _find_segment(insights, segment: str):
    return next(
        insight
        for insight in insights
        if insight.segment == segment
    )


def test_detects_basic_positive_contribution():
    dataframe = _dataframe(
        {"A": 100, "B": 900},
        {"A": 310, "B": 990},
    )

    insight = _detect(dataframe)

    assert insight is not None
    assert insight.type == "CONTRIBUTION"
    assert insight.direction == "UP"
    assert insight.values["totalAbsoluteChange"] == 300
    assert insight.values["segmentAbsoluteChange"] == 210
    assert insight.values["contributionShare"] == 0.7
    assert (
        insight.values["contributorRole"]
        == "POSITIVE_CONTRIBUTOR"
    )


def test_detects_negative_offset():
    dataframe = _dataframe(
        {"A": 200, "B": 800},
        {"A": 140, "B": 1160},
    )

    insight = _detect(dataframe)

    assert insight is not None
    assert insight.values["contributionShare"] == -0.2
    assert insight.values["contributorRole"] == "NEGATIVE_OFFSET"
    assert insight.direction == "DOWN"


def test_detects_negative_contributor():
    dataframe = _dataframe(
        {"A": 300, "B": 700},
        {"A": 90, "B": 610},
    )

    insight = _detect(dataframe)

    assert insight is not None
    assert insight.values["totalAbsoluteChange"] == -300
    assert insight.values["segmentAbsoluteChange"] == -210
    assert insight.values["contributionShare"] == 0.7
    assert (
        insight.values["contributorRole"]
        == "NEGATIVE_CONTRIBUTOR"
    )
    assert insight.direction == "DOWN"


def test_detects_positive_offset():
    dataframe = _dataframe(
        {"A": 100, "B": 900},
        {"A": 160, "B": 540},
    )

    insight = _detect(dataframe)

    assert insight is not None
    assert insight.values["totalAbsoluteChange"] == -300
    assert insight.values["segmentAbsoluteChange"] == 60
    assert insight.values["contributionShare"] == -0.2
    assert insight.values["contributorRole"] == "POSITIVE_OFFSET"
    assert insight.direction == "UP"


def test_null_dimension_value_remains_in_total_only():
    dataframe = _dataframe(
        {"A": 100, "B": 900, None: 0},
        {"A": 310, "B": 990, None: 300},
    )

    insight = _detect(dataframe)

    assert insight is not None
    assert insight.values["segmentPreviousValue"] == 100
    assert insight.values["segmentCurrentValue"] == 310
    assert insight.values["segmentAbsoluteChange"] == 210
    assert insight.values["totalPreviousValue"] == 1000
    assert insight.values["totalCurrentValue"] == 1600
    assert insight.values["totalAbsoluteChange"] == 600
    assert insight.values["contributionShare"] == 0.35


def test_preserves_contribution_above_one_hundred_percent():
    dataframe = _dataframe(
        {"A": 100, "B": 900},
        {"A": 500, "B": 800},
    )

    insight = _detect(dataframe)

    assert insight is not None
    assert insight.values["contributionShare"] == pytest.approx(
        4 / 3,
        abs=0.000001,
    )
    assert insight.values["contributionShare"] > 1.0


def test_returns_none_when_total_change_is_zero():
    dataframe = _dataframe(
        {"A": 100, "B": 900},
        {"A": 200, "B": 800},
    )

    assert _detect(dataframe) is None


def test_returns_none_below_configured_threshold():
    dataframe = _dataframe(
        {"A": 100, "B": 900},
        {"A": 150, "B": 1150},
    )

    assert _detect(dataframe) is None


def test_returns_none_for_unsupported_aggregation():
    dataframe = _dataframe(
        {"A": 100, "B": 900},
        {"A": 310, "B": 990},
    )

    assert _detect(dataframe, aggregation="AVG") is None


def test_serializes_evidence_and_source_with_aliases():
    dataframe = _dataframe(
        {"A": 100, "B": 900},
        {"A": 310, "B": 990},
    )

    insight = _detect(dataframe)

    assert insight is not None

    serialized = insight.model_dump(by_alias=True)

    assert serialized["source"] == {
        "fileName": "contribution.csv",
        "rowCount": 4,
    }
    assert {
        item["code"]
        for item in serialized["evidence"]
    } == {
        "SEGMENT_PREVIOUS_VALUE",
        "SEGMENT_CURRENT_VALUE",
        "SEGMENT_ABSOLUTE_CHANGE",
        "TOTAL_ABSOLUTE_CHANGE",
        "CONTRIBUTION_SHARE",
        "CONTRIBUTOR_ROLE",
    }


def test_promotes_largest_positive_contributor():
    dataframe = _dataframe(
        {"A": 100, "B": 100, "C": 800},
        {"A": 400, "B": 300, "C": 800},
    )

    insights = _detect_all(dataframe)

    assert (
        _find_segment(insights, "A").values["contributorRole"]
        == "PRIMARY_POSITIVE_CONTRIBUTOR"
    )


def test_keeps_other_positive_contributors_unpromoted():
    dataframe = _dataframe(
        {"A": 100, "B": 100, "C": 800},
        {"A": 400, "B": 300, "C": 800},
    )

    insights = _detect_all(dataframe)

    assert (
        _find_segment(insights, "B").values["contributorRole"]
        == "POSITIVE_CONTRIBUTOR"
    )


def test_promotes_largest_negative_contributor():
    dataframe = _dataframe(
        {"A": 400, "B": 300, "C": 300},
        {"A": 100, "B": 100, "C": 300},
    )

    insights = _detect_all(dataframe)

    assert (
        _find_segment(insights, "A").values["contributorRole"]
        == "PRIMARY_NEGATIVE_CONTRIBUTOR"
    )
    assert (
        _find_segment(insights, "B").values["contributorRole"]
        == "NEGATIVE_CONTRIBUTOR"
    )


def test_does_not_promote_offsets():
    dataframe = _dataframe(
        {"A": 400, "B": 300, "C": 200, "D": 100},
        {"A": 100, "B": 100, "C": 100, "D": 200},
    )

    insights = _detect_all(dataframe)
    offset = _find_segment(insights, "D")

    assert offset.values["contributorRole"] == "POSITIVE_OFFSET"
    assert not offset.values["contributorRole"].startswith("PRIMARY")


def test_breaks_primary_ties_by_segment_name():
    dataframe = _dataframe(
        {"B": 100, "A": 100, "C": 800},
        {"B": 300, "A": 300, "C": 800},
    )

    insights = _detect_all(dataframe)

    assert [insight.segment for insight in insights] == ["A", "B"]
    assert (
        _find_segment(insights, "A").values["contributorRole"]
        == "PRIMARY_POSITIVE_CONTRIBUTOR"
    )
    assert (
        _find_segment(insights, "B").values["contributorRole"]
        == "POSITIVE_CONTRIBUTOR"
    )


def test_primary_role_matches_contributor_role_evidence():
    dataframe = _dataframe(
        {"A": 100, "B": 100, "C": 800},
        {"A": 400, "B": 300, "C": 800},
    )

    primary = _find_segment(_detect_all(dataframe), "A")
    role_evidence = next(
        evidence
        for evidence in primary.evidence
        if evidence.code == "CONTRIBUTOR_ROLE"
    )

    assert (
        primary.values["contributorRole"]
        == role_evidence.value
        == "PRIMARY_POSITIVE_CONTRIBUTOR"
    )
