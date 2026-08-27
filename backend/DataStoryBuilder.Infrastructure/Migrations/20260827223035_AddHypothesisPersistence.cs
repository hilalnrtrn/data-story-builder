using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace DataStoryBuilder.Infrastructure.Migrations
{
    /// <inheritdoc />
    public partial class AddHypothesisPersistence : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "hypotheses",
                columns: table => new
                {
                    id = table.Column<string>(type: "character varying(128)", maxLength: 128, nullable: false),
                    analysis_id = table.Column<Guid>(type: "uuid", nullable: false),
                    statement = table.Column<string>(type: "character varying(2000)", maxLength: 2000, nullable: false),
                    status = table.Column<string>(type: "character varying(32)", maxLength: 32, nullable: false),
                    confidence = table.Column<double>(type: "double precision", nullable: false),
                    causality_status = table.Column<string>(type: "character varying(64)", maxLength: 64, nullable: false),
                    tracker_version = table.Column<string>(type: "character varying(64)", maxLength: 64, nullable: false),
                    source_insight_ids_json = table.Column<string>(type: "jsonb", nullable: false),
                    source_relationship_ids_json = table.Column<string>(type: "jsonb", nullable: false),
                    supporting_evidence_json = table.Column<string>(type: "jsonb", nullable: false),
                    counter_evidence_json = table.Column<string>(type: "jsonb", nullable: false),
                    missing_context_json = table.Column<string>(type: "jsonb", nullable: false),
                    reasons_json = table.Column<string>(type: "jsonb", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_hypotheses", x => new { x.analysis_id, x.id });
                    table.ForeignKey(
                        name: "FK_hypotheses_analyses_analysis_id",
                        column: x => x.analysis_id,
                        principalTable: "analyses",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Cascade);
                });
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "hypotheses");
        }
    }
}
