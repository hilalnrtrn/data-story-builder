using System.Text.Json;
using System.Text.Json.Nodes;
using DataStoryBuilder.Api;
using DataStoryBuilder.Application.Stories;
using DataStoryBuilder.Infrastructure.Generation;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Options;
using Xunit;

namespace DataStoryBuilder.Application.Tests.Stories;

public sealed class AnalysisStoryGenerationTests
{
    [Fact]
    public async Task SuccessAddsGeneratedStoryAndPreservesAnalyticsAndStoryPlan()
    {
        var client = new FakeLlmClient(ValidStoryJson);
        var service = CreateService(client);

        var output = (await service.GenerateAndComposeAsync(AnalyticsJson)).ResponseJson;

        using var original = JsonDocument.Parse(AnalyticsJson);
        using var result = JsonDocument.Parse(output);
        Assert.Equal(
            original.RootElement.GetProperty("existingField").GetRawText(),
            result.RootElement.GetProperty("existingField").GetRawText());
        Assert.True(JsonNode.DeepEquals(
            JsonNode.Parse(original.RootElement.GetProperty("storyPlan").GetRawText()),
            JsonNode.Parse(result.RootElement.GetProperty("storyPlan").GetRawText())));
        Assert.Equal(
            "Revenue overview",
            result.RootElement.GetProperty("generatedStory").GetProperty("title").GetString());
        Assert.Equal(
            "Succeeded",
            result.RootElement.GetProperty("storyGeneration").GetProperty("status").GetString());
        Assert.Equal(1, client.CallCount);
        Assert.Contains("REVENUE_CHANGE", client.Prompt);
        Assert.DoesNotContain("RAW_FILE_BYTES", client.Prompt);
    }

    [Theory]
    [InlineData(LlmClientError.Timeout, "Timeout")]
    [InlineData(LlmClientError.RateLimited, "RateLimited")]
    [InlineData(LlmClientError.ProviderUnavailable, "ProviderUnavailable")]
    public async Task ProviderFailureDoesNotRemoveAnalytics(
        LlmClientError error,
        string expectedCategory)
    {
        var client = new FakeLlmClient(new LlmClientException(error, "provider detail"));
        using var result = JsonDocument.Parse(
            (await CreateService(client).GenerateAndComposeAsync(AnalyticsJson)).ResponseJson);

        Assert.Equal(42, result.RootElement.GetProperty("existingField").GetInt32());
        Assert.Equal(JsonValueKind.Null, result.RootElement.GetProperty("generatedStory").ValueKind);
        var generation = result.RootElement.GetProperty("storyGeneration");
        Assert.Equal("Failed", generation.GetProperty("status").GetString());
        Assert.Equal(expectedCategory, generation.GetProperty("failureCategory").GetString());
        Assert.Equal(1, client.CallCount);
    }

    [Fact]
    public async Task SafetyRejectionReturnsAnalyticsAndNoGeneratedStory()
    {
        var client = new FakeLlmClient(
            ValidStoryJson.Replace("moved alongside Revenue", "caused Revenue growth"));
        using var result = JsonDocument.Parse(
            (await CreateService(client).GenerateAndComposeAsync(AnalyticsJson)).ResponseJson);

        Assert.Equal(42, result.RootElement.GetProperty("existingField").GetInt32());
        Assert.Equal(JsonValueKind.Null, result.RootElement.GetProperty("generatedStory").ValueKind);
        Assert.Equal(
            "SafetyRejected",
            result.RootElement.GetProperty("storyGeneration")
                .GetProperty("failureCategory").GetString());
        Assert.Equal(1, client.CallCount);
    }

    [Fact]
    public async Task GroundingFailureOccursBeforeProviderUse()
    {
        var client = new FakeLlmClient(ValidStoryJson);
        var inconsistent = AnalyticsJson.Replace(
            "\"id\":\"revenue-insight\"",
            "\"id\":\"missing-insight\"");
        using var result = JsonDocument.Parse(
            (await CreateService(client).GenerateAndComposeAsync(inconsistent)).ResponseJson);

        Assert.Equal(
            "GroundingPreconditionFailed",
            result.RootElement.GetProperty("storyGeneration")
                .GetProperty("failureCategory").GetString());
        Assert.Equal(0, client.CallCount);
    }

    [Fact]
    public async Task MissingConfigurationReturnsControlledFailureWithoutResolvingClient()
    {
        var services = new ServiceCollection().BuildServiceProvider();
        var service = new AnalysisStoryGeneration(
            Options.Create(new LlmOptions()),
            services);

        using var result = JsonDocument.Parse(
            (await service.GenerateAndComposeAsync(AnalyticsJson)).ResponseJson);

        Assert.Equal(42, result.RootElement.GetProperty("existingField").GetInt32());
        Assert.Equal(
            "ProviderUnavailable",
            result.RootElement.GetProperty("storyGeneration")
                .GetProperty("failureCategory").GetString());
    }

    [Fact]
    public async Task CallerCancellationPropagates()
    {
        using var cancellation = new CancellationTokenSource();
        cancellation.Cancel();
        var client = new FakeLlmClient(new OperationCanceledException(cancellation.Token));

        await Assert.ThrowsAnyAsync<OperationCanceledException>(() =>
            CreateService(client).GenerateAndComposeAsync(
                AnalyticsJson,
                cancellation.Token));
    }

    private static AnalysisStoryGeneration CreateService(FakeLlmClient client)
    {
        var services = new ServiceCollection()
            .AddSingleton<ILlmClient>(client)
            .AddSingleton<GroundedPromptBuilder>()
            .AddSingleton<GeneratedStorySafetyValidator>()
            .AddSingleton<StoryGenerator>()
            .BuildServiceProvider();
        return new AnalysisStoryGeneration(
            Options.Create(new LlmOptions
            {
                Model = "test-model",
                ApiKey = "test-key",
                TimeoutSeconds = 60,
                PromptVersion = "day13-v1"
            }),
            services);
    }

    private const string AnalyticsJson =
        """
        {
          "existingField":42,
          "insights":[
            {"id":"revenue-insight","type":"CHANGE","metric":"Revenue","dimension":null,"segment":null,"period":{"previous":"2025-05","current":"2025-06"},"direction":"UP","values":{"previous":1000,"current":1234.5},"evidence":[{"code":"REVENUE_CHANGE","label":"Revenue change","value":234.5,"unit":"TRY"}]},
            {"id":"marketing-insight","type":"CHANGE","metric":"MarketingSpend","dimension":null,"segment":null,"period":{"previous":"2025-05","current":"2025-06"},"direction":"UP","values":{"percentageChange":20},"evidence":[{"code":"MARKETING_CHANGE","label":"Marketing change","value":20,"unit":"%"}]}
          ],
          "insightIntegrity":[{"insightId":"revenue-insight","reasons":[]},{"insightId":"marketing-insight","reasons":[]}],
          "storyPlan":{
            "analysisId":"analysis-1","plannerVersion":"day12-v1",
            "mainOutcome":{"id":"main-item","role":"MAIN_OUTCOME","insightId":"revenue-insight","evidenceCodes":["REVENUE_CHANGE"],"requiresQualification":false},
            "context":[],"contributors":[],"secondaryFindings":[],"counterSignals":[],
            "associatedSignals":[{"id":"associated-item","role":"ASSOCIATED_SIGNAL","insightId":"marketing-insight","evidenceCodes":["MARKETING_CHANGE"],"requiresQualification":false}],"risks":[],
            "missingContext":[{"id":"missing-item","role":"MISSING_CONTEXT","insightId":"revenue-insight","field":"CompetitorPrice","status":"NOT_AVAILABLE","isDataQualityError":false,"reason":"Competitor pricing is unavailable."}],
            "causalityConstraints":[{"relationshipId":"relationship-1","sourceInsightId":"marketing-insight","targetInsightId":"revenue-insight","claimType":"CORRELATIONAL","associationPresent":true,"causalityEstablished":false,"status":"CAUSALITY_NOT_ESTABLISHED","allowedConcepts":["ASSOCIATED_WITH"],"forbiddenConcepts":["CAUSED","LED_TO","BECAUSE_OF","RESULTED_IN","DRIVEN_BY"],"reasons":["Causality is not established."]}],
            "outline":[{"order":1,"type":"OUTCOME","itemIds":["main-item"]},{"order":2,"type":"ASSOCIATED_SIGNALS","itemIds":["associated-item"]},{"order":3,"type":"LIMITATIONS","itemIds":["missing-item"]}],
            "interpretationLimited":true
          }
        }
        """;

    private const string ValidStoryJson =
        "{\"title\":\"Revenue overview\",\"executiveSummary\":\"Revenue changed while MarketingSpend moved alongside Revenue.\",\"sections\":[{\"order\":1,\"type\":\"OUTCOME\",\"items\":[{\"sourceItemId\":\"main-item\",\"text\":\"Revenue changed.\"}]},{\"order\":2,\"type\":\"ASSOCIATED_SIGNALS\",\"items\":[{\"sourceItemId\":\"associated-item\",\"text\":\"MarketingSpend moved alongside Revenue.\"}]},{\"order\":3,\"type\":\"LIMITATIONS\",\"items\":[{\"sourceItemId\":\"missing-item\",\"text\":\"CompetitorPrice is unavailable.\"}]}]}";

    private sealed class FakeLlmClient : ILlmClient
    {
        private readonly string? response;
        private readonly Exception? exception;

        public FakeLlmClient(string response) => this.response = response;
        public FakeLlmClient(Exception exception) => this.exception = exception;

        public int CallCount { get; private set; }
        public string Prompt { get; private set; } = string.Empty;

        public Task<string> GenerateStructuredAsync(
            string groundedPrompt,
            string jsonSchema,
            CancellationToken cancellationToken = default)
        {
            CallCount++;
            Prompt = groundedPrompt;
            return exception is null
                ? Task.FromResult(response!)
                : Task.FromException<string>(exception);
        }
    }
}
