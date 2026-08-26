import pytest

from app.models.business_relevance import (
    BusinessImpactDirection,
    BusinessRelevanceEvaluation,
    PriorityEvaluation,
    PriorityLevel,
    RankedInsight,
)
from app.models.causality import CausalityEvaluation, CausalityStatus
from app.models.context_summary import KnownUnknownContextSummary
from app.models.insight import (
    Evidence,
    Insight,
    InsightDirection,
    InsightType,
    PeriodGranularity,
)
from app.models.insight_cluster import InsightCluster
from app.models.insight_integrity import (
    CounterEvidenceItem,
    InsightIntegrityEvaluation,
    IntegrityStatus,
)
from app.models.missing_context import (
    MissingContextEvaluation,
    MissingContextItem,
    MissingContextStatus,
)
from app.models.relationship import Relationship, RelationshipType
from app.models.story_plan import StructuredStoryPlan, StoryPlanItem, StoryRole
from app.services.story_planner import (
    bind_story_item_evidence,
    build_story_plan,
)


def _insight(
    insight_id: str,
    metric: str,
    *,
    narrow: bool = True,
    evidence: list[Evidence] | None = None,
) -> Insight:
    return Insight(
        id=insight_id,
        analysisId="ANALYSIS-001",
        type=InsightType.CHANGE,
        metric=metric,
        dimension="Region" if narrow else None,
        segment=insight_id if narrow else None,
        periodGranularity=PeriodGranularity.MONTH,
        period={"previous": "2025-05", "current": "2025-06"},
        direction=InsightDirection.UP,
        evidence=evidence or [],
    )


def _ranked(insight_id: str, rank: int) -> RankedInsight:
    return RankedInsight(
        rank=rank,
        insightId=insight_id,
        priority=PriorityEvaluation(
            insightId=insight_id,
            priorityScore=1.0 - rank / 100,
            priorityLevel=PriorityLevel.HIGH,
        ),
        businessRelevance=BusinessRelevanceEvaluation(
            insightId=insight_id,
            businessRelevance=0.8,
            impactDirection=BusinessImpactDirection.POSITIVE,
        ),
    )


def _relationship(
    relationship_id: str,
    source: Insight,
    target: Insight,
    relationship_type: RelationshipType,
    *,
    strength: float = 0.8,
) -> Relationship:
    return Relationship(
        id=relationship_id,
        analysisId="ANALYSIS-001",
        sourceInsightId=source.id,
        targetInsightId=target.id,
        type=relationship_type,
        strength=strength,
        confidence=0.8,
    )


def _scenario():
    main = _insight(
        "MAIN",
        "Revenue",
        narrow=False,
        evidence=[
            Evidence(code="CURRENT_VALUE", label="Current", value=120),
            Evidence(code="CHANGE", label="Change", value=20),
            Evidence(code="CURRENT_VALUE", label="Duplicate", value=120),
        ],
    )
    contributor = _insight("CONTRIBUTOR", "RegionalRevenue")
    redundant = _insight("REDUNDANT", " Revenue ", narrow=False)
    counter = _insight("COUNTER", "Customers")
    associated = _insight("ASSOCIATED", "MarketingSpend")
    omitted_associated = _insight("OMITTED-ASSOCIATED", "Orders")
    risk = _insight("RISK", "StockLevel")
    unselected = _insight("UNSELECTED", "Returns")
    insights = [
        main,
        contributor,
        redundant,
        counter,
        associated,
        omitted_associated,
        risk,
        unselected,
    ]
    relationships = [
        _relationship("REL-CONTRIBUTOR", contributor, main, RelationshipType.CONTRIBUTES_TO),
        _relationship("REL-REDUNDANT", redundant, main, RelationshipType.CONTRIBUTES_TO),
        _relationship("REL-COUNTER", counter, main, RelationshipType.COUNTER_SIGNAL),
        _relationship("REL-ASSOCIATED", associated, main, RelationshipType.CO_MOVES_WITH, strength=0.9),
        _relationship("REL-OMITTED", omitted_associated, main, RelationshipType.CO_MOVES_WITH, strength=0.7),
    ]
    counter_evidence = CounterEvidenceItem(
        insightId=counter.id,
        relationshipId="REL-COUNTER",
        metric=counter.metric,
        direction=counter.direction,
    )
    integrity = [
        InsightIntegrityEvaluation(
            insightId=insight.id,
            status=(IntegrityStatus.REVIEW_REQUIRED if insight is risk else IntegrityStatus.PASS),
            counterEvidence=[counter_evidence] if insight is main else [],
            storyEligible=insight is not unselected,
            requiresQualification=insight is main,
        )
        for insight in insights
    ]
    rankings = [_ranked(insight.id, index) for index, insight in enumerate(insights, 1)]
    cluster = InsightCluster(
        id="CLUSTER-MAIN",
        analysisId="ANALYSIS-001",
        anchorInsightId=main.id,
        memberInsightIds=[contributor.id, redundant.id],
        relationshipIds=["REL-CONTRIBUTOR", "REL-REDUNDANT"],
    )
    evaluations = [
        CausalityEvaluation(
            relationshipId=relationship.id,
            sourceInsightId=relationship.source_insight_id,
            targetInsightId=relationship.target_insight_id,
            sourceMetric=relationship.source_insight_id,
            targetMetric=relationship.target_insight_id,
            associationPresent=True,
            causalityEstablished=False,
            status=CausalityStatus.CAUSALITY_NOT_ESTABLISHED,
        )
        for relationship in relationships[-2:]
    ]
    missing_context = [
        MissingContextEvaluation(
            insightId=main.id,
            missingContext=[
                MissingContextItem(
                    field="UnitPrice",
                    status=MissingContextStatus.NOT_AVAILABLE,
                    isDataQualityError=False,
                    reason="Unit price is unavailable.",
                ),
                MissingContextItem(
                    field="InvalidRows",
                    status=MissingContextStatus.NOT_AVAILABLE,
                    isDataQualityError=True,
                    reason="This is a data-quality issue.",
                ),
            ],
            interpretationLimited=True,
        ),
        MissingContextEvaluation(
            insightId=unselected.id,
            missingContext=[
                MissingContextItem(
                    field="UnselectedContext",
                    status=MissingContextStatus.NOT_AVAILABLE,
                    isDataQualityError=False,
                    reason="Not selected.",
                )
            ],
            interpretationLimited=True,
        ),
    ]
    summaries = [
        KnownUnknownContextSummary(
            insightId=main.id,
            interpretationLimited=True,
        )
    ]
    return (
        insights,
        relationships,
        [cluster],
        rankings,
        integrity,
        evaluations,
        missing_context,
        summaries,
    )


def test_valid_inputs_build_complete_deterministic_structured_plan():
    inputs = _scenario()

    first = build_story_plan(*inputs)
    second = build_story_plan(*inputs)

    assert isinstance(first, StructuredStoryPlan)
    assert first.model_dump() == second.model_dump()
    assert first.main_outcome.role == StoryRole.MAIN_OUTCOME
    assert first.main_outcome.requires_qualification is True
    assert first.main_outcome.evidence_codes == ["CURRENT_VALUE", "CHANGE"]
    assert [item.insight_id for item in first.contributors] == ["CONTRIBUTOR"]
    assert first.secondary_findings == []
    assert [item.insight_id for item in first.counter_signals] == ["COUNTER"]
    assert [item.insight_id for item in first.associated_signals] == ["ASSOCIATED"]
    assert [item.insight_id for item in first.risks] == ["RISK"]
    assert [item.field for item in first.missing_context] == ["UnitPrice"]
    assert first.interpretation_limited is True


def test_constraints_and_outline_reference_only_surviving_items():
    plan = build_story_plan(*_scenario())

    assert [item.relationship_id for item in plan.causality_constraints] == [
        "REL-ASSOCIATED"
    ]
    outlined_ids = {
        item_id for section in plan.outline for item_id in section.item_ids
    }
    final_ids = {
        plan.main_outcome.id,
        *(item.id for item in plan.contributors),
        *(item.id for item in plan.secondary_findings),
        *(item.id for item in plan.counter_signals),
        *(item.id for item in plan.associated_signals),
        *(item.id for item in plan.risks),
        *(item.id for item in plan.missing_context),
    }
    assert outlined_ids == final_ids
    assert [section.order for section in plan.outline] == list(
        range(1, len(plan.outline) + 1)
    )


def test_plan_respects_budgets_and_contains_no_generated_story_fields():
    plan = build_story_plan(*_scenario())

    assert len(plan.contributors) <= 2
    assert len(plan.secondary_findings) <= 1
    assert len(plan.counter_signals) <= 2
    assert len(plan.associated_signals) <= 1
    assert len(plan.risks) <= 1
    assert len(plan.missing_context) <= 2
    assert not (
        {"narrative", "textFact", "generatedStory"}
        & set(plan.model_dump())
    )


def test_no_eligible_ranked_candidates_raises_value_error():
    with pytest.raises(ValueError, match="No story-eligible ranked candidates"):
        build_story_plan([], [], [], [], [], [], [], [])


def test_evidence_binding_rejects_missing_reference_without_mutation():
    item = StoryPlanItem(id="ITEM", role=StoryRole.RISK, insightId="MISSING")
    snapshot = item.model_dump()

    with pytest.raises(ValueError, match="missing Insight"):
        bind_story_item_evidence([item], [])

    assert item.model_dump() == snapshot


def test_orchestration_does_not_mutate_inputs():
    inputs = _scenario()
    snapshots = tuple(
        [item.model_dump() for item in collection]
        for collection in inputs
    )

    build_story_plan(*inputs)

    assert tuple(
        [item.model_dump() for item in collection]
        for collection in inputs
    ) == snapshots
