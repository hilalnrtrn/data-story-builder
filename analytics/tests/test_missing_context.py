from copy import deepcopy

from app.config.insight_config_loader import load_insight_config
from app.config.metadata_loader import load_dataset_metadata
from app.models.insight import (
    Insight,
    InsightDirection,
    InsightType,
    PeriodGranularity,
)
from app.services.missing_context import evaluate_missing_context


EXPECTED_REVENUE_REQUIREMENTS = [
    (
        "CompetitorPrice",
        "Competitor pricing may affect interpretation of Revenue movements.",
    ),
    (
        "UnitPrice",
        (
            "AverageOrderValue growth does not establish that individual "
            "selling prices increased."
        ),
    ),
    (
        "PricingChange",
        "Explicit pricing policy changes are unavailable.",
    ),
]


def _insight(**overrides) -> Insight:
    values = {
        "id": "CHANGE-Revenue-2025-05-2025-06",
        "analysisId": "ANALYSIS-001",
        "type": InsightType.CHANGE,
        "metric": "Revenue",
        "periodGranularity": PeriodGranularity.MONTH,
        "period": {"previous": "2025-05", "current": "2025-06"},
        "direction": InsightDirection.UP,
    }
    values.update(overrides)
    return Insight(**values)


def _config_with_requirements(metric: str, fields: list[str]) -> dict:
    return {
        "missingContext": {
            "requirementsByMetric": {
                metric: [
                    {
                        "field": field,
                        "reason": f"{field} context is required.",
                    }
                    for field in fields
                ]
            }
        }
    }


def test_revenue_detects_exact_golden_missing_context_in_config_order():
    evaluation = evaluate_missing_context(
        _insight(),
        load_dataset_metadata(),
    )

    assert [item.field for item in evaluation.missing_context] == [
        field for field, _ in EXPECTED_REVENUE_REQUIREMENTS
    ]
    assert [item.reason for item in evaluation.missing_context] == [
        reason for _, reason in EXPECTED_REVENUE_REQUIREMENTS
    ]
    assert all(
        item.status == "NOT_AVAILABLE"
        for item in evaluation.missing_context
    )
    assert all(
        item.is_data_quality_error is False
        for item in evaluation.missing_context
    )
    assert evaluation.interpretation_limited is True
    assert evaluation.reasons == [
        "Interpretation is limited by unavailable context."
    ]


def test_available_column_is_removed_from_missing_context():
    metadata = load_dataset_metadata()
    metadata["columns"]["CompetitorPrice"] = {}

    evaluation = evaluate_missing_context(_insight(), metadata)

    assert [item.field for item in evaluation.missing_context] == [
        "UnitPrice",
        "PricingChange",
    ]


def test_all_available_requirements_do_not_limit_interpretation():
    metadata = load_dataset_metadata()
    for field, _ in EXPECTED_REVENUE_REQUIREMENTS:
        metadata["columns"][field] = {}

    evaluation = evaluate_missing_context(_insight(), metadata)

    assert evaluation.missing_context == []
    assert evaluation.interpretation_limited is False
    assert evaluation.reasons == []


def test_metric_without_requirements_has_no_missing_context():
    evaluation = evaluate_missing_context(
        _insight(metric="MarketingSpend"),
        load_dataset_metadata(),
    )

    assert evaluation.missing_context == []
    assert evaluation.interpretation_limited is False


def test_nullable_existing_column_counts_as_available():
    evaluation = evaluate_missing_context(
        _insight(metric="StockLevel"),
        load_dataset_metadata(),
        config=_config_with_requirements("StockLevel", ["StockLevel"]),
    )

    assert evaluation.missing_context == []
    assert evaluation.interpretation_limited is False


def test_derived_metric_key_counts_as_available():
    evaluation = evaluate_missing_context(
        _insight(metric="ReturnRate"),
        load_dataset_metadata(),
        config=_config_with_requirements("ReturnRate", ["ReturnRate"]),
    )

    assert evaluation.missing_context == []
    assert evaluation.interpretation_limited is False


def test_evaluation_does_not_mutate_supplied_metadata_or_config():
    metadata = load_dataset_metadata()
    config = load_insight_config()
    metadata_before = deepcopy(metadata)
    config_before = deepcopy(config)

    evaluate_missing_context(_insight(), metadata, config=config)

    assert metadata == metadata_before
    assert config == config_before
