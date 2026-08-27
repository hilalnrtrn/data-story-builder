using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace DataStoryBuilder.Infrastructure.Migrations
{
    /// <inheritdoc />
    public partial class AddFullStoryAuditPersistence : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<string>(
                name: "full_story_audit_json",
                table: "stories",
                type: "jsonb",
                nullable: true);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropColumn(
                name: "full_story_audit_json",
                table: "stories");
        }
    }
}
