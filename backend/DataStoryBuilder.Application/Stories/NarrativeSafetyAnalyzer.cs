namespace DataStoryBuilder.Application.Stories;

public static class NarrativeSafetyAnalyzer
{
    private const double HighConfidenceThreshold = 0.80;

    private static readonly string[] CertaintyPhrases =
    [
        "clearly proves",
        "definitely proves",
        "undeniably proves",
        "conclusively proves",
        "clearly demonstrates",
        "definitely demonstrates",
        "undeniably demonstrates",
        "conclusively demonstrates",
        "certainly caused",
        "definitely caused",
        "unquestionably",
        "without doubt"
    ];

    private static readonly IReadOnlyDictionary<string, string[]> CausalPhrases =
        new Dictionary<string, string[]>(StringComparer.Ordinal)
        {
            ["CAUSED"] = ["caused", "caused by"],
            ["LED_TO"] = ["led to"],
            ["BECAUSE_OF"] = ["because of"],
            ["RESULTED_IN"] = ["resulted in"],
            ["DRIVEN_BY"] = ["drove", "driven by", "drives"]
        };

    private static readonly IReadOnlyDictionary<string, string[]> ContextExplanationPhrases =
        new Dictionary<string, string[]>(StringComparer.OrdinalIgnoreCase)
        {
            ["UnitPrice"] =
            [
                "higher prices",
                "price increase",
                "prices increased",
                "selling prices increased"
            ],
            ["PricingChange"] =
            [
                "higher prices",
                "price increase",
                "prices increased",
                "pricing change"
            ]
        };

    public static IReadOnlyList<NarrativeBiasFinding> Analyze(
        GeneratedExecutiveStory story,
        GroundedStoryPromptInput groundedInput)
    {
        ArgumentNullException.ThrowIfNull(story);
        ArgumentNullException.ThrowIfNull(groundedInput);

        var findings = new List<NarrativeBiasFinding>();
        var generatedItems = story.Sections
            .OrderBy(section => section.Order)
            .SelectMany(section => section.Items)
            .ToArray();
        var generatedLookup = generatedItems.ToDictionary(
            item => item.SourceItemId,
            StringComparer.Ordinal);

        EvaluateCertainty(
            findings,
            story.ExecutiveSummary,
            groundedInput.Findings,
            generatedLookup);
        EvaluateCausality(findings, story, groundedInput, generatedItems);
        EvaluateContext(findings, story, groundedInput, generatedLookup);

        return DistinctFindings(findings);
    }

    private static void EvaluateCertainty(
        ICollection<NarrativeBiasFinding> findings,
        string executiveSummary,
        IEnumerable<GroundedStoryFinding> groundedFindings,
        IReadOnlyDictionary<string, GeneratedStoryItem> generatedLookup)
    {
        var groundedArray = groundedFindings.ToArray();
        foreach (var grounded in groundedArray)
        {
            if (!generatedLookup.TryGetValue(grounded.SourceItemId, out var generated))
            {
                continue;
            }

            var matched = CertaintyPhrases
                .Where(phrase => ContainsPhrase(generated.Text, phrase))
                .ToArray();
            if (matched.Length == 0)
            {
                continue;
            }

            var usesProofLanguage = matched.Any(phrase => phrase.Contains(
                "proves",
                StringComparison.Ordinal));
            var confidenceIsBelowHigh = grounded.Confidence is not null
                && grounded.Confidence < HighConfidenceThreshold;
            if (!usesProofLanguage
                && !grounded.RequiresQualification
                && !confidenceIsBelowHigh)
            {
                continue;
            }

            var reasons = new List<string>
            {
                $"Detected strong certainty phrase '{matched[0]}'."
            };
            if (grounded.Confidence is not null)
            {
                reasons.Add(FormattableString.Invariant(
                    $"Grounded confidence {grounded.Confidence.Value:F2} is compared with the explicit high-confidence threshold {HighConfidenceThreshold:F2}."));
            }
            if (grounded.RequiresQualification)
            {
                reasons.Add("The grounded finding requires qualification.");
                reasons.AddRange(grounded.QualificationReasons);
            }
            if (usesProofLanguage)
            {
                reasons.Add("Proof language exceeds the ordinary analytical finding contract.");
            }

            findings.Add(new NarrativeBiasFinding(
                BiasCategory.CertaintyInflation,
                usesProofLanguage || grounded.RequiresQualification
                    ? BiasRiskLevel.High
                    : BiasRiskLevel.Medium,
                grounded.SourceItemId,
                "The generated wording expresses stronger certainty than the grounded finding supports.",
                "Use evidence-calibrated language and preserve the required qualification.",
                reasons));
        }

        var summaryMatch = CertaintyPhrases.FirstOrDefault(phrase =>
            ContainsPhrase(executiveSummary, phrase));
        if (summaryMatch is null)
        {
            return;
        }

        var summaryUsesProof = summaryMatch.Contains("proves", StringComparison.Ordinal);
        var relevant = groundedArray
            .Where(finding => summaryUsesProof
                || finding.RequiresQualification
                || finding.Confidence is not null
                && finding.Confidence < HighConfidenceThreshold)
            .OrderByDescending(finding => finding.RequiresQualification)
            .ThenBy(finding => finding.Confidence ?? double.MaxValue)
            .FirstOrDefault();
        if (relevant is null)
        {
            return;
        }

        findings.Add(new NarrativeBiasFinding(
            BiasCategory.CertaintyInflation,
            summaryUsesProof || relevant.RequiresQualification
                ? BiasRiskLevel.High
                : BiasRiskLevel.Medium,
            null,
            "The executive summary expresses stronger certainty than the grounded findings support.",
            "Use evidence-calibrated language and preserve the required qualification.",
            [$"Detected strong certainty phrase '{summaryMatch}' in the executive summary."]));
    }

    private static void EvaluateCausality(
        ICollection<NarrativeBiasFinding> findings,
        GeneratedExecutiveStory story,
        GroundedStoryPromptInput groundedInput,
        IReadOnlyList<GeneratedStoryItem> generatedItems)
    {
        var insightBySourceItem = groundedInput.Findings.ToDictionary(
            finding => finding.SourceItemId,
            finding => finding.InsightId,
            StringComparer.Ordinal);

        foreach (var constraint in groundedInput.CausalityConstraints.Where(
                     constraint => !constraint.CausalityEstablished))
        {
            var phrases = constraint.ForbiddenConcepts
                .SelectMany(concept => CausalPhrases.GetValueOrDefault(concept) ?? [])
                .Distinct(StringComparer.OrdinalIgnoreCase)
                .ToArray();
            if (phrases.Length == 0)
            {
                continue;
            }

            var relevantItems = generatedItems.Where(item =>
            {
                var insightId = insightBySourceItem.GetValueOrDefault(item.SourceItemId);
                return insightId == constraint.SourceInsightId
                    || insightId == constraint.TargetInsightId;
            });
            var texts = relevantItems
                .Select(item => (item.Text, SourceItemId: (string?)item.SourceItemId))
                .Prepend((story.ExecutiveSummary, null));
            foreach (var text in texts)
            {
                var matched = phrases.FirstOrDefault(phrase =>
                    ContainsPhrase(text.Text, phrase));
                if (matched is null)
                {
                    continue;
                }

                findings.Add(new NarrativeBiasFinding(
                    BiasCategory.CausalFraming,
                    BiasRiskLevel.High,
                    text.SourceItemId,
                    "The generated narrative uses causal framing that is blocked by the grounded causality constraint.",
                    "Use the allowed association language and state that causality is not established.",
                    [
                        $"Detected blocked causal phrase '{matched}'.",
                        $"Grounded causality status is '{constraint.Status}'.",
                        .. constraint.Reasons
                    ]));
            }
        }
    }

    private static void EvaluateContext(
        ICollection<NarrativeBiasFinding> findings,
        GeneratedExecutiveStory story,
        GroundedStoryPromptInput groundedInput,
        IReadOnlyDictionary<string, GeneratedStoryItem> generatedLookup)
    {
        if (!groundedInput.InterpretationLimited
            || groundedInput.Limitations.Count == 0)
        {
            return;
        }

        var narrativeTexts = story.Sections
            .SelectMany(section => section.Items)
            .Select(item => (item.Text, SourceItemId: (string?)item.SourceItemId))
            .Prepend((story.ExecutiveSummary, null))
            .ToArray();

        foreach (var limitation in groundedInput.Limitations)
        {
            if (!generatedLookup.ContainsKey(limitation.SourceItemId))
            {
                findings.Add(new NarrativeBiasFinding(
                    BiasCategory.MissingContextOmission,
                    BiasRiskLevel.High,
                    limitation.SourceItemId,
                    "A required structured context limitation is not visible in the generated story.",
                    "Preserve the known context limitation and avoid presenting an unavailable explanation as established.",
                    [$"The required limitation for '{limitation.Field}' is absent."]));
            }

            if (!ContextExplanationPhrases.TryGetValue(
                    limitation.Field,
                    out var blockedExplanations))
            {
                continue;
            }

            foreach (var text in narrativeTexts)
            {
                var matched = blockedExplanations.FirstOrDefault(phrase =>
                    ContainsPhrase(text.Text, phrase));
                if (matched is null
                    || text.SourceItemId == limitation.SourceItemId)
                {
                    continue;
                }

                findings.Add(new NarrativeBiasFinding(
                    BiasCategory.MissingContextOmission,
                    BiasRiskLevel.High,
                    text.SourceItemId,
                    "The narrative presents a bounded price explanation despite unavailable pricing context.",
                    "Preserve the known context limitation and avoid presenting an unavailable explanation as established.",
                    [
                        $"Detected unsupported explanation phrase '{matched}'.",
                        $"Grounded context field '{limitation.Field}' is '{limitation.Status}'."
                    ]));
            }
        }
    }

    private static IReadOnlyList<NarrativeBiasFinding> DistinctFindings(
        IEnumerable<NarrativeBiasFinding> findings)
    {
        var seen = new HashSet<string>(StringComparer.Ordinal);
        return findings.Where(finding => seen.Add(
                $"{finding.Category}|{finding.SourceItemId}|{finding.Message}"))
            .ToArray();
    }

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
            var beforeIsWord = index > 0 && char.IsLetterOrDigit(text[index - 1]);
            var afterIsWord = end < text.Length && char.IsLetterOrDigit(text[end]);
            if (!beforeIsWord && !afterIsWord)
            {
                return true;
            }

            start = index + 1;
        }

        return false;
    }
}
