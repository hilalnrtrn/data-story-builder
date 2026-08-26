namespace DataStoryBuilder.Domain.Entities;

public class MissingContextEvaluation
{
    public Guid AnalysisId { get; set; }
    public string InsightId { get; set; } = string.Empty;
    public bool InterpretationLimited { get; set; }
    public string MissingContextJson { get; set; } = "[]";
    public string ReasonsJson { get; set; } = "[]";
    public string ContextSummaryJson { get; set; } = "{}";
}
