import inspect

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
from app.models.insight_cluster import InsightCluster
from app.services.story_planner import (
    build_cluster_lookup,
    select_main_outcome,
)


def _insight(
    insight_id: str,
    *,
    broad_scope: bool,
    metric: str = "Metric",
) -> Insight:
    return Insight(
        id=insight_id,
        analysisId="ANALYSIS-001",
        type=InsightType.CHANGE,
        metric=metric,
        dimension=None if broad_scope else "Region",
        segment=None if broad_scope else "North",
        periodGranularity=PeriodGranularity.MONTH,
        period={"previous": "2025-05", "current": "2025-06"},
        direction=InsightDirection.UP,
    )


def _cluster(anchor_insight_id: str, *, suffix: str = "") -> InsightCluster:
    return InsightCluster(
        id=f"CLUSTER-{anchor_insight_id}{suffix}",
        analysisId="ANALYSIS-001",
        anchorInsightId=anchor_insight_id,
    )


def _ranked(insight_id: str, rank: int) -> RankedInsight:
    business_relevance = BusinessRelevanceEvaluation(
        insightId=insight_id,
        businessRelevance=0.8,
        impactDirection=BusinessImpactDirection.POSITIVE,
    )
    priority = PriorityEvaluation(
        insightId=insight_id,
        priorityScore=0.8,
        priorityLevel=PriorityLevel.HIGH,
    )
    return RankedInsight(
        rank=rank,
        insightId=insight_id,
        priority=priority,
        businessRelevance=business_relevance,
    )


def _rankings(candidates: list[Insight]) -> list[RankedInsight]:
    return [
        _ranked(candidate.id, rank)
        for rank, candidate in enumerate(candidates, start=1)
    ]


def test_empty_candidates_raise_value_error():
    with pytest.raises(
        ValueError,
        match="No story-eligible candidates are available",
    ):
        select_main_outcome([], [], [])


def test_broad_scope_cluster_anchor_beats_higher_ordered_narrow_candidate():
    narrow = _insight("NARROW", broad_scope=False)
    broad_anchor = _insight("BROAD-ANCHOR", broad_scope=True)
    candidates = [narrow, broad_anchor]

    selected = select_main_outcome(
        candidates,
        _rankings(candidates),
        [_cluster(broad_anchor.id)],
    )

    assert selected.id == "BROAD-ANCHOR"


def test_broad_scope_beats_narrow_cluster_anchor_without_tier_one():
    narrow_anchor = _insight("NARROW-ANCHOR", broad_scope=False)
    broad = _insight("BROAD", broad_scope=True)
    candidates = [narrow_anchor, broad]

    selected = select_main_outcome(
        candidates,
        _rankings(candidates),
        [_cluster(narrow_anchor.id)],
    )

    assert selected.id == "BROAD"


def test_cluster_anchor_beats_non_anchor_when_no_broad_scope_exists():
    non_anchor = _insight("NON-ANCHOR", broad_scope=False)
    anchor = _insight("ANCHOR", broad_scope=False)
    candidates = [non_anchor, anchor]

    selected = select_main_outcome(
        candidates,
        _rankings(candidates),
        [_cluster(anchor.id)],
    )

    assert selected.id == "ANCHOR"


def test_existing_order_wins_without_broad_scope_or_cluster_anchor():
    first = _insight("FIRST", broad_scope=False)
    second = _insight("SECOND", broad_scope=False)
    candidates = [first, second]

    selected = select_main_outcome(
        candidates,
        _rankings(candidates),
        [],
    )

    assert selected is first


def test_incoming_order_is_preserved_within_winning_tier():
    first = _insight("FIRST-BROAD-ANCHOR", broad_scope=True)
    second = _insight("SECOND-BROAD-ANCHOR", broad_scope=True)
    candidates = [first, second]

    selected = select_main_outcome(
        candidates,
        _rankings(candidates),
        [_cluster(first.id), _cluster(second.id)],
    )

    assert selected is first


def test_anchor_only_does_not_override_broad_scope_anchor():
    anchor_only = _insight("ANCHOR-ONLY", broad_scope=False)
    broad_anchor = _insight("BROAD-ANCHOR", broad_scope=True)
    candidates = [anchor_only, broad_anchor]

    selected = select_main_outcome(
        candidates,
        _rankings(candidates),
        [_cluster(anchor_only.id), _cluster(broad_anchor.id)],
    )

    assert selected is broad_anchor


def test_main_outcome_selection_contains_no_revenue_special_case():
    implementation = inspect.getsource(select_main_outcome)

    assert "Revenue" not in implementation


def test_candidate_and_cluster_inputs_are_not_mutated():
    first = _insight("FIRST", broad_scope=False)
    second = _insight("SECOND", broad_scope=True)
    candidates = [first, second]
    clusters = [_cluster(second.id)]
    candidate_snapshot = [item.model_dump() for item in candidates]
    cluster_snapshot = [item.model_dump() for item in clusters]

    select_main_outcome(candidates, _rankings(candidates), clusters)

    assert [item.model_dump() for item in candidates] == candidate_snapshot
    assert [item.model_dump() for item in clusters] == cluster_snapshot


def test_duplicate_cluster_anchor_ids_are_rejected():
    anchor = _insight("ANCHOR", broad_scope=True)

    with pytest.raises(ValueError, match="Duplicate Insight Cluster"):
        build_cluster_lookup(
            [
                _cluster(anchor.id),
                _cluster(anchor.id, suffix="-DUPLICATE"),
            ]
        )
