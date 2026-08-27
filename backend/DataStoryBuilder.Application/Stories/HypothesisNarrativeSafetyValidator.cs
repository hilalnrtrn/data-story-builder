namespace DataStoryBuilder.Application.Stories;

public enum HypothesisNarrativeContentType
{
    Hypothesis
}

public sealed record HypothesisNarrativeSafetyResult(
    bool IsSafe,
    HypothesisNarrativeContentType ContentType,
    IReadOnlyList<string> Reasons);

public static class HypothesisNarrativeSafetyValidator
{
    private static readonly string[] AllowedStatuses =
    [
        "OPEN",
        "SUPPORTED",
        "CONFIRMED",
        "REJECTED"
    ];

    private static readonly string[] QualifiedPhrases =
    [
        "may be associated with",
        "could be related to",
        "may be relevant to explaining"
    ];

    private static readonly string[] ForbiddenCausalPhrases =
    [
        "caused",
        "causes",
        "led to",
        "resulted in",
        "drove",
        "driven by",
        "because of",
        "responsible for"
    ];

    public static HypothesisNarrativeSafetyResult Evaluate(
        string narrativeText,
        string hypothesisStatus,
        double hypothesisConfidence,
        string causalityStatus)
    {
        RequireText(narrativeText, nameof(narrativeText));
        RequireText(hypothesisStatus, nameof(hypothesisStatus));
        RequireText(causalityStatus, nameof(causalityStatus));

        if (!AllowedStatuses.Contains(hypothesisStatus, StringComparer.Ordinal))
        {
            throw new ArgumentException(
                "Hypothesis status is not part of the controlled vocabulary.",
                nameof(hypothesisStatus));
        }

        if (!double.IsFinite(hypothesisConfidence)
            || hypothesisConfidence is < 0.0 or > 1.0)
        {
            throw new ArgumentOutOfRangeException(
                nameof(hypothesisConfidence),
                "Hypothesis confidence must be finite and in [0, 1].");
        }

        var forbidden = ForbiddenCausalPhrases.FirstOrDefault(phrase =>
            ContainsPhrase(narrativeText, phrase));
        if (forbidden is not null)
        {
            return Rejected(
                $"Hypothesis narrative contains forbidden causal phrase '{forbidden}'.",
                $"Causality status is '{causalityStatus}'.");
        }

        if (!QualifiedPhrases.Any(phrase => ContainsPhrase(narrativeText, phrase)))
        {
            return Rejected(
                "Hypothesis narrative does not contain approved uncertainty language.");
        }

        return new HypothesisNarrativeSafetyResult(
            true,
            HypothesisNarrativeContentType.Hypothesis,
            ["Narrative preserves explicit hypothesis uncertainty."]);
    }

    private static HypothesisNarrativeSafetyResult Rejected(
        params string[] reasons) =>
        new(
            false,
            HypothesisNarrativeContentType.Hypothesis,
            reasons);

    private static bool ContainsPhrase(string text, string phrase)
    {
        var start = 0;
        while (start < text.Length)
        {
            var index = text.IndexOf(
                phrase,
                start,
                StringComparison.OrdinalIgnoreCase);
            if (index < 0)
            {
                return false;
            }

            var end = index + phrase.Length;
            var beforeIsWord = index > 0
                && char.IsLetterOrDigit(text[index - 1]);
            var afterIsWord = end < text.Length
                && char.IsLetterOrDigit(text[end]);
            if (!beforeIsWord && !afterIsWord)
            {
                return true;
            }

            start = index + 1;
        }

        return false;
    }

    private static void RequireText(string value, string parameterName)
    {
        if (string.IsNullOrWhiteSpace(value))
        {
            throw new ArgumentException(
                "Value must not be empty or whitespace.",
                parameterName);
        }
    }
}
