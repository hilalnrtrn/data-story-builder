namespace DataStoryBuilder.Domain.Entities;

public class Story
{
    public Guid Id { get; set; }
    public Guid AnalysisId { get; set; }
    public string PlannerVersion { get; set; } = string.Empty;
    public string StoryPlanJson { get; set; } = "{}";
    public DateTimeOffset CreatedAt { get; set; }
    public string? GeneratedStoryJson { get; set; }
    public string? PromptVersion { get; set; }
    public string? ModelIdentifier { get; set; }
    public DateTimeOffset? GeneratedAt { get; set; }
    public string? GenerationStatus { get; set; }
    public string? GenerationFailureReason { get; set; }
}
