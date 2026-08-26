import pytest

from app.models.story_plan import (
    StoryMissingContextItem,
    StoryPlanItem,
    StoryRole,
    StorySectionType,
)
from app.services.story_planner import (
    apply_story_size_budget,
    build_story_outline,
)


def _item(item_id: str, role: StoryRole) -> StoryPlanItem:
    return StoryPlanItem(id=item_id, role=role, insightId=f"I-{item_id}")


def _missing(item_id: str) -> StoryMissingContextItem:
    return StoryMissingContextItem(
        id=item_id,
        insightId="MAIN",
        field=item_id,
        status="NOT_AVAILABLE",
        isDataQualityError=False,
        reason=f"{item_id} is unavailable.",
    )


def _collections(size: int = 3):
    return (
        [_item(f"CONTRIBUTOR-{i}", StoryRole.PRIMARY_CONTRIBUTOR) for i in range(size)],
        [_item(f"SECONDARY-{i}", StoryRole.SECONDARY_FINDING) for i in range(size)],
        [_item(f"COUNTER-{i}", StoryRole.COUNTER_SIGNAL) for i in range(size)],
        [_item(f"ASSOCIATED-{i}", StoryRole.ASSOCIATED_SIGNAL) for i in range(size)],
        [_item(f"RISK-{i}", StoryRole.RISK) for i in range(size)],
        [_missing(f"MISSING-{i}") for i in range(size)],
    )


def test_default_story_size_budget_applies_all_limits_and_preserves_order():
    collections = _collections()

    budgeted = apply_story_size_budget(*collections)

    assert [len(items) for items in budgeted] == [2, 1, 2, 1, 1, 2]
    assert [item.id for item in budgeted[0]] == [
        "CONTRIBUTOR-0",
        "CONTRIBUTOR-1",
    ]
    assert [item.id for item in budgeted[2]] == ["COUNTER-0", "COUNTER-1"]
    assert [item.id for item in budgeted[5]] == ["MISSING-0", "MISSING-1"]


def test_custom_zero_limits_return_empty_collections():
    budgeted = apply_story_size_budget(
        *_collections(1),
        max_contributors=0,
        max_secondary_findings=0,
        max_counter_signals=0,
        max_associated_signals=0,
        max_risks=0,
        max_missing_context=0,
    )

    assert budgeted == ([], [], [], [], [], [])


@pytest.mark.parametrize(
    "limit_name",
    [
        "max_contributors",
        "max_secondary_findings",
        "max_counter_signals",
        "max_associated_signals",
        "max_risks",
        "max_missing_context",
    ],
)
def test_negative_story_size_limit_is_rejected(limit_name):
    with pytest.raises(ValueError, match="Story size limits"):
        apply_story_size_budget(*_collections(0), **{limit_name: -1})


def test_story_size_budget_does_not_mutate_inputs():
    collections = _collections()
    snapshots = tuple(
        [item.model_dump() for item in collection]
        for collection in collections
    )

    apply_story_size_budget(*collections)

    assert tuple(
        [item.model_dump() for item in collection]
        for collection in collections
    ) == snapshots


def _outline(
    *,
    context=None,
    contributors=None,
    secondary=None,
    counter=None,
    associated=None,
    risks=None,
    missing=None,
):
    return build_story_outline(
        _item("MAIN", StoryRole.MAIN_OUTCOME),
        context or [],
        contributors or [],
        secondary or [],
        counter or [],
        associated or [],
        risks or [],
        missing or [],
    )


def test_main_outcome_alone_produces_only_outcome_section():
    outline = _outline()

    assert len(outline) == 1
    assert outline[0].type == StorySectionType.OUTCOME
    assert outline[0].order == 1
    assert outline[0].item_ids == ["MAIN"]


def test_outline_omits_empty_sections_and_uses_defined_sequential_order():
    context = [_item("CONTEXT", StoryRole.CONTEXT)]
    contributors = [_item("CONTRIBUTOR", StoryRole.PRIMARY_CONTRIBUTOR)]
    secondary = [_item("SECONDARY", StoryRole.SECONDARY_FINDING)]
    counter = [_item("COUNTER", StoryRole.COUNTER_SIGNAL)]
    associated = [_item("ASSOCIATED", StoryRole.ASSOCIATED_SIGNAL)]
    risks = [_item("RISK", StoryRole.RISK)]
    missing = [_missing("MISSING")]

    outline = _outline(
        context=context,
        contributors=contributors,
        secondary=secondary,
        counter=counter,
        associated=associated,
        risks=risks,
        missing=missing,
    )

    assert [section.type for section in outline] == [
        StorySectionType.CONTEXT,
        StorySectionType.OUTCOME,
        StorySectionType.CONTRIBUTION,
        StorySectionType.SECONDARY_FINDINGS,
        StorySectionType.COUNTER_SIGNALS,
        StorySectionType.ASSOCIATED_SIGNALS,
        StorySectionType.RISKS,
        StorySectionType.LIMITATIONS,
    ]
    assert [section.order for section in outline] == list(range(1, 9))


def test_outline_preserves_item_order_and_uses_missing_context_ids():
    contributors = [
        _item("CONTRIBUTOR-2", StoryRole.PRIMARY_CONTRIBUTOR),
        _item("CONTRIBUTOR-1", StoryRole.SECONDARY_FINDING),
    ]
    missing = [_missing("MISSING-2"), _missing("MISSING-1")]

    outline = _outline(contributors=contributors, missing=missing)

    assert [section.type for section in outline] == [
        StorySectionType.OUTCOME,
        StorySectionType.CONTRIBUTION,
        StorySectionType.LIMITATIONS,
    ]
    assert outline[1].item_ids == ["CONTRIBUTOR-2", "CONTRIBUTOR-1"]
    assert outline[2].item_ids == ["MISSING-2", "MISSING-1"]


def test_repeated_outline_calls_are_identical_and_do_not_mutate_inputs():
    main = _item("MAIN", StoryRole.MAIN_OUTCOME)
    context = [_item("CONTEXT", StoryRole.CONTEXT)]
    contributors = [_item("CONTRIBUTOR", StoryRole.PRIMARY_CONTRIBUTOR)]
    collections = (context, contributors, [], [], [], [], [])
    snapshots = (
        main.model_dump(),
        *(
            [item.model_dump() for item in collection]
            for collection in collections
        ),
    )

    first = build_story_outline(main, *collections)
    second = build_story_outline(main, *collections)

    assert first == second
    assert main.model_dump() == snapshots[0]
    assert tuple(
        [item.model_dump() for item in collection]
        for collection in collections
    ) == snapshots[1:]
