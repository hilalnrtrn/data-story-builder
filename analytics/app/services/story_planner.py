from app.models.business_relevance import PriorityLevel, RankedInsight
from app.models.causality import CausalityEvaluation, ClaimType
from app.models.context_summary import KnownUnknownContextSummary
from app.models.insight import Insight
from app.models.insight_cluster import InsightCluster
from app.models.insight_integrity import (
    InsightIntegrityEvaluation,
    IntegrityRiskLevel,
    IntegrityStatus,
)
from app.models.missing_context import (
    MissingContextEvaluation,
    MissingContextItem,
)
from app.models.relationship import Relationship, RelationshipType
from app.models.story_plan import (
    StoryCausalityConstraint,
    StoryMissingContextItem,
    StoryPlanItem,
    StoryRole,
    StorySection,
    StorySectionType,
    StructuredStoryPlan,
)
from app.config.story_planner_config import load_story_planner_config


PRIORITY_ORDER = {
    PriorityLevel.CRITICAL.value: 0,
    PriorityLevel.HIGH.value: 1,
    PriorityLevel.MEDIUM.value: 2,
    PriorityLevel.LOW.value: 3,
}


def build_integrity_lookup(
    integrity_evaluations: list[InsightIntegrityEvaluation],
) -> dict[str, InsightIntegrityEvaluation]:
    lookup: dict[str, InsightIntegrityEvaluation] = {}

    for evaluation in integrity_evaluations:
        if evaluation.insight_id in lookup:
            raise ValueError(
                "Duplicate Insight Integrity insightId: "
                f"{evaluation.insight_id}"
            )

        lookup[evaluation.insight_id] = evaluation

    return lookup


def build_ranked_insight_lookup(
    ranked_insights: list[RankedInsight],
) -> dict[str, RankedInsight]:
    lookup: dict[str, RankedInsight] = {}

    for ranked_insight in ranked_insights:
        if ranked_insight.insight_id in lookup:
            raise ValueError(
                "Duplicate Ranked Insight insightId: "
                f"{ranked_insight.insight_id}"
            )

        lookup[ranked_insight.insight_id] = ranked_insight

    return lookup


def build_cluster_lookup(
    clusters: list[InsightCluster],
) -> dict[str, InsightCluster]:
    lookup: dict[str, InsightCluster] = {}

    for cluster in clusters:
        if cluster.anchor_insight_id in lookup:
            raise ValueError(
                "Duplicate Insight Cluster anchorInsightId: "
                f"{cluster.anchor_insight_id}"
            )

        lookup[cluster.anchor_insight_id] = cluster

    return lookup


def build_relationship_lookup(
    relationships: list[Relationship],
) -> dict[str, Relationship]:
    lookup: dict[str, Relationship] = {}

    for relationship in relationships:
        if relationship.id in lookup:
            raise ValueError(
                f"Duplicate Relationship id: {relationship.id}"
            )

        lookup[relationship.id] = relationship

    return lookup


def is_broad_scope_insight(insight: Insight) -> bool:
    return insight.dimension is None and insight.segment is None


def is_story_eligible(
    insight: Insight,
    integrity_lookup: dict[str, InsightIntegrityEvaluation],
) -> bool:
    evaluation = integrity_lookup.get(insight.id)
    return evaluation is not None and evaluation.story_eligible


def select_story_candidates(
    insights: list[Insight],
    ranked_insights: list[RankedInsight],
    integrity_evaluations: list[InsightIntegrityEvaluation],
) -> list[Insight]:
    integrity_lookup = build_integrity_lookup(integrity_evaluations)
    ranked_lookup = build_ranked_insight_lookup(ranked_insights)

    candidates = [
        (insight, ranked_lookup[insight.id])
        for insight in insights
        if is_story_eligible(insight, integrity_lookup)
        and insight.id in ranked_lookup
    ]

    candidates.sort(
        key=lambda candidate: (
            PRIORITY_ORDER[candidate[1].priority.priority_level],
            -candidate[1].priority.priority_score,
            candidate[1].rank,
            candidate[0].id,
        )
    )

    return [insight for insight, _ in candidates]


def select_main_outcome(
    candidates: list[Insight],
    ranked_insights: list[RankedInsight],
    clusters: list[InsightCluster],
) -> Insight:
    if not candidates:
        raise ValueError("No story-eligible candidates are available")

    build_ranked_insight_lookup(ranked_insights)
    cluster_lookup = build_cluster_lookup(clusters)

    preference_tiers = (
        lambda insight: (
            insight.id in cluster_lookup
            and is_broad_scope_insight(insight)
        ),
        is_broad_scope_insight,
        lambda insight: insight.id in cluster_lookup,
        lambda insight: True,
    )

    for matches_tier in preference_tiers:
        for candidate in candidates:
            if matches_tier(candidate):
                return candidate

    raise ValueError("No story-eligible candidates are available")


def select_contributors(
    main_outcome: Insight,
    candidates: list[Insight],
    relationships: list[Relationship],
    clusters: list[InsightCluster],
    ranked_insights: list[RankedInsight],
    max_contributors: int = 2,
    config: dict | None = None,
) -> list[tuple[Insight, Relationship]]:
    if max_contributors < 0:
        raise ValueError("max_contributors must be greater than or equal to 0")

    if max_contributors == 0:
        return []

    ranked_lookup = build_ranked_insight_lookup(ranked_insights)
    relationship_lookup = build_relationship_lookup(relationships)
    cluster = build_cluster_lookup(clusters).get(main_outcome.id)
    if cluster is None:
        return []

    candidate_lookup = {candidate.id: candidate for candidate in candidates}
    member_ids = set(cluster.member_insight_ids)
    effective_config = (
        config if config is not None else load_story_planner_config()
    )
    dimension_priority = _build_dimension_priority(effective_config)
    contributors: list[tuple[Insight, Relationship, RankedInsight]] = []

    for relationship in relationship_lookup.values():
        candidate = candidate_lookup.get(relationship.source_insight_id)
        ranked = ranked_lookup.get(relationship.source_insight_id)
        if (
            candidate is not None
            and ranked is not None
            and candidate.id in member_ids
            and relationship.target_insight_id == main_outcome.id
            and relationship.type == RelationshipType.CONTRIBUTES_TO
        ):
            contributors.append((candidate, relationship, ranked))

    contributors.sort(
        key=lambda contributor: (
            _contributor_semantic_preference(
                main_outcome,
                contributor[0],
            ),
            _contributor_dimension_preference(
                contributor[0],
                dimension_priority,
            ),
            PRIORITY_ORDER[contributor[2].priority.priority_level],
            -contributor[2].priority.priority_score,
            -contributor[1].strength,
            -contributor[1].confidence,
            contributor[2].rank,
            contributor[0].id,
        )
    )

    return [
        (insight, relationship)
        for insight, relationship, _ in contributors[:max_contributors]
    ]


def _build_dimension_priority(config: dict) -> dict[str, int]:
    configured_dimensions = config.get(
        "primaryContributorDimensionPriority",
        [],
    )
    priority: dict[str, int] = {}
    for index, dimension in enumerate(configured_dimensions):
        normalized = str(dimension).strip().casefold()
        if normalized not in priority:
            priority[normalized] = index
    return priority


def _contributor_dimension_preference(
    contributor: Insight,
    dimension_priority: dict[str, int],
) -> int:
    # Narrative/business policy only; analytical values and scores are unchanged.
    if contributor.dimension is None:
        return len(dimension_priority)
    return dimension_priority.get(
        contributor.dimension.strip().casefold(),
        len(dimension_priority),
    )


def _contributor_semantic_preference(
    main_outcome: Insight,
    contributor: Insight,
) -> int:
    contributor_role = contributor.values.get("contributorRole")
    if main_outcome.direction == "UP":
        if contributor_role in {
            "PRIMARY_POSITIVE_CONTRIBUTOR",
            "POSITIVE_CONTRIBUTOR",
        }:
            return 0
        if contributor_role == "NEGATIVE_OFFSET":
            return 2
    elif main_outcome.direction == "DOWN":
        if contributor_role in {
            "PRIMARY_NEGATIVE_CONTRIBUTOR",
            "NEGATIVE_CONTRIBUTOR",
        }:
            return 0
        if contributor_role == "POSITIVE_OFFSET":
            return 2

    return 1


def _ranked_relationship_order(
    item: tuple[Insight, Relationship, RankedInsight],
) -> tuple[int, float, float, float, int, str]:
    insight, relationship, ranked = item
    return (
        PRIORITY_ORDER[ranked.priority.priority_level],
        -ranked.priority.priority_score,
        -relationship.strength,
        -relationship.confidence,
        ranked.rank,
        insight.id,
    )


def select_counter_signals(
    main_outcome: Insight,
    candidates: list[Insight],
    relationships: list[Relationship],
    integrity_evaluations: list[InsightIntegrityEvaluation],
    ranked_insights: list[RankedInsight],
    max_counter_signals: int = 2,
) -> list[tuple[Insight, Relationship]]:
    if max_counter_signals < 0:
        raise ValueError(
            "max_counter_signals must be greater than or equal to 0"
        )

    if max_counter_signals == 0:
        return []

    integrity = build_integrity_lookup(integrity_evaluations).get(
        main_outcome.id
    )
    if integrity is None:
        return []

    ranked_lookup = build_ranked_insight_lookup(ranked_insights)
    relationship_lookup = build_relationship_lookup(relationships)
    candidate_lookup = {candidate.id: candidate for candidate in candidates}
    counter_signals: list[
        tuple[Insight, Relationship, RankedInsight]
    ] = []

    for counter_evidence in integrity.counter_evidence:
        candidate = candidate_lookup.get(counter_evidence.insight_id)
        relationship = relationship_lookup.get(
            counter_evidence.relationship_id
        )
        ranked = ranked_lookup.get(counter_evidence.insight_id)
        if (
            candidate is not None
            and relationship is not None
            and ranked is not None
            and relationship.source_insight_id == candidate.id
            and relationship.target_insight_id == main_outcome.id
            and relationship.type == RelationshipType.COUNTER_SIGNAL
        ):
            counter_signals.append((candidate, relationship, ranked))

    counter_signals.sort(key=_ranked_relationship_order)
    return [
        (insight, relationship)
        for insight, relationship, _ in counter_signals[
            :max_counter_signals
        ]
    ]


def select_associated_signals(
    main_outcome: Insight,
    candidates: list[Insight],
    relationships: list[Relationship],
    ranked_insights: list[RankedInsight],
    max_associated_signals: int = 1,
) -> list[tuple[Insight, Relationship]]:
    if max_associated_signals < 0:
        raise ValueError(
            "max_associated_signals must be greater than or equal to 0"
        )

    if max_associated_signals == 0:
        return []

    ranked_lookup = build_ranked_insight_lookup(ranked_insights)
    relationship_lookup = build_relationship_lookup(relationships)
    candidate_lookup = {candidate.id: candidate for candidate in candidates}
    associated_signals: list[
        tuple[Insight, Relationship, RankedInsight]
    ] = []

    for relationship in relationship_lookup.values():
        candidate = candidate_lookup.get(relationship.source_insight_id)
        ranked = ranked_lookup.get(relationship.source_insight_id)
        if (
            candidate is not None
            and ranked is not None
            and relationship.target_insight_id == main_outcome.id
            and relationship.type == RelationshipType.CO_MOVES_WITH
        ):
            associated_signals.append((candidate, relationship, ranked))

    associated_signals.sort(key=_ranked_relationship_order)
    return [
        (insight, relationship)
        for insight, relationship, _ in associated_signals[
            :max_associated_signals
        ]
    ]


def _story_plan_item_id(role: StoryRole, insight_id: str) -> str:
    return f"{role.value.lower()}-{insight_id}"


def build_main_outcome_item(
    main_outcome: Insight,
    *,
    cluster_id: str | None = None,
    requires_qualification: bool = False,
    selection_reasons: list[str] | None = None,
) -> StoryPlanItem:
    role = StoryRole.MAIN_OUTCOME
    return StoryPlanItem(
        id=_story_plan_item_id(role, main_outcome.id),
        role=role,
        insightId=main_outcome.id,
        clusterId=cluster_id,
        requiresQualification=requires_qualification,
        selectionReasons=list(selection_reasons or []),
    )


def build_contributor_items(
    contributors: list[tuple[Insight, Relationship]],
) -> list[StoryPlanItem]:
    items: list[StoryPlanItem] = []

    for index, (insight, relationship) in enumerate(contributors):
        role = (
            StoryRole.PRIMARY_CONTRIBUTOR
            if index == 0
            else StoryRole.SECONDARY_FINDING
        )
        items.append(
            StoryPlanItem(
                id=_story_plan_item_id(role, insight.id),
                role=role,
                insightId=insight.id,
                relationshipId=relationship.id,
            )
        )

    return items


def build_counter_signal_items(
    counter_signals: list[tuple[Insight, Relationship]],
) -> list[StoryPlanItem]:
    return [
        StoryPlanItem(
            id=_story_plan_item_id(StoryRole.COUNTER_SIGNAL, insight.id),
            role=StoryRole.COUNTER_SIGNAL,
            insightId=insight.id,
            relationshipId=relationship.id,
        )
        for insight, relationship in counter_signals
    ]


def build_associated_signal_items(
    associated_signals: list[tuple[Insight, Relationship]],
) -> list[StoryPlanItem]:
    return [
        StoryPlanItem(
            id=_story_plan_item_id(
                StoryRole.ASSOCIATED_SIGNAL,
                insight.id,
            ),
            role=StoryRole.ASSOCIATED_SIGNAL,
            insightId=insight.id,
            relationshipId=relationship.id,
        )
        for insight, relationship in associated_signals
    ]


def select_risks(
    candidates: list[Insight],
    integrity_evaluations: list[InsightIntegrityEvaluation],
    ranked_insights: list[RankedInsight],
    max_risks: int = 1,
) -> list[Insight]:
    if max_risks < 0:
        raise ValueError("max_risks must be greater than or equal to 0")

    if max_risks == 0:
        return []

    integrity_lookup = build_integrity_lookup(integrity_evaluations)
    ranked_lookup = build_ranked_insight_lookup(ranked_insights)
    risks: list[
        tuple[Insight, InsightIntegrityEvaluation, RankedInsight]
    ] = []

    for candidate in candidates:
        integrity = integrity_lookup.get(candidate.id)
        ranked = ranked_lookup.get(candidate.id)
        if integrity is None or ranked is None:
            continue

        review_required = (
            integrity.status == IntegrityStatus.REVIEW_REQUIRED
        )
        high_outlier = (
            integrity.outlier_check is not None
            and integrity.outlier_check.level == IntegrityRiskLevel.HIGH
        )
        high_one_off = (
            integrity.one_off_check is not None
            and integrity.one_off_check.risk == IntegrityRiskLevel.HIGH
        )
        if review_required or high_outlier or high_one_off:
            risks.append((candidate, integrity, ranked))

    risks.sort(
        key=lambda item: (
            item[1].status != IntegrityStatus.REVIEW_REQUIRED,
            not (
                item[1].outlier_check is not None
                and item[1].outlier_check.level
                == IntegrityRiskLevel.HIGH
            ),
            not (
                item[1].one_off_check is not None
                and item[1].one_off_check.risk == IntegrityRiskLevel.HIGH
            ),
            PRIORITY_ORDER[item[2].priority.priority_level],
            -item[2].priority.priority_score,
            item[2].rank,
            item[0].id,
        )
    )

    return [insight for insight, _, _ in risks[:max_risks]]


def build_risk_items(risks: list[Insight]) -> list[StoryPlanItem]:
    return [
        StoryPlanItem(
            id=_story_plan_item_id(StoryRole.RISK, insight.id),
            role=StoryRole.RISK,
            insightId=insight.id,
        )
        for insight in risks
    ]


def apply_integrity_qualification(
    story_items: list[StoryPlanItem],
    integrity_evaluations: list[InsightIntegrityEvaluation],
) -> list[StoryPlanItem]:
    integrity_lookup = build_integrity_lookup(integrity_evaluations)

    return [
        item.model_copy(
            update={
                "requires_qualification": (
                    integrity_lookup[item.insight_id].requires_qualification
                    if item.insight_id in integrity_lookup
                    else False
                )
            }
        )
        for item in story_items
    ]


def build_causality_constraints(
    selected_relationships: list[Relationship],
    causality_evaluations: list[CausalityEvaluation],
) -> list[StoryCausalityConstraint]:
    relationship_lookup = build_relationship_lookup(
        selected_relationships
    )
    evaluation_lookup = {
        evaluation.relationship_id: evaluation
        for evaluation in causality_evaluations
    }
    constraints: list[StoryCausalityConstraint] = []

    for relationship in relationship_lookup.values():
        evaluation = evaluation_lookup.get(relationship.id)
        if evaluation is None:
            continue

        if evaluation.causality_established:
            claim_type = ClaimType.CAUSAL
        elif evaluation.association_present:
            claim_type = ClaimType.CORRELATIONAL
        else:
            claim_type = ClaimType.DESCRIPTIVE

        constraints.append(
            StoryCausalityConstraint(
                relationshipId=evaluation.relationship_id,
                sourceInsightId=evaluation.source_insight_id,
                targetInsightId=evaluation.target_insight_id,
                claimType=claim_type,
                associationPresent=evaluation.association_present,
                causalityEstablished=evaluation.causality_established,
                status=evaluation.status,
                allowedConcepts=list(evaluation.allowed_concepts),
                forbiddenConcepts=list(evaluation.forbidden_concepts),
                reasons=list(evaluation.reasons),
            )
        )

    return constraints


def select_missing_context(
    selected_insights: list[Insight],
    missing_context_evaluations: list[MissingContextEvaluation],
    max_missing_context: int = 2,
) -> list[tuple[Insight, MissingContextItem]]:
    if max_missing_context < 0:
        raise ValueError(
            "max_missing_context must be greater than or equal to 0"
        )

    if max_missing_context == 0:
        return []

    evaluation_lookup = {
        evaluation.insight_id: evaluation
        for evaluation in missing_context_evaluations
    }
    seen_fields: set[str] = set()
    selected: list[tuple[Insight, MissingContextItem]] = []

    for insight in selected_insights:
        evaluation = evaluation_lookup.get(insight.id)
        if evaluation is None:
            continue

        for item in evaluation.missing_context:
            normalized_field = item.field.strip().casefold()
            if item.is_data_quality_error or normalized_field in seen_fields:
                continue

            seen_fields.add(normalized_field)
            selected.append((insight, item))
            if len(selected) == max_missing_context:
                return selected

    return selected


def build_story_missing_context_items(
    selected_missing_context: list[tuple[Insight, MissingContextItem]],
) -> list[StoryMissingContextItem]:
    return [
        StoryMissingContextItem(
            id=_story_plan_item_id(
                StoryRole.MISSING_CONTEXT,
                f"{insight.id}-{item.field.strip().casefold()}",
            ),
            role=StoryRole.MISSING_CONTEXT,
            insightId=insight.id,
            field=item.field,
            status=item.status,
            isDataQualityError=item.is_data_quality_error,
            reason=item.reason,
        )
        for insight, item in selected_missing_context
    ]


def resolve_interpretation_limited(
    selected_insights: list[Insight],
    context_summaries: list[KnownUnknownContextSummary],
    selected_missing_context: list[tuple[Insight, MissingContextItem]],
) -> bool:
    selected_ids = {insight.id for insight in selected_insights}
    return bool(selected_missing_context) or any(
        summary.insight_id in selected_ids
        and summary.interpretation_limited
        for summary in context_summaries
    )


def _normalize_story_string(value: str | None) -> str | None:
    return value.strip().casefold() if value is not None else None


def build_insight_story_key(
    insight: Insight,
) -> tuple[
    str,
    str,
    tuple[tuple[str, str], ...],
    str | None,
    str | None,
]:
    normalized_period = tuple(
        sorted(
            (
                key.strip().casefold(),
                value.strip().casefold(),
            )
            for key, value in insight.period.items()
        )
    )
    return (
        insight.metric.strip().casefold(),
        insight.period_granularity.strip().casefold(),
        normalized_period,
        _normalize_story_string(insight.dimension),
        _normalize_story_string(insight.segment),
    )


def remove_redundant_story_items(
    story_items: list[StoryPlanItem],
    insights: list[Insight],
) -> list[StoryPlanItem]:
    insight_lookup: dict[str, Insight] = {}
    for insight in insights:
        if insight.id in insight_lookup:
            raise ValueError(f"Duplicate Insight id: {insight.id}")
        insight_lookup[insight.id] = insight

    retained: list[StoryPlanItem] = []
    seen_insight_ids: set[str] = set()
    seen_story_keys: set[
        tuple[
            str,
            str,
            tuple[tuple[str, str], ...],
            str | None,
            str | None,
        ]
    ] = set()

    for item in story_items:
        insight = insight_lookup.get(item.insight_id)
        if insight is None:
            raise ValueError(
                f"StoryPlanItem references missing Insight: {item.insight_id}"
            )

        story_key = build_insight_story_key(insight)
        if insight.id in seen_insight_ids or story_key in seen_story_keys:
            continue

        retained.append(item)
        seen_insight_ids.add(insight.id)
        seen_story_keys.add(story_key)

    return retained


def remove_redundant_missing_context(
    items: list[StoryMissingContextItem],
) -> list[StoryMissingContextItem]:
    retained: list[StoryMissingContextItem] = []
    seen_fields: set[str] = set()

    for item in items:
        normalized_field = item.field.strip().casefold()
        if normalized_field in seen_fields:
            continue

        retained.append(item)
        seen_fields.add(normalized_field)

    return retained


def apply_story_size_budget(
    contributors: list[StoryPlanItem],
    secondary_findings: list[StoryPlanItem],
    counter_signals: list[StoryPlanItem],
    associated_signals: list[StoryPlanItem],
    risks: list[StoryPlanItem],
    missing_context: list[StoryMissingContextItem],
    *,
    max_contributors: int = 2,
    max_secondary_findings: int = 1,
    max_counter_signals: int = 2,
    max_associated_signals: int = 1,
    max_risks: int = 1,
    max_missing_context: int = 2,
) -> tuple[
    list[StoryPlanItem],
    list[StoryPlanItem],
    list[StoryPlanItem],
    list[StoryPlanItem],
    list[StoryPlanItem],
    list[StoryMissingContextItem],
]:
    limits = (
        max_contributors,
        max_secondary_findings,
        max_counter_signals,
        max_associated_signals,
        max_risks,
        max_missing_context,
    )
    if any(limit < 0 for limit in limits):
        raise ValueError("Story size limits must be greater than or equal to 0")

    return (
        contributors[:max_contributors],
        secondary_findings[:max_secondary_findings],
        counter_signals[:max_counter_signals],
        associated_signals[:max_associated_signals],
        risks[:max_risks],
        missing_context[:max_missing_context],
    )


def build_story_outline(
    main_outcome: StoryPlanItem,
    context: list[StoryPlanItem],
    contributors: list[StoryPlanItem],
    secondary_findings: list[StoryPlanItem],
    counter_signals: list[StoryPlanItem],
    associated_signals: list[StoryPlanItem],
    risks: list[StoryPlanItem],
    missing_context: list[StoryMissingContextItem],
) -> list[StorySection]:
    section_items = (
        (StorySectionType.CONTEXT, [item.id for item in context]),
        (StorySectionType.OUTCOME, [main_outcome.id]),
        (
            StorySectionType.CONTRIBUTION,
            [item.id for item in contributors],
        ),
        (
            StorySectionType.SECONDARY_FINDINGS,
            [item.id for item in secondary_findings],
        ),
        (
            StorySectionType.COUNTER_SIGNALS,
            [item.id for item in counter_signals],
        ),
        (
            StorySectionType.ASSOCIATED_SIGNALS,
            [item.id for item in associated_signals],
        ),
        (StorySectionType.RISKS, [item.id for item in risks]),
        (
            StorySectionType.LIMITATIONS,
            [item.id for item in missing_context],
        ),
    )

    return [
        StorySection(order=order, type=section_type, itemIds=item_ids)
        for order, (section_type, item_ids) in enumerate(
            (
                (section_type, item_ids)
                for section_type, item_ids in section_items
                if item_ids
            ),
            start=1,
        )
    ]


def bind_story_item_evidence(
    story_items: list[StoryPlanItem],
    insights: list[Insight],
) -> list[StoryPlanItem]:
    insight_lookup: dict[str, Insight] = {}
    for insight in insights:
        if insight.id in insight_lookup:
            raise ValueError(f"Duplicate Insight id: {insight.id}")
        insight_lookup[insight.id] = insight

    enriched: list[StoryPlanItem] = []
    for item in story_items:
        insight = insight_lookup.get(item.insight_id)
        if insight is None:
            raise ValueError(
                f"StoryPlanItem references missing Insight: {item.insight_id}"
            )

        evidence_codes: list[str] = []
        seen_codes: set[str] = set()
        for evidence in insight.evidence:
            if evidence.code not in seen_codes:
                evidence_codes.append(evidence.code)
                seen_codes.add(evidence.code)

        enriched.append(
            item.model_copy(update={"evidence_codes": evidence_codes})
        )

    return enriched


def build_story_plan(
    insights: list[Insight],
    relationships: list[Relationship],
    clusters: list[InsightCluster],
    ranked_insights: list[RankedInsight],
    integrity_evaluations: list[InsightIntegrityEvaluation],
    causality_evaluations: list[CausalityEvaluation],
    missing_context_evaluations: list[MissingContextEvaluation],
    context_summaries: list[KnownUnknownContextSummary],
) -> StructuredStoryPlan:
    candidates = select_story_candidates(
        insights,
        ranked_insights,
        integrity_evaluations,
    )
    if not candidates:
        raise ValueError("No story-eligible ranked candidates are available")

    main_outcome = select_main_outcome(
        candidates,
        ranked_insights,
        clusters,
    )
    contributors = select_contributors(
        main_outcome,
        candidates,
        relationships,
        clusters,
        ranked_insights,
    )
    counter_signals = select_counter_signals(
        main_outcome,
        candidates,
        relationships,
        integrity_evaluations,
        ranked_insights,
    )
    associated_signals = select_associated_signals(
        main_outcome,
        candidates,
        relationships,
        ranked_insights,
    )
    risks = select_risks(
        candidates,
        integrity_evaluations,
        ranked_insights,
    )

    cluster = build_cluster_lookup(clusters).get(main_outcome.id)
    main_item = build_main_outcome_item(
        main_outcome,
        cluster_id=cluster.id if cluster is not None else None,
    )
    contributor_items = build_contributor_items(contributors)
    primary_contributors = [
        item
        for item in contributor_items
        if item.role == StoryRole.PRIMARY_CONTRIBUTOR
    ]
    secondary_findings = [
        item
        for item in contributor_items
        if item.role == StoryRole.SECONDARY_FINDING
    ]
    counter_items = build_counter_signal_items(counter_signals)
    associated_items = build_associated_signal_items(associated_signals)
    risk_items = build_risk_items(risks)

    ordered_items = [
        main_item,
        *primary_contributors,
        *counter_items,
        *associated_items,
        *risk_items,
        *secondary_findings,
    ]
    qualified_items = apply_integrity_qualification(
        ordered_items,
        integrity_evaluations,
    )
    evidenced_items = bind_story_item_evidence(
        qualified_items,
        insights,
    )
    final_items = remove_redundant_story_items(
        evidenced_items,
        insights,
    )

    final_main = next(
        item for item in final_items if item.role == StoryRole.MAIN_OUTCOME
    )
    final_contributors = [
        item
        for item in final_items
        if item.role == StoryRole.PRIMARY_CONTRIBUTOR
    ]
    final_secondary = [
        item
        for item in final_items
        if item.role == StoryRole.SECONDARY_FINDING
    ]
    final_counter = [
        item
        for item in final_items
        if item.role == StoryRole.COUNTER_SIGNAL
    ]
    final_associated = [
        item
        for item in final_items
        if item.role == StoryRole.ASSOCIATED_SIGNAL
    ]
    final_risks = [
        item for item in final_items if item.role == StoryRole.RISK
    ]

    insight_lookup = {insight.id: insight for insight in insights}
    selected_insights = [
        insight_lookup[item.insight_id] for item in final_items
    ]
    selected_context = select_missing_context(
        selected_insights,
        missing_context_evaluations,
    )
    missing_context_items = remove_redundant_missing_context(
        build_story_missing_context_items(selected_context)
    )

    (
        final_contributors,
        final_secondary,
        final_counter,
        final_associated,
        final_risks,
        missing_context_items,
    ) = apply_story_size_budget(
        final_contributors,
        final_secondary,
        final_counter,
        final_associated,
        final_risks,
        missing_context_items,
    )

    budgeted_items = [
        final_main,
        *final_contributors,
        *final_counter,
        *final_associated,
        *final_risks,
        *final_secondary,
    ]
    relationship_lookup = build_relationship_lookup(relationships)
    selected_relationships: list[Relationship] = []
    seen_relationship_ids: set[str] = set()
    for item in budgeted_items:
        if (
            item.relationship_id is not None
            and item.relationship_id not in seen_relationship_ids
        ):
            selected_relationships.append(
                relationship_lookup[item.relationship_id]
            )
            seen_relationship_ids.add(item.relationship_id)

    causality_constraints = build_causality_constraints(
        selected_relationships,
        causality_evaluations,
    )
    interpretation_limited = resolve_interpretation_limited(
        [insight_lookup[item.insight_id] for item in budgeted_items],
        context_summaries,
        selected_context,
    )
    outline = build_story_outline(
        final_main,
        [],
        final_contributors,
        final_secondary,
        final_counter,
        final_associated,
        final_risks,
        missing_context_items,
    )

    return StructuredStoryPlan(
        analysisId=main_outcome.analysis_id,
        mainOutcome=final_main,
        contributors=final_contributors,
        secondaryFindings=final_secondary,
        counterSignals=final_counter,
        associatedSignals=final_associated,
        risks=final_risks,
        missingContext=missing_context_items,
        causalityConstraints=causality_constraints,
        outline=outline,
        interpretationLimited=interpretation_limited,
    )
