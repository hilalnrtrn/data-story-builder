namespace DataStoryBuilder.Application.Stories;

public sealed record StoryItemAuditSource(
    string SourceItemId,
    string GeneratedText,
    string? Role,
    string? InsightId,
    bool IsLimitation,
    IReadOnlyList<GroundedStoryEvidence> ResolvedEvidence,
    bool IsResolved);
