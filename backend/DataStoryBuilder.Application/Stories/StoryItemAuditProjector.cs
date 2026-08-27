namespace DataStoryBuilder.Application.Stories;

public static class StoryItemAuditProjector
{
    public static IReadOnlyList<StoryItemAuditSource> Create(
        GeneratedExecutiveStory story,
        GroundedStoryPromptInput groundedInput)
    {
        ArgumentNullException.ThrowIfNull(story);
        ArgumentNullException.ThrowIfNull(groundedInput);

        var findingLookup = BuildLookup(
            groundedInput.Findings,
            finding => finding.SourceItemId);
        var limitationLookup = BuildLookup(
            groundedInput.Limitations,
            limitation => limitation.SourceItemId);

        return story.Sections
            .OrderBy(section => section.Order)
            .SelectMany(section => section.Items)
            .Select(item => Resolve(item, findingLookup, limitationLookup))
            .ToArray();
    }

    private static StoryItemAuditSource Resolve(
        GeneratedStoryItem item,
        IReadOnlyDictionary<string, GroundedStoryFinding> findingLookup,
        IReadOnlyDictionary<string, GroundedStoryLimitation> limitationLookup)
    {
        if (findingLookup.TryGetValue(item.SourceItemId, out var finding))
        {
            return new StoryItemAuditSource(
                item.SourceItemId,
                item.Text,
                finding.Role,
                finding.InsightId,
                false,
                finding.Evidence,
                true);
        }

        if (limitationLookup.TryGetValue(item.SourceItemId, out var limitation))
        {
            return new StoryItemAuditSource(
                item.SourceItemId,
                item.Text,
                "MISSING_CONTEXT",
                limitation.InsightId,
                true,
                [],
                true);
        }

        return new StoryItemAuditSource(
            item.SourceItemId,
            item.Text,
            null,
            null,
            false,
            [],
            false);
    }

    private static IReadOnlyDictionary<string, T> BuildLookup<T>(
        IEnumerable<T> items,
        Func<T, string> idSelector)
    {
        var lookup = new Dictionary<string, T>(StringComparer.Ordinal);
        foreach (var item in items)
        {
            lookup.TryAdd(idSelector(item), item);
        }

        return lookup;
    }
}
