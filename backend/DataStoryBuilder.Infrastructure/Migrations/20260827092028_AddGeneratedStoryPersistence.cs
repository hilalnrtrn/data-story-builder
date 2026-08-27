using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace DataStoryBuilder.Infrastructure.Migrations
{
    /// <inheritdoc />
    public partial class AddGeneratedStoryPersistence : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<DateTimeOffset>(
                name: "generated_at",
                table: "stories",
                type: "timestamp with time zone",
                nullable: true);

            migrationBuilder.AddColumn<string>(
                name: "generated_story_json",
                table: "stories",
                type: "jsonb",
                nullable: true);

            migrationBuilder.AddColumn<string>(
                name: "generation_failure_reason",
                table: "stories",
                type: "character varying(1000)",
                maxLength: 1000,
                nullable: true);

            migrationBuilder.AddColumn<string>(
                name: "generation_status",
                table: "stories",
                type: "character varying(16)",
                maxLength: 16,
                nullable: true);

            migrationBuilder.AddColumn<string>(
                name: "model_identifier",
                table: "stories",
                type: "character varying(128)",
                maxLength: 128,
                nullable: true);

            migrationBuilder.AddColumn<string>(
                name: "prompt_version",
                table: "stories",
                type: "character varying(64)",
                maxLength: 64,
                nullable: true);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropColumn(
                name: "generated_at",
                table: "stories");

            migrationBuilder.DropColumn(
                name: "generated_story_json",
                table: "stories");

            migrationBuilder.DropColumn(
                name: "generation_failure_reason",
                table: "stories");

            migrationBuilder.DropColumn(
                name: "generation_status",
                table: "stories");

            migrationBuilder.DropColumn(
                name: "model_identifier",
                table: "stories");

            migrationBuilder.DropColumn(
                name: "prompt_version",
                table: "stories");
        }
    }
}
