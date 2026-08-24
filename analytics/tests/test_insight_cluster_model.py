import pytest
from pydantic import ValidationError

from app.models.insight_cluster import InsightCluster


def _cluster(**overrides) -> InsightCluster:
    values = {
        "id": "CLUSTER-CHANGE-Revenue-2025-05-2025-06",
        "analysisId": "ANALYSIS-001",
        "anchorInsightId": "CHANGE-Revenue-2025-05-2025-06",
        "memberInsightIds": ["CHANGE-Orders-2025-05-2025-06"],
        "relationshipIds": ["COUNTER_SIGNAL-ORDERS-REVENUE"],
    }
    values.update(overrides)
    return InsightCluster(**values)


def test_insight_cluster_accepts_camel_case_aliases():
    cluster = _cluster()

    assert cluster.analysis_id == "ANALYSIS-001"
    assert cluster.anchor_insight_id == "CHANGE-Revenue-2025-05-2025-06"
    assert cluster.member_insight_ids == [
        "CHANGE-Orders-2025-05-2025-06"
    ]
    assert cluster.relationship_ids == [
        "COUNTER_SIGNAL-ORDERS-REVENUE"
    ]


def test_insight_cluster_serializes_with_camel_case_aliases():
    cluster = _cluster()

    assert cluster.model_dump(by_alias=True) == {
        "id": "CLUSTER-CHANGE-Revenue-2025-05-2025-06",
        "analysisId": "ANALYSIS-001",
        "anchorInsightId": "CHANGE-Revenue-2025-05-2025-06",
        "memberInsightIds": ["CHANGE-Orders-2025-05-2025-06"],
        "relationshipIds": ["COUNTER_SIGNAL-ORDERS-REVENUE"],
    }


def test_insight_cluster_accepts_python_field_names():
    cluster = InsightCluster(
        id="CLUSTER-INSIGHT-001",
        analysis_id="ANALYSIS-001",
        anchor_insight_id="INSIGHT-001",
        member_insight_ids=["INSIGHT-002"],
        relationship_ids=["RELATIONSHIP-001"],
    )

    assert cluster.analysis_id == "ANALYSIS-001"
    assert cluster.anchor_insight_id == "INSIGHT-001"
    assert cluster.member_insight_ids == ["INSIGHT-002"]
    assert cluster.relationship_ids == ["RELATIONSHIP-001"]


def test_insight_cluster_mutable_defaults_are_not_shared():
    first = InsightCluster(
        id="CLUSTER-INSIGHT-001",
        analysisId="ANALYSIS-001",
        anchorInsightId="INSIGHT-001",
    )
    second = InsightCluster(
        id="CLUSTER-CHANGE-Orders-2025-05-2025-06",
        analysisId="ANALYSIS-001",
        anchorInsightId="CHANGE-Orders-2025-05-2025-06",
    )

    first.member_insight_ids.append("INSIGHT-002")
    first.relationship_ids.append("RELATIONSHIP-001")

    assert second.member_insight_ids == []
    assert second.relationship_ids == []


@pytest.mark.parametrize("invalid_id", ["", "   ", "\t", "\n"])
def test_insight_cluster_rejects_empty_or_whitespace_id(invalid_id):
    with pytest.raises(ValidationError):
        _cluster(id=invalid_id)


@pytest.mark.parametrize("invalid_id", ["", "   "])
def test_insight_cluster_rejects_empty_or_whitespace_analysis_id(invalid_id):
    with pytest.raises(ValidationError):
        _cluster(analysisId=invalid_id)


@pytest.mark.parametrize("invalid_id", ["", "   "])
def test_insight_cluster_rejects_empty_or_whitespace_anchor_id(invalid_id):
    with pytest.raises(ValidationError):
        _cluster(anchorInsightId=invalid_id)


@pytest.mark.parametrize("invalid_id", ["", "   "])
def test_insight_cluster_rejects_invalid_member_id(invalid_id):
    with pytest.raises(ValidationError):
        _cluster(memberInsightIds=[invalid_id])


@pytest.mark.parametrize("invalid_id", ["", "   "])
def test_insight_cluster_rejects_invalid_relationship_id(invalid_id):
    with pytest.raises(ValidationError):
        _cluster(relationshipIds=[invalid_id])


def test_insight_cluster_rejects_anchor_as_member():
    with pytest.raises(ValidationError):
        _cluster(
            memberInsightIds=["CHANGE-Revenue-2025-05-2025-06"]
        )


def test_insight_cluster_rejects_duplicate_member_ids():
    with pytest.raises(ValidationError):
        _cluster(memberInsightIds=["INSIGHT-002", "INSIGHT-002"])


def test_insight_cluster_rejects_duplicate_relationship_ids():
    with pytest.raises(ValidationError):
        _cluster(
            relationshipIds=["RELATIONSHIP-001", "RELATIONSHIP-001"]
        )


def test_insight_cluster_accepts_empty_member_ids():
    cluster = _cluster(memberInsightIds=[])

    assert cluster.member_insight_ids == []


def test_insight_cluster_accepts_empty_relationship_ids():
    cluster = _cluster(relationshipIds=[])

    assert cluster.relationship_ids == []
