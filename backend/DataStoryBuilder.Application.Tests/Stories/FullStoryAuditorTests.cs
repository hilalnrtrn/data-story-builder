using DataStoryBuilder.Application.Stories;
using Xunit;

namespace DataStoryBuilder.Application.Tests.Stories;

public sealed class FullStoryAuditorTests
{
    [Fact]
    public void CleanAuditPassesWithoutRegeneration()
    {
        var result = Audit(Day14(), Bias());

        Assert.Equal(StoryAuditDecision.Pass, result.Decision);
        Assert.False(result.RegenerationEligible);
        Assert.Equal("day15-v1", result.AuditorVersion);
    }

    [Fact]
    public void LowBiasOnlyPassesWithWarnings()
    {
        var result = Audit(
            Day14(),
            Bias(Finding(BiasCategory.PositiveFraming, BiasRiskLevel.Low)));

        Assert.Equal(StoryAuditDecision.PassWithWarnings, result.Decision);
        Assert.False(result.RegenerationEligible);
    }

    [Theory]
    [InlineData(BiasCategory.PositiveFraming)]
    [InlineData(BiasCategory.NegativeFraming)]
    [InlineData(BiasCategory.SelectiveEmphasis)]
    [InlineData(BiasCategory.CertaintyInflation)]
    [InlineData(BiasCategory.MissingContextOmission)]
    public void MaterialCorrectableBiasRegenerates(BiasCategory category)
    {
        var result = Audit(
            Day14(),
            Bias(Finding(category, BiasRiskLevel.Medium)));

        Assert.Equal(StoryAuditDecision.Regenerate, result.Decision);
        Assert.True(result.RegenerationEligible);
    }

    [Fact]
    public void HighUnsupportedCausalFramingBlocks()
    {
        var result = Audit(
            Day14(),
            Bias(Finding(BiasCategory.CausalFraming, BiasRiskLevel.High)));

        Assert.Equal(StoryAuditDecision.Block, result.Decision);
        Assert.False(result.RegenerationEligible);
    }

    [Fact]
    public void NumericalDistortionBlocks()
    {
        var mismatch = new StoryNumericalMismatch(
            "main-item",
            "32%",
            32,
            true,
            "Unsupported value.");
        var numerical = new StoryItemNumericalAudit(
            "main-item",
            [],
            [mismatch]);

        var result = Audit(Day14(numericalAudits: [numerical]), Bias());

        Assert.Equal(StoryAuditDecision.Block, result.Decision);
        Assert.False(result.RegenerationEligible);
    }

    [Fact]
    public void UnexpectedSourceItemBlocks()
    {
        var result = Audit(Day14(unexpected: ["invented"]), Bias());

        Assert.Equal(StoryAuditDecision.Block, result.Decision);
    }

    [Fact]
    public void OmittedRequiredContentRegenerates()
    {
        var result = Audit(
            Day14(coverage: 0.5, omitted: ["required-item"]),
            Bias());

        Assert.Equal(StoryAuditDecision.Regenerate, result.Decision);
        Assert.True(result.RegenerationEligible);
    }

    [Fact]
    public void MissingGroundedEvidenceBlocksWithoutAutomaticRegeneration()
    {
        var result = Audit(Day14(evidenceCoverage: 0.5), Bias());

        Assert.Equal(StoryAuditDecision.Block, result.Decision);
        Assert.False(result.RegenerationEligible);
    }

    [Fact]
    public void FullAuditReusesExactDay14InstanceAndPreservesFeedback()
    {
        var day14 = Day14();
        var first = Finding(BiasCategory.PositiveFraming, BiasRiskLevel.Medium);
        var second = Finding(BiasCategory.CertaintyInflation, BiasRiskLevel.Medium);
        var third = Finding(BiasCategory.MissingContextOmission, BiasRiskLevel.Medium);

        var result = Audit(day14, Bias(first, second, third));

        Assert.Same(day14, result.StoryDataDiff);
        Assert.Equal(StoryAuditDecision.Regenerate, result.Decision);
        Assert.Contains(first.Message, result.Reasons);
        Assert.Contains(first.Recommendation, result.Reasons);
        Assert.Contains(second.Recommendation, result.Reasons);
        Assert.Contains(third.Recommendation, result.Reasons);
    }

    private static FullStoryAuditResult Audit(
        StoryDataDiffResult day14,
        NarrativeBiasResult bias) =>
        FullStoryAuditor.Audit(day14, bias);

    private static NarrativeBiasResult Bias(
        params NarrativeBiasFinding[] findings) =>
        NarrativeBiasEvaluator.Compose(findings);

    private static NarrativeBiasFinding Finding(
        BiasCategory category,
        BiasRiskLevel risk) =>
        new(
            category,
            risk,
            "main-item",
            $"{category} was detected.",
            $"Correct {category}.",
            ["Deterministic reason."]);

    private static StoryDataDiffResult Day14(
        double coverage = 1.0,
        double evidenceCoverage = 1.0,
        IReadOnlyList<string>? omitted = null,
        IReadOnlyList<string>? unexpected = null,
        IReadOnlyList<StoryItemNumericalAudit>? numericalAudits = null) =>
        new(
            coverage == 1.0
            && evidenceCoverage == 1.0
            && (omitted?.Count ?? 0) == 0
            && (unexpected?.Count ?? 0) == 0
            && (numericalAudits?.SelectMany(item => item.UnsupportedTokens).Any() ?? false) == false
                ? StoryDataDiffStatus.Pass
                : StoryDataDiffStatus.Fail,
            coverage,
            evidenceCoverage,
            ["main-item"],
            coverage == 1.0 ? ["main-item"] : [],
            omitted ?? [],
            unexpected ?? [],
            [],
            numericalAudits ?? [],
            [],
            ["Semantic audit limitation."]);
}
