namespace DataStoryBuilder.Domain.Entities;

public class Analysis
{
    public Guid Id { get; set; }
    public string FileName { get; set; } = string.Empty;
    public string FileType { get; set; } = string.Empty;
    public AnalysisStatus Status { get; set; } = AnalysisStatus.Created;
    public DateTimeOffset CreatedAt { get; set; } = DateTimeOffset.UtcNow;
    public DateTimeOffset? CompletedAt { get; set; }
    public int RowCount { get; set; }
    public int ColumnCount { get; set; }
    public double? DataQualityScore { get; set; }
    public string AnalysisVersion { get; set; } = string.Empty;
    public string? FailureReason { get; set; }
}
