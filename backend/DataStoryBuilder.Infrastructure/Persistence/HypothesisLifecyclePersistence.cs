using System.Text.Json;
using DataStoryBuilder.Application.Hypotheses;
using DataStoryBuilder.Domain.Entities;
using Microsoft.EntityFrameworkCore;

namespace DataStoryBuilder.Infrastructure.Persistence;

public enum HypothesisStatusUpdateOutcome
{
    Updated,
    AnalysisNotFound,
    HypothesisNotFound,
    InvalidTransition
}

public sealed record HypothesisStatusUpdateResult(
    HypothesisStatusUpdateOutcome Outcome,
    AnalysisHypothesisDetail? Hypothesis = null);

public sealed class HypothesisLifecyclePersistence(
    DataStoryBuilderDbContext dbContext)
{
    public async Task<IReadOnlyList<AnalysisHypothesisDetail>?> GetAsync(
        Guid analysisId,
        CancellationToken cancellationToken = default)
    {
        var analysisExists = await dbContext.Analyses
            .AsNoTracking()
            .AnyAsync(item => item.Id == analysisId, cancellationToken);
        if (!analysisExists)
        {
            return null;
        }

        var hypotheses = await dbContext.Hypotheses
            .AsNoTracking()
            .Where(item => item.AnalysisId == analysisId)
            .OrderBy(item => item.Id)
            .ToListAsync(cancellationToken);
        return AnalysisDetailPersistence.ProjectHypotheses(hypotheses);
    }

    public async Task<HypothesisStatusUpdateResult> UpdateStatusAsync(
        Guid analysisId,
        string hypothesisId,
        HypothesisLifecycleStatus targetStatus,
        CancellationToken cancellationToken = default)
    {
        var analysisExists = await dbContext.Analyses
            .AsNoTracking()
            .AnyAsync(item => item.Id == analysisId, cancellationToken);
        if (!analysisExists)
        {
            return new(HypothesisStatusUpdateOutcome.AnalysisNotFound);
        }

        var hypothesis = await dbContext.Hypotheses.SingleOrDefaultAsync(
            item => item.AnalysisId == analysisId && item.Id == hypothesisId,
            cancellationToken);
        if (hypothesis is null)
        {
            return new(HypothesisStatusUpdateOutcome.HypothesisNotFound);
        }

        if (!ApplyStatusTransition(hypothesis, targetStatus))
        {
            return new(HypothesisStatusUpdateOutcome.InvalidTransition);
        }

        await dbContext.SaveChangesAsync(cancellationToken);
        var detail = AssertSingle(
            AnalysisDetailPersistence.ProjectHypotheses([hypothesis]));
        return new(HypothesisStatusUpdateOutcome.Updated, detail);
    }

    public static bool ApplyStatusTransition(
        Hypothesis hypothesis,
        HypothesisLifecycleStatus targetStatus)
    {
        ArgumentNullException.ThrowIfNull(hypothesis);
        if (!HypothesisStatusTransitions.TryParse(
                hypothesis.Status,
                out var currentStatus)
            || !HypothesisStatusTransitions.IsAllowed(
                currentStatus,
                targetStatus))
        {
            return false;
        }

        var current = HypothesisStatusTransitions.ToStorageValue(currentStatus);
        var target = HypothesisStatusTransitions.ToStorageValue(targetStatus);
        var reasons = JsonSerializer.Deserialize<List<string>>(
                hypothesis.ReasonsJson)
            ?? throw new JsonException(
                "Persisted hypothesis reasons must be a JSON array.");
        reasons.Add($"Hypothesis status changed from {current} to {target}.");

        hypothesis.Status = target;
        hypothesis.ReasonsJson = JsonSerializer.Serialize(reasons);
        return true;
    }

    private static T AssertSingle<T>(IReadOnlyList<T> values) =>
        values.Count == 1
            ? values[0]
            : throw new InvalidOperationException(
                "A single updated hypothesis was expected.");
}
