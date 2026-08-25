import copy
import json
import math
from pathlib import Path

import pytest

from app.services.ingestion import read_dataset
from app.services.insight_engine import generate_insights
from app.services.insight_integrity import (
    check_change_total_consistency,
    check_contribution_consistency,
)
from app.services.preparation import prepare_dataset


ROOT_DIR = Path(__file__).resolve().parents[2]
SAMPLE_DATA_PATH = ROOT_DIR / "sample-data" / "sales_demo_clean.csv"
GOLDEN_TRUTH_PATH = ROOT_DIR / "tests" / "golden" / "expected_results.json"
ANALYSIS_ID = "DAY9-CONSISTENCY-GOLDEN"


def test_revenue_and_marmara_reconciliations_match_golden_truth() -> None:
    golden_bytes = GOLDEN_TRUTH_PATH.read_bytes()
    golden_truth = json.loads(golden_bytes.decode("utf-8"))
    golden_snapshot = copy.deepcopy(golden_truth)

    expected_change = next(
        insight
        for insight in golden_truth["requiredInsights"]
        if insight["type"] == "CHANGE" and insight["metric"] == "Revenue"
    )
    expected_contribution = next(
        contribution
        for contribution in golden_truth["expectedContributions"]
        if contribution["metric"] == "Revenue"
        and contribution["dimension"] == "Region"
        and contribution["segment"] == "Marmara"
        and contribution["previousPeriod"] == expected_change["previousPeriod"]
        and contribution["currentPeriod"] == expected_change["currentPeriod"]
    )

    dataframe = read_dataset(
        file_bytes=SAMPLE_DATA_PATH.read_bytes(),
        file_name=SAMPLE_DATA_PATH.name,
    )
    prepared_dataframe, _ = prepare_dataset(dataframe)
    insights = generate_insights(
        prepared_dataframe,
        analysis_id=ANALYSIS_ID,
        file_name=SAMPLE_DATA_PATH.name,
    )

    revenue_matches = [
        insight
        for insight in insights
        if insight.type == "CHANGE"
        and insight.metric == expected_change["metric"]
        and insight.dimension is None
        and insight.segment is None
        and insight.period.get("previous") == expected_change["previousPeriod"]
        and insight.period.get("current") == expected_change["currentPeriod"]
    ]
    assert len(revenue_matches) == 1
    revenue_change = revenue_matches[0]
    assert revenue_change.values["previous"] == pytest.approx(
        expected_change["expectedPreviousValue"],
        abs=expected_change["tolerance"],
    )
    assert revenue_change.values["current"] == pytest.approx(
        expected_change["expectedCurrentValue"],
        abs=expected_change["tolerance"],
    )

    total_check = check_change_total_consistency(
        revenue_change,
        prepared_dataframe,
        dimension="Region",
        aggregation="SUM",
    )
    assert total_check is not None
    assert total_check.code == "TOTAL_VS_DIMENSION_RECONCILIATION"
    assert total_check.status == "PASS"
    assert total_check.expected_value is not None
    assert total_check.actual_value is not None
    assert total_check.difference is not None
    assert total_check.tolerance is not None
    assert math.isfinite(total_check.expected_value)
    assert math.isfinite(total_check.actual_value)
    assert abs(total_check.difference) <= total_check.tolerance
    assert total_check.expected_value == pytest.approx(
        expected_change["expectedCurrentValue"],
        abs=expected_change["tolerance"],
    )

    marmara_matches = [
        insight
        for insight in insights
        if insight.type == "CONTRIBUTION"
        and insight.metric == expected_contribution["metric"]
        and insight.dimension == expected_contribution["dimension"]
        and insight.segment == expected_contribution["segment"]
        and insight.period.get("previous")
        == expected_contribution["previousPeriod"]
        and insight.period.get("current")
        == expected_contribution["currentPeriod"]
    ]
    assert len(marmara_matches) == 1
    marmara_contribution = marmara_matches[0]
    assert marmara_contribution.values["contributionShare"] == pytest.approx(
        expected_contribution["expectedContributionShare"],
        abs=expected_contribution["tolerance"],
    )

    contribution_check = check_contribution_consistency(
        marmara_contribution,
        revenue_change,
    )
    assert contribution_check is not None
    assert contribution_check.code == "CONTRIBUTION_TOTAL_RECONCILIATION"
    assert contribution_check.status == "PASS"
    assert contribution_check.expected_value == revenue_change.values[
        "absoluteChange"
    ]
    assert contribution_check.actual_value == marmara_contribution.values[
        "totalAbsoluteChange"
    ]
    assert contribution_check.difference is not None
    assert contribution_check.tolerance is not None
    assert abs(contribution_check.difference) <= contribution_check.tolerance

    checks = [total_check, contribution_check]
    assert all(check.code != "DATA_CONTRADICTION" for check in checks)
    assert golden_truth == golden_snapshot
    assert GOLDEN_TRUTH_PATH.read_bytes() == golden_bytes
