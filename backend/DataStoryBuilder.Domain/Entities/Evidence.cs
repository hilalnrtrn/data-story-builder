namespace DataStoryBuilder.Domain.Entities;

public class Evidence
{
    public Guid AnalysisId { get; set; }
    public string InsightId { get; set; } = string.Empty;
    public int Ordinal { get; set; }
    public string Code { get; set; } = string.Empty;
    public string Label { get; set; } = string.Empty;
    public string ValueJson { get; set; } = "null";
    public string? Unit { get; set; }
}
