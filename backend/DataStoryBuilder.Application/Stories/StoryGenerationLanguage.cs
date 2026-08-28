namespace DataStoryBuilder.Application.Stories;

public static class StoryGenerationLanguage
{
    public const string English = "en";
    public const string Turkish = "tr";
    public const string Default = English;

    public static bool TryNormalize(string? value, out string language)
    {
        var candidate = string.IsNullOrWhiteSpace(value)
            ? Default
            : value.Trim();

        if (candidate is English or Turkish)
        {
            language = candidate;
            return true;
        }

        language = string.Empty;
        return false;
    }

    public static string RequireSupported(string value) =>
        TryNormalize(value, out var language)
            ? language
            : throw new ArgumentException(
                "Story generation language must be 'en' or 'tr'.",
                nameof(value));
}
