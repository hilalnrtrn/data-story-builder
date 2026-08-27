namespace DataStoryBuilder.Application.Stories;

public sealed record GeneratedStorySection
{
    public GeneratedStorySection(
        int order,
        string type,
        IReadOnlyList<GeneratedStoryItem> items)
    {
        if (order <= 0)
        {
            throw new ArgumentOutOfRangeException(
                nameof(order),
                "Order must be positive.");
        }

        if (string.IsNullOrWhiteSpace(type))
        {
            throw new ArgumentException(
                "Type must not be empty or whitespace.",
                nameof(type));
        }

        ArgumentNullException.ThrowIfNull(items);

        if (items.Count == 0)
        {
            throw new ArgumentException(
                "A generated story section must contain at least one item.",
                nameof(items));
        }

        if (
            items.Select(item => item.SourceItemId)
                .Distinct(StringComparer.Ordinal)
                .Count()
            != items.Count
        )
        {
            throw new ArgumentException(
                "SourceItemId values must be unique within a section.",
                nameof(items));
        }

        Order = order;
        Type = type;
        Items = items.ToArray();
    }

    public int Order { get; }
    public string Type { get; }
    public IReadOnlyList<GeneratedStoryItem> Items { get; }
}
