using System.Text.Json;
using System.Text.Json.Nodes;
using DataStoryBuilder.Application.Stories;
using Xunit;

namespace DataStoryBuilder.Application.Tests.Stories;

public sealed class StoryAuditContractTests
{
    [Fact]
    public void ControlledVocabulariesContainExactlyTheDay15Members()
    {
        Assert.Equal(
            ["PositiveFraming", "NegativeFraming", "SelectiveEmphasis", "CertaintyInflation", "CausalFraming", "MissingContextOmission"],
            Enum.GetNames<BiasCategory>());
        Assert.Equal(
            ["None", "Low", "Medium", "High"],
            Enum.GetNames<BiasRiskLevel>());
        Assert.Equal(
            ["Pass", "Warning", "Fail"],
            Enum.GetNames<NarrativeBiasStatus>());
        Assert.Equal(
            ["Pass", "PassWithWarnings", "Regenerate", "Block"],
            Enum.GetNames<StoryAuditDecision>());
    }

    [Fact]
    public void NarrativeBiasResultExposesFindingsCategoryRiskAndMaterialBias()
    {
        var finding = new NarrativeBiasFinding(
            BiasCategory.CertaintyInflation,
            BiasRiskLevel.Medium,
            "main-item",
            "The narrative certainty exceeds the grounded finding.",
            "Use qualified wording.",
            ["The finding requires qualification."]);
        var result = new NarrativeBiasResult(
            NarrativeBiasStatus.Warning,
            BiasRiskLevel.Medium,
            [finding]);

        Assert.True(result.HasMaterialBias);
        Assert.Same(finding, Assert.Single(result.Findings));
        Assert.Equal(
            BiasRiskLevel.Medium,
            result.GetCategoryRisk(BiasCategory.CertaintyInflation));
        Assert.Equal(
            BiasRiskLevel.None,
            result.GetCategoryRisk(BiasCategory.PositiveFraming));
    }

    [Fact]
    public void FullAuditReusesTheExactDay14ResultWithoutDuplicatingCoverageFields()
    {
        var day14 = Day14Result();
        var bias = new NarrativeBiasResult(
            NarrativeBiasStatus.Pass,
            BiasRiskLevel.None,
            []);

        var result = new FullStoryAuditResult(
            day14,
            bias,
            StoryAuditDecision.Pass,
            [],
            day14.RegenerationEligible,
            "day15-v1");

        Assert.Same(day14, result.StoryDataDiff);
        Assert.Same(bias, result.NarrativeBias);
        Assert.DoesNotContain(
            typeof(FullStoryAuditResult).GetProperties(),
            property => property.Name is "StoryCoverageScore"
                or "EvidenceCoverageScore"
                or "NumericalMismatches");
    }

    [Fact]
    public void FullAuditRoundTripsWithWebJsonConventions()
    {
        var options = new JsonSerializerOptions(JsonSerializerDefaults.Web);
        var original = new FullStoryAuditResult(
            Day14Result(),
            new NarrativeBiasResult(
                NarrativeBiasStatus.Pass,
                BiasRiskLevel.None,
                []),
            StoryAuditDecision.Pass,
            ["The story satisfies the configured audit rules."],
            false,
            "day15-v1");

        var json = JsonSerializer.Serialize(original, options);
        var roundTripped = JsonSerializer.Deserialize<FullStoryAuditResult>(
            json,
            options);

        Assert.NotNull(roundTripped);
        Assert.Equal("day15-v1", roundTripped.AuditorVersion);
        Assert.Equal(StoryAuditDecision.Pass, roundTripped.Decision);
        Assert.Equal(StoryDataDiffStatus.Pass, roundTripped.StoryDataDiff.Status);
    }

    [Fact]
    public void GroundedProjectionRetainsConfidenceAndInterpretationLimit()
    {
        var root = JsonNode.Parse(
            GoldenStoryGenerationTests.GoldenAnalyticsJson())!.AsObject();
        root["insights"]!.AsArray()[0]!["confidence"] = 0.91;
        using var document = JsonDocument.Parse(root.ToJsonString());

        var grounded = GroundedStoryPromptProjector.Create(
            document.RootElement);

        Assert.True(grounded.InterpretationLimited);
        Assert.Contains(
            grounded.Findings,
            finding => finding.Confidence == 0.91);
    }

    private static StoryDataDiffResult Day14Result() => new(
        StoryDataDiffStatus.Pass,
        1.0,
        1.0,
        ["main-item"],
        ["main-item"],
        [],
        [],
        [],
        [],
        [],
        ["Arbitrary nonnumerical semantic assertions are not verified."]);
}
