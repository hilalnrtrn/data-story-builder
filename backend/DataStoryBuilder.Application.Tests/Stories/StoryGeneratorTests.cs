using System.Text.Json;
using DataStoryBuilder.Application.Stories;
using Xunit;

namespace DataStoryBuilder.Application.Tests.Stories;

public sealed class StoryGeneratorTests
{
    [Fact]
    public async Task ValidAnalyticsResponseProducesSuccessfulStory()
    {
        var client = new FakeLlmClient(ValidStoryJson);
        var result = await CreateGenerator(client).GenerateAsync(Parse().RootElement);

        Assert.True(result.IsSuccess);
        Assert.NotNull(result.Story);
        Assert.Equal("Revenue overview", result.Story.Title);
        Assert.Null(result.Failure);
        Assert.Null(result.FailureReason);
    }

    [Fact]
    public async Task ProjectedFactsReachPromptAndFullPayloadDoesNot()
    {
        var client = new FakeLlmClient(ValidStoryJson);
        await CreateGenerator(client).GenerateAsync(Parse().RootElement);

        Assert.Contains("REVENUE_CHANGE", client.Prompt);
        Assert.Contains("1234.5", client.Prompt);
        Assert.DoesNotContain("SECRET_RAW_ROW", client.Prompt);
        Assert.DoesNotContain("rawSchema", client.Prompt);
    }

    [Fact]
    public async Task ExactGeneratedStorySchemaIsPassedToClient()
    {
        var client = new FakeLlmClient(ValidStoryJson);
        await CreateGenerator(client).GenerateAsync(Parse().RootElement);
        Assert.Equal(GeneratedExecutiveStorySchema.Build(), client.Schema);
    }

    [Fact]
    public async Task UnknownSourceItemIdIsSafetyRejected()
    {
        var json = ValidStoryJson.Replace("main-item", "unknown-item");
        var result = await CreateGenerator(new(json)).GenerateAsync(Parse().RootElement);
        AssertFailure(result, StoryGenerationFailure.SafetyRejected);
    }

    [Fact]
    public async Task ForbiddenCausalWordingIsSafetyRejected()
    {
        var json = ValidStoryJson.Replace(
            "moved alongside Revenue",
            "caused Revenue growth");
        var client = new FakeLlmClient(json);
        var result = await CreateGenerator(client).GenerateAsync(Parse().RootElement);
        AssertFailure(result, StoryGenerationFailure.SafetyRejected);
        Assert.Equal(1, client.CallCount);
    }

    [Fact]
    public async Task MissingRequiredLimitationIsSafetyRejected()
    {
        var json = ValidStoryJson.Replace(
            ",{" + "\"order\":3,\"type\":\"LIMITATIONS\",\"items\":[{\"sourceItemId\":\"missing-item\",\"text\":\"CompetitorPrice is unavailable.\"}]}",
            "");
        var result = await CreateGenerator(new(json)).GenerateAsync(Parse().RootElement);
        AssertFailure(result, StoryGenerationFailure.SafetyRejected);
    }

    [Theory]
    [InlineData(LlmClientError.Timeout, StoryGenerationFailure.Timeout)]
    [InlineData(LlmClientError.RateLimited, StoryGenerationFailure.RateLimited)]
    [InlineData(LlmClientError.ProviderUnavailable, StoryGenerationFailure.ProviderUnavailable)]
    [InlineData(LlmClientError.InvalidProviderResponse, StoryGenerationFailure.InvalidProviderResponse)]
    public async Task ProviderFailuresAreMapped(
        LlmClientError clientError,
        StoryGenerationFailure expected)
    {
        var client = new FakeLlmClient(new LlmClientException(
            clientError,
            "sensitive provider detail SECRET_RAW_BODY grounded prompt"));
        var result = await CreateGenerator(client).GenerateAsync(Parse().RootElement);

        AssertFailure(result, expected);
        Assert.DoesNotContain("sensitive", result.FailureReason);
        Assert.DoesNotContain("SECRET_RAW_BODY", result.FailureReason);
        Assert.DoesNotContain("grounded prompt", result.FailureReason);
        Assert.Equal(1, client.CallCount);
    }

    [Theory]
    [InlineData("not json")]
    [InlineData("null")]
    [InlineData("{\"title\":\"Title\",\"executiveSummary\":\"Summary\",\"sections\":[]}")]
    public async Task MalformedNullOrStructurallyUnusableJsonIsInvalidProviderResponse(string json)
    {
        var client = new FakeLlmClient(json);
        var result = await CreateGenerator(client).GenerateAsync(Parse().RootElement);
        AssertFailure(result, StoryGenerationFailure.InvalidProviderResponse);
        Assert.Equal(1, client.CallCount);
    }

    [Theory]
    [InlineData("\"insightId\":\"revenue-insight\"", "\"insightId\":\"missing-insight\"")]
    [InlineData("REVENUE_CHANGE\"]", "MISSING_EVIDENCE\"]")]
    public async Task MissingGroundingReferenceIsGroundingPreconditionFailure(
        string oldValue,
        string newValue)
    {
        var result = await CreateGenerator(new(ValidStoryJson)).GenerateAsync(
            Parse(json => json.Replace(oldValue, newValue)).RootElement);
        AssertFailure(result, StoryGenerationFailure.GroundingPreconditionFailed);
    }

    [Fact]
    public async Task DuplicateGroundingReferenceIsGroundingPreconditionFailure()
    {
        var result = await CreateGenerator(new(ValidStoryJson)).GenerateAsync(
            Parse(json => json.Replace("\"associated-item\"", "\"main-item\"")).RootElement);
        AssertFailure(result, StoryGenerationFailure.GroundingPreconditionFailed);
    }

    [Fact]
    public async Task CallerCancellationPropagates()
    {
        using var cancellation = new CancellationTokenSource();
        cancellation.Cancel();
        var client = new FakeLlmClient(new OperationCanceledException(cancellation.Token));

        await Assert.ThrowsAnyAsync<OperationCanceledException>(() =>
            CreateGenerator(client).GenerateAsync(Parse().RootElement, cancellation.Token));
    }

    [Fact]
    public async Task IdenticalInputProducesIdenticalPrompt()
    {
        var first = new FakeLlmClient(ValidStoryJson);
        var second = new FakeLlmClient(ValidStoryJson);
        await CreateGenerator(first).GenerateAsync(Parse().RootElement);
        await CreateGenerator(second).GenerateAsync(Parse().RootElement);
        Assert.Equal(first.Prompt, second.Prompt);
    }

    [Fact]
    public async Task UnexpectedClientFailureRemainsVisibleAndIdentifiesLlmCallBoundary()
    {
        var substages = new List<(string Substage, string State)>();
        var client = new FakeLlmClient(new InvalidOperationException("test defect"));

        await Assert.ThrowsAsync<InvalidOperationException>(() =>
            CreateGenerator(client).GenerateAsync(
                Parse().RootElement,
                (substage, state) => substages.Add((substage, state))));

        Assert.Equal(("llm-call", "started"), substages[^1]);
        Assert.Equal(1, client.CallCount);
    }

    private static StoryGenerator CreateGenerator(FakeLlmClient client) =>
        new(client, new GroundedPromptBuilder(), new GeneratedStorySafetyValidator());

    private static void AssertFailure(
        StoryGenerationResult result,
        StoryGenerationFailure failure)
    {
        Assert.False(result.IsSuccess);
        Assert.Null(result.Story);
        Assert.Equal(failure, result.Failure);
        Assert.False(string.IsNullOrWhiteSpace(result.FailureReason));
        Assert.True(result.FailureReason.Length < 200);
    }

    private static JsonDocument Parse(Func<string, string>? transform = null)
    {
        var json = """
        {
          "rawSchema":{"rows":["SECRET_RAW_ROW"]},
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
        return JsonDocument.Parse(transform?.Invoke(json) ?? json);
    }

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
        public string Schema { get; private set; } = string.Empty;

        public Task<string> GenerateStructuredAsync(
            string groundedPrompt,
            string jsonSchema,
            CancellationToken cancellationToken = default)
        {
            CallCount++;
            Prompt = groundedPrompt;
            Schema = jsonSchema;
            return exception is null
                ? Task.FromResult(response!)
                : Task.FromException<string>(exception);
        }
    }
}
