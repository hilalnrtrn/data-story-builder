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

            var isPercent = match.Value.StartsWith('%')
                || match.Value.EndsWith('%');
            var numericText = NormalizeNumericText(
                match.Value.Trim('%'),
                isPercent);
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

    private static string NormalizeNumericText(
        string numericText,
        bool isPercent)
    {
        var sign = numericText.Length > 0 && numericText[0] is '-' or '+'
            ? numericText[..1]
            : string.Empty;
        var unsigned = sign.Length == 0 ? numericText : numericText[1..];

        if (isPercent && HasSingleSeparator(unsigned, out _))
        {
            return sign + unsigned.Replace(',', '.');
        }

        var decimalPoint = unsigned.LastIndexOf('.');
        if (decimalPoint > 0
            && IsClearlyGroupedInteger(unsigned[..decimalPoint], ',')
            && IsAsciiDigits(unsigned[(decimalPoint + 1)..]))
        {
            return sign
                + unsigned[..decimalPoint].Replace(",", string.Empty, StringComparison.Ordinal)
                + unsigned[decimalPoint..];
        }

        if (IsClearlyGroupedInteger(unsigned, '.'))
        {
            return sign + unsigned.Replace(".", string.Empty, StringComparison.Ordinal);
        }

        if (IsClearlyGroupedInteger(unsigned, ','))
        {
            return sign + unsigned.Replace(",", string.Empty, StringComparison.Ordinal);
        }

        var comma = unsigned.IndexOf(',');
        if (comma > 0
            && comma == unsigned.LastIndexOf(',')
            && unsigned.Length - comma - 1 is 1 or 2
            && IsAsciiDigits(unsigned[..comma])
            && IsAsciiDigits(unsigned[(comma + 1)..]))
        {
            return sign + unsigned.Replace(',', '.');
        }

        return numericText;
    }

    private static bool IsClearlyGroupedInteger(string value, char separator)
    {
        var groups = value.Split(separator);
        return groups.Length > 1
            && groups[0].Length is >= 1 and <= 3
            && IsAsciiDigits(groups[0])
            && groups.Skip(1).All(group =>
                group.Length == 3 && IsAsciiDigits(group));
    }

    private static bool IsAsciiDigits(string value) =>
        value.Length > 0 && value.All(character => character is >= '0' and <= '9');

    private static bool HasSingleSeparator(string value, out int separatorIndex)
    {
        var dotIndex = value.IndexOf('.');
        var commaIndex = value.IndexOf(',');
        separatorIndex = Math.Max(dotIndex, commaIndex);
        return separatorIndex > 0
            && value.LastIndexOf('.') == dotIndex
            && value.LastIndexOf(',') == commaIndex
            && (dotIndex < 0 || commaIndex < 0)
            && IsAsciiDigits(value[..separatorIndex])
            && IsAsciiDigits(value[(separatorIndex + 1)..]);
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

            if (!string.Equals(evidence.Unit, "RATIO", StringComparison.Ordinal))
            {
                return false;
            }

            var precision = GetDisplayedDecimalPrecision(token.OriginalText);
            return precision <= 28
                && decimal.Round(
                    evidence.Value * 100m,
                    precision,
                    MidpointRounding.AwayFromZero)
                == token.NormalizedValue;
        }

        if (string.Equals(evidence.Unit, "RATIO", StringComparison.Ordinal))
        {
            return token.NormalizedValue == evidence.Value;
        }

        return evidence.Unit is null
            && token.NormalizedValue == evidence.Value;
    }

    private static int GetDisplayedDecimalPrecision(string originalText)
    {
        var numericText = originalText.Trim('%');
        var unsigned = numericText.Length > 0 && numericText[0] is '-' or '+'
            ? numericText[1..]
            : numericText;

        if (HasSingleSeparator(unsigned, out var singleSeparatorIndex))
        {
            return unsigned.Length - singleSeparatorIndex - 1;
        }

        if (IsClearlyGroupedInteger(unsigned, '.')
            || IsClearlyGroupedInteger(unsigned, ','))
        {
            return 0;
        }

        var separatorIndex = Math.Max(
            unsigned.LastIndexOf('.'),
            unsigned.LastIndexOf(','));
        return separatorIndex < 0
            ? 0
            : unsigned.Length - separatorIndex - 1;
    }

    private readonly record struct NumericEvidence(decimal Value, string? Unit);

    [GeneratedRegex(
        @"(?<![\p{L}\p{N}_])%?[-+]?(?:\d{1,3}(?:\.\d{3})+|\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+,\d{1,2}|\d+(?:\.\d+)?)(?:%)?(?![\p{L}\p{N}_])",
        RegexOptions.CultureInvariant)]
    private static partial Regex NumericTokenRegex();

    [GeneratedRegex(
        @"(?<!\d)\d{4}-\d{2}(?:-\d{2})?(?!\d)",
        RegexOptions.CultureInvariant)]
    private static partial Regex IsoDateRegex();
}
