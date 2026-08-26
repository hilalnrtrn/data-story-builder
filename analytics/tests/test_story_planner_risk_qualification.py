import pytest

from app.models.business_relevance import (
    BusinessImpactDirection,
    BusinessRelevanceEvaluation,
    PriorityEvaluation,
    PriorityLevel,
    RankedInsight,
)
from app.models.insight import (
    Insight,
    InsightDirection,
    InsightType,
    PeriodGranularity,
)
from app.models.insight_integrity import (
    CounterEvidenceItem,
    InsightIntegrityEvaluation,
    IntegrityRiskLevel,
    IntegrityStatus,
    OneOffEffectCheck,
    OutlierDependencyCheck,
)
from app.models.relationship import Relationship, RelationshipType
from app.models.story_plan import StoryPlanItem, StoryRole
from app.services.story_planner import (
    apply_integrity_qualification,
    build_risk_items,
    select_counter_signals,
    select_risks,
)


def _insight(
    insight_id: str,
    *,
    insight_type: InsightType = InsightType.CHANGE,
    direction: InsightDirection = InsightDirection.UP,
) -> Insight:
    return Insight(
        id=insight_id,
        analysisId="ANALYSIS-001",
        type=insight_type,
        metric=insight_id,
        periodGranularity=PeriodGranularity.MONTH,
        period={"previous": "2025-05", "current": "2025-06"},
        direction=direction,
    )


def _ranked(
    insight_id: str,
    *,
    level: PriorityLevel = PriorityLevel.HIGH,
    score: float = 0.8,
    rank: int = 1,
) -> RankedInsight:
    return RankedInsight(
        rank=rank,
        insightId=insight_id,
        priority=PriorityEvaluation(
            insightId=insight_id,
            priorityScore=score,
            priorityLevel=level,
        ),
        businessRelevance=BusinessRelevanceEvaluation(
            insightId=insight_id,
            businessRelevance=0.8,
            impactDirection=BusinessImpactDirection.NEGATIVE,
        ),
    )


def _outlier(level: IntegrityRiskLevel) -> OutlierDependencyCheck:
    return OutlierDependencyCheck(
        level=level,
        detected=level != IntegrityRiskLevel.NONE,
        statisticName=None,
        originalStatistic=None,
        adjustedStatistic=None,
        outlierPeriod=None,
        reason=None,
    )


def _one_off(risk: IntegrityRiskLevel) -> OneOffEffectCheck:
    return OneOffEffectCheck(
        risk=risk,
        eventPeriod=None,
        nextPeriod=None,
        baselineValue=None,
        eventValue=None,
        nextValue=None,
        reversionRatio=None,
        reason=None,
    )


def _integrity(
    insight_id: str,
    *,
    status: IntegrityStatus = IntegrityStatus.PASS,
    outlier: IntegrityRiskLevel | None = None,
    one_off: IntegrityRiskLevel | None = None,
    requires_qualification: bool = False,
    counter_evidence: list[CounterEvidenceItem] | None = None,
) -> InsightIntegrityEvaluation:
    return InsightIntegrityEvaluation(
        insightId=insight_id,
        status=status,
        outlierCheck=_outlier(outlier) if outlier is not None else None,
        oneOffCheck=_one_off(one_off) if one_off is not None else None,
        storyEligible=True,
        requiresQualification=requires_qualification,
        counterEvidence=counter_evidence or [],
    )


@pytest.mark.parametrize(
    "integrity",
    [
        _integrity("RISK", status=IntegrityStatus.REVIEW_REQUIRED),
        _integrity("RISK", outlier=IntegrityRiskLevel.HIGH),
        _integrity("RISK", one_off=IntegrityRiskLevel.HIGH),
    ],
)
def test_integrity_risk_conditions_select_insight(integrity):
    insight = _insight("RISK")

    assert select_risks(
        [insight], [integrity], [_ranked(insight.id)]
    ) == [insight]


@pytest.mark.parametrize(
    "insight,integrity",
    [
        (_insight("ANOMALY", insight_type=InsightType.ANOMALY), _integrity("ANOMALY")),
        (_insight("DOWN", direction=InsightDirection.DOWN), _integrity("DOWN")),
        (_insight("QUALIFIED"), _integrity("QUALIFIED", requires_qualification=True)),
        (
            _insight("COUNTER"),
            _integrity(
                "COUNTER",
                counter_evidence=[
                    CounterEvidenceItem(
                        insightId="OTHER",
                        relationshipId="REL-OTHER-COUNTER",
                        metric="Other",
                        direction=InsightDirection.DOWN,
                    )
                ],
            ),
        ),
    ],
)
def test_non_risk_signals_alone_do_not_create_risk(insight, integrity):
    assert select_risks(
        [insight], [integrity], [_ranked(insight.id)]
    ) == []


def test_insight_absent_from_candidates_is_not_selected():
    assert select_risks(
        [],
        [_integrity("RISK", status=IntegrityStatus.REVIEW_REQUIRED)],
        [_ranked("RISK")],
    ) == []


def test_risk_order_follows_integrity_then_priority_score_rank_and_id():
    ids = ["REVIEW", "OUTLIER", "ONE-OFF", "LOW-LEVEL", "LOW-SCORE", "LATE", "B-ID", "A-ID"]
    candidates = [_insight(insight_id) for insight_id in ids]
    integrity = [
        _integrity(ids[0], status=IntegrityStatus.REVIEW_REQUIRED),
        _integrity(ids[1], outlier=IntegrityRiskLevel.HIGH),
        _integrity(ids[2], one_off=IntegrityRiskLevel.HIGH),
        _integrity(ids[3], one_off=IntegrityRiskLevel.HIGH),
        _integrity(ids[4], one_off=IntegrityRiskLevel.HIGH),
        _integrity(ids[5], one_off=IntegrityRiskLevel.HIGH),
        _integrity(ids[6], one_off=IntegrityRiskLevel.HIGH),
        _integrity(ids[7], one_off=IntegrityRiskLevel.HIGH),
    ]
    rankings = [
        _ranked(ids[0], level=PriorityLevel.LOW),
        _ranked(ids[1], level=PriorityLevel.LOW),
        _ranked(ids[2], level=PriorityLevel.CRITICAL),
        _ranked(ids[3], level=PriorityLevel.MEDIUM),
        _ranked(ids[4], score=0.7),
        _ranked(ids[5], rank=2),
        _ranked(ids[6]),
        _ranked(ids[7]),
    ]

    selected = select_risks(
        candidates, integrity, rankings, max_risks=len(candidates)
    )

    assert [item.id for item in selected] == [
        "REVIEW",
        "OUTLIER",
        "ONE-OFF",
        "A-ID",
        "B-ID",
        "LATE",
        "LOW-SCORE",
        "LOW-LEVEL",
    ]


def test_risk_limit_zero_and_negative_behavior():
    risk = _insight("RISK")
    integrity = [_integrity(risk.id, status=IntegrityStatus.REVIEW_REQUIRED)]
    ranking = [_ranked(risk.id)]

    assert select_risks([risk], integrity, ranking, max_risks=1) == [risk]
    assert select_risks([risk], integrity, ranking, max_risks=0) == []
    with pytest.raises(ValueError, match="max_risks"):
        select_risks([risk], integrity, ranking, max_risks=-1)


def test_build_risk_items_preserves_order_role_id_and_empty_evidence():
    first = _insight("FIRST")
    second = _insight("SECOND")

    first_build = build_risk_items([first, second])
    second_build = build_risk_items([first, second])

    assert [item.role for item in first_build] == [StoryRole.RISK] * 2
    assert [item.insight_id for item in first_build] == ["FIRST", "SECOND"]
    assert [item.id for item in first_build] == [item.id for item in second_build]
    assert all(item.relationship_id is None for item in first_build)
    assert all(item.evidence_codes == [] for item in first_build)


def test_qualification_is_copied_for_multiple_supported_roles():
    roles = [
        StoryRole.MAIN_OUTCOME,
        StoryRole.PRIMARY_CONTRIBUTOR,
        StoryRole.SECONDARY_FINDING,
        StoryRole.COUNTER_SIGNAL,
        StoryRole.ASSOCIATED_SIGNAL,
        StoryRole.RISK,
    ]
    items = [
        StoryPlanItem(id=f"ITEM-{index}", role=role, insightId=f"I-{index}")
        for index, role in enumerate(roles)
    ]
    evaluations = [
        _integrity(item.insight_id, requires_qualification=index % 2 == 0)
        for index, item in enumerate(items)
    ]

    updated = apply_integrity_qualification(items, evaluations)

    assert [item.requires_qualification for item in updated] == [
        True,
        False,
        True,
        False,
        True,
        False,
    ]


def test_missing_integrity_does_not_infer_qualification_from_role_or_direction():
    item = StoryPlanItem(
        id="RISK-DOWN",
        role=StoryRole.RISK,
        insightId="DOWN",
        requiresQualification=True,
    )

    updated = apply_integrity_qualification([item], [])

    assert updated[0].requires_qualification is False


def test_qualification_and_risk_selection_do_not_mutate_inputs():
    risk = _insight("RISK")
    evaluations = [
        _integrity(
            risk.id,
            status=IntegrityStatus.REVIEW_REQUIRED,
            requires_qualification=True,
        )
    ]
    rankings = [_ranked(risk.id)]
    items = [StoryPlanItem(id="ITEM-RISK", role=StoryRole.RISK, insightId=risk.id)]
    snapshots = tuple(
        [item.model_dump() for item in collection]
        for collection in ([risk], evaluations, rankings, items)
    )

    select_risks([risk], evaluations, rankings)
    updated = apply_integrity_qualification(items, evaluations)

    assert [risk.model_dump()] == snapshots[0]
    assert [item.model_dump() for item in evaluations] == snapshots[1]
    assert [item.model_dump() for item in rankings] == snapshots[2]
    assert [item.model_dump() for item in items] == snapshots[3]
    assert updated[0] is not items[0]


def test_existing_counter_signal_selection_remains_valid():
    main = _insight("MAIN")
    counter = _insight("COUNTER")
    relationship = Relationship(
        id="REL-COUNTER-MAIN",
        analysisId="ANALYSIS-001",
        sourceInsightId=counter.id,
        targetInsightId=main.id,
        type=RelationshipType.COUNTER_SIGNAL,
        strength=0.8,
        confidence=0.8,
    )
    evidence = CounterEvidenceItem(
        insightId=counter.id,
        relationshipId=relationship.id,
        metric=counter.metric,
        direction=counter.direction,
    )

    selected = select_counter_signals(
        main,
        [counter],
        [relationship],
        [_integrity(main.id, counter_evidence=[evidence])],
        [_ranked(counter.id)],
    )

    assert selected == [(counter, relationship)]
