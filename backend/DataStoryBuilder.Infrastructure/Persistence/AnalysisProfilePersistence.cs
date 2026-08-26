using System.Text.Json;
using DataStoryBuilder.Domain.Entities;
using Microsoft.EntityFrameworkCore;

namespace DataStoryBuilder.Infrastructure.Persistence;

public sealed class AnalysisProfilePersistence(
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

        var preparedSchema = GetRequiredObject(
            root,
            "preparedSchema");
        var dataQuality = GetRequiredObject(
            root,
            "dataQuality");

        var rowCount = GetRequiredInt32(
            preparedSchema,
            "rowCount");
        var columnCount = GetRequiredInt32(
            preparedSchema,
            "columnCount");

        double? dataQualityScore = null;

        if (
            dataQuality.TryGetProperty("score", out var score)
            && score.ValueKind == JsonValueKind.Number
        )
        {
            dataQualityScore = score.GetDouble();
        }

        var profileJson = JsonSerializer.Serialize(
            new Dictionary<string, JsonElement>
            {
                ["rawSchema"] = GetRequiredObject(root, "rawSchema"),
                ["preparedSchema"] = preparedSchema,
                ["preparationReport"] = GetRequiredObject(
                    root,
                    "preparationReport"),
                ["datasetProfile"] = GetRequiredObject(
                    root,
                    "datasetProfile"),
                ["semanticRoles"] = GetRequiredObject(
                    root,
                    "semanticRoles"),
                ["integrity"] = GetRequiredObject(root, "integrity")
            });

        var analysis = await dbContext.Analyses.SingleAsync(
            item => item.Id == analysisId,
            cancellationToken);

        analysis.RowCount = rowCount;
        analysis.ColumnCount = columnCount;
        analysis.DataQualityScore = dataQualityScore;

        dbContext.DatasetProfiles.Add(new DatasetProfile
        {
            Id = Guid.NewGuid(),
            AnalysisId = analysisId,
            ProfileJson = profileJson,
            QualityJson = dataQuality.GetRawText()
        });

        await dbContext.SaveChangesAsync(cancellationToken);
    }

    private static JsonElement GetRequiredObject(
        JsonElement parent,
        string propertyName)
    {
        if (
            !parent.TryGetProperty(propertyName, out var property)
            || property.ValueKind != JsonValueKind.Object
        )
        {
            throw new JsonException(
                $"The analytics response property '{propertyName}' "
                + "must be a JSON object.");
        }

        return property;
    }

    private static int GetRequiredInt32(
        JsonElement parent,
        string propertyName)
    {
        if (
            !parent.TryGetProperty(propertyName, out var property)
            || property.ValueKind != JsonValueKind.Number
            || !property.TryGetInt32(out var value)
        )
        {
            throw new JsonException(
                $"The analytics response property '{propertyName}' "
                + "must be a 32-bit integer.");
        }

        return value;
    }
}
