from pydantic import BaseModel, Field


class ContextStatement(BaseModel):
    code: str = Field(min_length=1, pattern=r"\S")
    statement: str = Field(min_length=1, pattern=r"\S")

    model_config = {
        "populate_by_name": True,
        "use_enum_values": True,
    }


class KnownUnknownContextSummary(BaseModel):
    insight_id: str = Field(
        alias="insightId",
        min_length=1,
        pattern=r"\S",
    )
    known: list[ContextStatement] = Field(default_factory=list)
    unknown: list[ContextStatement] = Field(default_factory=list)
    interpretation_limited: bool = Field(alias="interpretationLimited")

    model_config = {
        "populate_by_name": True,
        "use_enum_values": True,
    }


class KnownUnknownContextResult(BaseModel):
    summaries: list[KnownUnknownContextSummary] = Field(default_factory=list)

    model_config = {
        "populate_by_name": True,
        "use_enum_values": True,
    }
