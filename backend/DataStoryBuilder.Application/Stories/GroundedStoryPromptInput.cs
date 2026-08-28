using System.Text.Json;

namespace DataStoryBuilder.Application.Stories;

public sealed record GroundedStoryPromptInput(
    string AnalysisId,
    string PlannerVersion,
    IReadOnlyList<GroundedStorySection> Sections,
    IReadOnlyList<GroundedStoryFinding> Findings,
    IReadOnlyList<GroundedCausalityConstraint> CausalityConstraints,
    IReadOnlyList<GroundedStoryLimitation> Limitations,
    bool InterpretationLimited = false,
    string OutputLanguage = StoryGenerationLanguage.Default);

public sealed record GroundedStorySection(
    int Order,
    string Type,
    IReadOnlyList<string> SourceItemIds);

public sealed record GroundedStoryFinding(
    string SourceItemId,
    string InsightId,
    string Role,
    string InsightType,
    string Metric,
    string? Dimension,
    string? Segment,
    JsonElement Period,
    string Direction,
    JsonElement Values,
    IReadOnlyList<GroundedStoryEvidence> Evidence,
    bool RequiresQualification,
    IReadOnlyList<string> QualificationReasons,
    double? Confidence = null);

public sealed record GroundedStoryEvidence(
    string Code,
    string Label,
    JsonElement Value,
    string? Unit);

public sealed record GroundedCausalityConstraint(
    string RelationshipId,
    string SourceInsightId,
    string TargetInsightId,
    string ClaimType,
    bool AssociationPresent,
    bool CausalityEstablished,
    string Status,
    IReadOnlyList<string> AllowedConcepts,
    IReadOnlyList<string> ForbiddenConcepts,
    IReadOnlyList<string> Reasons);

public sealed record GroundedStoryLimitation(
    string SourceItemId,
    string InsightId,
    string Field,
    string Status,
    string Reason);
