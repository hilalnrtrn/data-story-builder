namespace DataStoryBuilder.Application.Stories;

public sealed record StoryNumericToken(
    string OriginalText,
    decimal NormalizedValue,
    bool IsPercent);

public sealed record StoryNumericalMismatch(
    string SourceItemId,
    string OriginalToken,
    decimal NormalizedValue,
    bool IsPercent,
    string Reason);

public sealed record StoryItemNumericalAudit(
    string SourceItemId,
    IReadOnlyList<StoryNumericToken> ExtractedTokens,
    IReadOnlyList<StoryNumericalMismatch> UnsupportedTokens)
{
    public bool Passed => UnsupportedTokens.Count == 0;
}
