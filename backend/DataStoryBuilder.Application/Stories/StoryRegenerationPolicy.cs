namespace DataStoryBuilder.Application.Stories;

public static class StoryRegenerationPolicy
{
    public const int MaximumAttempts = 1;

    public static bool ShouldRegenerate(
        FullStoryAuditResult audit,
        int regenerationAttemptCount)
    {
        ArgumentNullException.ThrowIfNull(audit);
        return audit.Decision == StoryAuditDecision.Regenerate
            && audit.RegenerationEligible
            && regenerationAttemptCount < MaximumAttempts;
    }
}
