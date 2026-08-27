namespace DataStoryBuilder.Application.Stories;

public static class FullStoryAuditor
{
    public const string AuditorVersion = "day15-v1";

    public static FullStoryAuditResult Audit(
        StoryDataDiffResult storyDataDiff,
        NarrativeBiasResult narrativeBias)
    {
        ArgumentNullException.ThrowIfNull(storyDataDiff);
        ArgumentNullException.ThrowIfNull(narrativeBias);

        var decision = Decide(storyDataDiff, narrativeBias);
        var reasons = storyDataDiff.Reasons
            .Concat(narrativeBias.Findings.SelectMany(finding =>
                new[] { finding.Message, finding.Recommendation }))
            .Distinct(StringComparer.Ordinal)
            .ToArray();

        return new FullStoryAuditResult(
            storyDataDiff,
            narrativeBias,
            decision,
            reasons,
            decision == StoryAuditDecision.Regenerate,
            AuditorVersion);
    }

    private static StoryAuditDecision Decide(
        StoryDataDiffResult storyDataDiff,
        NarrativeBiasResult narrativeBias)
    {
        if (storyDataDiff.NumericalMismatches.Count > 0
            || storyDataDiff.UnexpectedSourceItemIds.Count > 0
            || storyDataDiff.EvidenceCoverageScore < 1.0
            || HasFinding(
                narrativeBias,
                BiasCategory.CausalFraming,
                BiasRiskLevel.High))
        {
            return StoryAuditDecision.Block;
        }

        if (storyDataDiff.OmittedSourceItemIds.Count > 0
            || storyDataDiff.StoryCoverageScore < 1.0
            || narrativeBias.Findings.Any(finding =>
                finding.RiskLevel is BiasRiskLevel.Medium or BiasRiskLevel.High))
        {
            return StoryAuditDecision.Regenerate;
        }

        if (narrativeBias.Findings.Count > 0)
        {
            return StoryAuditDecision.PassWithWarnings;
        }

        return StoryAuditDecision.Pass;
    }

    private static bool HasFinding(
        NarrativeBiasResult result,
        BiasCategory category,
        BiasRiskLevel riskLevel) =>
        result.Findings.Any(finding =>
            finding.Category == category
            && finding.RiskLevel == riskLevel);
}
