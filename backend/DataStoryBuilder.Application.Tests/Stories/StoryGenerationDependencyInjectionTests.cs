using DataStoryBuilder.Api;
using DataStoryBuilder.Application.Stories;
using DataStoryBuilder.Infrastructure.Generation;
using Microsoft.Extensions.DependencyInjection;
using Xunit;

namespace DataStoryBuilder.Application.Tests.Stories;

public sealed class StoryGenerationDependencyInjectionTests
{
    [Fact]
    public void ProductionEquivalentGraphResolvesWithoutNetworkUse()
    {
        var services = new ServiceCollection();
        services.AddLogging();
        services.Configure<LlmOptions>(options =>
        {
            options.Model = "test-model";
            options.ApiKey = "test-only-fake-key";
            options.TimeoutSeconds = 60;
            options.PromptVersion = "test-prompt-v1";
        });
        services.AddHttpClient<ILlmClient, GroqLlmClient>();
        services.AddScoped<GroundedPromptBuilder>();
        services.AddScoped<GeneratedStorySafetyValidator>();
        services.AddScoped<StoryGenerator>();
        services.AddScoped<AnalysisStoryGeneration>();

        using var provider = services.BuildServiceProvider();
        using var scope = provider.CreateScope();

        Assert.IsType<GroqLlmClient>(
            scope.ServiceProvider.GetRequiredService<ILlmClient>());
        Assert.NotNull(
            scope.ServiceProvider.GetRequiredService<StoryGenerator>());
        Assert.NotNull(
            scope.ServiceProvider.GetRequiredService<AnalysisStoryGeneration>());
    }
}
