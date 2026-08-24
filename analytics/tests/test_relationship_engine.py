from copy import deepcopy

import pytest

from app.config.insight_config_loader import load_insight_config
from app.models.insight import (
    Insight,
    InsightDirection,
    InsightType,
    PeriodGranularity,
)
from app.models.relationship import RelationshipType
from app.services.relationship_engine import (
    anomaly_direction_matches_change,
    anomaly_matches_change_period,
    build_related_anomaly_relationship,
    build_co_moves_with_relationship,
    build_counter_signal_relationship,
    build_contributes_to_relationship,
    is_co_moves_with,
    is_contributes_to,
    is_counter_signal,
    is_related_anomaly,
    metrics_are_compatible,
    opposite_direction,
    same_analysis,
    same_dimension,
    same_direction,
    same_metric,
    same_period,
    same_segment,
)


def _insight(**overrides) -> Insight:
    values = {
        "id": "INSIGHT-001",
        "analysisId": "ANALYSIS-001",
        "type": InsightType.CHANGE,
        "metric": "Revenue",
        "dimension": "Region",
        "segment": "Marmara",
        "periodGranularity": PeriodGranularity.MONTH,
        "period": {"previous": "2025-05", "current": "2025-06"},
        "direction": InsightDirection.UP,
    }
    values.update(overrides)
    return Insight(**values)


@pytest.mark.parametrize(
    ("target_analysis_id", "expected"),
    [("ANALYSIS-001", True), ("ANALYSIS-002", False)],
)
def test_same_analysis(target_analysis_id, expected):
    assert same_analysis(
        _insight(),
        _insight(analysisId=target_analysis_id),
    ) is expected


@pytest.mark.parametrize(
    ("target_granularity", "target_period", "expected"),
    [
        (
            PeriodGranularity.MONTH,
            {"previous": "2025-05", "current": "2025-06"},
            True,
        ),
        (
            PeriodGranularity.MONTH,
            {"previous": "2025-06", "current": "2025-07"},
            False,
        ),
        (
            PeriodGranularity.QUARTER,
            {"previous": "2025-05", "current": "2025-06"},
            False,
        ),
    ],
)
def test_same_period(target_granularity, target_period, expected):
    assert same_period(
        _insight(),
        _insight(
            periodGranularity=target_granularity,
            period=target_period,
        ),
    ) is expected


@pytest.mark.parametrize(
    ("target_metric", "expected"),
    [("Revenue", True), ("Orders", False)],
)
def test_same_metric(target_metric, expected):
    assert same_metric(_insight(), _insight(metric=target_metric)) is expected


@pytest.mark.parametrize(
    ("source_dimension", "target_dimension", "expected"),
    [
        ("Region", "Region", True),
        ("Region", "Product", False),
        (None, None, False),
    ],
)
def test_same_dimension(source_dimension, target_dimension, expected):
    assert same_dimension(
        _insight(dimension=source_dimension),
        _insight(dimension=target_dimension),
    ) is expected


@pytest.mark.parametrize(
    ("source_segment", "target_segment", "expected"),
    [
        ("Marmara", "Marmara", True),
        ("Marmara", "Central Anatolia", False),
        (None, None, False),
    ],
)
def test_same_segment(source_segment, target_segment, expected):
    assert same_segment(
        _insight(segment=source_segment),
        _insight(segment=target_segment),
    ) is expected


@pytest.mark.parametrize(
    ("source_direction", "target_direction", "expected"),
    [
        (InsightDirection.UP, InsightDirection.UP, True),
        (InsightDirection.DOWN, InsightDirection.DOWN, True),
        (InsightDirection.UP, InsightDirection.DOWN, False),
        (InsightDirection.HIGH, InsightDirection.HIGH, False),
        (InsightDirection.STABLE, InsightDirection.STABLE, False),
    ],
)
def test_same_direction(source_direction, target_direction, expected):
    assert same_direction(
        _insight(direction=source_direction),
        _insight(direction=target_direction),
    ) is expected


@pytest.mark.parametrize(
    ("source_direction", "target_direction", "expected"),
    [
        (InsightDirection.UP, InsightDirection.DOWN, True),
        (InsightDirection.DOWN, InsightDirection.UP, True),
        (InsightDirection.UP, InsightDirection.UP, False),
        (InsightDirection.HIGH, InsightDirection.LOW, False),
        (InsightDirection.STABLE, InsightDirection.UP, False),
    ],
)
def test_opposite_direction(source_direction, target_direction, expected):
    assert opposite_direction(
        _insight(direction=source_direction),
        _insight(direction=target_direction),
    ) is expected


def test_direction_helpers_accept_enum_instances_and_string_values():
    source = _insight().model_copy(update={"direction": InsightDirection.UP})
    target = _insight().model_copy(update={"direction": "UP"})

    assert same_direction(source, target) is True

    target = target.model_copy(update={"direction": InsightDirection.DOWN})

    assert opposite_direction(source, target) is True


def _contribution(**overrides) -> Insight:
    values = {
        "id": "CONTRIBUTION-Revenue-Region-Marmara-2025-05-2025-06",
        "analysisId": "ANALYSIS-001",
        "type": InsightType.CONTRIBUTION,
        "metric": "Revenue",
        "dimension": "Region",
        "segment": "Marmara",
        "periodGranularity": PeriodGranularity.MONTH,
        "period": {"previous": "2025-05", "current": "2025-06"},
        "direction": InsightDirection.UP,
        "values": {
            "totalPreviousValue": 1_000_000,
            "totalCurrentValue": 1_300_000,
            "totalAbsoluteChange": 300_000,
            "contributionShare": 0.7,
        },
    }
    values.update(overrides)
    return Insight(**values)


def _company_change(**overrides) -> Insight:
    values = {
        "id": "CHANGE-Revenue-2025-05-2025-06",
        "analysisId": "ANALYSIS-001",
        "type": InsightType.CHANGE,
        "metric": "Revenue",
        "dimension": None,
        "segment": None,
        "periodGranularity": PeriodGranularity.MONTH,
        "period": {"previous": "2025-05", "current": "2025-06"},
        "direction": InsightDirection.UP,
        "values": {
            "previous": 1_000_000,
            "current": 1_300_000,
            "absoluteChange": 300_000,
        },
    }
    values.update(overrides)
    return Insight(**values)


def test_contribution_matches_company_level_change():
    assert is_contributes_to(_contribution(), _company_change()) is True


def test_contribution_with_opposite_direction_still_matches():
    source = _contribution(direction=InsightDirection.DOWN)

    assert is_contributes_to(source, _company_change()) is True


@pytest.mark.parametrize(
    ("source", "target"),
    [
        (_contribution(id="SHARED-ID"), _company_change(id="SHARED-ID")),
        (_contribution(), _company_change(analysisId="ANALYSIS-002")),
        (_contribution(), _company_change(metric="Orders")),
        (
            _contribution(),
            _company_change(
                period={"previous": "2025-06", "current": "2025-07"}
            ),
        ),
        (_contribution(type=InsightType.CHANGE), _company_change()),
        (_contribution(), _company_change(type=InsightType.TREND)),
        (_contribution(), _company_change(dimension="Region", segment="Marmara")),
        (_contribution(dimension=None), _company_change()),
        (_contribution(segment=None), _company_change()),
    ],
    ids=[
        "same-insight-id",
        "different-analysis",
        "different-metric",
        "different-period",
        "source-not-contribution",
        "target-not-change",
        "segment-level-target",
        "source-without-dimension",
        "source-without-segment",
    ],
)
def test_contribution_rejects_structural_non_matches(source, target):
    assert is_contributes_to(source, target) is False


@pytest.mark.parametrize(
    ("source_values", "target_values"),
    [
        (
            {
                "totalPreviousValue": 999_999,
                "totalCurrentValue": 1_300_000,
                "totalAbsoluteChange": 300_000,
            },
            {"previous": 1_000_000, "current": 1_300_000, "absoluteChange": 300_000},
        ),
        (
            {
                "totalPreviousValue": 1_000_000,
                "totalCurrentValue": 1_299_999,
                "totalAbsoluteChange": 300_000,
            },
            {"previous": 1_000_000, "current": 1_300_000, "absoluteChange": 300_000},
        ),
        (
            {
                "totalPreviousValue": 1_000_000,
                "totalCurrentValue": 1_300_000,
                "totalAbsoluteChange": 299_999,
            },
            {"previous": 1_000_000, "current": 1_300_000, "absoluteChange": 300_000},
        ),
        (
            {"totalCurrentValue": 1_300_000, "totalAbsoluteChange": 300_000},
            {"previous": 1_000_000, "current": 1_300_000, "absoluteChange": 300_000},
        ),
        (
            {
                "totalPreviousValue": 1_000_000,
                "totalCurrentValue": 1_300_000,
                "totalAbsoluteChange": 300_000,
            },
            {"previous": 1_000_000, "absoluteChange": 300_000},
        ),
        (
            {
                "totalPreviousValue": float("nan"),
                "totalCurrentValue": 1_300_000,
                "totalAbsoluteChange": 300_000,
            },
            {"previous": 1_000_000, "current": 1_300_000, "absoluteChange": 300_000},
        ),
        (
            {
                "totalPreviousValue": 1_000_000,
                "totalCurrentValue": float("inf"),
                "totalAbsoluteChange": 300_000,
            },
            {"previous": 1_000_000, "current": 1_300_000, "absoluteChange": 300_000},
        ),
        (
            {
                "totalPreviousValue": True,
                "totalCurrentValue": 1_300_000,
                "totalAbsoluteChange": 300_000,
            },
            {"previous": 1_000_000, "current": 1_300_000, "absoluteChange": 300_000},
        ),
    ],
    ids=[
        "previous-mismatch",
        "current-mismatch",
        "absolute-change-mismatch",
        "missing-source-value",
        "missing-target-value",
        "nan-value",
        "infinite-value",
        "boolean-impostor",
    ],
)
def test_contribution_rejects_invalid_or_mismatched_totals(
    source_values,
    target_values,
):
    assert is_contributes_to(
        _contribution(values=source_values),
        _company_change(values=target_values),
    ) is False


def test_contribution_rule_accepts_enum_instances_and_string_values():
    source = _contribution().model_copy(update={"type": InsightType.CONTRIBUTION})
    target = _company_change().model_copy(update={"type": "CHANGE"})

    assert is_contributes_to(source, target) is True


def test_builds_contributes_to_relationship():
    source = _contribution(confidence=0.8)
    target = _company_change(confidence=0.9)

    relationship = build_contributes_to_relationship(source, target)

    assert relationship is not None
    assert relationship.type == "CONTRIBUTES_TO"
    assert relationship.analysis_id == "ANALYSIS-001"
    assert relationship.source_insight_id == source.id
    assert relationship.target_insight_id == target.id
    assert relationship.id == (
        f"CONTRIBUTES_TO-{source.id}-{target.id}"
    )
    assert relationship.id == build_contributes_to_relationship(source, target).id
    assert 0.0 <= relationship.strength <= 1.0
    assert relationship.strength_breakdown == {
        "temporalCompatibility": 1.0,
        "metricCompatibility": 1.0,
        "structuralCompatibility": 1.0,
        "arithmeticCompatibility": 1.0,
    }
    assert 0.0 <= relationship.confidence <= 1.0
    assert relationship.confidence == pytest.approx(0.9)
    assert relationship.confidence_breakdown == {
        "sourceInsightConfidence": 0.8,
        "targetInsightConfidence": 0.9,
        "arithmeticVerification": 1.0,
    }
    assert "Same metric: Revenue" in relationship.reasons
    assert "Same comparison period: 2025-05 to 2025-06" in relationship.reasons
    assert "Marmara contributed 70.0% of the total Revenue change" in relationship.reasons
    assert relationship.metadata == {
        "dimension": "Region",
        "segment": "Marmara",
        "contributionShare": 0.7,
    }


def test_build_contributes_to_returns_none_for_semantic_non_match():
    target = _company_change(metric="Orders")

    assert build_contributes_to_relationship(_contribution(), target) is None


@pytest.mark.parametrize(
    ("source_confidence", "target_confidence", "expected_source", "expected_target"),
    [
        (0.7, 0.8, 0.7, 0.8),
        (None, None, 0.5, 0.5),
        (float("nan"), 0.8, 0.5, 0.8),
        (0.7, float("inf"), 0.7, 0.5),
        (True, False, 0.5, 0.5),
    ],
    ids=[
        "valid",
        "missing",
        "nan",
        "infinite",
        "boolean",
    ],
)
def test_relationship_confidence_is_safe(
    source_confidence,
    target_confidence,
    expected_source,
    expected_target,
):
    source = _contribution().model_copy(update={"confidence": source_confidence})
    target = _company_change().model_copy(update={"confidence": target_confidence})

    relationship = build_contributes_to_relationship(source, target)

    assert relationship is not None
    assert relationship.confidence_breakdown == {
        "sourceInsightConfidence": expected_source,
        "targetInsightConfidence": expected_target,
        "arithmeticVerification": 1.0,
    }
    assert relationship.confidence == pytest.approx(
        (expected_source + expected_target + 1.0) / 3
    )
    assert 0.0 <= relationship.confidence <= 1.0


@pytest.mark.parametrize(
    "contribution_share",
    [None, float("nan"), float("inf"), True, "0.7"],
)
def test_invalid_contribution_share_is_omitted(contribution_share):
    source_values = {
        "totalPreviousValue": 1_000_000,
        "totalCurrentValue": 1_300_000,
        "totalAbsoluteChange": 300_000,
        "contributionShare": contribution_share,
    }

    relationship = build_contributes_to_relationship(
        _contribution(values=source_values),
        _company_change(),
    )

    assert relationship is not None
    assert "contributionShare" not in relationship.metadata
    assert not any("contributed" in reason for reason in relationship.reasons)


def test_relationship_reasons_and_metadata_use_no_causal_wording():
    relationship = build_contributes_to_relationship(
        _contribution(),
        _company_change(),
    )

    assert relationship is not None
    serialized_evidence = str(
        {
            "reasons": relationship.reasons,
            "metadata": relationship.metadata,
        }
    ).upper()
    causal_terms = {
        "CAUSED",
        "CAUSED_BY",
        "LED_TO",
        "RESULTED_IN",
        "DRIVEN_BY",
    }

    assert all(term not in serialized_evidence for term in causal_terms)


@pytest.mark.parametrize(
    ("source_metric", "target_metric", "relationship_type"),
    [
        ("Orders", "Revenue", RelationshipType.COUNTER_SIGNAL),
        ("Customers", "Revenue", "COUNTER_SIGNAL"),
        ("MarketingSpend", "Revenue", RelationshipType.CO_MOVES_WITH),
    ],
)
def test_configured_metrics_are_compatible(
    source_metric,
    target_metric,
    relationship_type,
):
    assert metrics_are_compatible(
        _insight(metric=source_metric),
        _insight(metric=target_metric),
        relationship_type,
        load_insight_config(),
    ) is True


@pytest.mark.parametrize(
    ("source_metric", "target_metric", "relationship_type"),
    [
        ("Revenue", "Orders", "COUNTER_SIGNAL"),
        ("Revenue", "Customers", "COUNTER_SIGNAL"),
        ("MarketingSpend", "Revenue", "COUNTER_SIGNAL"),
        ("Orders", "Revenue", "CO_MOVES_WITH"),
        ("Units", "Revenue", "COUNTER_SIGNAL"),
        ("Orders", "Revenue", "UNKNOWN"),
    ],
)
def test_unconfigured_metrics_are_not_compatible(
    source_metric,
    target_metric,
    relationship_type,
):
    assert metrics_are_compatible(
        _insight(metric=source_metric),
        _insight(metric=target_metric),
        relationship_type,
        load_insight_config(),
    ) is False


@pytest.mark.parametrize(
    "config",
    [
        {},
        {"relationship": {}},
        {"relationship": {"metricCompatibility": {}}},
        {
            "relationship": {
                "metricCompatibility": {"COUNTER_SIGNAL": {}}
            }
        },
        {
            "relationship": {
                "metricCompatibility": {
                    "COUNTER_SIGNAL": [
                        None,
                        "Orders:Revenue",
                        {},
                        {"sourceMetric": "Orders"},
                        {"targetMetric": "Revenue"},
                    ]
                }
            }
        },
    ],
)
def test_invalid_metric_compatibility_config_returns_false(config):
    assert metrics_are_compatible(
        _insight(metric="Orders"),
        _insight(metric="Revenue"),
        RelationshipType.COUNTER_SIGNAL,
        config,
    ) is False


def test_malformed_pair_does_not_prevent_later_valid_match():
    config = {
        "relationship": {
            "metricCompatibility": {
                "COUNTER_SIGNAL": [
                    {"sourceMetric": "Orders"},
                    {"sourceMetric": "Orders", "targetMetric": "Revenue"},
                ]
            }
        }
    }

    assert metrics_are_compatible(
        _insight(metric="Orders"),
        _insight(metric="Revenue"),
        "COUNTER_SIGNAL",
        config,
    ) is True


def test_metrics_are_compatible_does_not_mutate_config():
    config = load_insight_config()
    original = deepcopy(config)

    metrics_are_compatible(
        _insight(metric="Orders"),
        _insight(metric="Revenue"),
        RelationshipType.COUNTER_SIGNAL,
        config,
    )

    assert config == original


def test_insight_config_loads_relationship_section_without_changing_existing_values():
    config = load_insight_config()

    assert config["period"] == {"defaultGranularity": "MONTH"}
    assert config["change"] == {"minimumPercentageChange": 5.0}
    assert config["trend"] == {
        "minimumPeriods": 6,
        "highPersistenceThreshold": 0.8,
        "minimumPersistenceThreshold": 0.75,
    }
    assert config["anomaly"] == {
        "minimumPeriods": 6,
        "method": "IQR",
        "iqrMultiplier": 2.0,
    }
    assert config["contribution"] == {"minimumAbsoluteContributionShare": 0.20}
    assert config["contrast"] == {"minimumPercentagePointGap": 10.0}
    assert config["confidence"] == {
        "weights": {
            "dataQuality": 0.30,
            "sampleSufficiency": 0.20,
            "signalStrength": 0.30,
            "consistency": 0.20,
        }
    }
    assert config["relationship"]["metricCompatibility"] == {
        "COUNTER_SIGNAL": [
            {"sourceMetric": "Orders", "targetMetric": "Revenue"},
            {"sourceMetric": "Customers", "targetMetric": "Revenue"},
        ],
        "CO_MOVES_WITH": [
            {"sourceMetric": "MarketingSpend", "targetMetric": "Revenue"}
        ],
    }


@pytest.mark.parametrize("source_metric", ["Orders", "Customers"])
def test_golden_like_counter_signal_matches(source_metric):
    source = _company_change(
        id=f"CHANGE-{source_metric}-2025-05-2025-06",
        metric=source_metric,
        direction=InsightDirection.DOWN,
    )

    assert is_counter_signal(
        source,
        _company_change(),
        load_insight_config(),
    ) is True


def test_compatible_up_down_pair_matches_counter_signal():
    config = {
        "relationship": {
            "metricCompatibility": {
                "COUNTER_SIGNAL": [
                    {"sourceMetric": "Units", "targetMetric": "Revenue"}
                ]
            }
        }
    }
    source = _company_change(
        id="CHANGE-Units-2025-05-2025-06",
        metric="Units",
        direction=InsightDirection.UP,
    )
    target = _company_change(direction=InsightDirection.DOWN)

    assert is_counter_signal(source, target, config) is True


@pytest.mark.parametrize(
    ("source", "target"),
    [
        (
            _company_change(
                id="SHARED-ID",
                metric="Orders",
                direction=InsightDirection.DOWN,
            ),
            _company_change(id="SHARED-ID"),
        ),
        (
            _company_change(metric="Orders", direction=InsightDirection.DOWN),
            _company_change(analysisId="ANALYSIS-002"),
        ),
        (
            _company_change(
                metric="Orders",
                type=InsightType.TREND,
                direction=InsightDirection.DOWN,
            ),
            _company_change(),
        ),
        (
            _company_change(metric="Orders", direction=InsightDirection.DOWN),
            _company_change(type=InsightType.TREND),
        ),
        (
            _company_change(
                metric="Orders",
                dimension="Region",
                segment="Marmara",
                direction=InsightDirection.DOWN,
            ),
            _company_change(),
        ),
        (
            _company_change(metric="Orders", direction=InsightDirection.DOWN),
            _company_change(dimension="Region", segment="Marmara"),
        ),
        (
            _company_change(metric="Orders", direction=InsightDirection.DOWN),
            _company_change(
                period={"previous": "2025-06", "current": "2025-07"}
            ),
        ),
    ],
    ids=[
        "same-insight-id",
        "different-analysis",
        "source-not-change",
        "target-not-change",
        "segment-level-source",
        "segment-level-target",
        "different-period",
    ],
)
def test_counter_signal_rejects_structural_non_matches(source, target):
    assert is_counter_signal(source, target, load_insight_config()) is False


@pytest.mark.parametrize(
    ("source_metric", "target_metric"),
    [
        ("Units", "Revenue"),
        ("Revenue", "Orders"),
        ("MarketingSpend", "Revenue"),
    ],
    ids=[
        "unconfigured-pair",
        "reverse-pair",
        "co-moves-only-pair",
    ],
)
def test_counter_signal_rejects_semantically_incompatible_metrics(
    source_metric,
    target_metric,
):
    source = _company_change(
        id=f"CHANGE-{source_metric}-2025-05-2025-06",
        metric=source_metric,
        direction=InsightDirection.DOWN,
    )
    target = _company_change(metric=target_metric)

    assert is_counter_signal(source, target, load_insight_config()) is False


@pytest.mark.parametrize(
    ("source_direction", "target_direction"),
    [
        (InsightDirection.UP, InsightDirection.UP),
        (InsightDirection.DOWN, InsightDirection.DOWN),
        (InsightDirection.HIGH, InsightDirection.LOW),
        (InsightDirection.STABLE, InsightDirection.UP),
    ],
    ids=["up-up", "down-down", "high-low", "stable-involved"],
)
def test_counter_signal_rejects_non_opposite_change_directions(
    source_direction,
    target_direction,
):
    source = _company_change(
        id="CHANGE-Orders-2025-05-2025-06",
        metric="Orders",
        direction=source_direction,
    )
    target = _company_change(direction=target_direction)

    assert is_counter_signal(source, target, load_insight_config()) is False


def test_counter_signal_accepts_enum_and_string_insight_types():
    source = _company_change(
        id="CHANGE-Orders-2025-05-2025-06",
        metric="Orders",
        direction=InsightDirection.DOWN,
    ).model_copy(update={"type": InsightType.CHANGE})
    target = _company_change().model_copy(update={"type": "CHANGE"})

    assert is_counter_signal(source, target, load_insight_config()) is True


@pytest.mark.parametrize(
    "config",
    [
        {},
        {"relationship": {}},
        {"relationship": {"metricCompatibility": {"COUNTER_SIGNAL": {}}}},
    ],
)
def test_counter_signal_invalid_config_returns_false(config):
    source = _company_change(
        id="CHANGE-Orders-2025-05-2025-06",
        metric="Orders",
        direction=InsightDirection.DOWN,
    )

    assert is_counter_signal(source, _company_change(), config) is False


def test_counter_signal_does_not_mutate_config():
    config = load_insight_config()
    original = deepcopy(config)
    source = _company_change(
        id="CHANGE-Orders-2025-05-2025-06",
        metric="Orders",
        direction=InsightDirection.DOWN,
    )

    is_counter_signal(source, _company_change(), config)

    assert config == original


@pytest.mark.parametrize("source_metric", ["Orders", "Customers"])
def test_builds_golden_like_counter_signal_relationship(source_metric):
    source = _company_change(
        id=f"CHANGE-{source_metric}-2025-05-2025-06",
        metric=source_metric,
        direction=InsightDirection.DOWN,
        confidence=0.8,
    )
    target = _company_change(confidence=0.9)

    relationship = build_counter_signal_relationship(
        source,
        target,
        load_insight_config(),
    )

    assert relationship is not None
    assert relationship.type == "COUNTER_SIGNAL"
    assert relationship.analysis_id == "ANALYSIS-001"
    assert relationship.source_insight_id == source.id
    assert relationship.target_insight_id == target.id
    assert relationship.id == f"COUNTER_SIGNAL-{source.id}-{target.id}"
    assert relationship.id == build_counter_signal_relationship(
        source,
        target,
        load_insight_config(),
    ).id
    assert 0.0 <= relationship.strength <= 1.0
    assert relationship.strength_breakdown == {
        "temporalCompatibility": 1.0,
        "metricCompatibility": 1.0,
        "directionalOpposition": 1.0,
        "structuralCompatibility": 1.0,
    }
    assert 0.0 <= relationship.confidence <= 1.0
    assert relationship.confidence == pytest.approx(0.9)
    assert relationship.confidence_breakdown == {
        "sourceInsightConfidence": 0.8,
        "targetInsightConfidence": 0.9,
        "semanticCompatibility": 1.0,
    }
    assert "Same comparison period: 2025-05 to 2025-06" in relationship.reasons
    assert (
        f"Configured COUNTER_SIGNAL metric pair: {source_metric} -> Revenue"
        in relationship.reasons
    )
    assert (
        f"{source_metric} moved DOWN while Revenue moved UP"
        in relationship.reasons
    )
    assert relationship.metadata == {
        "sourceMetric": source_metric,
        "targetMetric": "Revenue",
        "sourceDirection": "DOWN",
        "targetDirection": "UP",
    }


@pytest.mark.parametrize(
    ("source", "target"),
    [
        (
            _company_change(
                id="CHANGE-Orders-2025-05-2025-06",
                metric="Orders",
                direction=InsightDirection.DOWN,
            ),
            _company_change(analysisId="ANALYSIS-002"),
        ),
        (
            _company_change(
                id="CHANGE-Orders-2025-05-2025-06",
                metric="Orders",
                direction=InsightDirection.UP,
            ),
            _company_change(),
        ),
        (
            _company_change(
                id="CHANGE-Units-2025-05-2025-06",
                metric="Units",
                direction=InsightDirection.DOWN,
            ),
            _company_change(),
        ),
        (
            _company_change(
                id="CHANGE-Revenue-SOURCE-2025-05-2025-06",
                metric="Revenue",
                direction=InsightDirection.UP,
            ),
            _company_change(
                id="CHANGE-Orders-TARGET-2025-05-2025-06",
                metric="Orders",
                direction=InsightDirection.DOWN,
            ),
        ),
    ],
    ids=[
        "semantic-non-match",
        "same-direction",
        "unconfigured-pair",
        "reverse-pair",
    ],
)
def test_build_counter_signal_returns_none_for_non_match(source, target):
    assert build_counter_signal_relationship(
        source,
        target,
        load_insight_config(),
    ) is None


@pytest.mark.parametrize(
    ("source_confidence", "target_confidence", "expected_source", "expected_target"),
    [
        (0.7, 0.8, 0.7, 0.8),
        (None, None, 0.5, 0.5),
        (float("nan"), 0.8, 0.5, 0.8),
        (0.7, float("inf"), 0.7, 0.5),
        (True, False, 0.5, 0.5),
    ],
    ids=["valid", "none", "nan", "infinite", "boolean"],
)
def test_counter_signal_relationship_confidence_is_safe(
    source_confidence,
    target_confidence,
    expected_source,
    expected_target,
):
    source = _company_change(
        id="CHANGE-Orders-2025-05-2025-06",
        metric="Orders",
        direction=InsightDirection.DOWN,
    ).model_copy(update={"confidence": source_confidence})
    target = _company_change().model_copy(update={"confidence": target_confidence})

    relationship = build_counter_signal_relationship(
        source,
        target,
        load_insight_config(),
    )

    assert relationship is not None
    assert relationship.confidence_breakdown == {
        "sourceInsightConfidence": expected_source,
        "targetInsightConfidence": expected_target,
        "semanticCompatibility": 1.0,
    }
    assert relationship.confidence == pytest.approx(
        (expected_source + expected_target + 1.0) / 3
    )
    assert 0.0 <= relationship.confidence <= 1.0


def test_build_counter_signal_does_not_mutate_config():
    config = load_insight_config()
    original = deepcopy(config)
    source = _company_change(
        id="CHANGE-Orders-2025-05-2025-06",
        metric="Orders",
        direction=InsightDirection.DOWN,
    )

    build_counter_signal_relationship(source, _company_change(), config)

    assert config == original


def test_counter_signal_relationship_has_no_conclusions_or_causal_language():
    source = _company_change(
        id="CHANGE-Orders-2025-05-2025-06",
        metric="Orders",
        direction=InsightDirection.DOWN,
    )
    relationship = build_counter_signal_relationship(
        source,
        _company_change(),
        load_insight_config(),
    )

    assert relationship is not None
    serialized_evidence = str(
        {
            "reasons": relationship.reasons,
            "metadata": relationship.metadata,
        }
    ).upper()
    prohibited_terms = {
        "CONTRADICTION",
        "COUNTER_EVIDENCE",
        "CAUSED",
        "CAUSED_BY",
        "LED_TO",
        "BECAUSE_OF",
        "RESULTED_IN",
        "DRIVEN_BY",
    }

    assert all(term not in serialized_evidence for term in prohibited_terms)


def test_marketing_spend_and_revenue_move_together():
    source = _company_change(
        id="CHANGE-MarketingSpend-2025-05-2025-06",
        metric="MarketingSpend",
        direction=InsightDirection.UP,
    )

    assert is_co_moves_with(
        source,
        _company_change(),
        load_insight_config(),
    ) is True


def test_custom_compatible_down_pair_moves_together():
    config = {
        "relationship": {
            "metricCompatibility": {
                "CO_MOVES_WITH": [
                    {"sourceMetric": "Units", "targetMetric": "Revenue"}
                ]
            }
        }
    }
    source = _company_change(
        id="CHANGE-Units-2025-05-2025-06",
        metric="Units",
        direction=InsightDirection.DOWN,
    )
    target = _company_change(direction=InsightDirection.DOWN)

    assert is_co_moves_with(source, target, config) is True


@pytest.mark.parametrize(
    ("source", "target"),
    [
        (
            _company_change(
                id="SHARED-ID",
                metric="MarketingSpend",
            ),
            _company_change(id="SHARED-ID"),
        ),
        (
            _company_change(metric="MarketingSpend"),
            _company_change(analysisId="ANALYSIS-002"),
        ),
        (
            _company_change(metric="MarketingSpend", type=InsightType.TREND),
            _company_change(),
        ),
        (
            _company_change(metric="MarketingSpend"),
            _company_change(type=InsightType.TREND),
        ),
        (
            _company_change(
                metric="MarketingSpend",
                dimension="Region",
                segment="Marmara",
            ),
            _company_change(),
        ),
        (
            _company_change(metric="MarketingSpend"),
            _company_change(dimension="Region", segment="Marmara"),
        ),
        (
            _company_change(metric="MarketingSpend"),
            _company_change(
                period={"previous": "2025-06", "current": "2025-07"}
            ),
        ),
    ],
    ids=[
        "same-insight-id",
        "different-analysis",
        "source-not-change",
        "target-not-change",
        "segment-level-source",
        "segment-level-target",
        "different-period",
    ],
)
def test_co_moves_with_rejects_structural_non_matches(source, target):
    assert is_co_moves_with(source, target, load_insight_config()) is False


@pytest.mark.parametrize(
    ("source_metric", "target_metric"),
    [
        ("Units", "Revenue"),
        ("Revenue", "MarketingSpend"),
        ("Orders", "Revenue"),
    ],
    ids=["unconfigured-pair", "reverse-pair", "counter-signal-only-pair"],
)
def test_co_moves_with_rejects_semantically_incompatible_metrics(
    source_metric,
    target_metric,
):
    source = _company_change(
        id=f"CHANGE-{source_metric}-2025-05-2025-06",
        metric=source_metric,
    )
    target = _company_change(metric=target_metric)

    assert is_co_moves_with(source, target, load_insight_config()) is False


@pytest.mark.parametrize(
    ("source_direction", "target_direction"),
    [
        (InsightDirection.UP, InsightDirection.DOWN),
        (InsightDirection.DOWN, InsightDirection.UP),
        (InsightDirection.HIGH, InsightDirection.HIGH),
        (InsightDirection.LOW, InsightDirection.LOW),
        (InsightDirection.STABLE, InsightDirection.STABLE),
    ],
    ids=["up-down", "down-up", "high-high", "low-low", "stable"],
)
def test_co_moves_with_rejects_non_ordinary_shared_directions(
    source_direction,
    target_direction,
):
    source = _company_change(
        id="CHANGE-MarketingSpend-2025-05-2025-06",
        metric="MarketingSpend",
        direction=source_direction,
    )
    target = _company_change(direction=target_direction)

    assert is_co_moves_with(source, target, load_insight_config()) is False


def test_co_moves_with_accepts_enum_and_string_insight_types():
    source = _company_change(
        id="CHANGE-MarketingSpend-2025-05-2025-06",
        metric="MarketingSpend",
    ).model_copy(update={"type": InsightType.CHANGE})
    target = _company_change().model_copy(update={"type": "CHANGE"})

    assert is_co_moves_with(source, target, load_insight_config()) is True


@pytest.mark.parametrize(
    "config",
    [
        {},
        {"relationship": {}},
        {"relationship": {"metricCompatibility": {"CO_MOVES_WITH": {}}}},
    ],
)
def test_co_moves_with_invalid_config_returns_false(config):
    source = _company_change(
        id="CHANGE-MarketingSpend-2025-05-2025-06",
        metric="MarketingSpend",
    )

    assert is_co_moves_with(source, _company_change(), config) is False


def test_co_moves_with_does_not_mutate_config():
    config = load_insight_config()
    original = deepcopy(config)
    source = _company_change(
        id="CHANGE-MarketingSpend-2025-05-2025-06",
        metric="MarketingSpend",
    )

    is_co_moves_with(source, _company_change(), config)

    assert config == original


def test_co_moves_with_is_only_a_boolean_non_causal_match():
    source = _company_change(
        id="CHANGE-MarketingSpend-2025-05-2025-06",
        metric="MarketingSpend",
    )

    result = is_co_moves_with(
        source,
        _company_change(),
        load_insight_config(),
    )

    assert type(result) is bool
    assert result is True


def test_builds_golden_like_co_moves_with_relationship():
    source = _company_change(
        id="CHANGE-MarketingSpend-2025-05-2025-06",
        metric="MarketingSpend",
        confidence=0.8,
    )
    target = _company_change(confidence=0.9)

    relationship = build_co_moves_with_relationship(
        source,
        target,
        load_insight_config(),
    )

    assert relationship is not None
    assert relationship.type == "CO_MOVES_WITH"
    assert relationship.analysis_id == "ANALYSIS-001"
    assert relationship.source_insight_id == source.id
    assert relationship.target_insight_id == target.id
    assert relationship.id == f"CO_MOVES_WITH-{source.id}-{target.id}"
    assert relationship.id == build_co_moves_with_relationship(
        source,
        target,
        load_insight_config(),
    ).id
    assert 0.0 <= relationship.strength <= 1.0
    assert relationship.strength_breakdown == {
        "temporalCompatibility": 1.0,
        "metricCompatibility": 1.0,
        "directionalAlignment": 1.0,
        "structuralCompatibility": 1.0,
    }
    assert 0.0 <= relationship.confidence <= 1.0
    assert relationship.confidence == pytest.approx(0.9)
    assert relationship.confidence_breakdown == {
        "sourceInsightConfidence": 0.8,
        "targetInsightConfidence": 0.9,
        "semanticCompatibility": 1.0,
    }
    assert "Same comparison period: 2025-05 to 2025-06" in relationship.reasons
    assert (
        "Configured CO_MOVES_WITH metric pair: MarketingSpend -> Revenue"
        in relationship.reasons
    )
    assert (
        "MarketingSpend and Revenue both moved UP"
        in relationship.reasons
    )
    assert relationship.metadata == {
        "sourceMetric": "MarketingSpend",
        "targetMetric": "Revenue",
        "sourceDirection": "UP",
        "targetDirection": "UP",
    }


def test_builds_custom_down_co_moves_with_relationship():
    config = {
        "relationship": {
            "metricCompatibility": {
                "CO_MOVES_WITH": [
                    {"sourceMetric": "Units", "targetMetric": "Revenue"}
                ]
            }
        }
    }
    source = _company_change(
        id="CHANGE-Units-2025-05-2025-06",
        metric="Units",
        direction=InsightDirection.DOWN,
    )
    target = _company_change(direction=InsightDirection.DOWN)

    relationship = build_co_moves_with_relationship(source, target, config)

    assert relationship is not None
    assert relationship.metadata["sourceDirection"] == "DOWN"
    assert relationship.metadata["targetDirection"] == "DOWN"
    assert "Units and Revenue both moved DOWN" in relationship.reasons


@pytest.mark.parametrize(
    ("source", "target"),
    [
        (
            _company_change(
                id="CHANGE-MarketingSpend-2025-05-2025-06",
                metric="MarketingSpend",
            ),
            _company_change(analysisId="ANALYSIS-002"),
        ),
        (
            _company_change(
                id="CHANGE-MarketingSpend-2025-05-2025-06",
                metric="MarketingSpend",
                direction=InsightDirection.DOWN,
            ),
            _company_change(),
        ),
        (
            _company_change(
                id="CHANGE-Units-2025-05-2025-06",
                metric="Units",
            ),
            _company_change(),
        ),
        (
            _company_change(
                id="CHANGE-Revenue-SOURCE-2025-05-2025-06",
                metric="Revenue",
            ),
            _company_change(
                id="CHANGE-MarketingSpend-TARGET-2025-05-2025-06",
                metric="MarketingSpend",
            ),
        ),
    ],
    ids=[
        "semantic-non-match",
        "opposite-direction",
        "unconfigured-pair",
        "reverse-pair",
    ],
)
def test_build_co_moves_with_returns_none_for_non_match(source, target):
    assert build_co_moves_with_relationship(
        source,
        target,
        load_insight_config(),
    ) is None


@pytest.mark.parametrize(
    ("source_confidence", "target_confidence", "expected_source", "expected_target"),
    [
        (0.7, 0.8, 0.7, 0.8),
        (None, None, 0.5, 0.5),
        (float("nan"), 0.8, 0.5, 0.8),
        (0.7, float("inf"), 0.7, 0.5),
        (True, False, 0.5, 0.5),
    ],
    ids=["valid", "none", "nan", "infinite", "boolean"],
)
def test_co_moves_with_relationship_confidence_is_safe(
    source_confidence,
    target_confidence,
    expected_source,
    expected_target,
):
    source = _company_change(
        id="CHANGE-MarketingSpend-2025-05-2025-06",
        metric="MarketingSpend",
    ).model_copy(update={"confidence": source_confidence})
    target = _company_change().model_copy(update={"confidence": target_confidence})

    relationship = build_co_moves_with_relationship(
        source,
        target,
        load_insight_config(),
    )

    assert relationship is not None
    assert relationship.confidence_breakdown == {
        "sourceInsightConfidence": expected_source,
        "targetInsightConfidence": expected_target,
        "semanticCompatibility": 1.0,
    }
    assert relationship.confidence == pytest.approx(
        (expected_source + expected_target + 1.0) / 3
    )
    assert 0.0 <= relationship.confidence <= 1.0


def test_build_co_moves_with_does_not_mutate_config():
    config = load_insight_config()
    original = deepcopy(config)
    source = _company_change(
        id="CHANGE-MarketingSpend-2025-05-2025-06",
        metric="MarketingSpend",
    )

    build_co_moves_with_relationship(source, _company_change(), config)

    assert config == original


def test_co_moves_with_relationship_has_no_causal_or_correlation_claims():
    source = _company_change(
        id="CHANGE-MarketingSpend-2025-05-2025-06",
        metric="MarketingSpend",
    )
    relationship = build_co_moves_with_relationship(
        source,
        _company_change(),
        load_insight_config(),
    )

    assert relationship is not None
    serialized_evidence = str(
        {
            "reasons": relationship.reasons,
            "metadata": relationship.metadata,
        }
    ).upper()
    prohibited_terms = {
        "CAUSAL",
        "CAUSED",
        "BECAUSE",
        "LED_TO",
        "RESULTED_IN",
        "DRIVER",
        "DRIVEN",
        "CORRELATION",
        "PEARSON",
    }

    assert all(term not in serialized_evidence for term in prohibited_terms)


def test_anomaly_matches_change_current_period():
    anomaly = _insight(period={"current": "2025-06"})
    change = _insight(
        period={"previous": "2025-05", "current": "2025-06"}
    )

    assert anomaly_matches_change_period(anomaly, change) is True


@pytest.mark.parametrize(
    ("anomaly_period", "change_period"),
    [
        (
            {"current": "2025-06"},
            {"previous": "2025-06", "current": "2025-07"},
        ),
        (
            {},
            {"previous": "2025-05", "current": "2025-06"},
        ),
        (
            {"current": "2025-06"},
            {"previous": "2025-05"},
        ),
        (
            {"current": None},
            {"previous": "2025-05", "current": "2025-06"},
        ),
        (
            {"current": "2025-06"},
            {"previous": "2025-05", "current": None},
        ),
    ],
    ids=[
        "different-current",
        "missing-anomaly-current",
        "missing-change-current",
        "none-anomaly-current",
        "none-change-current",
    ],
)
def test_anomaly_change_period_rejects_missing_or_different_current(
    anomaly_period,
    change_period,
):
    anomaly = _insight().model_copy(update={"period": anomaly_period})
    change = _insight().model_copy(update={"period": change_period})

    assert anomaly_matches_change_period(anomaly, change) is False


def test_anomaly_change_period_rejects_different_granularity():
    anomaly = _insight(
        periodGranularity=PeriodGranularity.MONTH,
        period={"current": "2025-06"},
    )
    change = _insight(
        periodGranularity=PeriodGranularity.QUARTER,
        period={"previous": "2025-05", "current": "2025-06"},
    )

    assert anomaly_matches_change_period(anomaly, change) is False


def test_anomaly_change_period_accepts_enum_and_string_granularity():
    anomaly = _insight(period={"current": "2025-06"}).model_copy(
        update={"period_granularity": PeriodGranularity.MONTH}
    )
    change = _insight().model_copy(update={"period_granularity": "MONTH"})

    assert anomaly_matches_change_period(anomaly, change) is True


@pytest.mark.parametrize("malformed_period", [None, [], "2025-06"])
def test_anomaly_change_period_rejects_malformed_period(malformed_period):
    anomaly = _insight().model_copy(update={"period": malformed_period})

    assert anomaly_matches_change_period(anomaly, _insight()) is False


def test_anomaly_change_period_does_not_mutate_insights():
    anomaly = _insight(period={"current": "2025-06"})
    change = _insight()
    anomaly_before = anomaly.model_dump()
    change_before = change.model_dump()

    anomaly_matches_change_period(anomaly, change)

    assert anomaly.model_dump() == anomaly_before
    assert change.model_dump() == change_before


def test_same_period_still_rejects_anomaly_and_change_period_shapes():
    anomaly = _insight(period={"current": "2025-06"})
    change = _insight(
        period={"previous": "2025-05", "current": "2025-06"}
    )

    assert same_period(anomaly, change) is False


@pytest.mark.parametrize(
    ("anomaly_direction", "change_direction", "expected"),
    [
        (InsightDirection.HIGH, InsightDirection.UP, True),
        (InsightDirection.LOW, InsightDirection.DOWN, True),
        (InsightDirection.HIGH, InsightDirection.DOWN, False),
        (InsightDirection.LOW, InsightDirection.UP, False),
        (InsightDirection.HIGH, InsightDirection.HIGH, False),
        (InsightDirection.UP, InsightDirection.UP, False),
        (InsightDirection.STABLE, InsightDirection.STABLE, False),
    ],
)
def test_anomaly_direction_matches_change_direction(
    anomaly_direction,
    change_direction,
    expected,
):
    assert anomaly_direction_matches_change(
        _insight(direction=anomaly_direction),
        _insight(direction=change_direction),
    ) is expected


def test_anomaly_direction_match_accepts_enum_and_string_values():
    anomaly = _insight().model_copy(update={"direction": InsightDirection.HIGH})
    change = _insight().model_copy(update={"direction": "UP"})

    assert anomaly_direction_matches_change(anomaly, change) is True


def _related_anomaly(**overrides) -> Insight:
    values = {
        "id": "ANOMALY-Revenue-Product-Smart Watch-2025-06",
        "analysisId": "ANALYSIS-001",
        "type": InsightType.ANOMALY,
        "metric": "Revenue",
        "dimension": "Product",
        "segment": "Smart Watch",
        "periodGranularity": PeriodGranularity.MONTH,
        "period": {"current": "2025-06"},
        "direction": InsightDirection.HIGH,
    }
    values.update(overrides)
    return Insight(**values)


def test_smart_watch_anomaly_is_related_to_revenue_change():
    assert is_related_anomaly(
        _related_anomaly(),
        _company_change(),
    ) is True


@pytest.mark.parametrize(
    ("source", "target"),
    [
        (
            _related_anomaly(id="SHARED-ID"),
            _company_change(id="SHARED-ID"),
        ),
        (
            _related_anomaly(),
            _company_change(analysisId="ANALYSIS-002"),
        ),
        (
            _related_anomaly(type=InsightType.CHANGE),
            _company_change(),
        ),
        (
            _related_anomaly(),
            _company_change(type=InsightType.TREND),
        ),
        (
            _related_anomaly(metric="Orders"),
            _company_change(),
        ),
        (
            _related_anomaly(dimension=None),
            _company_change(),
        ),
        (
            _related_anomaly(segment=None),
            _company_change(),
        ),
        (
            _related_anomaly(),
            _company_change(dimension="Region"),
        ),
        (
            _related_anomaly(),
            _company_change(segment="Marmara"),
        ),
        (
            _related_anomaly(period={"current": "2025-07"}),
            _company_change(),
        ),
        (
            _related_anomaly(
                periodGranularity=PeriodGranularity.QUARTER,
            ),
            _company_change(),
        ),
        (
            _related_anomaly(direction=InsightDirection.HIGH),
            _company_change(direction=InsightDirection.DOWN),
        ),
        (
            _related_anomaly(direction=InsightDirection.LOW),
            _company_change(direction=InsightDirection.UP),
        ),
        (
            _company_change(),
            _related_anomaly(),
        ),
    ],
    ids=[
        "same-insight-id",
        "different-analysis",
        "source-not-anomaly",
        "target-not-change",
        "different-metric",
        "source-dimension-missing",
        "source-segment-missing",
        "target-has-dimension",
        "target-has-segment",
        "different-current-period",
        "different-granularity",
        "high-with-down",
        "low-with-up",
        "reversed-roles",
    ],
)
def test_related_anomaly_rejects_non_matches(source, target):
    assert is_related_anomaly(source, target) is False


def test_builds_smart_watch_related_anomaly_relationship():
    source = _related_anomaly(confidence=0.8)
    target = _company_change(confidence=0.9)

    relationship = build_related_anomaly_relationship(source, target)

    assert relationship is not None
    assert relationship.type == "RELATED_ANOMALY"
    assert relationship.source_insight_id == source.id
    assert relationship.target_insight_id == target.id
    assert relationship.analysis_id == "ANALYSIS-001"
    assert relationship.id == f"RELATED_ANOMALY-{source.id}-{target.id}"
    assert relationship.strength == 1.0
    assert relationship.strength_breakdown == {
        "temporalCompatibility": 1.0,
        "metricCompatibility": 1.0,
        "directionalCompatibility": 1.0,
        "structuralCompatibility": 1.0,
    }
    assert 0.0 <= relationship.confidence <= 1.0
    assert relationship.confidence == pytest.approx(0.9)
    assert relationship.confidence_breakdown == {
        "sourceInsightConfidence": 0.8,
        "targetInsightConfidence": 0.9,
        "semanticCompatibility": 1.0,
    }
    assert relationship.reasons
    assert relationship.metadata == {
        "metric": "Revenue",
        "dimension": "Product",
        "segment": "Smart Watch",
        "anomalyDirection": "HIGH",
        "changeDirection": "UP",
        "currentPeriod": "2025-06",
    }


def test_build_related_anomaly_returns_none_for_non_match():
    target = _company_change(direction=InsightDirection.DOWN)

    assert build_related_anomaly_relationship(
        _related_anomaly(),
        target,
    ) is None


def test_related_anomaly_relationship_has_no_causal_wording():
    relationship = build_related_anomaly_relationship(
        _related_anomaly(),
        _company_change(),
    )

    assert relationship is not None
    serialized_evidence = str(
        {
            "reasons": relationship.reasons,
            "metadata": relationship.metadata,
        }
    ).upper()
    prohibited_terms = {
        "CAUSED",
        "CAUSED BY",
        "DROVE",
        "DRIVEN BY",
        "LED TO",
        "RESULTED IN",
        "EXPLAINS",
        "RESPONSIBLE FOR",
        "BECAUSE OF",
        "DUE TO",
        "CONTRIBUTED TO",
    }

    assert all(term not in serialized_evidence for term in prohibited_terms)


def test_build_related_anomaly_does_not_mutate_insights():
    source = _related_anomaly(confidence=0.8)
    target = _company_change(confidence=0.9)
    source_before = source.model_dump()
    target_before = target.model_dump()

    build_related_anomaly_relationship(source, target)

    assert source.model_dump() == source_before
    assert target.model_dump() == target_before
