namespace DataStoryBuilder.Application.Stories;

public enum StoryDataDiffStatus
{
    Pass,
    Fail
}

public enum StoryEvidenceStrength
{
    Strong,
    None,
    NotApplicable
}

public sealed record StoryEvidenceTrace(
    string InsightId,
    IReadOnlyList<GroundedStoryEvidence> ResolvedEvidence)
{
    public bool HasResolvedEvidence => ResolvedEvidence.Count > 0;
}

public sealed record StoryItemAudit(
    string SourceItemId,
    string? InsightId,
    string? Role,
    bool IsLimitation,
    bool IsCovered,
    bool HasResolvedEvidence,
    StoryEvidenceStrength EvidenceStrength,
    StoryEvidenceTrace? EvidenceTrace,
    IReadOnlyList<string> Reasons);

public sealed record StoryDataDiffResult(
    StoryDataDiffStatus Status,
    double StoryCoverageScore,
    double EvidenceCoverageScore,
    IReadOnlyList<string> RequiredSourceItemIds,
    IReadOnlyList<string> CoveredSourceItemIds,
    IReadOnlyList<string> OmittedSourceItemIds,
    IReadOnlyList<string> UnexpectedSourceItemIds,
    IReadOnlyList<StoryItemAudit> ItemAudits,
    IReadOnlyList<StoryItemNumericalAudit> NumericalAudits,
    IReadOnlyList<string> Reasons,
    IReadOnlyList<string> AuditLimitations)
{
    public bool AuditFailed => Status == StoryDataDiffStatus.Fail;

    public IReadOnlyList<StoryNumericalMismatch> NumericalMismatches =>
        NumericalAudits
            .SelectMany(audit => audit.UnsupportedTokens)
            .ToArray();

    public bool RegenerationEligible =>
        OmittedSourceItemIds.Count > 0
        || UnexpectedSourceItemIds.Count > 0
        || NumericalMismatches.Count > 0;
}
