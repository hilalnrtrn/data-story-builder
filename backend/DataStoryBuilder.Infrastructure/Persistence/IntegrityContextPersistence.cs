using System.Text.Json;
using DataStoryBuilder.Domain.Entities;

namespace DataStoryBuilder.Infrastructure.Persistence;

public sealed class IntegrityContextPersistence(
    DataStoryBuilderDbContext dbContext)
{
    public async Task PersistAsync(
        Guid analysisId,
        string analyticsResponseJson,
        CancellationToken cancellationToken = default)
    {
        using var document = JsonDocument.Parse(analyticsResponseJson);
        var root = document.RootElement;

        if (root.ValueKind != JsonValueKind.Object)
        {
            throw new JsonException(
                "The analytics response must be a JSON object.");
        }

        var integrityEvaluations = ParseIntegrityEvaluations(
            root,
            analysisId);
        var causalityEvaluations = ParseCausalityEvaluations(
            root,
            analysisId);
        var missingContextEvaluations = ParseMissingContextEvaluations(
            root,
            analysisId);

        dbContext.InsightIntegrityEvaluations.AddRange(
            integrityEvaluations);
        dbContext.CausalityEvaluations.AddRange(causalityEvaluations);
        dbContext.MissingContextEvaluations.AddRange(
            missingContextEvaluations);

        await dbContext.SaveChangesAsync(cancellationToken);
    }

    private static List<InsightIntegrityEvaluation>
        ParseIntegrityEvaluations(
            JsonElement root,
            Guid analysisId)
    {
        var evaluationsJson = GetRequiredArray(root, "insightIntegrity");
        var evaluations = new List<InsightIntegrityEvaluation>();
        var insightIds = new HashSet<string>(StringComparer.Ordinal);

        foreach (var item in evaluationsJson.EnumerateArray())
        {
            RequireObject(item, "insight integrity evaluation");
            var insightId = GetRequiredString(item, "insightId");

            if (!insightIds.Add(insightId))
            {
                throw new JsonException(
                    "Duplicate insight integrity evaluation for insight "
                    + $"'{insightId}'.");
            }

            evaluations.Add(new InsightIntegrityEvaluation
            {
                AnalysisId = analysisId,
                InsightId = insightId,
                Status = GetRequiredString(item, "status"),
                IntegrityScore = GetRequiredNullableDouble(
                    item,
                    "integrityScore"),
                StoryEligible = GetRequiredBoolean(
                    item,
                    "storyEligible"),
                RequiresQualification = GetRequiredBoolean(
                    item,
                    "requiresQualification"),
                CounterEvidenceJson = GetRequiredArray(
                    item,
                    "counterEvidence").GetRawText(),
                ContradictionsJson = GetRequiredArray(
                    item,
                    "contradictions").GetRawText(),
                OutlierCheckJson = GetRequiredNullableObjectJson(
                    item,
                    "outlierCheck"),
                OneOffCheckJson = GetRequiredNullableObjectJson(
                    item,
                    "oneOffCheck"),
                ConsistencyChecksJson = GetRequiredArray(
                    item,
                    "consistencyChecks").GetRawText(),
                IntegrityBreakdownJson = GetRequiredObject(
                    item,
                    "integrityBreakdown").GetRawText(),
                ReasonsJson = GetRequiredArray(
                    item,
                    "reasons").GetRawText()
            });
        }

        return evaluations;
    }

    private static List<CausalityEvaluation> ParseCausalityEvaluations(
        JsonElement root,
        Guid analysisId)
    {
        var evaluationsJson = GetRequiredArray(
            root,
            "causalityEvaluations");
        var evaluations = new List<CausalityEvaluation>();
        var relationshipIds = new HashSet<string>(StringComparer.Ordinal);

        foreach (var item in evaluationsJson.EnumerateArray())
        {
            RequireObject(item, "causality evaluation");
            var relationshipId = GetRequiredString(
                item,
                "relationshipId");

            if (!relationshipIds.Add(relationshipId))
            {
                throw new JsonException(
                    "Duplicate causality evaluation for relationship "
                    + $"'{relationshipId}'.");
            }

            evaluations.Add(new CausalityEvaluation
            {
                AnalysisId = analysisId,
                RelationshipId = relationshipId,
                SourceInsightId = GetRequiredString(
                    item,
                    "sourceInsightId"),
                TargetInsightId = GetRequiredString(
                    item,
                    "targetInsightId"),
                SourceMetric = GetRequiredString(item, "sourceMetric"),
                TargetMetric = GetRequiredString(item, "targetMetric"),
                Status = GetRequiredString(item, "status"),
                AssociationPresent = GetRequiredBoolean(
                    item,
                    "associationPresent"),
                CausalityEstablished = GetRequiredBoolean(
                    item,
                    "causalityEstablished"),
                CausalEvidenceJson = GetRequiredArray(
                    item,
                    "causalEvidence").GetRawText(),
                AllowedConceptsJson = GetRequiredArray(
                    item,
                    "allowedConcepts").GetRawText(),
                ForbiddenConceptsJson = GetRequiredArray(
                    item,
                    "forbiddenConcepts").GetRawText(),
                ReasonsJson = GetRequiredArray(
                    item,
                    "reasons").GetRawText()
            });
        }

        return evaluations;
    }

    private static List<MissingContextEvaluation>
        ParseMissingContextEvaluations(
            JsonElement root,
            Guid analysisId)
    {
        var summariesByInsightId = ParseContextSummaries(root);
        var evaluationsJson = GetRequiredArray(
            root,
            "missingContextEvaluations");
        var evaluations = new List<MissingContextEvaluation>();
        var insightIds = new HashSet<string>(StringComparer.Ordinal);

        foreach (var item in evaluationsJson.EnumerateArray())
        {
            RequireObject(item, "missing context evaluation");
            var insightId = GetRequiredString(item, "insightId");

            if (!insightIds.Add(insightId))
            {
                throw new JsonException(
                    "Duplicate missing context evaluation for insight "
                    + $"'{insightId}'.");
            }

            if (!summariesByInsightId.TryGetValue(
                insightId,
                out var summary))
            {
                throw new JsonException(
                    "A context summary is required for insight "
                    + $"'{insightId}'.");
            }

            evaluations.Add(new MissingContextEvaluation
            {
                AnalysisId = analysisId,
                InsightId = insightId,
                InterpretationLimited = GetRequiredBoolean(
                    item,
                    "interpretationLimited"),
                MissingContextJson = GetRequiredArray(
                    item,
                    "missingContext").GetRawText(),
                ReasonsJson = GetRequiredArray(
                    item,
                    "reasons").GetRawText(),
                ContextSummaryJson = summary.GetRawText()
            });
        }

        if (summariesByInsightId.Count != insightIds.Count)
        {
            throw new JsonException(
                "Each context summary must match one missing context "
                + "evaluation.");
        }

        return evaluations;
    }

    private static Dictionary<string, JsonElement> ParseContextSummaries(
        JsonElement root)
    {
        var summariesJson = GetRequiredArray(root, "contextSummaries");
        var summaries = new Dictionary<string, JsonElement>(
            StringComparer.Ordinal);

        foreach (var item in summariesJson.EnumerateArray())
        {
            RequireObject(item, "context summary");
            var insightId = GetRequiredString(item, "insightId");

            GetRequiredArray(item, "known");
            GetRequiredArray(item, "unknown");
            GetRequiredBoolean(item, "interpretationLimited");

            if (!summaries.TryAdd(insightId, item))
            {
                throw new JsonException(
                    $"Duplicate context summary for insight '{insightId}'.");
            }
        }

        return summaries;
    }

    private static JsonElement GetRequiredProperty(
        JsonElement parent,
        string propertyName)
    {
        if (!parent.TryGetProperty(propertyName, out var property))
        {
            throw new JsonException(
                $"The required property '{propertyName}' is missing.");
        }

        return property;
    }

    private static JsonElement GetRequiredArray(
        JsonElement parent,
        string propertyName)
    {
        var property = GetRequiredProperty(parent, propertyName);

        if (property.ValueKind != JsonValueKind.Array)
        {
            throw new JsonException(
                $"The property '{propertyName}' must be a JSON array.");
        }

        return property;
    }

    private static JsonElement GetRequiredObject(
        JsonElement parent,
        string propertyName)
    {
        var property = GetRequiredProperty(parent, propertyName);
        RequireObject(property, propertyName);
        return property;
    }

    private static string? GetRequiredNullableObjectJson(
        JsonElement parent,
        string propertyName)
    {
        var property = GetRequiredProperty(parent, propertyName);

        if (property.ValueKind == JsonValueKind.Null)
        {
            return null;
        }

        RequireObject(property, propertyName);
        return property.GetRawText();
    }

    private static void RequireObject(
        JsonElement property,
        string propertyName)
    {
        if (property.ValueKind != JsonValueKind.Object)
        {
            throw new JsonException(
                $"The property '{propertyName}' must be a JSON object.");
        }
    }

    private static string GetRequiredString(
        JsonElement parent,
        string propertyName)
    {
        var property = GetRequiredProperty(parent, propertyName);

        if (property.ValueKind != JsonValueKind.String)
        {
            throw new JsonException(
                $"The property '{propertyName}' must be a JSON string.");
        }

        return property.GetString()!;
    }

    private static bool GetRequiredBoolean(
        JsonElement parent,
        string propertyName)
    {
        var property = GetRequiredProperty(parent, propertyName);

        if (
            property.ValueKind != JsonValueKind.True
            && property.ValueKind != JsonValueKind.False
        )
        {
            throw new JsonException(
                $"The property '{propertyName}' must be a JSON boolean.");
        }

        return property.GetBoolean();
    }

    private static double? GetRequiredNullableDouble(
        JsonElement parent,
        string propertyName)
    {
        var property = GetRequiredProperty(parent, propertyName);

        if (property.ValueKind == JsonValueKind.Null)
        {
            return null;
        }

        if (
            property.ValueKind != JsonValueKind.Number
            || !property.TryGetDouble(out var value)
        )
        {
            throw new JsonException(
                $"The property '{propertyName}' must be a number or null.");
        }

        return value;
    }
}
