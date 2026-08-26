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
    IntegrityStatus,
)
from app.models.relationship import Relationship, RelationshipType
from app.services.story_planner import (
    select_associated_signals,
    select_counter_signals,
)


def _insight(insight_id: str) -> Insight:
    return Insight(
        id=insight_id,
        analysisId="ANALYSIS-001",
        type=InsightType.CHANGE,
        metric=insight_id,
        periodGranularity=PeriodGranularity.MONTH,
        period={"previous": "2025-05", "current": "2025-06"},
        direction=InsightDirection.UP,
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
            impactDirection=BusinessImpactDirection.POSITIVE,
        ),
    )


def _relationship(
    source_id: str,
    target_id: str,
    *,
    relationship_type: RelationshipType,
    suffix: str = "",
    strength: float = 0.8,
    confidence: float = 0.8,
) -> Relationship:
    return Relationship(
        id=f"REL-{source_id}-{target_id}{suffix}",
        analysisId="ANALYSIS-001",
        sourceInsightId=source_id,
        targetInsightId=target_id,
        type=relationship_type,
        strength=strength,
        confidence=confidence,
    )


def _integrity(
    main_id: str,
    counter_pairs: list[tuple[Insight, Relationship]],
) -> InsightIntegrityEvaluation:
    return InsightIntegrityEvaluation(
        insightId=main_id,
        status=IntegrityStatus.PASS_WITH_WARNINGS,
        storyEligible=True,
        requiresQualification=True,
        counterEvidence=[
            CounterEvidenceItem(
                insightId=insight.id,
                relationshipId=relationship.id,
                metric=insight.metric,
                direction=insight.direction,
            )
            for insight, relationship in counter_pairs
        ],
    )


def _counter_select(
    main: Insight,
    candidates: list[Insight],
    relationships: list[Relationship],
    *,
    integrity: list[InsightIntegrityEvaluation] | None = None,
    rankings: list[RankedInsight] | None = None,
    maximum: int = 2,
):
    return select_counter_signals(
        main,
        candidates,
        relationships,
        integrity if integrity is not None else [],
        rankings if rankings is not None else [_ranked(item.id) for item in candidates],
        maximum,
    )


def _associated_select(
    main: Insight,
    candidates: list[Insight],
    relationships: list[Relationship],
    *,
    rankings: list[RankedInsight] | None = None,
    maximum: int = 1,
):
    return select_associated_signals(
        main,
        candidates,
        relationships,
        rankings if rankings is not None else [_ranked(item.id) for item in candidates],
        maximum,
    )


def test_missing_main_outcome_integrity_returns_no_counter_signals():
    main = _insight("MAIN")
    counter = _insight("COUNTER")
    relationship = _relationship(
        counter.id, main.id, relationship_type=RelationshipType.COUNTER_SIGNAL
    )

    assert _counter_select(main, [counter], [relationship]) == []


def test_authoritative_counter_evidence_selects_valid_counter_signal():
    main = _insight("MAIN")
    counter = _insight("COUNTER")
    relationship = _relationship(
        counter.id, main.id, relationship_type=RelationshipType.COUNTER_SIGNAL
    )

    assert _counter_select(
        main,
        [counter],
        [relationship],
        integrity=[_integrity(main.id, [(counter, relationship)])],
    ) == [(counter, relationship)]


def test_opposite_direction_without_counter_evidence_is_not_selected():
    main = _insight("MAIN")
    opposite = _insight("OPPOSITE")
    opposite.direction = InsightDirection.DOWN
    relationship = _relationship(
        opposite.id,
        main.id,
        relationship_type=RelationshipType.COUNTER_SIGNAL,
    )

    assert _counter_select(
        main,
        [opposite],
        [relationship],
        integrity=[_integrity(main.id, [])],
    ) == []


@pytest.mark.parametrize(
    ("relationship_type", "target_id"),
    [
        (RelationshipType.CONTRIBUTES_TO, "MAIN"),
        (RelationshipType.COUNTER_SIGNAL, "OTHER"),
    ],
)
def test_counter_evidence_requires_correct_type_and_target(
    relationship_type,
    target_id,
):
    main = _insight("MAIN")
    counter = _insight("COUNTER")
    relationship = _relationship(
        counter.id, target_id, relationship_type=relationship_type
    )

    assert _counter_select(
        main,
        [counter],
        [relationship],
        integrity=[_integrity(main.id, [(counter, relationship)])],
    ) == []


def test_counter_missing_from_candidates_is_not_selected():
    main = _insight("MAIN")
    counter = _insight("COUNTER")
    relationship = _relationship(
        counter.id, main.id, relationship_type=RelationshipType.COUNTER_SIGNAL
    )

    assert _counter_select(
        main,
        [],
        [relationship],
        integrity=[_integrity(main.id, [(counter, relationship)])],
        rankings=[_ranked(counter.id)],
    ) == []


def test_critical_counter_signal_is_preferred_over_high():
    main = _insight("MAIN")
    high = _insight("HIGH")
    critical = _insight("CRITICAL")
    high_rel = _relationship(
        high.id, main.id, relationship_type=RelationshipType.COUNTER_SIGNAL
    )
    critical_rel = _relationship(
        critical.id, main.id, relationship_type=RelationshipType.COUNTER_SIGNAL
    )
    pairs = [(high, high_rel), (critical, critical_rel)]

    selected = _counter_select(
        main,
        [high, critical],
        [high_rel, critical_rel],
        integrity=[_integrity(main.id, pairs)],
        rankings=[
            _ranked(high.id, level=PriorityLevel.HIGH),
            _ranked(critical.id, level=PriorityLevel.CRITICAL),
        ],
    )

    assert [item.id for item, _ in selected] == ["CRITICAL", "HIGH"]


def test_counter_order_uses_score_strength_confidence_rank_and_id():
    _assert_full_signal_order(select_counter=True)


def test_counter_limit_zero_and_negative_behavior():
    main = _insight("MAIN")
    assert _counter_select(main, [], [], maximum=0) == []
    with pytest.raises(ValueError, match="max_counter_signals"):
        _counter_select(main, [], [], maximum=-1)


def test_valid_co_moves_with_selects_associated_signal():
    main = _insight("MAIN")
    associated = _insight("ASSOCIATED")
    relationship = _relationship(
        associated.id,
        main.id,
        relationship_type=RelationshipType.CO_MOVES_WITH,
    )

    assert _associated_select(main, [associated], [relationship]) == [
        (associated, relationship)
    ]


def test_same_period_and_direction_without_relationship_is_not_associated():
    assert _associated_select(_insight("MAIN"), [_insight("OTHER")], []) == []


@pytest.mark.parametrize(
    "relationship_type",
    [RelationshipType.COUNTER_SIGNAL, RelationshipType.CONTRIBUTES_TO],
)
def test_other_relationship_types_are_not_associated(relationship_type):
    main = _insight("MAIN")
    other = _insight("OTHER")
    relationship = _relationship(
        other.id, main.id, relationship_type=relationship_type
    )

    assert _associated_select(main, [other], [relationship]) == []


def test_associated_signal_missing_from_candidates_is_not_selected():
    main = _insight("MAIN")
    other = _insight("OTHER")
    relationship = _relationship(
        other.id, main.id, relationship_type=RelationshipType.CO_MOVES_WITH
    )

    assert _associated_select(
        main, [], [relationship], rankings=[_ranked(other.id)]
    ) == []


def test_associated_order_uses_priority_score_relationship_and_rank():
    _assert_full_signal_order(select_counter=False)


def _assert_full_signal_order(*, select_counter: bool):
    main = _insight("MAIN")
    ids = ["LOW-SCORE", "WEAK", "LOW-CONFIDENCE", "LATE", "B-ID", "A-ID"]
    candidates = [_insight(insight_id) for insight_id in ids]
    relationship_type = (
        RelationshipType.COUNTER_SIGNAL
        if select_counter
        else RelationshipType.CO_MOVES_WITH
    )
    relationships = [
        _relationship(ids[0], main.id, relationship_type=relationship_type),
        _relationship(ids[1], main.id, relationship_type=relationship_type, strength=0.7),
        _relationship(ids[2], main.id, relationship_type=relationship_type, confidence=0.7),
        _relationship(ids[3], main.id, relationship_type=relationship_type),
        _relationship(ids[4], main.id, relationship_type=relationship_type),
        _relationship(ids[5], main.id, relationship_type=relationship_type),
    ]
    rankings = [
        _ranked(ids[0], score=0.7),
        _ranked(ids[1]),
        _ranked(ids[2]),
        _ranked(ids[3], rank=2),
        _ranked(ids[4]),
        _ranked(ids[5]),
    ]
    if select_counter:
        selected = _counter_select(
            main,
            candidates,
            relationships,
            integrity=[_integrity(main.id, list(zip(candidates, relationships)))],
            rankings=rankings,
            maximum=len(candidates),
        )
    else:
        selected = _associated_select(
            main,
            candidates,
            relationships,
            rankings=rankings,
            maximum=len(candidates),
        )

    assert [item.id for item, _ in selected] == [
        "A-ID",
        "B-ID",
        "LATE",
        "LOW-CONFIDENCE",
        "WEAK",
        "LOW-SCORE",
    ]


def test_associated_limit_zero_and_negative_behavior():
    main = _insight("MAIN")
    first = _insight("FIRST")
    second = _insight("SECOND")
    relationships = [
        _relationship(item.id, main.id, relationship_type=RelationshipType.CO_MOVES_WITH)
        for item in (first, second)
    ]

    assert len(
        _associated_select(
            main, [first, second], relationships, maximum=1
        )
    ) == 1
    assert _associated_select(main, [], [], maximum=0) == []
    with pytest.raises(ValueError, match="max_associated_signals"):
        _associated_select(main, [], [], maximum=-1)


def test_signal_selection_does_not_mutate_inputs():
    main = _insight("MAIN")
    signal = _insight("SIGNAL")
    counter_relationship = _relationship(
        signal.id, main.id, relationship_type=RelationshipType.COUNTER_SIGNAL
    )
    associated_relationship = _relationship(
        signal.id,
        main.id,
        relationship_type=RelationshipType.CO_MOVES_WITH,
        suffix="-ASSOCIATED",
    )
    candidates = [signal]
    relationships = [counter_relationship, associated_relationship]
    integrity = [_integrity(main.id, [(signal, counter_relationship)])]
    rankings = [_ranked(signal.id)]
    snapshots = tuple(
        [item.model_dump() for item in items]
        for items in (candidates, relationships, integrity, rankings)
    )

    select_counter_signals(main, candidates, relationships, integrity, rankings)
    select_associated_signals(main, candidates, relationships, rankings)

    assert [item.model_dump() for item in candidates] == snapshots[0]
    assert [item.model_dump() for item in relationships] == snapshots[1]
    assert [item.model_dump() for item in integrity] == snapshots[2]
    assert [item.model_dump() for item in rankings] == snapshots[3]
