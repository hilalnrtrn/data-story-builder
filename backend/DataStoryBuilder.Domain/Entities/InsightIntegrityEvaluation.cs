namespace DataStoryBuilder.Domain.Entities;

public class InsightIntegrityEvaluation
{
    public Guid AnalysisId { get; set; }
    public string InsightId { get; set; } = string.Empty;
    public string Status { get; set; } = string.Empty;
    public double? IntegrityScore { get; set; }
    public bool StoryEligible { get; set; }
    public bool RequiresQualification { get; set; }
    public string CounterEvidenceJson { get; set; } = "[]";
    public string ContradictionsJson { get; set; } = "[]";
    public string? OutlierCheckJson { get; set; }
    public string? OneOffCheckJson { get; set; }
    public string ConsistencyChecksJson { get; set; } = "[]";
    public string IntegrityBreakdownJson { get; set; } = "{}";
    public string ReasonsJson { get; set; } = "[]";
}
