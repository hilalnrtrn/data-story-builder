namespace DataStoryBuilder.Infrastructure.Generation;

public sealed class LlmOptions
{
    public const string SectionName = "Llm";

    public string Model { get; set; } = string.Empty;
    public string ApiKey { get; set; } = string.Empty;
    public int TimeoutSeconds { get; set; } = 60;
    public string PromptVersion { get; set; } = string.Empty;

    public void Validate()
    {
        if (string.IsNullOrWhiteSpace(Model))
        {
            throw new InvalidOperationException("Llm:Model is required.");
        }
        if (string.IsNullOrWhiteSpace(ApiKey))
        {
            throw new InvalidOperationException("Llm:ApiKey is required.");
        }
        if (TimeoutSeconds is < 1 or > 300)
        {
            throw new InvalidOperationException(
                "Llm:TimeoutSeconds must be between 1 and 300.");
        }
        if (string.IsNullOrWhiteSpace(PromptVersion))
        {
            throw new InvalidOperationException("Llm:PromptVersion is required.");
        }
    }

    public override string ToString() =>
        $"LlmOptions {{ Model = {Model}, TimeoutSeconds = {TimeoutSeconds}, PromptVersion = {PromptVersion} }}";
}
