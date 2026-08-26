using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace DataStoryBuilder.Infrastructure.Migrations
{
    /// <inheritdoc />
    public partial class AddStructuredStoryPlan : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "stories",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false),
                    analysis_id = table.Column<Guid>(type: "uuid", nullable: false),
                    planner_version = table.Column<string>(type: "character varying(64)", maxLength: 64, nullable: false),
                    story_plan_json = table.Column<string>(type: "jsonb", nullable: false),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_stories", x => x.id);
                    table.ForeignKey(
                        name: "FK_stories_analyses_analysis_id",
                        column: x => x.analysis_id,
                        principalTable: "analyses",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateIndex(
                name: "IX_stories_analysis_id",
                table: "stories",
                column: "analysis_id",
                unique: true);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "stories");
        }
    }
}
