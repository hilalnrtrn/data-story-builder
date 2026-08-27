from enum import Enum
from typing import Annotated, Any, Self

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.causality import CausalityStatus
from app.models.insight_integrity import CounterEvidenceItem
from app.models.missing_context import MissingContextItem


NonBlankString = Annotated[str, Field(min_length=1, pattern=r"\S")]


class HypothesisStatus(str, Enum):
    OPEN = "OPEN"
    SUPPORTED = "SUPPORTED"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"


class HypothesisEvidenceReference(BaseModel):
    insight_id: NonBlankString = Field(alias="insightId")
    evidence_code: NonBlankString = Field(alias="evidenceCode")

    model_config = {
        "populate_by_name": True,
        "use_enum_values": True,
    }


class HypothesisMissingContextReference(BaseModel):
    source_insight_id: NonBlankString = Field(alias="sourceInsightId")
    item: MissingContextItem

    model_config = {
        "populate_by_name": True,
        "use_enum_values": True,
    }


class Hypothesis(BaseModel):
    id: NonBlankString
    analysis_id: NonBlankString = Field(alias="analysisId")
    statement: NonBlankString
    status: HypothesisStatus
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        allow_inf_nan=False,
    )
    source_insight_ids: list[NonBlankString] = Field(
        default_factory=list,
        alias="sourceInsightIds",
    )
    source_relationship_ids: list[NonBlankString] = Field(
        default_factory=list,
        alias="sourceRelationshipIds",
    )
    supporting_evidence: list[HypothesisEvidenceReference] = Field(
        default_factory=list,
        alias="supportingEvidence",
    )
    counter_evidence: list[CounterEvidenceItem] = Field(
        default_factory=list,
        alias="counterEvidence",
    )
    missing_context: list[HypothesisMissingContextReference] = Field(
        default_factory=list,
        alias="missingContext",
    )
    causality_status: CausalityStatus = Field(alias="causalityStatus")
    reasons: list[NonBlankString] = Field(default_factory=list)
    tracker_version: NonBlankString = Field(alias="trackerVersion")

    @field_validator("confidence", mode="before")
    @classmethod
    def reject_boolean_confidence(cls, value: Any) -> Any:
        if isinstance(value, bool):
            raise ValueError("confidence must be a number, not a boolean")

        return value

    @model_validator(mode="after")
    def reject_duplicate_references(self) -> Self:
        self._require_unique(self.source_insight_ids, "sourceInsightIds")
        self._require_unique(
            self.source_relationship_ids,
            "sourceRelationshipIds",
        )

        evidence_keys = [
            (reference.insight_id, reference.evidence_code)
            for reference in self.supporting_evidence
        ]
        self._require_unique(evidence_keys, "supportingEvidence")

        missing_context_keys = [
            (reference.source_insight_id, reference.item.field)
            for reference in self.missing_context
        ]
        self._require_unique(missing_context_keys, "missingContext")

        return self

    @staticmethod
    def _require_unique(values: list[Any], field_name: str) -> None:
        if len(values) != len(set(values)):
            raise ValueError(f"{field_name} must not contain duplicates")

    model_config = {
        "populate_by_name": True,
        "use_enum_values": True,
    }
