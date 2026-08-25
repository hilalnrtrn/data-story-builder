from enum import Enum

from pydantic import BaseModel, Field


class MissingContextStatus(str, Enum):
    NOT_AVAILABLE = "NOT_AVAILABLE"


class MissingContextItem(BaseModel):
    field: str = Field(min_length=1, pattern=r"\S")
    status: MissingContextStatus
    is_data_quality_error: bool = Field(alias="isDataQualityError")
    reason: str = Field(min_length=1, pattern=r"\S")

    model_config = {
        "populate_by_name": True,
        "use_enum_values": True,
    }


class MissingContextEvaluation(BaseModel):
    insight_id: str = Field(
        alias="insightId",
        min_length=1,
        pattern=r"\S",
    )
    missing_context: list[MissingContextItem] = Field(
        default_factory=list,
        alias="missingContext",
    )
    interpretation_limited: bool = Field(alias="interpretationLimited")
    reasons: list[str] = Field(default_factory=list)

    model_config = {
        "populate_by_name": True,
        "use_enum_values": True,
    }


class MissingContextResult(BaseModel):
    evaluations: list[MissingContextEvaluation] = Field(default_factory=list)

    model_config = {
        "populate_by_name": True,
        "use_enum_values": True,
    }
