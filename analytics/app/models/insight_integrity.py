from enum import Enum

from pydantic import BaseModel, Field

from app.models.insight import InsightDirection


class IntegrityStatus(str, Enum):
    PASS = "PASS"
    PASS_WITH_WARNINGS = "PASS_WITH_WARNINGS"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    FAIL = "FAIL"


class IntegrityRiskLevel(str, Enum):
    NONE = "NONE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class IntegrityCheckStatus(str, Enum):
    PASS = "PASS"
    WARNING = "WARNING"
    FAIL = "FAIL"


class ContradictionType(str, Enum):
    DATA_CONTRADICTION = "DATA_CONTRADICTION"
    INSIGHT_CONTRADICTION = "INSIGHT_CONTRADICTION"
    SEMANTIC_CONTRADICTION = "SEMANTIC_CONTRADICTION"


class CounterEvidenceItem(BaseModel):
    insight_id: str = Field(alias="insightId")
    relationship_id: str = Field(alias="relationshipId")
    metric: str
    direction: InsightDirection
    reasons: list[str] = Field(default_factory=list)

    model_config = {
        "populate_by_name": True,
        "use_enum_values": True,
    }


class ContradictionFinding(BaseModel):
    type: ContradictionType
    code: str
    related_insight_id: str | None = Field(alias="relatedInsightId")
    reason: str

    model_config = {
        "populate_by_name": True,
        "use_enum_values": True,
    }


class OutlierDependencyCheck(BaseModel):
    level: IntegrityRiskLevel
    detected: bool
    statistic_name: str | None = Field(alias="statisticName")
    original_statistic: float | None = Field(alias="originalStatistic")
    adjusted_statistic: float | None = Field(alias="adjustedStatistic")
    outlier_period: str | None = Field(alias="outlierPeriod")
    reason: str | None

    model_config = {
        "populate_by_name": True,
        "use_enum_values": True,
    }


class OneOffEffectCheck(BaseModel):
    risk: IntegrityRiskLevel
    event_period: str | None = Field(alias="eventPeriod")
    next_period: str | None = Field(alias="nextPeriod")
    baseline_value: float | None = Field(alias="baselineValue")
    event_value: float | None = Field(alias="eventValue")
    next_value: float | None = Field(alias="nextValue")
    reversion_ratio: float | None = Field(alias="reversionRatio")
    reason: str | None

    model_config = {
        "populate_by_name": True,
        "use_enum_values": True,
    }


class ConsistencyCheck(BaseModel):
    code: str
    status: IntegrityCheckStatus
    expected_value: float | None = Field(alias="expectedValue")
    actual_value: float | None = Field(alias="actualValue")
    difference: float | None
    tolerance: float | None
    reason: str

    model_config = {
        "populate_by_name": True,
        "use_enum_values": True,
    }


class InsightIntegrityEvaluation(BaseModel):
    insight_id: str = Field(alias="insightId")
    status: IntegrityStatus
    counter_evidence: list[CounterEvidenceItem] = Field(
        default_factory=list,
        alias="counterEvidence",
    )
    contradictions: list[ContradictionFinding] = Field(default_factory=list)
    outlier_check: OutlierDependencyCheck | None = Field(
        default=None,
        alias="outlierCheck",
    )
    one_off_check: OneOffEffectCheck | None = Field(
        default=None,
        alias="oneOffCheck",
    )
    consistency_checks: list[ConsistencyCheck] = Field(
        default_factory=list,
        alias="consistencyChecks",
    )
    integrity_score: float | None = Field(
        default=None,
        alias="integrityScore",
        ge=0.0,
        le=1.0,
        allow_inf_nan=False,
    )
    integrity_breakdown: dict[str, float] = Field(
        default_factory=dict,
        alias="integrityBreakdown",
    )
    story_eligible: bool = Field(alias="storyEligible")
    requires_qualification: bool = Field(alias="requiresQualification")
    reasons: list[str] = Field(default_factory=list)

    model_config = {
        "populate_by_name": True,
        "use_enum_values": True,
    }


class InsightIntegrityResult(BaseModel):
    evaluations: list[InsightIntegrityEvaluation] = Field(default_factory=list)

    model_config = {
        "populate_by_name": True,
        "use_enum_values": True,
    }
