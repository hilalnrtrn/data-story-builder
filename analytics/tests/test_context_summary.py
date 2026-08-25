from copy import deepcopy

from app.models.causality import CausalityEvaluation, CausalityStatus
from app.models.insight import (
    Insight,
    InsightDirection,
    InsightType,
    PeriodGranularity,
)
from app.models.missing_context import (
    MissingContextEvaluation,
    MissingContextItem,
    MissingContextStatus,
)
from app.services.context_summary import build_known_unknown_summary


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


def _causality_evaluation(**overrides) -> CausalityEvaluation:
    values = {
        "sourceInsightId": "CHANGE-MarketingSpend-2025-05-2025-06",
        "targetInsightId": "CHANGE-Revenue-2025-05-2025-06",
        "relationshipId": "CO_MOVES_WITH-MARKETINGSPEND-REVENUE",
        "sourceMetric": "MarketingSpend",
        "targetMetric": "Revenue",
        "associationPresent": True,
        "causalityEstablished": False,
        "status": CausalityStatus.CAUSALITY_NOT_ESTABLISHED,
    }
    values.update(overrides)
    return CausalityEvaluation(**values)


def _missing_context(**overrides) -> MissingContextEvaluation:
    values = {
        "insightId": "CHANGE-Revenue-2025-05-2025-06",
        "missingContext": [
            MissingContextItem(
                field="CompetitorPrice",
                status=MissingContextStatus.NOT_AVAILABLE,
                isDataQualityError=False,
                reason="Competitor pricing context is unavailable.",
            ),
            MissingContextItem(
                field="UnitPrice",
                status=MissingContextStatus.NOT_AVAILABLE,
                isDataQualityError=False,
                reason="Unit price context is unavailable.",
            ),
            MissingContextItem(
                field="PricingChange",
                status=MissingContextStatus.NOT_AVAILABLE,
                isDataQualityError=False,
                reason="Pricing change context is unavailable.",
            ),
        ],
        "interpretationLimited": True,
    }
    values.update(overrides)
    return MissingContextEvaluation(**values)


def test_insight_always_yields_observed_known_statement():
    summary = build_known_unknown_summary(_insight(), [])

    assert [(item.code, item.statement) for item in summary.known] == [
        (
            "INSIGHT_OBSERVED",
            "The insight for Revenue is an observed analytical finding.",
        )
    ]
    assert summary.interpretation_limited is False


def test_relevant_association_and_causality_limitation_are_summarized():
    summary = build_known_unknown_summary(
        _insight(),
        [_causality_evaluation()],
    )

    assert [item.code for item in summary.known] == [
        "INSIGHT_OBSERVED",
        "ASSOCIATION_PRESENT",
    ]
    assert summary.known[1].statement == (
        "Association evidence is present between MarketingSpend and Revenue."
    )
    assert [(item.code, item.statement) for item in summary.unknown] == [
        (
            "CAUSALITY_NOT_ESTABLISHED",
            "Causality between MarketingSpend and Revenue is not established.",
        )
    ]
    assert summary.interpretation_limited is True


def test_unrelated_causality_evaluation_is_ignored():
    summary = build_known_unknown_summary(
        _insight(),
        [
            _causality_evaluation(
                sourceInsightId="CHANGE-Orders-2025-05-2025-06",
                targetInsightId="CHANGE-Customers-2025-05-2025-06",
            )
        ],
    )

    assert [item.code for item in summary.known] == ["INSIGHT_OBSERVED"]
    assert summary.unknown == []
    assert summary.interpretation_limited is False


def test_established_causality_does_not_produce_causality_unknown():
    summary = build_known_unknown_summary(
        _insight(),
        [
            _causality_evaluation(
                causalityEstablished=True,
                status=CausalityStatus.CAUSALITY_ESTABLISHED,
            )
        ],
    )

    assert [item.code for item in summary.known] == [
        "INSIGHT_OBSERVED",
        "ASSOCIATION_PRESENT",
    ]
    assert summary.unknown == []
    assert summary.interpretation_limited is False


def test_missing_context_creates_ordered_unknown_statements():
    summary = build_known_unknown_summary(
        _insight(),
        [],
        missing_context_evaluation=_missing_context(),
    )

    assert [item.code for item in summary.unknown] == [
        "COMPETITORPRICE_UNAVAILABLE",
        "UNITPRICE_UNAVAILABLE",
        "PRICINGCHANGE_UNAVAILABLE",
    ]
    assert [item.statement for item in summary.unknown] == [
        "CompetitorPrice is unavailable as contextual information.",
        "UnitPrice is unavailable as contextual information.",
        "PricingChange is unavailable as contextual information.",
    ]
    assert summary.interpretation_limited is True


def test_missing_context_for_another_insight_is_ignored():
    summary = build_known_unknown_summary(
        _insight(),
        [],
        missing_context_evaluation=_missing_context(insightId="OTHER-INSIGHT"),
    )

    assert summary.unknown == []
    assert summary.interpretation_limited is False


def test_equivalent_causality_evaluations_are_not_duplicated():
    summary = build_known_unknown_summary(
        _insight(),
        [
            _causality_evaluation(),
            _causality_evaluation(relationshipId="RELATIONSHIP-002"),
        ],
    )

    assert [item.code for item in summary.known].count(
        "ASSOCIATION_PRESENT"
    ) == 1
    assert [item.code for item in summary.unknown].count(
        "CAUSALITY_NOT_ESTABLISHED"
    ) == 1


def test_matching_context_limitation_is_preserved_without_unknown_items():
    summary = build_known_unknown_summary(
        _insight(),
        [],
        missing_context_evaluation=_missing_context(
            missingContext=[],
            interpretationLimited=True,
        ),
    )

    assert summary.unknown == []
    assert summary.interpretation_limited is True


def test_summary_builder_does_not_mutate_inputs():
    insight = _insight()
    causality_evaluations = [_causality_evaluation()]
    missing_context = _missing_context()
    insight_before = insight.model_dump()
    causality_before = deepcopy(causality_evaluations)
    missing_context_before = missing_context.model_dump()

    build_known_unknown_summary(
        insight,
        causality_evaluations,
        missing_context,
    )

    assert insight.model_dump() == insight_before
    assert causality_evaluations == causality_before
    assert missing_context.model_dump() == missing_context_before
