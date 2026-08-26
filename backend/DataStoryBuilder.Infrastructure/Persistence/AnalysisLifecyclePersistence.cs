using DataStoryBuilder.Domain.Entities;
using Microsoft.EntityFrameworkCore;

namespace DataStoryBuilder.Infrastructure.Persistence;

public sealed class AnalysisLifecyclePersistence(
    DataStoryBuilderDbContext dbContext)
{
    private const int MaximumFailureReasonLength = 2000;

    public async Task CreateProcessingAsync(
        Guid analysisId,
        string fileName,
        string fileType,
        CancellationToken cancellationToken = default)
    {
        dbContext.Analyses.Add(new Analysis
        {
            Id = analysisId,
            FileName = fileName,
            FileType = fileType,
            Status = AnalysisStatus.Processing,
            CreatedAt = DateTimeOffset.UtcNow,
            CompletedAt = null,
            RowCount = 0,
            ColumnCount = 0,
            DataQualityScore = null,
            AnalysisVersion = "1.0",
            FailureReason = null
        });

        await dbContext.SaveChangesAsync(cancellationToken);
    }

    public async Task MarkCompletedAsync(
        Guid analysisId,
        CancellationToken cancellationToken = default)
    {
        var analysis = await LoadAnalysisAsync(
            analysisId,
            cancellationToken);

        analysis.Status = AnalysisStatus.Completed;
        analysis.CompletedAt = DateTimeOffset.UtcNow;
        analysis.FailureReason = null;

        await dbContext.SaveChangesAsync(cancellationToken);
    }

    public async Task MarkFailedAsync(
        Guid analysisId,
        string failureReason,
        CancellationToken cancellationToken = default)
    {
        var analysis = await LoadAnalysisAsync(
            analysisId,
            cancellationToken);

        analysis.Status = AnalysisStatus.Failed;
        analysis.CompletedAt = DateTimeOffset.UtcNow;
        analysis.FailureReason = failureReason.Length <= MaximumFailureReasonLength
            ? failureReason
            : failureReason[..MaximumFailureReasonLength];

        await dbContext.SaveChangesAsync(cancellationToken);
    }

    private async Task<Analysis> LoadAnalysisAsync(
        Guid analysisId,
        CancellationToken cancellationToken)
    {
        return await dbContext.Analyses.SingleAsync(
            analysis => analysis.Id == analysisId,
            cancellationToken);
    }
}
