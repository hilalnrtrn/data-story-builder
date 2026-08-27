using System.Text.Json;
using DataStoryBuilder.Application.Stories;
using Xunit;

namespace DataStoryBuilder.Application.Tests.Stories;

public sealed class GoldenStoryGenerationTests
{
    [Fact]
    public async Task NovaRetailGoldenPlanGeneratesGroundedExecutiveStory()
    {
        var client = new FakeLlmClient(GoldenGeneratedStoryJson());
        var generator = CreateGenerator(client);
        using var analytics = JsonDocument.Parse(GoldenAnalyticsJson());

        var result = await generator.GenerateAsync(analytics.RootElement);

        Assert.True(result.IsSuccess);
        Assert.NotNull(result.Story);
        Assert.Equal(1, client.CallCount);

        var outline = analytics.RootElement.GetProperty("storyPlan")
            .GetProperty("outline").EnumerateArray().ToArray();
        Assert.Equal(outline.Length, result.Story.Sections.Count);
        Assert.Equal(
            outline.Select(item => item.GetProperty("order").GetInt32()),
            result.Story.Sections.Select(item => item.Order));
        Assert.Equal(
            outline.Select(item => item.GetProperty("type").GetString()),
            result.Story.Sections.Select(item => item.Type));

        var expectedIds = outline
            .SelectMany(item => item.GetProperty("itemIds").EnumerateArray())
            .Select(item => item.GetString()!)
            .ToArray();
        var actualIds = result.Story.Sections
            .SelectMany(section => section.Items)
            .Select(item => item.SourceItemId)
            .ToArray();
        Assert.Equal(expectedIds, actualIds);
        Assert.DoesNotContain("unselected-item", actualIds);

        Assert.Contains(MainId, actualIds);
        Assert.Contains(MarmaraId, actualIds);
        Assert.Contains(OnlineId, actualIds);
        Assert.Contains(OrdersId, actualIds);
        Assert.Contains(CustomersId, actualIds);
        Assert.Contains(MarketingId, actualIds);
        Assert.Contains(RiskId, actualIds);
        Assert.Contains(CompetitorPriceId, actualIds);
        Assert.Contains(UnitPriceId, actualIds);

        var constraint = analytics.RootElement.GetProperty("storyPlan")
            .GetProperty("causalityConstraints")[0];
        Assert.False(constraint.GetProperty("causalityEstablished").GetBoolean());
        Assert.Equal(
            "CAUSALITY_NOT_ESTABLISHED",
            constraint.GetProperty("status").GetString());

        var generatedText = JsonSerializer.Serialize(result.Story);
        foreach (var phrase in new[]
        {
            "caused", "led to", "because of", "resulted in", "driven by"
        })
        {
            Assert.DoesNotContain(phrase, generatedText, StringComparison.OrdinalIgnoreCase);
        }

        AssertPromptIsGoldenGrounded(client.Prompt);

        var persistedJson = JsonSerializer.Serialize(
            result.Story,
            new JsonSerializerOptions(JsonSerializerDefaults.Web));
        var reloaded = JsonSerializer.Deserialize<GeneratedExecutiveStory>(
            persistedJson,
            new JsonSerializerOptions(JsonSerializerDefaults.Web));
        Assert.Equal(
            result.Story.Sections.SelectMany(section => section.Items).Select(item => item.Text),
            reloaded!.Sections.SelectMany(section => section.Items).Select(item => item.Text));
    }

    [Fact]
    public async Task GoldenGenerationIsDeterministic()
    {
        var firstClient = new FakeLlmClient(GoldenGeneratedStoryJson());
        var secondClient = new FakeLlmClient(GoldenGeneratedStoryJson());
        using var firstInput = JsonDocument.Parse(GoldenAnalyticsJson());
        using var secondInput = JsonDocument.Parse(GoldenAnalyticsJson());

        var first = await CreateGenerator(firstClient).GenerateAsync(firstInput.RootElement);
        var second = await CreateGenerator(secondClient).GenerateAsync(secondInput.RootElement);

        Assert.True(first.IsSuccess);
        Assert.True(second.IsSuccess);
        Assert.Equal(firstClient.Prompt, secondClient.Prompt);
        Assert.Equal(
            JsonSerializer.Serialize(first.Story),
            JsonSerializer.Serialize(second.Story));
        Assert.Equal(1, firstClient.CallCount);
        Assert.Equal(1, secondClient.CallCount);
    }

    private static void AssertPromptIsGoldenGrounded(string prompt)
    {
        Assert.Contains("Revenue", prompt);
        Assert.Contains("\"percentageChange\": 30", prompt);
        Assert.Contains("Marmara", prompt);
        Assert.Contains("\"contributionShare\": 0.7", prompt);
        Assert.Contains("Orders", prompt);
        Assert.Contains("\"percentageChange\": -15", prompt);
        Assert.Contains("Customers", prompt);
        Assert.Contains("\"percentageChange\": -12", prompt);
        Assert.Contains("MarketingSpend", prompt);
        Assert.Contains("\"percentageChange\": 20", prompt);
        Assert.Contains("CAUSALITY_NOT_ESTABLISHED", prompt);
        Assert.Contains("CAUSED", prompt);
        Assert.Contains("CompetitorPrice", prompt);
        Assert.Contains("UnitPrice", prompt);
        Assert.DoesNotContain("raw CSV", prompt, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("RAW_FILE_BYTES", prompt);
        Assert.DoesNotContain("Customer Satisfaction", prompt);
        Assert.DoesNotContain("unselected-insight", prompt);
    }

    private static StoryGenerator CreateGenerator(FakeLlmClient client) =>
        new(client, new GroundedPromptBuilder(), new GeneratedStorySafetyValidator());

    internal static string GoldenAnalyticsJson()
    {
        var insights = new object[]
        {
            ChangeInsight("CHANGE-Revenue-2025-05-2025-06", "Revenue", 1_000_000, 1_300_000, 300_000, 30),
            ContributionInsight("CONTRIBUTION-Revenue-Region-Marmara-2025-05-2025-06", "Region", "Marmara", 380_000, 590_000, 210_000, 0.7),
            ContributionInsight("CONTRIBUTION-Revenue-Channel-Online-2025-05-2025-06", "Channel", "Online", 550_000, 780_000, 230_000, 0.766667),
            ChangeInsight("CHANGE-Orders-2025-05-2025-06", "Orders", 10_000, 8_500, -1_500, -15),
            ChangeInsight("CHANGE-Customers-2025-05-2025-06", "Customers", 8_000, 7_040, -960, -12),
            ChangeInsight("CHANGE-MarketingSpend-2025-05-2025-06", "MarketingSpend", 100_000, 120_000, 20_000, 20),
            AnomalyInsight()
        };

        var plan = new
        {
            analysisId = "DAY12-STORY-PLANNER-GOLDEN",
            mainOutcome = PlanItem(MainId, "MAIN_OUTCOME", "CHANGE-Revenue-2025-05-2025-06", ChangeEvidence, true),
            context = Array.Empty<object>(),
            contributors = new[] { PlanItem(MarmaraId, "PRIMARY_CONTRIBUTOR", "CONTRIBUTION-Revenue-Region-Marmara-2025-05-2025-06", ContributionEvidence, false) },
            secondaryFindings = new[] { PlanItem(OnlineId, "SECONDARY_FINDING", "CONTRIBUTION-Revenue-Channel-Online-2025-05-2025-06", ContributionEvidence, false) },
            counterSignals = new[]
            {
                PlanItem(OrdersId, "COUNTER_SIGNAL", "CHANGE-Orders-2025-05-2025-06", ChangeEvidence, true),
                PlanItem(CustomersId, "COUNTER_SIGNAL", "CHANGE-Customers-2025-05-2025-06", ChangeEvidence, true)
            },
            associatedSignals = new[] { PlanItem(MarketingId, "ASSOCIATED_SIGNAL", "CHANGE-MarketingSpend-2025-05-2025-06", ChangeEvidence, false) },
            risks = new[] { PlanItem(RiskId, "RISK", "ANOMALY-Revenue-Product-Smart Watch-2025-06", AnomalyEvidence, true) },
            missingContext = new object[]
            {
                new { id = CompetitorPriceId, role = "MISSING_CONTEXT", insightId = "CHANGE-Revenue-2025-05-2025-06", field = "CompetitorPrice", status = "NOT_AVAILABLE", isDataQualityError = false, reason = "Competitor pricing may affect interpretation of Revenue movements." },
                new { id = UnitPriceId, role = "MISSING_CONTEXT", insightId = "CHANGE-Revenue-2025-05-2025-06", field = "UnitPrice", status = "NOT_AVAILABLE", isDataQualityError = false, reason = "AverageOrderValue growth does not establish that individual selling prices increased." }
            },
            causalityConstraints = new[]
            {
                new
                {
                    relationshipId = "CO_MOVES_WITH-CHANGE-MarketingSpend-2025-05-2025-06-CHANGE-Revenue-2025-05-2025-06",
                    sourceInsightId = "CHANGE-MarketingSpend-2025-05-2025-06",
                    targetInsightId = "CHANGE-Revenue-2025-05-2025-06",
                    claimType = "CORRELATIONAL",
                    associationPresent = true,
                    causalityEstablished = false,
                    status = "CAUSALITY_NOT_ESTABLISHED",
                    allowedConcepts = new[] { "ASSOCIATED_WITH", "COINCIDED_WITH", "MOVED_ALONGSIDE" },
                    forbiddenConcepts = new[] { "CAUSED", "LED_TO", "BECAUSE_OF", "RESULTED_IN", "DRIVEN_BY" },
                    reasons = new[] { "CO_MOVES_WITH is association evidence and does not establish causality on its own." }
                }
            },
            outline = new object[]
            {
                Section(1, "OUTCOME", MainId),
                Section(2, "CONTRIBUTION", MarmaraId),
                Section(3, "SECONDARY_FINDINGS", OnlineId),
                Section(4, "COUNTER_SIGNALS", OrdersId, CustomersId),
                Section(5, "ASSOCIATED_SIGNALS", MarketingId),
                Section(6, "RISKS", RiskId),
                Section(7, "LIMITATIONS", CompetitorPriceId, UnitPriceId)
            },
            interpretationLimited = true,
            plannerVersion = "day12-v1"
        };

        var integrity = insights.Select(item =>
        {
            using var json = JsonDocument.Parse(JsonSerializer.Serialize(item));
            return new
            {
                insightId = json.RootElement.GetProperty("id").GetString(),
                reasons = new[] { "Interpret with the supplied qualification." }
            };
        }).ToArray();

        return JsonSerializer.Serialize(new
        {
            rawFile = "RAW_FILE_BYTES",
            insights,
            insightIntegrity = integrity,
            storyPlan = plan
        });
    }

    private static object ChangeInsight(
        string id,
        string metric,
        double previous,
        double current,
        double absoluteChange,
        double percentageChange) =>
        new
        {
            id,
            type = "CHANGE",
            metric,
            dimension = (string?)null,
            segment = (string?)null,
            period = new { previous = "2025-05", current = "2025-06" },
            direction = percentageChange >= 0 ? "UP" : "DOWN",
            values = new { previous, current, absoluteChange, percentageChange },
            evidence = new object[]
            {
                Evidence("PREVIOUS_PERIOD_VALUE", "Previous period value", previous),
                Evidence("CURRENT_PERIOD_VALUE", "Current period value", current),
                Evidence("ABSOLUTE_CHANGE", "Absolute change", absoluteChange),
                Evidence("PERCENTAGE_CHANGE", "Percentage change", percentageChange, "PERCENT")
            }
        };

    private static object ContributionInsight(
        string id,
        string dimension,
        string segment,
        double previous,
        double current,
        double absoluteChange,
        double contributionShare) =>
        new
        {
            id,
            type = "CONTRIBUTION",
            metric = "Revenue",
            dimension,
            segment,
            period = new { previous = "2025-05", current = "2025-06" },
            direction = "UP",
            values = new
            {
                segmentPreviousValue = previous,
                segmentCurrentValue = current,
                segmentAbsoluteChange = absoluteChange,
                totalAbsoluteChange = 300_000,
                contributionShare,
                contributorRole = "PRIMARY_POSITIVE_CONTRIBUTOR"
            },
            evidence = new object[]
            {
                Evidence("SEGMENT_PREVIOUS_VALUE", "Segment previous period value", previous),
                Evidence("SEGMENT_CURRENT_VALUE", "Segment current period value", current),
                Evidence("SEGMENT_ABSOLUTE_CHANGE", "Segment absolute change", absoluteChange),
                Evidence("TOTAL_ABSOLUTE_CHANGE", "Total absolute change", 300_000),
                Evidence("CONTRIBUTION_SHARE", "Contribution share", contributionShare, "RATIO"),
                Evidence("CONTRIBUTOR_ROLE", "Contributor role", "PRIMARY_POSITIVE_CONTRIBUTOR")
            }
        };

    private static object AnomalyInsight() => new
    {
        id = "ANOMALY-Revenue-Product-Smart Watch-2025-06",
        type = "ANOMALY",
        metric = "Revenue",
        dimension = "Product",
        segment = "Smart Watch",
        period = new { current = "2025-06" },
        direction = "HIGH",
        values = new { observed = 145_000, q1 = 72_500, q3 = 76_500, lowerBound = 64_500, upperBound = 84_500 },
        evidence = new object[]
        {
            Evidence("OBSERVED_VALUE", "Observed period value", 145_000),
            Evidence("IQR_Q1", "Historical first quartile", 72_500),
            Evidence("IQR_Q3", "Historical third quartile", 76_500),
            Evidence("IQR_LOWER_BOUND", "Lower anomaly bound", 64_500),
            Evidence("IQR_UPPER_BOUND", "Upper anomaly bound", 84_500)
        }
    };

    private static object Evidence(string code, string label, object value, string? unit = null) =>
        new { code, label, value, unit };

    private static object PlanItem(
        string id,
        string role,
        string insightId,
        string[] evidenceCodes,
        bool requiresQualification) =>
        new { id, role, insightId, evidenceCodes, requiresQualification };

    private static object Section(int order, string type, params string[] itemIds) =>
        new { order, type, itemIds };

    internal static string GoldenGeneratedStoryJson()
    {
        object Item(string sourceItemId, string text) => new { sourceItemId, text };
        object SectionJson(int order, string type, params object[] items) =>
            new { order, type, items };

        return JsonSerializer.Serialize(new
        {
            title = "NovaRetail May to June revenue overview",
            executiveSummary = "Revenue increased while Orders and Customers declined; MarketingSpend moved alongside Revenue during the same period, and causality is not established.",
            sections = new object[]
            {
                SectionJson(1, "OUTCOME", Item(MainId, "Revenue moved from 1,000,000 to 1,300,000, an increase of 300,000 or 30%.")),
                SectionJson(2, "CONTRIBUTION", Item(MarmaraId, "Marmara Revenue moved from 380,000 to 590,000 and represented 70% of the total absolute Revenue change.")),
                SectionJson(3, "SECONDARY_FINDINGS", Item(OnlineId, "Online Revenue moved from 550,000 to 780,000, an increase of 230,000.")),
                SectionJson(4, "COUNTER_SIGNALS", Item(OrdersId, "Orders moved from 10,000 to 8,500, a decline of 15%."), Item(CustomersId, "Customers moved from 8,000 to 7,040, a decline of 12%.")),
                SectionJson(5, "ASSOCIATED_SIGNALS", Item(MarketingId, "MarketingSpend moved from 100,000 to 120,000 and moved alongside Revenue; causality is not established.")),
                SectionJson(6, "RISKS", Item(RiskId, "Smart Watch Revenue was a high June anomaly at 145,000 and requires qualification.")),
                SectionJson(7, "LIMITATIONS", Item(CompetitorPriceId, "CompetitorPrice is unavailable as contextual information."), Item(UnitPriceId, "UnitPrice is unavailable, so individual selling-price movement is not established."))
            }
        });
    }

    private static readonly string[] ChangeEvidence =
        ["PREVIOUS_PERIOD_VALUE", "CURRENT_PERIOD_VALUE", "ABSOLUTE_CHANGE", "PERCENTAGE_CHANGE"];
    private static readonly string[] ContributionEvidence =
        ["SEGMENT_PREVIOUS_VALUE", "SEGMENT_CURRENT_VALUE", "SEGMENT_ABSOLUTE_CHANGE", "TOTAL_ABSOLUTE_CHANGE", "CONTRIBUTION_SHARE", "CONTRIBUTOR_ROLE"];
    private static readonly string[] AnomalyEvidence =
        ["OBSERVED_VALUE", "IQR_Q1", "IQR_Q3", "IQR_LOWER_BOUND", "IQR_UPPER_BOUND"];

    private const string MainId = "main_outcome-CHANGE-Revenue-2025-05-2025-06";
    private const string MarmaraId = "primary_contributor-CONTRIBUTION-Revenue-Region-Marmara-2025-05-2025-06";
    private const string OnlineId = "secondary_finding-CONTRIBUTION-Revenue-Channel-Online-2025-05-2025-06";
    private const string OrdersId = "counter_signal-CHANGE-Orders-2025-05-2025-06";
    private const string CustomersId = "counter_signal-CHANGE-Customers-2025-05-2025-06";
    private const string MarketingId = "associated_signal-CHANGE-MarketingSpend-2025-05-2025-06";
    private const string RiskId = "risk-ANOMALY-Revenue-Product-Smart Watch-2025-06";
    private const string CompetitorPriceId = "missing_context-CHANGE-Revenue-2025-05-2025-06-competitorprice";
    private const string UnitPriceId = "missing_context-CHANGE-Revenue-2025-05-2025-06-unitprice";

    private sealed class FakeLlmClient(string response) : ILlmClient
    {
        public int CallCount { get; private set; }
        public string Prompt { get; private set; } = string.Empty;

        public Task<string> GenerateStructuredAsync(
            string groundedPrompt,
            string jsonSchema,
            CancellationToken cancellationToken = default)
        {
            CallCount++;
            Prompt = groundedPrompt;
            return Task.FromResult(response);
        }
    }
}
