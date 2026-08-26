import pytest

from app.models.causality import (
    AllowedCausalityConcept,
    CausalityEvaluation,
    CausalityStatus,
    ClaimType,
    ForbiddenCausalityConcept,
)
from app.models.context_summary import KnownUnknownContextSummary
from app.models.insight import (
    Insight,
    InsightDirection,
    InsightType,
    PeriodGranularity,
)
from app.models.missing_context import (
    MissingContextEvaluation,
    MissingContextItem,
    MissingContextStatus,
)
from app.models.relationship import Relationship, RelationshipType
from app.models.story_plan import StoryRole
from app.services.story_planner import (
    build_causality_constraints,
    build_story_missing_context_items,
    resolve_interpretation_limited,
    select_missing_context,
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


def _relationship(relationship_id: str, source: str, target: str) -> Relationship:
    return Relationship(
        id=relationship_id,
        analysisId="ANALYSIS-001",
        sourceInsightId=source,
        targetInsightId=target,
        type=RelationshipType.CO_MOVES_WITH,
        strength=0.8,
        confidence=0.8,
    )


def _causality(
    relationship: Relationship,
    *,
    association: bool = True,
    established: bool = False,
) -> CausalityEvaluation:
    return CausalityEvaluation(
        relationshipId=relationship.id,
        sourceInsightId=relationship.source_insight_id,
        targetInsightId=relationship.target_insight_id,
        sourceMetric=relationship.source_insight_id,
        targetMetric=relationship.target_insight_id,
        associationPresent=association,
        causalityEstablished=established,
        status=(
            CausalityStatus.CAUSALITY_ESTABLISHED
            if established
            else CausalityStatus.CAUSALITY_NOT_ESTABLISHED
            if association
            else CausalityStatus.NOT_APPLICABLE
        ),
        allowedConcepts=[AllowedCausalityConcept.ASSOCIATED_WITH],
        forbiddenConcepts=[ForbiddenCausalityConcept.CAUSED],
        reasons=["Structured Day 10 reason."],
    )


def _context_item(
    field: str,
    *,
    data_quality_error: bool = False,
) -> MissingContextItem:
    return MissingContextItem(
        field=field,
        status=MissingContextStatus.NOT_AVAILABLE,
        isDataQualityError=data_quality_error,
        reason=f"{field} is unavailable.",
    )


def _context_evaluation(
    insight_id: str,
    items: list[MissingContextItem],
) -> MissingContextEvaluation:
    return MissingContextEvaluation(
        insightId=insight_id,
        missingContext=items,
        interpretationLimited=bool(items),
    )


def test_matching_selected_relationship_copies_causality_constraint_fields():
    relationship = _relationship("REL-1", "MARKETING", "REVENUE")
    evaluation = _causality(relationship)

    constraint = build_causality_constraints(
        [relationship], [evaluation]
    )[0]

    assert constraint.relationship_id == relationship.id
    assert constraint.source_insight_id == "MARKETING"
    assert constraint.target_insight_id == "REVENUE"
    assert constraint.claim_type == ClaimType.CORRELATIONAL
    assert constraint.association_present is True
    assert constraint.causality_established is False
    assert constraint.status == CausalityStatus.CAUSALITY_NOT_ESTABLISHED
    assert constraint.allowed_concepts == ["ASSOCIATED_WITH"]
    assert constraint.forbidden_concepts == ["CAUSED"]
    assert constraint.reasons == ["Structured Day 10 reason."]


def test_non_selected_and_unmatched_relationships_do_not_create_constraints():
    selected = _relationship("SELECTED", "A", "B")
    unselected = _relationship("UNSELECTED", "C", "D")

    assert build_causality_constraints(
        [selected], [_causality(unselected)]
    ) == []
    assert build_causality_constraints([selected], []) == []


@pytest.mark.parametrize(
    ("association", "established", "expected"),
    [
        (True, False, ClaimType.CORRELATIONAL),
        (True, True, ClaimType.CAUSAL),
        (False, False, ClaimType.DESCRIPTIVE),
    ],
)
def test_claim_type_mapping(association, established, expected):
    relationship = _relationship("REL-1", "A", "B")

    constraint = build_causality_constraints(
        [relationship],
        [
            _causality(
                relationship,
                association=association,
                established=established,
            )
        ],
    )[0]

    assert constraint.claim_type == expected


def test_selected_relationship_order_is_preserved():
    second = _relationship("REL-2", "C", "D")
    first = _relationship("REL-1", "A", "B")

    constraints = build_causality_constraints(
        [second, first], [_causality(first), _causality(second)]
    )

    assert [item.relationship_id for item in constraints] == ["REL-2", "REL-1"]


def test_duplicate_selected_relationship_ids_are_rejected():
    relationship = _relationship("REL-1", "A", "B")

    with pytest.raises(ValueError, match="Duplicate Relationship"):
        build_causality_constraints([relationship, relationship], [])


def test_selected_insight_context_is_ordered_and_unselected_is_excluded():
    first = _insight("FIRST")
    second = _insight("SECOND")
    unselected = _insight("UNSELECTED")
    first_items = [_context_item("UnitPrice"), _context_item("PricingChange")]
    second_items = [_context_item("CompetitorPrice")]

    selected = select_missing_context(
        [second, first],
        [
            _context_evaluation(first.id, first_items),
            _context_evaluation(unselected.id, [_context_item("Ignored")]),
            _context_evaluation(second.id, second_items),
        ],
        max_missing_context=3,
    )

    assert [(insight.id, item.field) for insight, item in selected] == [
        ("SECOND", "CompetitorPrice"),
        ("FIRST", "UnitPrice"),
        ("FIRST", "PricingChange"),
    ]


def test_data_quality_items_are_excluded():
    insight = _insight("REVENUE")

    selected = select_missing_context(
        [insight],
        [_context_evaluation(insight.id, [_context_item("Bad", data_quality_error=True)])],
    )

    assert selected == []


def test_field_deduplication_is_trimmed_case_insensitive_and_earliest_wins():
    first = _insight("FIRST")
    second = _insight("SECOND")
    first_item = _context_item("CompetitorPrice")
    duplicate = _context_item(" competitorprice ")

    selected = select_missing_context(
        [first, second],
        [
            _context_evaluation(second.id, [duplicate]),
            _context_evaluation(first.id, [first_item]),
        ],
    )

    assert selected == [(first, first_item)]


def test_missing_context_limit_zero_and_negative_behavior():
    insight = _insight("REVENUE")
    evaluation = _context_evaluation(insight.id, [_context_item("UnitPrice")])

    assert len(select_missing_context([insight], [evaluation], 1)) == 1
    assert select_missing_context([insight], [evaluation], 0) == []
    with pytest.raises(ValueError, match="max_missing_context"):
        select_missing_context([insight], [evaluation], -1)


def test_story_missing_context_item_preserves_contract_and_deterministic_id():
    insight = _insight("REVENUE")
    context = _context_item("UnitPrice")

    first = build_story_missing_context_items([(insight, context)])[0]
    second = build_story_missing_context_items([(insight, context)])[0]

    assert first.role == StoryRole.MISSING_CONTEXT
    assert first.insight_id == insight.id
    assert first.field == context.field
    assert first.status == context.status
    assert first.is_data_quality_error is False
    assert first.reason == context.reason
    assert first.id == second.id


def test_interpretation_limited_uses_matching_summary_or_selected_context():
    insight = _insight("REVENUE")
    unrelated_summary = KnownUnknownContextSummary(
        insightId="OTHER", interpretationLimited=True
    )
    matching_summary = KnownUnknownContextSummary(
        insightId=insight.id, interpretationLimited=True
    )
    selected_context = [(insight, _context_item("UnitPrice"))]

    assert resolve_interpretation_limited([insight], [matching_summary], [])
    assert resolve_interpretation_limited(
        [insight], [unrelated_summary], selected_context
    )
    assert not resolve_interpretation_limited(
        [insight], [unrelated_summary], []
    )


def test_inputs_are_not_mutated():
    insight = _insight("REVENUE")
    relationship = _relationship("REL-1", "MARKETING", insight.id)
    evaluation = _causality(relationship)
    context_evaluation = _context_evaluation(
        insight.id, [_context_item("UnitPrice")]
    )
    summary = KnownUnknownContextSummary(
        insightId=insight.id, interpretationLimited=True
    )
    collections = (
        [relationship],
        [evaluation],
        [insight],
        [context_evaluation],
        [summary],
    )
    snapshots = tuple(
        [item.model_dump() for item in collection]
        for collection in collections
    )

    build_causality_constraints(collections[0], collections[1])
    selected = select_missing_context(collections[2], collections[3])
    build_story_missing_context_items(selected)
    resolve_interpretation_limited(collections[2], collections[4], selected)

    assert tuple(
        [item.model_dump() for item in collection]
        for collection in collections
    ) == snapshots
