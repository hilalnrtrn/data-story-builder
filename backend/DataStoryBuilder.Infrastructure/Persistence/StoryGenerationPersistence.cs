using System.Text.Json;
using DataStoryBuilder.Application.Stories;
using DataStoryBuilder.Domain.Entities;
using Microsoft.EntityFrameworkCore;

namespace DataStoryBuilder.Infrastructure.Persistence;

public sealed class StoryGenerationPersistence(
    DataStoryBuilderDbContext dbContext)
{
    private const int MaximumFailureReasonLength = 1000;
    private static readonly JsonSerializerOptions JsonOptions =
        new(JsonSerializerDefaults.Web);

    public async Task PersistAsync(
        Guid analysisId,
        StoryGenerationResult generation,
        string? promptVersion,
        string? modelIdentifier,
        DateTimeOffset? generatedAt,
        CancellationToken cancellationToken = default)
    {
        var story = await dbContext.Stories.SingleAsync(
            item => item.AnalysisId == analysisId,
            cancellationToken);

        Apply(
            story,
            generation,
            promptVersion,
            modelIdentifier,
            generatedAt);

        await dbContext.SaveChangesAsync(cancellationToken);
    }

    public static void Apply(
        Story story,
        StoryGenerationResult generation,
        string? promptVersion,
        string? modelIdentifier,
        DateTimeOffset? generatedAt)
    {
        ArgumentNullException.ThrowIfNull(story);
        ArgumentNullException.ThrowIfNull(generation);

        story.PromptVersion = NullIfWhiteSpace(promptVersion);
        story.ModelIdentifier = NullIfWhiteSpace(modelIdentifier);

        if (generation.IsSuccess)
        {
            story.GeneratedStoryJson = JsonSerializer.Serialize(
                generation.Story,
                JsonOptions);
            story.GeneratedAt = generatedAt
                ?? throw new ArgumentNullException(nameof(generatedAt));
            story.GenerationStatus = "Succeeded";
            story.GenerationFailureReason = null;
            return;
        }

        story.GeneratedStoryJson = null;
        story.GeneratedAt = null;
        story.GenerationStatus = "Failed";
        story.GenerationFailureReason = Bound(generation.FailureReason!);
    }

    private static string? NullIfWhiteSpace(string? value) =>
        string.IsNullOrWhiteSpace(value) ? null : value;

    private static string Bound(string value) =>
        value.Length <= MaximumFailureReasonLength
            ? value
            : value[..MaximumFailureReasonLength];
}
