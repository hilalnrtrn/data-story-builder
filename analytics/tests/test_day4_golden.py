import json
from pathlib import Path

from app.services.ingestion import read_dataset
from app.services.integrity import validate_integrity
from app.services.preparation import prepare_dataset
from app.services.profiler import profile_dataset


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


def _load_prepared_dirty_dataset():
    file_path = SAMPLE_DATA_DIR / "sales_demo_dirty.csv"

    dataframe = read_dataset(
        file_bytes=file_path.read_bytes(),
        file_name=file_path.name,
    )

    prepared_dataframe, _ = prepare_dataset(dataframe)

    return prepared_dataframe


def _find_column_profile(
    profile: dict,
    column_name: str,
) -> dict:
    return next(
        column
        for column in profile["columns"]
        if column["name"] == column_name
    )


def _find_integrity_finding(
    integrity: dict,
    code: str,
    column: str | None = None,
) -> dict:
    for finding in integrity["findings"]:
        if finding["code"] != code:
            continue

        if column is not None:
            if finding.get("column") != column:
                continue

        return finding

    raise AssertionError(
        f"Integrity finding not found: {code}"
    )


def test_day4_golden_truth():
    golden = _load_golden_truth()

    expected = golden["expectedDataQualityIssues"]

    prepared_dataframe = _load_prepared_dirty_dataset()

    profile = profile_dataset(prepared_dataframe)

    integrity = validate_integrity(
        prepared_dataframe
    )

    stock_level = _find_column_profile(
        profile,
        "StockLevel",
    )

    date = _find_column_profile(
        profile,
        "Date",
    )

    product_category = _find_integrity_finding(
        integrity,
        "PRODUCT_CATEGORY_INCONSISTENCY",
    )

    invalid_discount = _find_integrity_finding(
        integrity,
        "VALUE_ABOVE_MAXIMUM",
        column="Discount",
    )

    negative_orders = _find_integrity_finding(
        integrity,
        "VALUE_BELOW_MINIMUM",
        column="Orders",
    )

    returns_quantity = _find_integrity_finding(
        integrity,
        "RETURNS_NOT_GREATER_THAN_QUANTITY",
    )

    checks = {
        "stockLevelMissingValues": (
            expected["stockLevelMissingValues"],
            stock_level["missingCount"],
        ),
        "invalidDateValues": (
            expected["invalidDateValues"],
            date["missingCount"],
        ),
        "invalidProductCategoryMappings": (
            expected["invalidProductCategoryMappings"],
            product_category["affectedRowCount"],
        ),
        "invalidDiscountValues": (
            expected["invalidDiscountValues"],
            invalid_discount["affectedRowCount"],
        ),
        "negativeOrderValues": (
            expected["negativeOrderValues"],
            negative_orders["affectedRowCount"],
        ),
        "returnsGreaterThanQuantity": (
            expected["returnsGreaterThanQuantity"],
            returns_quantity["affectedRowCount"],
        ),
    }

    failed_checks = []

    print()
    print("=" * 72)
    print("DAY 4 GOLDEN TRUTH CHECK")
    print("=" * 72)

    for name, (expected_value, actual_value) in checks.items():
        passed = expected_value == actual_value

        status = "PASS" if passed else "FAIL"

        print(
            f"{name}: "
            f"expected={expected_value}, "
            f"actual={actual_value}, "
            f"{status}"
        )

        if not passed:
            failed_checks.append(name)

    print("=" * 72)

    if failed_checks:
        print(
            "RESULT: DAY 4 CHECKS FAILED"
        )
    else:
        print(
            "RESULT: ALL DAY 4 CHECKS PASSED"
        )

    print("=" * 72)

    assert failed_checks == []