from enum import Enum
from typing import Annotated, Self

from pydantic import BaseModel, Field, model_validator

from app.models.causality import ClaimType


NonEmptyString = Annotated[
    str,
    Field(min_length=1, pattern=r"\S"),
]


class StoryRole(str, Enum):
    CONTEXT = "CONTEXT"
    MAIN_OUTCOME = "MAIN_OUTCOME"
    PRIMARY_CONTRIBUTOR = "PRIMARY_CONTRIBUTOR"
    SECONDARY_FINDING = "SECONDARY_FINDING"
    COUNTER_SIGNAL = "COUNTER_SIGNAL"
    ASSOCIATED_SIGNAL = "ASSOCIATED_SIGNAL"
    RISK = "RISK"
    MISSING_CONTEXT = "MISSING_CONTEXT"


class StorySectionType(str, Enum):
    CONTEXT = "CONTEXT"
    OUTCOME = "OUTCOME"
    CONTRIBUTION = "CONTRIBUTION"
    SECONDARY_FINDINGS = "SECONDARY_FINDINGS"
    COUNTER_SIGNALS = "COUNTER_SIGNALS"
    ASSOCIATED_SIGNALS = "ASSOCIATED_SIGNALS"
    RISKS = "RISKS"
    LIMITATIONS = "LIMITATIONS"


class StoryPlanItem(BaseModel):
    id: NonEmptyString
    role: StoryRole
    insight_id: NonEmptyString | None = Field(
        default=None,
        alias="insightId",
    )
    relationship_id: NonEmptyString | None = Field(
        default=None,
        alias="relationshipId",
    )
    cluster_id: NonEmptyString | None = Field(
        default=None,
        alias="clusterId",
    )
    evidence_codes: list[NonEmptyString] = Field(
        default_factory=list,
        alias="evidenceCodes",
    )
    requires_qualification: bool = Field(
        default=False,
        alias="requiresQualification",
    )
    selection_reasons: list[NonEmptyString] = Field(
        default_factory=list,
        alias="selectionReasons",
    )

    @model_validator(mode="after")
    def validate_item(self) -> Self:
        if self.insight_id is None:
            raise ValueError("insightId is required")

        if len(self.evidence_codes) != len(set(self.evidence_codes)):
            raise ValueError("evidenceCodes must not contain duplicates")

        if len(self.selection_reasons) != len(
            set(self.selection_reasons)
        ):
            raise ValueError("selectionReasons must not contain duplicates")

        return self

    model_config = {
        "populate_by_name": True,
        "use_enum_values": True,
    }


class StoryMissingContextItem(BaseModel):
    id: NonEmptyString
    role: StoryRole = StoryRole.MISSING_CONTEXT
    insight_id: NonEmptyString = Field(alias="insightId")
    field: NonEmptyString
    status: NonEmptyString
    is_data_quality_error: bool = Field(alias="isDataQualityError")
    reason: NonEmptyString

    @model_validator(mode="after")
    def require_missing_context_role(self) -> Self:
        if self.role != StoryRole.MISSING_CONTEXT:
            raise ValueError("role must be MISSING_CONTEXT")

        return self

    model_config = {
        "populate_by_name": True,
        "use_enum_values": True,
    }


class StoryCausalityConstraint(BaseModel):
    relationship_id: NonEmptyString = Field(alias="relationshipId")
    source_insight_id: NonEmptyString = Field(alias="sourceInsightId")
    target_insight_id: NonEmptyString = Field(alias="targetInsightId")
    claim_type: ClaimType = Field(alias="claimType")
    association_present: bool = Field(alias="associationPresent")
    causality_established: bool = Field(alias="causalityEstablished")
    status: NonEmptyString
    allowed_concepts: list[NonEmptyString] = Field(
        default_factory=list,
        alias="allowedConcepts",
    )
    forbidden_concepts: list[NonEmptyString] = Field(
        default_factory=list,
        alias="forbiddenConcepts",
    )
    reasons: list[NonEmptyString] = Field(default_factory=list)

    @model_validator(mode="after")
    def reject_duplicate_values(self) -> Self:
        if len(self.allowed_concepts) != len(set(self.allowed_concepts)):
            raise ValueError("allowedConcepts must not contain duplicates")

        if len(self.forbidden_concepts) != len(
            set(self.forbidden_concepts)
        ):
            raise ValueError("forbiddenConcepts must not contain duplicates")

        if len(self.reasons) != len(set(self.reasons)):
            raise ValueError("reasons must not contain duplicates")

        return self

    model_config = {
        "populate_by_name": True,
        "use_enum_values": True,
    }


class StorySection(BaseModel):
    order: int = Field(ge=1)
    type: StorySectionType
    item_ids: list[NonEmptyString] = Field(
        default_factory=list,
        alias="itemIds",
    )

    @model_validator(mode="after")
    def reject_duplicate_item_ids(self) -> Self:
        if len(self.item_ids) != len(set(self.item_ids)):
            raise ValueError("itemIds must not contain duplicates")

        return self

    model_config = {
        "populate_by_name": True,
        "use_enum_values": True,
    }


class StructuredStoryPlan(BaseModel):
    analysis_id: NonEmptyString = Field(alias="analysisId")
    main_outcome: StoryPlanItem = Field(alias="mainOutcome")
    context: list[StoryPlanItem] = Field(default_factory=list)
    contributors: list[StoryPlanItem] = Field(default_factory=list)
    secondary_findings: list[StoryPlanItem] = Field(
        default_factory=list,
        alias="secondaryFindings",
    )
    counter_signals: list[StoryPlanItem] = Field(
        default_factory=list,
        alias="counterSignals",
    )
    associated_signals: list[StoryPlanItem] = Field(
        default_factory=list,
        alias="associatedSignals",
    )
    risks: list[StoryPlanItem] = Field(default_factory=list)
    missing_context: list[StoryMissingContextItem] = Field(
        default_factory=list,
        alias="missingContext",
    )
    causality_constraints: list[StoryCausalityConstraint] = Field(
        default_factory=list,
        alias="causalityConstraints",
    )
    outline: list[StorySection] = Field(default_factory=list)
    interpretation_limited: bool = Field(
        default=False,
        alias="interpretationLimited",
    )
    planner_version: NonEmptyString = Field(
        default="day12-v1",
        alias="plannerVersion",
    )

    @model_validator(mode="after")
    def validate_plan(self) -> Self:
        if self.main_outcome.role != StoryRole.MAIN_OUTCOME:
            raise ValueError("mainOutcome role must be MAIN_OUTCOME")

        plan_items = [
            self.main_outcome,
            *self.context,
            *self.contributors,
            *self.secondary_findings,
            *self.counter_signals,
            *self.associated_signals,
            *self.risks,
        ]
        plan_item_ids = [item.id for item in plan_items]
        if len(plan_item_ids) != len(set(plan_item_ids)):
            raise ValueError("StoryPlanItem ids must be unique")

        missing_context_ids = [item.id for item in self.missing_context]
        if len(missing_context_ids) != len(set(missing_context_ids)):
            raise ValueError("Missing-context item ids must be unique")

        section_orders = [section.order for section in self.outline]
        if len(section_orders) != len(set(section_orders)):
            raise ValueError("Story section order values must be unique")

        return self

    model_config = {
        "populate_by_name": True,
        "use_enum_values": True,
    }
