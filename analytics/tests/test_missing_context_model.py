import pytest
from pydantic import ValidationError

from app.models.missing_context import (
    MissingContextEvaluation,
    MissingContextItem,
    MissingContextResult,
    MissingContextStatus,
)


def _competitor_price_item(**overrides) -> MissingContextItem:
    values = {
        "field": "CompetitorPrice",
        "status": MissingContextStatus.NOT_AVAILABLE,
        "isDataQualityError": False,
        "reason": (
            "Competitor pricing may affect interpretation of Revenue "
            "movements."
        ),
    }
    values.update(overrides)
    return MissingContextItem(**values)


def test_missing_context_item_accepts_golden_scenario_values():
    item = _competitor_price_item()

    assert item.field == "CompetitorPrice"
    assert item.status == "NOT_AVAILABLE"
    assert item.is_data_quality_error is False


def test_missing_context_item_serializes_with_camel_case_aliases():
    assert _competitor_price_item().model_dump(by_alias=True) == {
        "field": "CompetitorPrice",
        "status": "NOT_AVAILABLE",
        "isDataQualityError": False,
        "reason": (
            "Competitor pricing may affect interpretation of Revenue "
            "movements."
        ),
    }


def test_missing_context_status_has_exact_controlled_value():
    assert [status.value for status in MissingContextStatus] == [
        "NOT_AVAILABLE"
    ]


@pytest.mark.parametrize("invalid_field", ["", "   ", "\t", " \n"])
def test_missing_context_item_rejects_blank_field(invalid_field):
    with pytest.raises(ValidationError):
        _competitor_price_item(field=invalid_field)


@pytest.mark.parametrize("invalid_reason", ["", "   ", "\t", " \n"])
def test_missing_context_item_rejects_blank_reason(invalid_reason):
    with pytest.raises(ValidationError):
        _competitor_price_item(reason=invalid_reason)


def test_missing_context_evaluation_accepts_camel_case_aliases():
    evaluation = MissingContextEvaluation(
        insightId="CHANGE-Revenue-2025-05-2025-06",
        missingContext=[
            _competitor_price_item(),
            _competitor_price_item(
                field="UnitPrice",
                reason=(
                    "AverageOrderValue growth does not establish that "
                    "individual selling prices increased."
                ),
            ),
            _competitor_price_item(
                field="PricingChange",
                reason="Explicit pricing policy changes are unavailable.",
            ),
        ],
        interpretationLimited=True,
        reasons=["External pricing context is not available."],
    )

    serialized = evaluation.model_dump(by_alias=True)
    assert serialized["insightId"] == "CHANGE-Revenue-2025-05-2025-06"
    assert [item["field"] for item in serialized["missingContext"]] == [
        "CompetitorPrice",
        "UnitPrice",
        "PricingChange",
    ]
    assert serialized["interpretationLimited"] is True


def test_missing_context_evaluation_requires_insight_id():
    with pytest.raises(ValidationError):
        MissingContextEvaluation(interpretationLimited=True)


@pytest.mark.parametrize("insight_id", ["", "   ", "\t", " \n"])
def test_missing_context_evaluation_rejects_blank_insight_id(insight_id):
    with pytest.raises(ValidationError):
        MissingContextEvaluation(
            insightId=insight_id,
            interpretationLimited=True,
        )


def test_missing_context_result_evaluations_default_is_empty():
    assert MissingContextResult().evaluations == []
