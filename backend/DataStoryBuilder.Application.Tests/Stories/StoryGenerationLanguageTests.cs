using DataStoryBuilder.Application.Stories;
using Xunit;

namespace DataStoryBuilder.Application.Tests.Stories;

public sealed class StoryGenerationLanguageTests
{
    [Theory]
    [InlineData("tr", "tr")]
    [InlineData("en", "en")]
    public void SupportedLanguageIsAccepted(string input, string expected)
    {
        Assert.True(StoryGenerationLanguage.TryNormalize(input, out var actual));
        Assert.Equal(expected, actual);
    }

    [Theory]
    [InlineData("de")]
    [InlineData("TR")]
    [InlineData("en-US")]
    public void UnsupportedLanguageIsRejected(string input)
    {
        Assert.False(StoryGenerationLanguage.TryNormalize(input, out _));
    }

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("   ")]
    public void MissingLanguageDefaultsToEnglish(string? input)
    {
        Assert.True(StoryGenerationLanguage.TryNormalize(input, out var actual));
        Assert.Equal("en", actual);
    }
}
