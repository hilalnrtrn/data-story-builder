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
        StoryDataDiffResult? storyAudit = null;
        FullStoryAuditResult? fullStoryAudit = null;
        var regenerationAttemptCount = 0;

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
                var groundedInput = GroundedStoryPromptProjector.Create(
                    analyticsDocument.RootElement);
                generation = await generator.GenerateAsync(
                    groundedInput,
                    [],
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

                if (generation.IsSuccess)
                {
                    (storyAudit, fullStoryAudit) = Audit(
                        generation.Story!,
                        groundedInput);
                }

                if (fullStoryAudit is not null
                    && StoryRegenerationPolicy.ShouldRegenerate(
                        fullStoryAudit,
                        regenerationAttemptCount))
                {
                    regenerationAttemptCount++;
                    var initialGeneration = generation;
                    var initialStoryAudit = storyAudit!;
                    var initialFullStoryAudit = fullStoryAudit;
                    var regenerated = await generator.GenerateAsync(
                        groundedInput,
                        fullStoryAudit.Reasons,
                        (substage, state) =>
                        {
                            currentSubstage = $"regeneration-{substage}";
                            safeLogger.LogInformation(
                                "Story regeneration substage {Substage} {State} for analysis {AnalysisId}.",
                                substage,
                                state,
                                analysisId);
                        },
                        cancellationToken);
                    if (regenerated.IsSuccess)
                    {
                        generation = regenerated;
                        (storyAudit, fullStoryAudit) = Audit(
                            regenerated.Story!,
                            groundedInput);
                        fullStoryAudit = fullStoryAudit with
                        {
                            RegenerationAttempted = true,
                            RegenerationAttemptCount = regenerationAttemptCount
                        };
                    }
                    else
                    {
                        generation = initialGeneration;
                        storyAudit = initialStoryAudit;
                        fullStoryAudit = initialFullStoryAudit with
                        {
                            RegenerationAttempted = true,
                            RegenerationAttemptCount = regenerationAttemptCount,
                            RegenerationFailureReason = Bound(
                                regenerated.FailureReason
                                    ?? "Story regeneration failed.")
                        };
                    }
                }
            }
            catch (JsonException) when (currentSubstage == "grounded-projection")
            {
                generation = StoryGenerationResult.Failed(
                    StoryGenerationFailure.GroundingPreconditionFailed,
                    "The analytics response does not contain a consistent grounded story plan.");
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

        if (generation.IsSuccess && storyAudit is null)
        {
            var groundedInput = GroundedStoryPromptProjector.Create(
                analyticsDocument.RootElement);
            (storyAudit, fullStoryAudit) = Audit(
                generation.Story!,
                groundedInput);
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
        response["storyAudit"] = storyAudit is null
            ? null
            : JsonSerializer.SerializeToNode(storyAudit, JsonOptions);
        response["fullStoryAudit"] = fullStoryAudit is null
            ? null
            : JsonSerializer.SerializeToNode(fullStoryAudit, JsonOptions);
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
            ["failureReason"] = generation.FailureReason,
            ["regenerationAttempted"] = regenerationAttemptCount > 0,
            ["regenerationAttemptCount"] = regenerationAttemptCount,
            ["regenerationFailureReason"] = fullStoryAudit?.RegenerationFailureReason
        };
        safeLogger.LogInformation(
            "Story generation substage {Substage} completed for analysis {AnalysisId}.",
            "response-compose",
            analysisId);

        return new AnalysisStoryGenerationResult(
            response.ToJsonString(JsonOptions),
            generation,
            storyAudit,
            fullStoryAudit,
            promptVersion,
            modelIdentifier,
            generatedAt);
    }

    private static bool IsConfigured(LlmOptions value) =>
        !string.IsNullOrWhiteSpace(value.Model)
        && !string.IsNullOrWhiteSpace(value.ApiKey);

    private static string? NullIfWhiteSpace(string? value) =>
        string.IsNullOrWhiteSpace(value) ? null : value;

    private static (StoryDataDiffResult StoryAudit, FullStoryAuditResult FullStoryAudit) Audit(
        GeneratedExecutiveStory story,
        GroundedStoryPromptInput groundedInput)
    {
        var storyAudit = StoryDataDiffEvaluator.Evaluate(story, groundedInput);
        var narrativeBias = NarrativeBiasEvaluator.Evaluate(story, groundedInput);
        return (storyAudit, FullStoryAuditor.Audit(storyAudit, narrativeBias));
    }

    private static string Bound(string value) =>
        value.Length <= 1000 ? value : value[..1000];

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
    StoryDataDiffResult? StoryAudit,
    FullStoryAuditResult? FullStoryAudit,
    string? PromptVersion,
    string? ModelIdentifier,
    DateTimeOffset? GeneratedAt);
