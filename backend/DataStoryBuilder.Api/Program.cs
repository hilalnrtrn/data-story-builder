using DataStoryBuilder.Infrastructure.Persistence;
using DataStoryBuilder.Application.Stories;
using DataStoryBuilder.Application.Hypotheses;
using DataStoryBuilder.Api;
using DataStoryBuilder.Infrastructure.Generation;
using Microsoft.EntityFrameworkCore;
using Npgsql;

var builder = WebApplication.CreateBuilder(args);

var baseConnectionString =
    builder.Configuration.GetConnectionString("PostgreSql");

var password =
    builder.Configuration["ConnectionStrings:PostgreSqlPassword"];

var connectionString =
    $"{baseConnectionString};Password={password}";

builder.Services.AddDbContext<DataStoryBuilderDbContext>(options =>
    options.UseNpgsql(connectionString));
builder.Services.AddScoped<AnalysisLifecyclePersistence>();
builder.Services.AddScoped<AnalysisProfilePersistence>();
builder.Services.AddScoped<InsightPersistence>();
builder.Services.AddScoped<RelationshipRankingPersistence>();
builder.Services.AddScoped<IntegrityContextPersistence>();
builder.Services.AddScoped<AnalysisHistoryPersistence>();
builder.Services.AddScoped<AnalysisDetailPersistence>();
builder.Services.AddScoped<StoryPlanPersistence>();
builder.Services.AddScoped<StoryGenerationPersistence>();
builder.Services.AddScoped<HypothesisPersistence>();
builder.Services.AddScoped<HypothesisLifecyclePersistence>();
builder.Services.Configure<LlmOptions>(
    builder.Configuration.GetSection(LlmOptions.SectionName));
builder.Services.AddHttpClient<ILlmClient, GroqLlmClient>();
builder.Services.AddScoped<GroundedPromptBuilder>();
builder.Services.AddScoped<GeneratedStorySafetyValidator>();
builder.Services.AddScoped<StoryGenerator>();
builder.Services.AddScoped<AnalysisStoryGeneration>();

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
    IHttpClientFactory httpClientFactory) =>
{
    var databaseStatus = "unhealthy";
    var analyticsStatus = "unhealthy";

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

app.MapGet("/api/analyses", async (
    AnalysisHistoryPersistence analysisHistoryPersistence,
    CancellationToken cancellationToken) =>
{
    var analyses = await analysisHistoryPersistence.GetAsync(
        cancellationToken);

    return Results.Ok(analyses);
})
.WithName("GetAnalyses")
.WithOpenApi();

app.MapGet("/api/analyses/{id:guid}", async (
    Guid id,
    AnalysisDetailPersistence analysisDetailPersistence,
    CancellationToken cancellationToken) =>
{
    var analysis = await analysisDetailPersistence.GetAsync(
        id,
        cancellationToken);

    return analysis is null
        ? Results.NotFound()
        : Results.Ok(analysis);
})
.WithName("GetAnalysis")
.WithOpenApi();

app.MapGet("/api/analyses/{analysisId:guid}/hypotheses", async (
    Guid analysisId,
    HypothesisLifecyclePersistence hypothesisLifecyclePersistence,
    CancellationToken cancellationToken) =>
{
    var hypotheses = await hypothesisLifecyclePersistence.GetAsync(
        analysisId,
        cancellationToken);

    return hypotheses is null
        ? Results.NotFound()
        : Results.Ok(hypotheses);
})
.WithName("GetAnalysisHypotheses")
.WithOpenApi();

app.MapPatch(
    "/api/analyses/{analysisId:guid}/hypotheses/{hypothesisId}/status",
    async (
        Guid analysisId,
        string hypothesisId,
        HypothesisStatusUpdateRequest request,
        HypothesisLifecyclePersistence hypothesisLifecyclePersistence,
        CancellationToken cancellationToken) =>
    {
        if (!HypothesisStatusTransitions.TryParse(
                request.Status,
                out var targetStatus))
        {
            return Results.BadRequest(new
            {
                error = "The target hypothesis status is invalid."
            });
        }

        var result = await hypothesisLifecyclePersistence.UpdateStatusAsync(
            analysisId,
            hypothesisId,
            targetStatus,
            cancellationToken);

        return result.Outcome switch
        {
            HypothesisStatusUpdateOutcome.Updated =>
                Results.Ok(result.Hypothesis),
            HypothesisStatusUpdateOutcome.AnalysisNotFound =>
                Results.NotFound(),
            HypothesisStatusUpdateOutcome.HypothesisNotFound =>
                Results.NotFound(),
            HypothesisStatusUpdateOutcome.InvalidTransition =>
                Results.BadRequest(new
                {
                    error = "The requested hypothesis status transition is invalid."
                }),
            _ => throw new InvalidOperationException(
                "Unknown hypothesis status update outcome.")
        };
    })
.WithName("UpdateHypothesisStatus")
.WithOpenApi();

app.MapPost("/api/analyses", async (
    HttpRequest request,
    IHttpClientFactory httpClientFactory,
    AnalysisLifecyclePersistence analysisLifecyclePersistence,
    AnalysisProfilePersistence analysisProfilePersistence,
    InsightPersistence insightPersistence,
    RelationshipRankingPersistence relationshipRankingPersistence,
    IntegrityContextPersistence integrityContextPersistence,
    StoryPlanPersistence storyPlanPersistence,
    HypothesisPersistence hypothesisPersistence,
    StoryGenerationPersistence storyGenerationPersistence,
    AnalysisStoryGeneration storyGeneration,
    ILoggerFactory loggerFactory,
    DataStoryBuilderDbContext dbContext) =>
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
    var requestedLanguage = form["language"].FirstOrDefault();

    if (!StoryGenerationLanguage.TryNormalize(
            requestedLanguage,
            out var generationLanguage))
    {
        return Results.BadRequest(new
        {
            error = "Language must be 'en' or 'tr'."
        });
    }

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
    var cancellationToken = request.HttpContext.RequestAborted;
    var analyticsCompleted = false;
    var postCompletionStage = "analytics";
    var generationLogger = loggerFactory.CreateLogger(
        "DataStoryBuilder.StoryGeneration");

    try
    {
        await analysisLifecyclePersistence.CreateProcessingAsync(
            analysisId,
            file.FileName,
            extension.TrimStart('.'),
            cancellationToken);
    }
    catch
    {
        return Results.Problem(
            detail: "The analysis lifecycle could not be created.",
            statusCode: StatusCodes.Status500InternalServerError);
    }

    try
    {
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
            try
            {
                await analysisLifecyclePersistence.MarkFailedAsync(
                    analysisId,
                    "Analytics service was unavailable.",
                    cancellationToken);
            }
            catch
            {
            }

            return Results.Problem(
                detail: "Analytics service is unavailable.",
                statusCode: StatusCodes.Status503ServiceUnavailable);
        }

        var responseBody =
            await analyticsResponse.Content.ReadAsStringAsync();

        if (!analyticsResponse.IsSuccessStatusCode)
        {
            try
            {
                await analysisLifecyclePersistence.MarkFailedAsync(
                    analysisId,
                    $"Analytics service returned HTTP {(int)analyticsResponse.StatusCode}.",
                    cancellationToken);
            }
            catch
            {
            }

            return Results.Content(
                responseBody,
                contentType: "application/json",
                statusCode: (int)analyticsResponse.StatusCode);
        }

        {
            await using var resultTransaction =
                await dbContext.Database.BeginTransactionAsync(
                    cancellationToken);

            try
            {
                await analysisProfilePersistence.PersistAsync(
                    analysisId,
                    responseBody,
                    cancellationToken);

                await insightPersistence.PersistAsync(
                    analysisId,
                    responseBody,
                    cancellationToken);

                await relationshipRankingPersistence.PersistAsync(
                    analysisId,
                    responseBody,
                    cancellationToken);

                await integrityContextPersistence.PersistAsync(
                    analysisId,
                    responseBody,
                    cancellationToken);

                await storyPlanPersistence.PersistAsync(
                    analysisId,
                    responseBody,
                    cancellationToken);

                await hypothesisPersistence.PersistAsync(
                    analysisId,
                    responseBody,
                    cancellationToken);

                await analysisLifecyclePersistence.MarkCompletedAsync(
                    analysisId,
                    cancellationToken);

                await resultTransaction.CommitAsync(cancellationToken);
                analyticsCompleted = true;
            }
            catch
            {
                try
                {
                    await resultTransaction.RollbackAsync(
                        CancellationToken.None);
                }
                catch
                {
                }

                dbContext.ChangeTracker.Clear();
                throw;
            }
        }

        postCompletionStage = "story-generation";
        AnalysisStoryGenerationResult generatedStoryResult;
        try
        {
            generatedStoryResult =
                await storyGeneration.GenerateAndComposeAsync(
                    responseBody,
                    generationLanguage,
                    cancellationToken);
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
        {
            throw;
        }
        catch (Exception exception)
        {
            generationLogger.LogError(
                "Post-completion stage {Stage} failed for analysis {AnalysisId} with exception type {ExceptionType}.",
                postCompletionStage,
                analysisId,
                exception.GetType().Name);
            throw;
        }

        postCompletionStage = "story-persistence";
        try
        {
            await using var storyTransaction =
                await dbContext.Database.BeginTransactionAsync(
                    cancellationToken);

            try
            {
                await storyGenerationPersistence.PersistAsync(
                    analysisId,
                    generatedStoryResult.Generation,
                    generatedStoryResult.StoryAudit,
                    generatedStoryResult.FullStoryAudit,
                    generatedStoryResult.PromptVersion,
                    generatedStoryResult.ModelIdentifier,
                    generatedStoryResult.GeneratedAt,
                    generatedStoryResult.GenerationLanguage,
                    cancellationToken);

                await storyTransaction.CommitAsync(cancellationToken);
            }
            catch
            {
                try
                {
                    await storyTransaction.RollbackAsync(CancellationToken.None);
                }
                catch
                {
                }

                throw;
            }
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
        {
            dbContext.ChangeTracker.Clear();
            throw;
        }
        catch (Exception exception)
        {
            generationLogger.LogError(
                "Post-completion stage {Stage} failed for analysis {AnalysisId} with exception type {ExceptionType}.",
                postCompletionStage,
                analysisId,
                exception.GetType().Name);
            dbContext.ChangeTracker.Clear();
            return Results.Problem(
                detail: "The analysis completed, but its generated story result could not be persisted.",
                statusCode: StatusCodes.Status500InternalServerError,
                extensions: new Dictionary<string, object?>
                {
                    ["analysisId"] = analysisId
                });
        }

        return Results.Content(
            generatedStoryResult.ResponseJson,
            contentType: "application/json",
            statusCode: StatusCodes.Status200OK);
    }
    catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
    {
        throw;
    }
    catch
    {
        if (!analyticsCompleted)
        {
            try
            {
                await analysisLifecyclePersistence.MarkFailedAsync(
                    analysisId,
                    "Unexpected failure while processing the analysis.",
                    cancellationToken);
            }
            catch
            {
            }
        }

        return Results.Problem(
            detail: "The analysis could not be completed.",
            statusCode: StatusCodes.Status500InternalServerError);
    }
})
.DisableAntiforgery()
.Accepts<AnalysisUploadRequest>("multipart/form-data")
.WithName("CreateAnalysis")
.WithOpenApi();

app.Run();

public sealed class AnalysisUploadRequest
{
    public IFormFile File { get; set; } = default!;
    public string? Language { get; set; }
}

public sealed record HypothesisStatusUpdateRequest(string? Status);
