namespace DataStoryBuilder.Application.Stories;

public enum NarrativeFramingDirection
{
    Positive,
    Negative
}

public enum StructuredFindingDirection
{
    Positive,
    Negative,
    NeutralOrUnknown
}

public sealed record NarrativeFramingSignal(
    NarrativeFramingDirection Direction,
    string MatchedPhrase,
    string? SourceItemId,
    string Text);

public sealed record NarrativeFramingAnalysis(
    IReadOnlyList<NarrativeFramingSignal> Signals,
    IReadOnlyList<NarrativeBiasFinding> Findings);

public static class NarrativeFramingAnalyzer
{
    private static readonly string[] PositivePhrases =
    [
        "remarkable",
        "exceptional",
        "outstanding",
        "spectacular",
        "impressive",
        "dramatic growth",
        "strong growth",
        "strong performance"
    ];

    private static readonly string[] NegativePhrases =
    [
        "disastrous",
        "catastrophic",
        "alarming",
        "severe collapse",
        "dramatic decline"
    ];

    public static NarrativeFramingAnalysis Analyze(
        GeneratedExecutiveStory story,
        GroundedStoryPromptInput groundedInput)
    {
        ArgumentNullException.ThrowIfNull(story);
        ArgumentNullException.ThrowIfNull(groundedInput);

        var signals = DetectSignals(story);
        var directions = groundedInput.Findings.ToDictionary(
            finding => finding.SourceItemId,
            ClassifyDirection,
            StringComparer.Ordinal);
        var positiveItems = Exposure(story, directions, StructuredFindingDirection.Positive);
        var negativeItems = Exposure(story, directions, StructuredFindingDirection.Negative);
        var findings = new List<NarrativeBiasFinding>();

        if (positiveItems.Count > 0 && negativeItems.Count > 0)
        {
            AddFramingFinding(
                findings,
                signals,
                NarrativeFramingDirection.Positive,
                BiasCategory.PositiveFraming,
                "The mixed story uses repeated strong positive framing.",
                "Use more neutral wording and retain visible counter-signals.");
            AddFramingFinding(
                findings,
                signals,
                NarrativeFramingDirection.Negative,
                BiasCategory.NegativeFraming,
                "The mixed story uses repeated alarmist negative framing.",
                "Use more neutral wording and retain visible positive findings.");

            var emphasis = EvaluateEmphasis(
                positiveItems,
                negativeItems,
                signals);
            if (emphasis is not null)
            {
                findings.Add(emphasis);
            }
        }

        return new NarrativeFramingAnalysis(signals, findings);
    }

    public static StructuredFindingDirection ClassifyDirection(
        GroundedStoryFinding finding)
    {
        ArgumentNullException.ThrowIfNull(finding);

        if (finding.Role == "ASSOCIATED_SIGNAL"
            || finding.Role == "RISK"
            || finding.Role == "CONTEXT")
        {
            return StructuredFindingDirection.NeutralOrUnknown;
        }

        var supportedMetric = finding.Metric is "Revenue" or "Orders" or "Customers";
        var supportedRole = finding.Role is "MAIN_OUTCOME"
            or "PRIMARY_CONTRIBUTOR"
            or "SECONDARY_FINDING"
            or "COUNTER_SIGNAL";
        if (!supportedMetric || !supportedRole)
        {
            return StructuredFindingDirection.NeutralOrUnknown;
        }

        return finding.Direction switch
        {
            "UP" => StructuredFindingDirection.Positive,
            "DOWN" => StructuredFindingDirection.Negative,
            _ => StructuredFindingDirection.NeutralOrUnknown
        };
    }

    private static IReadOnlyList<NarrativeFramingSignal> DetectSignals(
        GeneratedExecutiveStory story)
    {
        var result = new List<NarrativeFramingSignal>();
        AddSignals(result, story.ExecutiveSummary, null);
        foreach (var item in story.Sections
                     .OrderBy(section => section.Order)
                     .SelectMany(section => section.Items))
        {
            AddSignals(result, item.Text, item.SourceItemId);
        }

        return result;
    }

    private static void AddSignals(
        ICollection<NarrativeFramingSignal> result,
        string text,
        string? sourceItemId)
    {
        AddSignals(
            result,
            text,
            sourceItemId,
            NarrativeFramingDirection.Positive,
            PositivePhrases);
        AddSignals(
            result,
            text,
            sourceItemId,
            NarrativeFramingDirection.Negative,
            NegativePhrases);
    }

    private static void AddSignals(
        ICollection<NarrativeFramingSignal> result,
        string text,
        string? sourceItemId,
        NarrativeFramingDirection direction,
        IEnumerable<string> phrases)
    {
        foreach (var phrase in phrases)
        {
            foreach (var _ in MatchIndexes(text, phrase))
            {
                result.Add(new NarrativeFramingSignal(
                    direction,
                    phrase,
                    sourceItemId,
                    text));
            }
        }
    }

    private static IEnumerable<int> MatchIndexes(string text, string phrase)
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
                yield break;
            }

            var end = index + phrase.Length;
            var beforeIsWord = index > 0 && char.IsLetterOrDigit(text[index - 1]);
            var afterIsWord = end < text.Length && char.IsLetterOrDigit(text[end]);
            if (!beforeIsWord && !afterIsWord)
            {
                yield return index;
            }

            start = Math.Max(end, index + 1);
        }
    }

    private static List<ItemExposure> Exposure(
        GeneratedExecutiveStory story,
        IReadOnlyDictionary<string, StructuredFindingDirection> directions,
        StructuredFindingDirection requestedDirection) =>
        story.Sections
            .OrderBy(section => section.Order)
            .SelectMany(section => section.Items)
            .Where(item => directions.GetValueOrDefault(item.SourceItemId)
                == requestedDirection)
            .Select(item => new ItemExposure(
                item.SourceItemId,
                WordCount(item.Text)))
            .ToList();

    private static void AddFramingFinding(
        ICollection<NarrativeBiasFinding> findings,
        IReadOnlyList<NarrativeFramingSignal> signals,
        NarrativeFramingDirection direction,
        BiasCategory category,
        string message,
        string recommendation)
    {
        var matching = signals.Where(signal => signal.Direction == direction).ToArray();
        if (matching.Length < 2)
        {
            return;
        }

        findings.Add(new NarrativeBiasFinding(
            category,
            matching.Length >= 4 ? BiasRiskLevel.High : BiasRiskLevel.Medium,
            null,
            message,
            recommendation,
            [$"Detected {matching.Length} bounded {direction.ToString().ToLowerInvariant()} framing signals."]));
    }

    private static NarrativeBiasFinding? EvaluateEmphasis(
        IReadOnlyList<ItemExposure> positiveItems,
        IReadOnlyList<ItemExposure> negativeItems,
        IReadOnlyList<NarrativeFramingSignal> signals)
    {
        var positiveAverage = positiveItems.Average(item => item.WordCount);
        var negativeAverage = negativeItems.Average(item => item.WordCount);
        var positiveSignals = signals.Count(signal =>
            signal.Direction == NarrativeFramingDirection.Positive);
        var negativeSignals = signals.Count(signal =>
            signal.Direction == NarrativeFramingDirection.Negative);

        var positiveDominates = IsMateriallyLarger(
            positiveAverage,
            negativeAverage,
            positiveSignals,
            negativeSignals);
        var negativeDominates = IsMateriallyLarger(
            negativeAverage,
            positiveAverage,
            negativeSignals,
            positiveSignals);
        if (!positiveDominates && !negativeDominates)
        {
            return null;
        }

        var dominant = positiveDominates ? "positive" : "negative";
        var dominantAverage = positiveDominates ? positiveAverage : negativeAverage;
        var otherAverage = positiveDominates ? negativeAverage : positiveAverage;
        return new NarrativeBiasFinding(
            BiasCategory.SelectiveEmphasis,
            dominantAverage >= otherAverage * 4
                ? BiasRiskLevel.High
                : BiasRiskLevel.Medium,
            null,
            $"The mixed story gives materially greater exposure to {dominant} findings.",
            positiveDominates
                ? "Give validated negative counter-signals proportionate visibility."
                : "Give validated positive findings proportionate visibility.",
            [FormattableString.Invariant(
                $"Average {dominant} item exposure is {dominantAverage:F1} words versus {otherAverage:F1} words for the other direction.")]);
    }

    private static bool IsMateriallyLarger(
        double dominantAverage,
        double otherAverage,
        int dominantSignals,
        int otherSignals) =>
        dominantAverage - otherAverage >= 10
        && (dominantAverage >= otherAverage * 2.5
            || dominantSignals - otherSignals >= 2
            && dominantAverage >= otherAverage * 1.75);

    private static int WordCount(string text) =>
        text.Split((char[]?)null, StringSplitOptions.RemoveEmptyEntries).Length;

    private sealed record ItemExposure(string SourceItemId, int WordCount);
}
