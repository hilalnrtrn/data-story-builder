namespace DataStoryBuilder.Domain.Entities;

public class Hypothesis
{
    public string Id { get; set; } = string.Empty;
    public Guid AnalysisId { get; set; }
    public string Statement { get; set; } = string.Empty;
    public string Status { get; set; } = string.Empty;
    public double Confidence { get; set; }
    public string CausalityStatus { get; set; } = string.Empty;
    public string TrackerVersion { get; set; } = string.Empty;
    public string SourceInsightIdsJson { get; set; } = "[]";
    public string SourceRelationshipIdsJson { get; set; } = "[]";
    public string SupportingEvidenceJson { get; set; } = "[]";
    public string CounterEvidenceJson { get; set; } = "[]";
    public string MissingContextJson { get; set; } = "[]";
    public string ReasonsJson { get; set; } = "[]";
}
