using System.Text.Json;
using DataStoryBuilder.Application.Stories;
using Xunit;

namespace DataStoryBuilder.Application.Tests.Stories;

public sealed class StoryDataDiffEvaluatorTests
{
    [Fact]
    public void PerfectStoryPassesWithCompleteCoverageAndTraceability()
    {
        var evidence = Evidence("CURRENT_VALUE", 1300);
        var result = Evaluate(
            [Section(2, "LIMITATIONS", "limit"), Section(1, "OUTCOME", "finding")],
            [Finding("finding", evidence)],
            [Limitation("limit")],
            GroundedSection(1, "OUTCOME", "finding"),
            GroundedSection(2, "LIMITATIONS", "limit"));

        Assert.Equal(StoryDataDiffStatus.Pass, result.Status);
        Assert.Equal(1.0, result.StoryCoverageScore);
        Assert.Equal(1.0, result.EvidenceCoverageScore);
        Assert.Equal(["finding", "limit"], result.RequiredSourceItemIds);
        Assert.Equal(["finding", "limit"], result.CoveredSourceItemIds);
        Assert.Empty(result.OmittedSourceItemIds);
        Assert.Empty(result.UnexpectedSourceItemIds);

        var audit = result.ItemAudits[0];
        Assert.True(audit.HasResolvedEvidence);
        Assert.Equal("insight-finding", audit.EvidenceTrace!.InsightId);
        Assert.Same(evidence, Assert.Single(audit.EvidenceTrace.ResolvedEvidence));
    }

    [Fact]
    public void OmittedItemIsReportedInAuthoritativeOrderAndFails()
    {
        var result = Evaluate(
            [Section(1, "OUTCOME", "first")],
            [Finding("first", Evidence("E1", 1)), Finding("second", Evidence("E2", 2))],
            [],
            GroundedSection(1, "OUTCOME", "first", "second"));

        Assert.Equal(StoryDataDiffStatus.Fail, result.Status);
        Assert.Equal(0.5, result.StoryCoverageScore);
        Assert.Equal(["first"], result.CoveredSourceItemIds);
        Assert.Equal(["second"], result.OmittedSourceItemIds);
    }

    [Fact]
    public void UnexpectedGeneratedItemIsReportedInGeneratedOrderAndFails()
    {
        var result = Evaluate(
            [Section(1, "OUTCOME", "required", "unexpected-2", "unexpected-1")],
            [Finding("required", Evidence("E", 1))],
            [],
            GroundedSection(1, "OUTCOME", "required"));

        Assert.Equal(StoryDataDiffStatus.Fail, result.Status);
        Assert.Equal(["unexpected-2", "unexpected-1"], result.UnexpectedSourceItemIds);
        Assert.Equal(1.0, result.StoryCoverageScore);
    }

    [Fact]
    public void FindingWithoutEvidenceReducesEvidenceCoverageAndFails()
    {
        var result = Evaluate(
            [Section(1, "OUTCOME", "with-evidence", "without-evidence")],
            [Finding("with-evidence", Evidence("E", 1)), Finding("without-evidence")],
            [],
            GroundedSection(1, "OUTCOME", "with-evidence", "without-evidence"));

        Assert.Equal(StoryDataDiffStatus.Fail, result.Status);
        Assert.Equal(1.0, result.StoryCoverageScore);
        Assert.Equal(0.5, result.EvidenceCoverageScore);
        Assert.False(result.ItemAudits[1].HasResolvedEvidence);
    }

    [Fact]
    public void LimitationIsStoryCoveredButExcludedFromEvidenceDenominator()
    {
        var result = Evaluate(
            [Section(1, "LIMITATIONS", "limit")],
            [],
            [Limitation("limit")],
            GroundedSection(1, "LIMITATIONS", "limit"));

        Assert.Equal(StoryDataDiffStatus.Pass, result.Status);
        Assert.Equal(1.0, result.StoryCoverageScore);
        Assert.Equal(1.0, result.EvidenceCoverageScore);
        Assert.True(Assert.Single(result.ItemAudits).IsLimitation);
    }

    [Fact]
    public void MixedCoverageUsesOnlyGeneratedResolvedFindingsForEvidenceScore()
    {
        var result = Evaluate(
            [Section(1, "OUTCOME", "first", "second"), Section(2, "LIMITATIONS", "limit")],
            [Finding("first", Evidence("E", 1)), Finding("second")],
            [Limitation("limit")],
            GroundedSection(1, "OUTCOME", "first", "second"),
            GroundedSection(2, "LIMITATIONS", "limit"));

        Assert.Equal(1.0, result.StoryCoverageScore);
        Assert.Equal(0.5, result.EvidenceCoverageScore);
        Assert.Equal(StoryDataDiffStatus.Fail, result.Status);
    }

    [Fact]
    public void EmptyAuthorityProducesNormalizedScores()
    {
        var result = Evaluate([], [], []);
        Assert.InRange(result.StoryCoverageScore, 0.0, 1.0);
        Assert.InRange(result.EvidenceCoverageScore, 0.0, 1.0);
        Assert.Equal(1.0, result.StoryCoverageScore);
        Assert.Equal(1.0, result.EvidenceCoverageScore);
    }

    private static StoryDataDiffResult Evaluate(
        IReadOnlyList<GeneratedStorySection> generatedSections,
        IReadOnlyList<GroundedStoryFinding> findings,
        IReadOnlyList<GroundedStoryLimitation> limitations,
        params GroundedStorySection[] groundedSections) =>
        StoryDataDiffEvaluator.Evaluate(
            new GeneratedExecutiveStory("Title", "Summary", generatedSections.Count == 0
                ? [new GeneratedStorySection(1, "EMPTY", [new GeneratedStoryItem("unexpected", "Text")])]
                : generatedSections),
            new GroundedStoryPromptInput(
                "analysis-1",
                "day12-v1",
                groundedSections,
                findings,
                [],
                limitations));

    private static GeneratedStorySection Section(
        int order,
        string type,
        params string[] ids) =>
        new(order, type, ids.Select(id => new GeneratedStoryItem(id, $"Text for {id}.")).ToArray());

    private static GroundedStorySection GroundedSection(
        int order,
        string type,
        params string[] ids) =>
        new(order, type, ids);

    private static GroundedStoryFinding Finding(
        string id,
        params GroundedStoryEvidence[] evidence)
    {
        using var json = JsonDocument.Parse("{}");
        return new GroundedStoryFinding(
            id,
            $"insight-{id}",
            "MAIN_OUTCOME",
            "CHANGE",
            "Revenue",
            null,
            null,
            json.RootElement.Clone(),
            "UP",
            json.RootElement.Clone(),
            evidence,
            false,
            []);
    }

    private static GroundedStoryLimitation Limitation(string id) =>
        new(id, $"insight-{id}", "CompetitorPrice", "NOT_AVAILABLE", "Unavailable.");

    private static GroundedStoryEvidence Evidence(string code, int value)
    {
        using var json = JsonDocument.Parse(value.ToString());
        return new GroundedStoryEvidence(code, code, json.RootElement.Clone(), null);
    }
}
