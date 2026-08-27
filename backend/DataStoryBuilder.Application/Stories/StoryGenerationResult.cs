namespace DataStoryBuilder.Application.Stories;

public enum StoryGenerationFailure
{
    Timeout,
    RateLimited,
    ProviderUnavailable,
    InvalidProviderResponse,
    SafetyRejected,
    GroundingPreconditionFailed
}

public sealed record StoryGenerationResult
{
    private StoryGenerationResult(
        GeneratedExecutiveStory? story,
        StoryGenerationFailure? failure,
        string? failureReason)
    {
        Story = story;
        Failure = failure;
        FailureReason = failureReason;
    }

    public bool IsSuccess => Story is not null;
    public GeneratedExecutiveStory? Story { get; }
    public StoryGenerationFailure? Failure { get; }
    public string? FailureReason { get; }

    public static StoryGenerationResult Succeeded(GeneratedExecutiveStory story)
    {
        ArgumentNullException.ThrowIfNull(story);
        return new StoryGenerationResult(story, null, null);
    }

    public static StoryGenerationResult Failed(
        StoryGenerationFailure failure,
        string failureReason)
    {
        if (string.IsNullOrWhiteSpace(failureReason))
        {
            throw new ArgumentException(
                "Failure reason must not be empty or whitespace.",
                nameof(failureReason));
        }

        return new StoryGenerationResult(null, failure, failureReason);
    }
}
