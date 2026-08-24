from typing import Annotated, Self

from pydantic import BaseModel, Field, model_validator


Identifier = Annotated[
    str,
    Field(min_length=1, pattern=r"\S"),
]


class InsightCluster(BaseModel):
    id: Identifier
    analysis_id: Identifier = Field(alias="analysisId")
    anchor_insight_id: Identifier = Field(alias="anchorInsightId")
    member_insight_ids: list[Identifier] = Field(
        default_factory=list,
        alias="memberInsightIds",
    )
    relationship_ids: list[Identifier] = Field(
        default_factory=list,
        alias="relationshipIds",
    )

    @model_validator(mode="after")
    def validate_references(self) -> Self:
        if self.anchor_insight_id in self.member_insight_ids:
            raise ValueError(
                "anchorInsightId must not appear in memberInsightIds"
            )

        if len(self.member_insight_ids) != len(
            set(self.member_insight_ids)
        ):
            raise ValueError("memberInsightIds must not contain duplicates")

        if len(self.relationship_ids) != len(set(self.relationship_ids)):
            raise ValueError("relationshipIds must not contain duplicates")

        return self

    model_config = {
        "populate_by_name": True,
    }
