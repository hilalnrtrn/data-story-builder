import pytest

from app.models.insight import (
    Insight,
    InsightDirection,
    InsightType,
    PeriodGranularity,
)
from app.models.story_plan import (
    StoryMissingContextItem,
    StoryPlanItem,
    StoryRole,
)
from app.services.story_planner import (
    build_insight_story_key,
    remove_redundant_missing_context,
    remove_redundant_story_items,
)


def _insight(
    insight_id: str,
    *,
    insight_type: InsightType = InsightType.CHANGE,
    metric: str = "Revenue",
    period: dict[str, str] | None = None,
    dimension: str | None = None,
    segment: str | None = None,
) -> Insight:
    return Insight(
        id=insight_id,
        analysisId="ANALYSIS-001",
        type=insight_type,
        metric=metric,
        dimension=dimension,
        segment=segment,
        periodGranularity=PeriodGranularity.MONTH,
        period=period or {"previous": "2025-05", "current": "2025-06"},
        direction=InsightDirection.UP,
    )


def _item(insight_id: str, role: StoryRole, suffix: str = "") -> StoryPlanItem:
    return StoryPlanItem(
        id=f"{role.value}-{insight_id}{suffix}",
        role=role,
        insightId=insight_id,
    )


def _missing_context(
    item_id: str,
    field: str,
) -> StoryMissingContextItem:
    return StoryMissingContextItem(
        id=item_id,
        insightId="REVENUE",
        field=field,
        status="NOT_AVAILABLE",
        isDataQualityError=False,
        reason=f"{field} is unavailable.",
    )


def test_repeated_insight_id_is_removed_and_first_role_wins():
    insight = _insight("SAME")
    first = _item(insight.id, StoryRole.MAIN_OUTCOME)
    later = _item(insight.id, StoryRole.RISK, "-LATER")

    assert remove_redundant_story_items(
        [first, later], [insight]
    ) == [first]


def test_same_analytical_event_is_redundant_even_when_types_differ():
    change = _insight("CHANGE", insight_type=InsightType.CHANGE)
    anomaly = _insight("ANOMALY", insight_type=InsightType.ANOMALY)
    first = _item(change.id, StoryRole.MAIN_OUTCOME)
    later = _item(anomaly.id, StoryRole.RISK)

    assert build_insight_story_key(change) == build_insight_story_key(anomaly)
    assert remove_redundant_story_items(
        [first, later], [change, anomaly]
    ) == [first]


@pytest.mark.parametrize(
    "changed",
    [
        _insight(
            "DIFFERENT-PERIOD",
            period={"previous": "2025-06", "current": "2025-07"},
        ),
        _insight("DIFFERENT-DIMENSION", dimension="Region"),
        _insight("DIFFERENT-SEGMENT", segment="North"),
    ],
)
def test_different_period_dimension_or_segment_is_not_redundant(changed):
    original = _insight("ORIGINAL")
    items = [
        _item(original.id, StoryRole.MAIN_OUTCOME),
        _item(changed.id, StoryRole.SECONDARY_FINDING),
    ]

    assert remove_redundant_story_items(
        items, [original, changed]
    ) == items


def test_story_key_normalizes_strings_and_period_dictionary_order():
    first = _insight(
        "FIRST",
        metric=" Revenue ",
        period={" Previous ": " 2025-05 ", "CURRENT": "2025-06"},
        dimension=" Region ",
        segment=" NORTH ",
    )
    second = _insight(
        "SECOND",
        metric="revenue",
        period={"current": "2025-06", "previous": "2025-05"},
        dimension="region",
        segment="north",
    )

    assert build_insight_story_key(first) == build_insight_story_key(second)


def test_none_scope_remains_distinct_from_populated_scope():
    none_scope = _insight("NONE", dimension=None)
    populated = _insight("POPULATED", dimension="none")

    assert build_insight_story_key(none_scope) != build_insight_story_key(
        populated
    )


def test_retained_story_item_order_is_preserved():
    first = _insight("FIRST", metric="Revenue")
    duplicate = _insight("DUPLICATE", metric=" revenue ")
    second = _insight("SECOND", metric="Orders")
    items = [
        _item(first.id, StoryRole.MAIN_OUTCOME),
        _item(duplicate.id, StoryRole.ASSOCIATED_SIGNAL),
        _item(second.id, StoryRole.SECONDARY_FINDING),
    ]

    assert remove_redundant_story_items(
        items, [second, duplicate, first]
    ) == [items[0], items[2]]


def test_missing_referenced_insight_raises_value_error():
    with pytest.raises(ValueError, match="missing Insight"):
        remove_redundant_story_items(
            [_item("MISSING", StoryRole.RISK)],
            [],
        )


def test_duplicate_insight_ids_raise_value_error():
    insight = _insight("DUPLICATE")

    with pytest.raises(ValueError, match="Duplicate Insight"):
        remove_redundant_story_items([], [insight, insight])


def test_story_item_inputs_are_not_mutated():
    first = _insight("FIRST")
    duplicate = _insight("DUPLICATE")
    items = [
        _item(first.id, StoryRole.MAIN_OUTCOME),
        _item(duplicate.id, StoryRole.RISK),
    ]
    insights = [first, duplicate]
    snapshots = (
        [item.model_dump() for item in items],
        [insight.model_dump() for insight in insights],
    )

    remove_redundant_story_items(items, insights)

    assert [item.model_dump() for item in items] == snapshots[0]
    assert [insight.model_dump() for insight in insights] == snapshots[1]


def test_missing_context_normalization_deduplicates_and_first_wins():
    first = _missing_context("FIRST", "CompetitorPrice")
    duplicate_case = _missing_context("SECOND", "competitorprice")
    duplicate_space = _missing_context("THIRD", " CompetitorPrice ")
    different = _missing_context("FOURTH", "UnitPrice")

    assert remove_redundant_missing_context(
        [first, duplicate_case, duplicate_space, different]
    ) == [first, different]


def test_missing_context_input_is_not_mutated():
    items = [
        _missing_context("FIRST", "UnitPrice"),
        _missing_context("SECOND", " unitprice "),
    ]
    snapshot = [item.model_dump() for item in items]

    remove_redundant_missing_context(items)

    assert [item.model_dump() for item in items] == snapshot
