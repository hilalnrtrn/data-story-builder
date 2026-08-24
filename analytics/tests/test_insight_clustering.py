from copy import deepcopy

import pytest

from app.models.insight import (
    Insight,
    InsightDirection,
    InsightType,
    PeriodGranularity,
)
from app.models.relationship import Relationship, RelationshipType
from app.services.insight_clustering import (
    build_insight_lookup,
    build_insight_clusters,
    build_relationship_clusters,
    build_relationship_lookup,
    cluster_member_anchor_ids,
    relationship_supports_cluster_membership,
    validate_cluster_relationship_reference,
)


def _insight(**overrides) -> Insight:
    values = {
        "id": "INSIGHT-001",
        "analysisId": "ANALYSIS-001",
        "type": InsightType.CHANGE,
        "metric": "Revenue",
        "periodGranularity": PeriodGranularity.MONTH,
        "period": {"previous": "2025-05", "current": "2025-06"},
        "direction": InsightDirection.UP,
    }
    values.update(overrides)
    return Insight(**values)


def _relationship(**overrides) -> Relationship:
    values = {
        "id": "RELATIONSHIP-001",
        "analysisId": "ANALYSIS-001",
        "sourceInsightId": "INSIGHT-001",
        "targetInsightId": "INSIGHT-002",
        "type": RelationshipType.CONTRIBUTES_TO,
        "strength": 1.0,
        "confidence": 0.9,
    }
    values.update(overrides)
    return Relationship(**values)


@pytest.mark.parametrize(
    "relationship_type",
    [
        RelationshipType.CONTRIBUTES_TO,
        RelationshipType.COUNTER_SIGNAL,
        RelationshipType.CO_MOVES_WITH,
        RelationshipType.RELATED_ANOMALY,
    ],
)
def test_supported_relationship_types_allow_cluster_membership(
    relationship_type,
):
    assert relationship_supports_cluster_membership(
        _relationship(type=relationship_type)
    ) is True


def test_drilldown_does_not_support_cluster_membership():
    assert relationship_supports_cluster_membership(
        _relationship(type=RelationshipType.DRILLDOWN_OF)
    ) is False


@pytest.mark.parametrize(
    ("runtime_type", "expected"),
    [
        (RelationshipType.RELATED_ANOMALY, True),
        ("RELATED_ANOMALY", True),
        (RelationshipType.DRILLDOWN_OF, False),
        ("DRILLDOWN_OF", False),
    ],
)
def test_membership_supports_enum_and_string_runtime_types(
    runtime_type,
    expected,
):
    relationship = _relationship().model_copy(update={"type": runtime_type})

    assert relationship_supports_cluster_membership(relationship) is expected


def test_builds_insight_lookup_by_id():
    first = _insight()
    second = _insight(id="INSIGHT-002", metric="Orders")

    lookup = build_insight_lookup([first, second])

    assert lookup == {first.id: first, second.id: second}
    assert lookup[first.id] is first
    assert lookup[second.id] is second


def test_empty_insight_list_builds_empty_lookup():
    assert build_insight_lookup([]) == {}


def test_duplicate_insight_id_raises_value_error():
    with pytest.raises(ValueError, match="Duplicate Insight ID"):
        build_insight_lookup([_insight(), _insight()])


def test_build_insight_lookup_does_not_mutate_input():
    insights = [_insight(), _insight(id="INSIGHT-002")]
    before = deepcopy([insight.model_dump() for insight in insights])

    build_insight_lookup(insights)

    assert [insight.model_dump() for insight in insights] == before


def test_builds_relationship_lookup_by_id():
    first = _relationship()
    second = _relationship(id="RELATIONSHIP-002")

    lookup = build_relationship_lookup([first, second])

    assert lookup == {first.id: first, second.id: second}
    assert lookup[first.id] is first
    assert lookup[second.id] is second


def test_empty_relationship_list_builds_empty_lookup():
    assert build_relationship_lookup([]) == {}


def test_duplicate_relationship_id_raises_value_error():
    with pytest.raises(ValueError, match="Duplicate Relationship ID"):
        build_relationship_lookup([_relationship(), _relationship()])


def test_build_relationship_lookup_does_not_mutate_input():
    relationships = [_relationship(), _relationship(id="RELATIONSHIP-002")]
    before = deepcopy(
        [relationship.model_dump() for relationship in relationships]
    )

    build_relationship_lookup(relationships)

    assert [
        relationship.model_dump() for relationship in relationships
    ] == before


def test_validates_existing_same_analysis_relationship_references():
    source = _insight()
    target = _insight(id="INSIGHT-002")

    assert validate_cluster_relationship_reference(
        _relationship(),
        build_insight_lookup([source, target]),
    ) is None


def test_missing_source_reference_raises_value_error():
    with pytest.raises(ValueError, match="source Insight does not exist"):
        validate_cluster_relationship_reference(
            _relationship(),
            build_insight_lookup([_insight(id="INSIGHT-002")]),
        )


def test_missing_target_reference_raises_value_error():
    with pytest.raises(ValueError, match="target Insight does not exist"):
        validate_cluster_relationship_reference(
            _relationship(),
            build_insight_lookup([_insight()]),
        )


def test_source_analysis_mismatch_raises_value_error():
    source = _insight(analysisId="ANALYSIS-002")
    target = _insight(id="INSIGHT-002")

    with pytest.raises(ValueError, match="source Insight analysis"):
        validate_cluster_relationship_reference(
            _relationship(),
            build_insight_lookup([source, target]),
        )


def test_target_analysis_mismatch_raises_value_error():
    source = _insight()
    target = _insight(id="INSIGHT-002", analysisId="ANALYSIS-002")

    with pytest.raises(ValueError, match="target Insight analysis"):
        validate_cluster_relationship_reference(
            _relationship(),
            build_insight_lookup([source, target]),
        )


@pytest.mark.parametrize(
    "relationship_type",
    [
        RelationshipType.CONTRIBUTES_TO,
        RelationshipType.COUNTER_SIGNAL,
        RelationshipType.CO_MOVES_WITH,
        RelationshipType.RELATED_ANOMALY,
    ],
)
def test_supported_relationship_resolves_source_member_and_target_anchor(
    relationship_type,
):
    assert cluster_member_anchor_ids(
        _relationship(type=relationship_type)
    ) == ("INSIGHT-001", "INSIGHT-002")


def test_drilldown_relationship_does_not_resolve_membership():
    assert cluster_member_anchor_ids(
        _relationship(type=RelationshipType.DRILLDOWN_OF)
    ) is None


def test_clustering_helpers_do_not_infer_semantic_membership():
    source = _insight(
        metric="Revenue",
        period={"current": "2025-06"},
        direction=InsightDirection.HIGH,
    )
    target = _insight(id="INSIGHT-002")
    relationship = _relationship(type=RelationshipType.DRILLDOWN_OF)

    validate_cluster_relationship_reference(
        relationship,
        build_insight_lookup([source, target]),
    )

    assert relationship_supports_cluster_membership(relationship) is False
    assert cluster_member_anchor_ids(relationship) is None


def _cluster_dumps(insights, relationships):
    return [
        cluster.model_dump(by_alias=True)
        for cluster in build_relationship_clusters(insights, relationships)
    ]


def test_empty_inputs_build_no_relationship_clusters():
    assert build_relationship_clusters([], []) == []


def test_one_relationship_builds_one_direct_cluster():
    clusters = build_relationship_clusters(
        [_insight(), _insight(id="INSIGHT-002")],
        [_relationship()],
    )

    assert len(clusters) == 1
    assert clusters[0].model_dump(by_alias=True) == {
        "id": "CLUSTER-INSIGHT-002",
        "analysisId": "ANALYSIS-001",
        "anchorInsightId": "INSIGHT-002",
        "memberInsightIds": ["INSIGHT-001"],
        "relationshipIds": ["RELATIONSHIP-001"],
    }


def test_multiple_members_share_one_anchor_cluster():
    insights = [
        _insight(id="REVENUE"),
        _insight(id="ORDERS", metric="Orders"),
        _insight(id="CUSTOMERS", metric="Customers"),
        _insight(id="MARKETING", metric="MarketingSpend"),
    ]
    relationships = [
        _relationship(
            id="REL-ORDERS",
            sourceInsightId="ORDERS",
            targetInsightId="REVENUE",
            type=RelationshipType.COUNTER_SIGNAL,
        ),
        _relationship(
            id="REL-CUSTOMERS",
            sourceInsightId="CUSTOMERS",
            targetInsightId="REVENUE",
            type=RelationshipType.COUNTER_SIGNAL,
        ),
        _relationship(
            id="REL-MARKETING",
            sourceInsightId="MARKETING",
            targetInsightId="REVENUE",
            type=RelationshipType.CO_MOVES_WITH,
        ),
    ]

    clusters = build_relationship_clusters(insights, relationships)

    assert len(clusters) == 1
    assert clusters[0].anchor_insight_id == "REVENUE"
    assert clusters[0].member_insight_ids == [
        "CUSTOMERS",
        "MARKETING",
        "ORDERS",
    ]
    assert clusters[0].relationship_ids == [
        "REL-CUSTOMERS",
        "REL-MARKETING",
        "REL-ORDERS",
    ]


def test_different_anchors_build_separate_sorted_clusters():
    insights = [
        _insight(id="MEMBER-A"),
        _insight(id="ANCHOR-Z"),
        _insight(id="MEMBER-B"),
        _insight(id="ANCHOR-A"),
    ]
    relationships = [
        _relationship(
            id="REL-Z",
            sourceInsightId="MEMBER-A",
            targetInsightId="ANCHOR-Z",
        ),
        _relationship(
            id="REL-A",
            sourceInsightId="MEMBER-B",
            targetInsightId="ANCHOR-A",
        ),
    ]

    clusters = build_relationship_clusters(insights, relationships)

    assert [cluster.id for cluster in clusters] == [
        "CLUSTER-ANCHOR-A",
        "CLUSTER-ANCHOR-Z",
    ]


def test_drilldown_relationship_builds_no_cluster():
    assert build_relationship_clusters(
        [_insight(), _insight(id="INSIGHT-002")],
        [_relationship(type=RelationshipType.DRILLDOWN_OF)],
    ) == []


def test_unsupported_relationship_references_are_still_validated():
    with pytest.raises(ValueError, match="target Insight does not exist"):
        build_relationship_clusters(
            [_insight()],
            [_relationship(type=RelationshipType.DRILLDOWN_OF)],
        )


def test_cluster_builder_rejects_duplicate_insight_ids():
    with pytest.raises(ValueError, match="Duplicate Insight ID"):
        build_relationship_clusters([_insight(), _insight()], [])


def test_cluster_builder_rejects_duplicate_relationship_ids():
    insights = [_insight(), _insight(id="INSIGHT-002")]

    with pytest.raises(ValueError, match="Duplicate Relationship ID"):
        build_relationship_clusters(
            insights,
            [_relationship(), _relationship()],
        )


@pytest.mark.parametrize(
    ("insights", "message"),
    [
        ([_insight(id="INSIGHT-002")], "source Insight does not exist"),
        ([_insight()], "target Insight does not exist"),
    ],
)
def test_cluster_builder_rejects_missing_references(insights, message):
    with pytest.raises(ValueError, match=message):
        build_relationship_clusters(insights, [_relationship()])


def test_cluster_builder_rejects_analysis_mismatch():
    insights = [
        _insight(),
        _insight(id="INSIGHT-002", analysisId="ANALYSIS-002"),
    ]

    with pytest.raises(ValueError, match="target Insight analysis"):
        build_relationship_clusters(insights, [_relationship()])


def test_multiple_relationships_retain_all_evidence_and_one_member():
    insights = [_insight(), _insight(id="INSIGHT-002")]
    relationships = [
        _relationship(id="RELATIONSHIP-002"),
        _relationship(
            id="RELATIONSHIP-001",
            type=RelationshipType.RELATED_ANOMALY,
        ),
    ]

    clusters = build_relationship_clusters(insights, relationships)

    assert clusters[0].member_insight_ids == ["INSIGHT-001"]
    assert clusters[0].relationship_ids == [
        "RELATIONSHIP-001",
        "RELATIONSHIP-002",
    ]


def test_cluster_output_is_deterministic_for_reordered_inputs():
    insights = [
        _insight(id="ANCHOR"),
        _insight(id="MEMBER-Z"),
        _insight(id="MEMBER-A"),
    ]
    relationships = [
        _relationship(
            id="REL-Z",
            sourceInsightId="MEMBER-Z",
            targetInsightId="ANCHOR",
        ),
        _relationship(
            id="REL-A",
            sourceInsightId="MEMBER-A",
            targetInsightId="ANCHOR",
        ),
    ]

    forward = _cluster_dumps(insights, relationships)
    reversed_inputs = _cluster_dumps(
        list(reversed(insights)),
        list(reversed(relationships)),
    )

    assert forward == reversed_inputs
    assert forward[0]["memberInsightIds"] == ["MEMBER-A", "MEMBER-Z"]
    assert forward[0]["relationshipIds"] == ["REL-A", "REL-Z"]


def test_cluster_builder_does_not_mutate_inputs():
    insights = [_insight(), _insight(id="INSIGHT-002")]
    relationships = [_relationship()]
    insights_before = deepcopy(
        [insight.model_dump() for insight in insights]
    )
    relationships_before = deepcopy(
        [relationship.model_dump() for relationship in relationships]
    )

    build_relationship_clusters(insights, relationships)

    assert [insight.model_dump() for insight in insights] == insights_before
    assert [
        relationship.model_dump() for relationship in relationships
    ] == relationships_before


def test_cluster_builder_uses_direct_edges_without_transitive_membership():
    insights = [
        _insight(id="A"),
        _insight(id="B"),
        _insight(id="C"),
    ]
    relationships = [
        _relationship(
            id="REL-A-B",
            sourceInsightId="A",
            targetInsightId="B",
        ),
        _relationship(
            id="REL-B-C",
            sourceInsightId="B",
            targetInsightId="C",
        ),
    ]

    clusters = build_relationship_clusters(insights, relationships)

    assert [
        (cluster.anchor_insight_id, cluster.member_insight_ids)
        for cluster in clusters
    ] == [("B", ["A"]), ("C", ["B"])]


def test_matching_insights_without_relationships_build_no_clusters():
    insights = [
        _insight(id="INSIGHT-001"),
        _insight(id="INSIGHT-002"),
        _insight(id="INSIGHT-003"),
    ]

    assert build_relationship_clusters(insights, []) == []


def _complete_cluster_dumps(insights, relationships):
    return [
        cluster.model_dump(by_alias=True)
        for cluster in build_insight_clusters(insights, relationships)
    ]


def test_empty_inputs_build_no_complete_clusters():
    assert build_insight_clusters([], []) == []


def test_one_unrelated_insight_builds_one_singleton():
    clusters = build_insight_clusters([_insight()], [])

    assert [cluster.model_dump(by_alias=True) for cluster in clusters] == [
        {
            "id": "CLUSTER-INSIGHT-001",
            "analysisId": "ANALYSIS-001",
            "anchorInsightId": "INSIGHT-001",
            "memberInsightIds": [],
            "relationshipIds": [],
        }
    ]


def test_multiple_unrelated_insights_build_one_singleton_each():
    clusters = build_insight_clusters(
        [_insight(id="INSIGHT-C"), _insight(id="INSIGHT-A")],
        [],
    )

    assert [cluster.anchor_insight_id for cluster in clusters] == [
        "INSIGHT-A",
        "INSIGHT-C",
    ]
    assert all(cluster.member_insight_ids == [] for cluster in clusters)
    assert all(cluster.relationship_ids == [] for cluster in clusters)


def test_covered_anchor_and_member_do_not_build_singletons():
    clusters = build_insight_clusters(
        [_insight(), _insight(id="INSIGHT-002")],
        [_relationship()],
    )

    assert len(clusters) == 1
    assert clusters[0].anchor_insight_id == "INSIGHT-002"
    assert clusters[0].member_insight_ids == ["INSIGHT-001"]


def test_relationship_cluster_and_unrelated_singleton_are_preserved():
    clusters = build_insight_clusters(
        [
            _insight(id="MEMBER"),
            _insight(id="ANCHOR"),
            _insight(id="UNRELATED"),
        ],
        [
            _relationship(
                sourceInsightId="MEMBER",
                targetInsightId="ANCHOR",
            )
        ],
    )

    assert [
        (cluster.anchor_insight_id, cluster.member_insight_ids)
        for cluster in clusters
    ] == [("ANCHOR", ["MEMBER"]), ("UNRELATED", [])]


def test_multiple_relationship_clusters_and_singletons_are_preserved():
    insights = [
        _insight(id="MEMBER-Z"),
        _insight(id="ANCHOR-Z"),
        _insight(id="MEMBER-A"),
        _insight(id="ANCHOR-A"),
        _insight(id="UNRELATED-B"),
        _insight(id="UNRELATED-A"),
    ]
    relationships = [
        _relationship(
            id="REL-Z",
            sourceInsightId="MEMBER-Z",
            targetInsightId="ANCHOR-Z",
        ),
        _relationship(
            id="REL-A",
            sourceInsightId="MEMBER-A",
            targetInsightId="ANCHOR-A",
        ),
    ]

    clusters = build_insight_clusters(insights, relationships)

    assert [cluster.id for cluster in clusters] == [
        "CLUSTER-ANCHOR-A",
        "CLUSTER-ANCHOR-Z",
        "CLUSTER-UNRELATED-A",
        "CLUSTER-UNRELATED-B",
    ]


def test_drilldown_endpoints_become_singletons():
    clusters = build_insight_clusters(
        [_insight(), _insight(id="INSIGHT-002")],
        [_relationship(type=RelationshipType.DRILLDOWN_OF)],
    )

    assert [cluster.anchor_insight_id for cluster in clusters] == [
        "INSIGHT-001",
        "INSIGHT-002",
    ]
    assert all(cluster.member_insight_ids == [] for cluster in clusters)


@pytest.mark.parametrize(
    "insight_type",
    [InsightType.TREND, InsightType.CONTRAST],
)
def test_unconnected_insight_types_become_singletons(insight_type):
    insight = _insight(type=insight_type)

    clusters = build_insight_clusters([insight], [])

    assert len(clusters) == 1
    assert clusters[0].anchor_insight_id == insight.id
    assert clusters[0].member_insight_ids == []
    assert clusters[0].relationship_ids == []


def test_every_insight_is_represented_once_in_non_overlapping_scenario():
    insights = [
        _insight(id="MEMBER-A"),
        _insight(id="MEMBER-B"),
        _insight(id="ANCHOR"),
        _insight(id="SINGLETON"),
    ]
    relationships = [
        _relationship(
            id="REL-A",
            sourceInsightId="MEMBER-A",
            targetInsightId="ANCHOR",
        ),
        _relationship(
            id="REL-B",
            sourceInsightId="MEMBER-B",
            targetInsightId="ANCHOR",
        ),
    ]

    clusters = build_insight_clusters(insights, relationships)
    represented_ids = [
        insight_id
        for cluster in clusters
        for insight_id in (
            cluster.anchor_insight_id,
            *cluster.member_insight_ids,
        )
    ]

    assert sorted(represented_ids) == sorted(insight.id for insight in insights)
    assert len(represented_ids) == len(set(represented_ids))


def test_complete_cluster_output_is_deterministic_for_reordered_inputs():
    insights = [
        _insight(id="MEMBER-Z"),
        _insight(id="MEMBER-A"),
        _insight(id="ANCHOR"),
        _insight(id="SINGLETON"),
    ]
    relationships = [
        _relationship(
            id="REL-Z",
            sourceInsightId="MEMBER-Z",
            targetInsightId="ANCHOR",
        ),
        _relationship(
            id="REL-A",
            sourceInsightId="MEMBER-A",
            targetInsightId="ANCHOR",
        ),
    ]

    assert _complete_cluster_dumps(
        insights,
        relationships,
    ) == _complete_cluster_dumps(
        list(reversed(insights)),
        list(reversed(relationships)),
    )


def test_complete_cluster_builder_does_not_mutate_inputs():
    insights = [
        _insight(),
        _insight(id="INSIGHT-002"),
        _insight(id="INSIGHT-003"),
    ]
    relationships = [_relationship()]
    insights_before = deepcopy(
        [insight.model_dump() for insight in insights]
    )
    relationships_before = deepcopy(
        [relationship.model_dump() for relationship in relationships]
    )

    build_insight_clusters(insights, relationships)

    assert [insight.model_dump() for insight in insights] == insights_before
    assert [
        relationship.model_dump() for relationship in relationships
    ] == relationships_before


def test_complete_cluster_builder_preserves_invalid_reference_behavior():
    with pytest.raises(ValueError, match="target Insight does not exist"):
        build_insight_clusters([_insight()], [_relationship()])


def test_complete_cluster_builder_rejects_duplicate_insight_ids():
    with pytest.raises(ValueError, match="Duplicate Insight ID"):
        build_insight_clusters([_insight(), _insight()], [])


def test_complete_cluster_builder_rejects_duplicate_relationship_ids():
    insights = [_insight(), _insight(id="INSIGHT-002")]

    with pytest.raises(ValueError, match="Duplicate Relationship ID"):
        build_insight_clusters(
            insights,
            [_relationship(), _relationship()],
        )
