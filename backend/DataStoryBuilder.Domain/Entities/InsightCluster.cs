namespace DataStoryBuilder.Domain.Entities;

public class InsightCluster
{
    public string Id { get; set; } = string.Empty;
    public Guid AnalysisId { get; set; }
    public string AnchorInsightId { get; set; } = string.Empty;
    public string MemberInsightIdsJson { get; set; } = "[]";
    public string RelationshipIdsJson { get; set; } = "[]";
}
