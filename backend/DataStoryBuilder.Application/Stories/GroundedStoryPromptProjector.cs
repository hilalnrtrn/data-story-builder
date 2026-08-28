using System.Text.Json;

namespace DataStoryBuilder.Application.Stories;

public static class GroundedStoryPromptProjector
{
    private static readonly string[] StoryItemCollections =
    [
        "context",
        "contributors",
        "secondaryFindings",
        "counterSignals",
        "associatedSignals",
        "risks"
    ];

    public static GroundedStoryPromptInput Create(
        JsonElement analyticsResponse,
        string outputLanguage = StoryGenerationLanguage.Default)
    {
        var normalizedLanguage = StoryGenerationLanguage.RequireSupported(
            outputLanguage);
        RequireObject(analyticsResponse, "analytics response");
        var storyPlan = GetObject(analyticsResponse, "storyPlan");
        var itemLookup = BuildStoryItemLookup(storyPlan);
        var limitationLookup = BuildLimitationLookup(storyPlan);
        var insightLookup = BuildObjectLookup(
            GetArray(analyticsResponse, "insights"),
            "id",
            "insight");
        var integrityLookup = BuildObjectLookup(
            GetArray(analyticsResponse, "insightIntegrity"),
            "insightId",
            "integrity evaluation");

        var sections = new List<GroundedStorySection>();
        var findings = new List<GroundedStoryFinding>();
        var limitations = new List<GroundedStoryLimitation>();
        var selectedInsightIds = new HashSet<string>(StringComparer.Ordinal);
        var projectedItemIds = new HashSet<string>(StringComparer.Ordinal);

        foreach (var sectionJson in GetArray(storyPlan, "outline").EnumerateArray())
        {
            RequireObject(sectionJson, "story section");
            var sectionType = GetString(sectionJson, "type");
            var sourceItemIds = GetStringArray(sectionJson, "itemIds");
            sections.Add(new GroundedStorySection(
                GetInt32(sectionJson, "order"),
                sectionType,
                sourceItemIds));

            foreach (var sourceItemId in sourceItemIds)
            {
                if (!projectedItemIds.Add(sourceItemId))
                {
                    throw new JsonException(
                        $"Story source item '{sourceItemId}' appears more than once in the outline.");
                }

                if (sectionType == "LIMITATIONS")
                {
                    if (!limitationLookup.TryGetValue(sourceItemId, out var limitation))
                    {
                        throw new JsonException(
                            $"Missing Story Plan limitation '{sourceItemId}'.");
                    }

                    limitations.Add(ProjectLimitation(limitation));
                    continue;
                }

                if (!itemLookup.TryGetValue(sourceItemId, out var item))
                {
                    throw new JsonException(
                        $"Missing Story Plan item '{sourceItemId}'.");
                }

                var insightId = GetString(item, "insightId");
                if (!insightLookup.TryGetValue(insightId, out var insight))
                {
                    throw new JsonException(
                        $"Story Plan item '{sourceItemId}' references missing insight '{insightId}'.");
                }

                findings.Add(ProjectFinding(
                    item,
                    insight,
                    integrityLookup.GetValueOrDefault(insightId)));
                selectedInsightIds.Add(insightId);
            }
        }

        var constraints = ProjectConstraints(storyPlan, selectedInsightIds);

        return new GroundedStoryPromptInput(
            GetString(storyPlan, "analysisId"),
            GetString(storyPlan, "plannerVersion"),
            sections.ToArray(),
            findings.ToArray(),
            constraints,
            limitations.ToArray(),
            GetBoolean(storyPlan, "interpretationLimited"),
            normalizedLanguage);
    }

    private static Dictionary<string, JsonElement> BuildStoryItemLookup(
        JsonElement storyPlan)
    {
        var lookup = new Dictionary<string, JsonElement>(StringComparer.Ordinal);
        AddUnique(lookup, GetObject(storyPlan, "mainOutcome"), "story item");

        foreach (var propertyName in StoryItemCollections)
        {
            foreach (var item in GetArray(storyPlan, propertyName).EnumerateArray())
            {
                AddUnique(lookup, item, "story item");
            }
        }

        return lookup;
    }

    private static Dictionary<string, JsonElement> BuildLimitationLookup(
        JsonElement storyPlan)
    {
        var lookup = new Dictionary<string, JsonElement>(StringComparer.Ordinal);
        foreach (var item in GetArray(storyPlan, "missingContext").EnumerateArray())
        {
            AddUnique(lookup, item, "missing-context item");
        }
        return lookup;
    }

    private static Dictionary<string, JsonElement> BuildObjectLookup(
        JsonElement array,
        string idProperty,
        string itemName)
    {
        var lookup = new Dictionary<string, JsonElement>(StringComparer.Ordinal);
        foreach (var item in array.EnumerateArray())
        {
            RequireObject(item, itemName);
            var id = GetString(item, idProperty);
            if (!lookup.TryAdd(id, item))
            {
                throw new JsonException($"Duplicate {itemName} id '{id}'.");
            }
        }
        return lookup;
    }

    private static void AddUnique(
        IDictionary<string, JsonElement> lookup,
        JsonElement item,
        string itemName)
    {
        RequireObject(item, itemName);
        var id = GetString(item, "id");
        if (!lookup.TryAdd(id, item))
        {
            throw new JsonException($"Duplicate {itemName} id '{id}'.");
        }
    }

    private static GroundedStoryFinding ProjectFinding(
        JsonElement item,
        JsonElement insight,
        JsonElement integrity)
    {
        var evidenceLookup = BuildObjectLookup(
            GetArray(insight, "evidence"),
            "code",
            "evidence");
        var evidence = new List<GroundedStoryEvidence>();
        foreach (var code in GetStringArray(item, "evidenceCodes"))
        {
            if (!evidenceLookup.TryGetValue(code, out var evidenceItem))
            {
                throw new JsonException(
                    $"Insight '{GetString(insight, "id")}' is missing referenced evidence '{code}'.");
            }

            evidence.Add(new GroundedStoryEvidence(
                code,
                GetString(evidenceItem, "label"),
                GetProperty(evidenceItem, "value").Clone(),
                GetOptionalString(evidenceItem, "unit")));
        }

        var requiresQualification = GetBoolean(item, "requiresQualification");
        var qualificationReasons = Array.Empty<string>();
        if (requiresQualification)
        {
            if (integrity.ValueKind != JsonValueKind.Object)
            {
                throw new JsonException(
                    $"Qualified insight '{GetString(insight, "id")}' is missing integrity information.");
            }
            qualificationReasons = GetStringArray(integrity, "reasons");
        }

        return new GroundedStoryFinding(
            GetString(item, "id"),
            GetString(insight, "id"),
            GetString(item, "role"),
            GetString(insight, "type"),
            GetString(insight, "metric"),
            GetOptionalString(insight, "dimension"),
            GetOptionalString(insight, "segment"),
            GetObject(insight, "period").Clone(),
            GetString(insight, "direction"),
            GetObject(insight, "values").Clone(),
            evidence.ToArray(),
            requiresQualification,
            qualificationReasons,
            GetOptionalDouble(insight, "confidence"));
    }

    private static GroundedStoryLimitation ProjectLimitation(JsonElement item) =>
        new(
            GetString(item, "id"),
            GetString(item, "insightId"),
            GetString(item, "field"),
            GetString(item, "status"),
            GetString(item, "reason"));

    private static IReadOnlyList<GroundedCausalityConstraint> ProjectConstraints(
        JsonElement storyPlan,
        ISet<string> selectedInsightIds)
    {
        var result = new List<GroundedCausalityConstraint>();
        foreach (var item in GetArray(storyPlan, "causalityConstraints").EnumerateArray())
        {
            var sourceId = GetString(item, "sourceInsightId");
            var targetId = GetString(item, "targetInsightId");
            if (!selectedInsightIds.Contains(sourceId)
                || !selectedInsightIds.Contains(targetId))
            {
                continue;
            }

            result.Add(new GroundedCausalityConstraint(
                GetString(item, "relationshipId"),
                sourceId,
                targetId,
                GetString(item, "claimType"),
                GetBoolean(item, "associationPresent"),
                GetBoolean(item, "causalityEstablished"),
                GetString(item, "status"),
                GetStringArray(item, "allowedConcepts"),
                GetStringArray(item, "forbiddenConcepts"),
                GetStringArray(item, "reasons")));
        }
        return result.ToArray();
    }

    private static JsonElement GetProperty(JsonElement parent, string name)
    {
        if (!parent.TryGetProperty(name, out var property))
        {
            throw new JsonException($"Required property '{name}' is missing.");
        }
        return property;
    }

    private static JsonElement GetObject(JsonElement parent, string name)
    {
        var property = GetProperty(parent, name);
        RequireObject(property, name);
        return property;
    }

    private static JsonElement GetArray(JsonElement parent, string name)
    {
        var property = GetProperty(parent, name);
        if (property.ValueKind != JsonValueKind.Array)
        {
            throw new JsonException($"Property '{name}' must be an array.");
        }
        return property;
    }

    private static void RequireObject(JsonElement value, string name)
    {
        if (value.ValueKind != JsonValueKind.Object)
        {
            throw new JsonException($"'{name}' must be an object.");
        }
    }

    private static string GetString(JsonElement parent, string name)
    {
        var property = GetProperty(parent, name);
        if (property.ValueKind != JsonValueKind.String
            || string.IsNullOrWhiteSpace(property.GetString()))
        {
            throw new JsonException($"Property '{name}' must be a non-empty string.");
        }
        return property.GetString()!;
    }

    private static string? GetOptionalString(JsonElement parent, string name)
    {
        var property = GetProperty(parent, name);
        return property.ValueKind == JsonValueKind.Null
            ? null
            : property.GetString();
    }

    private static bool GetBoolean(JsonElement parent, string name) =>
        GetProperty(parent, name).GetBoolean();

    private static double? GetOptionalDouble(JsonElement parent, string name)
    {
        if (!parent.TryGetProperty(name, out var property)
            || property.ValueKind == JsonValueKind.Null)
        {
            return null;
        }

        if (property.ValueKind != JsonValueKind.Number
            || !property.TryGetDouble(out var value))
        {
            throw new JsonException(
                $"Property '{name}' must be a number or null.");
        }

        return value;
    }

    private static int GetInt32(JsonElement parent, string name) =>
        GetProperty(parent, name).GetInt32();

    private static string[] GetStringArray(JsonElement parent, string name) =>
        GetArray(parent, name)
            .EnumerateArray()
            .Select(item => item.GetString()
                ?? throw new JsonException($"Property '{name}' contains a null value."))
            .ToArray();
}
