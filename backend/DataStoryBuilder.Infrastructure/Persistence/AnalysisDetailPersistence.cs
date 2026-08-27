using System.Text.Json;
using Microsoft.EntityFrameworkCore;

namespace DataStoryBuilder.Infrastructure.Persistence;

public sealed class AnalysisDetailPersistence(
    DataStoryBuilderDbContext dbContext)
{
    public async Task<AnalysisDetailResult?> GetAsync(
        Guid analysisId,
        CancellationToken cancellationToken = default)
    {
        var analysis = await dbContext.Analyses
            .AsNoTracking()
            .SingleOrDefaultAsync(
                item => item.Id == analysisId,
                cancellationToken);

        if (analysis is null)
        {
            return null;
        }

        var datasetProfile = await dbContext.DatasetProfiles
            .AsNoTracking()
            .SingleOrDefaultAsync(
                item => item.AnalysisId == analysisId,
                cancellationToken);

        var evidence = await dbContext.Evidence
            .AsNoTracking()
            .Where(item => item.AnalysisId == analysisId)
            .OrderBy(item => item.InsightId)
            .ThenBy(item => item.Ordinal)
            .ToListAsync(cancellationToken);

        var evidenceByInsightId = evidence
            .GroupBy(item => item.InsightId, StringComparer.Ordinal)
            .ToDictionary(
                group => group.Key,
                group => (IReadOnlyList<AnalysisEvidenceDetail>)group
                    .Select(item => new AnalysisEvidenceDetail(
                        item.Code,
                        item.Label,
                        ParseJson(item.ValueJson),
                        item.Unit))
                    .ToList(),
                StringComparer.Ordinal);

        var insightEntities = await dbContext.Insights
            .AsNoTracking()
            .Where(item => item.AnalysisId == analysisId)
            .OrderBy(item => item.Rank == null)
            .ThenBy(item => item.Rank)
            .ThenBy(item => item.Id)
            .ToListAsync(cancellationToken);

        var insights = insightEntities
            .Select(item => new AnalysisInsightDetail(
                item.Id,
                item.Type,
                item.Metric,
                item.Dimension,
                item.Segment,
                item.PeriodGranularity,
                item.Direction,
                item.Confidence,
                item.Importance,
                item.BusinessRelevance,
                item.ImpactDirection,
                item.PriorityScore,
                item.PriorityLevel,
                item.Rank,
                ParseJson(item.PeriodJson),
                ParseJson(item.ValuesJson),
                ParseJson(item.DetectionJson),
                ParseJson(item.ConfidenceBreakdownJson),
                ParseJson(item.ImportanceBreakdownJson),
                ParseNullableJson(item.SourceJson),
                ParseNullableJson(item.BusinessRelevanceDetailsJson),
                ParseNullableJson(item.PriorityDetailsJson),
                ParseNullableJson(item.RankingDetailsJson),
                evidenceByInsightId.GetValueOrDefault(item.Id)
                    ?? []))
            .ToList();

        var relationshipEntities = await dbContext.Relationships
            .AsNoTracking()
            .Where(item => item.AnalysisId == analysisId)
            .OrderBy(item => item.Id)
            .ToListAsync(cancellationToken);

        var relationships = relationshipEntities
            .Select(item => new AnalysisRelationshipDetail(
                item.Id,
                item.SourceInsightId,
                item.TargetInsightId,
                item.Type,
                item.Strength,
                item.Confidence,
                ParseJson(item.StrengthBreakdownJson),
                ParseJson(item.ConfidenceBreakdownJson),
                ParseJson(item.ReasonsJson),
                ParseJson(item.MetadataJson)))
            .ToList();

        var clusterEntities = await dbContext.InsightClusters
            .AsNoTracking()
            .Where(item => item.AnalysisId == analysisId)
            .OrderBy(item => item.Id)
            .ToListAsync(cancellationToken);

        var insightClusters = clusterEntities
            .Select(item => new AnalysisInsightClusterDetail(
                item.Id,
                item.AnchorInsightId,
                ParseJson(item.MemberInsightIdsJson),
                ParseJson(item.RelationshipIdsJson)))
            .ToList();

        var integrityEntities = await dbContext.InsightIntegrityEvaluations
            .AsNoTracking()
            .Where(item => item.AnalysisId == analysisId)
            .OrderBy(item => item.InsightId)
            .ToListAsync(cancellationToken);

        var insightIntegrity = integrityEntities
            .Select(item => new AnalysisInsightIntegrityDetail(
                item.InsightId,
                item.Status,
                item.IntegrityScore,
                item.StoryEligible,
                item.RequiresQualification,
                ParseJson(item.CounterEvidenceJson),
                ParseJson(item.ContradictionsJson),
                ParseNullableJson(item.OutlierCheckJson),
                ParseNullableJson(item.OneOffCheckJson),
                ParseJson(item.ConsistencyChecksJson),
                ParseJson(item.IntegrityBreakdownJson),
                ParseJson(item.ReasonsJson)))
            .ToList();

        var causalityEntities = await dbContext.CausalityEvaluations
            .AsNoTracking()
            .Where(item => item.AnalysisId == analysisId)
            .OrderBy(item => item.RelationshipId)
            .ToListAsync(cancellationToken);

        var causalityEvaluations = causalityEntities
            .Select(item => new AnalysisCausalityDetail(
                item.RelationshipId,
                item.SourceInsightId,
                item.TargetInsightId,
                item.SourceMetric,
                item.TargetMetric,
                item.Status,
                item.AssociationPresent,
                item.CausalityEstablished,
                ParseJson(item.CausalEvidenceJson),
                ParseJson(item.AllowedConceptsJson),
                ParseJson(item.ForbiddenConceptsJson),
                ParseJson(item.ReasonsJson)))
            .ToList();

        var missingContextEntities = await dbContext.MissingContextEvaluations
            .AsNoTracking()
            .Where(item => item.AnalysisId == analysisId)
            .OrderBy(item => item.InsightId)
            .ToListAsync(cancellationToken);

        var missingContextEvaluations = missingContextEntities
            .Select(item => new AnalysisMissingContextDetail(
                item.InsightId,
                item.InterpretationLimited,
                ParseJson(item.MissingContextJson),
                ParseJson(item.ReasonsJson),
                ParseJson(item.ContextSummaryJson)))
            .ToList();

        var story = await dbContext.Stories
            .AsNoTracking()
            .SingleOrDefaultAsync(
                item => item.AnalysisId == analysisId,
                cancellationToken);

        return new AnalysisDetailResult(
            analysis.Id,
            analysis.FileName,
            analysis.FileType,
            analysis.Status.ToString(),
            analysis.CreatedAt,
            analysis.CompletedAt,
            analysis.RowCount,
            analysis.ColumnCount,
            analysis.DataQualityScore,
            analysis.AnalysisVersion,
            analysis.FailureReason,
            datasetProfile is null
                ? null
                : ParseJson(datasetProfile.ProfileJson),
            datasetProfile is null
                ? null
                : ParseJson(datasetProfile.QualityJson),
            insights,
            relationships,
            insightClusters,
            insightIntegrity,
            causalityEvaluations,
            missingContextEvaluations,
            story is null ? null : ParseJson(story.StoryPlanJson),
            story is null ? null : ParseNullableJson(story.GeneratedStoryJson),
            ProjectStoryGeneration(story),
            ProjectStoryAudit(story),
            ProjectFullStoryAudit(story));
    }

    private static JsonElement ParseJson(string json)
    {
        using var document = JsonDocument.Parse(json);
        return document.RootElement.Clone();
    }

    private static JsonElement? ParseNullableJson(string? json)
    {
        return json is null ? null : ParseJson(json);
    }

    public static AnalysisStoryGenerationDetail? ProjectStoryGeneration(
        DataStoryBuilder.Domain.Entities.Story? story)
    {
        if (story is null
            || story.GenerationStatus is null
            && story.PromptVersion is null
            && story.ModelIdentifier is null
            && story.GeneratedAt is null
            && story.GenerationFailureReason is null)
        {
            return null;
        }

        return new AnalysisStoryGenerationDetail(
            story.GenerationStatus!,
            story.PromptVersion,
            story.ModelIdentifier,
            story.GeneratedAt,
            story.GenerationFailureReason);
    }

    public static JsonElement? ProjectStoryAudit(
        DataStoryBuilder.Domain.Entities.Story? story) =>
        story is null ? null : ParseNullableJson(story.StoryAuditJson);

    public static JsonElement? ProjectFullStoryAudit(
        DataStoryBuilder.Domain.Entities.Story? story) =>
        story is null ? null : ParseNullableJson(story.FullStoryAuditJson);
}

public sealed record AnalysisDetailResult(
    Guid Id,
    string FileName,
    string FileType,
    string Status,
    DateTimeOffset CreatedAt,
    DateTimeOffset? CompletedAt,
    int RowCount,
    int ColumnCount,
    double? DataQualityScore,
    string AnalysisVersion,
    string? FailureReason,
    JsonElement? Profile,
    JsonElement? Quality,
    IReadOnlyList<AnalysisInsightDetail> Insights,
    IReadOnlyList<AnalysisRelationshipDetail> Relationships,
    IReadOnlyList<AnalysisInsightClusterDetail> InsightClusters,
    IReadOnlyList<AnalysisInsightIntegrityDetail> InsightIntegrity,
    IReadOnlyList<AnalysisCausalityDetail> CausalityEvaluations,
    IReadOnlyList<AnalysisMissingContextDetail> MissingContextEvaluations,
    JsonElement? StoryPlan,
    JsonElement? GeneratedStory,
    AnalysisStoryGenerationDetail? StoryGeneration,
    JsonElement? StoryAudit,
    JsonElement? FullStoryAudit);

public sealed record AnalysisStoryGenerationDetail(
    string Status,
    string? PromptVersion,
    string? ModelIdentifier,
    DateTimeOffset? GeneratedAt,
    string? FailureReason);

public sealed record AnalysisInsightDetail(
    string Id,
    string Type,
    string Metric,
    string? Dimension,
    string? Segment,
    string? PeriodGranularity,
    string? Direction,
    double? Confidence,
    double? Importance,
    double? BusinessRelevance,
    string? ImpactDirection,
    double? PriorityScore,
    string? PriorityLevel,
    int? Rank,
    JsonElement Period,
    JsonElement Values,
    JsonElement Detection,
    JsonElement ConfidenceBreakdown,
    JsonElement ImportanceBreakdown,
    JsonElement? Source,
    JsonElement? BusinessRelevanceDetails,
    JsonElement? PriorityDetails,
    JsonElement? RankingDetails,
    IReadOnlyList<AnalysisEvidenceDetail> Evidence);

public sealed record AnalysisEvidenceDetail(
    string Code,
    string Label,
    JsonElement Value,
    string? Unit);

public sealed record AnalysisRelationshipDetail(
    string Id,
    string SourceInsightId,
    string TargetInsightId,
    string Type,
    double Strength,
    double Confidence,
    JsonElement StrengthBreakdown,
    JsonElement ConfidenceBreakdown,
    JsonElement Reasons,
    JsonElement Metadata);

public sealed record AnalysisInsightClusterDetail(
    string Id,
    string AnchorInsightId,
    JsonElement MemberInsightIds,
    JsonElement RelationshipIds);

public sealed record AnalysisInsightIntegrityDetail(
    string InsightId,
    string Status,
    double? IntegrityScore,
    bool StoryEligible,
    bool RequiresQualification,
    JsonElement CounterEvidence,
    JsonElement Contradictions,
    JsonElement? OutlierCheck,
    JsonElement? OneOffCheck,
    JsonElement ConsistencyChecks,
    JsonElement IntegrityBreakdown,
    JsonElement Reasons);

public sealed record AnalysisCausalityDetail(
    string RelationshipId,
    string SourceInsightId,
    string TargetInsightId,
    string SourceMetric,
    string TargetMetric,
    string Status,
    bool AssociationPresent,
    bool CausalityEstablished,
    JsonElement CausalEvidence,
    JsonElement AllowedConcepts,
    JsonElement ForbiddenConcepts,
    JsonElement Reasons);

public sealed record AnalysisMissingContextDetail(
    string InsightId,
    bool InterpretationLimited,
    JsonElement MissingContext,
    JsonElement Reasons,
    JsonElement ContextSummary);
