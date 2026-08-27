using System.Text.Json;
using System.Text.Json.Nodes;
using DataStoryBuilder.Application.Stories;
using Xunit;

namespace DataStoryBuilder.Application.Tests.Stories;

public sealed class GeneratedStoryAdversarialTests
{
    [Theory]
    [InlineData("Marketing spend caused revenue growth.")]
    [InlineData("Revenue growth was driven by higher marketing spend.")]
    [InlineData("Revenue increased because of marketing spend.")]
    [InlineData("Marketing spend led to revenue growth.")]
    [InlineData("Marketing spend resulted in revenue growth.")]
    [InlineData("MARKETING SPEND CAUSED REVENUE GROWTH.")]
    [InlineData("The Marmara region drove the revenue increase.")]
    [InlineData("THE MARMARA REGION DROVE THE REVENUE INCREASE.")]
    public async Task ForbiddenGoldenCausalClaimsAreSafetyRejected(string text)
    {
        var output = MutateStory(root => Item(root, 4, 0)["text"] = text);
        var (result, client) = await Generate(output);

        AssertRejected(result, StoryGenerationFailure.SafetyRejected);
        Assert.Equal(1, client.CallCount);
    }

    [Fact]
    public async Task InventedSourceItemIdIsRejected()
    {
        var output = MutateStory(root =>
            Item(root, 0, 0)["sourceItemId"] = "provider-invented-item");
        var (result, _) = await Generate(output);
        AssertRejected(result, StoryGenerationFailure.SafetyRejected);
    }

    [Fact]
    public async Task SourceItemMovedFromAnotherSectionIsRejected()
    {
        var output = MutateStory(root =>
            Item(root, 0, 0)["sourceItemId"] =
                "associated_signal-CHANGE-MarketingSpend-2025-05-2025-06");
        var (result, _) = await Generate(output);
        AssertRejected(result, StoryGenerationFailure.SafetyRejected);
    }

    [Fact]
    public async Task OmittedRequiredSourceItemIsRejected()
    {
        var output = MutateStory(root =>
            Items(root, 3).RemoveAt(1));
        var (result, _) = await Generate(output);
        AssertRejected(result, StoryGenerationFailure.SafetyRejected);
    }

    [Fact]
    public async Task DuplicateSourceItemIdIsRejectedByGeneratedContract()
    {
        var output = MutateStory(root =>
            Item(root, 3, 1)["sourceItemId"] =
                "counter_signal-CHANGE-Orders-2025-05-2025-06");
        var (result, _) = await Generate(output);
        AssertRejected(result, StoryGenerationFailure.InvalidProviderResponse);
    }

    [Fact]
    public async Task InventedLimitationItemIsRejected()
    {
        var output = MutateStory(root =>
            Item(root, 6, 1)["sourceItemId"] = "invented-limitation");
        var (result, _) = await Generate(output);
        AssertRejected(result, StoryGenerationFailure.SafetyRejected);
    }

    [Fact]
    public async Task OmittingOneRequiredLimitationIsRejected()
    {
        var output = MutateStory(root => Items(root, 6).RemoveAt(1));
        var (result, _) = await Generate(output);
        AssertRejected(result, StoryGenerationFailure.SafetyRejected);
    }

    [Fact]
    public async Task OmittingLimitationsSectionIsRejected()
    {
        var output = MutateStory(root => Sections(root).RemoveAt(6));
        var (result, _) = await Generate(output);
        AssertRejected(result, StoryGenerationFailure.SafetyRejected);
    }

    [Fact]
    public async Task UnsupportedSemanticSentenceIsNotYetAudited()
    {
        var output = MutateStory(root =>
            Item(root, 0, 0)["text"] = "Customer satisfaction improved.");
        var (result, client) = await Generate(output);

        Assert.True(result.IsSuccess);
        Assert.NotNull(result.Story);
        Assert.Equal(1, client.CallCount);
    }

    [Theory]
    [InlineData(0, "Revenue increased by 32%.", 0)]
    [InlineData(3, "Orders fell by 20%.", 0)]
    [InlineData(3, "Customers fell by 10%.", 1)]
    public async Task NumericalMutationWithValidSourceIdIsNotYetAudited(
        int sectionIndex,
        string text,
        int itemIndex)
    {
        var output = MutateStory(root =>
            Item(root, sectionIndex, itemIndex)["text"] = text);
        var (result, client) = await Generate(output);

        Assert.True(result.IsSuccess);
        Assert.NotNull(result.Story);
        Assert.Equal(1, client.CallCount);
    }

    [Fact]
    public async Task GroundedPromptContainsPreventionRules()
    {
        var (result, client) = await Generate(
            GoldenStoryGenerationTests.GoldenGeneratedStoryJson());

        Assert.True(result.IsSuccess);
        Assert.Contains("Do not introduce new numerical values", client.Prompt);
        Assert.Contains("facts", client.Prompt);
        Assert.Contains("Do not infer causes", client.Prompt);
        Assert.Contains("Do not select, omit, or reorder findings", client.Prompt);
        Assert.Contains("missing-context limitations", client.Prompt);
    }

    private static void AssertRejected(
        StoryGenerationResult result,
        StoryGenerationFailure expected)
    {
        Assert.False(result.IsSuccess);
        Assert.Null(result.Story);
        Assert.Equal(expected, result.Failure);
    }

    private static async Task<(StoryGenerationResult Result, FakeLlmClient Client)>
        Generate(string output)
    {
        var client = new FakeLlmClient(output);
        var generator = new StoryGenerator(
            client,
            new GroundedPromptBuilder(),
            new GeneratedStorySafetyValidator());
        using var analytics = JsonDocument.Parse(
            GoldenStoryGenerationTests.GoldenAnalyticsJson());
        return (await generator.GenerateAsync(analytics.RootElement), client);
    }

    private static string MutateStory(Action<JsonObject> mutate)
    {
        var root = JsonNode.Parse(
            GoldenStoryGenerationTests.GoldenGeneratedStoryJson())!.AsObject();
        mutate(root);
        return root.ToJsonString();
    }

    private static JsonArray Sections(JsonObject root) =>
        root["sections"]!.AsArray();

    private static JsonArray Items(JsonObject root, int sectionIndex) =>
        Sections(root)[sectionIndex]!["items"]!.AsArray();

    private static JsonObject Item(
        JsonObject root,
        int sectionIndex,
        int itemIndex) =>
        Items(root, sectionIndex)[itemIndex]!.AsObject();

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
