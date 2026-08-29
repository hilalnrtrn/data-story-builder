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
            Evidence(evidenceValue, unit),
            evidenceValue.StartsWith("-", StringComparison.Ordinal) ? "DOWN" : "UP");

        Assert.Equal(StoryDataDiffStatus.Pass, result.Status);
        Assert.Equal(1.0, result.StoryCoverageScore);
        Assert.Equal(1.0, result.EvidenceCoverageScore);
        Assert.Empty(result.NumericalMismatches);
        Assert.True(Assert.Single(result.NumericalAudits).Passed);
    }

    [Fact]
    public void TurkishRevenueItemPassesWithOnlyItsAuthoritativeEvidence()
    {
        var result = StoryDataDiffEvaluator.Evaluate(
            Story(Section(1, "OUTCOME", Item(
                "finding",
                "Gelir %30 artış göstererek 1.300.000 TL'ye yükseldi (önceki dönem 1.000.000 TL)."))),
            Input(
                [new GroundedStorySection(1, "OUTCOME", ["finding"])],
                [Finding(
                    "finding",
                    Evidence("1000000"),
                    Evidence("1300000"),
                    Evidence("30", "PERCENT"))],
                []));

        Assert.Equal(StoryDataDiffStatus.Pass, result.Status);
        Assert.Empty(result.NumericalMismatches);
        Assert.True(Assert.Single(result.NumericalAudits).Passed);
    }

    [Fact]
    public void RoundedOnlineContributionPassesWithRatioEvidence()
    {
        var result = StoryDataDiffEvaluator.Evaluate(
            Story(Section(1, "SECONDARY_FINDINGS", Item(
                "online-contribution",
                "Online kanal, gelir artışına 230.000 TL ekleyerek toplam artışın yaklaşık %76,7'sine katkı sağlamıştır."))),
            Input(
                [new GroundedStorySection(
                    1,
                    "SECONDARY_FINDINGS",
                    ["online-contribution"])],
                [Finding(
                    "online-contribution",
                    Evidence("230000"),
                    Evidence("0.766667", "RATIO"))],
                []));

        Assert.Equal(StoryDataDiffStatus.Pass, result.Status);
        Assert.Empty(result.NumericalMismatches);
        var audit = Assert.Single(result.NumericalAudits);
        Assert.True(audit.Passed);
        Assert.Empty(audit.UnsupportedTokens);
        Assert.Equal(2, audit.ExtractedTokens.Count);
    }

    [Theory]
    [InlineData("%76,8")]
    [InlineData("%75")]
    public void IncorrectRoundedOnlineContributionStillFails(string generatedText)
    {
        var result = EvaluateFinding(
            generatedText,
            Evidence("0.766667", "RATIO"));

        Assert.Equal(StoryDataDiffStatus.Fail, result.Status);
        Assert.Single(result.NumericalMismatches);
        Assert.False(Assert.Single(result.NumericalAudits).Passed);
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
        GroundedStoryEvidence evidence,
        string direction = "UP") =>
        StoryDataDiffEvaluator.Evaluate(
            Story(Section(1, "OUTCOME", Item("finding", generatedText))),
            Input(
                [new GroundedStorySection(1, "OUTCOME", ["finding"])],
                [Finding("finding", direction, evidence)],
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
        => Finding(id, "UP", evidence);

    private static GroundedStoryFinding Finding(
        string id,
        string direction,
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
            direction,
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
