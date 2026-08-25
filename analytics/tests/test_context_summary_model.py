import pytest
from pydantic import ValidationError

from app.models.context_summary import (
    ContextStatement,
    KnownUnknownContextResult,
    KnownUnknownContextSummary,
)


def test_context_statement_accepts_valid_values():
    statement = ContextStatement(
        code="CAUSALITY_NOT_ESTABLISHED",
        statement="The available evidence does not establish causality.",
    )

    assert statement.code == "CAUSALITY_NOT_ESTABLISHED"
    assert statement.statement == (
        "The available evidence does not establish causality."
    )


@pytest.mark.parametrize("code", ["", "   ", "\t", " \n"])
def test_context_statement_rejects_blank_code(code):
    with pytest.raises(ValidationError):
        ContextStatement(code=code, statement="Valid context statement.")


@pytest.mark.parametrize("statement", ["", "   ", "\t", " \n"])
def test_context_statement_rejects_blank_statement(statement):
    with pytest.raises(ValidationError):
        ContextStatement(
            code="COMPETITOR_PRICE_UNAVAILABLE",
            statement=statement,
        )


def test_known_unknown_summary_accepts_camel_case_aliases():
    summary = KnownUnknownContextSummary(
        insightId="CHANGE-Revenue-2025-05-2025-06",
        known=[
            ContextStatement(
                code="CAUSALITY_NOT_ESTABLISHED",
                statement=(
                    "The available evidence does not establish causality."
                ),
            )
        ],
        unknown=[
            ContextStatement(
                code="COMPETITOR_PRICE_UNAVAILABLE",
                statement="CompetitorPrice context is unavailable.",
            )
        ],
        interpretationLimited=True,
    )

    assert summary.model_dump(by_alias=True) == {
        "insightId": "CHANGE-Revenue-2025-05-2025-06",
        "known": [
            {
                "code": "CAUSALITY_NOT_ESTABLISHED",
                "statement": (
                    "The available evidence does not establish causality."
                ),
            }
        ],
        "unknown": [
            {
                "code": "COMPETITOR_PRICE_UNAVAILABLE",
                "statement": "CompetitorPrice context is unavailable.",
            }
        ],
        "interpretationLimited": True,
    }


def test_known_and_unknown_default_to_empty_lists():
    summary = KnownUnknownContextSummary(
        insightId="CHANGE-Revenue-2025-05-2025-06",
        interpretationLimited=False,
    )

    assert summary.known == []
    assert summary.unknown == []


def test_interpretation_limited_is_required():
    with pytest.raises(ValidationError):
        KnownUnknownContextSummary(
            insightId="CHANGE-Revenue-2025-05-2025-06"
        )


@pytest.mark.parametrize("insight_id", ["", "   ", "\t", " \n"])
def test_known_unknown_summary_rejects_blank_insight_id(insight_id):
    with pytest.raises(ValidationError):
        KnownUnknownContextSummary(
            insightId=insight_id,
            interpretationLimited=True,
        )


def test_context_result_summaries_default_is_empty():
    assert KnownUnknownContextResult().summaries == []
