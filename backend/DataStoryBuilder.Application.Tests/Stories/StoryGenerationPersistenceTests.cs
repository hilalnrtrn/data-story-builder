using System.Text.Json;
using DataStoryBuilder.Application.Stories;
using DataStoryBuilder.Domain.Entities;
using DataStoryBuilder.Infrastructure.Persistence;
using Microsoft.EntityFrameworkCore;
using Xunit;

namespace DataStoryBuilder.Application.Tests.Stories;

public sealed class StoryGenerationPersistenceTests
{
    [Fact]
    public void SuccessUpdatesGenerationFieldsWithoutChangingStoryPlan()
    {
        var story = ExistingStory();
        var originalPlan = story.StoryPlanJson;
        var generatedAt = new DateTimeOffset(2026, 8, 27, 10, 0, 0, TimeSpan.Zero);
        var generated = new GeneratedExecutiveStory(
            "Revenue overview",
            "Revenue changed.",
            [new GeneratedStorySection(
                1,
                "OUTCOME",
                [new GeneratedStoryItem("main-item", "Exact generated wording.")])]);

        StoryGenerationPersistence.Apply(
            story,
            StoryGenerationResult.Succeeded(generated),
            Audit(StoryDataDiffStatus.Pass),
            "day13-v1",
            "approved-model",
            generatedAt);

        Assert.Equal(originalPlan, story.StoryPlanJson);
        Assert.Equal("Succeeded", story.GenerationStatus);
        Assert.Equal("day13-v1", story.PromptVersion);
        Assert.Equal("approved-model", story.ModelIdentifier);
        Assert.Equal(generatedAt, story.GeneratedAt);
        Assert.Null(story.GenerationFailureReason);
        Assert.NotNull(story.GeneratedStoryJson);
        Assert.NotNull(story.StoryAuditJson);
        using var document = JsonDocument.Parse(story.GeneratedStoryJson);
        Assert.Equal(
            "Exact generated wording.",
            document.RootElement.GetProperty("sections")[0]
                .GetProperty("items")[0].GetProperty("text").GetString());
    }

    [Fact]
    public void ControlledFailureStoresSanitizedFailureAndNoGeneratedStory()
    {
        var story = ExistingStory();
        var failure = StoryGenerationResult.Failed(
            StoryGenerationFailure.SafetyRejected,
            "Generated story failed safety validation.");

        StoryGenerationPersistence.Apply(
            story,
            failure,
            null,
            "day13-v1",
            null,
            null);

        Assert.Equal("Failed", story.GenerationStatus);
        Assert.Null(story.GeneratedStoryJson);
        Assert.Null(story.StoryAuditJson);
        Assert.Null(story.GeneratedAt);
        Assert.Null(story.ModelIdentifier);
        Assert.Equal("day13-v1", story.PromptVersion);
        Assert.Equal(
            "Generated story failed safety validation.",
            story.GenerationFailureReason);
        Assert.Equal("{\"analysisId\":\"analysis-1\"}", story.StoryPlanJson);
    }

    [Fact]
    public void FailureReasonIsBounded()
    {
        var story = ExistingStory();
        StoryGenerationPersistence.Apply(
            story,
            StoryGenerationResult.Failed(
                StoryGenerationFailure.InvalidProviderResponse,
                new string('x', 1200)),
            null,
            null,
            null,
            null);
        Assert.Equal(1000, story.GenerationFailureReason!.Length);
    }

    [Fact]
    public void EfModelKeepsOneStoryPerAnalysisAndMapsGenerationColumns()
    {
        var options = new DbContextOptionsBuilder<DataStoryBuilderDbContext>()
            .UseNpgsql("Host=localhost;Database=model_only")
            .Options;
        using var context = new DataStoryBuilderDbContext(options);
        var entity = context.Model.FindEntityType(typeof(Story))!;

        Assert.Contains(
            entity.GetIndexes(),
            index => index.IsUnique
                && index.Properties.Single().Name == nameof(Story.AnalysisId));
        Assert.Equal("jsonb", entity.FindProperty(nameof(Story.GeneratedStoryJson))!.GetColumnType());
        Assert.Equal("jsonb", entity.FindProperty(nameof(Story.StoryAuditJson))!.GetColumnType());
        Assert.Equal(64, entity.FindProperty(nameof(Story.PromptVersion))!.GetMaxLength());
        Assert.Equal(128, entity.FindProperty(nameof(Story.ModelIdentifier))!.GetMaxLength());
        Assert.Equal(16, entity.FindProperty(nameof(Story.GenerationStatus))!.GetMaxLength());
        Assert.Equal(1000, entity.FindProperty(nameof(Story.GenerationFailureReason))!.GetMaxLength());
        Assert.True(entity.FindProperty(nameof(Story.GeneratedStoryJson))!.IsNullable);
        Assert.True(entity.FindProperty(nameof(Story.StoryAuditJson))!.IsNullable);
    }

    [Theory]
    [InlineData(StoryDataDiffStatus.Pass, false)]
    [InlineData(StoryDataDiffStatus.Fail, true)]
    public void SuccessfulGenerationPersistsAuditAsJsonObjectAndKeepsGenerationSucceeded(
        StoryDataDiffStatus status,
        bool expectedAuditFailed)
    {
        var story = ExistingStory();
        var generated = new GeneratedExecutiveStory(
            "Revenue overview",
            "Revenue changed.",
            [new GeneratedStorySection(1, "OUTCOME", [new GeneratedStoryItem("main-item", "Revenue changed.")])]);

        StoryGenerationPersistence.Apply(
            story,
            StoryGenerationResult.Succeeded(generated),
            Audit(status),
            "day13-v1",
            "approved-model",
            DateTimeOffset.UtcNow);

        Assert.Equal("Succeeded", story.GenerationStatus);
        using var document = JsonDocument.Parse(story.StoryAuditJson!);
        var root = document.RootElement;
        Assert.Equal(JsonValueKind.Object, root.ValueKind);
        Assert.Equal((int)status, root.GetProperty("status").GetInt32());
        Assert.Equal(1.0, root.GetProperty("storyCoverageScore").GetDouble());
        Assert.Equal(1.0, root.GetProperty("evidenceCoverageScore").GetDouble());
        Assert.Equal(expectedAuditFailed, root.GetProperty("auditFailed").GetBoolean());
        Assert.Equal(status == StoryDataDiffStatus.Fail, root.GetProperty("regenerationEligible").GetBoolean());
        Assert.Equal(JsonValueKind.Array, root.GetProperty("auditLimitations").ValueKind);
        Assert.Equal(JsonValueKind.Array, root.GetProperty("numericalMismatches").ValueKind);
    }

    [Fact]
    public void ReloadProjectionReturnsPersistedAuditAndLegacyRowReturnsNull()
    {
        var story = ExistingStory();
        story.StoryAuditJson = "{\"status\":\"Pass\",\"storyCoverageScore\":1}";

        var audit = AnalysisDetailPersistence.ProjectStoryAudit(story);

        Assert.NotNull(audit);
        Assert.Equal("Pass", audit.Value.GetProperty("status").GetString());
        Assert.Null(AnalysisDetailPersistence.ProjectStoryAudit(ExistingStory()));
    }

    [Fact]
    public void ReloadProjectionReturnsPersistedMetadata()
    {
        var generatedAt = new DateTimeOffset(2026, 8, 27, 10, 0, 0, TimeSpan.Zero);
        var story = ExistingStory();
        story.GenerationStatus = "Succeeded";
        story.PromptVersion = "day13-v1";
        story.ModelIdentifier = "approved-model";
        story.GeneratedAt = generatedAt;

        var detail = AnalysisDetailPersistence.ProjectStoryGeneration(story);

        Assert.NotNull(detail);
        Assert.Equal("Succeeded", detail.Status);
        Assert.Equal("day13-v1", detail.PromptVersion);
        Assert.Equal("approved-model", detail.ModelIdentifier);
        Assert.Equal(generatedAt, detail.GeneratedAt);
        Assert.Null(detail.FailureReason);
    }

    [Fact]
    public void LegacyStoryReloadHasNoGenerationMetadata()
    {
        Assert.Null(AnalysisDetailPersistence.ProjectStoryGeneration(ExistingStory()));
    }

    private static Story ExistingStory() => new()
    {
        Id = Guid.NewGuid(),
        AnalysisId = Guid.NewGuid(),
        PlannerVersion = "day12-v1",
        StoryPlanJson = "{\"analysisId\":\"analysis-1\"}",
        CreatedAt = DateTimeOffset.UtcNow
    };

    private static StoryDataDiffResult Audit(StoryDataDiffStatus status) => new(
        status,
        1.0,
        1.0,
        ["main-item"],
        ["main-item"],
        [],
        status == StoryDataDiffStatus.Fail ? ["unexpected-item"] : [],
        [],
        [],
        status == StoryDataDiffStatus.Fail ? ["Unexpected generated source items were found."] : [],
        ["Arbitrary semantic assertions are not verified."]);
}
