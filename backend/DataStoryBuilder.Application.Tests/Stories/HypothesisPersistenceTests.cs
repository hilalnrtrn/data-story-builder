using System.Text.Json;
using DataStoryBuilder.Domain.Entities;
using DataStoryBuilder.Infrastructure.Persistence;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata;
using Xunit;

namespace DataStoryBuilder.Application.Tests.Stories;

public sealed class HypothesisPersistenceTests
{
    private static readonly Guid AnalysisId =
        Guid.Parse("11111111-1111-1111-1111-111111111111");

    [Theory]
    [InlineData("OPEN")]
    [InlineData("SUPPORTED")]
    [InlineData("CONFIRMED")]
    [InlineData("REJECTED")]
    public void ParserPreservesControlledLifecycleStatus(string status)
    {
        var entity = Assert.Single(
            HypothesisPersistence.Parse(AnalysisId, Response(status)));

        Assert.Equal(status, entity.Status);
        Assert.Equal(AnalysisId, entity.AnalysisId);
        Assert.Equal(
            "HYPOTHESIS-0123456789abcdef",
            entity.Id);
    }

    [Fact]
    public void ParserPreservesScalarAndJsonSnapshotsExactly()
    {
        var entity = Assert.Single(
            HypothesisPersistence.Parse(AnalysisId, Response("OPEN")));

        Assert.Equal(
            "MarketingSpend may be associated with Revenue.",
            entity.Statement);
        Assert.Equal(0.69, entity.Confidence);
        Assert.Equal("CAUSALITY_NOT_ESTABLISHED", entity.CausalityStatus);
        Assert.Equal("day16-v1", entity.TrackerVersion);
        Assert.Equal(
            ["marketing-insight", "revenue-insight"],
            Strings(entity.SourceInsightIdsJson));
        Assert.Equal(
            ["marketing-revenue-relationship"],
            Strings(entity.SourceRelationshipIdsJson));

        using var evidence = JsonDocument.Parse(entity.SupportingEvidenceJson);
        Assert.Equal(
            "RELATIVE_CHANGE",
            evidence.RootElement[0].GetProperty("evidenceCode").GetString());
        using var counter = JsonDocument.Parse(entity.CounterEvidenceJson);
        Assert.Equal(
            "Orders",
            counter.RootElement[0].GetProperty("metric").GetString());
        using var missing = JsonDocument.Parse(entity.MissingContextJson);
        Assert.Equal(
            "revenue-insight",
            missing.RootElement[0].GetProperty("sourceInsightId").GetString());
        Assert.False(
            missing.RootElement[0].GetProperty("item")
                .GetProperty("isDataQualityError").GetBoolean());
        Assert.Equal(
            ["Creation reason.", "Scoring reason."],
            Strings(entity.ReasonsJson));
    }

    [Fact]
    public void DetailProjectionReloadsPersistedSnapshotsWithoutRecomputation()
    {
        var entity = Assert.Single(
            HypothesisPersistence.Parse(AnalysisId, Response("OPEN")));

        var detail = Assert.Single(
            AnalysisDetailPersistence.ProjectHypotheses([entity]));

        Assert.Equal(entity.Id, detail.Id);
        Assert.Equal(entity.AnalysisId, detail.AnalysisId);
        Assert.Equal(entity.Statement, detail.Statement);
        Assert.Equal(entity.Status, detail.Status);
        Assert.Equal(entity.Confidence, detail.Confidence);
        Assert.Equal(entity.CausalityStatus, detail.CausalityStatus);
        Assert.Equal(entity.TrackerVersion, detail.TrackerVersion);
        Assert.Equal(
            entity.SourceInsightIdsJson,
            detail.SourceInsightIds.GetRawText());
        Assert.Equal(
            entity.SupportingEvidenceJson,
            detail.SupportingEvidence.GetRawText());
        Assert.Equal(
            entity.MissingContextJson,
            detail.MissingContext.GetRawText());
    }

    [Fact]
    public void DetailProjectionOrdersMultipleHypothesesByDeterministicId()
    {
        var first = Assert.Single(
            HypothesisPersistence.Parse(AnalysisId, Response("OPEN")));
        var second = Clone(first, "HYPOTHESIS-z");
        first.Id = "HYPOTHESIS-a";

        var details = AnalysisDetailPersistence.ProjectHypotheses(
            [second, first]);

        Assert.Equal(
            ["HYPOTHESIS-a", "HYPOTHESIS-z"],
            details.Select(item => item.Id));
    }

    [Fact]
    public void ZeroHypothesesReloadsAsEmptyCollection()
    {
        Assert.Empty(AnalysisDetailPersistence.ProjectHypotheses([]));
        Assert.Empty(HypothesisPersistence.Parse(
            AnalysisId,
            "{\"hypotheses\":[]}"));
    }

    [Fact]
    public void EfModelUsesCompositeKeyJsonbSnapshotsAndCascadeOwnership()
    {
        var options = new DbContextOptionsBuilder<DataStoryBuilderDbContext>()
            .UseNpgsql("Host=localhost;Database=model_only")
            .Options;
        using var context = new DataStoryBuilderDbContext(options);
        var entity = context.Model.FindEntityType(typeof(Hypothesis))!;

        Assert.Equal(
            [nameof(Hypothesis.AnalysisId), nameof(Hypothesis.Id)],
            entity.FindPrimaryKey()!.Properties.Select(item => item.Name));
        foreach (var propertyName in new[]
        {
            nameof(Hypothesis.SourceInsightIdsJson),
            nameof(Hypothesis.SourceRelationshipIdsJson),
            nameof(Hypothesis.SupportingEvidenceJson),
            nameof(Hypothesis.CounterEvidenceJson),
            nameof(Hypothesis.MissingContextJson),
            nameof(Hypothesis.ReasonsJson)
        })
        {
            Assert.Equal(
                "jsonb",
                entity.FindProperty(propertyName)!.GetColumnType());
        }

        var foreignKey = Assert.Single(entity.GetForeignKeys());
        Assert.Equal(DeleteBehavior.Cascade, foreignKey.DeleteBehavior);
        Assert.Equal(typeof(Analysis), foreignKey.PrincipalEntityType.ClrType);
    }

    [Fact]
    public void RoundTripProjectionIsStructurallyEquivalentAndDoesNotTransition()
    {
        var entity = Assert.Single(
            HypothesisPersistence.Parse(AnalysisId, Response("SUPPORTED")));
        var detail = Assert.Single(
            AnalysisDetailPersistence.ProjectHypotheses([entity]));

        Assert.Equal("SUPPORTED", detail.Status);
        Assert.Equal(0.69, detail.Confidence);
        Assert.Equal(
            entity.CounterEvidenceJson,
            detail.CounterEvidence.GetRawText());
        Assert.Equal(entity.ReasonsJson, detail.Reasons.GetRawText());
    }

    private static string Response(string status) => JsonSerializer.Serialize(
        new
        {
            hypotheses = new[]
            {
                new
                {
                    id = "HYPOTHESIS-0123456789abcdef",
                    analysisId = AnalysisId.ToString(),
                    statement = "MarketingSpend may be associated with Revenue.",
                    status,
                    confidence = 0.69,
                    sourceInsightIds = new[]
                    {
                        "marketing-insight",
                        "revenue-insight"
                    },
                    sourceRelationshipIds = new[]
                    {
                        "marketing-revenue-relationship"
                    },
                    supportingEvidence = new[]
                    {
                        new
                        {
                            insightId = "marketing-insight",
                            evidenceCode = "RELATIVE_CHANGE"
                        }
                    },
                    counterEvidence = new[]
                    {
                        new
                        {
                            insightId = "orders-insight",
                            relationshipId = "orders-revenue-relationship",
                            metric = "Orders",
                            direction = "DOWN",
                            reasons = new[] { "Counter reason." }
                        }
                    },
                    missingContext = new[]
                    {
                        new
                        {
                            sourceInsightId = "revenue-insight",
                            item = new
                            {
                                field = "CompetitorPrice",
                                status = "NOT_AVAILABLE",
                                isDataQualityError = false,
                                reason = "Competitor pricing is unavailable."
                            }
                        }
                    },
                    causalityStatus = "CAUSALITY_NOT_ESTABLISHED",
                    reasons = new[] { "Creation reason.", "Scoring reason." },
                    trackerVersion = "day16-v1"
                }
            }
        });

    private static string[] Strings(string json)
    {
        using var document = JsonDocument.Parse(json);
        return document.RootElement
            .EnumerateArray()
            .Select(item => item.GetString()!)
            .ToArray();
    }

    private static Hypothesis Clone(Hypothesis source, string id) => new()
    {
        Id = id,
        AnalysisId = source.AnalysisId,
        Statement = source.Statement,
        Status = source.Status,
        Confidence = source.Confidence,
        CausalityStatus = source.CausalityStatus,
        TrackerVersion = source.TrackerVersion,
        SourceInsightIdsJson = source.SourceInsightIdsJson,
        SourceRelationshipIdsJson = source.SourceRelationshipIdsJson,
        SupportingEvidenceJson = source.SupportingEvidenceJson,
        CounterEvidenceJson = source.CounterEvidenceJson,
        MissingContextJson = source.MissingContextJson,
        ReasonsJson = source.ReasonsJson
    };
}
