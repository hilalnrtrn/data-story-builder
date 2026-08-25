from enum import Enum

from pydantic import BaseModel, Field


class CausalityStatus(str, Enum):
    NOT_APPLICABLE = "NOT_APPLICABLE"
    ASSOCIATION_ONLY = "ASSOCIATION_ONLY"
    CAUSALITY_NOT_ESTABLISHED = "CAUSALITY_NOT_ESTABLISHED"
    CAUSALITY_ESTABLISHED = "CAUSALITY_ESTABLISHED"


class AllowedCausalityConcept(str, Enum):
    ASSOCIATED_WITH = "ASSOCIATED_WITH"
    COINCIDED_WITH = "COINCIDED_WITH"
    MOVED_ALONGSIDE = "MOVED_ALONGSIDE"


class ForbiddenCausalityConcept(str, Enum):
    CAUSED = "CAUSED"
    LED_TO = "LED_TO"
    BECAUSE_OF = "BECAUSE_OF"
    RESULTED_IN = "RESULTED_IN"
    DRIVEN_BY = "DRIVEN_BY"


class CausalClaimStatus(str, Enum):
    ALLOWED = "ALLOWED"
    BLOCKED = "BLOCKED"


class ClaimType(str, Enum):
    DESCRIPTIVE = "DESCRIPTIVE"
    COMPARATIVE = "COMPARATIVE"
    CORRELATIONAL = "CORRELATIONAL"
    CAUSAL = "CAUSAL"


class CausalEvidenceType(str, Enum):
    CONTROLLED_EXPERIMENT = "CONTROLLED_EXPERIMENT"
    AB_TEST = "AB_TEST"
    RANDOMIZED_INTERVENTION = "RANDOMIZED_INTERVENTION"
    EXPLICIT_CAUSAL_MODEL = "EXPLICIT_CAUSAL_MODEL"
    EXTERNAL_CAUSAL_EVIDENCE = "EXTERNAL_CAUSAL_EVIDENCE"


class CausalEvidence(BaseModel):
    type: CausalEvidenceType
    source: str = Field(min_length=1, pattern=r"\S")
    description: str = Field(min_length=1, pattern=r"\S")

    model_config = {
        "populate_by_name": True,
        "use_enum_values": True,
    }


class CausalClaimGuardResult(BaseModel):
    original_claim: str = Field(
        alias="originalClaim",
        min_length=1,
        pattern=r"\S",
    )
    status: CausalClaimStatus
    blocked_concepts: list[ForbiddenCausalityConcept] = Field(
        default_factory=list,
        alias="blockedConcepts",
    )
    reasons: list[str] = Field(default_factory=list)
    safe_rewrite: str | None = Field(default=None, alias="safeRewrite")

    model_config = {
        "populate_by_name": True,
        "use_enum_values": True,
    }


class CausalityEvaluation(BaseModel):
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
    relationship_id: str = Field(
        alias="relationshipId",
        min_length=1,
        pattern=r"\S",
    )
    source_metric: str = Field(alias="sourceMetric")
    target_metric: str = Field(alias="targetMetric")
    association_present: bool = Field(alias="associationPresent")
    causality_established: bool = Field(alias="causalityEstablished")
    status: CausalityStatus
    causal_evidence: list[CausalEvidence] = Field(
        default_factory=list,
        alias="causalEvidence",
    )
    allowed_concepts: list[AllowedCausalityConcept] = Field(
        default_factory=list,
        alias="allowedConcepts",
    )
    forbidden_concepts: list[ForbiddenCausalityConcept] = Field(
        default_factory=list,
        alias="forbiddenConcepts",
    )
    reasons: list[str] = Field(default_factory=list)

    model_config = {
        "populate_by_name": True,
        "use_enum_values": True,
    }


class CausalityResult(BaseModel):
    evaluations: list[CausalityEvaluation] = Field(default_factory=list)

    model_config = {
        "populate_by_name": True,
        "use_enum_values": True,
    }
