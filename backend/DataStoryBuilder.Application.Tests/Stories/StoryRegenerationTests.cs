using System.Text.Json;
using DataStoryBuilder.Api;
using DataStoryBuilder.Application.Stories;
using DataStoryBuilder.Infrastructure.Generation;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Options;
using Xunit;

namespace DataStoryBuilder.Application.Tests.Stories;

public sealed class StoryRegenerationTests
{
    [Fact]
    public async Task PassingInitialStoryUsesOneLlmCall()
    {
        var client = new QueueLlmClient(AnalysisStoryGenerationTests.ValidStoryJson);

        var result = await Service(client).GenerateAndComposeAsync(
            AnalysisStoryGenerationTests.AnalyticsJson);

        Assert.Equal(1, client.CallCount);
        Assert.False(result.FullStoryAudit!.RegenerationAttempted);
        Assert.Equal(0, result.FullStoryAudit.RegenerationAttemptCount);
    }

    [Theory]
    [InlineData(StoryAuditDecision.Pass)]
    [InlineData(StoryAuditDecision.PassWithWarnings)]
    [InlineData(StoryAuditDecision.Block)]
    public void NonRegenerationDecisionsNeverRequestAttempt(
        StoryAuditDecision decision)
    {
        Assert.False(StoryRegenerationPolicy.ShouldRegenerate(
            Audit(decision, regenerationEligible: false),
            0));
    }

    [Fact]
    public async Task RegenerationThatPassesUsesExactlyTwoCallsAndPersistsFinalStoryAudit()
    {
        var initial = CertaintyInflatedStory();
        var client = new QueueLlmClient(
            initial,
            AnalysisStoryGenerationTests.ValidStoryJson);

        var result = await Service(client).GenerateAndComposeAsync(
            AnalysisStoryGenerationTests.AnalyticsJson);

        Assert.Equal(2, client.CallCount);
        Assert.Equal(StoryAuditDecision.Pass, result.FullStoryAudit!.Decision);
        Assert.True(result.FullStoryAudit.RegenerationAttempted);
        Assert.Equal(1, result.FullStoryAudit.RegenerationAttemptCount);
        Assert.Equal(StoryDataDiffStatus.Pass, result.StoryAudit!.Status);
        Assert.Equal(
            "Revenue changed.",
            result.Generation.Story!.Sections[0].Items[0].Text);
        Assert.Contains("REGENERATION AUDIT FEEDBACK", client.Prompts[1]);
        Assert.Contains(
            "Use evidence-calibrated language and preserve the required qualification.",
            client.Prompts[1]);
        Assert.Contains("Do not introduce new numerical values", client.Prompts[1]);
        Assert.Contains("Do not infer causes", client.Prompts[1]);
        Assert.Contains("Preserve required qualifications, counter-signals", client.Prompts[1]);
    }

    [Fact]
    public async Task RegenerationThatBlocksStopsAfterSecondCall()
    {
        var blocked = AnalysisStoryGenerationTests.ValidStoryJson.Replace(
            "Revenue changed.",
            "Revenue changed by 999.",
            StringComparison.Ordinal);
        var client = new QueueLlmClient(CertaintyInflatedStory(), blocked);

        var result = await Service(client).GenerateAndComposeAsync(
            AnalysisStoryGenerationTests.AnalyticsJson);

        Assert.Equal(2, client.CallCount);
        Assert.Equal(StoryAuditDecision.Block, result.FullStoryAudit!.Decision);
        Assert.Equal(StoryDataDiffStatus.Fail, result.StoryAudit!.Status);
        Assert.False(result.FullStoryAudit.RegenerationEligible);
        Assert.Equal(1, result.FullStoryAudit.RegenerationAttemptCount);
    }

    [Fact]
    public async Task RegenerationThatStillRequiresRegenerationStopsAfterSecondCall()
    {
        var initial = CertaintyInflatedStory();
        var client = new QueueLlmClient(initial, initial);

        var result = await Service(client).GenerateAndComposeAsync(
            AnalysisStoryGenerationTests.AnalyticsJson);

        Assert.Equal(2, client.CallCount);
        Assert.Equal(StoryAuditDecision.Regenerate, result.FullStoryAudit!.Decision);
        Assert.True(result.FullStoryAudit.RegenerationEligible);
        Assert.Equal(1, result.FullStoryAudit.RegenerationAttemptCount);
        Assert.False(StoryRegenerationPolicy.ShouldRegenerate(
            result.FullStoryAudit,
            result.FullStoryAudit.RegenerationAttemptCount));
    }

    [Fact]
    public async Task RegenerationProviderFailureRetainsInitialStoryAndAuditWithoutThirdCall()
    {
        var initial = CertaintyInflatedStory();
        var client = new QueueLlmClient(
            initial,
            new LlmClientException(LlmClientError.Timeout, "provider detail"));

        var result = await Service(client).GenerateAndComposeAsync(
            AnalysisStoryGenerationTests.AnalyticsJson);

        Assert.Equal(2, client.CallCount);
        Assert.Equal(StoryAuditDecision.Regenerate, result.FullStoryAudit!.Decision);
        Assert.Equal(
            "This clearly proves Revenue changed.",
            result.Generation.Story!.Sections[0].Items[0].Text);
        Assert.True(result.FullStoryAudit.RegenerationAttempted);
        Assert.Equal(1, result.FullStoryAudit.RegenerationAttemptCount);
        Assert.Equal(
            "The story generation provider timed out.",
            result.FullStoryAudit.RegenerationFailureReason);
        Assert.DoesNotContain("provider detail", result.ResponseJson);
    }

    [Fact]
    public void MaximumAttemptCountPreventsAnotherAttemptForEveryFinalDecision()
    {
        foreach (var decision in Enum.GetValues<StoryAuditDecision>())
        {
            Assert.False(StoryRegenerationPolicy.ShouldRegenerate(
                Audit(
                    decision,
                    regenerationEligible: decision == StoryAuditDecision.Regenerate),
                StoryRegenerationPolicy.MaximumAttempts));
        }
    }

    private static string CertaintyInflatedStory() =>
        AnalysisStoryGenerationTests.ValidStoryJson.Replace(
            "Revenue changed.",
            "This clearly proves Revenue changed.",
            StringComparison.Ordinal);

    private static AnalysisStoryGeneration Service(QueueLlmClient client)
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

    private static FullStoryAuditResult Audit(
        StoryAuditDecision decision,
        bool regenerationEligible) =>
        new(
            Day14(),
            new NarrativeBiasResult(
                NarrativeBiasStatus.Pass,
                BiasRiskLevel.None,
                []),
            decision,
            [],
            regenerationEligible,
            "day15-v1");

    private static StoryDataDiffResult Day14() => new(
        StoryDataDiffStatus.Pass,
        1,
        1,
        [],
        [],
        [],
        [],
        [],
        [],
        [],
        []);

    private sealed class QueueLlmClient : ILlmClient
    {
        private readonly Queue<object> results;

        public QueueLlmClient(params object[] results) =>
            this.results = new Queue<object>(results);

        public int CallCount { get; private set; }
        public List<string> Prompts { get; } = [];

        public Task<string> GenerateStructuredAsync(
            string groundedPrompt,
            string jsonSchema,
            CancellationToken cancellationToken = default)
        {
            CallCount++;
            Prompts.Add(groundedPrompt);
            var result = results.Dequeue();
            return result is Exception exception
                ? Task.FromException<string>(exception)
                : Task.FromResult((string)result);
        }
    }
}
