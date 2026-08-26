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
    InsightIntegrityEvaluation,
    IntegrityStatus,
)
from app.services.story_planner import (
    build_integrity_lookup,
    build_ranked_insight_lookup,
    select_story_candidates,
)


def _insight(insight_id: str) -> Insight:
    return Insight(
        id=insight_id,
        analysisId="ANALYSIS-001",
        type=InsightType.CHANGE,
        metric="Revenue",
        periodGranularity=PeriodGranularity.MONTH,
        period={"previous": "2025-05", "current": "2025-06"},
        direction=InsightDirection.UP,
        confidence=0.9,
        importance=0.8,
    )


def _integrity(
    insight_id: str,
    *,
    story_eligible: bool = True,
) -> InsightIntegrityEvaluation:
    return InsightIntegrityEvaluation(
        insightId=insight_id,
        status=IntegrityStatus.PASS,
        storyEligible=story_eligible,
        requiresQualification=False,
    )


def _ranked(
    insight_id: str,
    priority_level: PriorityLevel,
    *,
    priority_score: float = 0.8,
    rank: int = 1,
) -> RankedInsight:
    business_relevance = BusinessRelevanceEvaluation(
        insightId=insight_id,
        businessRelevance=0.8,
        impactDirection=BusinessImpactDirection.POSITIVE,
    )
    priority = PriorityEvaluation(
        insightId=insight_id,
        priorityScore=priority_score,
        priorityLevel=priority_level,
    )
    return RankedInsight(
        rank=rank,
        insightId=insight_id,
        priority=priority,
        businessRelevance=business_relevance,
    )


def _candidate_ids(insights, rankings, integrity):
    return [
        insight.id
        for insight in select_story_candidates(
            insights,
            rankings,
            integrity,
        )
    ]


def test_story_ineligible_insight_is_excluded():
    insight = _insight("INSIGHT-001")

    assert _candidate_ids(
        [insight],
        [_ranked(insight.id, PriorityLevel.HIGH)],
        [_integrity(insight.id, story_eligible=False)],
    ) == []


def test_insight_without_integrity_evaluation_is_excluded():
    insight = _insight("INSIGHT-001")

    assert _candidate_ids(
        [insight],
        [_ranked(insight.id, PriorityLevel.HIGH)],
        [],
    ) == []


def test_eligible_insight_without_ranking_is_excluded():
    insight = _insight("INSIGHT-001")

    assert _candidate_ids(
        [insight],
        [],
        [_integrity(insight.id)],
    ) == []


def test_critical_is_ordered_before_high():
    high = _insight("HIGH")
    critical = _insight("CRITICAL")

    assert _candidate_ids(
        [high, critical],
        [
            _ranked(high.id, PriorityLevel.HIGH, rank=1),
            _ranked(critical.id, PriorityLevel.CRITICAL, rank=2),
        ],
        [_integrity(high.id), _integrity(critical.id)],
    ) == ["CRITICAL", "HIGH"]


def test_high_is_ordered_before_medium():
    medium = _insight("MEDIUM")
    high = _insight("HIGH")

    assert _candidate_ids(
        [medium, high],
        [
            _ranked(medium.id, PriorityLevel.MEDIUM, rank=1),
            _ranked(high.id, PriorityLevel.HIGH, rank=2),
        ],
        [_integrity(medium.id), _integrity(high.id)],
    ) == ["HIGH", "MEDIUM"]


def test_medium_remains_available_without_high_or_critical():
    medium = _insight("MEDIUM")

    assert _candidate_ids(
        [medium],
        [_ranked(medium.id, PriorityLevel.MEDIUM)],
        [_integrity(medium.id)],
    ) == ["MEDIUM"]


def test_same_priority_orders_higher_priority_score_first():
    lower_score = _insight("LOWER-SCORE")
    higher_score = _insight("HIGHER-SCORE")

    assert _candidate_ids(
        [lower_score, higher_score],
        [
            _ranked(
                lower_score.id,
                PriorityLevel.HIGH,
                priority_score=0.7,
                rank=1,
            ),
            _ranked(
                higher_score.id,
                PriorityLevel.HIGH,
                priority_score=0.9,
                rank=2,
            ),
        ],
        [_integrity(lower_score.id), _integrity(higher_score.id)],
    ) == ["HIGHER-SCORE", "LOWER-SCORE"]


def test_equal_priority_score_orders_lower_existing_rank_first():
    later_rank = _insight("LATER-RANK")
    earlier_rank = _insight("EARLIER-RANK")

    assert _candidate_ids(
        [later_rank, earlier_rank],
        [
            _ranked(later_rank.id, PriorityLevel.HIGH, rank=2),
            _ranked(earlier_rank.id, PriorityLevel.HIGH, rank=1),
        ],
        [_integrity(later_rank.id), _integrity(earlier_rank.id)],
    ) == ["EARLIER-RANK", "LATER-RANK"]


def test_equal_score_and_rank_orders_by_insight_id():
    second = _insight("INSIGHT-B")
    first = _insight("INSIGHT-A")

    assert _candidate_ids(
        [second, first],
        [
            _ranked(second.id, PriorityLevel.HIGH),
            _ranked(first.id, PriorityLevel.HIGH),
        ],
        [_integrity(second.id), _integrity(first.id)],
    ) == ["INSIGHT-A", "INSIGHT-B"]


def test_duplicate_integrity_insight_ids_are_rejected():
    evaluation = _integrity("INSIGHT-001")

    with pytest.raises(ValueError, match="Duplicate Insight Integrity"):
        build_integrity_lookup([evaluation, evaluation])


def test_duplicate_ranked_insight_ids_are_rejected():
    ranked = _ranked("INSIGHT-001", PriorityLevel.HIGH)

    with pytest.raises(ValueError, match="Duplicate Ranked Insight"):
        build_ranked_insight_lookup([ranked, ranked])


def test_selection_does_not_mutate_inputs():
    insights = [_insight("INSIGHT-B"), _insight("INSIGHT-A")]
    rankings = [
        _ranked("INSIGHT-B", PriorityLevel.MEDIUM, rank=2),
        _ranked("INSIGHT-A", PriorityLevel.HIGH, rank=1),
    ]
    integrity = [_integrity("INSIGHT-B"), _integrity("INSIGHT-A")]
    snapshots = (
        [item.model_dump() for item in insights],
        [item.model_dump() for item in rankings],
        [item.model_dump() for item in integrity],
    )

    select_story_candidates(insights, rankings, integrity)

    assert [item.model_dump() for item in insights] == snapshots[0]
    assert [item.model_dump() for item in rankings] == snapshots[1]
    assert [item.model_dump() for item in integrity] == snapshots[2]
