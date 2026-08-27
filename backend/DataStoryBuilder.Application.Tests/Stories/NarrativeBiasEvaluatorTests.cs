using System.Text.Json;
using DataStoryBuilder.Application.Stories;
using Xunit;

namespace DataStoryBuilder.Application.Tests.Stories;

public sealed class NarrativeBiasEvaluatorTests
{
    [Fact]
    public void NeutralStoryProducesPassWithNoFindings()
    {
        var result = NarrativeBiasEvaluator.Evaluate(
            Story("Revenue increased while Customers declined."),
            Grounded());

        Assert.Equal(NarrativeBiasStatus.Pass, result.Status);
        Assert.Equal(BiasRiskLevel.None, result.RiskLevel);
        Assert.Empty(result.Findings);
    }

    [Fact]
    public void EvaluatorCombinesFramingAndSafetyFindings()
    {
        var story = Story(
            "Revenue delivered remarkable and exceptional performance. This clearly demonstrates the result.");

        var result = NarrativeBiasEvaluator.Evaluate(story, Grounded(0.65));

        Assert.Contains(result.Findings, item => item.Category == BiasCategory.PositiveFraming);
        Assert.Contains(result.Findings, item => item.Category == BiasCategory.CertaintyInflation);
        Assert.Equal(NarrativeBiasStatus.Warning, result.Status);
        Assert.Equal(BiasRiskLevel.Medium, result.RiskLevel);
    }

    [Fact]
    public void ComposeDeduplicatesExactFindingsButRetainsDistinctCategories()
    {
        var framing = Finding(BiasCategory.PositiveFraming, BiasRiskLevel.Medium);
        var certainty = Finding(BiasCategory.CertaintyInflation, BiasRiskLevel.Medium);

        var result = NarrativeBiasEvaluator.Compose(
            [framing, framing, certainty]);

        Assert.Equal(2, result.Findings.Count);
        Assert.Contains(framing, result.Findings);
        Assert.Contains(certainty, result.Findings);
    }

    [Theory]
    [InlineData(BiasRiskLevel.Low, NarrativeBiasStatus.Warning)]
    [InlineData(BiasRiskLevel.Medium, NarrativeBiasStatus.Warning)]
    [InlineData(BiasRiskLevel.High, NarrativeBiasStatus.Fail)]
    public void HighestRiskDeterminesStatus(
        BiasRiskLevel risk,
        NarrativeBiasStatus expectedStatus)
    {
        var result = NarrativeBiasEvaluator.Compose(
            [Finding(BiasCategory.SelectiveEmphasis, risk)]);

        Assert.Equal(expectedStatus, result.Status);
        Assert.Equal(risk, result.RiskLevel);
    }

    private static NarrativeBiasFinding Finding(
        BiasCategory category,
        BiasRiskLevel risk) =>
        new(category, risk, "revenue", "Message", "Recommendation", ["Reason"]);

    private static GeneratedExecutiveStory Story(string revenueText) => new(
        "Mixed performance",
        "Revenue increased while Customers declined.",
        [
            new GeneratedStorySection(
                1,
                "FINDINGS",
                [
                    new GeneratedStoryItem("revenue", revenueText),
                    new GeneratedStoryItem("customers", "Customers declined during the period.")
                ])
        ]);

    private static GroundedStoryPromptInput Grounded(double confidence = 0.90) => new(
        "analysis-1",
        "day12-v1",
        [new GroundedStorySection(1, "FINDINGS", ["revenue", "customers"])],
        [
            Finding("revenue", "MAIN_OUTCOME", "Revenue", "UP", confidence),
            Finding("customers", "COUNTER_SIGNAL", "Customers", "DOWN", 0.90)
        ],
        [],
        []);

    private static GroundedStoryFinding Finding(
        string id,
        string role,
        string metric,
        string direction,
        double confidence)
    {
        using var json = JsonDocument.Parse("{}");
        using var value = JsonDocument.Parse("1");
        return new GroundedStoryFinding(
            id,
            id + "-insight",
            role,
            "CHANGE",
            metric,
            null,
            null,
            json.RootElement.Clone(),
            direction,
            json.RootElement.Clone(),
            [new GroundedStoryEvidence("VALUE", "Value", value.RootElement.Clone(), null)],
            false,
            [],
            confidence);
    }
}
