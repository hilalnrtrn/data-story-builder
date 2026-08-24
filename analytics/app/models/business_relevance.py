from enum import Enum

from pydantic import BaseModel, Field


class BusinessImpactDirection(str, Enum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    NEUTRAL = "NEUTRAL"
    MIXED = "MIXED"
    CONTEXT_DEPENDENT = "CONTEXT_DEPENDENT"


class PriorityLevel(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class BusinessRelevanceComponent(BaseModel):
    name: str
    score: float = Field(
        ge=0.0,
        le=1.0,
        allow_inf_nan=False,
    )
    reason: str


class BusinessRelevanceEvaluation(BaseModel):
    insight_id: str = Field(
        alias="insightId",
        min_length=1,
        pattern=r"\S",
    )
    business_relevance: float = Field(
        alias="businessRelevance",
        ge=0.0,
        le=1.0,
        allow_inf_nan=False,
    )
    impact_direction: BusinessImpactDirection = Field(
        alias="impactDirection",
    )
    components: list[BusinessRelevanceComponent] = Field(
        default_factory=list,
    )
    reasons: list[str] = Field(default_factory=list)

    model_config = {
        "populate_by_name": True,
        "use_enum_values": True,
    }


class PriorityEvaluation(BaseModel):
    insight_id: str = Field(
        alias="insightId",
        min_length=1,
        pattern=r"\S",
    )
    priority_score: float = Field(
        alias="priorityScore",
        ge=0.0,
        le=1.0,
        allow_inf_nan=False,
    )
    priority_level: PriorityLevel = Field(alias="priorityLevel")
    breakdown: dict[str, float] = Field(default_factory=dict)
    reasons: list[str] = Field(default_factory=list)

    model_config = {
        "populate_by_name": True,
        "use_enum_values": True,
    }


class RankedInsight(BaseModel):
    rank: int = Field(ge=1)
    insight_id: str = Field(
        alias="insightId",
        min_length=1,
        pattern=r"\S",
    )
    priority: PriorityEvaluation
    business_relevance: BusinessRelevanceEvaluation = Field(
        alias="businessRelevance",
    )

    model_config = {
        "populate_by_name": True,
        "use_enum_values": True,
    }


class BusinessRelevanceResult(BaseModel):
    business_evaluations: list[BusinessRelevanceEvaluation] = Field(
        default_factory=list,
        alias="businessEvaluations",
    )
    priority_evaluations: list[PriorityEvaluation] = Field(
        default_factory=list,
        alias="priorityEvaluations",
    )
    ranked_insights: list[RankedInsight] = Field(
        default_factory=list,
        alias="rankedInsights",
    )
    top_ranked_insights: list[RankedInsight] = Field(
        default_factory=list,
        alias="topRankedInsights",
    )

    model_config = {
        "populate_by_name": True,
        "use_enum_values": True,
    }
