import json
from pathlib import Path

from app.services.contribution_detector import detect_contributions
from app.services.ingestion import read_dataset
from app.services.preparation import prepare_dataset


ROOT_DIR = Path(__file__).resolve().parents[2]

SAMPLE_DATA_PATH = (
    ROOT_DIR
    / "sample-data"
    / "sales_demo_clean.csv"
)

GOLDEN_TRUTH_PATH = (
    ROOT_DIR
    / "tests"
    / "golden"
    / "expected_results.json"
)

DATASET_METADATA_PATH = (
    ROOT_DIR
    / "analytics"
    / "app"
    / "config"
    / "dataset_metadata.json"
)


def _load_json(path: Path) -> dict:
    with path.open(
        "r",
        encoding="utf-8",
    ) as json_file:
        return json.load(json_file)


def _load_prepared_clean_dataset():
    dataframe = read_dataset(
        file_bytes=SAMPLE_DATA_PATH.read_bytes(),
        file_name=SAMPLE_DATA_PATH.name,
    )

    prepared_dataframe, _ = prepare_dataset(dataframe)

    return prepared_dataframe


def test_day6_contribution_golden_truth():
    golden = _load_json(GOLDEN_TRUTH_PATH)
    metadata = _load_json(DATASET_METADATA_PATH)
    dataframe = _load_prepared_clean_dataset()

    failed_checks = []

    print()
    print("=" * 72)
    print("DAY 6 CONTRIBUTION GOLDEN TRUTH CHECK")
    print("=" * 72)

    for expected in golden["expectedContributions"]:
        metric = expected["metric"]
        aggregation = metadata["columns"][metric][
            "aggregation"
        ]

        insights = detect_contributions(
            dataframe,
            analysis_id="DAY6-CONTRIBUTION-GOLDEN",
            file_name=SAMPLE_DATA_PATH.name,
            metric=metric,
            dimension=expected["dimension"],
            aggregation=aggregation,
            previous_period=expected["previousPeriod"],
            current_period=expected["currentPeriod"],
        )

        insight = next(
            (
                candidate
                for candidate in insights
                if candidate.metric == metric
                and candidate.dimension == expected["dimension"]
                and candidate.segment == expected["segment"]
                and candidate.period["previous"]
                == expected["previousPeriod"]
                and candidate.period["current"]
                == expected["currentPeriod"]
            ),
            None,
        )

        passed = insight is not None

        if passed:
            tolerance = expected["tolerance"]

            passed = (
                insight.type == "CONTRIBUTION"
                and insight.metric == metric
                and insight.dimension == expected["dimension"]
                and insight.segment == expected["segment"]
                and insight.period["previous"]
                == expected["previousPeriod"]
                and insight.period["current"]
                == expected["currentPeriod"]
                and abs(
                    insight.values["segmentPreviousValue"]
                    - expected["segmentPreviousValue"]
                )
                <= tolerance
                and abs(
                    insight.values["segmentCurrentValue"]
                    - expected["segmentCurrentValue"]
                )
                <= tolerance
                and abs(
                    insight.values["segmentAbsoluteChange"]
                    - expected["segmentAbsoluteChange"]
                )
                <= tolerance
                and abs(
                    insight.values["totalAbsoluteChange"]
                    - expected["totalAbsoluteChange"]
                )
                <= tolerance
                and abs(
                    insight.values["contributionShare"]
                    - expected["expectedContributionShare"]
                )
                <= tolerance
                and insight.values["contributorRole"]
                == expected["expectedRole"]
            )

        actual_values = (
            insight.values
            if insight is not None
            else {}
        )

        print(
            f"CONTRIBUTION {metric} / "
            f"{expected['dimension']} / "
            f"{expected['segment']}"
        )
        print(
            "segmentPrevious: "
            f"expected={expected['segmentPreviousValue']} "
            "actual="
            f"{actual_values.get('segmentPreviousValue')}"
        )
        print(
            "segmentCurrent: "
            f"expected={expected['segmentCurrentValue']} "
            "actual="
            f"{actual_values.get('segmentCurrentValue')}"
        )
        print(
            "segmentChange: "
            f"expected={expected['segmentAbsoluteChange']} "
            "actual="
            f"{actual_values.get('segmentAbsoluteChange')}"
        )
        print(
            "totalChange: "
            f"expected={expected['totalAbsoluteChange']} "
            "actual="
            f"{actual_values.get('totalAbsoluteChange')}"
        )
        print(
            "share: "
            f"expected={expected['expectedContributionShare']} "
            "actual="
            f"{actual_values.get('contributionShare')}"
        )
        print(
            "detectorRole: "
            f"{actual_values.get('contributorRole')}"
        )
        print(
            "expectedRole: "
            f"{expected['expectedRole']}"
        )
        print("PASS" if passed else "FAIL")

        if not passed:
            failed_checks.append(expected["id"])

    print("=" * 72)

    if failed_checks:
        print(
            "RESULT: DAY 6 CONTRIBUTION NUMERIC "
            "CHECKS FAILED"
        )
    else:
        print(
            "RESULT: ALL DAY 6 CONTRIBUTION "
            "GOLDEN CHECKS PASSED"
        )

    print("=" * 72)

    assert failed_checks == []
