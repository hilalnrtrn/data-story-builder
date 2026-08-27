import inspect

import pytest

import app.services.hypothesis_tracker as tracker_module
from app.models.causality import CausalityEvaluation, CausalityStatus
from app.models.insight import (
    Evidence,
    Insight,
    InsightDirection,
    InsightType,
    PeriodGranularity,
)
from app.models.insight_integrity import (
    CounterEvidenceItem,
    InsightIntegrityEvaluation,
    IntegrityStatus,
)
from app.models.missing_context import (
    MissingContextEvaluation,
    MissingContextItem,
    MissingContextStatus,
)
from app.models.relationship import Relationship, RelationshipType
from app.services.hypothesis_tracker import track_hypotheses


ANALYSIS_ID = "DAY16-ADVERSARIAL"
MARKETING_ID = "CHANGE-MarketingSpend-2025-05-2025-06"
REVENUE_ID = "CHANGE-Revenue-2025-05-2025-06"
RELATIONSHIP_ID = "CO_MOVES_WITH-MarketingSpend-Revenue"
FORBIDDEN_CAUSAL_WORDING = (
    "caused",
    "led to",
    "resulted in",
    "drove",
    "because of",
    "responsible for",
)


def _insight(
    insight_id: str,
    metric: str,
    *,
    analysis_id: str = ANALYSIS_ID,
    evidence: list[Evidence] | None = None,
) -> Insight:
    return Insight(
        id=insight_id,
        analysisId=analysis_id,
        type=InsightType.CHANGE,
        metric=metric,
        periodGranularity=PeriodGranularity.MONTH,
        period={"previous": "2025-05", "current": "2025-06"},
        direction=InsightDirection.UP,
        values={"relativeChange": 20},
        evidence=(
            evidence
            if evidence is not None
            else [
                Evidence(
                    code="PERCENTAGE_CHANGE",
                    label="Percentage change",
                    value=20,
                    unit="PERCENT",
                )
            ]
        ),
    )


def _relationship(
    relationship_type: RelationshipType = RelationshipType.CO_MOVES_WITH,
    *,
    analysis_id: str = ANALYSIS_ID,
    source_id: str = MARKETING_ID,
    target_id: str = REVENUE_ID,
    confidence: float = 0.8,
) -> Relationship:
    return Relationship(
        id=RELATIONSHIP_ID,
        analysisId=analysis_id,
        sourceInsightId=source_id,
        targetInsightId=target_id,
        type=relationship_type,
        strength=0.8,
        confidence=confidence,
    )


def _causality(
    relationship: Relationship,
    *,
    association: bool = True,
    established: bool = False,
    status: CausalityStatus = CausalityStatus.CAUSALITY_NOT_ESTABLISHED,
) -> CausalityEvaluation:
    return CausalityEvaluation(
        relationshipId=relationship.id,
        sourceInsightId=relationship.source_insight_id,
        targetInsightId=relationship.target_insight_id,
        sourceMetric="MarketingSpend",
        targetMetric="Revenue",
        associationPresent=association,
        causalityEstablished=established,
        status=status,
    )


def _inputs(*, confidence: float = 0.8):
    insights = [
        _insight(MARKETING_ID, "MarketingSpend"),
        _insight(REVENUE_ID, "Revenue"),
    ]
    relationship = _relationship(confidence=confidence)
    integrity = [
        InsightIntegrityEvaluation(
            insightId=MARKETING_ID,
            status=IntegrityStatus.PASS,
            integrityScore=1,
            storyEligible=True,
            requiresQualification=False,
        ),
        InsightIntegrityEvaluation(
            insightId=REVENUE_ID,
            status=IntegrityStatus.PASS,
            integrityScore=1,
            storyEligible=True,
            requiresQualification=False,
        ),
    ]
    missing = [
        MissingContextEvaluation(
            insightId=MARKETING_ID,
            interpretationLimited=False,
        ),
        MissingContextEvaluation(
            insightId=REVENUE_ID,
            interpretationLimited=False,
        ),
    ]
    return insights, [relationship], integrity, [_causality(relationship)], missing


@pytest.mark.parametrize(
    "relationship_type",
    [
        RelationshipType.CONTRIBUTES_TO,
        RelationshipType.COUNTER_SIGNAL,
        RelationshipType.RELATED_ANOMALY,
    ],
)
def test_non_association_relationship_types_are_ineligible(
    relationship_type,
) -> None:
    insights, _, integrity, _, missing = _inputs()
    relationship = _relationship(relationship_type)

    assert track_hypotheses(
        insights,
        [relationship],
        integrity,
        [_causality(relationship)],
        missing,
    ) == []


@pytest.mark.parametrize(
    ("association", "established", "status"),
    [
        (False, False, CausalityStatus.CAUSALITY_NOT_ESTABLISHED),
        (True, True, CausalityStatus.CAUSALITY_ESTABLISHED),
        (True, False, CausalityStatus.NOT_APPLICABLE),
    ],
)
def test_invalid_causality_states_are_ineligible(
    association,
    established,
    status,
) -> None:
    insights, relationships, integrity, _, missing = _inputs()

    assert track_hypotheses(
        insights,
        relationships,
        integrity,
        [
            _causality(
                relationships[0],
                association=association,
                established=established,
                status=status,
            )
        ],
        missing,
    ) == []


def test_unknown_cross_analysis_and_self_edge_relationships_are_rejected() -> None:
    inputs = _inputs()
    insights, _, integrity, _, missing = inputs
    unknown = _relationship(source_id="unknown-insight")
    cross_analysis = _relationship(analysis_id="OTHER-ANALYSIS")
    self_edge = Relationship.model_construct(
        id="self-edge",
        analysis_id=ANALYSIS_ID,
        source_insight_id=MARKETING_ID,
        target_insight_id=MARKETING_ID,
        type=RelationshipType.CO_MOVES_WITH.value,
        strength=0.8,
        confidence=0.8,
        strength_breakdown={},
        confidence_breakdown={},
        reasons=[],
        metadata={},
    )

    for relationship in (unknown, cross_analysis, self_edge):
        assert track_hypotheses(
            insights,
            [relationship],
            integrity,
            [_causality(relationship)],
            missing,
        ) == []


def test_maximum_confidence_never_establishes_causality_or_changes_status() -> None:
    inputs = _inputs(confidence=1.0)
    hypothesis = track_hypotheses(*inputs)[0]

    assert hypothesis.confidence == 1.0
    assert hypothesis.status == "OPEN"
    assert hypothesis.causality_status == "CAUSALITY_NOT_ESTABLISHED"
    assert not any(
        phrase in hypothesis.statement.lower()
        for phrase in FORBIDDEN_CAUSAL_WORDING
    )


def test_adverse_signals_and_low_confidence_never_transition_lifecycle() -> None:
    insights, relationships, integrity, evaluations, missing = _inputs(
        confidence=0.0
    )
    integrity[1] = integrity[1].model_copy(
        update={
            "counter_evidence": [
                CounterEvidenceItem(
                    insightId="unrelated-counter-insight",
                    relationshipId="counter-relationship",
                    metric="Orders",
                    direction=InsightDirection.DOWN,
                    reasons=["Opposite movement."],
                )
            ]
        }
    )
    missing[1] = MissingContextEvaluation(
        insightId=REVENUE_ID,
        missingContext=[
            MissingContextItem(
                field="CompetitorPrice",
                status=MissingContextStatus.NOT_AVAILABLE,
                isDataQualityError=False,
                reason="Competitor pricing is unavailable.",
            )
        ],
        interpretationLimited=True,
    )

    hypothesis = track_hypotheses(
        insights, relationships, integrity, evaluations, missing
    )[0]

    assert hypothesis.status == "OPEN"
    assert hypothesis.status not in {"SUPPORTED", "CONFIRMED", "REJECTED"}


def test_evidence_is_reference_only_scoped_and_deduplicated() -> None:
    duplicate = Evidence(
        code="PERCENTAGE_CHANGE",
        label="Percentage change",
        value=999,
        unit="PERCENT",
    )
    inputs = _inputs()
    inputs[0][0] = _insight(
        MARKETING_ID,
        "MarketingSpend",
        evidence=[duplicate, duplicate.model_copy(deep=True)],
    )
    unrelated = _insight(
        "CHANGE-Unrelated-2025-05-2025-06",
        "Unrelated",
        evidence=[
            Evidence(
                code="UNRELATED_CODE",
                label="Unrelated",
                value=123,
            )
        ],
    )
    inputs[0].append(unrelated)
    inputs[2].append(
        InsightIntegrityEvaluation(
            insightId=unrelated.id,
            status=IntegrityStatus.PASS,
            counterEvidence=[
                CounterEvidenceItem(
                    insightId="other",
                    relationshipId="other",
                    metric="Unrelated",
                    direction=InsightDirection.DOWN,
                )
            ],
            storyEligible=True,
            requiresQualification=False,
        )
    )
    inputs[4].append(
        MissingContextEvaluation(
            insightId=unrelated.id,
            missingContext=[
                MissingContextItem(
                    field="UnrelatedField",
                    status=MissingContextStatus.NOT_AVAILABLE,
                    isDataQualityError=False,
                    reason="Unrelated.",
                )
            ],
            interpretationLimited=True,
        )
    )

    hypothesis = track_hypotheses(*inputs)[0]
    dumped_references = [
        reference.model_dump() for reference in hypothesis.supporting_evidence
    ]

    assert dumped_references == [
        {"insight_id": MARKETING_ID, "evidence_code": "PERCENTAGE_CHANGE"},
        {"insight_id": REVENUE_ID, "evidence_code": "PERCENTAGE_CHANGE"},
    ]
    assert "UNRELATED_CODE" not in str(dumped_references)
    assert all(
        set(reference) == {"insight_id", "evidence_code"}
        for reference in dumped_references
    )
    assert not hypothesis.counter_evidence
    assert not hypothesis.missing_context


def test_missing_context_provenance_is_preserved() -> None:
    inputs = _inputs()
    inputs[4][1] = MissingContextEvaluation(
        insightId=REVENUE_ID,
        missingContext=[
            MissingContextItem(
                field="UnitPrice",
                status=MissingContextStatus.NOT_AVAILABLE,
                isDataQualityError=False,
                reason="Unit price is unavailable.",
            )
        ],
        interpretationLimited=True,
    )

    reference = track_hypotheses(*inputs)[0].missing_context[0]
    assert reference.source_insight_id == REVENUE_ID
    assert reference.item.field == "UnitPrice"
    assert reference.item.is_data_quality_error is False


def test_ordering_duplicates_and_repeated_runs_are_deterministic() -> None:
    inputs = _inputs()
    baseline = track_hypotheses(*inputs)
    reordered = track_hypotheses(
        list(reversed(inputs[0])),
        [inputs[1][0].model_copy(deep=True), inputs[1][0]],
        list(reversed(inputs[2])),
        [inputs[3][0].model_copy(deep=True), inputs[3][0]],
        list(reversed(inputs[4])),
    )

    assert reordered == baseline
    assert track_hypotheses(*inputs) == baseline
    assert len(reordered) == 1
    assert reordered[0].source_insight_ids == [MARKETING_ID, REVENUE_ID]
    assert reordered[0].reasons == baseline[0].reasons


def test_hypothesis_boundary_has_no_raw_data_or_forbidden_dependencies() -> None:
    hypothesis = track_hypotheses(*_inputs())[0]
    serialized = hypothesis.model_dump(by_alias=True)
    production_source = inspect.getsource(tracker_module).lower()

    assert not ({"dataframe", "dataset", "rows", "rawData"} & serialized.keys())
    assert "pandas" not in production_source
    assert "dataframe" not in production_source
    assert "llm" not in production_source
    assert "story_planner" not in production_source
    assert "expected_results" not in production_source
    assert "golden" not in production_source
