namespace DataStoryBuilder.Application.Stories;

public sealed record GeneratedExecutiveStory
{
    public GeneratedExecutiveStory(
        string title,
        string executiveSummary,
        IReadOnlyList<GeneratedStorySection> sections)
    {
        Title = RequireText(title, nameof(title));
        ExecutiveSummary = RequireText(
            executiveSummary,
            nameof(executiveSummary));

        ArgumentNullException.ThrowIfNull(sections);

        if (sections.Count == 0)
        {
            throw new ArgumentException(
                "A generated executive story must contain at least one section.",
                nameof(sections));
        }

        if (
            sections.Select(section => section.Order).Distinct().Count()
            != sections.Count
        )
        {
            throw new ArgumentException(
                "Section order values must be unique.",
                nameof(sections));
        }

        Sections = sections.ToArray();
    }

    public string Title { get; }
    public string ExecutiveSummary { get; }
    public IReadOnlyList<GeneratedStorySection> Sections { get; }

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
