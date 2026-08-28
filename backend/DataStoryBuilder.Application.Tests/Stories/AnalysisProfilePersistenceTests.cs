using System.Text.Json;
using DataStoryBuilder.Infrastructure.Persistence;
using Xunit;

namespace DataStoryBuilder.Application.Tests.Stories;

public sealed class AnalysisProfilePersistenceTests
{
    [Fact]
    public void ProfileProjectionPreservesOverviewChartContract()
    {
        using var response = JsonDocument.Parse(
            """
            {
              "rawSchema": {},
              "preparedSchema": { "rowCount": 2, "columnCount": 2 },
              "preparationReport": {},
              "datasetProfile": {},
              "overviewCharts": {
                "revenueOverTime": {
                  "status": "READY",
                  "metric": "Revenue",
                  "aggregation": "SUM",
                  "granularity": "MONTH",
                  "periodStart": "2030-01",
                  "periodEnd": "2030-02",
                  "points": [
                    { "period": "2030-01", "value": 12.5 },
                    { "period": "2030-02", "value": 18.75 }
                  ],
                  "unavailableReason": null
                }
              },
              "semanticRoles": {},
              "integrity": {},
              "dataQuality": { "score": 100 }
            }
            """);

        var profileJson = AnalysisProfilePersistence.BuildProfileJson(
            response.RootElement);

        using var profile = JsonDocument.Parse(profileJson);
        var chart = profile.RootElement
            .GetProperty("overviewCharts")
            .GetProperty("revenueOverTime");

        Assert.Equal("READY", chart.GetProperty("status").GetString());
        Assert.Equal("SUM", chart.GetProperty("aggregation").GetString());
        Assert.Equal(2, chart.GetProperty("points").GetArrayLength());
        Assert.Equal(
            18.75,
            chart.GetProperty("points")[1].GetProperty("value").GetDouble());
    }
}
