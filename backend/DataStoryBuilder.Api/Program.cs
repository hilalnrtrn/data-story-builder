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

app.MapPost("/api/analyses", async (
    HttpRequest request,
    IHttpClientFactory httpClientFactory) =>
{
    const long maxFileSize = 10 * 1024 * 1024;

    if (!request.HasFormContentType)
    {
        return Results.BadRequest(new
        {
            error = "A multipart form with a file is required."
        });
    }

    var form = await request.ReadFormAsync();
    var file = form.Files.GetFile("file");

    if (file is null)
    {
        return Results.BadRequest(new
        {
            error = "A file is required."
        });
    }

    if (file.Length == 0)
    {
        return Results.BadRequest(new
        {
            error = "The uploaded file is empty."
        });
    }

    if (file.Length > maxFileSize)
    {
        return Results.BadRequest(new
        {
            error = "The uploaded file exceeds the 10 MB limit."
        });
    }

    var extension =
        Path.GetExtension(file.FileName).ToLowerInvariant();

    if (extension is not ".csv" and not ".xlsx")
    {
        return Results.BadRequest(new
        {
            error = "Unsupported file type. Only CSV and XLSX files are supported."
        });
    }

    var analysisId = Guid.NewGuid();

    var client =
        httpClientFactory.CreateClient("AnalyticsService");

    using var multipartContent =
        new MultipartFormDataContent();

    multipartContent.Add(
        new StringContent(analysisId.ToString()),
        "analysis_id");

    await using var fileStream = file.OpenReadStream();

    using var fileContent =
        new StreamContent(fileStream);

    if (!string.IsNullOrWhiteSpace(file.ContentType))
    {
        fileContent.Headers.ContentType =
            new System.Net.Http.Headers.MediaTypeHeaderValue(
                file.ContentType);
    }

    multipartContent.Add(
        fileContent,
        "file",
        file.FileName);

    HttpResponseMessage analyticsResponse;

    try
    {
        analyticsResponse = await client.PostAsync(
            "/datasets/prepare",
            multipartContent);
    }
    catch (HttpRequestException)
    {
        return Results.Problem(
            detail: "Analytics service is unavailable.",
            statusCode: StatusCodes.Status503ServiceUnavailable);
    }

    var responseBody =
        await analyticsResponse.Content.ReadAsStringAsync();

    if (!analyticsResponse.IsSuccessStatusCode)
    {
        return Results.Content(
            responseBody,
            contentType: "application/json",
            statusCode: (int)analyticsResponse.StatusCode);
    }

    return Results.Content(
        responseBody,
        contentType: "application/json",
        statusCode: StatusCodes.Status200OK);
})
.DisableAntiforgery()
.Accepts<AnalysisUploadRequest>("multipart/form-data")
.WithName("CreateAnalysis")
.WithOpenApi();

app.Run();

public sealed class AnalysisUploadRequest
{
    public IFormFile File { get; set; } = default!;
}