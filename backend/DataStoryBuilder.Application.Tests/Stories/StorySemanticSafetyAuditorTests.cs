using System.Text.Json;
using DataStoryBuilder.Application.Stories;
using Xunit;

namespace DataStoryBuilder.Application.Tests.Stories;

public sealed class StorySemanticSafetyAuditorTests
{
    [Theory]
    [InlineData("Revenue increased by 30%. Customer satisfaction improved.", "customer satisfaction")]
    [InlineData("Revenue increased by 30%. Employee productivity increased.", "employee productivity")]
    public void UnsupportedBusinessConceptBlocksFullAudit(string text, string concept)
    {
        var (diff, full) = Audit("Revenue", "UP", 30, text);

        Assert.Equal(StoryDataDiffStatus.Fail, diff.Status);
        Assert.True(diff.HasSemanticSafetyFailure);
        Assert.Contains(diff.ItemAudits[0].Reasons, reason =>
            reason.Contains($"unsupported business concept '{concept}'", StringComparison.Ordinal));
        Assert.Equal(StoryAuditDecision.Block, full.Decision);
    }

    [Theory]
    [InlineData("Customers increased by 12%.")]
    [InlineData("Müşteri sayısı %12 arttı.")]
    [InlineData("Customer count grew by 12%.")]
    [InlineData("Müşteri sayısı %12 yükseldi.")]
    public void DownFindingRejectsExplicitUpWording(string text)
    {
        var (diff, full) = Audit("Customers", "DOWN", -12, text);

        Assert.True(diff.HasSemanticSafetyFailure);
        Assert.Contains(diff.ItemAudits[0].Reasons, reason =>
            reason.Contains("contradicts grounded direction 'DOWN'", StringComparison.Ordinal));
        Assert.Equal(StoryAuditDecision.Block, full.Decision);
    }

    [Theory]
    [InlineData("Customers decreased by 12%.")]
    [InlineData("Müşteri sayısı %12 azaldı.")]
    public void DownFindingAcceptsConsistentEnglishAndTurkishWording(string text)
    {
        var (diff, full) = Audit("Customers", "DOWN", -12, text);

        Assert.False(diff.HasSemanticSafetyFailure);
        Assert.Equal(StoryDataDiffStatus.Pass, diff.Status);
        Assert.Equal(StoryAuditDecision.Pass, full.Decision);
    }

    [Fact]
    public void UpFindingRejectsExplicitDownWording()
    {
        var (diff, full) = Audit("Revenue", "UP", 30, "Revenue decreased by 30%.");

        Assert.True(diff.HasSemanticSafetyFailure);
        Assert.Equal(StoryAuditDecision.Block, full.Decision);
    }

    [Theory]
    [InlineData("Revenue increased by 30%.")]
    [InlineData("Gelir %30 arttı.")]
    public void BalancedValidUpWordingStillPasses(string text)
    {
        var (diff, full) = Audit("Revenue", "UP", 30, text);

        Assert.False(diff.HasSemanticSafetyFailure);
        Assert.Equal(StoryDataDiffStatus.Pass, diff.Status);
        Assert.Equal(StoryAuditDecision.Pass, full.Decision);
    }

    private static (StoryDataDiffResult Diff, FullStoryAuditResult Full) Audit(
        string metric,
        string direction,
        decimal relativePercent,
        string text)
    {
        var sourceItemId = "finding-1";
        var evidence = Evidence("RELATIVE_CHANGE", relativePercent);
        using var emptyJson = JsonDocument.Parse("{}");
        var finding = new GroundedStoryFinding(
            sourceItemId,
            "insight-1",
            "MAIN_OUTCOME",
            "CHANGE",
            metric,
            null,
            null,
            emptyJson.RootElement.Clone(),
            direction,
            emptyJson.RootElement.Clone(),
            [evidence],
            false,
            []);
        var grounded = new GroundedStoryPromptInput(
            "analysis-1",
            "day12-v1",
            [new GroundedStorySection(1, "OUTCOME", [sourceItemId])],
            [finding],
            [],
            []);
        var story = new GeneratedExecutiveStory(
            "Title",
            "Summary",
            [new GeneratedStorySection(
                1,
                "OUTCOME",
                [new GeneratedStoryItem(sourceItemId, text)])]);
        var diff = StoryDataDiffEvaluator.Evaluate(story, grounded);
        var full = FullStoryAuditor.Audit(diff, NarrativeBiasEvaluator.Evaluate(story, grounded));
        return (diff, full);
    }

    private static GroundedStoryEvidence Evidence(string code, decimal value)
    {
        using var json = JsonDocument.Parse(value.ToString(
            System.Globalization.CultureInfo.InvariantCulture));
        return new GroundedStoryEvidence(
            code,
            "Relative change",
            json.RootElement.Clone(),
            "PERCENT");
    }
}
