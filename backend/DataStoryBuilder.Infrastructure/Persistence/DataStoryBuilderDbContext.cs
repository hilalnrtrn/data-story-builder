using DataStoryBuilder.Domain.Entities;
using Microsoft.EntityFrameworkCore;

namespace DataStoryBuilder.Infrastructure.Persistence;

public class DataStoryBuilderDbContext(
    DbContextOptions<DataStoryBuilderDbContext> options)
    : DbContext(options)
{
    public DbSet<Analysis> Analyses => Set<Analysis>();
    public DbSet<DatasetProfile> DatasetProfiles => Set<DatasetProfile>();
    public DbSet<Insight> Insights => Set<Insight>();
    public DbSet<Evidence> Evidence => Set<Evidence>();
    public DbSet<Relationship> Relationships => Set<Relationship>();
    public DbSet<InsightCluster> InsightClusters => Set<InsightCluster>();
    public DbSet<InsightIntegrityEvaluation> InsightIntegrityEvaluations =>
        Set<InsightIntegrityEvaluation>();
    public DbSet<CausalityEvaluation> CausalityEvaluations =>
        Set<CausalityEvaluation>();
    public DbSet<MissingContextEvaluation> MissingContextEvaluations =>
        Set<MissingContextEvaluation>();
    public DbSet<Story> Stories => Set<Story>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        base.OnModelCreating(modelBuilder);

        modelBuilder.Entity<Analysis>(analysis =>
        {
            analysis.ToTable("analyses");
            analysis.HasKey(item => item.Id);

            analysis.Property(item => item.Id)
                .HasColumnName("id")
                .ValueGeneratedNever();
            analysis.Property(item => item.FileName)
                .HasColumnName("file_name")
                .HasMaxLength(512)
                .IsRequired();
            analysis.Property(item => item.FileType)
                .HasColumnName("file_type")
                .HasMaxLength(32)
                .IsRequired();
            analysis.Property(item => item.Status)
                .HasColumnName("status")
                .HasConversion<string>()
                .HasMaxLength(32)
                .IsRequired();
            analysis.Property(item => item.CreatedAt)
                .HasColumnName("created_at")
                .IsRequired();
            analysis.Property(item => item.CompletedAt)
                .HasColumnName("completed_at");
            analysis.Property(item => item.RowCount)
                .HasColumnName("row_count")
                .IsRequired();
            analysis.Property(item => item.ColumnCount)
                .HasColumnName("column_count")
                .IsRequired();
            analysis.Property(item => item.DataQualityScore)
                .HasColumnName("data_quality_score");
            analysis.Property(item => item.AnalysisVersion)
                .HasColumnName("analysis_version")
                .HasMaxLength(64)
                .IsRequired();
            analysis.Property(item => item.FailureReason)
                .HasColumnName("failure_reason")
                .HasMaxLength(2000);
        });

        modelBuilder.Entity<DatasetProfile>(profile =>
        {
            profile.ToTable("analysis_profiles");
            profile.HasKey(item => item.Id);

            profile.Property(item => item.Id)
                .HasColumnName("id");
            profile.Property(item => item.AnalysisId)
                .HasColumnName("analysis_id")
                .IsRequired();
            profile.Property(item => item.ProfileJson)
                .HasColumnName("profile_json")
                .HasColumnType("jsonb")
                .IsRequired();
            profile.Property(item => item.QualityJson)
                .HasColumnName("quality_json")
                .HasColumnType("jsonb")
                .IsRequired();

            profile.HasIndex(item => item.AnalysisId)
                .IsUnique();
            profile.HasOne<Analysis>()
                .WithOne()
                .HasForeignKey<DatasetProfile>(item => item.AnalysisId)
                .OnDelete(DeleteBehavior.Cascade);
        });

        modelBuilder.Entity<Insight>(insight =>
        {
            insight.ToTable("insights");
            insight.HasKey(item => new { item.AnalysisId, item.Id });

            insight.Property(item => item.AnalysisId)
                .HasColumnName("analysis_id")
                .IsRequired();
            insight.Property(item => item.Id)
                .HasColumnName("id")
                .HasMaxLength(512)
                .IsRequired();
            insight.Property(item => item.Type)
                .HasColumnName("type")
                .HasMaxLength(64)
                .IsRequired();
            insight.Property(item => item.Metric)
                .HasColumnName("metric")
                .HasMaxLength(128)
                .IsRequired();
            insight.Property(item => item.Dimension)
                .HasColumnName("dimension")
                .HasMaxLength(128);
            insight.Property(item => item.Segment)
                .HasColumnName("segment")
                .HasMaxLength(256);
            insight.Property(item => item.PeriodGranularity)
                .HasColumnName("period_granularity")
                .HasMaxLength(32);
            insight.Property(item => item.Direction)
                .HasColumnName("direction")
                .HasMaxLength(32);
            insight.Property(item => item.Confidence)
                .HasColumnName("confidence");
            insight.Property(item => item.Importance)
                .HasColumnName("importance");
            insight.Property(item => item.BusinessRelevance)
                .HasColumnName("business_relevance");
            insight.Property(item => item.ImpactDirection)
                .HasColumnName("impact_direction")
                .HasMaxLength(64);
            insight.Property(item => item.PriorityScore)
                .HasColumnName("priority_score");
            insight.Property(item => item.PriorityLevel)
                .HasColumnName("priority_level")
                .HasMaxLength(32);
            insight.Property(item => item.Rank)
                .HasColumnName("rank");
            insight.Property(item => item.PeriodJson)
                .HasColumnName("period_json")
                .HasColumnType("jsonb")
                .IsRequired();
            insight.Property(item => item.ValuesJson)
                .HasColumnName("values_json")
                .HasColumnType("jsonb")
                .IsRequired();
            insight.Property(item => item.DetectionJson)
                .HasColumnName("detection_json")
                .HasColumnType("jsonb")
                .IsRequired();
            insight.Property(item => item.ConfidenceBreakdownJson)
                .HasColumnName("confidence_breakdown_json")
                .HasColumnType("jsonb")
                .IsRequired();
            insight.Property(item => item.ImportanceBreakdownJson)
                .HasColumnName("importance_breakdown_json")
                .HasColumnType("jsonb")
                .IsRequired();
            insight.Property(item => item.SourceJson)
                .HasColumnName("source_json")
                .HasColumnType("jsonb")
                .IsRequired(false);
            insight.Property(item => item.BusinessRelevanceDetailsJson)
                .HasColumnName("business_relevance_details_json")
                .HasColumnType("jsonb")
                .IsRequired(false);
            insight.Property(item => item.PriorityDetailsJson)
                .HasColumnName("priority_details_json")
                .HasColumnType("jsonb")
                .IsRequired(false);
            insight.Property(item => item.RankingDetailsJson)
                .HasColumnName("ranking_details_json")
                .HasColumnType("jsonb")
                .IsRequired(false);

            insight.HasOne<Analysis>()
                .WithMany()
                .HasForeignKey(item => item.AnalysisId)
                .OnDelete(DeleteBehavior.Cascade);
        });

        modelBuilder.Entity<Evidence>(evidence =>
        {
            evidence.ToTable("evidence");
            evidence.HasKey(item => new
            {
                item.AnalysisId,
                item.InsightId,
                item.Ordinal
            });

            evidence.Property(item => item.AnalysisId)
                .HasColumnName("analysis_id")
                .IsRequired();
            evidence.Property(item => item.InsightId)
                .HasColumnName("insight_id")
                .HasMaxLength(512)
                .IsRequired();
            evidence.Property(item => item.Ordinal)
                .HasColumnName("ordinal")
                .IsRequired();
            evidence.Property(item => item.Code)
                .HasColumnName("code")
                .HasMaxLength(128)
                .IsRequired();
            evidence.Property(item => item.Label)
                .HasColumnName("label")
                .HasMaxLength(512)
                .IsRequired();
            evidence.Property(item => item.ValueJson)
                .HasColumnName("value_json")
                .HasColumnType("jsonb")
                .IsRequired();
            evidence.Property(item => item.Unit)
                .HasColumnName("unit")
                .HasMaxLength(64);

            evidence.HasOne<Insight>()
                .WithMany()
                .HasForeignKey(item => new
                {
                    item.AnalysisId,
                    item.InsightId
                })
                .HasPrincipalKey(item => new
                {
                    item.AnalysisId,
                    item.Id
                })
                .OnDelete(DeleteBehavior.Cascade);
        });

        modelBuilder.Entity<Relationship>(relationship =>
        {
            relationship.ToTable("relationships");
            relationship.HasKey(item => new { item.AnalysisId, item.Id });

            relationship.Property(item => item.AnalysisId)
                .HasColumnName("analysis_id")
                .IsRequired();
            relationship.Property(item => item.Id)
                .HasColumnName("id")
                .HasMaxLength(512)
                .IsRequired();
            relationship.Property(item => item.SourceInsightId)
                .HasColumnName("source_insight_id")
                .HasMaxLength(512)
                .IsRequired();
            relationship.Property(item => item.TargetInsightId)
                .HasColumnName("target_insight_id")
                .HasMaxLength(512)
                .IsRequired();
            relationship.Property(item => item.Type)
                .HasColumnName("type")
                .HasMaxLength(64)
                .IsRequired();
            relationship.Property(item => item.Strength)
                .HasColumnName("strength")
                .IsRequired();
            relationship.Property(item => item.Confidence)
                .HasColumnName("confidence")
                .IsRequired();
            relationship.Property(item => item.StrengthBreakdownJson)
                .HasColumnName("strength_breakdown_json")
                .HasColumnType("jsonb")
                .IsRequired();
            relationship.Property(item => item.ConfidenceBreakdownJson)
                .HasColumnName("confidence_breakdown_json")
                .HasColumnType("jsonb")
                .IsRequired();
            relationship.Property(item => item.ReasonsJson)
                .HasColumnName("reasons_json")
                .HasColumnType("jsonb")
                .IsRequired();
            relationship.Property(item => item.MetadataJson)
                .HasColumnName("metadata_json")
                .HasColumnType("jsonb")
                .IsRequired();

            relationship.HasOne<Analysis>()
                .WithMany()
                .HasForeignKey(item => item.AnalysisId)
                .OnDelete(DeleteBehavior.Cascade);
            relationship.HasOne<Insight>()
                .WithMany()
                .HasForeignKey(item => new
                {
                    item.AnalysisId,
                    item.SourceInsightId
                })
                .HasPrincipalKey(item => new
                {
                    item.AnalysisId,
                    item.Id
                })
                .OnDelete(DeleteBehavior.Restrict);
            relationship.HasOne<Insight>()
                .WithMany()
                .HasForeignKey(item => new
                {
                    item.AnalysisId,
                    item.TargetInsightId
                })
                .HasPrincipalKey(item => new
                {
                    item.AnalysisId,
                    item.Id
                })
                .OnDelete(DeleteBehavior.Restrict);
        });

        modelBuilder.Entity<InsightCluster>(cluster =>
        {
            cluster.ToTable("insight_clusters");
            cluster.HasKey(item => new { item.AnalysisId, item.Id });

            cluster.Property(item => item.AnalysisId)
                .HasColumnName("analysis_id")
                .IsRequired();
            cluster.Property(item => item.Id)
                .HasColumnName("id")
                .HasMaxLength(512)
                .IsRequired();
            cluster.Property(item => item.AnchorInsightId)
                .HasColumnName("anchor_insight_id")
                .HasMaxLength(512)
                .IsRequired();
            cluster.Property(item => item.MemberInsightIdsJson)
                .HasColumnName("member_insight_ids_json")
                .HasColumnType("jsonb")
                .IsRequired();
            cluster.Property(item => item.RelationshipIdsJson)
                .HasColumnName("relationship_ids_json")
                .HasColumnType("jsonb")
                .IsRequired();

            cluster.HasOne<Insight>()
                .WithMany()
                .HasForeignKey(item => new
                {
                    item.AnalysisId,
                    item.AnchorInsightId
                })
                .HasPrincipalKey(item => new
                {
                    item.AnalysisId,
                    item.Id
                })
                .OnDelete(DeleteBehavior.Cascade);
        });

        modelBuilder.Entity<InsightIntegrityEvaluation>(integrity =>
        {
            integrity.ToTable("insight_integrity_evaluations");
            integrity.HasKey(item => new { item.AnalysisId, item.InsightId });

            integrity.Property(item => item.AnalysisId)
                .HasColumnName("analysis_id")
                .IsRequired();
            integrity.Property(item => item.InsightId)
                .HasColumnName("insight_id")
                .HasMaxLength(512)
                .IsRequired();
            integrity.Property(item => item.Status)
                .HasColumnName("status")
                .HasMaxLength(64)
                .IsRequired();
            integrity.Property(item => item.IntegrityScore)
                .HasColumnName("integrity_score");
            integrity.Property(item => item.StoryEligible)
                .HasColumnName("story_eligible")
                .IsRequired();
            integrity.Property(item => item.RequiresQualification)
                .HasColumnName("requires_qualification")
                .IsRequired();
            integrity.Property(item => item.CounterEvidenceJson)
                .HasColumnName("counter_evidence_json")
                .HasColumnType("jsonb")
                .IsRequired();
            integrity.Property(item => item.ContradictionsJson)
                .HasColumnName("contradictions_json")
                .HasColumnType("jsonb")
                .IsRequired();
            integrity.Property(item => item.OutlierCheckJson)
                .HasColumnName("outlier_check_json")
                .HasColumnType("jsonb")
                .IsRequired(false);
            integrity.Property(item => item.OneOffCheckJson)
                .HasColumnName("one_off_check_json")
                .HasColumnType("jsonb")
                .IsRequired(false);
            integrity.Property(item => item.ConsistencyChecksJson)
                .HasColumnName("consistency_checks_json")
                .HasColumnType("jsonb")
                .IsRequired();
            integrity.Property(item => item.IntegrityBreakdownJson)
                .HasColumnName("integrity_breakdown_json")
                .HasColumnType("jsonb")
                .IsRequired();
            integrity.Property(item => item.ReasonsJson)
                .HasColumnName("reasons_json")
                .HasColumnType("jsonb")
                .IsRequired();

            integrity.HasOne<Insight>()
                .WithMany()
                .HasForeignKey(item => new
                {
                    item.AnalysisId,
                    item.InsightId
                })
                .HasPrincipalKey(item => new
                {
                    item.AnalysisId,
                    item.Id
                })
                .OnDelete(DeleteBehavior.Cascade);
        });

        modelBuilder.Entity<CausalityEvaluation>(causality =>
        {
            causality.ToTable("causality_evaluations");
            causality.HasKey(item => new
            {
                item.AnalysisId,
                item.RelationshipId
            });

            causality.Property(item => item.AnalysisId)
                .HasColumnName("analysis_id")
                .IsRequired();
            causality.Property(item => item.RelationshipId)
                .HasColumnName("relationship_id")
                .HasMaxLength(512)
                .IsRequired();
            causality.Property(item => item.SourceInsightId)
                .HasColumnName("source_insight_id")
                .HasMaxLength(512)
                .IsRequired();
            causality.Property(item => item.TargetInsightId)
                .HasColumnName("target_insight_id")
                .HasMaxLength(512)
                .IsRequired();
            causality.Property(item => item.SourceMetric)
                .HasColumnName("source_metric")
                .HasMaxLength(128)
                .IsRequired();
            causality.Property(item => item.TargetMetric)
                .HasColumnName("target_metric")
                .HasMaxLength(128)
                .IsRequired();
            causality.Property(item => item.Status)
                .HasColumnName("status")
                .HasMaxLength(64)
                .IsRequired();
            causality.Property(item => item.AssociationPresent)
                .HasColumnName("association_present")
                .IsRequired();
            causality.Property(item => item.CausalityEstablished)
                .HasColumnName("causality_established")
                .IsRequired();
            causality.Property(item => item.CausalEvidenceJson)
                .HasColumnName("causal_evidence_json")
                .HasColumnType("jsonb")
                .IsRequired();
            causality.Property(item => item.AllowedConceptsJson)
                .HasColumnName("allowed_concepts_json")
                .HasColumnType("jsonb")
                .IsRequired();
            causality.Property(item => item.ForbiddenConceptsJson)
                .HasColumnName("forbidden_concepts_json")
                .HasColumnType("jsonb")
                .IsRequired();
            causality.Property(item => item.ReasonsJson)
                .HasColumnName("reasons_json")
                .HasColumnType("jsonb")
                .IsRequired();

            causality.HasOne<Relationship>()
                .WithMany()
                .HasForeignKey(item => new
                {
                    item.AnalysisId,
                    item.RelationshipId
                })
                .HasPrincipalKey(item => new
                {
                    item.AnalysisId,
                    item.Id
                })
                .OnDelete(DeleteBehavior.Cascade);
        });

        modelBuilder.Entity<MissingContextEvaluation>(missingContext =>
        {
            missingContext.ToTable("missing_context_evaluations");
            missingContext.HasKey(item => new
            {
                item.AnalysisId,
                item.InsightId
            });

            missingContext.Property(item => item.AnalysisId)
                .HasColumnName("analysis_id")
                .IsRequired();
            missingContext.Property(item => item.InsightId)
                .HasColumnName("insight_id")
                .HasMaxLength(512)
                .IsRequired();
            missingContext.Property(item => item.InterpretationLimited)
                .HasColumnName("interpretation_limited")
                .IsRequired();
            missingContext.Property(item => item.MissingContextJson)
                .HasColumnName("missing_context_json")
                .HasColumnType("jsonb")
                .IsRequired();
            missingContext.Property(item => item.ReasonsJson)
                .HasColumnName("reasons_json")
                .HasColumnType("jsonb")
                .IsRequired();
            missingContext.Property(item => item.ContextSummaryJson)
                .HasColumnName("context_summary_json")
                .HasColumnType("jsonb")
                .IsRequired();

            missingContext.HasOne<Insight>()
                .WithMany()
                .HasForeignKey(item => new
                {
                    item.AnalysisId,
                    item.InsightId
                })
                .HasPrincipalKey(item => new
                {
                    item.AnalysisId,
                    item.Id
                })
                .OnDelete(DeleteBehavior.Cascade);
        });

        modelBuilder.Entity<Story>(story =>
        {
            story.ToTable("stories");
            story.HasKey(item => item.Id);

            story.Property(item => item.Id)
                .HasColumnName("id")
                .ValueGeneratedNever();
            story.Property(item => item.AnalysisId)
                .HasColumnName("analysis_id")
                .IsRequired();
            story.Property(item => item.PlannerVersion)
                .HasColumnName("planner_version")
                .HasMaxLength(64)
                .IsRequired();
            story.Property(item => item.StoryPlanJson)
                .HasColumnName("story_plan_json")
                .HasColumnType("jsonb")
                .IsRequired();
            story.Property(item => item.CreatedAt)
                .HasColumnName("created_at")
                .IsRequired();
            story.Property(item => item.GeneratedStoryJson)
                .HasColumnName("generated_story_json")
                .HasColumnType("jsonb");
            story.Property(item => item.StoryAuditJson)
                .HasColumnName("story_audit_json")
                .HasColumnType("jsonb");
            story.Property(item => item.PromptVersion)
                .HasColumnName("prompt_version")
                .HasMaxLength(64);
            story.Property(item => item.ModelIdentifier)
                .HasColumnName("model_identifier")
                .HasMaxLength(128);
            story.Property(item => item.GeneratedAt)
                .HasColumnName("generated_at");
            story.Property(item => item.GenerationStatus)
                .HasColumnName("generation_status")
                .HasMaxLength(16);
            story.Property(item => item.GenerationFailureReason)
                .HasColumnName("generation_failure_reason")
                .HasMaxLength(1000);

            story.HasIndex(item => item.AnalysisId)
                .IsUnique();
            story.HasOne<Analysis>()
                .WithOne()
                .HasForeignKey<Story>(item => item.AnalysisId)
                .OnDelete(DeleteBehavior.Cascade);
        });
    }
}
