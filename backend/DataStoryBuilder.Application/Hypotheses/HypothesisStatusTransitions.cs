namespace DataStoryBuilder.Application.Hypotheses;

public enum HypothesisLifecycleStatus
{
    Open,
    Supported,
    Confirmed,
    Rejected
}

public static class HypothesisStatusTransitions
{
    private static readonly IReadOnlySet<(
        HypothesisLifecycleStatus Current,
        HypothesisLifecycleStatus Target)> Allowed =
        new HashSet<(
            HypothesisLifecycleStatus Current,
            HypothesisLifecycleStatus Target)>
        {
            (HypothesisLifecycleStatus.Open, HypothesisLifecycleStatus.Supported),
            (HypothesisLifecycleStatus.Open, HypothesisLifecycleStatus.Rejected),
            (HypothesisLifecycleStatus.Supported, HypothesisLifecycleStatus.Confirmed),
            (HypothesisLifecycleStatus.Supported, HypothesisLifecycleStatus.Rejected)
        };

    public static bool IsAllowed(
        HypothesisLifecycleStatus current,
        HypothesisLifecycleStatus target) =>
        Allowed.Contains((current, target));

    public static bool TryParse(
        string? value,
        out HypothesisLifecycleStatus status)
    {
        status = value switch
        {
            "OPEN" => HypothesisLifecycleStatus.Open,
            "SUPPORTED" => HypothesisLifecycleStatus.Supported,
            "CONFIRMED" => HypothesisLifecycleStatus.Confirmed,
            "REJECTED" => HypothesisLifecycleStatus.Rejected,
            _ => default
        };
        return value is "OPEN" or "SUPPORTED" or "CONFIRMED" or "REJECTED";
    }

    public static string ToStorageValue(HypothesisLifecycleStatus status) =>
        status switch
        {
            HypothesisLifecycleStatus.Open => "OPEN",
            HypothesisLifecycleStatus.Supported => "SUPPORTED",
            HypothesisLifecycleStatus.Confirmed => "CONFIRMED",
            HypothesisLifecycleStatus.Rejected => "REJECTED",
            _ => throw new ArgumentOutOfRangeException(nameof(status))
        };
}
