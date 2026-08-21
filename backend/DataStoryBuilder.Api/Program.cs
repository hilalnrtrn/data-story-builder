using Npgsql;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddHttpClient("AnalyticsService", client =>
{
    var baseUrl = builder.Configuration["AnalyticsService:BaseUrl"];

    if (string.IsNullOrWhiteSpace(baseUrl))
    {
        throw new InvalidOperationException(
            "AnalyticsService:BaseUrl configuration is missing.");
    }

    client.BaseAddress = new Uri(baseUrl);
});

builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();

builder.Services.AddCors(options =>
{
    options.AddPolicy("Frontend", policy =>
    {
        policy
            .WithOrigins("http://localhost:5173")
            .AllowAnyHeader()
            .AllowAnyMethod();
    });
});

var app = builder.Build();

if (app.Environment.IsDevelopment())
{
    app.UseSwagger();
    app.UseSwaggerUI();
}

app.UseCors("Frontend");

app.UseHttpsRedirection();

app.MapGet("/api/health", async (
    IConfiguration configuration,
    IHttpClientFactory httpClientFactory) =>
{
    var databaseStatus = "unhealthy";
    var analyticsStatus = "unhealthy";

    var baseConnectionString =
        configuration.GetConnectionString("PostgreSql");

    var password =
        configuration["ConnectionStrings:PostgreSqlPassword"];

    var connectionString =
        $"{baseConnectionString};Password={password}";

    try
    {
        await using var connection =
            new NpgsqlConnection(connectionString);

        await connection.OpenAsync();
        databaseStatus = "healthy";
    }
    catch
    {
        databaseStatus = "unhealthy";
    }

    try
    {
        var client =
            httpClientFactory.CreateClient("AnalyticsService");

        var response =
            await client.GetAsync("/health");

        if (response.IsSuccessStatusCode)
        {
            analyticsStatus = "healthy";
        }
    }
    catch
    {
        analyticsStatus = "unhealthy";
    }

    var overallStatus =
        databaseStatus == "healthy" &&
        analyticsStatus == "healthy"
            ? "healthy"
            : "degraded";

    return Results.Ok(new
    {
        status = overallStatus,

        backend = new
        {
            status = "healthy"
        },

        analytics = new
        {
            status = analyticsStatus
        },

        database = new
        {
            status = databaseStatus
        }
    });
})
.WithName("GetHealth")
.WithOpenApi();

app.Run();