using DataStoryBuilder.Application.Hypotheses;
using DataStoryBuilder.Domain.Entities;
using DataStoryBuilder.Infrastructure.Persistence;
using Xunit;

namespace DataStoryBuilder.Application.Tests.Stories;

public sealed class HypothesisLifecycleTests
{
    [Theory]
    [InlineData("OPEN", HypothesisLifecycleStatus.Supported, "SUPPORTED")]
    [InlineData("OPEN", HypothesisLifecycleStatus.Rejected, "REJECTED")]
    [InlineData("SUPPORTED", HypothesisLifecycleStatus.Confirmed, "CONFIRMED")]
    [InlineData("SUPPORTED", HypothesisLifecycleStatus.Rejected, "REJECTED")]
    public void LockedTransitionsAppendExactlyOneDeterministicReason(
        string current,
        HypothesisLifecycleStatus target,
        string expected)
    {
        var hypothesis = Entity(current);
        hypothesis.ReasonsJson = "[\"Initial hypothesis created.\"]";

        Assert.True(HypothesisLifecyclePersistence.ApplyStatusTransition(
            hypothesis,
            target));
        Assert.Equal(expected, hypothesis.Status);
        Assert.Equal(
            [
                "Initial hypothesis created.",
                $"Hypothesis status changed from {current} to {expected}."
            ],
            Reasons(hypothesis));
    }

    [Theory]
    [InlineData("OPEN", HypothesisLifecycleStatus.Confirmed)]
    [InlineData("SUPPORTED", HypothesisLifecycleStatus.Open)]
    [InlineData("CONFIRMED", HypothesisLifecycleStatus.Open)]
    [InlineData("CONFIRMED", HypothesisLifecycleStatus.Supported)]
    [InlineData("CONFIRMED", HypothesisLifecycleStatus.Rejected)]
    [InlineData("REJECTED", HypothesisLifecycleStatus.Open)]
    [InlineData("REJECTED", HypothesisLifecycleStatus.Supported)]
    [InlineData("REJECTED", HypothesisLifecycleStatus.Confirmed)]
    public void ForbiddenCrossStateTransitionsFailWithoutMutation(
        string current,
        HypothesisLifecycleStatus target)
    {
        var hypothesis = Entity(current);
        var reasons = hypothesis.ReasonsJson;

        Assert.False(HypothesisLifecyclePersistence.ApplyStatusTransition(
            hypothesis,
            target));
        Assert.Equal(current, hypothesis.Status);
        Assert.Equal(reasons, hypothesis.ReasonsJson);
    }

    [Theory]
    [InlineData("OPEN", HypothesisLifecycleStatus.Open)]
    [InlineData("SUPPORTED", HypothesisLifecycleStatus.Supported)]
    [InlineData("CONFIRMED", HypothesisLifecycleStatus.Confirmed)]
    [InlineData("REJECTED", HypothesisLifecycleStatus.Rejected)]
    public void SameStateTransitionIsInvalid(
        string current,
        HypothesisLifecycleStatus target)
    {
        var hypothesis = Entity(current);
        var reasons = hypothesis.ReasonsJson;

        Assert.False(HypothesisLifecyclePersistence.ApplyStatusTransition(
            hypothesis,
            target));
        Assert.Equal(current, hypothesis.Status);
        Assert.Equal(reasons, hypothesis.ReasonsJson);
    }

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("supported")]
    [InlineData("UNKNOWN")]
    public void InvalidTargetStatusStringIsRejected(string? value)
    {
        Assert.False(HypothesisStatusTransitions.TryParse(value, out _));
    }

    [Fact]
    public void ValidTransitionChangesOnlyLifecycleFields()
    {
        var hypothesis = Entity("OPEN");
        var snapshot = AnalyticalSnapshot(hypothesis);

        Assert.True(HypothesisLifecyclePersistence.ApplyStatusTransition(
            hypothesis,
            HypothesisLifecycleStatus.Supported));

        Assert.Equal("SUPPORTED", hypothesis.Status);
        Assert.Equal(snapshot, AnalyticalSnapshot(hypothesis));
        Assert.Equal(3, Reasons(hypothesis).Count);
    }

    [Fact]
    public void RepeatedInvalidTransitionDoesNotMutatePersistedState()
    {
        var hypothesis = Entity("OPEN");

        Assert.False(HypothesisLifecyclePersistence.ApplyStatusTransition(
            hypothesis,
            HypothesisLifecycleStatus.Confirmed));
        Assert.False(HypothesisLifecyclePersistence.ApplyStatusTransition(
            hypothesis,
            HypothesisLifecycleStatus.Confirmed));
        Assert.Equal("OPEN", hypothesis.Status);
    }

    [Fact]
    public void RepeatRequestAfterSuccessDoesNotAppendDuplicateReason()
    {
        var hypothesis = Entity("OPEN");

        Assert.True(HypothesisLifecyclePersistence.ApplyStatusTransition(
            hypothesis,
            HypothesisLifecycleStatus.Supported));
        var reasonsAfterSuccess = hypothesis.ReasonsJson;

        Assert.False(HypothesisLifecyclePersistence.ApplyStatusTransition(
            hypothesis,
            HypothesisLifecycleStatus.Supported));
        Assert.Equal("SUPPORTED", hypothesis.Status);
        Assert.Equal(reasonsAfterSuccess, hypothesis.ReasonsJson);
        Assert.Single(Reasons(hypothesis), reason =>
            reason == "Hypothesis status changed from OPEN to SUPPORTED.");
    }

    [Fact]
    public void ReadProjectionPreservesEveryPersistedFieldAndOrder()
    {
        var second = Entity("SUPPORTED");
        second.Id = "HYPOTHESIS-z";
        var first = Entity("OPEN");
        first.Id = "HYPOTHESIS-a";

        var results = AnalysisDetailPersistence.ProjectHypotheses(
            [second, first]);

        Assert.Equal(
            ["HYPOTHESIS-a", "HYPOTHESIS-z"],
            results.Select(item => item.Id));
        Assert.Equal(first.Statement, results[0].Statement);
        Assert.Equal(first.Confidence, results[0].Confidence);
        Assert.Equal(first.CausalityStatus, results[0].CausalityStatus);
        Assert.Equal(first.TrackerVersion, results[0].TrackerVersion);
        Assert.Equal(
            first.SourceInsightIdsJson,
            results[0].SourceInsightIds.GetRawText());
        Assert.Equal(
            first.SupportingEvidenceJson,
            results[0].SupportingEvidence.GetRawText());
        Assert.Equal(
            first.CounterEvidenceJson,
            results[0].CounterEvidence.GetRawText());
        Assert.Equal(
            first.MissingContextJson,
            results[0].MissingContext.GetRawText());
        Assert.Equal(first.ReasonsJson, results[0].Reasons.GetRawText());
    }

    [Fact]
    public void EmptyPersistedCollectionProjectsAsEmptyWithoutMutation()
    {
        Assert.Empty(AnalysisDetailPersistence.ProjectHypotheses([]));
    }

    private static Hypothesis Entity(string status) => new()
    {
        Id = "HYPOTHESIS-0123456789abcdef",
        AnalysisId = Guid.Parse("11111111-1111-1111-1111-111111111111"),
        Statement = "MarketingSpend may be associated with Revenue.",
        Status = status,
        Confidence = 0.69,
        CausalityStatus = "CAUSALITY_NOT_ESTABLISHED",
        TrackerVersion = "day16-v1",
        SourceInsightIdsJson = "[\"marketing\",\"revenue\"]",
        SourceRelationshipIdsJson = "[\"relationship\"]",
        SupportingEvidenceJson = "[{\"insightId\":\"marketing\",\"evidenceCode\":\"CHANGE\"}]",
        CounterEvidenceJson = "[{\"metric\":\"Orders\"}]",
        MissingContextJson = "[{\"sourceInsightId\":\"revenue\"}]",
        ReasonsJson = "[\"Creation reason.\",\"Scoring reason.\"]"
    };

    private static IReadOnlyList<string> Reasons(Hypothesis item) =>
        System.Text.Json.JsonSerializer.Deserialize<string[]>(item.ReasonsJson)!;

    private static object AnalyticalSnapshot(Hypothesis item) => new
    {
        item.Id,
        item.AnalysisId,
        item.Statement,
        item.Confidence,
        item.CausalityStatus,
        item.TrackerVersion,
        item.SourceInsightIdsJson,
        item.SourceRelationshipIdsJson,
        item.SupportingEvidenceJson,
        item.CounterEvidenceJson,
        item.MissingContextJson
    };
}
