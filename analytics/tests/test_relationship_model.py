import pytest
from pydantic import ValidationError

from app.models.relationship import Relationship, RelationshipType


def _relationship(**overrides) -> Relationship:
    values = {
        "id": "REL-001",
        "analysisId": "ANALYSIS-001",
        "sourceInsightId": "INSIGHT-001",
        "targetInsightId": "INSIGHT-002",
        "type": RelationshipType.CONTRIBUTES_TO,
        "strength": 0.8,
        "confidence": 0.9,
    }
    values.update(overrides)
    return Relationship(**values)


def test_relationship_types_serialize_to_required_values():
    assert [relationship_type.value for relationship_type in RelationshipType] == [
        "CONTRIBUTES_TO",
        "COUNTER_SIGNAL",
        "CO_MOVES_WITH",
        "RELATED_ANOMALY",
        "DRILLDOWN_OF",
    ]

    for relationship_type in RelationshipType:
        relationship = _relationship(type=relationship_type)
        assert relationship.model_dump()["type"] == relationship_type.value


def test_relationship_serializes_with_camel_case_aliases():
    relationship = _relationship(
        strengthBreakdown={"semanticCompatibility": 0.8},
        confidenceBreakdown={"evidenceQuality": 0.9},
        reasons=["Shared metric context"],
        metadata={"period": "2025-Q2"},
    )

    assert relationship.model_dump(by_alias=True) == {
        "id": "REL-001",
        "analysisId": "ANALYSIS-001",
        "sourceInsightId": "INSIGHT-001",
        "targetInsightId": "INSIGHT-002",
        "type": "CONTRIBUTES_TO",
        "strength": 0.8,
        "confidence": 0.9,
        "strengthBreakdown": {"semanticCompatibility": 0.8},
        "confidenceBreakdown": {"evidenceQuality": 0.9},
        "reasons": ["Shared metric context"],
        "metadata": {"period": "2025-Q2"},
    }


def test_relationship_accepts_python_field_names():
    relationship = Relationship(
        id="REL-001",
        analysis_id="ANALYSIS-001",
        source_insight_id="INSIGHT-001",
        target_insight_id="INSIGHT-002",
        type=RelationshipType.DRILLDOWN_OF,
        strength=0.7,
        confidence=0.8,
    )

    assert relationship.analysis_id == "ANALYSIS-001"
    assert relationship.source_insight_id == "INSIGHT-001"
    assert relationship.target_insight_id == "INSIGHT-002"


def test_mutable_defaults_are_not_shared():
    first = _relationship()
    second = _relationship(id="REL-002")

    first.strength_breakdown["overlap"] = 0.5
    first.confidence_breakdown["quality"] = 0.6
    first.reasons.append("Same period")
    first.metadata["scope"] = "region"

    assert second.strength_breakdown == {}
    assert second.confidence_breakdown == {}
    assert second.reasons == []
    assert second.metadata == {}


def test_relationship_type_has_no_causal_values():
    causal_values = {"CAUSES", "CAUSED_BY", "LED_TO", "RESULTS_IN", "DRIVEN_BY"}

    assert causal_values.isdisjoint(relationship_type.value for relationship_type in RelationshipType)


@pytest.mark.parametrize(
    ("strength", "confidence"),
    [
        (0.0, 0.0),
        (1.0, 1.0),
    ],
)
def test_relationship_accepts_score_boundaries(strength, confidence):
    relationship = _relationship(
        strength=strength,
        confidence=confidence,
    )

    assert relationship.strength == strength
    assert relationship.confidence == confidence


@pytest.mark.parametrize(
    "strength",
    [-0.01, 1.01, float("nan"), float("inf"), float("-inf")],
)
def test_relationship_rejects_invalid_strength(strength):
    with pytest.raises(ValidationError):
        _relationship(strength=strength)


@pytest.mark.parametrize(
    "confidence",
    [-0.01, 1.01, float("nan"), float("inf"), float("-inf")],
)
def test_relationship_rejects_invalid_confidence(confidence):
    with pytest.raises(ValidationError):
        _relationship(confidence=confidence)


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("id", ""),
        ("id", "   "),
        ("analysisId", ""),
        ("analysisId", "\t"),
        ("sourceInsightId", ""),
        ("sourceInsightId", "\n"),
        ("targetInsightId", ""),
        ("targetInsightId", "  \t"),
    ],
)
def test_relationship_rejects_empty_or_whitespace_alias_ids(
    field_name,
    invalid_value,
):
    with pytest.raises(ValidationError):
        _relationship(**{field_name: invalid_value})


@pytest.mark.parametrize(
    "field_name",
    ["analysis_id", "source_insight_id", "target_insight_id"],
)
def test_relationship_rejects_whitespace_python_field_ids(field_name):
    values = {
        "id": "REL-001",
        "analysis_id": "ANALYSIS-001",
        "source_insight_id": "INSIGHT-001",
        "target_insight_id": "INSIGHT-002",
        "type": RelationshipType.CONTRIBUTES_TO,
        "strength": 0.8,
        "confidence": 0.9,
    }
    values[field_name] = "   "

    with pytest.raises(ValidationError):
        Relationship(**values)


def test_relationship_rejects_self_edge():
    with pytest.raises(ValidationError):
        _relationship(targetInsightId="INSIGHT-001")
