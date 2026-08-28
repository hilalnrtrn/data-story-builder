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
        StoryDataDiffResult? storyAudit,
        FullStoryAuditResult? fullStoryAudit,
        string? promptVersion,
        string? modelIdentifier,
        DateTimeOffset? generatedAt,
        string? generationLanguage = null,
        CancellationToken cancellationToken = default)
    {
        var story = await dbContext.Stories.SingleAsync(
            item => item.AnalysisId == analysisId,
            cancellationToken);

        Apply(
            story,
            generation,
            storyAudit,
            fullStoryAudit,
            promptVersion,
            modelIdentifier,
            generatedAt,
            generationLanguage);

        await dbContext.SaveChangesAsync(cancellationToken);
    }

    public static void Apply(
        Story story,
        StoryGenerationResult generation,
        StoryDataDiffResult? storyAudit,
        FullStoryAuditResult? fullStoryAudit,
        string? promptVersion,
        string? modelIdentifier,
        DateTimeOffset? generatedAt,
        string? generationLanguage = null)
    {
        ArgumentNullException.ThrowIfNull(story);
        ArgumentNullException.ThrowIfNull(generation);

        story.PromptVersion = NullIfWhiteSpace(promptVersion);
        story.ModelIdentifier = NullIfWhiteSpace(modelIdentifier);
        story.GenerationLanguage = NormalizeLanguage(generationLanguage);

        if (generation.IsSuccess)
        {
            ArgumentNullException.ThrowIfNull(storyAudit);
            ArgumentNullException.ThrowIfNull(fullStoryAudit);
            story.GeneratedStoryJson = JsonSerializer.Serialize(
                generation.Story,
                JsonOptions);
            story.StoryAuditJson = JsonSerializer.Serialize(
                storyAudit,
                JsonOptions);
            story.FullStoryAuditJson = JsonSerializer.Serialize(
                fullStoryAudit,
                JsonOptions);
            story.GeneratedAt = generatedAt
                ?? throw new ArgumentNullException(nameof(generatedAt));
            story.GenerationStatus = "Succeeded";
            story.GenerationFailureReason = null;
            return;
        }

        story.GeneratedStoryJson = null;
        story.StoryAuditJson = null;
        story.FullStoryAuditJson = null;
        story.GeneratedAt = null;
        story.GenerationStatus = "Failed";
        story.GenerationFailureReason = Bound(generation.FailureReason!);
    }

    private static string? NullIfWhiteSpace(string? value) =>
        string.IsNullOrWhiteSpace(value) ? null : value;

    private static string? NormalizeLanguage(string? value) =>
        string.IsNullOrWhiteSpace(value)
            ? null
            : StoryGenerationLanguage.RequireSupported(value);

    private static string Bound(string value) =>
        value.Length <= MaximumFailureReasonLength
            ? value
            : value[..MaximumFailureReasonLength];
}
