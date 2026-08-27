namespace DataStoryBuilder.Application.Stories;

public enum BiasCategory
{
    PositiveFraming,
    NegativeFraming,
    SelectiveEmphasis,
    CertaintyInflation,
    CausalFraming,
    MissingContextOmission
}

public enum BiasRiskLevel
{
    None,
    Low,
    Medium,
    High
}

public enum NarrativeBiasStatus
{
    Pass,
    Warning,
    Fail
}

public sealed record NarrativeBiasFinding(
    BiasCategory Category,
    BiasRiskLevel RiskLevel,
    string? SourceItemId,
    string Message,
    string Recommendation,
    IReadOnlyList<string> Reasons);

public sealed record NarrativeBiasResult(
    NarrativeBiasStatus Status,
    BiasRiskLevel RiskLevel,
    IReadOnlyList<NarrativeBiasFinding> Findings)
{
    public bool HasMaterialBias =>
        Status == NarrativeBiasStatus.Fail
        || RiskLevel is BiasRiskLevel.Medium or BiasRiskLevel.High;

    public BiasRiskLevel GetCategoryRisk(BiasCategory category) =>
        Findings
            .Where(finding => finding.Category == category)
            .Select(finding => finding.RiskLevel)
            .DefaultIfEmpty(BiasRiskLevel.None)
            .Max();
}
