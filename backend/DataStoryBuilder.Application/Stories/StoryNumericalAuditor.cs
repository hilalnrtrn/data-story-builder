using System.Globalization;
using System.Text.Json;
using System.Text.RegularExpressions;

namespace DataStoryBuilder.Application.Stories;

public static partial class StoryNumericalAuditor
{
    private const NumberStyles NumericStyles =
        NumberStyles.AllowLeadingSign | NumberStyles.AllowDecimalPoint;

    public static IReadOnlyList<StoryItemNumericalAudit> Audit(
        IReadOnlyList<StoryItemAuditSource> sources)
    {
        ArgumentNullException.ThrowIfNull(sources);

        return sources
            .Where(source => source.IsResolved && !source.IsLimitation)
            .Select(AuditSource)
            .ToArray();
    }

    public static IReadOnlyList<StoryNumericToken> ExtractTokens(string text)
    {
        ArgumentNullException.ThrowIfNull(text);
        var dateRanges = IsoDateRegex().Matches(text)
            .Select(match => (match.Index, End: match.Index + match.Length))
            .ToArray();
        var result = new List<StoryNumericToken>();

        foreach (Match match in NumericTokenRegex().Matches(text))
        {
            if (dateRanges.Any(range =>
                match.Index < range.End
                && match.Index + match.Length > range.Index))
            {
                continue;
            }

            var isPercent = match.Value.EndsWith('%');
            var numericText = match.Value
                .TrimEnd('%')
                .Replace(",", string.Empty, StringComparison.Ordinal);
            if (!decimal.TryParse(
                numericText,
                NumericStyles,
                CultureInfo.InvariantCulture,
                out var value))
            {
                continue;
            }

            if (!isPercent
                && decimal.Truncate(value) == value
                && value is >= 1900 and <= 2199
                && match.Value.Length == 4)
            {
                continue;
            }

            result.Add(new StoryNumericToken(match.Value, value, isPercent));
        }

        return result;
    }

    private static StoryItemNumericalAudit AuditSource(StoryItemAuditSource source)
    {
        var tokens = ExtractTokens(source.GeneratedText);
        var evidence = source.ResolvedEvidence
            .Select(ToNumericEvidence)
            .Where(item => item is not null)
            .Select(item => item!.Value)
            .ToArray();
        var unsupported = tokens
            .Where(token => !evidence.Any(item => Matches(token, item)))
            .Select(token => new StoryNumericalMismatch(
                source.SourceItemId,
                token.OriginalText,
                token.NormalizedValue,
                token.IsPercent,
                "The generated numeric token is not supported by numerical evidence for the same source item."))
            .ToArray();

        return new StoryItemNumericalAudit(
            source.SourceItemId,
            tokens,
            unsupported);
    }

    private static NumericEvidence? ToNumericEvidence(
        GroundedStoryEvidence evidence)
    {
        if (evidence.Value.ValueKind != JsonValueKind.Number
            || !evidence.Value.TryGetDecimal(out var value))
        {
            return null;
        }

        return new NumericEvidence(value, evidence.Unit);
    }

    private static bool Matches(StoryNumericToken token, NumericEvidence evidence)
    {
        if (token.IsPercent)
        {
            if (string.Equals(evidence.Unit, "PERCENT", StringComparison.Ordinal))
            {
                return Math.Abs(token.NormalizedValue)
                    == Math.Abs(evidence.Value);
            }

            return string.Equals(evidence.Unit, "RATIO", StringComparison.Ordinal)
                && token.NormalizedValue / 100m == evidence.Value;
        }

        if (string.Equals(evidence.Unit, "RATIO", StringComparison.Ordinal))
        {
            return token.NormalizedValue == evidence.Value;
        }

        return evidence.Unit is null
            && token.NormalizedValue == evidence.Value;
    }

    private readonly record struct NumericEvidence(decimal Value, string? Unit);

    [GeneratedRegex(
        @"(?<![\p{L}\p{N}_])[-+]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?%?(?![\p{L}\p{N}_])",
        RegexOptions.CultureInvariant)]
    private static partial Regex NumericTokenRegex();

    [GeneratedRegex(
        @"(?<!\d)\d{4}-\d{2}(?:-\d{2})?(?!\d)",
        RegexOptions.CultureInvariant)]
    private static partial Regex IsoDateRegex();
}
