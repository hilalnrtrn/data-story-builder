namespace DataStoryBuilder.Application.Stories;

public static class NarrativeBiasEvaluator
{
    public static NarrativeBiasResult Evaluate(
        GeneratedExecutiveStory story,
        GroundedStoryPromptInput groundedInput)
    {
        ArgumentNullException.ThrowIfNull(story);
        ArgumentNullException.ThrowIfNull(groundedInput);

        var framing = NarrativeFramingAnalyzer.Analyze(story, groundedInput);
        var safety = NarrativeSafetyAnalyzer.Analyze(story, groundedInput);
        return Compose([.. framing.Findings, .. safety]);
    }

    public static NarrativeBiasResult Compose(
        IEnumerable<NarrativeBiasFinding> findings)
    {
        ArgumentNullException.ThrowIfNull(findings);

        var seen = new HashSet<string>(StringComparer.Ordinal);
        var distinct = findings.Where(finding => seen.Add(Key(finding))).ToArray();
        var risk = distinct
            .Select(finding => finding.RiskLevel)
            .DefaultIfEmpty(BiasRiskLevel.None)
            .Max();
        var status = distinct.Length == 0
            ? NarrativeBiasStatus.Pass
            : risk == BiasRiskLevel.High
                ? NarrativeBiasStatus.Fail
                : NarrativeBiasStatus.Warning;

        return new NarrativeBiasResult(status, risk, distinct);
    }

    private static string Key(NarrativeBiasFinding finding) =>
        string.Join(
            "\u001f",
            finding.Category,
            finding.RiskLevel,
            finding.SourceItemId,
            finding.Message,
            finding.Recommendation,
            string.Join("\u001e", finding.Reasons));
}
