namespace DataStoryBuilder.Application.Stories;

public sealed record GeneratedStoryItem
{
    public GeneratedStoryItem(string sourceItemId, string text)
    {
        SourceItemId = RequireText(sourceItemId, nameof(sourceItemId));
        Text = RequireText(text, nameof(text));
    }

    public string SourceItemId { get; }
    public string Text { get; }

    private static string RequireText(string value, string parameterName)
    {
        if (string.IsNullOrWhiteSpace(value))
        {
            throw new ArgumentException(
                "Value must not be empty or whitespace.",
                parameterName);
        }

        return value;
    }
}
