using System.Text.Json;
using DataStoryBuilder.Domain.Entities;
using Microsoft.EntityFrameworkCore;

namespace DataStoryBuilder.Infrastructure.Persistence;

public sealed class RelationshipRankingPersistence(
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

        var relationships = ParseRelationships(root, analysisId);
        var clusters = ParseClusters(root, analysisId);
        var insightsById = await dbContext.Insights
            .Where(insight => insight.AnalysisId == analysisId)
            .ToDictionaryAsync(
                insight => insight.Id,
                StringComparer.Ordinal,
                cancellationToken);

        ApplyBusinessRelevance(root, insightsById);
        ApplyPriority(root, insightsById);
        ApplyRanking(root, insightsById);

        dbContext.Relationships.AddRange(relationships);
        dbContext.InsightClusters.AddRange(clusters);

        await dbContext.SaveChangesAsync(cancellationToken);
    }

    private static List<Relationship> ParseRelationships(
        JsonElement root,
        Guid analysisId)
    {
        var relationshipsJson = GetRequiredArray(root, "relationships");
        var relationships = new List<Relationship>();
        var relationshipIds = new HashSet<string>(StringComparer.Ordinal);

        foreach (var item in relationshipsJson.EnumerateArray())
        {
            RequireObject(item, "relationship");
            var relationshipId = GetRequiredString(item, "id");

            if (!relationshipIds.Add(relationshipId))
            {
                throw new JsonException(
                    $"Duplicate relationship id '{relationshipId}' "
                    + "was returned.");
            }

            relationships.Add(new Relationship
            {
                Id = relationshipId,
                AnalysisId = analysisId,
                SourceInsightId = GetRequiredString(
                    item,
                    "sourceInsightId"),
                TargetInsightId = GetRequiredString(
                    item,
                    "targetInsightId"),
                Type = GetRequiredString(item, "type"),
                Strength = GetRequiredDouble(item, "strength"),
                Confidence = GetRequiredDouble(item, "confidence"),
                StrengthBreakdownJson = GetRequiredObjectJson(
                    item,
                    "strengthBreakdown"),
                ConfidenceBreakdownJson = GetRequiredObjectJson(
                    item,
                    "confidenceBreakdown"),
                ReasonsJson = GetRequiredArray(item, "reasons").GetRawText(),
                MetadataJson = GetRequiredObjectJson(item, "metadata")
            });
        }

        return relationships;
    }

    private static List<InsightCluster> ParseClusters(
        JsonElement root,
        Guid analysisId)
    {
        var clustersJson = GetRequiredArray(root, "insightClusters");
        var clusters = new List<InsightCluster>();
        var clusterIds = new HashSet<string>(StringComparer.Ordinal);

        foreach (var item in clustersJson.EnumerateArray())
        {
            RequireObject(item, "insight cluster");
            var clusterId = GetRequiredString(item, "id");

            if (!clusterIds.Add(clusterId))
            {
                throw new JsonException(
                    $"Duplicate insight cluster id '{clusterId}' "
                    + "was returned.");
            }

            clusters.Add(new InsightCluster
            {
                Id = clusterId,
                AnalysisId = analysisId,
                AnchorInsightId = GetRequiredString(
                    item,
                    "anchorInsightId"),
                MemberInsightIdsJson = GetRequiredArray(
                    item,
                    "memberInsightIds").GetRawText(),
                RelationshipIdsJson = GetRequiredArray(
                    item,
                    "relationshipIds").GetRawText()
            });
        }

        return clusters;
    }

    private static void ApplyBusinessRelevance(
        JsonElement root,
        IReadOnlyDictionary<string, Insight> insightsById)
    {
        var evaluations = GetRequiredArray(root, "businessRelevance");
        var evaluatedInsightIds = new HashSet<string>(StringComparer.Ordinal);

        foreach (var item in evaluations.EnumerateArray())
        {
            RequireObject(item, "business relevance evaluation");
            var insight = GetReferencedInsight(
                item,
                insightsById,
                evaluatedInsightIds,
                "business relevance evaluation");

            insight.BusinessRelevance = GetRequiredDouble(
                item,
                "businessRelevance");
            insight.ImpactDirection = GetRequiredString(
                item,
                "impactDirection");
            insight.BusinessRelevanceDetailsJson = item.GetRawText();
        }
    }

    private static void ApplyPriority(
        JsonElement root,
        IReadOnlyDictionary<string, Insight> insightsById)
    {
        var evaluations = GetRequiredArray(root, "priorityEvaluations");
        var evaluatedInsightIds = new HashSet<string>(StringComparer.Ordinal);

        foreach (var item in evaluations.EnumerateArray())
        {
            RequireObject(item, "priority evaluation");
            var insight = GetReferencedInsight(
                item,
                insightsById,
                evaluatedInsightIds,
                "priority evaluation");

            insight.PriorityScore = GetRequiredDouble(
                item,
                "priorityScore");
            insight.PriorityLevel = GetRequiredString(
                item,
                "priorityLevel");
            insight.PriorityDetailsJson = item.GetRawText();
        }
    }

    private static void ApplyRanking(
        JsonElement root,
        IReadOnlyDictionary<string, Insight> insightsById)
    {
        var rankings = GetRequiredArray(root, "rankedInsights");
        var rankedInsightIds = new HashSet<string>(StringComparer.Ordinal);

        foreach (var item in rankings.EnumerateArray())
        {
            RequireObject(item, "ranked insight");
            var insight = GetReferencedInsight(
                item,
                insightsById,
                rankedInsightIds,
                "ranked insight");

            insight.Rank = GetRequiredInt32(item, "rank");
            insight.RankingDetailsJson = item.GetRawText();
        }
    }

    private static Insight GetReferencedInsight(
        JsonElement item,
        IReadOnlyDictionary<string, Insight> insightsById,
        ISet<string> seenInsightIds,
        string itemName)
    {
        var insightId = GetRequiredString(item, "insightId");

        if (!seenInsightIds.Add(insightId))
        {
            throw new JsonException(
                $"Duplicate {itemName} for insight '{insightId}'.");
        }

        if (!insightsById.TryGetValue(insightId, out var insight))
        {
            throw new JsonException(
                $"The {itemName} references unknown insight "
                + $"'{insightId}'.");
        }

        return insight;
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

    private static string GetRequiredObjectJson(
        JsonElement parent,
        string propertyName)
    {
        var property = GetRequiredProperty(parent, propertyName);
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

    private static double GetRequiredDouble(
        JsonElement parent,
        string propertyName)
    {
        var property = GetRequiredProperty(parent, propertyName);

        if (
            property.ValueKind != JsonValueKind.Number
            || !property.TryGetDouble(out var value)
        )
        {
            throw new JsonException(
                $"The property '{propertyName}' must be a JSON number.");
        }

        return value;
    }

    private static int GetRequiredInt32(
        JsonElement parent,
        string propertyName)
    {
        var property = GetRequiredProperty(parent, propertyName);

        if (
            property.ValueKind != JsonValueKind.Number
            || !property.TryGetInt32(out var value)
        )
        {
            throw new JsonException(
                $"The property '{propertyName}' must be a 32-bit integer.");
        }

        return value;
    }
}
