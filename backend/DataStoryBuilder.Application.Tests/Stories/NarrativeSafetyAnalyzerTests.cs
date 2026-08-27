using System.Text.Json;
using DataStoryBuilder.Application.Stories;
using Xunit;

namespace DataStoryBuilder.Application.Tests.Stories;

public sealed class NarrativeSafetyAnalyzerTests
{
    [Fact]
    public void NeutralFactualStatementDoesNotInflateCertainty()
    {
        var findings = Analyze("Revenue increased 30%.", confidence: 0.65);

        Assert.DoesNotContain(findings, Is(BiasCategory.CertaintyInflation));
    }

    [Fact]
    public void ModerateConfidenceWithStrongCertaintyIsReported()
    {
        var findings = Analyze(
            "This clearly demonstrates the Revenue result.",
            confidence: 0.65);

        var finding = Assert.Single(findings, Is(BiasCategory.CertaintyInflation));
        Assert.Equal(BiasRiskLevel.Medium, finding.RiskLevel);
        Assert.Equal("revenue-item", finding.SourceItemId);
    }

    [Fact]
    public void ExecutiveSummaryCertaintyIsAlsoEvaluated()
    {
        var story = Story(
            "Revenue increased.",
            includeLimitationItem: false,
            executiveSummary: "This clearly demonstrates the result.");
        var grounded = Grounded(confidence: 0.65);

        var findings = NarrativeSafetyAnalyzer.Analyze(story, grounded);

        Assert.Single(findings, Is(BiasCategory.CertaintyInflation));
    }

    [Fact]
    public void RequiredQualificationWithProofLanguageIsHighRisk()
    {
        var findings = Analyze(
            "This conclusively proves the Revenue result.",
            confidence: 0.90,
            requiresQualification: true);

        var finding = Assert.Single(findings, Is(BiasCategory.CertaintyInflation));
        Assert.Equal(BiasRiskLevel.High, finding.RiskLevel);
        Assert.Contains(
            finding.Reasons,
            reason => reason.Contains("requires qualification", StringComparison.Ordinal));
    }

    [Fact]
    public void UnsupportedCausalWordingIsHighRiskFormalAuditFinding()
    {
        var findings = Analyze(
            "Marketing spend drove revenue growth.",
            includeCausalityConstraint: true);

        var finding = Assert.Single(findings, Is(BiasCategory.CausalFraming));
        Assert.Equal(BiasRiskLevel.High, finding.RiskLevel);
        Assert.Contains("drove", finding.Reasons[0]);
    }

    [Theory]
    [InlineData("Marketing spend increased alongside revenue.")]
    [InlineData("Marketing spend and revenue moved together.")]
    public void SafeAssociationLanguageIsNotCausalFraming(string text)
    {
        var findings = Analyze(text, includeCausalityConstraint: true);

        Assert.DoesNotContain(findings, Is(BiasCategory.CausalFraming));
    }

    [Fact]
    public void EstablishedCausalityDoesNotCreateUnsupportedCausalFinding()
    {
        var findings = Analyze(
            "Marketing spend drove revenue growth.",
            includeCausalityConstraint: true,
            causalityEstablished: true);

        Assert.DoesNotContain(findings, Is(BiasCategory.CausalFraming));
    }

    [Fact]
    public void VisibleLimitationAndQualifiedWordingAreCompliant()
    {
        var findings = Analyze(
            "Revenue increased, but the finding remains qualified.",
            confidence: 0.65,
            requiresQualification: true,
            includeLimitation: true,
            includeLimitationItem: true);

        Assert.DoesNotContain(findings, Is(BiasCategory.CertaintyInflation));
        Assert.DoesNotContain(findings, Is(BiasCategory.MissingContextOmission));
    }

    [Fact]
    public void UnsupportedPriceExplanationViolatesKnownMissingContext()
    {
        var findings = Analyze(
            "Higher prices caused revenue per order to rise.",
            includeLimitation: true,
            includeLimitationItem: true);

        Assert.Single(findings, Is(BiasCategory.MissingContextOmission));
    }

    [Fact]
    public void MissingStructuredLimitationItemIsReportedWithoutChangingDay14()
    {
        var story = Story("Revenue increased.", includeLimitationItem: false);
        var grounded = Grounded(
            confidence: 0.65,
            includeLimitation: true);
        var day14 = StoryDataDiffEvaluator.Evaluate(story, grounded);

        var findings = NarrativeSafetyAnalyzer.Analyze(story, grounded);

        Assert.Equal(StoryDataDiffStatus.Fail, day14.Status);
        Assert.Single(findings, Is(BiasCategory.MissingContextOmission));
    }

    [Fact]
    public void CombinedViolationProducesDistinctCategoriesWithoutDuplicates()
    {
        var findings = Analyze(
            "This conclusively proves higher prices caused revenue growth.",
            confidence: 0.65,
            requiresQualification: true,
            includeCausalityConstraint: true,
            includeLimitation: true,
            includeLimitationItem: true);

        Assert.Single(findings, Is(BiasCategory.CertaintyInflation));
        Assert.Single(findings, Is(BiasCategory.CausalFraming));
        Assert.Single(findings, Is(BiasCategory.MissingContextOmission));
    }

    [Fact]
    public void ArbitraryUnverifiableSemanticsDoNotProduceAClaimedFinding()
    {
        var findings = Analyze("Customer satisfaction improved.", confidence: null);

        Assert.Empty(findings);
    }

    private static IReadOnlyList<NarrativeBiasFinding> Analyze(
        string revenueText,
        double? confidence = 0.90,
        bool requiresQualification = false,
        bool includeCausalityConstraint = false,
        bool causalityEstablished = false,
        bool includeLimitation = false,
        bool includeLimitationItem = false)
    {
        var story = Story(revenueText, includeLimitationItem);
        var grounded = Grounded(
            confidence,
            requiresQualification,
            includeCausalityConstraint,
            causalityEstablished,
            includeLimitation);
        return NarrativeSafetyAnalyzer.Analyze(story, grounded);
    }

    private static GeneratedExecutiveStory Story(
        string revenueText,
        bool includeLimitationItem,
        string? executiveSummary = null)
    {
        var items = new List<GeneratedStoryItem>
        {
            new("revenue-item", revenueText),
            new("marketing-item", "MarketingSpend increased alongside Revenue.")
        };
        if (includeLimitationItem)
        {
            items.Add(new GeneratedStoryItem(
                "unit-price-missing",
                "UnitPrice is unavailable as contextual information."));
        }

        return new GeneratedExecutiveStory(
            "Revenue review",
            executiveSummary
                ?? "Revenue and MarketingSpend moved during the period.",
            [new GeneratedStorySection(1, "FINDINGS", items)]);
    }

    private static GroundedStoryPromptInput Grounded(
        double? confidence,
        bool requiresQualification = false,
        bool includeCausalityConstraint = false,
        bool causalityEstablished = false,
        bool includeLimitation = false)
    {
        var findings = new[]
        {
            Finding(
                "revenue-item",
                "revenue-insight",
                "MAIN_OUTCOME",
                "Revenue",
                confidence,
                requiresQualification),
            Finding(
                "marketing-item",
                "marketing-insight",
                "ASSOCIATED_SIGNAL",
                "MarketingSpend",
                0.90,
                false)
        };
        GroundedCausalityConstraint[] constraints = includeCausalityConstraint
            ?
            [
                new GroundedCausalityConstraint(
                    "relationship-1",
                    "marketing-insight",
                    "revenue-insight",
                    "CORRELATIONAL",
                    true,
                    causalityEstablished,
                    causalityEstablished
                        ? "CAUSALITY_ESTABLISHED"
                        : "CAUSALITY_NOT_ESTABLISHED",
                    ["ASSOCIATED_WITH"],
                    ["CAUSED", "DRIVEN_BY"],
                    ["Association evidence does not establish causality."])
            ]
            : [];
        GroundedStoryLimitation[] limitations = includeLimitation
            ?
            [
                new GroundedStoryLimitation(
                    "unit-price-missing",
                    "revenue-insight",
                    "UnitPrice",
                    "NOT_AVAILABLE",
                    "UnitPrice is unavailable.")
            ]
            : [];
        var sourceIds = new List<string> { "revenue-item", "marketing-item" };
        if (includeLimitation)
        {
            sourceIds.Add("unit-price-missing");
        }

        return new GroundedStoryPromptInput(
            "analysis-1",
            "day12-v1",
            [new GroundedStorySection(1, "FINDINGS", sourceIds)],
            findings,
            constraints,
            limitations,
            includeLimitation);
    }

    private static GroundedStoryFinding Finding(
        string sourceItemId,
        string insightId,
        string role,
        string metric,
        double? confidence,
        bool requiresQualification)
    {
        using var period = JsonDocument.Parse("{}");
        using var values = JsonDocument.Parse("{}");
        using var evidenceValue = JsonDocument.Parse("1");
        return new GroundedStoryFinding(
            sourceItemId,
            insightId,
            role,
            "CHANGE",
            metric,
            null,
            null,
            period.RootElement.Clone(),
            "UP",
            values.RootElement.Clone(),
            [new GroundedStoryEvidence(
                "VALUE",
                "Value",
                evidenceValue.RootElement.Clone(),
                null)],
            requiresQualification,
            requiresQualification ? ["The result requires qualification."] : [],
            confidence);
    }

    private static Predicate<NarrativeBiasFinding> Is(BiasCategory category) =>
        finding => finding.Category == category;
}
