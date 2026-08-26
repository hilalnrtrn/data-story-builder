namespace DataStoryBuilder.Domain.Entities;

public class Relationship
{
    public string Id { get; set; } = string.Empty;
    public Guid AnalysisId { get; set; }
    public string SourceInsightId { get; set; } = string.Empty;
    public string TargetInsightId { get; set; } = string.Empty;
    public string Type { get; set; } = string.Empty;
    public double Strength { get; set; }
    public double Confidence { get; set; }
    public string StrengthBreakdownJson { get; set; } = "{}";
    public string ConfidenceBreakdownJson { get; set; } = "{}";
    public string ReasonsJson { get; set; } = "[]";
    public string MetadataJson { get; set; } = "{}";
}
