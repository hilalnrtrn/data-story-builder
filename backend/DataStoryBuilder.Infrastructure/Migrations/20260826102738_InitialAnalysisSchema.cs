using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace DataStoryBuilder.Infrastructure.Migrations
{
    /// <inheritdoc />
    public partial class InitialAnalysisSchema : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "analyses",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false),
                    file_name = table.Column<string>(type: "character varying(512)", maxLength: 512, nullable: false),
                    file_type = table.Column<string>(type: "character varying(32)", maxLength: 32, nullable: false),
                    status = table.Column<string>(type: "character varying(32)", maxLength: 32, nullable: false),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false),
                    completed_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: true),
                    row_count = table.Column<int>(type: "integer", nullable: false),
                    column_count = table.Column<int>(type: "integer", nullable: false),
                    data_quality_score = table.Column<double>(type: "double precision", nullable: true),
                    analysis_version = table.Column<string>(type: "character varying(64)", maxLength: 64, nullable: false),
                    failure_reason = table.Column<string>(type: "character varying(2000)", maxLength: 2000, nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_analyses", x => x.id);
                });

            migrationBuilder.CreateTable(
                name: "analysis_profiles",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false),
                    analysis_id = table.Column<Guid>(type: "uuid", nullable: false),
                    profile_json = table.Column<string>(type: "jsonb", nullable: false),
                    quality_json = table.Column<string>(type: "jsonb", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_analysis_profiles", x => x.id);
                    table.ForeignKey(
                        name: "FK_analysis_profiles_analyses_analysis_id",
                        column: x => x.analysis_id,
                        principalTable: "analyses",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateTable(
                name: "insights",
                columns: table => new
                {
                    id = table.Column<string>(type: "character varying(512)", maxLength: 512, nullable: false),
                    analysis_id = table.Column<Guid>(type: "uuid", nullable: false),
                    type = table.Column<string>(type: "character varying(64)", maxLength: 64, nullable: false),
                    metric = table.Column<string>(type: "character varying(128)", maxLength: 128, nullable: false),
                    dimension = table.Column<string>(type: "character varying(128)", maxLength: 128, nullable: true),
                    segment = table.Column<string>(type: "character varying(256)", maxLength: 256, nullable: true),
                    period_granularity = table.Column<string>(type: "character varying(32)", maxLength: 32, nullable: true),
                    direction = table.Column<string>(type: "character varying(32)", maxLength: 32, nullable: true),
                    confidence = table.Column<double>(type: "double precision", nullable: true),
                    importance = table.Column<double>(type: "double precision", nullable: true),
                    business_relevance = table.Column<double>(type: "double precision", nullable: true),
                    impact_direction = table.Column<string>(type: "character varying(64)", maxLength: 64, nullable: true),
                    priority_score = table.Column<double>(type: "double precision", nullable: true),
                    priority_level = table.Column<string>(type: "character varying(32)", maxLength: 32, nullable: true),
                    rank = table.Column<int>(type: "integer", nullable: true),
                    period_json = table.Column<string>(type: "jsonb", nullable: false),
                    values_json = table.Column<string>(type: "jsonb", nullable: false),
                    detection_json = table.Column<string>(type: "jsonb", nullable: false),
                    confidence_breakdown_json = table.Column<string>(type: "jsonb", nullable: false),
                    importance_breakdown_json = table.Column<string>(type: "jsonb", nullable: false),
                    source_json = table.Column<string>(type: "jsonb", nullable: true),
                    business_relevance_details_json = table.Column<string>(type: "jsonb", nullable: true),
                    priority_details_json = table.Column<string>(type: "jsonb", nullable: true),
                    ranking_details_json = table.Column<string>(type: "jsonb", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_insights", x => new { x.analysis_id, x.id });
                    table.ForeignKey(
                        name: "FK_insights_analyses_analysis_id",
                        column: x => x.analysis_id,
                        principalTable: "analyses",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateTable(
                name: "evidence",
                columns: table => new
                {
                    analysis_id = table.Column<Guid>(type: "uuid", nullable: false),
                    insight_id = table.Column<string>(type: "character varying(512)", maxLength: 512, nullable: false),
                    ordinal = table.Column<int>(type: "integer", nullable: false),
                    code = table.Column<string>(type: "character varying(128)", maxLength: 128, nullable: false),
                    label = table.Column<string>(type: "character varying(512)", maxLength: 512, nullable: false),
                    value_json = table.Column<string>(type: "jsonb", nullable: false),
                    unit = table.Column<string>(type: "character varying(64)", maxLength: 64, nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_evidence", x => new { x.analysis_id, x.insight_id, x.ordinal });
                    table.ForeignKey(
                        name: "FK_evidence_insights_analysis_id_insight_id",
                        columns: x => new { x.analysis_id, x.insight_id },
                        principalTable: "insights",
                        principalColumns: new[] { "analysis_id", "id" },
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateTable(
                name: "insight_clusters",
                columns: table => new
                {
                    id = table.Column<string>(type: "character varying(512)", maxLength: 512, nullable: false),
                    analysis_id = table.Column<Guid>(type: "uuid", nullable: false),
                    anchor_insight_id = table.Column<string>(type: "character varying(512)", maxLength: 512, nullable: false),
                    member_insight_ids_json = table.Column<string>(type: "jsonb", nullable: false),
                    relationship_ids_json = table.Column<string>(type: "jsonb", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_insight_clusters", x => new { x.analysis_id, x.id });
                    table.ForeignKey(
                        name: "FK_insight_clusters_insights_analysis_id_anchor_insight_id",
                        columns: x => new { x.analysis_id, x.anchor_insight_id },
                        principalTable: "insights",
                        principalColumns: new[] { "analysis_id", "id" },
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateTable(
                name: "insight_integrity_evaluations",
                columns: table => new
                {
                    analysis_id = table.Column<Guid>(type: "uuid", nullable: false),
                    insight_id = table.Column<string>(type: "character varying(512)", maxLength: 512, nullable: false),
                    status = table.Column<string>(type: "character varying(64)", maxLength: 64, nullable: false),
                    integrity_score = table.Column<double>(type: "double precision", nullable: true),
                    story_eligible = table.Column<bool>(type: "boolean", nullable: false),
                    requires_qualification = table.Column<bool>(type: "boolean", nullable: false),
                    counter_evidence_json = table.Column<string>(type: "jsonb", nullable: false),
                    contradictions_json = table.Column<string>(type: "jsonb", nullable: false),
                    outlier_check_json = table.Column<string>(type: "jsonb", nullable: true),
                    one_off_check_json = table.Column<string>(type: "jsonb", nullable: true),
                    consistency_checks_json = table.Column<string>(type: "jsonb", nullable: false),
                    integrity_breakdown_json = table.Column<string>(type: "jsonb", nullable: false),
                    reasons_json = table.Column<string>(type: "jsonb", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_insight_integrity_evaluations", x => new { x.analysis_id, x.insight_id });
                    table.ForeignKey(
                        name: "FK_insight_integrity_evaluations_insights_analysis_id_insight_~",
                        columns: x => new { x.analysis_id, x.insight_id },
                        principalTable: "insights",
                        principalColumns: new[] { "analysis_id", "id" },
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateTable(
                name: "missing_context_evaluations",
                columns: table => new
                {
                    analysis_id = table.Column<Guid>(type: "uuid", nullable: false),
                    insight_id = table.Column<string>(type: "character varying(512)", maxLength: 512, nullable: false),
                    interpretation_limited = table.Column<bool>(type: "boolean", nullable: false),
                    missing_context_json = table.Column<string>(type: "jsonb", nullable: false),
                    reasons_json = table.Column<string>(type: "jsonb", nullable: false),
                    context_summary_json = table.Column<string>(type: "jsonb", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_missing_context_evaluations", x => new { x.analysis_id, x.insight_id });
                    table.ForeignKey(
                        name: "FK_missing_context_evaluations_insights_analysis_id_insight_id",
                        columns: x => new { x.analysis_id, x.insight_id },
                        principalTable: "insights",
                        principalColumns: new[] { "analysis_id", "id" },
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateTable(
                name: "relationships",
                columns: table => new
                {
                    id = table.Column<string>(type: "character varying(512)", maxLength: 512, nullable: false),
                    analysis_id = table.Column<Guid>(type: "uuid", nullable: false),
                    source_insight_id = table.Column<string>(type: "character varying(512)", maxLength: 512, nullable: false),
                    target_insight_id = table.Column<string>(type: "character varying(512)", maxLength: 512, nullable: false),
                    type = table.Column<string>(type: "character varying(64)", maxLength: 64, nullable: false),
                    strength = table.Column<double>(type: "double precision", nullable: false),
                    confidence = table.Column<double>(type: "double precision", nullable: false),
                    strength_breakdown_json = table.Column<string>(type: "jsonb", nullable: false),
                    confidence_breakdown_json = table.Column<string>(type: "jsonb", nullable: false),
                    reasons_json = table.Column<string>(type: "jsonb", nullable: false),
                    metadata_json = table.Column<string>(type: "jsonb", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_relationships", x => new { x.analysis_id, x.id });
                    table.ForeignKey(
                        name: "FK_relationships_analyses_analysis_id",
                        column: x => x.analysis_id,
                        principalTable: "analyses",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Cascade);
                    table.ForeignKey(
                        name: "FK_relationships_insights_analysis_id_source_insight_id",
                        columns: x => new { x.analysis_id, x.source_insight_id },
                        principalTable: "insights",
                        principalColumns: new[] { "analysis_id", "id" },
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "FK_relationships_insights_analysis_id_target_insight_id",
                        columns: x => new { x.analysis_id, x.target_insight_id },
                        principalTable: "insights",
                        principalColumns: new[] { "analysis_id", "id" },
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "causality_evaluations",
                columns: table => new
                {
                    analysis_id = table.Column<Guid>(type: "uuid", nullable: false),
                    relationship_id = table.Column<string>(type: "character varying(512)", maxLength: 512, nullable: false),
                    source_insight_id = table.Column<string>(type: "character varying(512)", maxLength: 512, nullable: false),
                    target_insight_id = table.Column<string>(type: "character varying(512)", maxLength: 512, nullable: false),
                    source_metric = table.Column<string>(type: "character varying(128)", maxLength: 128, nullable: false),
                    target_metric = table.Column<string>(type: "character varying(128)", maxLength: 128, nullable: false),
                    status = table.Column<string>(type: "character varying(64)", maxLength: 64, nullable: false),
                    association_present = table.Column<bool>(type: "boolean", nullable: false),
                    causality_established = table.Column<bool>(type: "boolean", nullable: false),
                    causal_evidence_json = table.Column<string>(type: "jsonb", nullable: false),
                    allowed_concepts_json = table.Column<string>(type: "jsonb", nullable: false),
                    forbidden_concepts_json = table.Column<string>(type: "jsonb", nullable: false),
                    reasons_json = table.Column<string>(type: "jsonb", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_causality_evaluations", x => new { x.analysis_id, x.relationship_id });
                    table.ForeignKey(
                        name: "FK_causality_evaluations_relationships_analysis_id_relationshi~",
                        columns: x => new { x.analysis_id, x.relationship_id },
                        principalTable: "relationships",
                        principalColumns: new[] { "analysis_id", "id" },
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateIndex(
                name: "IX_analysis_profiles_analysis_id",
                table: "analysis_profiles",
                column: "analysis_id",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_insight_clusters_analysis_id_anchor_insight_id",
                table: "insight_clusters",
                columns: new[] { "analysis_id", "anchor_insight_id" });

            migrationBuilder.CreateIndex(
                name: "IX_relationships_analysis_id_source_insight_id",
                table: "relationships",
                columns: new[] { "analysis_id", "source_insight_id" });

            migrationBuilder.CreateIndex(
                name: "IX_relationships_analysis_id_target_insight_id",
                table: "relationships",
                columns: new[] { "analysis_id", "target_insight_id" });
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "analysis_profiles");

            migrationBuilder.DropTable(
                name: "causality_evaluations");

            migrationBuilder.DropTable(
                name: "evidence");

            migrationBuilder.DropTable(
                name: "insight_clusters");

            migrationBuilder.DropTable(
                name: "insight_integrity_evaluations");

            migrationBuilder.DropTable(
                name: "missing_context_evaluations");

            migrationBuilder.DropTable(
                name: "relationships");

            migrationBuilder.DropTable(
                name: "insights");

            migrationBuilder.DropTable(
                name: "analyses");
        }
    }
}
