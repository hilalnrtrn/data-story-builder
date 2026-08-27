using System.Text.Json;
using DataStoryBuilder.Application.Stories;
using Xunit;

namespace DataStoryBuilder.Application.Tests.Stories;

public sealed class GeneratedExecutiveStorySchemaTests
{
    [Fact]
    public void SchemaRequiresAllRootProperties()
    {
        using var document = JsonDocument.Parse(GeneratedExecutiveStorySchema.Build());
        Assert.Equal(
            ["title", "executiveSummary", "sections"],
            Strings(document.RootElement.GetProperty("required")));
    }

    [Fact]
    public void SchemaRequiresNestedSectionProperties()
    {
        using var document = JsonDocument.Parse(GeneratedExecutiveStorySchema.Build());
        var section = document.RootElement.GetProperty("properties")
            .GetProperty("sections").GetProperty("items");
        Assert.Equal(["order", "type", "items"], Strings(section.GetProperty("required")));
        Assert.Equal(1, section.GetProperty("properties").GetProperty("order").GetProperty("minimum").GetInt32());
    }

    [Fact]
    public void SchemaRequiresNestedItemProperties()
    {
        using var document = JsonDocument.Parse(GeneratedExecutiveStorySchema.Build());
        var item = document.RootElement.GetProperty("properties")
            .GetProperty("sections").GetProperty("items")
            .GetProperty("properties").GetProperty("items").GetProperty("items");
        Assert.Equal(["sourceItemId", "text"], Strings(item.GetProperty("required")));
    }

    [Fact]
    public void SchemaDisablesUnexpectedPropertiesAndRequiresNonEmptyArrays()
    {
        using var document = JsonDocument.Parse(GeneratedExecutiveStorySchema.Build());
        var root = document.RootElement;
        var sections = root.GetProperty("properties").GetProperty("sections");
        var section = sections.GetProperty("items");
        var items = section.GetProperty("properties").GetProperty("items");
        var item = items.GetProperty("items");
        Assert.False(root.GetProperty("additionalProperties").GetBoolean());
        Assert.False(section.GetProperty("additionalProperties").GetBoolean());
        Assert.False(item.GetProperty("additionalProperties").GetBoolean());
        Assert.Equal(1, sections.GetProperty("minItems").GetInt32());
        Assert.Equal(1, items.GetProperty("minItems").GetInt32());
    }

    [Fact]
    public void SchemaOutputIsDeterministic()
    {
        Assert.Equal(
            GeneratedExecutiveStorySchema.Build(),
            GeneratedExecutiveStorySchema.Build());
    }

    private static string[] Strings(JsonElement array) =>
        array.EnumerateArray().Select(item => item.GetString()!).ToArray();
}

public sealed class GeneratedStorySafetyValidatorTests
{
    private readonly GeneratedStorySafetyValidator validator = new();

    [Fact]
    public void ValidGeneratedStoryIsAccepted() =>
        validator.Validate(CreateStory(), CreateInput());

    [Fact]
    public void SectionCountMismatchIsRejected()
    {
        var story = CreateStory(sections: CreateStory().Sections.Take(2).ToArray());
        AssertRejected(story, CreateInput());
    }

    [Fact]
    public void SectionOrderMismatchIsRejected()
    {
        var sections = CreateStory().Sections.ToArray();
        sections[0] = new GeneratedStorySection(4, "OUTCOME", [Item("main-item")]);
        AssertRejected(CreateStory(sections: sections), CreateInput());
    }

    [Fact]
    public void SectionTypeMismatchIsRejected()
    {
        var sections = CreateStory().Sections.ToArray();
        sections[0] = new GeneratedStorySection(1, "RISKS", [Item("main-item")]);
        AssertRejected(CreateStory(sections: sections), CreateInput());
    }

    [Fact]
    public void UnknownSourceItemIdIsRejected()
    {
        var sections = CreateStory().Sections.ToArray();
        sections[0] = new GeneratedStorySection(1, "OUTCOME", [Item("invented")]);
        AssertRejected(CreateStory(sections: sections), CreateInput());
    }

    [Fact]
    public void SourceItemMovedToWrongSectionIsRejected()
    {
        var sections = CreateStory().Sections.ToArray();
        sections[0] = new GeneratedStorySection(1, "OUTCOME", [Item("associated-item")]);
        sections[1] = new GeneratedStorySection(2, "ASSOCIATED_SIGNALS", [Item("main-item")]);
        AssertRejected(CreateStory(sections: sections), CreateInput());
    }

    [Fact]
    public void OmittedRequiredSourceItemIsRejected()
    {
        var input = CreateInput(outcomeIds: ["main-item", "second-main-item"]);
        AssertRejected(CreateStory(), input);
    }

    [Fact]
    public void DuplicateSourceItemIdIsRejectedByContract()
    {
        Assert.Throws<ArgumentException>(() =>
            new GeneratedStorySection(
                1,
                "OUTCOME",
                [Item("main-item"), Item("main-item")]));
    }

    [Fact]
    public void LimitationsAreRetained() =>
        validator.Validate(CreateStory(), CreateInput());

    [Fact]
    public void MissingLimitationIsRejected()
    {
        var sections = CreateStory().Sections.Take(2).ToArray();
        AssertRejected(CreateStory(sections: sections), CreateInput());
    }

    [Theory]
    [InlineData("MarketingSpend caused Revenue growth.")]
    [InlineData("MarketingSpend led to Revenue growth.")]
    [InlineData("Revenue grew because of MarketingSpend.")]
    [InlineData("MarketingSpend resulted in Revenue growth.")]
    [InlineData("Revenue growth was driven by MarketingSpend.")]
    [InlineData("MarketingSpend drives Revenue growth.")]
    [InlineData("The Marmara region drove the revenue increase.")]
    [InlineData("The Marmara region DROVE the revenue increase.")]
    public void CausalPhraseIsRejectedWhenForbidden(string text)
    {
        var sections = CreateStory().Sections.ToArray();
        sections[1] = new GeneratedStorySection(2, "ASSOCIATED_SIGNALS", [Item("associated-item", text)]);
        AssertRejected(CreateStory(sections: sections), CreateInput());
    }

    [Fact]
    public void CausalPhraseInTitleIsRejected() =>
        AssertRejected(CreateStory(title: "MarketingSpend caused Revenue growth"), CreateInput());

    [Fact]
    public void CausalPhraseInExecutiveSummaryIsRejected() =>
        AssertRejected(CreateStory(summary: "MarketingSpend led to Revenue growth."), CreateInput());

    [Fact]
    public void CausalPhraseIsAllowedWithoutRelevantProhibition()
    {
        validator.Validate(
            CreateStory(title: "The Marmara region drove the revenue increase"),
            CreateInput(constraints: []));
    }

    [Fact]
    public void AssociatedSignalRemainsInItsGroundedSection() =>
        validator.Validate(CreateStory(), CreateInput());

    [Fact]
    public void ValidationIsDeterministic()
    {
        var story = CreateStory(title: "MarketingSpend caused Revenue growth");
        var input = CreateInput();
        var first = Assert.Throws<GeneratedStorySafetyException>(() => validator.Validate(story, input));
        var second = Assert.Throws<GeneratedStorySafetyException>(() => validator.Validate(story, input));
        Assert.Equal(first.Message, second.Message);
    }

    [Fact]
    public void AmbiguousGroundedSourceIdIsRejected()
    {
        var input = CreateInput(associatedIds: ["main-item"]);
        AssertRejected(CreateStory(), input);
    }

    private void AssertRejected(GeneratedExecutiveStory story, GroundedStoryPromptInput input) =>
        Assert.Throws<GeneratedStorySafetyException>(() => validator.Validate(story, input));

    private static GeneratedExecutiveStory CreateStory(
        string title = "Revenue increased",
        string summary = "Revenue and MarketingSpend moved alongside each other.",
        IReadOnlyList<GeneratedStorySection>? sections = null) =>
        new(
            title,
            summary,
            sections ??
            [
                new GeneratedStorySection(1, "OUTCOME", [Item("main-item")]),
                new GeneratedStorySection(2, "ASSOCIATED_SIGNALS", [Item("associated-item")]),
                new GeneratedStorySection(3, "LIMITATIONS", [Item("missing-item")])
            ]);

    private static GeneratedStoryItem Item(string id, string text = "Grounded narrative text.") =>
        new(id, text);

    private static GroundedStoryPromptInput CreateInput(
        IReadOnlyList<string>? outcomeIds = null,
        IReadOnlyList<string>? associatedIds = null,
        IReadOnlyList<GroundedCausalityConstraint>? constraints = null) =>
        new(
            "analysis-1",
            "day12-v1",
            [
                new GroundedStorySection(1, "OUTCOME", outcomeIds ?? ["main-item"]),
                new GroundedStorySection(2, "ASSOCIATED_SIGNALS", associatedIds ?? ["associated-item"]),
                new GroundedStorySection(3, "LIMITATIONS", ["missing-item"])
            ],
            [],
            constraints ??
            [
                new GroundedCausalityConstraint(
                    "relationship-1",
                    "marketing-insight",
                    "revenue-insight",
                    "CORRELATIONAL",
                    true,
                    false,
                    "CAUSALITY_NOT_ESTABLISHED",
                    ["ASSOCIATED_WITH"],
                    ["CAUSED", "LED_TO", "BECAUSE_OF", "RESULTED_IN", "DRIVEN_BY"],
                    ["Causality is not established."])
            ],
            [
                new GroundedStoryLimitation(
                    "missing-item",
                    "revenue-insight",
                    "CompetitorPrice",
                    "NOT_AVAILABLE",
                    "Competitor pricing is unavailable.")
            ]);
}
