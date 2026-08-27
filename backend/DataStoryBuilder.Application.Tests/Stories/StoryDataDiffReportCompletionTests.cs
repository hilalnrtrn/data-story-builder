using System.Text.Json;
using DataStoryBuilder.Application.Stories;
using Xunit;

namespace DataStoryBuilder.Application.Tests.Stories;

public sealed class StoryDataDiffReportCompletionTests
{
    private const string SemanticLimitation =
        "Arbitrary nonnumerical semantic assertions are not verified by the current prose-only generated-story contract.";

    [Fact]
    public void FindingWithEvidenceIsStrongAndPerfectStoryNeedsNoRegeneration()
    {
        var result = Evaluate(
            ["finding"],
            [Finding("finding", Evidence("30", "PERCENT"))],
            [],
            Item("finding", "Revenue increased 30%."));

        var audit = Assert.Single(result.ItemAudits);
        Assert.Equal(StoryEvidenceStrength.Strong, audit.EvidenceStrength);
        Assert.True(audit.HasResolvedEvidence);
        Assert.Equal(1.0, result.StoryCoverageScore);
        Assert.Equal(1.0, result.EvidenceCoverageScore);
        Assert.False(result.AuditFailed);
        Assert.False(result.RegenerationEligible);
        Assert.Equal([SemanticLimitation], result.AuditLimitations);
        Assert.Equal(StoryDataDiffStatus.Pass, result.Status);
    }

    [Fact]
    public void FindingWithoutEvidenceIsNoneAndFailureIsNotRegenerationEligible()
    {
        var result = Evaluate(
            ["finding"],
            [Finding("finding")],
            [],
            Item("finding", "Revenue changed."));

        Assert.Equal(StoryEvidenceStrength.None, Assert.Single(result.ItemAudits).EvidenceStrength);
        Assert.Equal(0.0, result.EvidenceCoverageScore);
        Assert.True(result.AuditFailed);
        Assert.False(result.RegenerationEligible);
    }

    [Fact]
    public void LimitationIsNotApplicableAndDoesNotReduceEvidenceCoverage()
    {
        var result = Evaluate(
            ["limit"],
            [],
            [Limitation("limit")],
            Item("limit", "CompetitorPrice is unavailable."),
            sectionType: "LIMITATIONS");

        Assert.Equal(
            StoryEvidenceStrength.NotApplicable,
            Assert.Single(result.ItemAudits).EvidenceStrength);
        Assert.Equal(1.0, result.StoryCoverageScore);
        Assert.Equal(1.0, result.EvidenceCoverageScore);
        Assert.False(result.AuditFailed);
        Assert.False(result.RegenerationEligible);
    }

    [Fact]
    public void NumericalMismatchFailsWithPerfectCoverageAndCanRegenerate()
    {
        var result = Evaluate(
            ["finding"],
            [Finding("finding", Evidence("30", "PERCENT"))],
            [],
            Item("finding", "Revenue increased 32%."));

        Assert.Equal(1.0, result.StoryCoverageScore);
        Assert.Equal(1.0, result.EvidenceCoverageScore);
        Assert.True(result.AuditFailed);
        Assert.True(result.RegenerationEligible);
        Assert.Equal("32%", Assert.Single(result.NumericalMismatches).OriginalToken);
    }

    [Fact]
    public void OmissionIsRegenerationEligibleWithoutChangingEvidenceScore()
    {
        var result = Evaluate(
            ["covered", "omitted"],
            [Finding("covered", Evidence("1")), Finding("omitted", Evidence("2"))],
            [],
            Item("covered", "Value was 1."));

        Assert.True(result.AuditFailed);
        Assert.True(result.RegenerationEligible);
        Assert.Equal(["omitted"], result.OmittedSourceItemIds);
        Assert.Equal(0.5, result.StoryCoverageScore);
        Assert.Equal(1.0, result.EvidenceCoverageScore);
    }

    [Fact]
    public void UnexpectedGeneratedIdIsRegenerationEligible()
    {
        var result = Evaluate(
            ["finding"],
            [Finding("finding", Evidence("1"))],
            [],
            Item("finding", "Value was 1."),
            Item("unexpected", "Unexpected prose."));

        Assert.True(result.AuditFailed);
        Assert.True(result.RegenerationEligible);
        Assert.Equal(["unexpected"], result.UnexpectedSourceItemIds);
    }

    [Fact]
    public void MissingEvidencePlusNumericalMismatchIsRegenerationEligible()
    {
        var result = Evaluate(
            ["finding"],
            [Finding("finding")],
            [],
            Item("finding", "Revenue increased 32%."));

        Assert.Equal(0.0, result.EvidenceCoverageScore);
        Assert.True(result.AuditFailed);
        Assert.True(result.RegenerationEligible);
        Assert.Single(result.NumericalMismatches);
    }

    private static StoryDataDiffResult Evaluate(
        IReadOnlyList<string> requiredIds,
        IReadOnlyList<GroundedStoryFinding> findings,
        IReadOnlyList<GroundedStoryLimitation> limitations,
        GeneratedStoryItem firstItem,
        GeneratedStoryItem? secondItem = null,
        string sectionType = "OUTCOME")
    {
        var items = secondItem is null
            ? new[] { firstItem }
            : new[] { firstItem, secondItem };
        return StoryDataDiffEvaluator.Evaluate(
            new GeneratedExecutiveStory(
                "Title",
                "Summary",
                [new GeneratedStorySection(1, sectionType, items)]),
            new GroundedStoryPromptInput(
                "analysis",
                "day12-v1",
                [new GroundedStorySection(1, sectionType, requiredIds)],
                findings,
                [],
                limitations));
    }

    private static GeneratedStoryItem Item(string id, string text) => new(id, text);

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

    private static GroundedStoryEvidence Evidence(
        string value,
        string? unit = null)
    {
        using var json = JsonDocument.Parse(value);
        return new GroundedStoryEvidence("VALUE", "Value", json.RootElement.Clone(), unit);
    }
}
