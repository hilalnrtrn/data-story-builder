import json
from pathlib import Path

from app.services.contrast_detector import (
    detect_top_bottom_contrast,
)
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


def test_day6_contrast_golden_truth():
    golden = _load_json(GOLDEN_TRUTH_PATH)
    metadata = _load_json(DATASET_METADATA_PATH)
    dataframe = _load_prepared_clean_dataset()

    failed_checks = []

    print()
    print("=" * 72)
    print("DAY 6 CONTRAST GOLDEN TRUTH CHECK")
    print("=" * 72)

    for expected in golden["expectedContrasts"]:
        metric = expected["metric"]
        aggregation = metadata["columns"][metric][
            "aggregation"
        ]

        insight = detect_top_bottom_contrast(
            dataframe,
            analysis_id="DAY6-CONTRAST-GOLDEN",
            file_name=SAMPLE_DATA_PATH.name,
            metric=metric,
            dimension=expected["dimension"],
            aggregation=aggregation,
            previous_period=expected["previousPeriod"],
            current_period=expected["currentPeriod"],
        )

        expected_difference = (
            expected["expectedSubjectChangePercent"]
            - expected["expectedComparisonChangePercent"]
        )
        passed = insight is not None

        if passed:
            tolerance = expected["tolerance"]

            passed = (
                insight.type == "CONTRAST"
                and insight.metric == metric
                and insight.dimension == expected["dimension"]
                and insight.period["previous"]
                == expected["previousPeriod"]
                and insight.period["current"]
                == expected["currentPeriod"]
                and insight.values["subject"]
                == expected["subject"]
                and insight.values["comparison"]
                == expected["comparison"]
                and abs(
                    insight.values["subjectChangePercent"]
                    - expected[
                        "expectedSubjectChangePercent"
                    ]
                )
                <= tolerance
                and abs(
                    insight.values["comparisonChangePercent"]
                    - expected[
                        "expectedComparisonChangePercent"
                    ]
                )
                <= tolerance
                and abs(
                    insight.values[
                        "differencePercentagePoints"
                    ]
                    - expected_difference
                )
                <= tolerance
                and insight.values["comparisonResult"]
                == expected["expectedDirection"]
            )

        actual_values = (
            insight.values
            if insight is not None
            else {}
        )

        print(
            f"CONTRAST {metric} / "
            f"{expected['dimension']}"
        )
        print(
            "subject: "
            f"expected={expected['subject']} "
            f"actual={actual_values.get('subject')}"
        )
        print(
            "comparison: "
            f"expected={expected['comparison']} "
            f"actual={actual_values.get('comparison')}"
        )
        print(
            "subjectChange: "
            "expected="
            f"{expected['expectedSubjectChangePercent']} "
            "actual="
            f"{actual_values.get('subjectChangePercent')}"
        )
        print(
            "comparisonChange: "
            "expected="
            f"{expected['expectedComparisonChangePercent']} "
            "actual="
            f"{actual_values.get('comparisonChangePercent')}"
        )
        print(
            "differencePP: "
            f"expected={expected_difference} "
            "actual="
            f"{actual_values.get('differencePercentagePoints')}"
        )
        print(
            "result: "
            f"expected={expected['expectedDirection']} "
            "actual="
            f"{actual_values.get('comparisonResult')}"
        )
        print("PASS" if passed else "FAIL")

        if not passed:
            failed_checks.append(expected["id"])

    print("=" * 72)

    if failed_checks:
        print("RESULT: DAY 6 CONTRAST GOLDEN CHECKS FAILED")
    else:
        print(
            "RESULT: ALL DAY 6 CONTRAST "
            "GOLDEN CHECKS PASSED"
        )

    print("=" * 72)

    assert failed_checks == []
