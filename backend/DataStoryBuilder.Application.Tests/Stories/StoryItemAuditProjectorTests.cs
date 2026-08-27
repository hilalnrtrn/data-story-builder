using System.Text.Json;
using DataStoryBuilder.Application.Stories;
using Xunit;

namespace DataStoryBuilder.Application.Tests.Stories;

public sealed class StoryItemAuditProjectorTests
{
    [Fact]
    public void NormalItemResolvesAndPreservesGroundedTraceability()
    {
        const string text = "  Revenue changed exactly as reported.  ";
        var evidence = Evidence("CURRENT_VALUE", 1300);
        var result = StoryItemAuditProjector.Create(
            Story(Section(1, "OUTCOME", Item("main-item", text))),
            Input(findings: [Finding("main-item", "MAIN_OUTCOME", "revenue", evidence)]));

        var source = Assert.Single(result);
        Assert.Equal("main-item", source.SourceItemId);
        Assert.Equal(text, source.GeneratedText);
        Assert.Equal("MAIN_OUTCOME", source.Role);
        Assert.Equal("revenue", source.InsightId);
        Assert.False(source.IsLimitation);
        Assert.True(source.IsResolved);
        Assert.Same(evidence, Assert.Single(source.ResolvedEvidence));
    }

    [Fact]
    public void LimitationResolvesWithoutFabricatedAnalyticalEvidence()
    {
        var result = StoryItemAuditProjector.Create(
            Story(Section(1, "LIMITATIONS", Item("missing-item", "Context is unavailable."))),
            Input(limitations: [new GroundedStoryLimitation(
                "missing-item",
                "revenue",
                "CompetitorPrice",
                "NOT_AVAILABLE",
                "Competitor pricing is unavailable.")]));

        var source = Assert.Single(result);
        Assert.Equal("MISSING_CONTEXT", source.Role);
        Assert.Equal("revenue", source.InsightId);
        Assert.True(source.IsLimitation);
        Assert.True(source.IsResolved);
        Assert.Empty(source.ResolvedEvidence);
    }

    [Fact]
    public void UnexpectedSourceIdRemainsUnresolvedWithoutGuessing()
    {
        var result = StoryItemAuditProjector.Create(
            Story(Section(1, "OUTCOME", Item("unexpected-item", "Unverified wording."))),
            Input());

        var source = Assert.Single(result);
        Assert.Equal("unexpected-item", source.SourceItemId);
        Assert.Equal("Unverified wording.", source.GeneratedText);
        Assert.False(source.IsResolved);
        Assert.False(source.IsLimitation);
        Assert.Null(source.Role);
        Assert.Null(source.InsightId);
        Assert.Empty(source.ResolvedEvidence);
    }

    [Fact]
    public void ProjectionUsesSectionOrderAndPreservesItemOrder()
    {
        var result = StoryItemAuditProjector.Create(
            Story(
                Section(2, "SECONDARY_FINDINGS", Item("third", "Third")),
                Section(1, "OUTCOME", Item("first", "First"), Item("second", "Second"))),
            Input());

        Assert.Equal(
            ["first", "second", "third"],
            result.Select(item => item.SourceItemId));
    }

    private static GeneratedExecutiveStory Story(
        params GeneratedStorySection[] sections) =>
        new("Title", "Summary", sections);

    private static GeneratedStorySection Section(
        int order,
        string type,
        params GeneratedStoryItem[] items) =>
        new(order, type, items);

    private static GeneratedStoryItem Item(string id, string text) => new(id, text);

    private static GroundedStoryPromptInput Input(
        IReadOnlyList<GroundedStoryFinding>? findings = null,
        IReadOnlyList<GroundedStoryLimitation>? limitations = null) =>
        new(
            "analysis-1",
            "day12-v1",
            [],
            findings ?? [],
            [],
            limitations ?? []);

    private static GroundedStoryFinding Finding(
        string sourceItemId,
        string role,
        string insightId,
        params GroundedStoryEvidence[] evidence)
    {
        using var period = JsonDocument.Parse("{}");
        using var values = JsonDocument.Parse("{}");
        return new GroundedStoryFinding(
            sourceItemId,
            insightId,
            role,
            "CHANGE",
            "Revenue",
            null,
            null,
            period.RootElement.Clone(),
            "UP",
            values.RootElement.Clone(),
            evidence,
            false,
            []);
    }

    private static GroundedStoryEvidence Evidence(string code, int value)
    {
        using var document = JsonDocument.Parse(value.ToString());
        return new GroundedStoryEvidence(
            code,
            "Current value",
            document.RootElement.Clone(),
            null);
    }
}
