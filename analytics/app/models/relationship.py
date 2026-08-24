from enum import Enum
from typing import Any, Self

from pydantic import BaseModel, Field, model_validator


class RelationshipType(str, Enum):
    CONTRIBUTES_TO = "CONTRIBUTES_TO"
    COUNTER_SIGNAL = "COUNTER_SIGNAL"
    CO_MOVES_WITH = "CO_MOVES_WITH"
    RELATED_ANOMALY = "RELATED_ANOMALY"
    DRILLDOWN_OF = "DRILLDOWN_OF"


class Relationship(BaseModel):
    id: str = Field(min_length=1, pattern=r"\S")
    analysis_id: str = Field(
        alias="analysisId",
        min_length=1,
        pattern=r"\S",
    )
    source_insight_id: str = Field(
        alias="sourceInsightId",
        min_length=1,
        pattern=r"\S",
    )
    target_insight_id: str = Field(
        alias="targetInsightId",
        min_length=1,
        pattern=r"\S",
    )
    type: RelationshipType
    strength: float = Field(
        ge=0.0,
        le=1.0,
        allow_inf_nan=False,
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        allow_inf_nan=False,
    )
    strength_breakdown: dict[str, Any] = Field(
        default_factory=dict,
        alias="strengthBreakdown",
    )
    confidence_breakdown: dict[str, Any] = Field(
        default_factory=dict,
        alias="confidenceBreakdown",
    )
    reasons: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def reject_self_edge(self) -> Self:
        if self.source_insight_id == self.target_insight_id:
            raise ValueError(
                "sourceInsightId and targetInsightId must differ"
            )

        return self

    model_config = {
        "populate_by_name": True,
        "use_enum_values": True,
    }
