using Microsoft.EntityFrameworkCore;

namespace DataStoryBuilder.Infrastructure.Persistence;

public sealed class AnalysisHistoryPersistence(
    DataStoryBuilderDbContext dbContext)
{
    public async Task<IReadOnlyList<AnalysisHistorySummary>> GetAsync(
        CancellationToken cancellationToken = default)
    {
        var rows = await dbContext.Analyses
            .AsNoTracking()
            .OrderByDescending(analysis => analysis.CreatedAt)
            .Select(analysis => new
            {
                analysis.Id,
                analysis.FileName,
                analysis.FileType,
                analysis.Status,
                analysis.CreatedAt,
                analysis.CompletedAt,
                analysis.RowCount,
                analysis.ColumnCount,
                analysis.DataQualityScore,
                analysis.AnalysisVersion,
                InsightCount = dbContext.Insights.Count(
                    insight => insight.AnalysisId == analysis.Id)
            })
            .ToListAsync(cancellationToken);

        return rows
            .Select(row => new AnalysisHistorySummary(
                row.Id,
                row.FileName,
                row.FileType,
                row.Status.ToString(),
                row.CreatedAt,
                row.CompletedAt,
                row.RowCount,
                row.ColumnCount,
                row.DataQualityScore,
                row.AnalysisVersion,
                row.InsightCount))
            .ToList();
    }
}

public sealed record AnalysisHistorySummary(
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
    int InsightCount);
