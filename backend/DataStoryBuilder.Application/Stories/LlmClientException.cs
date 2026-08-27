namespace DataStoryBuilder.Application.Stories;

public enum LlmClientError
{
    Timeout,
    RateLimited,
    ProviderUnavailable,
    InvalidProviderResponse
}

public sealed class LlmClientException(
    LlmClientError error,
    string message,
    Exception? innerException = null)
    : Exception(message, innerException)
{
    public LlmClientError Error { get; } = error;
}
