using System.Globalization;
using System.Text.Json;
using System.Text.Json.Nodes;
using DataStoryBuilder.Application.Stories;
using Xunit;

namespace DataStoryBuilder.Application.Tests.Stories;

public sealed class GroundedPromptBuilderTests
{
    [Fact]
    public void ValidResponseProjectsGroundedPromptInput()
    {
        var input = Project();

        Assert.Equal("analysis-1", input.AnalysisId);
        Assert.Equal("day12-v1", input.PlannerVersion);
        Assert.Equal(3, input.Sections.Count);
        Assert.Equal(2, input.Findings.Count);
    }

    [Fact]
    public void OnlySelectedInsightsAreIncluded()
    {
        var input = Project();

        Assert.Equal(
            ["revenue-insight", "marketing-insight"],
            input.Findings.Select(item => item.InsightId));
    }

    [Fact]
    public void UnselectedInsightIsExcluded()
    {
        Assert.DoesNotContain(
            Project().Findings,
            item => item.InsightId == "unselected-insight");
    }

    [Fact]
    public void OnlyReferencedEvidenceCodesAreIncluded()
    {
        Assert.Equal(
            ["REVENUE_CHANGE"],
            Project().Findings[0].Evidence.Select(item => item.Code));
    }

    [Fact]
    public void UnrelatedEvidenceIsExcluded()
    {
        Assert.DoesNotContain(
            Project().Findings.SelectMany(item => item.Evidence),
            item => item.Code == "UNRELATED");
    }

    [Fact]
    public void MissingInsightReferenceIsRejected()
    {
        using var document = ParseResponse(
            json => json.Replace(
                "\"insightId\": \"revenue-insight\"",
                "\"insightId\": \"missing-insight\""));

        Assert.Throws<JsonException>(() =>
            GroundedStoryPromptProjector.Create(document.RootElement));
    }

    [Fact]
    public void MissingEvidenceReferenceIsRejected()
    {
        using var document = ParseResponse(
            json => json.Replace("REVENUE_CHANGE\"]", "MISSING_EVIDENCE\"]"));

        Assert.Throws<JsonException>(() =>
            GroundedStoryPromptProjector.Create(document.RootElement));
    }

    [Fact]
    public void OutlineOrderIsPreserved()
    {
        Assert.Equal([1, 2, 3], Project().Sections.Select(item => item.Order));
    }

    [Fact]
    public void SourceItemIdsArePreserved()
    {
        Assert.Equal(
            ["main-item", "associated-item", "missing-item"],
            Project().Sections.SelectMany(item => item.SourceItemIds));
    }

    [Fact]
    public void MissingContextLimitationsArePreserved()
    {
        var limitation = Assert.Single(Project().Limitations);
        Assert.Equal("CompetitorPrice", limitation.Field);
        Assert.Equal("NOT_AVAILABLE", limitation.Status);
        Assert.Equal("Competitor pricing is unavailable.", limitation.Reason);
    }

    [Fact]
    public void CausalityForbiddenConceptsArePreserved()
    {
        var constraint = Assert.Single(Project().CausalityConstraints);
        Assert.Equal(["CAUSED", "LED_TO"], constraint.ForbiddenConcepts);
        Assert.False(constraint.CausalityEstablished);
    }

    [Fact]
    public void QualificationInformationIsPreserved()
    {
        var finding = Project().Findings[0];
        Assert.True(finding.RequiresQualification);
        Assert.Equal(["Interpret with qualification."], finding.QualificationReasons);
    }

    [Fact]
    public void PromptExcludesRawRowsFullPayloadAndUnselectedData()
    {
        var prompt = new GroundedPromptBuilder().Build(Project());

        Assert.DoesNotContain("rawSchema", prompt);
        Assert.DoesNotContain("SECRET_RAW_ROW", prompt);
        Assert.DoesNotContain("unselected-insight", prompt);
        Assert.DoesNotContain("UNRELATED", prompt);
    }

    [Fact]
    public void PromptContainsExplicitNoAnalysisAndNoCausalityRules()
    {
        var prompt = new GroundedPromptBuilder().Build(Project());

        Assert.Contains("Do not analyze data", prompt);
        Assert.Contains("Do not infer causes", prompt);
        Assert.Contains("association is not a driver or cause", prompt);
    }

    [Theory]
    [InlineData("tr", "in Turkish")]
    [InlineData("en", "in English")]
    public void PromptRequiresRequestedOutputLanguage(
        string language,
        string expectedInstruction)
    {
        var input = Project(language);
        var prompt = new GroundedPromptBuilder().Build(input);

        Assert.Equal(language, input.OutputLanguage);
        Assert.Contains(expectedInstruction, prompt);
        Assert.Contains("Do not analyze data", prompt);
        Assert.Contains("Do not introduce new numerical values", prompt);
        Assert.Contains("preserve section order, type, sourceItemId, evidence", prompt);
    }

    [Fact]
    public void PromptIsDeterministic()
    {
        var input = Project();
        var builder = new GroundedPromptBuilder();

        Assert.Equal(builder.Build(input), builder.Build(input));
    }

    [Fact]
    public void PromptUsesInvariantNumericFormatting()
    {
        var originalCulture = CultureInfo.CurrentCulture;
        try
        {
            CultureInfo.CurrentCulture = CultureInfo.GetCultureInfo("tr-TR");
            var prompt = new GroundedPromptBuilder().Build(Project());
            Assert.Contains("1234.5", prompt);
            Assert.DoesNotContain("1234,5", prompt);
        }
        finally
        {
            CultureInfo.CurrentCulture = originalCulture;
        }
    }

    [Fact]
    public void PromptIncludesTitleAndSummaryGroundingRules()
    {
        var prompt = new GroundedPromptBuilder().Build(Project());
        Assert.Contains("Title and executiveSummary are wording-only", prompt);
        Assert.Contains("profitability claims", prompt);
        Assert.Contains("recommendations", prompt);
    }

    [Fact]
    public void PromptInputRoundTripsWithWebJsonOptions()
    {
        var expected = Project();
        var options = new JsonSerializerOptions(JsonSerializerDefaults.Web);
        var json = JsonSerializer.Serialize(expected, options);
        var actual = JsonSerializer.Deserialize<GroundedStoryPromptInput>(json, options);

        Assert.NotNull(actual);
        Assert.Equal(expected.AnalysisId, actual.AnalysisId);
        Assert.Equal(
            expected.Sections.Select(item => (item.Order, item.Type)),
            actual.Sections.Select(item => (item.Order, item.Type)));
        Assert.Equal(
            expected.Sections.SelectMany(item => item.SourceItemIds),
            actual.Sections.SelectMany(item => item.SourceItemIds));
        Assert.True(JsonNode.DeepEquals(
            JsonNode.Parse(expected.Findings[0].Values.GetRawText()),
            JsonNode.Parse(actual.Findings[0].Values.GetRawText())));
        Assert.Contains("\"sourceItemId\"", json);
    }

    private static GroundedStoryPromptInput Project(
        string outputLanguage = StoryGenerationLanguage.Default)
    {
        using var document = ParseResponse();
        return GroundedStoryPromptProjector.Create(
            document.RootElement,
            outputLanguage);
    }

    private static JsonDocument ParseResponse(Func<string, string>? transform = null)
    {
        var json = """
        {
          "rawSchema": { "rows": ["SECRET_RAW_ROW"] },
          "insights": [
            {
              "id": "revenue-insight", "type": "CHANGE", "metric": "Revenue",
              "dimension": null, "segment": null, "period": { "previous": "2025-05", "current": "2025-06" },
              "direction": "UP", "values": { "previous": 1000, "current": 1234.5, "percentageChange": 23.45 },
              "evidence": [
                { "code": "REVENUE_CHANGE", "label": "Revenue change", "value": 234.5, "unit": "TRY" },
                { "code": "UNRELATED", "label": "Not selected", "value": 99, "unit": null }
              ]
            },
            {
              "id": "marketing-insight", "type": "CHANGE", "metric": "MarketingSpend",
              "dimension": null, "segment": null, "period": { "previous": "2025-05", "current": "2025-06" },
              "direction": "UP", "values": { "percentageChange": 20 },
              "evidence": [{ "code": "MARKETING_CHANGE", "label": "Marketing change", "value": 20, "unit": "%" }]
            },
            {
              "id": "unselected-insight", "type": "CHANGE", "metric": "Orders",
              "dimension": null, "segment": null, "period": { "previous": "2025-05", "current": "2025-06" },
              "direction": "DOWN", "values": { "percentageChange": -15 },
              "evidence": []
            }
          ],
          "insightIntegrity": [
            { "insightId": "revenue-insight", "reasons": ["Interpret with qualification."] },
            { "insightId": "marketing-insight", "reasons": [] }
          ],
          "storyPlan": {
            "analysisId": "analysis-1", "plannerVersion": "day12-v1",
            "mainOutcome": {
              "id": "main-item", "role": "MAIN_OUTCOME", "insightId": "revenue-insight",
              "evidenceCodes": ["REVENUE_CHANGE"], "requiresQualification": true
            },
            "context": [], "contributors": [], "secondaryFindings": [], "counterSignals": [],
            "associatedSignals": [{
              "id": "associated-item", "role": "ASSOCIATED_SIGNAL", "insightId": "marketing-insight",
              "evidenceCodes": ["MARKETING_CHANGE"], "requiresQualification": false
            }],
            "risks": [],
            "missingContext": [{
              "id": "missing-item", "role": "MISSING_CONTEXT", "insightId": "revenue-insight",
              "field": "CompetitorPrice", "status": "NOT_AVAILABLE", "isDataQualityError": false,
              "reason": "Competitor pricing is unavailable."
            }],
            "causalityConstraints": [{
              "relationshipId": "relationship-1", "sourceInsightId": "marketing-insight",
              "targetInsightId": "revenue-insight", "claimType": "CORRELATIONAL",
              "associationPresent": true, "causalityEstablished": false,
              "status": "CAUSALITY_NOT_ESTABLISHED", "allowedConcepts": ["ASSOCIATED_WITH"],
              "forbiddenConcepts": ["CAUSED", "LED_TO"], "reasons": ["Causality is not established."]
            }],
            "outline": [
              { "order": 1, "type": "OUTCOME", "itemIds": ["main-item"] },
              { "order": 2, "type": "ASSOCIATED_SIGNALS", "itemIds": ["associated-item"] },
              { "order": 3, "type": "LIMITATIONS", "itemIds": ["missing-item"] }
            ],
            "interpretationLimited": true
          }
        }
        """;
        return JsonDocument.Parse(transform?.Invoke(json) ?? json);
    }
}
