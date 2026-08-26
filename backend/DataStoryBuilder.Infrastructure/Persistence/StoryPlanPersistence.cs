using System.Text.Json;
using DataStoryBuilder.Domain.Entities;

namespace DataStoryBuilder.Infrastructure.Persistence;

public sealed class StoryPlanPersistence(
    DataStoryBuilderDbContext dbContext)
{
    public async Task PersistAsync(
        Guid analysisId,
        string analyticsResponseJson,
        CancellationToken cancellationToken = default)
    {
        using var document = JsonDocument.Parse(analyticsResponseJson);
        var root = document.RootElement;

        if (
            root.ValueKind != JsonValueKind.Object
            || !root.TryGetProperty("storyPlan", out var storyPlan)
            || storyPlan.ValueKind != JsonValueKind.Object
        )
        {
            throw new JsonException(
                "The analytics response must contain a storyPlan object.");
        }

        var plannerVersion = GetRequiredString(
            storyPlan,
            "plannerVersion");
        var responseAnalysisId = GetRequiredString(
            storyPlan,
            "analysisId");

        if (
            !Guid.TryParse(responseAnalysisId, out var parsedAnalysisId)
            || parsedAnalysisId != analysisId
        )
        {
            throw new JsonException(
                "The storyPlan analysisId does not match the analysis.");
        }

        dbContext.Stories.Add(new Story
        {
            Id = Guid.NewGuid(),
            AnalysisId = analysisId,
            PlannerVersion = plannerVersion,
            StoryPlanJson = storyPlan.GetRawText(),
            CreatedAt = DateTimeOffset.UtcNow
        });

        await dbContext.SaveChangesAsync(cancellationToken);
    }

    private static string GetRequiredString(
        JsonElement parent,
        string propertyName)
    {
        if (
            !parent.TryGetProperty(propertyName, out var property)
            || property.ValueKind != JsonValueKind.String
            || string.IsNullOrWhiteSpace(property.GetString())
        )
        {
            throw new JsonException(
                $"The storyPlan property '{propertyName}' must be a non-empty string.");
        }

        return property.GetString()!;
    }
}
