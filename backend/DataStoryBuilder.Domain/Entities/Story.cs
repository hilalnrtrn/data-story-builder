namespace DataStoryBuilder.Domain.Entities;

public class Story
{
    public Guid Id { get; set; }
    public Guid AnalysisId { get; set; }
    public string PlannerVersion { get; set; } = string.Empty;
    public string StoryPlanJson { get; set; } = "{}";
    public DateTimeOffset CreatedAt { get; set; }
}
