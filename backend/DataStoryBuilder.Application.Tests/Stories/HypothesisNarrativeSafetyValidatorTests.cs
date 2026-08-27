using System.Text.Json;
using DataStoryBuilder.Application.Stories;
using Xunit;

namespace DataStoryBuilder.Application.Tests.Stories;

public sealed class HypothesisNarrativeSafetyValidatorTests
{
    [Theory]
    [InlineData("OPEN", "MarketingSpend may be associated with Revenue.")]
    [InlineData("SUPPORTED", "MarketingSpend could be related to Revenue.")]
    public void OpenAndSupportedQualifiedNarrativesPass(
        string status,
        string text)
    {
        var result = Evaluate(text, status);

        Assert.True(result.IsSafe);
        Assert.Equal(HypothesisNarrativeContentType.Hypothesis, result.ContentType);
    }

    [Fact]
    public void ConfirmedDoesNotBypassUnestablishedCausality()
    {
        var result = Evaluate(
            "MarketingSpend caused Revenue growth.",
            "CONFIRMED",
            confidence: 1.0);

        Assert.False(result.IsSafe);
        Assert.Contains("caused", result.Reasons[0], StringComparison.Ordinal);
    }

    [Fact]
    public void HighConfidenceDoesNotPermitCausalLanguage()
    {
        Assert.False(Evaluate(
            "MarketingSpend drove Revenue growth.",
            confidence: 1.0).IsSafe);
    }

    [Fact]
    public void LowConfidenceDoesNotRejectQualifiedLanguage()
    {
        Assert.True(Evaluate(
            "MarketingSpend may be associated with Revenue.",
            confidence: 0.0).IsSafe);
    }

    [Theory]
    [InlineData("MarketingSpend caused Revenue growth.")]
    [InlineData("MarketingSpend led to Revenue growth.")]
    [InlineData("MarketingSpend resulted in Revenue growth.")]
    [InlineData("Revenue growth was driven by MarketingSpend.")]
    [InlineData("Revenue increased because of MarketingSpend.")]
    [InlineData("MarketingSpend was responsible for Revenue growth.")]
    public void BoundedCausalPhrasesAreRejected(string text)
    {
        Assert.False(Evaluate(text).IsSafe);
    }

    [Theory]
    [InlineData("MarketingSpend may be associated with Revenue.")]
    [InlineData("MarketingSpend could be related to Revenue.")]
    [InlineData("MarketingSpend may be relevant to explaining Revenue.")]
    public void ApprovedAssociationLanguageIsAccepted(string text)
    {
        Assert.True(Evaluate(text).IsSafe);
    }

    [Fact]
    public void UnqualifiedFactualWordingIsRejected()
    {
        var result = Evaluate("MarketingSpend explains Revenue growth.");

        Assert.False(result.IsSafe);
        Assert.Contains(
            result.Reasons,
            reason => reason.Contains("uncertainty", StringComparison.Ordinal));
    }

    [Fact]
    public void ContentClassificationCanOnlyBeHypothesis()
    {
        Assert.Equal(
            ["Hypothesis"],
            Enum.GetNames<HypothesisNarrativeContentType>());
        Assert.Equal(
            HypothesisNarrativeContentType.Hypothesis,
            Evaluate("MarketingSpend may be associated with Revenue.").ContentType);
    }

    [Fact]
    public void ValidatorDoesNotCreateNumericalFacts()
    {
        var result = Evaluate(
            "MarketingSpend may be associated with Revenue.");

        Assert.DoesNotContain(
            result.Reasons,
            reason => reason.Any(char.IsDigit));
    }

    [Fact]
    public void EvaluationDoesNotChangeStatusOrConfidence()
    {
        const string status = "OPEN";
        const double confidence = 1.0;

        Evaluate(
            "MarketingSpend may be associated with Revenue.",
            status,
            confidence);

        Assert.Equal("OPEN", status);
        Assert.Equal(1.0, confidence);
    }

    [Fact]
    public void RepeatedEvaluationIsDeterministic()
    {
        var first = Evaluate("MarketingSpend caused Revenue growth.");
        var second = Evaluate("MarketingSpend caused Revenue growth.");

        Assert.Equal(first.IsSafe, second.IsSafe);
        Assert.Equal(first.ContentType, second.ContentType);
        Assert.Equal(first.Reasons, second.Reasons);
    }

    [Fact]
    public void ExistingStoryDataDiffRemainsAuthoritativeAndUnchanged()
    {
        var evidence = new GroundedStoryEvidence(
            "CHANGE",
            "Relative change",
            Json("30"),
            "PERCENT");
        var grounded = Grounded(evidence);
        var story = Story("Revenue increased 30%.");

        var result = StoryDataDiffEvaluator.Evaluate(story, grounded);

        Assert.Equal(StoryDataDiffStatus.Pass, result.Status);
        Assert.Equal(1.0, result.StoryCoverageScore);
        Assert.Equal(1.0, result.EvidenceCoverageScore);
        Assert.Same(
            evidence,
            Assert.Single(result.ItemAudits).EvidenceTrace!.ResolvedEvidence[0]);
    }

    [Fact]
    public void ExistingNarrativeCausalFramingRemainsCompatible()
    {
        var findings = NarrativeSafetyAnalyzer.Analyze(
            Story("MarketingSpend drove Revenue growth."),
            Grounded(new GroundedStoryEvidence(
                "CHANGE",
                "Relative change",
                Json("30"),
                "PERCENT")));

        Assert.Contains(
            findings,
            finding => finding.Category == BiasCategory.CausalFraming
                && finding.RiskLevel == BiasRiskLevel.High);
    }

    private static HypothesisNarrativeSafetyResult Evaluate(
        string text,
        string status = "OPEN",
        double confidence = 0.6) =>
        HypothesisNarrativeSafetyValidator.Evaluate(
            text,
            status,
            confidence,
            "CAUSALITY_NOT_ESTABLISHED");

    private static GeneratedExecutiveStory Story(string text) =>
        new(
            "Revenue overview",
            "Revenue and MarketingSpend moved alongside each other.",
            [
                new GeneratedStorySection(
                    1,
                    "OUTCOME",
                    [new GeneratedStoryItem("revenue-item", text)])
            ]);

    private static GroundedStoryPromptInput Grounded(
        GroundedStoryEvidence evidence) =>
        new(
            "analysis-1",
            "day12-v1",
            [new GroundedStorySection(1, "OUTCOME", ["revenue-item"])],
            [
                new GroundedStoryFinding(
                    "revenue-item",
                    "revenue-insight",
                    "MAIN_OUTCOME",
                    "CHANGE",
                    "Revenue",
                    null,
                    null,
                    Json("{\"previous\":\"2025-05\",\"current\":\"2025-06\"}"),
                    "UP",
                    Json("{\"relativeChange\":30}"),
                    [evidence],
                    false,
                    [],
                    0.9)
            ],
            [
                new GroundedCausalityConstraint(
                    "marketing-revenue-relationship",
                    "marketing-insight",
                    "revenue-insight",
                    "CORRELATIONAL",
                    true,
                    false,
                    "CAUSALITY_NOT_ESTABLISHED",
                    ["ASSOCIATED_WITH"],
                    ["DRIVEN_BY", "CAUSED"],
                    ["Causality is not established."])
            ],
            [],
            false);

    private static JsonElement Json(string json)
    {
        using var document = JsonDocument.Parse(json);
        return document.RootElement.Clone();
    }
}
