namespace DataStoryBuilder.Domain.Entities;

public class Insight
{
    public string Id { get; set; } = string.Empty;
    public Guid AnalysisId { get; set; }
    public string Type { get; set; } = string.Empty;
    public string Metric { get; set; } = string.Empty;
    public string? Dimension { get; set; }
    public string? Segment { get; set; }
    public string? PeriodGranularity { get; set; }
    public string? Direction { get; set; }
    public double? Confidence { get; set; }
    public double? Importance { get; set; }
    public double? BusinessRelevance { get; set; }
    public string? ImpactDirection { get; set; }
    public double? PriorityScore { get; set; }
    public string? PriorityLevel { get; set; }
    public int? Rank { get; set; }
    public string PeriodJson { get; set; } = "{}";
    public string ValuesJson { get; set; } = "{}";
    public string DetectionJson { get; set; } = "{}";
    public string ConfidenceBreakdownJson { get; set; } = "{}";
    public string ImportanceBreakdownJson { get; set; } = "{}";
    public string? SourceJson { get; set; }
    public string? BusinessRelevanceDetailsJson { get; set; }
    public string? PriorityDetailsJson { get; set; }
    public string? RankingDetailsJson { get; set; }
}
