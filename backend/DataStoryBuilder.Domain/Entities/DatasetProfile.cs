namespace DataStoryBuilder.Domain.Entities;

public class DatasetProfile
{
    public Guid Id { get; set; }
    public Guid AnalysisId { get; set; }
    public string ProfileJson { get; set; } = "{}";
    public string QualityJson { get; set; } = "{}";
}
