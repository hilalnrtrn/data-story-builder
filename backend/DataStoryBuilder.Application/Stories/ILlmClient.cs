namespace DataStoryBuilder.Application.Stories;

public interface ILlmClient
{
    Task<string> GenerateStructuredAsync(
        string groundedPrompt,
        string jsonSchema,
        CancellationToken cancellationToken = default);
}
