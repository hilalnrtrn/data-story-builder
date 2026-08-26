import pytest
from pydantic import ValidationError

from app.models.causality import ClaimType
from app.models.story_plan import (
    StoryCausalityConstraint,
    StoryMissingContextItem,
    StoryPlanItem,
    StoryRole,
    StorySection,
    StorySectionType,
    StructuredStoryPlan,
)


def _plan_item(**overrides) -> StoryPlanItem:
    values = {
        "id": "OUTCOME-REVENUE",
        "role": StoryRole.MAIN_OUTCOME,
        "insightId": "CHANGE-Revenue-2025-05-2025-06",
        "evidenceCodes": ["CHANGE_VALUES"],
        "selectionReasons": ["Highest-ranked eligible outcome."],
    }
    values.update(overrides)
    return StoryPlanItem(**values)


def _causality_constraint(**overrides) -> StoryCausalityConstraint:
    values = {
        "relationshipId": "CO_MOVES_WITH-MARKETING-REVENUE",
        "sourceInsightId": "CHANGE-MarketingSpend-2025-05-2025-06",
        "targetInsightId": "CHANGE-Revenue-2025-05-2025-06",
        "claimType": ClaimType.CORRELATIONAL,
        "associationPresent": True,
        "causalityEstablished": False,
        "status": "CAUSALITY_NOT_ESTABLISHED",
        "allowedConcepts": ["ASSOCIATED_WITH"],
        "forbiddenConcepts": ["CAUSED"],
        "reasons": ["Association evidence does not establish causality."],
    }
    values.update(overrides)
    return StoryCausalityConstraint(**values)


def test_valid_structured_story_plan_can_be_created():
    plan = StructuredStoryPlan(
        analysisId="ANALYSIS-001",
        mainOutcome=_plan_item(),
        causalityConstraints=[_causality_constraint()],
        outline=[
            StorySection(
                order=1,
                type=StorySectionType.OUTCOME,
                itemIds=["OUTCOME-REVENUE"],
            )
        ],
    )

    serialized = plan.model_dump(by_alias=True)

    assert serialized["analysisId"] == "ANALYSIS-001"
    assert serialized["mainOutcome"]["role"] == "MAIN_OUTCOME"
    assert serialized["plannerVersion"] == "day12-v1"


def test_story_plan_item_rejects_missing_insight_id():
    with pytest.raises(ValidationError):
        _plan_item(insightId=None)


def test_story_plan_item_rejects_duplicate_evidence_codes():
    with pytest.raises(ValidationError):
        _plan_item(evidenceCodes=["CHANGE_VALUES", "CHANGE_VALUES"])


def test_main_outcome_rejects_non_main_outcome_role():
    with pytest.raises(ValidationError):
        StructuredStoryPlan(
            analysisId="ANALYSIS-001",
            mainOutcome=_plan_item(role=StoryRole.CONTEXT),
        )


def test_missing_context_item_rejects_non_missing_context_role():
    with pytest.raises(ValidationError):
        StoryMissingContextItem(
            id="MISSING-COMPETITOR-PRICE",
            role=StoryRole.RISK,
            insightId="CHANGE-Revenue-2025-05-2025-06",
            field="CompetitorPrice",
            status="NOT_AVAILABLE",
            isDataQualityError=False,
            reason="Competitor pricing context is unavailable.",
        )


def test_duplicate_story_plan_item_ids_across_collections_are_rejected():
    with pytest.raises(ValidationError):
        StructuredStoryPlan(
            analysisId="ANALYSIS-001",
            mainOutcome=_plan_item(),
            context=[
                _plan_item(
                    role=StoryRole.CONTEXT,
                    insightId="TREND-Revenue-2025",
                )
            ],
        )


def test_duplicate_story_section_orders_are_rejected():
    with pytest.raises(ValidationError):
        StructuredStoryPlan(
            analysisId="ANALYSIS-001",
            mainOutcome=_plan_item(),
            outline=[
                StorySection(order=1, type=StorySectionType.OUTCOME),
                StorySection(order=1, type=StorySectionType.LIMITATIONS),
            ],
        )


def test_causality_constraint_accepts_existing_correlational_claim_type():
    constraint = _causality_constraint()

    assert constraint.claim_type == ClaimType.CORRELATIONAL
    assert constraint.model_dump(by_alias=True)["claimType"] == (
        "CORRELATIONAL"
    )


@pytest.mark.parametrize(
    ("field_name", "duplicate_value"),
    [
        ("allowedConcepts", "ASSOCIATED_WITH"),
        ("forbiddenConcepts", "CAUSED"),
    ],
)
def test_causality_constraint_rejects_duplicate_concepts(
    field_name,
    duplicate_value,
):
    with pytest.raises(ValidationError):
        _causality_constraint(
            **{field_name: [duplicate_value, duplicate_value]}
        )
