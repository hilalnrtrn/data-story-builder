using System.Text.Json;
using DataStoryBuilder.Application.Stories;
using Xunit;

namespace DataStoryBuilder.Application.Tests.Stories;

public sealed class StoryNumericalAuditorTests
{
    [Theory]
    [InlineData("Revenue reached 1.300.000 TL.", "1.300.000", "1300000", false)]
    [InlineData("Previous revenue was 1.000.000 TL.", "1.000.000", "1000000", false)]
    [InlineData("Marmara contributed 210.000 TL.", "210.000", "210000", false)]
    [InlineData("Smart Watch revenue was 145.000 TL.", "145.000", "145000", false)]
    [InlineData("Gelir %30 arttı.", "%30", "30", true)]
    [InlineData("Müşteriler %12 azaldı.", "%12", "12", true)]
    [InlineData("Marmara katkısı %70 oldu.", "%70", "70", true)]
    [InlineData("Oran 30,5 seviyesine ulaştı.", "30,5", "30.5", false)]
    [InlineData("Revenue reached 1,300,000.", "1,300,000", "1300000", false)]
    [InlineData("Revenue increased 30%.", "30%", "30", true)]
    [InlineData("Revenue reached 1300000.", "1300000", "1300000", false)]
    public void ExtractTokensSupportsLocalizedAndInvariantForms(
        string text,
        string original,
        string normalized,
        bool isPercent)
    {
        var token = Assert.Single(StoryNumericalAuditor.ExtractTokens(text));

        Assert.Equal(original, token.OriginalText);
        Assert.Equal(decimal.Parse(normalized, System.Globalization.CultureInfo.InvariantCulture), token.NormalizedValue);
        Assert.Equal(isPercent, token.IsPercent);
    }

    [Theory]
    [InlineData("30%", "30", "PERCENT")]
    [InlineData("12%", "-12", "PERCENT")]
    [InlineData("70%", "0.70", "RATIO")]
    [InlineData("%70", "0.70", "RATIO")]
    [InlineData("76.7%", "0.766667", "RATIO")]
    [InlineData("%76,7", "0.766667", "RATIO")]
    [InlineData("76.67%", "0.766667", "RATIO")]
    [InlineData("%76,67", "0.766667", "RATIO")]
    [InlineData("76.667%", "0.766667", "RATIO")]
    [InlineData("0.70", "0.70", "RATIO")]
    [InlineData("1,300,000", "1300000", null)]
    [InlineData("1300000", "1300000", null)]
    [InlineData("0", "0", null)]
    [InlineData("0%", "0", "PERCENT")]
    [InlineData("1,500.50", "1500.50", null)]
    public void SupportedFormsMatchGroundedEvidence(
        string token,
        string evidenceValue,
        string? unit)
    {
        var audit = Audit(token, Evidence("VALUE", evidenceValue, unit));
        Assert.True(audit.Passed);
        Assert.Empty(audit.UnsupportedTokens);
        Assert.Single(audit.ExtractedTokens);
    }

    [Theory]
    [InlineData("32%", "30", "PERCENT")]
    [InlineData("10%", "-12", "PERCENT")]
    [InlineData("75%", "0.70", "RATIO")]
    [InlineData("76.8%", "0.766667", "RATIO")]
    [InlineData("%76,8", "0.766667", "RATIO")]
    [InlineData("%75", "0.766667", "RATIO")]
    [InlineData("76%", "0.766667", "RATIO")]
    [InlineData("1,500,000", "1300000", null)]
    [InlineData("30", "30", "PERCENT")]
    public void UnsupportedFormsAreRetainedAsMismatches(
        string token,
        string evidenceValue,
        string? unit)
    {
        var audit = Audit(token, Evidence("VALUE", evidenceValue, unit));
        var mismatch = Assert.Single(audit.UnsupportedTokens);
        Assert.False(audit.Passed);
        Assert.Equal(token, mismatch.OriginalToken);
        Assert.Equal(Assert.Single(audit.ExtractedTokens).NormalizedValue, mismatch.NormalizedValue);
        Assert.Equal("item-1", mismatch.SourceItemId);
    }

    [Fact]
    public void RevenueSentenceMatchesAllGroundedNumbers()
    {
        var audit = Audit(
            "Revenue moved from 1,000,000 to 1,300,000, an increase of 300,000 or 30%.",
            Evidence("PREVIOUS_PERIOD_VALUE", "1000000"),
            Evidence("CURRENT_PERIOD_VALUE", "1300000"),
            Evidence("ABSOLUTE_CHANGE", "300000"),
            Evidence("PERCENTAGE_CHANGE", "30", "PERCENT"));

        Assert.True(audit.Passed);
        Assert.Equal(4, audit.ExtractedTokens.Count);
    }

    [Fact]
    public void TurkishRevenueSentenceMatchesAuthoritativeEvidence()
    {
        var audit = Audit(
            "Gelir %30 artış göstererek 1.300.000 TL'ye yükseldi (önceki dönem 1.000.000 TL).",
            Evidence("PREVIOUS_PERIOD_VALUE", "1000000"),
            Evidence("CURRENT_PERIOD_VALUE", "1300000"),
            Evidence("PERCENTAGE_CHANGE", "30", "PERCENT"));

        Assert.True(audit.Passed);
        Assert.Empty(audit.UnsupportedTokens);
        Assert.Equal(3, audit.ExtractedTokens.Count);
    }

    [Theory]
    [InlineData("30%", "32", "PERCENT")]
    [InlineData("1.300.000", "1200000", null)]
    [InlineData("%30", "25", "PERCENT")]
    public void LocalizedFormsDoNotWeakenAuthoritativeMatching(
        string token,
        string evidenceValue,
        string? unit)
    {
        var audit = Audit(token, Evidence("VALUE", evidenceValue, unit));

        Assert.False(audit.Passed);
        Assert.Single(audit.UnsupportedTokens);
    }

    [Fact]
    public void OrdersSentenceUsesMagnitudeAndDoesNotRequireEveryEvidenceValue()
    {
        var audit = Audit(
            "Orders moved from 10,000 to 8,500, a decline of 15%.",
            Evidence("PREVIOUS_PERIOD_VALUE", "10000"),
            Evidence("CURRENT_PERIOD_VALUE", "8500"),
            Evidence("ABSOLUTE_CHANGE", "-1500"),
            Evidence("PERCENTAGE_CHANGE", "-15", "PERCENT"));

        Assert.True(audit.Passed);
        Assert.Equal(3, audit.ExtractedTokens.Count);
    }

    [Fact]
    public void AnomalyDoesNotRequireOmittedBounds()
    {
        var audit = Audit(
            "Smart Watch Revenue was a high June anomaly at 145,000.",
            Evidence("OBSERVED_VALUE", "145000"),
            Evidence("IQR_Q1", "72500"),
            Evidence("IQR_UPPER_BOUND", "84500"));

        Assert.True(audit.Passed);
        Assert.Single(audit.ExtractedTokens);
    }

    [Fact]
    public void NonnumericEvidenceIsIgnored()
    {
        using var stringValue = JsonDocument.Parse("\"PRIMARY_POSITIVE_CONTRIBUTOR\"");
        var audit = Audit(
            "Contribution was 70%.",
            new GroundedStoryEvidence(
                "CONTRIBUTOR_ROLE",
                "Role",
                stringValue.RootElement.Clone(),
                null));

        Assert.False(audit.Passed);
        Assert.Single(audit.UnsupportedTokens);
    }

    [Theory]
    [InlineData("June 2025")]
    [InlineData("Period 2025-06")]
    [InlineData("Period 2025-06-01")]
    public void DatesAndStandaloneCalendarYearsAreExcluded(string text)
    {
        Assert.Empty(StoryNumericalAuditor.ExtractTokens(text));
    }

    [Fact]
    public void EvidenceFromAnotherSourceItemCannotValidateCurrentItem()
    {
        var first = Source("first", "Revenue was 1,300,000.", Evidence("VALUE", "1000000"));
        var second = Source("second", "Revenue was 1,000,000.", Evidence("VALUE", "1300000"));

        var audits = StoryNumericalAuditor.Audit([first, second]);

        Assert.All(audits, audit => Assert.False(audit.Passed));
    }

    [Fact]
    public void LimitationsAndUnresolvedItemsAreOutsideNumericalAuditScope()
    {
        var limitation = new StoryItemAuditSource(
            "limit", "Unavailable in 2024.", "MISSING_CONTEXT", "insight", true, [], true);
        var unresolved = new StoryItemAuditSource(
            "unknown", "Invented 99.", null, null, false, [], false);

        Assert.Empty(StoryNumericalAuditor.Audit([limitation, unresolved]));
    }

    private static StoryItemNumericalAudit Audit(
        string text,
        params GroundedStoryEvidence[] evidence) =>
        Assert.Single(StoryNumericalAuditor.Audit([Source("item-1", text, evidence)]));

    private static StoryItemAuditSource Source(
        string id,
        string text,
        params GroundedStoryEvidence[] evidence) =>
        new(id, text, "MAIN_OUTCOME", $"insight-{id}", false, evidence, true);

    private static GroundedStoryEvidence Evidence(
        string code,
        string value,
        string? unit = null)
    {
        using var document = JsonDocument.Parse(value);
        return new GroundedStoryEvidence(
            code,
            code,
            document.RootElement.Clone(),
            unit);
    }
}
