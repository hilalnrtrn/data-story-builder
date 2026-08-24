from enum import Enum

from app.models.insight import Insight
from app.models.insight_cluster import InsightCluster
from app.models.relationship import Relationship, RelationshipType


SUPPORTED_CLUSTER_MEMBERSHIP_TYPES = frozenset(
    {
        RelationshipType.CONTRIBUTES_TO.value,
        RelationshipType.COUNTER_SIGNAL.value,
        RelationshipType.CO_MOVES_WITH.value,
        RelationshipType.RELATED_ANOMALY.value,
    }
)


def build_insight_clusters(
    insights: list[Insight],
    relationships: list[Relationship],
) -> list[InsightCluster]:
    relationship_clusters = build_relationship_clusters(
        insights,
        relationships,
    )

    covered_insight_ids = {
        insight_id
        for cluster in relationship_clusters
        for insight_id in (
            cluster.anchor_insight_id,
            *cluster.member_insight_ids,
        )
    }

    singleton_clusters = [
        InsightCluster(
            id=f"CLUSTER-{insight.id}",
            analysisId=insight.analysis_id,
            anchorInsightId=insight.id,
            memberInsightIds=[],
            relationshipIds=[],
        )
        for insight in insights
        if insight.id not in covered_insight_ids
    ]

    return sorted(
        [*relationship_clusters, *singleton_clusters],
        key=lambda cluster: cluster.id,
    )


def build_relationship_clusters(
    insights: list[Insight],
    relationships: list[Relationship],
) -> list[InsightCluster]:
    insight_lookup = build_insight_lookup(insights)
    relationship_lookup = build_relationship_lookup(relationships)

    for relationship in relationship_lookup.values():
        validate_cluster_relationship_reference(
            relationship,
            insight_lookup,
        )

    grouped_members: dict[str, set[str]] = {}
    grouped_relationships: dict[str, list[str]] = {}

    for relationship in relationship_lookup.values():
        member_anchor_ids = cluster_member_anchor_ids(relationship)
        if member_anchor_ids is None:
            continue

        member_id, anchor_id = member_anchor_ids
        grouped_members.setdefault(anchor_id, set()).add(member_id)
        grouped_relationships.setdefault(anchor_id, []).append(
            relationship.id
        )

    clusters = [
        InsightCluster(
            id=f"CLUSTER-{anchor_id}",
            analysisId=insight_lookup[anchor_id].analysis_id,
            anchorInsightId=anchor_id,
            memberInsightIds=sorted(grouped_members[anchor_id]),
            relationshipIds=sorted(grouped_relationships[anchor_id]),
        )
        for anchor_id in grouped_members
    ]

    return sorted(clusters, key=lambda cluster: cluster.id)


def relationship_supports_cluster_membership(
    relationship: Relationship,
) -> bool:
    return (
        _enum_value(relationship.type)
        in SUPPORTED_CLUSTER_MEMBERSHIP_TYPES
    )


def build_insight_lookup(
    insights: list[Insight],
) -> dict[str, Insight]:
    lookup: dict[str, Insight] = {}

    for insight in insights:
        if insight.id in lookup:
            raise ValueError(f"Duplicate Insight ID: {insight.id}")

        lookup[insight.id] = insight

    return lookup


def build_relationship_lookup(
    relationships: list[Relationship],
) -> dict[str, Relationship]:
    lookup: dict[str, Relationship] = {}

    for relationship in relationships:
        if relationship.id in lookup:
            raise ValueError(
                f"Duplicate Relationship ID: {relationship.id}"
            )

        lookup[relationship.id] = relationship

    return lookup


def validate_cluster_relationship_reference(
    relationship: Relationship,
    insight_lookup: dict[str, Insight],
) -> None:
    source = insight_lookup.get(relationship.source_insight_id)
    if source is None:
        raise ValueError(
            "Relationship source Insight does not exist: "
            f"{relationship.source_insight_id}"
        )

    target = insight_lookup.get(relationship.target_insight_id)
    if target is None:
        raise ValueError(
            "Relationship target Insight does not exist: "
            f"{relationship.target_insight_id}"
        )

    if source.analysis_id != relationship.analysis_id:
        raise ValueError(
            "Relationship source Insight analysis does not match "
            "relationship analysis"
        )

    if target.analysis_id != relationship.analysis_id:
        raise ValueError(
            "Relationship target Insight analysis does not match "
            "relationship analysis"
        )


def cluster_member_anchor_ids(
    relationship: Relationship,
) -> tuple[str, str] | None:
    if not relationship_supports_cluster_membership(relationship):
        return None

    return (
        relationship.source_insight_id,
        relationship.target_insight_id,
    )


def _enum_value(value: str | Enum) -> str:
    if isinstance(value, Enum):
        return str(value.value)

    return value
