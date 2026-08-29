using System.Text.Json;
using System.Text.Json.Nodes;
using DataStoryBuilder.Application.Stories;
using Xunit;

namespace DataStoryBuilder.Application.Tests.Stories;

public sealed class Day15StoryAuditorGoldenTests
{
    private static readonly JsonSerializerOptions JsonOptions =
        new(JsonSerializerDefaults.Web);

    [Fact]
    public void BalancedNovaRetailGoldenStoryPassesFullAudit()
    {
        var result = Audit(GoldenStory());

        Assert.Equal(StoryDataDiffStatus.Pass, result.Day14.Status);
        Assert.Equal(1.0, result.Day14.StoryCoverageScore);
        Assert.Equal(1.0, result.Day14.EvidenceCoverageScore);
        Assert.Equal(NarrativeBiasStatus.Pass, result.Bias.Status);
        Assert.Equal(StoryAuditDecision.Pass, result.Full.Decision);
        Assert.False(result.Full.RegenerationEligible);
    }

    [Fact]
    public void PositiveOverFramingAddsValueBeyondPassingDay14Coverage()
    {
        var grounded = GoldenGrounded();
        var revenue = MainRevenueId(grounded);
        var story = Mutate(root =>
        {
            FindItem(root, revenue)["text"] =
                "Revenue delivered remarkable, exceptional and outstanding performance, moving from 1,000,000 to 1,300,000, an impressive increase of 300,000 or 30% across a highly visible commercial period.";
            FindItem(root, MetricId(grounded, "Customers"))["text"] =
                "Customers declined 12%.";
            FindItem(root, MetricId(grounded, "Orders"))["text"] =
                "Orders declined 15%.";
        });

        var result = Audit(story, grounded);

        Assert.Equal(StoryDataDiffStatus.Pass, result.Day14.Status);
        Assert.Contains(result.Bias.Findings, finding =>
            finding.Category == BiasCategory.PositiveFraming);
        Assert.Contains(result.Bias.Findings, finding =>
            finding.Category == BiasCategory.SelectiveEmphasis);
        Assert.Equal(StoryAuditDecision.Regenerate, result.Full.Decision);
        Assert.True(result.Full.RegenerationEligible);
    }

    [Fact]
    public void AlarmistNegativeGoldenStoryRegeneratesWithoutFactualFailure()
    {
        var grounded = GoldenGrounded();
        var story = Mutate(root =>
        {
            FindItem(root, MetricId(grounded, "Customers"))["text"] =
                "Customers experienced a catastrophic and alarming move from 8,000 to 7,040, a dramatic decline of 12%.";
            FindItem(root, MetricId(grounded, "Orders"))["text"] =
                "Orders experienced a disastrous decline from 10,000 to 8,500, a decline of 15%.";
        });

        var result = Audit(story, grounded);

        Assert.Equal(StoryDataDiffStatus.Pass, result.Day14.Status);
        Assert.Contains(result.Bias.Findings, finding =>
            finding.Category == BiasCategory.NegativeFraming);
        Assert.Equal(StoryAuditDecision.Regenerate, result.Full.Decision);
    }

    [Fact]
    public void QualifiedGoldenFindingWithProofLanguageRegenerates()
    {
        var grounded = GoldenGrounded();
        var risk = grounded.Findings.Single(finding => finding.Role == "RISK");
        Assert.True(risk.RequiresQualification);
        var story = Mutate(root =>
            FindItem(root, risk.SourceItemId)["text"] =
                "The 145,000 Smart Watch Revenue anomaly conclusively demonstrates severe performance and requires qualification.");

        var result = Audit(story, grounded);

        Assert.Equal(StoryDataDiffStatus.Pass, result.Day14.Status);
        Assert.Contains(result.Bias.Findings, finding =>
            finding.Category == BiasCategory.CertaintyInflation);
        Assert.Equal(StoryAuditDecision.Regenerate, result.Full.Decision);
    }

    [Fact]
    public void UnsupportedGoldenCausalClaimBlocksFormalAudit()
    {
        var grounded = GoldenGrounded();
        var marketing = MetricId(grounded, "MarketingSpend");
        var story = Mutate(root =>
            FindItem(root, marketing)["text"] =
                "MarketingSpend moved from 100,000 to 120,000 and drove Revenue growth.");

        var result = Audit(story, grounded);

        Assert.Equal(StoryDataDiffStatus.Pass, result.Day14.Status);
        var finding = Assert.Single(result.Bias.Findings, item =>
            item.Category == BiasCategory.CausalFraming);
        Assert.Equal(BiasRiskLevel.High, finding.RiskLevel);
        Assert.Equal(StoryAuditDecision.Block, result.Full.Decision);
        Assert.False(result.Full.RegenerationEligible);
    }

    [Fact]
    public void GoldenPricingContextOverclaimProducesContextAndCausalFindings()
    {
        var grounded = GoldenGrounded();
        Assert.Contains(grounded.Limitations, limitation => limitation.Field == "UnitPrice");
        var story = Mutate(root =>
            FindItem(root, MainRevenueId(grounded))["text"] =
                "Revenue moved from 1,000,000 to 1,300,000, an increase of 300,000 or 30%; higher prices caused revenue per order to rise.");

        var result = Audit(story, grounded);

        Assert.Equal(StoryDataDiffStatus.Pass, result.Day14.Status);
        Assert.Contains(result.Bias.Findings, finding =>
            finding.Category == BiasCategory.MissingContextOmission);
        Assert.Contains(result.Bias.Findings, finding =>
            finding.Category == BiasCategory.CausalFraming);
        Assert.Equal(StoryAuditDecision.Block, result.Full.Decision);
    }

    [Theory]
    [InlineData("Revenue", null, "30%", "32%")]
    [InlineData("Customers", null, "12%", "10%")]
    [InlineData("Revenue", "Marmara", "70%", "75%")]
    public void NumericalGoldenDistortionsBlock(
        string metric,
        string? segment,
        string original,
        string replacement)
    {
        var grounded = GoldenGrounded();
        var sourceId = grounded.Findings.Single(finding =>
            finding.Metric == metric
            && finding.Segment == segment
            && (segment is not null || finding.Role == "MAIN_OUTCOME"
                || metric == "Customers")).SourceItemId;
        var story = Mutate(root =>
        {
            var item = FindItem(root, sourceId);
            item["text"] = item["text"]!.GetValue<string>().Replace(
                original,
                replacement,
                StringComparison.Ordinal);
        });

        var result = Audit(story, grounded);

        Assert.Equal(StoryDataDiffStatus.Fail, result.Day14.Status);
        Assert.Contains(result.Day14.NumericalMismatches, mismatch =>
            mismatch.OriginalToken == replacement);
        Assert.Equal(StoryAuditDecision.Block, result.Full.Decision);
        Assert.False(result.Full.RegenerationEligible);
    }

    [Fact]
    public void OmittedGoldenCounterSignalRegeneratesRatherThanBlocks()
    {
        var grounded = GoldenGrounded();
        var customers = MetricId(grounded, "Customers");
        var story = Mutate(root => RemoveItem(root, customers));

        var result = Audit(story, grounded);

        Assert.Equal([customers], result.Day14.OmittedSourceItemIds);
        Assert.Empty(result.Day14.NumericalMismatches);
        Assert.Equal(StoryAuditDecision.Regenerate, result.Full.Decision);
        Assert.True(result.Full.RegenerationEligible);
    }

    [Fact]
    public void CurrentAnalyzersDoNotFabricateALowWarningPath()
    {
        var grounded = GoldenGrounded();
        var story = Mutate(root =>
            FindItem(root, MainRevenueId(grounded))["text"] =
                "Revenue showed strong growth from 1,000,000 to 1,300,000, an increase of 300,000 or 30%.");

        var result = Audit(story, grounded);

        Assert.DoesNotContain(result.Bias.Findings, finding =>
            finding.RiskLevel == BiasRiskLevel.Low);
        Assert.Equal(StoryAuditDecision.Pass, result.Full.Decision);
    }

    [Fact]
    public void ClearUnsupportedSemanticAdditionBlocksFullAudit()
    {
        var grounded = GoldenGrounded();
        var story = Mutate(root =>
            FindItem(root, MainRevenueId(grounded))["text"] =
                "Revenue moved from 1,000,000 to 1,300,000, an increase of 300,000 or 30%; customer satisfaction improved.");

        var result = Audit(story, grounded);

        Assert.Equal(StoryDataDiffStatus.Fail, result.Day14.Status);
        Assert.True(result.Day14.HasSemanticSafetyFailure);
        Assert.Equal(StoryAuditDecision.Block, result.Full.Decision);
        Assert.Contains(result.Day14.AuditLimitations, limitation =>
            limitation.Contains("beyond explicit direction contradictions", StringComparison.Ordinal));
        Assert.DoesNotContain(result.Bias.Findings, finding =>
            finding.Message.Contains("customer satisfaction", StringComparison.OrdinalIgnoreCase));
    }

    [Fact]
    public void CombinedGoldenAdversarialStoryBlocksWithDistinctDeterministicReasons()
    {
        var grounded = GoldenGrounded();
        var story = Mutate(root =>
        {
            FindItem(root, MainRevenueId(grounded))["text"] =
                "Revenue delivered remarkable, exceptional and outstanding performance, moving from 1,000,000 to 1,300,000, an impressive increase of 300,000 or 30%; this conclusively proves higher prices caused revenue growth.";
            FindItem(root, MetricId(grounded, "Customers"))["text"] =
                "Customers declined 12%.";
            FindItem(root, MetricId(grounded, "Orders"))["text"] =
                "Orders declined 15%.";
        });

        var first = Audit(story, grounded);
        var second = Audit(story, grounded);

        Assert.Contains(first.Bias.Findings, finding => finding.Category == BiasCategory.PositiveFraming);
        Assert.Contains(first.Bias.Findings, finding => finding.Category == BiasCategory.SelectiveEmphasis);
        Assert.Contains(first.Bias.Findings, finding => finding.Category == BiasCategory.CertaintyInflation);
        Assert.Contains(first.Bias.Findings, finding => finding.Category == BiasCategory.CausalFraming);
        Assert.Contains(first.Bias.Findings, finding => finding.Category == BiasCategory.MissingContextOmission);
        Assert.Equal(StoryAuditDecision.Block, first.Full.Decision);
        Assert.False(first.Full.RegenerationEligible);
        Assert.Equal(first.Full.Reasons, first.Full.Reasons.Distinct(StringComparer.Ordinal));
        Assert.Equal(first.Full.Reasons, second.Full.Reasons);
    }

    private static AuditResult Audit(
        GeneratedExecutiveStory story,
        GroundedStoryPromptInput? grounded = null)
    {
        grounded ??= GoldenGrounded();
        var day14 = StoryDataDiffEvaluator.Evaluate(story, grounded);
        var bias = NarrativeBiasEvaluator.Evaluate(story, grounded);
        return new AuditResult(day14, bias, FullStoryAuditor.Audit(day14, bias));
    }

    private static GroundedStoryPromptInput GoldenGrounded()
    {
        using var analytics = JsonDocument.Parse(
            GoldenStoryGenerationTests.GoldenAnalyticsJson());
        return GroundedStoryPromptProjector.Create(analytics.RootElement);
    }

    private static GeneratedExecutiveStory GoldenStory() =>
        JsonSerializer.Deserialize<GeneratedExecutiveStory>(
            GoldenStoryGenerationTests.GoldenGeneratedStoryJson(),
            JsonOptions)!;

    private static GeneratedExecutiveStory Mutate(Action<JsonObject> mutate)
    {
        var root = JsonNode.Parse(
            GoldenStoryGenerationTests.GoldenGeneratedStoryJson())!.AsObject();
        mutate(root);
        return JsonSerializer.Deserialize<GeneratedExecutiveStory>(
            root.ToJsonString(),
            JsonOptions)!;
    }

    private static string MainRevenueId(GroundedStoryPromptInput grounded) =>
        grounded.Findings.Single(finding =>
            finding.Metric == "Revenue" && finding.Role == "MAIN_OUTCOME").SourceItemId;

    private static string MetricId(
        GroundedStoryPromptInput grounded,
        string metric) =>
        grounded.Findings.Single(finding => finding.Metric == metric).SourceItemId;

    private static JsonObject FindItem(JsonObject root, string sourceItemId) =>
        root["sections"]!.AsArray()
            .SelectMany(section => section!["items"]!.AsArray())
            .Select(item => item!.AsObject())
            .Single(item => item["sourceItemId"]!.GetValue<string>() == sourceItemId);

    private static void RemoveItem(JsonObject root, string sourceItemId)
    {
        foreach (var section in root["sections"]!.AsArray())
        {
            var items = section!["items"]!.AsArray();
            var item = items.SingleOrDefault(candidate =>
                candidate!["sourceItemId"]!.GetValue<string>() == sourceItemId);
            if (item is not null)
            {
                items.Remove(item);
                return;
            }
        }
    }

    private sealed record AuditResult(
        StoryDataDiffResult Day14,
        NarrativeBiasResult Bias,
        FullStoryAuditResult Full);
}
