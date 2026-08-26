using System.Text.Json;
using DataStoryBuilder.Domain.Entities;

namespace DataStoryBuilder.Infrastructure.Persistence;

public sealed class InsightPersistence(
    DataStoryBuilderDbContext dbContext)
{
    public async Task PersistAsync(
        Guid analysisId,
        string analyticsResponseJson,
        CancellationToken cancellationToken = default)
    {
        using var document = JsonDocument.Parse(analyticsResponseJson);
        var root = document.RootElement;

        if (
            root.ValueKind != JsonValueKind.Object
            || !root.TryGetProperty("insights", out var insightsJson)
            || insightsJson.ValueKind != JsonValueKind.Array
        )
        {
            throw new JsonException(
                "The analytics response property 'insights' "
                + "must be a JSON array.");
        }

        var insights = new List<Insight>();
        var evidenceItems = new List<Evidence>();
        var insightIds = new HashSet<string>(StringComparer.Ordinal);

        foreach (var insightJson in insightsJson.EnumerateArray())
        {
            if (insightJson.ValueKind != JsonValueKind.Object)
            {
                throw new JsonException(
                    "Each analytics insight must be a JSON object.");
            }

            var insightId = GetRequiredString(insightJson, "id");

            if (!insightIds.Add(insightId))
            {
                throw new JsonException(
                    $"Duplicate insight id '{insightId}' was returned.");
            }

            var source = GetRequiredProperty(insightJson, "source");

            var insight = new Insight
            {
                Id = insightId,
                AnalysisId = analysisId,
                Type = GetRequiredString(insightJson, "type"),
                Metric = GetRequiredString(insightJson, "metric"),
                Dimension = GetOptionalString(insightJson, "dimension"),
                Segment = GetOptionalString(insightJson, "segment"),
                PeriodGranularity = GetRequiredString(
                    insightJson,
                    "periodGranularity"),
                Direction = GetRequiredString(insightJson, "direction"),
                Confidence = GetOptionalDouble(insightJson, "confidence"),
                Importance = GetOptionalDouble(insightJson, "importance"),
                PeriodJson = GetRequiredObjectJson(insightJson, "period"),
                ValuesJson = GetRequiredObjectJson(insightJson, "values"),
                DetectionJson = GetRequiredObjectJson(
                    insightJson,
                    "detection"),
                ConfidenceBreakdownJson = GetRequiredObjectJson(
                    insightJson,
                    "confidenceBreakdown"),
                ImportanceBreakdownJson = GetRequiredObjectJson(
                    insightJson,
                    "importanceBreakdown"),
                SourceJson = source.ValueKind == JsonValueKind.Null
                    ? null
                    : GetObjectJson(source, "source")
            };

            insights.Add(insight);

            var evidenceJson = GetRequiredProperty(
                insightJson,
                "evidence");

            if (evidenceJson.ValueKind != JsonValueKind.Array)
            {
                throw new JsonException(
                    "The insight property 'evidence' must be a JSON array.");
            }

            var ordinal = 0;

            foreach (var evidenceJsonItem in evidenceJson.EnumerateArray())
            {
                if (evidenceJsonItem.ValueKind != JsonValueKind.Object)
                {
                    throw new JsonException(
                        "Each evidence item must be a JSON object.");
                }

                evidenceItems.Add(new Evidence
                {
                    AnalysisId = analysisId,
                    InsightId = insightId,
                    Ordinal = ordinal,
                    Code = GetRequiredString(evidenceJsonItem, "code"),
                    Label = GetRequiredString(evidenceJsonItem, "label"),
                    ValueJson = GetRequiredProperty(
                        evidenceJsonItem,
                        "value").GetRawText(),
                    Unit = GetOptionalString(evidenceJsonItem, "unit")
                });

                ordinal++;
            }
        }

        dbContext.Insights.AddRange(insights);
        dbContext.Evidence.AddRange(evidenceItems);

        await dbContext.SaveChangesAsync(cancellationToken);
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

    private static string? GetOptionalString(
        JsonElement parent,
        string propertyName)
    {
        if (!parent.TryGetProperty(propertyName, out var property))
        {
            return null;
        }

        if (property.ValueKind == JsonValueKind.Null)
        {
            return null;
        }

        if (property.ValueKind != JsonValueKind.String)
        {
            throw new JsonException(
                $"The property '{propertyName}' must be a string or null.");
        }

        return property.GetString();
    }

    private static double? GetOptionalDouble(
        JsonElement parent,
        string propertyName)
    {
        if (!parent.TryGetProperty(propertyName, out var property))
        {
            return null;
        }

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

    private static string GetRequiredObjectJson(
        JsonElement parent,
        string propertyName)
    {
        return GetObjectJson(
            GetRequiredProperty(parent, propertyName),
            propertyName);
    }

    private static string GetObjectJson(
        JsonElement property,
        string propertyName)
    {
        if (property.ValueKind != JsonValueKind.Object)
        {
            throw new JsonException(
                $"The property '{propertyName}' must be a JSON object.");
        }

        return property.GetRawText();
    }
}
