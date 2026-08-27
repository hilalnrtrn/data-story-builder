using System.Text.Json;
using DataStoryBuilder.Domain.Entities;

namespace DataStoryBuilder.Infrastructure.Persistence;

public sealed class HypothesisPersistence(
    DataStoryBuilderDbContext dbContext)
{
    private static readonly HashSet<string> AllowedStatuses =
        new(StringComparer.Ordinal)
        {
            "OPEN",
            "SUPPORTED",
            "CONFIRMED",
            "REJECTED"
        };

    public async Task PersistAsync(
        Guid analysisId,
        string analyticsResponseJson,
        CancellationToken cancellationToken = default)
    {
        var hypotheses = Parse(analysisId, analyticsResponseJson);
        dbContext.Hypotheses.AddRange(hypotheses);
        await dbContext.SaveChangesAsync(cancellationToken);
    }

    public static IReadOnlyList<Hypothesis> Parse(
        Guid analysisId,
        string analyticsResponseJson)
    {
        using var document = JsonDocument.Parse(analyticsResponseJson);
        var root = document.RootElement;
        if (root.ValueKind != JsonValueKind.Object
            || !root.TryGetProperty("hypotheses", out var hypothesesJson)
            || hypothesesJson.ValueKind != JsonValueKind.Array)
        {
            throw new JsonException(
                "The analytics response must contain a hypotheses array.");
        }

        var hypotheses = new List<Hypothesis>();
        var ids = new HashSet<string>(StringComparer.Ordinal);
        foreach (var item in hypothesesJson.EnumerateArray())
        {
            if (item.ValueKind != JsonValueKind.Object)
            {
                throw new JsonException("Each hypothesis must be an object.");
            }

            var id = RequiredString(item, "id");
            if (!ids.Add(id))
            {
                throw new JsonException($"Duplicate hypothesis id '{id}'.");
            }

            var responseAnalysisId = RequiredString(item, "analysisId");
            if (!Guid.TryParse(responseAnalysisId, out var parsedAnalysisId)
                || parsedAnalysisId != analysisId)
            {
                throw new JsonException(
                    "Hypothesis analysisId does not match the analysis.");
            }

            var confidence = RequiredNumber(item, "confidence");
            if (!double.IsFinite(confidence)
                || confidence is < 0.0 or > 1.0)
            {
                throw new JsonException(
                    "Hypothesis confidence must be finite and in [0, 1].");
            }

            var status = RequiredString(item, "status");
            if (!AllowedStatuses.Contains(status))
            {
                throw new JsonException(
                    $"Hypothesis status '{status}' is not supported.");
            }

            hypotheses.Add(new Hypothesis
            {
                Id = id,
                AnalysisId = analysisId,
                Statement = RequiredString(item, "statement"),
                Status = status,
                Confidence = confidence,
                CausalityStatus = RequiredString(item, "causalityStatus"),
                TrackerVersion = RequiredString(item, "trackerVersion"),
                SourceInsightIdsJson = RequiredArray(item, "sourceInsightIds"),
                SourceRelationshipIdsJson = RequiredArray(
                    item,
                    "sourceRelationshipIds"),
                SupportingEvidenceJson = RequiredArray(
                    item,
                    "supportingEvidence"),
                CounterEvidenceJson = RequiredArray(item, "counterEvidence"),
                MissingContextJson = RequiredArray(item, "missingContext"),
                ReasonsJson = RequiredArray(item, "reasons")
            });
        }

        return hypotheses;
    }

    private static string RequiredString(JsonElement item, string name)
    {
        if (!item.TryGetProperty(name, out var property)
            || property.ValueKind != JsonValueKind.String
            || string.IsNullOrWhiteSpace(property.GetString()))
        {
            throw new JsonException(
                $"Hypothesis property '{name}' must be a non-empty string.");
        }

        return property.GetString()!;
    }

    private static double RequiredNumber(JsonElement item, string name)
    {
        if (!item.TryGetProperty(name, out var property)
            || property.ValueKind != JsonValueKind.Number
            || !property.TryGetDouble(out var value))
        {
            throw new JsonException(
                $"Hypothesis property '{name}' must be a number.");
        }

        return value;
    }

    private static string RequiredArray(JsonElement item, string name)
    {
        if (!item.TryGetProperty(name, out var property)
            || property.ValueKind != JsonValueKind.Array)
        {
            throw new JsonException(
                $"Hypothesis property '{name}' must be an array.");
        }

        return property.GetRawText();
    }
}
