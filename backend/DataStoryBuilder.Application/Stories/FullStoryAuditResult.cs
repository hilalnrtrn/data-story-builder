namespace DataStoryBuilder.Application.Stories;

public enum StoryAuditDecision
{
    Pass,
    PassWithWarnings,
    Regenerate,
    Block
}

public sealed record FullStoryAuditResult(
    StoryDataDiffResult StoryDataDiff,
    NarrativeBiasResult NarrativeBias,
    StoryAuditDecision Decision,
    IReadOnlyList<string> Reasons,
    bool RegenerationEligible,
    string AuditorVersion,
    bool RegenerationAttempted = false,
    int RegenerationAttemptCount = 0,
    string? RegenerationFailureReason = null);
