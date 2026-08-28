using System.Text;
using System.Text.Json;

namespace DataStoryBuilder.Application.Stories;

public sealed class GroundedPromptBuilder
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
        WriteIndented = true
    };

    public string Build(GroundedStoryPromptInput input)
        => Build(input, []);

    public string Build(
        GroundedStoryPromptInput input,
        IReadOnlyList<string> auditFeedback)
    {
        ArgumentNullException.ThrowIfNull(input);
        ArgumentNullException.ThrowIfNull(auditFeedback);

        var prompt = new StringBuilder();
        prompt.AppendLine("SYSTEM / RULES");
        prompt.AppendLine("You are an executive business narrative generator.");
        prompt.AppendLine("Use only the supplied validated information.");
        prompt.AppendLine("Do not analyze data or calculate new values.");
        prompt.AppendLine("Do not introduce new numerical values, facts, profitability claims, unsupported adjectives, or recommendations.");
        prompt.AppendLine("Do not select, omit, or reorder findings contrary to the supplied story structure.");
        prompt.AppendLine("Do not infer causes or use causal wording where forbidden.");
        prompt.AppendLine("Preserve required qualifications, counter-signals, associations, and missing-context limitations.");
        prompt.AppendLine("PRIMARY_CONTRIBUTOR and ASSOCIATED_SIGNAL are distinct; association is not a driver or cause.");
        prompt.AppendLine("Use concise, neutral, evidence-aware executive language.");
        prompt.AppendLine(input.OutputLanguage switch
        {
            StoryGenerationLanguage.Turkish =>
                "Write the title, executiveSummary, and every generated story item text in Turkish.",
            StoryGenerationLanguage.English =>
                "Write the title, executiveSummary, and every generated story item text in English.",
            _ => throw new ArgumentException(
                "The grounded story output language is not supported.",
                nameof(input))
        });
        prompt.AppendLine("The language instruction changes only natural-language wording; preserve section order, type, sourceItemId, evidence, analytical values, qualifications, counter-signals, causality constraints, and limitations exactly.");
        prompt.AppendLine("Title and executiveSummary are wording-only and must add no new meaning.");
        prompt.AppendLine("Return only the required GeneratedExecutiveStory structure.");
        AppendJson(prompt, "STORY STRUCTURE", input.Sections);
        AppendJson(prompt, "VALIDATED FINDINGS", input.Findings);
        AppendJson(prompt, "CAUSALITY CONSTRAINTS", input.CausalityConstraints);
        AppendJson(prompt, "LIMITATIONS", input.Limitations);
        if (auditFeedback.Count > 0)
        {
            AppendJson(
                prompt,
                "REGENERATION AUDIT FEEDBACK",
                auditFeedback.Distinct(StringComparer.Ordinal).ToArray());
            prompt.AppendLine("Revise the story using only this deterministic audit feedback and the supplied grounded information.");
        }
        prompt.AppendLine("OUTPUT CONTRACT");
        prompt.AppendLine("GeneratedExecutiveStory: { title, executiveSummary, sections[] }");
        prompt.AppendLine("Each section: { order, type, items[] }");
        prompt.AppendLine("Each item: { sourceItemId, text }");
        prompt.Append("Preserve every supplied section order, type, and sourceItemId exactly.");
        return prompt.ToString();
    }

    private static void AppendJson(StringBuilder prompt, string heading, object value)
    {
        prompt.AppendLine(heading);
        prompt.AppendLine(JsonSerializer.Serialize(value, JsonOptions));
    }
}
