from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class InsightType(str, Enum):
    CHANGE = "CHANGE"
    TREND = "TREND"
    ANOMALY = "ANOMALY"


class InsightDirection(str, Enum):
    UP = "UP"
    DOWN = "DOWN"
    STABLE = "STABLE"
    HIGH = "HIGH"
    LOW = "LOW"


class PeriodGranularity(str, Enum):
    MONTH = "MONTH"
    QUARTER = "QUARTER"


class Evidence(BaseModel):
    code: str
    label: str
    value: Any
    unit: str | None = None


class InsightSource(BaseModel):
    file_name: str | None = Field(
        default=None,
        alias="fileName",
    )
    row_count: int | None = Field(
        default=None,
        alias="rowCount",
    )


class Insight(BaseModel):
    id: str
    analysis_id: str = Field(alias="analysisId")

    type: InsightType
    metric: str

    dimension: str | None = None
    segment: str | None = None

    period_granularity: PeriodGranularity = Field(
        alias="periodGranularity",
    )

    period: dict[str, str]
    direction: InsightDirection

    values: dict[str, Any] = Field(default_factory=dict)
    detection: dict[str, Any] = Field(default_factory=dict)

    evidence: list[Evidence] = Field(default_factory=list)

    source: InsightSource | None = None

    model_config = {
        "populate_by_name": True,
        "use_enum_values": True,
    }