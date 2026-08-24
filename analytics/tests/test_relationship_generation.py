from collections import Counter
from copy import deepcopy

import pytest

from app.models.insight import (
    Insight,
    InsightDirection,
    InsightType,
    PeriodGranularity,
)
from app.models.relationship import Relationship, RelationshipType
from app.services import relationship_engine
from app.services.relationship_engine import generate_relationships


def _insight(
    insight_id: str,
    insight_type: InsightType,
    metric: str,
    *,
    analysis_id: str = "analysis-1",
    direction: InsightDirection = InsightDirection.UP,
    dimension: str | None = None,
    segment: str | None = None,
    period: dict[str, str] | None = None,
    values: dict[str, float] | None = None,
) -> Insight:
    return Insight(
        id=insight_id,
        analysisId=analysis_id,
        type=insight_type,
        metric=metric,
        dimension=dimension,
        segment=segment,
        periodGranularity=PeriodGranularity.MONTH,
        period=period or {"previous": "2025-05", "current": "2025-06"},
        values=values or {},
        direction=direction,
        confidence=0.9,
        importance=0.8,
        reasons=[],
        metadata={},
    )


def _change(
    insight_id: str,
    metric: str,
    *,
    direction: InsightDirection = InsightDirection.UP,
    analysis_id: str = "analysis-1",
    dimension: str | None = None,
    segment: str | None = None,
    period: dict[str, str] | None = None,
) -> Insight:
    return _insight(
        insight_id,
        InsightType.CHANGE,
        metric,
        direction=direction,
        analysis_id=analysis_id,
        dimension=dimension,
        segment=segment,
        period=period,
        values={
            "previous": 100.0,
            "current": 120.0,
            "absoluteChange": 20.0,
        },
    )


def _config() -> dict:
    return {
        "relationship": {
            "metricCompatibility": {
                "COUNTER_SIGNAL": [
                    {"sourceMetric": "Orders", "targetMetric": "Revenue"},
                    {
                        "sourceMetric": "Customers",
                        "targetMetric": "Revenue",
                    },
                ],
                "CO_MOVES_WITH": [
                    {
                        "sourceMetric": "MarketingSpend",
                        "targetMetric": "Revenue",
                    }
                ],
            }
        }
    }


def _contribution(
    *,
    metric: str = "Revenue",
    dimension: str | None = "Region",
    segment: str | None = "Marmara",
    period: dict[str, str] | None = None,
    values: dict[str, float] | None = None,
) -> Insight:
    return _insight(
        "contribution",
        InsightType.CONTRIBUTION,
        metric,
        dimension=dimension,
        segment=segment,
        period=period,
        values=values
        or {
            "totalPreviousValue": 100.0,
            "totalCurrentValue": 120.0,
            "totalAbsoluteChange": 20.0,
        },
    )


def _anomaly(
    *,
    metric: str = "Revenue",
    direction: InsightDirection = InsightDirection.HIGH,
    dimension: str | None = "Region",
    segment: str | None = "Marmara",
    current: str = "2025-06",
) -> Insight:
    return _insight(
        "anomaly",
        InsightType.ANOMALY,
        metric,
        direction=direction,
        dimension=dimension,
        segment=segment,
        period={"current": current},
    )


def _multi_edge_fixture() -> tuple[list[Insight], dict]:
    return (
        [
            _change("change-revenue", "Revenue"),
            _change(
                "change-orders",
                "Orders",
                direction=InsightDirection.DOWN,
            ),
            _change(
                "change-customers",
                "Customers",
                direction=InsightDirection.DOWN,
            ),
            _change("change-marketing", "MarketingSpend"),
            _contribution(),
            _anomaly(),
        ],
        _config(),
    )


def test_empty_and_single_inputs_return_empty_without_loading_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_loader() -> dict:
        raise AssertionError("configuration should not be loaded")

    monkeypatch.setattr(relationship_engine, "load_insight_config", fail_loader)

    assert generate_relationships([]) == []
    assert generate_relationships([_change("change-revenue", "Revenue")]) == []


def test_duplicate_insight_ids_raise() -> None:
    insights = [
        _change("duplicate", "Revenue"),
        _change("duplicate", "Orders", direction=InsightDirection.DOWN),
    ]

    with pytest.raises(ValueError, match="Duplicate Insight ID"):
        generate_relationships(insights, _config())


def test_mixed_analysis_ids_raise() -> None:
    insights = [
        _change("change-a", "Revenue", analysis_id="analysis-1"),
        _change("change-b", "Orders", analysis_id="analysis-2"),
    ]

    with pytest.raises(ValueError, match="same analysis"):
        generate_relationships(insights, _config())


def test_contribution_to_change_generates_contributes_to() -> None:
    revenue = _change("change-revenue", "Revenue")
    contribution = _insight(
        "contribution-revenue-marmara",
        InsightType.CONTRIBUTION,
        "Revenue",
        dimension="Region",
        segment="Marmara",
        values={
            "totalPreviousValue": 100.0,
            "totalCurrentValue": 120.0,
            "totalAbsoluteChange": 20.0,
            "contributionShare": 0.6,
        },
    )

    relationships = generate_relationships([revenue, contribution])

    assert [item.type for item in relationships] == [
        RelationshipType.CONTRIBUTES_TO.value
    ]


def test_anomaly_to_change_generates_related_anomaly() -> None:
    revenue = _change("change-revenue", "Revenue")
    anomaly = _insight(
        "anomaly-revenue-marmara",
        InsightType.ANOMALY,
        "Revenue",
        dimension="Region",
        segment="Marmara",
        period={"current": "2025-06"},
        direction=InsightDirection.HIGH,
    )

    relationships = generate_relationships([revenue, anomaly])

    assert [item.type for item in relationships] == [
        RelationshipType.RELATED_ANOMALY.value
    ]


def test_change_to_change_generates_counter_signal_with_supplied_config() -> None:
    relationships = generate_relationships(
        [
            _change("change-revenue", "Revenue"),
            _change("change-orders", "Orders", direction=InsightDirection.DOWN),
        ],
        _config(),
    )

    assert [item.type for item in relationships] == [
        RelationshipType.COUNTER_SIGNAL.value
    ]


def test_change_to_change_generates_co_moves_with_with_supplied_config() -> None:
    relationships = generate_relationships(
        [
            _change("change-revenue", "Revenue"),
            _change("change-marketing", "MarketingSpend"),
        ],
        _config(),
    )

    assert [item.type for item in relationships] == [
        RelationshipType.CO_MOVES_WITH.value
    ]


@pytest.mark.parametrize("insight_type", [InsightType.TREND, InsightType.CONTRAST])
def test_unsupported_source_types_generate_nothing(
    insight_type: InsightType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_loader() -> dict:
        raise AssertionError("configuration should not be loaded")

    monkeypatch.setattr(relationship_engine, "load_insight_config", fail_loader)
    source = _insight("unsupported", insight_type, "Revenue")
    target = _change("change-revenue", "Revenue")

    assert generate_relationships([source, target]) == []


def test_output_is_deterministic_for_reversed_input_order() -> None:
    insights = [
        _change("change-revenue", "Revenue"),
        _change("change-orders", "Orders", direction=InsightDirection.DOWN),
        _change("change-marketing", "MarketingSpend"),
    ]

    forward = generate_relationships(insights, _config())
    reversed_result = generate_relationships(list(reversed(insights)), _config())

    assert [item.model_dump(by_alias=True) for item in forward] == [
        item.model_dump(by_alias=True) for item in reversed_result
    ]
    assert [item.id for item in forward] == sorted(item.id for item in forward)


def test_generation_does_not_mutate_inputs_or_config() -> None:
    insights = [
        _change("change-revenue", "Revenue"),
        _change("change-marketing", "MarketingSpend"),
    ]
    original_order = list(insights)
    insight_snapshots = [item.model_dump(by_alias=True) for item in insights]
    config = _config()
    config_snapshot = deepcopy(config)

    generate_relationships(insights, config)

    assert insights == original_order
    assert [item.model_dump(by_alias=True) for item in insights] == insight_snapshots
    assert config == config_snapshot


def test_config_is_loaded_once_only_for_change_to_change_evaluation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0

    def load_config() -> dict:
        nonlocal calls
        calls += 1
        return _config()

    monkeypatch.setattr(relationship_engine, "load_insight_config", load_config)
    insights = [
        _change("change-revenue", "Revenue"),
        _change("change-marketing", "MarketingSpend"),
    ]

    relationships = generate_relationships(insights)

    assert calls == 1
    assert [item.type for item in relationships] == [
        RelationshipType.CO_MOVES_WITH.value
    ]


def test_identical_generated_relationship_ids_are_deduplicated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixed = Relationship(
        id="fixed-relationship",
        analysisId="analysis-1",
        sourceInsightId="change-a",
        targetInsightId="change-b",
        type=RelationshipType.COUNTER_SIGNAL,
        strength=1.0,
        confidence=1.0,
    )
    monkeypatch.setattr(
        relationship_engine,
        "build_counter_signal_relationship",
        lambda source, target, config: fixed,
    )
    monkeypatch.setattr(
        relationship_engine,
        "build_co_moves_with_relationship",
        lambda source, target, config: None,
    )

    relationships = generate_relationships(
        [_change("change-a", "A"), _change("change-b", "B")],
        {},
    )

    assert relationships == [fixed]


def test_conflicting_generated_relationship_ids_raise(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def conflicting_builder(
        source: Insight,
        target: Insight,
        config: dict,
    ) -> Relationship:
        return Relationship(
            id="fixed-relationship",
            analysisId=source.analysis_id,
            sourceInsightId=source.id,
            targetInsightId=target.id,
            type=RelationshipType.COUNTER_SIGNAL,
            strength=1.0,
            confidence=1.0,
        )

    monkeypatch.setattr(
        relationship_engine,
        "build_counter_signal_relationship",
        conflicting_builder,
    )
    monkeypatch.setattr(
        relationship_engine,
        "build_co_moves_with_relationship",
        lambda source, target, config: None,
    )

    with pytest.raises(ValueError, match="Conflicting generated Relationship ID"):
        generate_relationships(
            [_change("change-a", "A"), _change("change-b", "B")],
            {},
        )


def test_generation_introduces_no_deferred_or_causal_relationship_types() -> None:
    relationships = generate_relationships(
        [
            _change("change-revenue", "Revenue"),
            _change("change-orders", "Orders", direction=InsightDirection.DOWN),
            _change("change-marketing", "MarketingSpend"),
        ],
        _config(),
    )

    assert {item.type for item in relationships} <= {
        "CONTRIBUTES_TO",
        "COUNTER_SIGNAL",
        "CO_MOVES_WITH",
        "RELATED_ANOMALY",
    }
    assert all(item.type != RelationshipType.DRILLDOWN_OF.value for item in relationships)
    causal_terms = ("CAUSE", "LED_TO", "RESULT", "DRIVEN", "BECAUSE")
    assert all(
        not any(term in item.type for term in causal_terms)
        for item in relationships
    )


@pytest.mark.parametrize(
    ("source", "target"),
    [
        (_contribution(metric="Revenue"), _change("change", "Orders")),
        (
            _contribution(
                period={"previous": "2025-04", "current": "2025-05"}
            ),
            _change("change", "Revenue"),
        ),
        (
            _contribution(
                values={
                    "totalPreviousValue": 100.0,
                    "totalCurrentValue": 121.0,
                    "totalAbsoluteChange": 21.0,
                }
            ),
            _change("change", "Revenue"),
        ),
        (
            _contribution(dimension=None, segment=None),
            _change("change", "Revenue"),
        ),
        (
            _contribution(),
            _change(
                "change",
                "Revenue",
                dimension="Region",
                segment="Marmara",
            ),
        ),
    ],
    ids=[
        "wrong-metric",
        "wrong-period",
        "arithmetic-mismatch",
        "company-level-source",
        "segment-level-target",
    ],
)
def test_invalid_contribution_contract_generates_no_relationship(
    source: Insight,
    target: Insight,
) -> None:
    assert generate_relationships([source, target]) == []


@pytest.mark.parametrize(
    ("source", "target"),
    [
        (_anomaly(metric="Revenue"), _change("change", "Orders")),
        (_anomaly(current="2025-05"), _change("change", "Revenue")),
        (
            _anomaly(direction=InsightDirection.HIGH),
            _change("change", "Revenue", direction=InsightDirection.DOWN),
        ),
        (
            _anomaly(direction=InsightDirection.LOW),
            _change("change", "Revenue", direction=InsightDirection.UP),
        ),
        (
            _anomaly(dimension=None, segment=None),
            _change("change", "Revenue"),
        ),
        (
            _anomaly(),
            _change(
                "change",
                "Revenue",
                dimension="Region",
                segment="Marmara",
            ),
        ),
    ],
    ids=[
        "wrong-metric",
        "wrong-current-period",
        "high-with-down",
        "low-with-up",
        "company-level-anomaly",
        "segment-level-change",
    ],
)
def test_invalid_anomaly_contract_generates_no_relationship(
    source: Insight,
    target: Insight,
) -> None:
    assert generate_relationships([source, target]) == []


@pytest.mark.parametrize(
    ("source", "target"),
    [
        (
            _change("orders", "Orders"),
            _change("revenue", "Revenue"),
        ),
        (
            _change("profit", "Profit", direction=InsightDirection.DOWN),
            _change("revenue", "Revenue"),
        ),
        (
            _change("orders", "Orders", direction=InsightDirection.DOWN),
            _change(
                "revenue",
                "Revenue",
                period={"previous": "2025-04", "current": "2025-05"},
            ),
        ),
        (
            _change(
                "orders",
                "Orders",
                direction=InsightDirection.DOWN,
                dimension="Region",
                segment="Marmara",
            ),
            _change("revenue", "Revenue"),
        ),
    ],
    ids=[
        "same-direction",
        "incompatible-metrics",
        "wrong-period",
        "segment-level",
    ],
)
def test_invalid_counter_signal_contract_generates_no_relationship(
    source: Insight,
    target: Insight,
) -> None:
    assert generate_relationships([source, target], _config()) == []


@pytest.mark.parametrize(
    ("source", "target"),
    [
        (
            _change(
                "marketing",
                "MarketingSpend",
                direction=InsightDirection.DOWN,
            ),
            _change("revenue", "Revenue"),
        ),
        (
            _change("profit", "Profit"),
            _change("revenue", "Revenue"),
        ),
        (
            _change("marketing", "MarketingSpend"),
            _change(
                "revenue",
                "Revenue",
                period={"previous": "2025-04", "current": "2025-05"},
            ),
        ),
        (
            _change(
                "marketing",
                "MarketingSpend",
                dimension="Region",
                segment="Marmara",
            ),
            _change("revenue", "Revenue"),
        ),
    ],
    ids=[
        "opposite-direction",
        "incompatible-metrics",
        "wrong-period",
        "segment-level",
    ],
)
def test_invalid_co_moves_with_contract_generates_no_relationship(
    source: Insight,
    target: Insight,
) -> None:
    assert generate_relationships([source, target], _config()) == []


@pytest.mark.parametrize(
    ("source", "target", "expected_type"),
    [
        (
            _change("orders", "Orders", direction=InsightDirection.DOWN),
            _change("revenue", "Revenue"),
            RelationshipType.COUNTER_SIGNAL.value,
        ),
        (
            _change("marketing", "MarketingSpend"),
            _change("revenue", "Revenue"),
            RelationshipType.CO_MOVES_WITH.value,
        ),
    ],
    ids=["counter-signal", "co-moves-with"],
)
def test_directional_config_generates_only_the_configured_edge(
    source: Insight,
    target: Insight,
    expected_type: str,
) -> None:
    relationships = generate_relationships([target, source], _config())

    assert len(relationships) == 1
    assert relationships[0].type == expected_type
    assert relationships[0].source_insight_id == source.id
    assert relationships[0].target_insight_id == target.id


def test_generation_never_returns_a_self_edge() -> None:
    single = _change("change", "Revenue")

    assert generate_relationships([single], _config()) == []

    relationships = generate_relationships(
        [
            _change("orders", "Orders", direction=InsightDirection.DOWN),
            _change("revenue", "Revenue"),
            _change("marketing", "MarketingSpend"),
        ],
        _config(),
    )
    assert all(
        item.source_insight_id != item.target_insight_id
        for item in relationships
    )


@pytest.mark.parametrize(
    "config",
    [
        {},
        {"relationship": {}},
        {"relationship": {"unrelated": {}}},
    ],
    ids=["empty", "missing-metric-compatibility", "unrelated-key"],
)
def test_missing_relationship_configuration_generates_no_change_relationship(
    config: dict,
) -> None:
    insights = [
        _change("orders", "Orders", direction=InsightDirection.DOWN),
        _change("revenue", "Revenue"),
        _change("marketing", "MarketingSpend"),
    ]

    assert generate_relationships(insights, config) == []


def test_multi_edge_generation_preserves_all_relationship_contracts() -> None:
    insights, config = _multi_edge_fixture()
    relationships = generate_relationships(insights, config)

    assert [item.id for item in relationships] == [
        "CONTRIBUTES_TO-contribution-change-revenue",
        "COUNTER_SIGNAL-change-customers-change-revenue",
        "COUNTER_SIGNAL-change-orders-change-revenue",
        "CO_MOVES_WITH-change-marketing-change-revenue",
        "RELATED_ANOMALY-anomaly-change-revenue",
    ]
    assert Counter(item.type for item in relationships) == {
        RelationshipType.CONTRIBUTES_TO.value: 1,
        RelationshipType.COUNTER_SIGNAL.value: 2,
        RelationshipType.CO_MOVES_WITH.value: 1,
        RelationshipType.RELATED_ANOMALY.value: 1,
    }
    assert len({item.id for item in relationships}) == 5
    assert {
        (item.source_insight_id, item.target_insight_id)
        for item in relationships
    } == {
        ("contribution", "change-revenue"),
        ("change-orders", "change-revenue"),
        ("change-customers", "change-revenue"),
        ("change-marketing", "change-revenue"),
        ("anomaly", "change-revenue"),
    }
    assert all(item.analysis_id == "analysis-1" for item in relationships)
    assert all(
        item.source_insight_id != item.target_insight_id
        for item in relationships
    )
    assert all(0.0 <= item.strength <= 1.0 for item in relationships)
    assert all(0.0 <= item.confidence <= 1.0 for item in relationships)
    assert all(item.strength_breakdown for item in relationships)
    assert all(item.confidence_breakdown for item in relationships)
    assert all(item.reasons for item in relationships)

    for relationship in relationships:
        assert relationship.strength == pytest.approx(
            sum(relationship.strength_breakdown.values())
            / len(relationship.strength_breakdown)
        )
        assert relationship.confidence == pytest.approx(
            sum(relationship.confidence_breakdown.values())
            / len(relationship.confidence_breakdown)
        )


def test_multi_edge_generation_is_deterministic_across_input_permutations() -> None:
    insights, config = _multi_edge_fixture()
    manually_shuffled = [
        insights[4],
        insights[1],
        insights[5],
        insights[3],
        insights[0],
        insights[2],
    ]

    results = [
        generate_relationships(insights, config),
        generate_relationships(list(reversed(insights)), config),
        generate_relationships(manually_shuffled, config),
    ]
    serialized = [
        [item.model_dump(by_alias=True) for item in result]
        for result in results
    ]

    assert serialized[1:] == [serialized[0], serialized[0]]


def test_multi_edge_generation_is_repeatable_and_does_not_mutate_inputs() -> None:
    insights, config = _multi_edge_fixture()
    original_order = list(insights)
    insight_snapshots = [item.model_dump(by_alias=True) for item in insights]
    config_snapshot = deepcopy(config)

    first = generate_relationships(insights, config)
    second = generate_relationships(insights, config)

    assert [item.model_dump(by_alias=True) for item in first] == [
        item.model_dump(by_alias=True) for item in second
    ]
    assert insights == original_order
    assert [item.model_dump(by_alias=True) for item in insights] == insight_snapshots
    assert config == config_snapshot
