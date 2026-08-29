using System.Text;
using System.Text.Json;

namespace DataStoryBuilder.Application.Stories;

public static class StorySemanticSafetyAuditor
{
    private sealed record BusinessConcept(
        string Name,
        string[] NarrativeTerms,
        string[] GroundingTerms);

    private static readonly string[] UpTerms =
    [
        "increase", "increased", "increasing", "grew", "growth", "rose", "rising",
        "artti", "artis", "yukseldi", "yukselis"
    ];

    private static readonly string[] DownTerms =
    [
        "decrease", "decreased", "decreasing", "decline", "declined", "fell", "falling",
        "dropped", "azaldi", "azalis", "dustu", "dusus", "geriledi"
    ];

    private static readonly BusinessConcept[] MaterialBusinessConcepts =
    [
        new(
            "customer satisfaction",
            ["customer satisfaction", "musteri memnuniyeti"],
            ["customer satisfaction", "customersatisfaction", "musteri memnuniyeti"]),
        new(
            "employee productivity",
            ["employee productivity", "calisan verimliligi", "personel verimliligi"],
            ["employee productivity", "employeeproductivity", "calisan verimliligi", "personel verimliligi"]),
        new(
            "profitability",
            ["profitability", "profit margin", "karlilik", "kar marji"],
            ["profitability", "profit margin", "profitmargin", "karlilik", "kar marji"]),
        new(
            "pricing",
            ["price increase", "prices increased", "prices were raised", "pricing change", "fiyat artisi", "fiyatlar arttirildi"],
            ["unitprice", "pricingchange", "price", "pricing", "fiyat"])
    ];

    public static IReadOnlyList<string> Audit(
        GeneratedStoryItem generated,
        GroundedStoryFinding grounded,
        GroundedStoryPromptInput groundedInput)
    {
        ArgumentNullException.ThrowIfNull(generated);
        ArgumentNullException.ThrowIfNull(grounded);
        ArgumentNullException.ThrowIfNull(groundedInput);

        var reasons = new List<string>();
        var normalizedText = Normalize(generated.Text);
        var normalizedDirection = grounded.Direction.Trim().ToUpperInvariant();
        var contradictoryTerms = normalizedDirection switch
        {
            "UP" or "HIGH" or "INCREASE" => DownTerms,
            "DOWN" or "LOW" or "DECREASE" => UpTerms,
            _ => []
        };
        var directionTerm = contradictoryTerms.FirstOrDefault(term =>
            ContainsTerm(normalizedText, term));
        if (directionTerm is not null)
        {
            reasons.Add(
                $"{StoryDataDiffResult.SemanticSafetyReasonPrefix} Generated wording '{directionTerm}' contradicts grounded direction '{grounded.Direction}'.");
        }

        var grounding = Normalize(BuildGroundingText(grounded, groundedInput));
        foreach (var concept in MaterialBusinessConcepts)
        {
            var narrativeTerm = concept.NarrativeTerms
                .Select(Normalize)
                .FirstOrDefault(term => ContainsTerm(normalizedText, term));
            if (narrativeTerm is null || concept.GroundingTerms
                    .Select(Normalize)
                    .Any(term => ContainsTerm(grounding, term)))
            {
                continue;
            }

            reasons.Add(
                $"{StoryDataDiffResult.SemanticSafetyReasonPrefix} Generated item introduces unsupported business concept '{concept.Name}' absent from its grounded source and evidence.");
        }

        return reasons;
    }

    private static string BuildGroundingText(
        GroundedStoryFinding finding,
        GroundedStoryPromptInput input)
    {
        var values = new List<string>
        {
            finding.InsightType,
            finding.Metric,
            finding.Dimension ?? string.Empty,
            finding.Segment ?? string.Empty,
            finding.Direction,
            finding.Values.GetRawText(),
            finding.Period.GetRawText()
        };
        values.AddRange(finding.Evidence.SelectMany(evidence => new[]
        {
            evidence.Code,
            evidence.Label,
            evidence.Unit ?? string.Empty,
            evidence.Value.GetRawText()
        }));
        values.AddRange(input.CausalityConstraints
            .Where(constraint => constraint.SourceInsightId == finding.InsightId
                || constraint.TargetInsightId == finding.InsightId)
            .SelectMany(constraint => constraint.AllowedConcepts
                .Concat(constraint.ForbiddenConcepts)
                .Append(constraint.Status)));
        values.AddRange(input.Limitations
            .Where(limitation => limitation.InsightId == finding.InsightId)
            .SelectMany(limitation => new[]
            {
                limitation.Field,
                limitation.Status,
                limitation.Reason
            }));
        return string.Join(' ', values);
    }

    private static string Normalize(string value)
    {
        var decomposed = value.ToLowerInvariant().Normalize(NormalizationForm.FormD);
        var builder = new StringBuilder(decomposed.Length);
        foreach (var character in decomposed)
        {
            if (System.Globalization.CharUnicodeInfo.GetUnicodeCategory(character)
                == System.Globalization.UnicodeCategory.NonSpacingMark)
            {
                continue;
            }

            builder.Append(character == 'ı'
                ? 'i'
                : char.IsLetterOrDigit(character) ? character : ' ');
        }

        return string.Join(' ', builder.ToString()
            .Split(' ', StringSplitOptions.RemoveEmptyEntries));
    }

    private static bool ContainsTerm(string text, string term) =>
        $" {text} ".Contains($" {term} ", StringComparison.Ordinal);
}
