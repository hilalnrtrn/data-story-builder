import json
from pathlib import Path

from app.services.ingestion import read_dataset
from app.services.insight_engine import generate_insights
from app.services.preparation import prepare_dataset


ROOT_DIR = Path(__file__).resolve().parents[2]

SAMPLE_DATA_DIR = ROOT_DIR / "sample-data"

GOLDEN_TRUTH_PATH = (
    ROOT_DIR
    / "tests"
    / "golden"
    / "expected_results.json"
)


def _load_golden_truth() -> dict:
    with GOLDEN_TRUTH_PATH.open(
        "r",
        encoding="utf-8",
    ) as golden_file:
        return json.load(golden_file)


def _load_prepared_clean_dataset():
    file_path = SAMPLE_DATA_DIR / "sales_demo_clean.csv"

    dataframe = read_dataset(
        file_bytes=file_path.read_bytes(),
        file_name=file_path.name,
    )

    prepared_dataframe, _ = prepare_dataset(dataframe)

    return prepared_dataframe, file_path.name


def _find_change_insight(
    insights,
    metric: str,
    previous_period: str,
    current_period: str,
):
    return next(
        (
            insight
            for insight in insights
            if insight.type == "CHANGE"
            and insight.metric == metric
            and insight.period.get("previous") == previous_period
            and insight.period.get("current") == current_period
        ),
        None,
    )


def _find_trend_insight(
    insights,
    metric: str,
    dimension: str,
    segment: str,
):
    return next(
        (
            insight
            for insight in insights
            if insight.type == "TREND"
            and insight.metric == metric
            and insight.dimension == dimension
            and insight.segment == segment
        ),
        None,
    )


def _find_anomaly_insight(
    insights,
    metric: str,
    dimension: str,
    segment: str,
    period: str,
):
    return next(
        (
            insight
            for insight in insights
            if insight.type == "ANOMALY"
            and insight.metric == metric
            and insight.dimension == dimension
            and insight.segment == segment
            and insight.period.get("current") == period
        ),
        None,
    )


def test_day5_golden_truth():
    golden = _load_golden_truth()

    prepared_dataframe, file_name = (
        _load_prepared_clean_dataset()
    )

    insights = generate_insights(
        prepared_dataframe,
        analysis_id="DAY5-GOLDEN",
        file_name=file_name,
    )

    failed_checks = []

    print()
    print("=" * 72)
    print("DAY 5 GOLDEN TRUTH CHECK")
    print("=" * 72)

    for expected in golden["requiredInsights"]:
        insight = _find_change_insight(
            insights,
            metric=expected["metric"],
            previous_period=expected["previousPeriod"],
            current_period=expected["currentPeriod"],
        )

        passed = insight is not None

        if passed:
            tolerance = expected["tolerance"]

            passed = (
                insight.direction
                == expected["expectedDirection"]
                and abs(
                    insight.values["previous"]
                    - expected["expectedPreviousValue"]
                )
                <= tolerance
                and abs(
                    insight.values["current"]
                    - expected["expectedCurrentValue"]
                )
                <= tolerance
                and abs(
                    insight.values["absoluteChange"]
                    - expected["expectedAbsoluteChange"]
                )
                <= tolerance
                and abs(
                    insight.values["percentageChange"]
                    - expected["expectedPercentageChange"]
                )
                <= tolerance
            )

        status = "PASS" if passed else "FAIL"

        actual_percentage = (
            insight.values["percentageChange"]
            if insight is not None
            else None
        )

        print(
            f"CHANGE {expected['metric']}: "
            f"expected={expected['expectedPercentageChange']}, "
            f"actual={actual_percentage}, "
            f"{status}"
        )

        if not passed:
            failed_checks.append(
                f"CHANGE {expected['metric']}"
            )

    for expected in golden["expectedTrends"]:
        if not expected.get("required", False):
            continue

        insight = _find_trend_insight(
            insights,
            metric=expected["metric"],
            dimension=expected["dimension"],
            segment=expected["segment"],
        )

        passed = insight is not None

        if passed:
            passed = (
                insight.direction
                == expected["expectedDirection"]
                and insight.detection["persistenceLevel"]
                == expected["expectedPersistence"]
                and insight.detection["monotonicMovement"]
                == expected["expectedMonotonicMovement"]
                and insight.period["start"]
                == expected["periodStart"]
                and insight.period["end"]
                == expected["periodEnd"]
            )

        status = "PASS" if passed else "FAIL"

        actual_direction = (
            insight.direction
            if insight is not None
            else None
        )

        actual_persistence = (
            insight.detection["persistenceLevel"]
            if insight is not None
            else None
        )

        print(
            f"TREND {expected['segment']}: "
            f"expectedDirection={expected['expectedDirection']}, "
            f"actualDirection={actual_direction}, "
            f"expectedPersistence="
            f"{expected['expectedPersistence']}, "
            f"actualPersistence={actual_persistence}, "
            f"{status}"
        )

        if not passed:
            failed_checks.append(
                f"TREND {expected['segment']}"
            )

    for expected in golden["expectedAnomalies"]:
        if not expected.get("required", False):
            continue

        insight = _find_anomaly_insight(
            insights,
            metric=expected["metric"],
            dimension=expected["dimension"],
            segment=expected["segment"],
            period=expected["period"],
        )

        passed = insight is not None

        if passed:
            passed = (
                insight.direction
                == expected["expectedDirection"]
                and insight.period["current"]
                == expected["period"]
            )

        status = "PASS" if passed else "FAIL"

        actual_direction = (
            insight.direction
            if insight is not None
            else None
        )

        print(
            f"ANOMALY {expected['segment']} "
            f"{expected['period']}: "
            f"expectedDirection="
            f"{expected['expectedDirection']}, "
            f"actualDirection={actual_direction}, "
            f"{status}"
        )

        if not passed:
            failed_checks.append(
                f"ANOMALY {expected['segment']}"
            )

    print("=" * 72)

    if failed_checks:
        print("RESULT: DAY 5 CHECKS FAILED")
    else:
        print(
            "RESULT: ALL DAY 5 REQUIRED CHECKS PASSED"
        )

    print("=" * 72)

    assert failed_checks == []