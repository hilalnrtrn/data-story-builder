import inspect

import pytest

from app.config.story_planner_config import load_story_planner_config
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
from app.models.relationship import Relationship, RelationshipType
from app.services.story_planner import (
    build_relationship_lookup,
    select_contributors,
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
    relationship_id: str | None = None,
    relationship_type: RelationshipType = RelationshipType.CONTRIBUTES_TO,
    strength: float = 0.8,
    confidence: float = 0.8,
) -> Relationship:
    return Relationship(
        id=relationship_id or f"REL-{source_id}-{target_id}",
        analysisId="ANALYSIS-001",
        sourceInsightId=source_id,
        targetInsightId=target_id,
        type=relationship_type,
        strength=strength,
        confidence=confidence,
    )


def _cluster(main_id: str, member_ids: list[str]) -> InsightCluster:
    return InsightCluster(
        id=f"CLUSTER-{main_id}",
        analysisId="ANALYSIS-001",
        anchorInsightId=main_id,
        memberInsightIds=member_ids,
    )


def _select(
    main: Insight,
    candidates: list[Insight],
    relationships: list[Relationship],
    *,
    clusters: list[InsightCluster] | None = None,
    rankings: list[RankedInsight] | None = None,
    max_contributors: int = 2,
    config: dict | None = None,
):
    return select_contributors(
        main,
        candidates,
        relationships,
        clusters if clusters is not None else [_cluster(main.id, [item.id for item in candidates])],
        rankings if rankings is not None else [_ranked(item.id) for item in candidates],
        max_contributors,
        config,
    )


def test_main_outcome_without_matching_cluster_returns_empty():
    main = _insight("MAIN")
    contributor = _insight("CONTRIBUTOR")

    assert _select(
        main,
        [contributor],
        [_relationship(contributor.id, main.id)],
        clusters=[],
    ) == []


def test_cluster_member_with_contributes_to_is_selected():
    main = _insight("MAIN")
    contributor = _insight("CONTRIBUTOR")
    relationship = _relationship(contributor.id, main.id)

    assert _select(main, [contributor], [relationship]) == [
        (contributor, relationship)
    ]


@pytest.mark.parametrize(
    "relationship_type",
    [RelationshipType.COUNTER_SIGNAL, RelationshipType.CO_MOVES_WITH],
)
def test_non_contributor_relationship_types_are_not_selected(
    relationship_type,
):
    main = _insight("MAIN")
    member = _insight("MEMBER")

    assert _select(
        main,
        [member],
        [_relationship(member.id, main.id, relationship_type=relationship_type)],
    ) == []


def test_cluster_membership_without_contributes_to_is_not_enough():
    main = _insight("MAIN")
    member = _insight("MEMBER")

    assert _select(main, [member], []) == []


def test_contributes_to_outside_main_cluster_is_not_enough():
    main = _insight("MAIN")
    contributor = _insight("CONTRIBUTOR")

    assert _select(
        main,
        [contributor],
        [_relationship(contributor.id, main.id)],
        clusters=[_cluster(main.id, [])],
    ) == []


def test_insight_outside_candidate_list_is_not_selected():
    main = _insight("MAIN")
    member = _insight("MEMBER")

    assert _select(
        main,
        [],
        [_relationship(member.id, main.id)],
        clusters=[_cluster(main.id, [member.id])],
        rankings=[_ranked(member.id)],
    ) == []


def test_priority_level_orders_critical_before_high():
    main = _insight("MAIN")
    high = _insight("HIGH")
    critical = _insight("CRITICAL")
    relationships = [
        _relationship(high.id, main.id),
        _relationship(critical.id, main.id),
    ]

    selected = _select(
        main,
        [high, critical],
        relationships,
        rankings=[
            _ranked(high.id, level=PriorityLevel.HIGH),
            _ranked(critical.id, level=PriorityLevel.CRITICAL),
        ],
    )

    assert [insight.id for insight, _ in selected] == ["CRITICAL", "HIGH"]


def test_same_priority_orders_by_score_strength_and_confidence():
    main = _insight("MAIN")
    low_score = _insight("LOW-SCORE")
    weak = _insight("WEAK")
    low_confidence = _insight("LOW-CONFIDENCE")
    strongest = _insight("STRONGEST")
    candidates = [low_score, weak, low_confidence, strongest]
    relationships = [
        _relationship(low_score.id, main.id, strength=1.0, confidence=1.0),
        _relationship(weak.id, main.id, strength=0.7, confidence=1.0),
        _relationship(low_confidence.id, main.id, strength=0.9, confidence=0.7),
        _relationship(strongest.id, main.id, strength=0.9, confidence=0.9),
    ]
    rankings = [
        _ranked(low_score.id, score=0.7),
        _ranked(weak.id, score=0.8),
        _ranked(low_confidence.id, score=0.8),
        _ranked(strongest.id, score=0.8),
    ]

    selected = _select(
        main,
        candidates,
        relationships,
        rankings=rankings,
        max_contributors=4,
    )

    assert [insight.id for insight, _ in selected] == [
        "STRONGEST",
        "LOW-CONFIDENCE",
        "WEAK",
        "LOW-SCORE",
    ]


def test_remaining_ties_use_rank_then_insight_id():
    main = _insight("MAIN")
    later_rank = _insight("A-LATER-RANK")
    id_second = _insight("C-SAME-RANK")
    id_first = _insight("B-SAME-RANK")
    candidates = [later_rank, id_second, id_first]

    selected = _select(
        main,
        candidates,
        [_relationship(item.id, main.id) for item in candidates],
        rankings=[
            _ranked(later_rank.id, rank=2),
            _ranked(id_second.id, rank=1),
            _ranked(id_first.id, rank=1),
        ],
        max_contributors=3,
    )

    assert [insight.id for insight, _ in selected] == [
        "B-SAME-RANK",
        "C-SAME-RANK",
        "A-LATER-RANK",
    ]


def test_max_contributors_limits_output_and_zero_returns_empty():
    main = _insight("MAIN")
    first = _insight("FIRST")
    second = _insight("SECOND")
    relationships = [
        _relationship(first.id, main.id),
        _relationship(second.id, main.id),
    ]
    rankings = [_ranked(first.id, rank=1), _ranked(second.id, rank=2)]

    selected = _select(
        main,
        [second, first],
        relationships,
        rankings=rankings,
        max_contributors=1,
    )

    assert [insight.id for insight, _ in selected] == ["FIRST"]
    assert _select(
        main,
        [first],
        [relationships[0]],
        max_contributors=0,
    ) == []


def test_negative_max_contributors_is_rejected():
    with pytest.raises(ValueError, match="max_contributors"):
        _select(_insight("MAIN"), [], [], max_contributors=-1)


def test_duplicate_relationship_ids_are_rejected():
    relationship = _relationship("SOURCE", "MAIN")

    with pytest.raises(ValueError, match="Duplicate Relationship"):
        build_relationship_lookup([relationship, relationship])


def test_selection_does_not_mutate_inputs():
    main = _insight("MAIN")
    contributor = _insight("CONTRIBUTOR")
    candidates = [contributor]
    relationships = [_relationship(contributor.id, main.id)]
    clusters = [_cluster(main.id, [contributor.id])]
    rankings = [_ranked(contributor.id)]
    snapshots = tuple(
        [item.model_dump() for item in items]
        for items in (candidates, relationships, clusters, rankings)
    )

    select_contributors(main, candidates, relationships, clusters, rankings)

    assert [item.model_dump() for item in candidates] == snapshots[0]
    assert [item.model_dump() for item in relationships] == snapshots[1]
    assert [item.model_dump() for item in clusters] == snapshots[2]
    assert [item.model_dump() for item in rankings] == snapshots[3]


def test_positive_contributor_outranks_better_ranked_negative_offset():
    main = _insight("OUTCOME")
    positive = _insight("COMPATIBLE")
    negative_offset = _insight("OFFSET")
    positive.values["contributorRole"] = "POSITIVE_CONTRIBUTOR"
    negative_offset.values["contributorRole"] = "NEGATIVE_OFFSET"
    relationships = [
        _relationship(negative_offset.id, main.id),
        _relationship(positive.id, main.id),
    ]

    selected = _select(
        main,
        [negative_offset, positive],
        relationships,
        rankings=[
            _ranked(
                negative_offset.id,
                level=PriorityLevel.CRITICAL,
                score=0.99,
                rank=1,
            ),
            _ranked(
                positive.id,
                level=PriorityLevel.LOW,
                score=0.10,
                rank=2,
            ),
        ],
    )

    assert selected[0][0] is positive
    assert selected[0][0].values["contributorRole"] != "NEGATIVE_OFFSET"


def test_negative_outcome_prefers_negative_contributor_over_positive_offset():
    main = _insight("OUTCOME")
    main.direction = InsightDirection.DOWN
    compatible = _insight("COMPATIBLE")
    positive_offset = _insight("OFFSET")
    compatible.values["contributorRole"] = "NEGATIVE_CONTRIBUTOR"
    positive_offset.values["contributorRole"] = "POSITIVE_OFFSET"

    selected = _select(
        main,
        [positive_offset, compatible],
        [
            _relationship(positive_offset.id, main.id),
            _relationship(compatible.id, main.id),
        ],
        rankings=[
            _ranked(positive_offset.id, level=PriorityLevel.CRITICAL),
            _ranked(compatible.id, level=PriorityLevel.LOW, rank=2),
        ],
    )

    assert selected[0][0] is compatible


def test_compatible_contributors_keep_existing_deterministic_order():
    main = _insight("OUTCOME")
    lower_score = _insight("LOWER-SCORE")
    higher_score = _insight("HIGHER-SCORE")
    for candidate in (lower_score, higher_score):
        candidate.values["contributorRole"] = "POSITIVE_CONTRIBUTOR"

    selected = _select(
        main,
        [lower_score, higher_score],
        [
            _relationship(lower_score.id, main.id),
            _relationship(higher_score.id, main.id),
        ],
        rankings=[
            _ranked(lower_score.id, score=0.7),
            _ranked(higher_score.id, score=0.9, rank=2),
        ],
    )

    assert [item.id for item, _ in selected] == [
        "HIGHER-SCORE",
        "LOWER-SCORE",
    ]


def test_contributor_semantics_have_no_dataset_name_special_cases():
    implementation = inspect.getsource(select_contributors)

    assert all(
        name not in implementation
        for name in ("Revenue", "Region", "Marmara", "Campaign")
    )


def test_configured_dimension_overrides_better_generic_priority():
    main = _insight("OUTCOME")
    preferred = _insight("PREFERRED")
    other = _insight("OTHER")
    preferred.dimension = "PreferredDimension"
    other.dimension = "OtherDimension"

    selected = _select(
        main,
        [other, preferred],
        [
            _relationship(other.id, main.id),
            _relationship(preferred.id, main.id),
        ],
        rankings=[
            _ranked(other.id, level=PriorityLevel.CRITICAL, score=0.99),
            _ranked(
                preferred.id,
                level=PriorityLevel.LOW,
                score=0.10,
                rank=2,
            ),
        ],
        config={
            "primaryContributorDimensionPriority": [
                "PreferredDimension",
                "OtherDimension",
            ]
        },
    )

    assert selected[0][0] is preferred


def test_default_dimension_policy_is_explicit_and_ordered():
    assert load_story_planner_config() == {
        "primaryContributorDimensionPriority": [
            "Region",
            "Channel",
            "Product",
            "Category",
            "Campaign",
        ]
    }


def test_changing_config_changes_dimension_order_without_hardcoding():
    main = _insight("OUTCOME")
    first = _insight("FIRST")
    second = _insight("SECOND")
    first.dimension = "SyntheticOne"
    second.dimension = "SyntheticTwo"
    relationships = [
        _relationship(first.id, main.id),
        _relationship(second.id, main.id),
    ]
    rankings = [_ranked(first.id), _ranked(second.id)]

    first_order = _select(
        main,
        [first, second],
        relationships,
        rankings=rankings,
        config={
            "primaryContributorDimensionPriority": [
                "SyntheticOne",
                "SyntheticTwo",
            ]
        },
    )
    second_order = _select(
        main,
        [first, second],
        relationships,
        rankings=rankings,
        config={
            "primaryContributorDimensionPriority": [
                "SyntheticTwo",
                "SyntheticOne",
            ]
        },
    )

    assert first_order[0][0] is first
    assert second_order[0][0] is second


def test_same_dimension_uses_existing_order_and_unconfigured_stays_eligible():
    main = _insight("OUTCOME")
    higher = _insight("HIGHER")
    lower = _insight("LOWER")
    unconfigured = _insight("UNCONFIGURED")
    for candidate in (higher, lower):
        candidate.dimension = "Configured"
    unconfigured.dimension = "Unconfigured"

    selected = _select(
        main,
        [lower, unconfigured, higher],
        [
            _relationship(lower.id, main.id),
            _relationship(unconfigured.id, main.id),
            _relationship(higher.id, main.id),
        ],
        rankings=[
            _ranked(lower.id, score=0.7),
            _ranked(unconfigured.id, level=PriorityLevel.CRITICAL),
            _ranked(higher.id, score=0.9, rank=2),
        ],
        max_contributors=3,
        config={"primaryContributorDimensionPriority": ["Configured"]},
    )

    assert [item.id for item, _ in selected] == [
        "HIGHER",
        "LOWER",
        "UNCONFIGURED",
    ]


def test_absent_configured_dimensions_preserve_existing_order():
    main = _insight("OUTCOME")
    higher = _insight("HIGHER")
    lower = _insight("LOWER")
    higher.dimension = "DatasetDimensionA"
    lower.dimension = "DatasetDimensionB"

    selected = _select(
        main,
        [lower, higher],
        [
            _relationship(lower.id, main.id),
            _relationship(higher.id, main.id),
        ],
        rankings=[
            _ranked(lower.id, score=0.7),
            _ranked(higher.id, score=0.9, rank=2),
        ],
        config={"primaryContributorDimensionPriority": ["NotPresent"]},
    )

    assert [item.id for item, _ in selected] == ["HIGHER", "LOWER"]


def test_semantics_precede_dimension_policy_and_config_is_not_mutated():
    main = _insight("OUTCOME")
    positive = _insight("POSITIVE")
    negative_offset = _insight("OFFSET")
    positive.dimension = "LaterDimension"
    negative_offset.dimension = "EarlierDimension"
    positive.values["contributorRole"] = "POSITIVE_CONTRIBUTOR"
    negative_offset.values["contributorRole"] = "NEGATIVE_OFFSET"
    config = {
        "primaryContributorDimensionPriority": [
            "EarlierDimension",
            "LaterDimension",
        ]
    }
    config_snapshot = {
        key: list(value) for key, value in config.items()
    }

    selected = _select(
        main,
        [negative_offset, positive],
        [
            _relationship(negative_offset.id, main.id),
            _relationship(positive.id, main.id),
        ],
        rankings=[
            _ranked(negative_offset.id, level=PriorityLevel.CRITICAL),
            _ranked(positive.id, level=PriorityLevel.LOW, rank=2),
        ],
        config=config,
    )

    assert selected[0][0] is positive
    assert config == config_snapshot
