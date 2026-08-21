from __future__ import annotations

import csv
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

CLEAN_CSV_PATH = (
    PROJECT_ROOT
    / "sample-data"
    / "sales_demo_clean.csv"
)

DIRTY_CSV_PATH = (
    PROJECT_ROOT
    / "sample-data"
    / "sales_demo_dirty.csv"
)

GOLDEN_TRUTH_PATH = (
    PROJECT_ROOT
    / "tests"
    / "golden"
    / "expected_results.json"
)


def load_clean_dataset() -> list[dict]:
    """
    Loads the exported clean CSV from disk.
    Numeric values are converted back to useful Python types.
    """

    rows = []

    with CLEAN_CSV_PATH.open(
        mode="r",
        newline="",
        encoding="utf-8-sig",
    ) as csv_file:

        reader = csv.DictReader(csv_file)

        for row in reader:

            row["Revenue"] = float(row["Revenue"])
            row["Orders"] = int(row["Orders"])
            row["Customers"] = int(row["Customers"])
            row["Quantity"] = int(row["Quantity"])

            row["MarketingSpend"] = float(
                row["MarketingSpend"]
            )

            row["StockLevel"] = int(
                row["StockLevel"]
            )

            row["Discount"] = float(
                row["Discount"]
            )

            row["Returns"] = int(
                row["Returns"]
            )

            rows.append(row)

    return rows

def load_dirty_dataset_raw() -> list[dict]:
    """
    Loads dirty CSV without converting values.

    Raw strings are intentionally preserved because several
    controlled issues are format-related.
    """

    with DIRTY_CSV_PATH.open(
        mode="r",
        newline="",
        encoding="utf-8-sig",
    ) as csv_file:

        return list(
            csv.DictReader(csv_file)
        )

def validate_dirty_dataset_against_golden(
    dirty_rows: list[dict],
    golden_truth: dict,
) -> None:
    """
    Independently validates dirty CSV issue counts against
    expected_results.json.
    """

    expected = golden_truth[
        "expectedDataQualityIssues"
    ]

    stock_missing = sum(
        1
        for row in dirty_rows
        if row["StockLevel"] == ""
    )

    region_normalization = sum(
        1
        for row in dirty_rows
        if row["Region"] not in {
            "Marmara",
            "Ege",
            "İç Anadolu",
            "Akdeniz",
            "Karadeniz",
        }
        and any(
            row["Region"].casefold()
            == valid.casefold()
            for valid in [
                "Marmara",
                "Ege",
                "İç Anadolu",
                "Akdeniz",
                "Karadeniz",
            ]
        )
    )

    product_whitespace = sum(
        1
        for row in dirty_rows
        if row["Product"]
        != row["Product"].strip()
    )

    canonical_product_categories = {
        "Wireless Headphones": "Electronics",
        "Smart Watch": "Electronics",
        "Bluetooth Speaker": "Electronics",
        "Power Bank": "Electronics",
        "Coffee Machine": "Home",
        "Air Fryer": "Home",
        "Vacuum Cleaner": "Home",
        "Desk Lamp": "Home",
        "Office Chair": "Office",
        "Mechanical Keyboard": "Office",
        "Monitor Stand": "Office",
        "Webcam": "Office",
    }

    invalid_mapping = sum(
        1
        for row in dirty_rows
        if row["Product"] in canonical_product_categories
        and row["Category"]
        != canonical_product_categories[row["Product"]]
    )

    invalid_discount = sum(
        1
        for row in dirty_rows
        if float(row["Discount"]) > 0.50
    )

    negative_orders = sum(
        1
        for row in dirty_rows
        if int(row["Orders"]) < 0
    )

    invalid_returns = sum(
        1
        for row in dirty_rows
        if int(row["Returns"])
        > int(row["Quantity"])
    )

    invalid_dates = sum(
        1
        for row in dirty_rows
        if row["Date"] in {
            "not-a-date",
            "2025-13-04",
        }
    )

    numeric_format = sum(
        1
        for row in dirty_rows
        if "," in row["MarketingSpend"]
    )

    grain_keys = [
        (
            row["Date"],
            row["Region"],
            row["Product"],
            row["Channel"],
        )
        for row in dirty_rows
    ]

    duplicate_rows = (
        len(grain_keys)
        - len(set(grain_keys))
    )

    actual = {
        "duplicateRows": duplicate_rows,
        "regionNormalizationIssues": region_normalization,
        "productWhitespaceIssues": product_whitespace,
        "invalidProductCategoryMappings": invalid_mapping,
        "stockLevelMissingValues": stock_missing,
        "invalidDiscountValues": invalid_discount,
        "negativeOrderValues": negative_orders,
        "returnsGreaterThanQuantity": invalid_returns,
        "invalidDateValues": invalid_dates,
        "numericFormatIssues": numeric_format,
    }

    print()
    print("9. Dirty Dataset vs Golden Truth")
    print("--------------------------------")

    for key, expected_count in expected.items():

        actual_count = actual[key]

        assert actual_count == expected_count, (
            f"{key}: "
            f"{actual_count} != {expected_count}"
        )

        print(
            f"{key:<32}"
            f"{actual_count:>3}  PASSED"
        )


def load_golden_truth() -> dict:
    """
    Loads the expected Day 1 Golden Truth specification.
    """

    with GOLDEN_TRUTH_PATH.open(
        mode="r",
        encoding="utf-8",
    ) as json_file:

        return json.load(json_file)

def find_by_id(
    items: list[dict],
    item_id: str,
) -> dict:
    """
    Finds one Golden Truth item by its stable ID.
    """

    for item in items:
        if item.get("id") == item_id:
            return item

    raise AssertionError(
        f"Golden Truth item not found: {item_id}"
    )


def monthly_total(
    rows: list[dict],
    month: str,
    metric: str,
) -> float:

    return sum(
        row[metric]
        for row in rows
        if row["Date"].startswith(month)
    )


def monthly_dimension_total(
    rows: list[dict],
    month: str,
    metric: str,
    dimension: str,
    dimension_value: str,
) -> float:

    return sum(
        row[metric]
        for row in rows
        if row["Date"].startswith(month)
        and row[dimension] == dimension_value
    )


def percentage_change(
    previous: float,
    current: float,
) -> float:

    assert previous != 0

    return (
        (current - previous)
        / previous
    )

def validate_main_change_scenario(
    rows: list[dict],
    golden_truth: dict,
) -> None:
    """
    Validates required CHANGE insights directly against
    expected_results.json.
    """

    print()
    print("1. Required Change Insights")
    print("---------------------------")

    for expected in golden_truth["requiredInsights"]:

        if expected["type"] != "CHANGE":
            continue

        metric = expected["metric"]
        previous_period = expected["previousPeriod"]
        current_period = expected["currentPeriod"]

        previous_value = monthly_total(
            rows,
            previous_period,
            metric,
        )

        current_value = monthly_total(
            rows,
            current_period,
            metric,
        )

        actual_percentage_change = (
            percentage_change(
                previous_value,
                current_value,
            )
            * 100
        )

        tolerance = expected["tolerance"]

        assert abs(
            previous_value
            - expected["expectedPreviousValue"]
        ) <= tolerance, (
            f"{metric} previous value mismatch."
        )

        assert abs(
            current_value
            - expected["expectedCurrentValue"]
        ) <= tolerance, (
            f"{metric} current value mismatch."
        )

        assert abs(
            actual_percentage_change
            - expected["expectedPercentageChange"]
        ) <= tolerance, (
            f"{metric} percentage change mismatch: "
            f"{actual_percentage_change} != "
            f"{expected['expectedPercentageChange']}"
        )

        print(
            f"{metric:<18}"
            f"{actual_percentage_change:>8.2f}%  PASSED"
        )

def validate_contribution_scenario(
    rows: list[dict],
    golden_truth: dict,
) -> None:

    expected = find_by_id(
        golden_truth["expectedContributions"],
        "GT-CON-001",
    )

    metric = expected["metric"]
    dimension = expected["dimension"]
    segment = expected["segment"]

    previous_period = expected["previousPeriod"]
    current_period = expected["currentPeriod"]

    previous_total = monthly_total(
        rows,
        previous_period,
        metric,
    )

    current_total = monthly_total(
        rows,
        current_period,
        metric,
    )

    previous_segment = monthly_dimension_total(
        rows,
        previous_period,
        metric,
        dimension,
        segment,
    )

    current_segment = monthly_dimension_total(
        rows,
        current_period,
        metric,
        dimension,
        segment,
    )

    total_change = current_total - previous_total
    segment_change = current_segment - previous_segment

    contribution = segment_change / total_change

    assert abs(
        contribution
        - expected["expectedContributionShare"]
    ) <= expected["tolerance"]

    assert abs(
        previous_segment
        - expected["segmentPreviousValue"]
    ) <= expected["tolerance"]

    assert abs(
        current_segment
        - expected["segmentCurrentValue"]
    ) <= expected["tolerance"]

    print()
    print("2. Contribution Scenario")
    print("------------------------")
    print(
        f"{segment} contribution: "
        f"{contribution * 100:.2f}%  PASSED"
    )

def validate_smart_watch_scenario(
    rows: list[dict],
) -> None:

    may_revenue = monthly_dimension_total(
        rows,
        "2025-05",
        "Revenue",
        "Product",
        "Smart Watch",
    )

    june_revenue = monthly_dimension_total(
        rows,
        "2025-06",
        "Revenue",
        "Product",
        "Smart Watch",
    )

    assert abs(
        may_revenue - 73_000
    ) <= 0.01

    assert abs(
        june_revenue - 145_000
    ) <= 0.01

    change = percentage_change(
        may_revenue,
        june_revenue,
    )

    print()
    print("3. Smart Watch Scenario")
    print("-----------------------")

    print(
        f"May Revenue:  {may_revenue:,.2f}"
    )

    print(
        f"June Revenue: {june_revenue:,.2f}"
    )

    print(
        f"Change:       {change * 100:.2f}%  PASSED"
    )

def validate_trend_scenario(
    rows: list[dict],
    golden_truth: dict,
) -> None:
    """
    Validates that the controlled Office Chair trend pattern
    required by Golden Truth exists in the exported dataset.

    This does NOT execute the future Trend Engine.
    """

    expected = find_by_id(
        golden_truth["expectedTrends"],
        "GT-TREND-001",
    )

    product = expected["segment"]

    monthly_values = []

    for month_number in range(1, 13):

        month = f"2025-{month_number:02d}"

        value = monthly_dimension_total(
            rows,
            month,
            expected["metric"],
            expected["dimension"],
            product,
        )

        monthly_values.append(value)

    if expected["expectedMonotonicMovement"]:
        assert all(
            current > previous
            for previous, current in zip(
                monthly_values,
                monthly_values[1:],
            )
        ), (
            "Office Chair controlled upward trend "
            "is not monotonic."
        )

    assert monthly_values[-1] > monthly_values[0]

    print()
    print("4. Trend Scenario")
    print("-----------------")
    print(
        f"{product}: "
        f"{monthly_values[0]:,.2f} -> "
        f"{monthly_values[-1]:,.2f}"
    )
    print("Monotonic upward pattern: PASSED")

def validate_outlier_scenario(
    rows: list[dict],
    golden_truth: dict,
) -> None:
    """
    Validates the deliberately inserted Bluetooth Speaker
    September outlier pattern.

    This does NOT run the future Outlier Integrity algorithm.
    """

    expected = find_by_id(
        golden_truth["expectedIntegrityFindings"],
        "GT-INT-001",
    )

    product = expected["segment"]
    outlier_period = expected["expectedOutlierPeriod"]

    monthly_values = {}

    for month_number in range(1, 13):

        month = f"2025-{month_number:02d}"

        monthly_values[month] = monthly_dimension_total(
            rows,
            month,
            expected["metric"],
            expected["dimension"],
            product,
        )

    outlier_value = monthly_values[outlier_period]

    non_outlier_values = [
        value
        for month, value in monthly_values.items()
        if month != outlier_period
    ]

    normal_max = max(non_outlier_values)

    assert outlier_value > normal_max * 2, (
        "Controlled Bluetooth Speaker outlier "
        "is not sufficiently separated from baseline."
    )

    print()
    print("5. Outlier Scenario")
    print("-------------------")
    print(
        f"{product} {outlier_period}: "
        f"{outlier_value:,.2f}"
    )
    print(
        f"Highest non-outlier month: "
        f"{normal_max:,.2f}"
    )
    print("Controlled outlier pattern: PASSED")

def validate_missing_context(
    rows: list[dict],
    golden_truth: dict,
) -> None:
    """
    Validates that intentionally unavailable context fields
    are actually absent from the dataset schema.
    """

    actual_columns = set(rows[0].keys())

    print()
    print("6. Missing Context")
    print("------------------")

    for expected in golden_truth["expectedMissingContext"]:

        field = expected["field"]

        assert field not in actual_columns, (
            f"{field} should be intentionally unavailable."
        )

        assert (
            expected["expectedStatus"]
            == "NOT_AVAILABLE"
        )

        assert (
            expected["isDataQualityError"]
            is False
        )

        print(
            f"{field:<20} NOT_AVAILABLE  PASSED"
        )

def validate_derived_metrics(
    rows: list[dict],
) -> None:

    tolerance = 0.05

    may_revenue = monthly_total(
        rows,
        "2025-05",
        "Revenue",
    )

    june_revenue = monthly_total(
        rows,
        "2025-06",
        "Revenue",
    )

    may_orders = monthly_total(
        rows,
        "2025-05",
        "Orders",
    )

    june_orders = monthly_total(
        rows,
        "2025-06",
        "Orders",
    )

    may_customers = monthly_total(
        rows,
        "2025-05",
        "Customers",
    )

    june_customers = monthly_total(
        rows,
        "2025-06",
        "Customers",
    )

    may_aov = may_revenue / may_orders
    june_aov = june_revenue / june_orders

    aov_change = percentage_change(
        may_aov,
        june_aov,
    )

    may_rpc = (
        may_revenue / may_customers
    )

    june_rpc = (
        june_revenue / june_customers
    )

    rpc_change = percentage_change(
        may_rpc,
        june_rpc,
    )

    assert abs(may_aov - 100.00) <= tolerance
    assert abs(june_aov - 152.94) <= tolerance
    assert abs(aov_change - 0.5294) <= tolerance

    assert abs(may_rpc - 125.00) <= tolerance
    assert abs(june_rpc - 184.66) <= tolerance
    assert abs(rpc_change - 0.4773) <= tolerance

    print()
    print("7. Derived Metrics")
    print("------------------")

    print(
        f"AOV: "
        f"{may_aov:.2f} -> {june_aov:.2f} "
        f"({aov_change * 100:+.2f}%)  PASSED"
    )

    print(
        f"Revenue/Customer: "
        f"{may_rpc:.2f} -> {june_rpc:.2f} "
        f"({rpc_change * 100:+.2f}%)  PASSED"
    )

def validate_business_relevance_scenario(
    rows: list[dict],
) -> None:

    def average_discount(month: str) -> float:

        values = [
            row["Discount"]
            for row in rows
            if row["Date"].startswith(month)
        ]

        return sum(values) / len(values)

    def return_rate(month: str) -> float:

        returns = monthly_total(
            rows,
            month,
            "Returns",
        )

        quantity = monthly_total(
            rows,
            month,
            "Quantity",
        )

        return returns / quantity

    august_discount = average_discount(
        "2025-08"
    )

    september_discount = average_discount(
        "2025-09"
    )

    august_return_rate = return_rate(
        "2025-08"
    )

    september_return_rate = return_rate(
        "2025-09"
    )

    assert abs(
        august_discount - 0.10
    ) <= 0.0001

    assert abs(
        september_discount - 0.18
    ) <= 0.0001

    assert abs(
        august_return_rate - 0.02
    ) <= 0.0001

    assert abs(
        september_return_rate - 0.035
    ) <= 0.0001

    print()
    print("8. Business Relevance Scenario")
    print("------------------------------")

    print(
        "Discount:    "
        f"{august_discount * 100:.2f}% "
        f"-> {september_discount * 100:.2f}%  PASSED"
    )

    print(
        "Return Rate: "
        f"{august_return_rate * 100:.2f}% "
        f"-> {september_return_rate * 100:.2f}%  PASSED"
    )

def validate_golden_truth_file(
    golden_truth: dict,
) -> None:

    required_sections = [
        "dataset",
        "datasetExpectations",
        "requiredInsights",
        "expectedDerivedMetrics",
        "expectedContributions",
        "expectedContrasts",
        "expectedTrends",
        "expectedAnomalies",
        "expectedRelationships",
        "expectedCounterEvidence",
        "expectedIntegrityFindings",
        "expectedCausalityChecks",
        "expectedMissingContext",
        "expectedBusinessRanking",
        "allowedInsights",
        "forbiddenClaims",
        "expectedDataQualityIssues",
    ]

    for section in required_sections:
        assert section in golden_truth, (
            f"Golden Truth section missing: {section}"
        )

    print()
    print("Golden Truth file:      LOADED")
    print("Golden Truth structure: PASSED")

def main() -> None:

    print(
        "Data Story Builder — "
        "Independent Golden Validation"
    )

    print(
        "-------------------------------------------"
    )

    rows = load_clean_dataset()
    golden_truth = load_golden_truth()

    print(
        f"Loaded clean rows:      {len(rows):,}"
    )

    validate_golden_truth_file(
        golden_truth
    )

    validate_main_change_scenario(
        rows,
        golden_truth,
    )

    validate_contribution_scenario(
        rows,
        golden_truth,
    )

    validate_smart_watch_scenario(
        rows
    )

    validate_trend_scenario(
        rows,
        golden_truth,
    )

    validate_outlier_scenario(
        rows,
        golden_truth,
    )

    validate_missing_context(
        rows,
        golden_truth,
    )

    dirty_rows = load_dirty_dataset_raw()

    validate_derived_metrics(
        rows
    )

    validate_business_relevance_scenario(
        rows
    )

    validate_dirty_dataset_against_golden(
        dirty_rows,
        golden_truth,
    )

    print()
    print(
        "==========================================="
    )

    print(
        "INDEPENDENT GOLDEN VALIDATION: PASSED"
    )

    print(
        "==========================================="
    )


if __name__ == "__main__":
    main()