using System.Text.Json;

namespace DataStoryBuilder.Application.Stories;

public sealed class StoryGenerator(
    ILlmClient llmClient,
    GroundedPromptBuilder promptBuilder,
    GeneratedStorySafetyValidator safetyValidator)
{
    private static readonly JsonSerializerOptions JsonOptions =
        new(JsonSerializerDefaults.Web);

    public async Task<StoryGenerationResult> GenerateAsync(
        JsonElement analyticsResponse,
        CancellationToken cancellationToken = default)
        => await GenerateAsync(analyticsResponse, null, cancellationToken);

    public async Task<StoryGenerationResult> GenerateAsync(
        JsonElement analyticsResponse,
        Action<string, string>? reportSubstage,
        CancellationToken cancellationToken = default)
    {
        GroundedStoryPromptInput groundedInput;
        try
        {
            groundedInput = GroundedStoryPromptProjector.Create(analyticsResponse);
        }
        catch (JsonException)
        {
            return Failure(
                StoryGenerationFailure.GroundingPreconditionFailed,
                "The analytics response does not contain a consistent grounded story plan.");
        }

        return await GenerateAsync(
            groundedInput,
            [],
            reportSubstage,
            cancellationToken);
    }

    public async Task<StoryGenerationResult> GenerateAsync(
        GroundedStoryPromptInput groundedInput,
        IReadOnlyList<string> auditFeedback,
        Action<string, string>? reportSubstage = null,
        CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(groundedInput);
        ArgumentNullException.ThrowIfNull(auditFeedback);

        reportSubstage?.Invoke("grounded-projection", "completed");
        reportSubstage?.Invoke("prompt-build", "started");
        var groundedPrompt = promptBuilder.Build(groundedInput, auditFeedback);
        reportSubstage?.Invoke("prompt-build", "completed");
        reportSubstage?.Invoke("schema-build", "started");
        var generatedStorySchema = GeneratedExecutiveStorySchema.Build();
        reportSubstage?.Invoke("schema-build", "completed");
        string generatedJson;
        try
        {
            reportSubstage?.Invoke("llm-call", "started");
            generatedJson = await llmClient.GenerateStructuredAsync(
                groundedPrompt,
                generatedStorySchema,
                cancellationToken);
            reportSubstage?.Invoke("llm-call", "completed");
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
        {
            throw;
        }
        catch (LlmClientException exception)
        {
            return MapProviderFailure(exception.Error);
        }

        GeneratedExecutiveStory? story;
        try
        {
            reportSubstage?.Invoke("generated-json-deserialization", "started");
            story = JsonSerializer.Deserialize<GeneratedExecutiveStory>(
                generatedJson,
                JsonOptions);
            reportSubstage?.Invoke("generated-json-deserialization", "completed");
        }
        catch (JsonException)
        {
            return InvalidProviderResponse();
        }
        catch (ArgumentException)
        {
            return InvalidProviderResponse();
        }

        if (story is null)
        {
            return InvalidProviderResponse();
        }

        try
        {
            reportSubstage?.Invoke("safety-validation", "started");
            safetyValidator.Validate(story, groundedInput);
            reportSubstage?.Invoke("safety-validation", "completed");
        }
        catch (GeneratedStorySafetyException)
        {
            return Failure(
                StoryGenerationFailure.SafetyRejected,
                "The generated story did not satisfy grounded story safety constraints.");
        }

        return StoryGenerationResult.Succeeded(story);
    }

    private static StoryGenerationResult MapProviderFailure(LlmClientError error) =>
        error switch
        {
            LlmClientError.Timeout => Failure(
                StoryGenerationFailure.Timeout,
                "The story generation provider timed out."),
            LlmClientError.RateLimited => Failure(
                StoryGenerationFailure.RateLimited,
                "The story generation provider rate limit was reached."),
            LlmClientError.ProviderUnavailable => Failure(
                StoryGenerationFailure.ProviderUnavailable,
                "The story generation provider is unavailable."),
            LlmClientError.InvalidProviderResponse => InvalidProviderResponse(),
            _ => InvalidProviderResponse()
        };

    private static StoryGenerationResult InvalidProviderResponse() =>
        Failure(
            StoryGenerationFailure.InvalidProviderResponse,
            "The story generation provider returned an invalid structured response.");

    private static StoryGenerationResult Failure(
        StoryGenerationFailure failure,
        string reason) =>
        StoryGenerationResult.Failed(failure, reason);
}
