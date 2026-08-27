using System.Text.Json;
using DataStoryBuilder.Application.Stories;
using Xunit;

namespace DataStoryBuilder.Application.Tests.Stories;

public sealed class GeneratedExecutiveStoryTests
{
    [Fact]
    public void ValidStoryCanBeCreated()
    {
        var story = CreateStory();

        Assert.Equal("Revenue strengthened", story.Title);
        Assert.Single(story.Sections);
        Assert.Equal("main-outcome", story.Sections[0].Items[0].SourceItemId);
    }

    [Theory]
    [InlineData("")]
    [InlineData("   ")]
    public void BlankTitleIsRejected(string title)
    {
        Assert.Throws<ArgumentException>(() =>
            new GeneratedExecutiveStory(
                title,
                "Revenue moved during the period.",
                [CreateSection()]));
    }

    [Theory]
    [InlineData("")]
    [InlineData("   ")]
    public void BlankExecutiveSummaryIsRejected(string summary)
    {
        Assert.Throws<ArgumentException>(() =>
            new GeneratedExecutiveStory(
                "Revenue strengthened",
                summary,
                [CreateSection()]));
    }

    [Fact]
    public void NoSectionsIsRejected()
    {
        Assert.Throws<ArgumentException>(() =>
            new GeneratedExecutiveStory(
                "Revenue strengthened",
                "Revenue moved during the period.",
                []));
    }

    [Theory]
    [InlineData(0)]
    [InlineData(-1)]
    public void NonPositiveSectionOrderIsRejected(int order)
    {
        Assert.Throws<ArgumentOutOfRangeException>(() =>
            new GeneratedStorySection(
                order,
                "OUTCOME",
                [CreateItem()]));
    }

    [Theory]
    [InlineData("")]
    [InlineData("   ")]
    public void BlankSectionTypeIsRejected(string type)
    {
        Assert.Throws<ArgumentException>(() =>
            new GeneratedStorySection(1, type, [CreateItem()]));
    }

    [Fact]
    public void EmptySectionItemsAreRejected()
    {
        Assert.Throws<ArgumentException>(() =>
            new GeneratedStorySection(1, "OUTCOME", []));
    }

    [Theory]
    [InlineData("")]
    [InlineData("   ")]
    public void BlankSourceItemIdIsRejected(string sourceItemId)
    {
        Assert.Throws<ArgumentException>(() =>
            new GeneratedStoryItem(sourceItemId, "Revenue increased."));
    }

    [Theory]
    [InlineData("")]
    [InlineData("   ")]
    public void BlankItemTextIsRejected(string text)
    {
        Assert.Throws<ArgumentException>(() =>
            new GeneratedStoryItem("main-outcome", text));
    }

    [Fact]
    public void DuplicateSectionOrderIsRejected()
    {
        Assert.Throws<ArgumentException>(() =>
            new GeneratedExecutiveStory(
                "Revenue strengthened",
                "Revenue moved during the period.",
                [
                    CreateSection(),
                    new GeneratedStorySection(
                        1,
                        "LIMITATIONS",
                        [new GeneratedStoryItem("context-1", "Context is unavailable.")])
                ]));
    }

    [Fact]
    public void DuplicateSourceItemIdWithinSectionIsRejected()
    {
        Assert.Throws<ArgumentException>(() =>
            new GeneratedStorySection(
                1,
                "OUTCOME",
                [
                    CreateItem(),
                    new GeneratedStoryItem("main-outcome", "Repeated wording.")
                ]));
    }

    [Fact]
    public void JsonRoundTripUsesCamelCaseWebShape()
    {
        var expected = CreateStory();
        var options = new JsonSerializerOptions(JsonSerializerDefaults.Web);

        var json = JsonSerializer.Serialize(expected, options);
        var actual = JsonSerializer.Deserialize<GeneratedExecutiveStory>(
            json,
            options);

        Assert.Contains("\"executiveSummary\"", json);
        Assert.Contains("\"sourceItemId\"", json);
        Assert.NotNull(actual);
        Assert.Equal(expected.Title, actual.Title);
        Assert.Equal(expected.ExecutiveSummary, actual.ExecutiveSummary);
        Assert.Equal(expected.Sections.Count, actual.Sections.Count);
        Assert.Equal(expected.Sections[0].Order, actual.Sections[0].Order);
        Assert.Equal(expected.Sections[0].Type, actual.Sections[0].Type);
        Assert.Equal(
            expected.Sections[0].Items[0],
            actual.Sections[0].Items[0]);
    }

    private static GeneratedExecutiveStory CreateStory() =>
        new(
            "Revenue strengthened",
            "Revenue moved during the period.",
            [CreateSection()]);

    private static GeneratedStorySection CreateSection() =>
        new(1, "OUTCOME", [CreateItem()]);

    private static GeneratedStoryItem CreateItem() =>
        new("main-outcome", "Revenue increased during the period.");
}
