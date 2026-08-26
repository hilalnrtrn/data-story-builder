from app.models.insight import (
    Insight,
    InsightDirection,
    InsightType,
    PeriodGranularity,
)
from app.models.relationship import Relationship, RelationshipType
from app.models.story_plan import StoryRole
from app.services.story_planner import (
    build_associated_signal_items,
    build_contributor_items,
    build_counter_signal_items,
    build_main_outcome_item,
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


def _relationship(
    insight: Insight,
    relationship_type: RelationshipType,
) -> Relationship:
    return Relationship(
        id=f"REL-{insight.id}",
        analysisId="ANALYSIS-001",
        sourceInsightId=insight.id,
        targetInsightId="MAIN",
        type=relationship_type,
        strength=0.8,
        confidence=0.8,
    )


def test_main_outcome_role_and_supplied_provenance_are_preserved():
    main = _insight("MAIN")

    item = build_main_outcome_item(
        main,
        cluster_id="CLUSTER-MAIN",
        requires_qualification=True,
        selection_reasons=["Selected cluster anchor."],
    )

    assert item.role == StoryRole.MAIN_OUTCOME
    assert item.insight_id == main.id
    assert item.relationship_id is None
    assert item.cluster_id == "CLUSTER-MAIN"
    assert item.requires_qualification is True
    assert item.selection_reasons == ["Selected cluster anchor."]
    assert item.evidence_codes == []


def test_contributor_roles_and_input_order_are_preserved():
    first = _insight("FIRST")
    second = _insight("SECOND")
    first_relationship = _relationship(
        first, RelationshipType.CONTRIBUTES_TO
    )
    second_relationship = _relationship(
        second, RelationshipType.CONTRIBUTES_TO
    )

    items = build_contributor_items(
        [(first, first_relationship), (second, second_relationship)]
    )

    assert [item.role for item in items] == [
        StoryRole.PRIMARY_CONTRIBUTOR,
        StoryRole.SECONDARY_FINDING,
    ]
    assert [item.insight_id for item in items] == ["FIRST", "SECOND"]
    assert [item.relationship_id for item in items] == [
        first_relationship.id,
        second_relationship.id,
    ]
    assert all(item.evidence_codes == [] for item in items)


def test_counter_signal_role_preserves_references():
    counter = _insight("COUNTER")
    relationship = _relationship(counter, RelationshipType.COUNTER_SIGNAL)

    item = build_counter_signal_items([(counter, relationship)])[0]

    assert item.role == StoryRole.COUNTER_SIGNAL
    assert item.insight_id == counter.id
    assert item.relationship_id == relationship.id
    assert item.evidence_codes == []


def test_associated_signal_role_preserves_references():
    associated = _insight("ASSOCIATED")
    relationship = _relationship(
        associated, RelationshipType.CO_MOVES_WITH
    )

    item = build_associated_signal_items([(associated, relationship)])[0]

    assert item.role == StoryRole.ASSOCIATED_SIGNAL
    assert item.insight_id == associated.id
    assert item.relationship_id == relationship.id
    assert item.evidence_codes == []


def test_signal_input_order_is_preserved():
    first = _insight("FIRST")
    second = _insight("SECOND")
    counter_pairs = [
        (item, _relationship(item, RelationshipType.COUNTER_SIGNAL))
        for item in (first, second)
    ]
    associated_pairs = [
        (item, _relationship(item, RelationshipType.CO_MOVES_WITH))
        for item in (first, second)
    ]

    assert [
        item.insight_id for item in build_counter_signal_items(counter_pairs)
    ] == ["FIRST", "SECOND"]
    assert [
        item.insight_id
        for item in build_associated_signal_items(associated_pairs)
    ] == ["FIRST", "SECOND"]


def test_item_ids_are_deterministic_and_contain_no_random_component():
    main = _insight("MAIN")
    first = build_main_outcome_item(main)
    second = build_main_outcome_item(main)

    assert first.id == second.id == "main_outcome-MAIN"


def test_role_assignment_does_not_mutate_inputs():
    main = _insight("MAIN")
    contributor = _insight("CONTRIBUTOR")
    relationship = _relationship(
        contributor, RelationshipType.CONTRIBUTES_TO
    )
    pairs = [(contributor, relationship)]
    reasons = ["Selected deterministically."]
    snapshots = (
        main.model_dump(),
        contributor.model_dump(),
        relationship.model_dump(),
        list(pairs),
        list(reasons),
    )

    build_main_outcome_item(main, selection_reasons=reasons)
    build_contributor_items(pairs)

    assert main.model_dump() == snapshots[0]
    assert contributor.model_dump() == snapshots[1]
    assert relationship.model_dump() == snapshots[2]
    assert pairs == snapshots[3]
    assert reasons == snapshots[4]
