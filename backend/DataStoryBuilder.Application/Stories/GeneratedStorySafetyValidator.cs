using System.Diagnostics.CodeAnalysis;

namespace DataStoryBuilder.Application.Stories;

public sealed class GeneratedStorySafetyValidator
{
    private static readonly IReadOnlyDictionary<string, string[]> CausalPhrases =
        new Dictionary<string, string[]>(StringComparer.Ordinal)
        {
            ["CAUSED"] = ["caused", "cause"],
            ["LED_TO"] = ["led to"],
            ["BECAUSE_OF"] = ["because of"],
            ["RESULTED_IN"] = ["resulted in"],
            ["DRIVEN_BY"] = ["driven by", "drives", "drove"]
        };

    public void Validate(
        GeneratedExecutiveStory story,
        GroundedStoryPromptInput groundedInput)
    {
        ArgumentNullException.ThrowIfNull(story);
        ArgumentNullException.ThrowIfNull(groundedInput);

        RejectAmbiguousGroundedIds(groundedInput.Sections);

        if (story.Sections.Count != groundedInput.Sections.Count)
        {
            Reject("Generated section count does not match the grounded structure.");
        }

        for (var index = 0; index < groundedInput.Sections.Count; index++)
        {
            ValidateSection(story.Sections[index], groundedInput.Sections[index]);
        }

        ValidateLimitations(story, groundedInput);
        ValidateCausalLanguage(story, groundedInput.CausalityConstraints);
    }

    private static void ValidateSection(
        GeneratedStorySection generated,
        GroundedStorySection grounded)
    {
        if (generated.Order != grounded.Order)
        {
            Reject("Generated section order does not match the grounded structure.");
        }

        if (!string.Equals(generated.Type, grounded.Type, StringComparison.Ordinal))
        {
            Reject("Generated section type does not match the grounded structure.");
        }

        var expectedIds = grounded.SourceItemIds.ToHashSet(StringComparer.Ordinal);
        var generatedIds = generated.Items
            .Select(item => item.SourceItemId)
            .ToArray();

        if (generatedIds.Length != generatedIds.Distinct(StringComparer.Ordinal).Count())
        {
            Reject("Generated SourceItemId values must be unique within a section.");
        }

        if (generatedIds.Any(id => !expectedIds.Contains(id)))
        {
            Reject("Generated section contains an unknown or misplaced SourceItemId.");
        }

        if (generatedIds.Length != expectedIds.Count
            || expectedIds.Any(id => !generatedIds.Contains(id, StringComparer.Ordinal)))
        {
            Reject("Generated section omits a required SourceItemId.");
        }
    }

    private static void RejectAmbiguousGroundedIds(
        IReadOnlyList<GroundedStorySection> sections)
    {
        var seen = new HashSet<string>(StringComparer.Ordinal);
        foreach (var section in sections)
        {
            foreach (var sourceItemId in section.SourceItemIds)
            {
                if (!seen.Add(sourceItemId))
                {
                    Reject("Grounded SourceItemId is ambiguous across sections.");
                }
            }
        }
    }

    private static void ValidateLimitations(
        GeneratedExecutiveStory story,
        GroundedStoryPromptInput groundedInput)
    {
        if (groundedInput.Limitations.Count == 0)
        {
            return;
        }

        var limitationSection = story.Sections.SingleOrDefault(
            section => section.Type == "LIMITATIONS");
        if (limitationSection is null)
        {
            Reject("Required LIMITATIONS section is missing.");
        }

        var limitationIds = limitationSection.Items
            .Select(item => item.SourceItemId)
            .ToHashSet(StringComparer.Ordinal);
        if (groundedInput.Limitations.Any(
            limitation => !limitationIds.Contains(limitation.SourceItemId)))
        {
            Reject("Generated story omits a required limitation.");
        }
    }

    private static void ValidateCausalLanguage(
        GeneratedExecutiveStory story,
        IReadOnlyList<GroundedCausalityConstraint> constraints)
    {
        var forbiddenPhrases = constraints
            .Where(constraint => !constraint.CausalityEstablished)
            .SelectMany(constraint => constraint.ForbiddenConcepts)
            .Distinct(StringComparer.Ordinal)
            .SelectMany(concept => CausalPhrases.GetValueOrDefault(concept) ?? [])
            .Distinct(StringComparer.OrdinalIgnoreCase)
            .ToArray();

        if (forbiddenPhrases.Length == 0)
        {
            return;
        }

        foreach (var text in EnumerateGeneratedText(story))
        {
            if (forbiddenPhrases.Any(phrase => ContainsPhrase(text, phrase)))
            {
                Reject("Generated story contains causal wording forbidden by the grounded constraints.");
            }
        }
    }

    private static IEnumerable<string> EnumerateGeneratedText(
        GeneratedExecutiveStory story)
    {
        yield return story.Title;
        yield return story.ExecutiveSummary;
        foreach (var item in story.Sections.SelectMany(section => section.Items))
        {
            yield return item.Text;
        }
    }

    private static bool ContainsPhrase(string text, string phrase)
    {
        var startIndex = 0;
        while (startIndex < text.Length)
        {
            var index = text.IndexOf(
                phrase,
                startIndex,
                StringComparison.OrdinalIgnoreCase);
            if (index < 0)
            {
                return false;
            }

            var beforeIsLetter = index > 0 && char.IsLetter(text[index - 1]);
            var end = index + phrase.Length;
            var afterIsLetter = end < text.Length && char.IsLetter(text[end]);
            if (!beforeIsLetter && !afterIsLetter)
            {
                return true;
            }

            startIndex = index + 1;
        }

        return false;
    }

    [DoesNotReturn]
    private static void Reject(string message) =>
        throw new GeneratedStorySafetyException(message);
}
