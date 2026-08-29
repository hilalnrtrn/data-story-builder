using System.Text.Json;
using System.Text.Json.Nodes;
using DataStoryBuilder.Application.Stories;
using Xunit;

namespace DataStoryBuilder.Application.Tests.Stories;

public sealed class StoryDataDiffGoldenTests
{
    private static readonly JsonSerializerOptions JsonOptions =
        new(JsonSerializerDefaults.Web);

    [Fact]
    public void NovaRetailGoldenStoryPassesWithCompleteCoverageAndTraceability()
    {
        var (story, grounded) = Golden();

        var result = StoryDataDiffEvaluator.Evaluate(story, grounded);

        Assert.Equal(StoryDataDiffStatus.Pass, result.Status);
        Assert.False(result.AuditFailed);
        Assert.False(result.RegenerationEligible);
        Assert.Equal(1.0, result.StoryCoverageScore);
        Assert.Equal(1.0, result.EvidenceCoverageScore);
        Assert.Empty(result.OmittedSourceItemIds);
        Assert.Empty(result.UnexpectedSourceItemIds);
        Assert.Empty(result.NumericalMismatches);

        var revenue = grounded.Findings.Single(item =>
            item.Metric == "Revenue"
            && item.Role == "MAIN_OUTCOME");
        var revenueAudit = result.ItemAudits.Single(item =>
            item.SourceItemId == revenue.SourceItemId);
        Assert.Equal(revenue.InsightId, revenueAudit.InsightId);
        Assert.Equal(StoryEvidenceStrength.Strong, revenueAudit.EvidenceStrength);
        Assert.Contains(
            "PERCENTAGE_CHANGE",
            revenueAudit.EvidenceTrace!.ResolvedEvidence.Select(item => item.Code));

        var marmara = grounded.Findings.Single(item => item.Segment == "Marmara");
        var marmaraAudit = result.ItemAudits.Single(item =>
            item.SourceItemId == marmara.SourceItemId);
        Assert.Equal(marmara.InsightId, marmaraAudit.InsightId);
        Assert.Contains(
            "CONTRIBUTION_SHARE",
            marmaraAudit.EvidenceTrace!.ResolvedEvidence.Select(item => item.Code));

        var limitation = result.ItemAudits.First(item => item.IsLimitation);
        Assert.Equal(StoryEvidenceStrength.NotApplicable, limitation.EvidenceStrength);
    }

    [Fact]
    public void OmittingGoldenCustomersCounterSignalIsReportedWithoutNumericMismatch()
    {
        var (story, grounded) = Golden();
        var customersId = grounded.Findings.Single(item => item.Metric == "Customers").SourceItemId;
        story = MutateStory(root => RemoveItem(root, customersId));

        var result = StoryDataDiffEvaluator.Evaluate(story, grounded);

        Assert.Equal(StoryDataDiffStatus.Fail, result.Status);
        Assert.True(result.AuditFailed);
        Assert.True(result.RegenerationEligible);
        Assert.Equal([customersId], result.OmittedSourceItemIds);
        Assert.True(result.StoryCoverageScore < 1.0);
        Assert.Empty(result.NumericalMismatches);
    }

    [Fact]
    public void GoldenRevenueThirtyTwoPercentMutationFailsNumericalPreservation()
    {
        var (_, grounded) = Golden();
        var revenueId = grounded.Findings.Single(item =>
            item.Metric == "Revenue" && item.Role == "MAIN_OUTCOME").SourceItemId;
        var story = MutateStory(root =>
            FindItem(root, revenueId)["text"] =
                "Revenue moved from 1,000,000 to 1,300,000, an increase of 300,000 or 32%.");

        var result = StoryDataDiffEvaluator.Evaluate(story, grounded);

        Assert.Equal(StoryDataDiffStatus.Fail, result.Status);
        Assert.True(result.AuditFailed);
        Assert.True(result.RegenerationEligible);
        Assert.Equal(1.0, result.StoryCoverageScore);
        Assert.Equal(1.0, result.EvidenceCoverageScore);
        Assert.Equal("32%", Assert.Single(result.NumericalMismatches).OriginalToken);
        Assert.Contains(
            result.ItemAudits,
            item => item.SourceItemId == revenueId && item.IsCovered);
        Assert.Contains(
            "Generated story contains unsupported numerical values.",
            result.Reasons);
    }

    [Fact]
    public void UnknownGoldenGeneratedSourceItemIsFormallyReported()
    {
        var (_, grounded) = Golden();
        var story = MutateStory(root =>
        {
            var items = root["sections"]![0]!["items"]!.AsArray();
            items.Add(new JsonObject
            {
                ["sourceItemId"] = "unknown-golden-item",
                ["text"] = "Unexpected prose."
            });
        });

        var result = StoryDataDiffEvaluator.Evaluate(story, grounded);

        Assert.Equal(StoryDataDiffStatus.Fail, result.Status);
        Assert.Equal(["unknown-golden-item"], result.UnexpectedSourceItemIds);
        Assert.True(result.RegenerationEligible);
    }

    [Fact]
    public void GoldenDerivedMissingEvidenceFailsWithoutRegenerationEligibility()
    {
        var (_, grounded) = Golden();
        var revenue = grounded.Findings.Single(item =>
            item.Metric == "Revenue" && item.Role == "MAIN_OUTCOME");
        var findings = grounded.Findings
            .Select(item => item.SourceItemId == revenue.SourceItemId
                ? item with { Evidence = [] }
                : item)
            .ToArray();
        grounded = grounded with { Findings = findings };
        var story = MutateStory(root =>
            FindItem(root, revenue.SourceItemId)["text"] = "Revenue changed.");

        var result = StoryDataDiffEvaluator.Evaluate(story, grounded);

        Assert.Equal(StoryDataDiffStatus.Fail, result.Status);
        Assert.True(result.AuditFailed);
        Assert.False(result.RegenerationEligible);
        Assert.True(result.EvidenceCoverageScore < 1.0);
        var audit = result.ItemAudits.Single(item =>
            item.SourceItemId == revenue.SourceItemId);
        Assert.Equal(StoryEvidenceStrength.None, audit.EvidenceStrength);
        Assert.Empty(result.NumericalMismatches);
    }

    [Fact]
    public void ClearUnsupportedSemanticAdditionFailsWithExplainableFinding()
    {
        var (_, grounded) = Golden();
        var revenueId = grounded.Findings.Single(item =>
            item.Metric == "Revenue" && item.Role == "MAIN_OUTCOME").SourceItemId;
        var story = MutateStory(root =>
            FindItem(root, revenueId)["text"] = "Customer satisfaction improved.");

        var result = StoryDataDiffEvaluator.Evaluate(story, grounded);

        Assert.Equal(StoryDataDiffStatus.Fail, result.Status);
        Assert.True(result.HasSemanticSafetyFailure);
        Assert.Contains(result.ItemAudits.SelectMany(audit => audit.Reasons), reason =>
            reason.Contains("unsupported business concept 'customer satisfaction'", StringComparison.Ordinal));
        Assert.Contains(
            "Semantic assertions beyond explicit direction contradictions and the bounded material business-concept vocabulary are not verified by the current prose-only generated-story contract.",
            result.AuditLimitations);
    }

    [Fact]
    public void GoldenAuditIsDeterministic()
    {
        var (story, grounded) = Golden();

        var first = StoryDataDiffEvaluator.Evaluate(story, grounded);
        var second = StoryDataDiffEvaluator.Evaluate(story, grounded);

        Assert.Equal(first.Status, second.Status);
        Assert.Equal(first.StoryCoverageScore, second.StoryCoverageScore);
        Assert.Equal(first.EvidenceCoverageScore, second.EvidenceCoverageScore);
        Assert.Equal(first.RequiredSourceItemIds, second.RequiredSourceItemIds);
        Assert.Equal(first.CoveredSourceItemIds, second.CoveredSourceItemIds);
        Assert.Equal(first.OmittedSourceItemIds, second.OmittedSourceItemIds);
        Assert.Equal(first.UnexpectedSourceItemIds, second.UnexpectedSourceItemIds);
        Assert.Equal(
            first.NumericalMismatches.Select(item => item.OriginalToken),
            second.NumericalMismatches.Select(item => item.OriginalToken));
        Assert.Equal(
            first.ItemAudits.Select(item => item.SourceItemId),
            second.ItemAudits.Select(item => item.SourceItemId));
    }

    private static (GeneratedExecutiveStory Story, GroundedStoryPromptInput Grounded) Golden()
    {
        using var analytics = JsonDocument.Parse(
            GoldenStoryGenerationTests.GoldenAnalyticsJson());
        var grounded = GroundedStoryPromptProjector.Create(analytics.RootElement);
        var story = JsonSerializer.Deserialize<GeneratedExecutiveStory>(
            GoldenStoryGenerationTests.GoldenGeneratedStoryJson(),
            JsonOptions)!;
        return (story, grounded);
    }

    private static GeneratedExecutiveStory MutateStory(Action<JsonObject> mutate)
    {
        var root = JsonNode.Parse(
            GoldenStoryGenerationTests.GoldenGeneratedStoryJson())!.AsObject();
        mutate(root);
        return JsonSerializer.Deserialize<GeneratedExecutiveStory>(
            root.ToJsonString(),
            JsonOptions)!;
    }

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
}
