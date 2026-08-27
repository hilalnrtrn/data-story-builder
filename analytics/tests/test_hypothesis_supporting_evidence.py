from copy import deepcopy

import pytest

from app.models.causality import CausalityEvaluation, CausalityStatus
from app.models.hypothesis import HypothesisEvidenceReference
from app.models.insight import (
    Evidence,
    Insight,
    InsightDirection,
    InsightType,
    PeriodGranularity,
)
from app.models.relationship import Relationship, RelationshipType
from app.services.hypothesis_tracker import (
    HypothesisCandidate,
    attach_supporting_evidence,
    create_hypothesis_from_candidate,
)


ANALYSIS_ID = "550e8400-e29b-41d4-a716-446655440000"
MARKETING_ID = "CHANGE-MarketingSpend-2025-05-2025-06"
REVENUE_ID = "CHANGE-Revenue-2025-05-2025-06"
RELATIONSHIP_ID = "CO_MOVES_WITH-MarketingSpend-Revenue"


def _insight(
    insight_id: str,
    metric: str,
    evidence: list[Evidence] | None = None,
    analysis_id: str = ANALYSIS_ID,
) -> Insight:
    return Insight(
        id=insight_id,
        analysisId=analysis_id,
        type=InsightType.CHANGE,
        metric=metric,
        periodGranularity=PeriodGranularity.MONTH,
        period={"previous": "2025-05", "current": "2025-06"},
        direction=InsightDirection.UP,
        evidence=evidence or [],
    )


def _evidence(code: str, value: float) -> Evidence:
    return Evidence(
        code=code,
        label=f"Label for {code}",
        value=value,
        unit="PERCENT",
    )


def _source_insights() -> list[Insight]:
    return [
        _insight(
            MARKETING_ID,
            "MarketingSpend",
            [_evidence("PREVIOUS_VALUE", 100_000), _evidence("CHANGE", 20)],
        ),
        _insight(
            REVENUE_ID,
            "Revenue",
            [_evidence("PREVIOUS_VALUE", 1_000_000), _evidence("CHANGE", 30)],
        ),
    ]


def _base_hypothesis():
    relationship = Relationship(
        id=RELATIONSHIP_ID,
        analysisId=ANALYSIS_ID,
        sourceInsightId=MARKETING_ID,
        targetInsightId=REVENUE_ID,
        type=RelationshipType.CO_MOVES_WITH,
        strength=0.8,
        confidence=0.75,
    )
    evaluation = CausalityEvaluation(
        relationshipId=RELATIONSHIP_ID,
        sourceInsightId=MARKETING_ID,
        targetInsightId=REVENUE_ID,
        sourceMetric="MarketingSpend",
        targetMetric="Revenue",
        associationPresent=True,
        causalityEstablished=False,
        status=CausalityStatus.CAUSALITY_NOT_ESTABLISHED,
    )
    return create_hypothesis_from_candidate(
        HypothesisCandidate(RELATIONSHIP_ID, MARKETING_ID, REVENUE_ID),
        _source_insights(),
        [relationship],
        [evaluation],
    )


def test_two_source_insights_link_their_authoritative_evidence():
    linked = attach_supporting_evidence(_base_hypothesis(), _source_insights())

    assert linked.supporting_evidence == [
        HypothesisEvidenceReference(
            insightId=MARKETING_ID,
            evidenceCode="PREVIOUS_VALUE",
        ),
        HypothesisEvidenceReference(
            insightId=MARKETING_ID,
            evidenceCode="CHANGE",
        ),
        HypothesisEvidenceReference(
            insightId=REVENUE_ID,
            evidenceCode="PREVIOUS_VALUE",
        ),
        HypothesisEvidenceReference(
            insightId=REVENUE_ID,
            evidenceCode="CHANGE",
        ),
    ]


def test_references_contain_only_insight_id_and_evidence_code():
    linked = attach_supporting_evidence(_base_hypothesis(), _source_insights())

    assert linked.supporting_evidence[0].model_dump(by_alias=True) == {
        "insightId": MARKETING_ID,
        "evidenceCode": "PREVIOUS_VALUE",
    }


def test_source_and_evidence_order_are_preserved():
    hypothesis = _base_hypothesis().model_copy(
        update={"source_insight_ids": [REVENUE_ID, MARKETING_ID]}
    )

    linked = attach_supporting_evidence(hypothesis, _source_insights())

    assert [
        (item.insight_id, item.evidence_code)
        for item in linked.supporting_evidence
    ] == [
        (REVENUE_ID, "PREVIOUS_VALUE"),
        (REVENUE_ID, "CHANGE"),
        (MARKETING_ID, "PREVIOUS_VALUE"),
        (MARKETING_ID, "CHANGE"),
    ]


def test_duplicate_code_on_same_insight_is_not_duplicated():
    insights = _source_insights()
    insights[0].evidence.append(_evidence("CHANGE", 20))

    linked = attach_supporting_evidence(_base_hypothesis(), insights)

    assert sum(
        item.insight_id == MARKETING_ID and item.evidence_code == "CHANGE"
        for item in linked.supporting_evidence
    ) == 1


def test_same_evidence_code_on_different_insights_remains_distinct():
    linked = attach_supporting_evidence(_base_hypothesis(), _source_insights())

    previous_value_references = [
        item
        for item in linked.supporting_evidence
        if item.evidence_code == "PREVIOUS_VALUE"
    ]
    assert [item.insight_id for item in previous_value_references] == [
        MARKETING_ID,
        REVENUE_ID,
    ]


def test_unrelated_insight_evidence_is_not_linked():
    unrelated = _insight(
        "CHANGE-Orders-2025-05-2025-06",
        "Orders",
        [_evidence("UNRELATED", -15)],
    )

    linked = attach_supporting_evidence(
        _base_hypothesis(), [*_source_insights(), unrelated]
    )

    assert all(
        item.evidence_code != "UNRELATED"
        for item in linked.supporting_evidence
    )


def test_unknown_source_insight_is_rejected():
    hypothesis = _base_hypothesis().model_copy(
        update={"source_insight_ids": [MARKETING_ID, "unknown-insight"]}
    )

    with pytest.raises(ValueError, match="could not be resolved"):
        attach_supporting_evidence(hypothesis, _source_insights())


def test_cross_analysis_source_insight_is_rejected():
    insights = _source_insights()
    insights[1] = _insight(
        REVENUE_ID,
        "Revenue",
        [_evidence("CHANGE", 30)],
        analysis_id="another-analysis",
    )

    with pytest.raises(ValueError, match="different analysis"):
        attach_supporting_evidence(_base_hypothesis(), insights)


def test_source_insight_without_evidence_contributes_no_reference():
    insights = _source_insights()
    insights[1] = _insight(REVENUE_ID, "Revenue")

    linked = attach_supporting_evidence(_base_hypothesis(), insights)

    assert {item.insight_id for item in linked.supporting_evidence} == {
        MARKETING_ID
    }


def test_evidence_details_remain_only_on_authoritative_insight():
    insights = _source_insights()
    linked = attach_supporting_evidence(_base_hypothesis(), insights)
    reference = linked.supporting_evidence[0]

    assert not hasattr(reference, "value")
    assert not hasattr(reference, "label")
    assert not hasattr(reference, "unit")
    assert insights[0].evidence[0].value == 100_000
    assert insights[0].evidence[0].unit == "PERCENT"


def test_input_hypothesis_is_not_mutated():
    hypothesis = _base_hypothesis()

    linked = attach_supporting_evidence(hypothesis, _source_insights())

    assert linked is not hypothesis
    assert hypothesis.supporting_evidence == []


def test_input_insight_and_evidence_objects_are_not_mutated():
    insights = _source_insights()
    before = deepcopy(insights)

    attach_supporting_evidence(_base_hypothesis(), insights)

    assert insights == before


def test_repeated_linking_is_structurally_identical():
    assert attach_supporting_evidence(
        _base_hypothesis(), _source_insights()
    ) == attach_supporting_evidence(_base_hypothesis(), _source_insights())


def test_later_stage_fields_and_open_status_remain_unchanged():
    hypothesis = _base_hypothesis()
    linked = attach_supporting_evidence(hypothesis, _source_insights())

    assert linked.counter_evidence == hypothesis.counter_evidence == []
    assert linked.missing_context == hypothesis.missing_context == []
    assert linked.confidence == hypothesis.confidence == 0.0
    assert linked.status == hypothesis.status == "OPEN"
