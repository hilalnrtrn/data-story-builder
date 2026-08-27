using System.Text.Json;
using System.Text.Json.Nodes;
using DataStoryBuilder.Application.Stories;
using DataStoryBuilder.Infrastructure.Generation;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Logging.Abstractions;
using Microsoft.Extensions.Options;

namespace DataStoryBuilder.Api;

public sealed class AnalysisStoryGeneration(
    IOptions<LlmOptions> options,
    IServiceProvider services,
    ILogger<AnalysisStoryGeneration>? logger = null)
{
    private static readonly JsonSerializerOptions JsonOptions =
        new(JsonSerializerDefaults.Web);

    public async Task<AnalysisStoryGenerationResult> GenerateAndComposeAsync(
        string analyticsJson,
        CancellationToken cancellationToken = default)
    {
        var safeLogger = logger ?? NullLogger<AnalysisStoryGeneration>.Instance;
        using var analyticsDocument = JsonDocument.Parse(analyticsJson);
        var analysisId = GetAnalysisId(analyticsDocument.RootElement);
        StoryGenerationResult generation;

        safeLogger.LogInformation(
            "Story generation substage {Substage} started for analysis {AnalysisId}.",
            "configuration-access",
            analysisId);
        var configuredOptions = options.Value;
        safeLogger.LogInformation(
            "Story generation substage {Substage} completed for analysis {AnalysisId}.",
            "configuration-access",
            analysisId);

        if (IsConfigured(configuredOptions))
        {
            safeLogger.LogInformation(
                "Story generation substage {Substage} started for analysis {AnalysisId}.",
                "service-resolution",
                analysisId);
            var generator = services.GetRequiredService<StoryGenerator>();
            safeLogger.LogInformation(
                "Story generation substage {Substage} completed for analysis {AnalysisId}.",
                "service-resolution",
                analysisId);
            var currentSubstage = "grounded-projection";
            safeLogger.LogInformation(
                "Story generation substage {Substage} started for analysis {AnalysisId}.",
                currentSubstage,
                analysisId);
            try
            {
                generation = await generator.GenerateAsync(
                    analyticsDocument.RootElement,
                    (substage, state) =>
                    {
                        currentSubstage = substage;
                        safeLogger.LogInformation(
                            "Story generation substage {Substage} {State} for analysis {AnalysisId}.",
                            substage,
                            state,
                            analysisId);
                    },
                    cancellationToken);
            }
            catch (Exception exception) when (exception is not OperationCanceledException)
            {
                safeLogger.LogError(
                    "Story generation substage {Substage} failed for analysis {AnalysisId} with exception type {ExceptionType}.",
                    currentSubstage,
                    analysisId,
                    exception.GetType().Name);
                throw;
            }
        }
        else
        {
            generation = StoryGenerationResult.Failed(
                StoryGenerationFailure.ProviderUnavailable,
                "Story generation is not configured.");
        }

        safeLogger.LogInformation(
            "Story generation substage {Substage} started for analysis {AnalysisId}.",
            "response-compose",
            analysisId);
        var response = JsonNode.Parse(analyticsJson)?.AsObject()
            ?? throw new JsonException("The analytics response must be a JSON object.");

        response["generatedStory"] = generation.Story is null
            ? null
            : JsonSerializer.SerializeToNode(generation.Story, JsonOptions);
        var promptVersion = NullIfWhiteSpace(configuredOptions.PromptVersion);
        var modelIdentifier = NullIfWhiteSpace(configuredOptions.Model);
        var generatedAt = generation.IsSuccess
            ? DateTimeOffset.UtcNow
            : (DateTimeOffset?)null;
        response["storyGeneration"] = new JsonObject
        {
            ["status"] = generation.IsSuccess ? "Succeeded" : "Failed",
            ["failureCategory"] = generation.Failure?.ToString(),
            ["promptVersion"] = promptVersion,
            ["modelIdentifier"] = modelIdentifier,
            ["generatedAt"] = generatedAt,
            ["failureReason"] = generation.FailureReason
        };
        safeLogger.LogInformation(
            "Story generation substage {Substage} completed for analysis {AnalysisId}.",
            "response-compose",
            analysisId);

        return new AnalysisStoryGenerationResult(
            response.ToJsonString(JsonOptions),
            generation,
            promptVersion,
            modelIdentifier,
            generatedAt);
    }

    private static bool IsConfigured(LlmOptions value) =>
        !string.IsNullOrWhiteSpace(value.Model)
        && !string.IsNullOrWhiteSpace(value.ApiKey);

    private static string? NullIfWhiteSpace(string? value) =>
        string.IsNullOrWhiteSpace(value) ? null : value;

    private static string GetAnalysisId(JsonElement analyticsResponse)
    {
        if (analyticsResponse.TryGetProperty("storyPlan", out var storyPlan)
            && storyPlan.ValueKind == JsonValueKind.Object
            && storyPlan.TryGetProperty("analysisId", out var analysisId)
            && analysisId.ValueKind == JsonValueKind.String)
        {
            return analysisId.GetString() ?? "unknown";
        }

        return "unknown";
    }
}

public sealed record AnalysisStoryGenerationResult(
    string ResponseJson,
    StoryGenerationResult Generation,
    string? PromptVersion,
    string? ModelIdentifier,
    DateTimeOffset? GeneratedAt);
