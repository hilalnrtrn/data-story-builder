using System.Net;
using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text.Json;
using DataStoryBuilder.Application.Stories;
using Microsoft.Extensions.Options;

namespace DataStoryBuilder.Infrastructure.Generation;

public sealed class OpenAiLlmClient : ILlmClient
{
    private readonly HttpClient httpClient;
    private readonly LlmOptions options;

    public OpenAiLlmClient(HttpClient httpClient, IOptions<LlmOptions> options)
        : this(httpClient, options.Value)
    {
    }

    public OpenAiLlmClient(HttpClient httpClient, LlmOptions options)
    {
        this.httpClient = httpClient;
        this.options = options;
        this.options.Validate();
        this.httpClient.BaseAddress ??= new Uri("https://api.openai.com/v1/");
        this.httpClient.Timeout = TimeSpan.FromSeconds(this.options.TimeoutSeconds);
        this.httpClient.DefaultRequestHeaders.Authorization =
            new AuthenticationHeaderValue("Bearer", this.options.ApiKey);
    }

    public async Task<string> GenerateStructuredAsync(
        string groundedPrompt,
        string jsonSchema,
        CancellationToken cancellationToken = default)
    {
        if (string.IsNullOrWhiteSpace(groundedPrompt))
        {
            throw new ArgumentException("Grounded prompt is required.", nameof(groundedPrompt));
        }

        JsonElement schema;
        try
        {
            using var schemaDocument = JsonDocument.Parse(jsonSchema);
            schema = schemaDocument.RootElement.Clone();
        }
        catch (JsonException exception)
        {
            throw InvalidResponse("Structured-output schema is invalid.", exception);
        }

        using var request = new HttpRequestMessage(HttpMethod.Post, "responses")
        {
            Content = JsonContent.Create(new
            {
                model = options.Model,
                input = groundedPrompt,
                store = false,
                text = new
                {
                    format = new
                    {
                        type = "json_schema",
                        name = "generated_executive_story",
                        strict = true,
                        schema
                    }
                }
            })
        };

        HttpResponseMessage response;
        try
        {
            response = await httpClient.SendAsync(request, cancellationToken);
        }
        catch (OperationCanceledException) when (!cancellationToken.IsCancellationRequested)
        {
            throw new LlmClientException(LlmClientError.Timeout, "The LLM request timed out.");
        }
        catch (HttpRequestException exception)
        {
            throw new LlmClientException(
                LlmClientError.ProviderUnavailable,
                "The LLM provider is unavailable.",
                exception);
        }

        using (response)
        {
            if (response.StatusCode == HttpStatusCode.TooManyRequests)
            {
                throw new LlmClientException(LlmClientError.RateLimited, "The LLM provider rate limit was reached.");
            }
            if (response.StatusCode == HttpStatusCode.RequestTimeout
                || (int)response.StatusCode >= 500)
            {
                throw new LlmClientException(LlmClientError.ProviderUnavailable, "The LLM provider is unavailable.");
            }
            if (!response.IsSuccessStatusCode)
            {
                throw InvalidResponse("The LLM provider rejected the request.");
            }

            try
            {
                using var document = JsonDocument.Parse(
                    await response.Content.ReadAsStreamAsync(cancellationToken));
                return ExtractOutput(document.RootElement);
            }
            catch (JsonException exception)
            {
                throw InvalidResponse("The LLM provider response was malformed.", exception);
            }
        }
    }

    private static string ExtractOutput(JsonElement root)
    {
        if (root.ValueKind != JsonValueKind.Object
            || !root.TryGetProperty("status", out var status)
            || status.GetString() != "completed"
            || root.TryGetProperty("error", out var error) && error.ValueKind != JsonValueKind.Null
            || !root.TryGetProperty("output", out var output)
            || output.ValueKind != JsonValueKind.Array)
        {
            throw InvalidResponse("The LLM provider did not return a completed response.");
        }

        foreach (var outputItem in output.EnumerateArray())
        {
            if (!outputItem.TryGetProperty("content", out var content)
                || content.ValueKind != JsonValueKind.Array)
            {
                continue;
            }
            foreach (var contentItem in content.EnumerateArray())
            {
                if (contentItem.TryGetProperty("type", out var type)
                    && type.GetString() == "refusal")
                {
                    throw InvalidResponse("The LLM provider refused the request.");
                }
                if (type.GetString() == "output_text"
                    && contentItem.TryGetProperty("text", out var text)
                    && !string.IsNullOrWhiteSpace(text.GetString()))
                {
                    return text.GetString()!;
                }
            }
        }

        throw InvalidResponse("The LLM provider returned no structured output.");
    }

    private static LlmClientException InvalidResponse(
        string message,
        Exception? innerException = null) =>
        new(LlmClientError.InvalidProviderResponse, message, innerException);
}
