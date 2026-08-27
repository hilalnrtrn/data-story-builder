using System.Text.Json;
using DataStoryBuilder.Application.Stories;
using Xunit;

namespace DataStoryBuilder.Application.Tests.Stories;

public sealed class StoryDataDiffNumericalIntegrationTests
{
    [Theory]
    [InlineData("30%", "30", "PERCENT")]
    [InlineData("decline of 15%", "-15", "PERCENT")]
    [InlineData("70%", "0.70", "RATIO")]
    [InlineData("1,300,000", "1300000", null)]
    public void SupportedNumericalFormsPass(
        string generatedText,
        string evidenceValue,
        string? unit)
    {
        var result = EvaluateFinding(
            generatedText,
            Evidence(evidenceValue, unit));

        Assert.Equal(StoryDataDiffStatus.Pass, result.Status);
        Assert.Equal(1.0, result.StoryCoverageScore);
        Assert.Equal(1.0, result.EvidenceCoverageScore);
        Assert.Empty(result.NumericalMismatches);
        Assert.True(Assert.Single(result.NumericalAudits).Passed);
    }

    [Theory]
    [InlineData("32%", "30", "PERCENT", "32%")]
    [InlineData("decline of 20%", "-15", "PERCENT", "20%")]
    [InlineData("75%", "0.70", "RATIO", "75%")]
    [InlineData("1,500,000", "1300000", null, "1,500,000")]
    public void UnsupportedNumericalFormsFailWithoutChangingCoverage(
        string generatedText,
        string evidenceValue,
        string? unit,
        string expectedToken)
    {
        var result = EvaluateFinding(
            generatedText,
            Evidence(evidenceValue, unit));

        Assert.Equal(StoryDataDiffStatus.Fail, result.Status);
        Assert.Equal(1.0, result.StoryCoverageScore);
        Assert.Equal(1.0, result.EvidenceCoverageScore);
        var mismatch = Assert.Single(result.NumericalMismatches);
        Assert.Equal("finding", mismatch.SourceItemId);
        Assert.Equal(expectedToken, mismatch.OriginalToken);
        Assert.False(Assert.Single(result.NumericalAudits).Passed);
        Assert.Contains(
            "Generated story contains unsupported numerical values.",
            result.Reasons);
    }

    [Fact]
    public void LimitationNumbersRemainOutsideNumericalAudit()
    {
        var story = Story(Section(1, "LIMITATIONS", Item("limit", "Unavailable in 2025; reference 99.")));
        var input = Input(
            [new GroundedStorySection(1, "LIMITATIONS", ["limit"])],
            [],
            [new GroundedStoryLimitation(
                "limit", "insight", "CompetitorPrice", "NOT_AVAILABLE", "Unavailable.")]);

        var result = StoryDataDiffEvaluator.Evaluate(story, input);

        Assert.Equal(StoryDataDiffStatus.Pass, result.Status);
        Assert.Empty(result.NumericalAudits);
        Assert.Empty(result.NumericalMismatches);
    }

    [Fact]
    public void ExistingStructuralAndEvidenceFailuresRemainIndependent()
    {
        var story = Story(Section(1, "OUTCOME", Item("without-evidence", "No number.")));
        var input = Input(
            [new GroundedStorySection(1, "OUTCOME", ["without-evidence", "omitted"])],
            [Finding("without-evidence"), Finding("omitted", Evidence("1"))],
            []);

        var result = StoryDataDiffEvaluator.Evaluate(story, input);

        Assert.Equal(StoryDataDiffStatus.Fail, result.Status);
        Assert.Equal(0.5, result.StoryCoverageScore);
        Assert.Equal(0.0, result.EvidenceCoverageScore);
        Assert.Equal(["omitted"], result.OmittedSourceItemIds);
        Assert.Empty(result.NumericalMismatches);
    }

    private static StoryDataDiffResult EvaluateFinding(
        string generatedText,
        GroundedStoryEvidence evidence) =>
        StoryDataDiffEvaluator.Evaluate(
            Story(Section(1, "OUTCOME", Item("finding", generatedText))),
            Input(
                [new GroundedStorySection(1, "OUTCOME", ["finding"])],
                [Finding("finding", evidence)],
                []));

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
        IReadOnlyList<GroundedStorySection> sections,
        IReadOnlyList<GroundedStoryFinding> findings,
        IReadOnlyList<GroundedStoryLimitation> limitations) =>
        new("analysis", "day12-v1", sections, findings, [], limitations);

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

    private static GroundedStoryEvidence Evidence(
        string value,
        string? unit = null)
    {
        using var json = JsonDocument.Parse(value);
        return new GroundedStoryEvidence(
            "VALUE",
            "Value",
            json.RootElement.Clone(),
            unit);
    }
}
