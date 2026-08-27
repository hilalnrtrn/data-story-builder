using System.Text.Json;
using DataStoryBuilder.Application.Stories;
using Xunit;

namespace DataStoryBuilder.Application.Tests.Stories;

public sealed class NarrativeFramingAnalyzerTests
{
    [Fact]
    public void NeutralBalancedStoryHasNoMaterialFramingOrEmphasisFinding()
    {
        var result = Analyze(
            "Revenue increased while Orders and Customers declined.",
            "Revenue increased 30% during the period.",
            "Customers declined 12% during the period.",
            "Orders declined 15% during the period.");

        Assert.Empty(result.Signals);
        Assert.Empty(result.Findings);
    }

    [Fact]
    public void SingleStrongPhraseIsSignalButNotMaterialBiasWhenStoryIsBalanced()
    {
        var result = Analyze(
            "Revenue and counter-signals moved in different directions.",
            "Revenue showed strong growth of 30% during the period.",
            "Customers declined 12% and remained a visible counter-signal.",
            "Orders declined 15% and remained a visible counter-signal.");

        var signal = Assert.Single(result.Signals);
        Assert.Equal("strong growth", signal.MatchedPhrase);
        Assert.DoesNotContain(
            result.Findings,
            finding => finding.Category == BiasCategory.PositiveFraming);
    }

    [Fact]
    public void RepeatedStrongPositiveFramingInMixedStoryIsReported()
    {
        var result = Analyze(
            "Revenue delivered remarkable and exceptional growth while counter-signals declined.",
            "Revenue delivered outstanding, impressive growth during the period.",
            "Customers declined 12% during the period.",
            "Orders declined 15% during the period.");

        var finding = Assert.Single(
            result.Findings,
            item => item.Category == BiasCategory.PositiveFraming);
        Assert.Equal(BiasRiskLevel.High, finding.RiskLevel);
    }

    [Fact]
    public void RepeatedAlarmistNegativeFramingInMixedStoryIsReported()
    {
        var result = Analyze(
            "Revenue increased, but Orders faced a catastrophic and alarming decline.",
            "Revenue increased 30% during the period.",
            "Customers experienced a dramatic decline of 12%.",
            "Orders experienced a disastrous decline of 15%.");

        Assert.Contains(
            result.Findings,
            finding => finding.Category == BiasCategory.NegativeFraming
                && finding.RiskLevel == BiasRiskLevel.High);
    }

    [Fact]
    public void MaterialPositiveExposureAndFramingProducesSelectiveEmphasis()
    {
        var result = Analyze(
            "Revenue delivered remarkable and exceptional performance.",
            "Revenue delivered outstanding and impressive strong growth throughout the period, with sustained momentum across the principal commercial result and broad operational visibility.",
            "Customers declined.",
            "Orders declined.");

        var finding = Assert.Single(
            result.Findings,
            item => item.Category == BiasCategory.SelectiveEmphasis);
        Assert.Contains("proportionate visibility", finding.Recommendation);
    }

    [Fact]
    public void SelectiveEmphasisDoesNotModifyPassingDay14Coverage()
    {
        var story = Story(
            "Revenue delivered remarkable and exceptional performance.",
            "Revenue delivered outstanding and impressive strong growth throughout the period, with sustained momentum across the principal commercial result and broad operational visibility.",
            "Customers declined.",
            "Orders declined.");
        var grounded = Grounded();
        var day14 = StoryDataDiffEvaluator.Evaluate(story, grounded);

        var framing = NarrativeFramingAnalyzer.Analyze(story, grounded);

        Assert.Equal(StoryDataDiffStatus.Pass, day14.Status);
        Assert.Equal(1.0, day14.StoryCoverageScore);
        Assert.Contains(
            framing.Findings,
            finding => finding.Category == BiasCategory.SelectiveEmphasis);
    }

    [Fact]
    public void UnsupportedMetricDirectionRemainsNeutralOrUnknown()
    {
        var finding = Finding("stock", "MAIN_OUTCOME", "StockLevel", "UP");

        Assert.Equal(
            StructuredFindingDirection.NeutralOrUnknown,
            NarrativeFramingAnalyzer.ClassifyDirection(finding));
    }

    [Fact]
    public void AssociatedSignalAndLimitationDoNotDistortDirectionBalance()
    {
        var grounded = Grounded() with
        {
            Findings =
            [
                .. Grounded().Findings,
                Finding("marketing", "ASSOCIATED_SIGNAL", "MarketingSpend", "UP")
            ],
            Limitations =
            [
                new GroundedStoryLimitation(
                    "missing",
                    "revenue",
                    "CompetitorPrice",
                    "NOT_AVAILABLE",
                    "CompetitorPrice is unavailable.")
            ]
        };
        var story = new GeneratedExecutiveStory(
            "Mixed result",
            "Revenue increased while counter-signals declined.",
            [
                new GeneratedStorySection(
                    1,
                    "FINDINGS",
                    [
                        Item("revenue", "Revenue increased during the period."),
                        Item("customers", "Customers declined during the period."),
                        Item("orders", "Orders declined during the period."),
                        Item("marketing", "MarketingSpend increased during the period."),
                        Item("missing", "CompetitorPrice is unavailable as context.")
                    ])
            ]);

        var result = NarrativeFramingAnalyzer.Analyze(story, grounded);

        Assert.Empty(result.Findings);
        Assert.Equal(
            StructuredFindingDirection.NeutralOrUnknown,
            NarrativeFramingAnalyzer.ClassifyDirection(
                grounded.Findings.Single(item => item.SourceItemId == "marketing")));
    }

    private static NarrativeFramingAnalysis Analyze(
        string summary,
        string revenue,
        string customers,
        string orders) =>
        NarrativeFramingAnalyzer.Analyze(
            Story(summary, revenue, customers, orders),
            Grounded());

    private static GeneratedExecutiveStory Story(
        string summary,
        string revenue,
        string customers,
        string orders) =>
        new(
            "Mixed performance",
            summary,
            [
                new GeneratedStorySection(
                    1,
                    "FINDINGS",
                    [
                        Item("revenue", revenue),
                        Item("customers", customers),
                        Item("orders", orders)
                    ])
            ]);

    private static GeneratedStoryItem Item(string id, string text) => new(id, text);

    private static GroundedStoryPromptInput Grounded() => new(
        "analysis-1",
        "day12-v1",
        [new GroundedStorySection(1, "FINDINGS", ["revenue", "customers", "orders"])],
        [
            Finding("revenue", "MAIN_OUTCOME", "Revenue", "UP"),
            Finding("customers", "COUNTER_SIGNAL", "Customers", "DOWN"),
            Finding("orders", "COUNTER_SIGNAL", "Orders", "DOWN")
        ],
        [],
        []);

    private static GroundedStoryFinding Finding(
        string id,
        string role,
        string metric,
        string direction)
    {
        using var period = JsonDocument.Parse("{}");
        using var values = JsonDocument.Parse("{}");
        return new GroundedStoryFinding(
            id,
            id + "-insight",
            role,
            "CHANGE",
            metric,
            null,
            null,
            period.RootElement.Clone(),
            direction,
            values.RootElement.Clone(),
            [Evidence()],
            false,
            []);
    }

    private static GroundedStoryEvidence Evidence()
    {
        using var value = JsonDocument.Parse("1");
        return new GroundedStoryEvidence(
            "VALUE",
            "Value",
            value.RootElement.Clone(),
            null);
    }
}
