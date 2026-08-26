namespace DataStoryBuilder.Domain.Entities;

public class CausalityEvaluation
{
    public Guid AnalysisId { get; set; }
    public string RelationshipId { get; set; } = string.Empty;
    public string SourceInsightId { get; set; } = string.Empty;
    public string TargetInsightId { get; set; } = string.Empty;
    public string SourceMetric { get; set; } = string.Empty;
    public string TargetMetric { get; set; } = string.Empty;
    public string Status { get; set; } = string.Empty;
    public bool AssociationPresent { get; set; }
    public bool CausalityEstablished { get; set; }
    public string CausalEvidenceJson { get; set; } = "[]";
    public string AllowedConceptsJson { get; set; } = "[]";
    public string ForbiddenConceptsJson { get; set; } = "[]";
    public string ReasonsJson { get; set; } = "[]";
}
