using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace DataStoryBuilder.Infrastructure.Migrations
{
    /// <inheritdoc />
    public partial class AddStoryGenerationLanguage : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<string>(
                name: "generation_language",
                table: "stories",
                type: "character varying(2)",
                maxLength: 2,
                nullable: true);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropColumn(
                name: "generation_language",
                table: "stories");
        }
    }
}
