using System.Net;
using System.Text;
using System.Text.Json;
using DataStoryBuilder.Application.Stories;
using DataStoryBuilder.Infrastructure.Generation;
using Xunit;

namespace DataStoryBuilder.Application.Tests.Stories;

public sealed class GroqLlmClientTests
{
    private const string TestApiKey = "test-only-secret-value";

    [Fact]
    public async Task RequestUsesGroqResponsesEndpointAndStrictSchema()
    {
        HttpRequestMessage? captured = null;
        string? body = null;
        var handler = new StubHandler(async request =>
        {
            captured = request;
            body = await request.Content!.ReadAsStringAsync();
            return Completed("{\"title\":\"Story\"}");
        });

        await CreateClient(handler).GenerateStructuredAsync(
            "grounded prompt",
            GeneratedExecutiveStorySchema.Build());

        Assert.Equal(HttpMethod.Post, captured!.Method);
        Assert.Equal(
            "https://api.groq.com/openai/v1/responses",
            captured.RequestUri!.ToString());
        Assert.Equal("Bearer", captured.Headers.Authorization!.Scheme);
        Assert.Equal(TestApiKey, captured.Headers.Authorization.Parameter);
        using var document = JsonDocument.Parse(body!);
        var root = document.RootElement;
        Assert.Equal("openai/gpt-oss-120b", root.GetProperty("model").GetString());
        Assert.Equal("grounded prompt", root.GetProperty("input").GetString());
        Assert.False(root.TryGetProperty("store", out _));
        var format = root.GetProperty("text").GetProperty("format");
        Assert.Equal("json_schema", format.GetProperty("type").GetString());
        Assert.Equal("generated_executive_story", format.GetProperty("name").GetString());
        Assert.True(format.GetProperty("strict").GetBoolean());
        Assert.Equal(
            "object",
            format.GetProperty("schema").GetProperty("type").GetString());
    }

    [Fact]
    public async Task CompletedResponseReturnsStructuredOutputText()
    {
        var client = CreateClient(new StubHandler(_ => Task.FromResult(
            Completed("{\"title\":\"Story\"}"))));
        Assert.Equal(
            "{\"title\":\"Story\"}",
            await client.GenerateStructuredAsync(
                "prompt",
                GeneratedExecutiveStorySchema.Build()));
    }

    [Theory]
    [InlineData(HttpStatusCode.TooManyRequests, LlmClientError.RateLimited)]
    [InlineData(HttpStatusCode.RequestTimeout, LlmClientError.ProviderUnavailable)]
    [InlineData(HttpStatusCode.InternalServerError, LlmClientError.ProviderUnavailable)]
    [InlineData(HttpStatusCode.ServiceUnavailable, LlmClientError.ProviderUnavailable)]
    public async Task HttpFailuresMapWithoutRetry(
        HttpStatusCode status,
        LlmClientError expected)
    {
        var handler = new StubHandler(_ =>
            Task.FromResult(new HttpResponseMessage(status)));
        var error = await Assert.ThrowsAsync<LlmClientException>(() =>
            CreateClient(handler).GenerateStructuredAsync(
                "prompt",
                GeneratedExecutiveStorySchema.Build()));

        Assert.Equal(expected, error.Error);
        Assert.Equal(1, handler.CallCount);
        Assert.DoesNotContain(TestApiKey, error.ToString());
    }

    [Fact]
    public async Task ConnectionFailureMapsProviderUnavailable()
    {
        var handler = new StubHandler(_ => throw new HttpRequestException());
        var error = await Assert.ThrowsAsync<LlmClientException>(() =>
            CreateClient(handler).GenerateStructuredAsync(
                "prompt",
                GeneratedExecutiveStorySchema.Build()));
        Assert.Equal(LlmClientError.ProviderUnavailable, error.Error);
        Assert.Equal(1, handler.CallCount);
    }

    [Fact]
    public async Task ConfiguredTimeoutMapsTimeout()
    {
        var handler = new StubHandler(_ => throw new TaskCanceledException());
        var error = await Assert.ThrowsAsync<LlmClientException>(() =>
            CreateClient(handler).GenerateStructuredAsync(
                "prompt",
                GeneratedExecutiveStorySchema.Build()));
        Assert.Equal(LlmClientError.Timeout, error.Error);
        Assert.Equal(1, handler.CallCount);
    }

    [Fact]
    public async Task CallerCancellationPropagates()
    {
        using var cancellation = new CancellationTokenSource();
        cancellation.Cancel();
        var handler = new StubHandler(_ =>
            Task.FromCanceled<HttpResponseMessage>(cancellation.Token));

        await Assert.ThrowsAnyAsync<OperationCanceledException>(() =>
            CreateClient(handler).GenerateStructuredAsync(
                "prompt",
                GeneratedExecutiveStorySchema.Build(),
                cancellation.Token));
        Assert.Equal(1, handler.CallCount);
    }

    [Theory]
    [InlineData("not-json")]
    [InlineData("{}")]
    [InlineData("{\"status\":\"completed\",\"error\":null,\"output\":[]}")]
    [InlineData("{\"status\":\"completed\",\"error\":null,\"output\":[{\"content\":[{}]}]}")]
    [InlineData("{\"status\":\"completed\",\"error\":null,\"output\":[{\"content\":[{\"type\":\"output_text\",\"text\":\"\"}]}]}")]
    [InlineData("{\"status\":\"incomplete\",\"output\":[]}")]
    [InlineData("{\"status\":\"failed\",\"error\":{\"code\":\"server_error\"},\"output\":[]}")]
    public async Task InvalidEnvelopeMapsInvalidProviderResponse(string responseJson)
    {
        var handler = new StubHandler(_ =>
            Task.FromResult(JsonResponse(responseJson)));
        var error = await Assert.ThrowsAsync<LlmClientException>(() =>
            CreateClient(handler).GenerateStructuredAsync(
                "prompt",
                GeneratedExecutiveStorySchema.Build()));

        Assert.Equal(LlmClientError.InvalidProviderResponse, error.Error);
        Assert.Equal(1, handler.CallCount);
        Assert.DoesNotContain(responseJson, error.Message);
        Assert.DoesNotContain(TestApiKey, error.ToString());
    }

    [Fact]
    public async Task RefusalMapsInvalidProviderResponse()
    {
        const string response =
            "{\"status\":\"completed\",\"error\":null,\"output\":[{\"content\":[{\"type\":\"refusal\",\"refusal\":\"Cannot comply\"}]}]}";
        var handler = new StubHandler(_ => Task.FromResult(JsonResponse(response)));
        var error = await Assert.ThrowsAsync<LlmClientException>(() =>
            CreateClient(handler).GenerateStructuredAsync(
                "prompt",
                GeneratedExecutiveStorySchema.Build()));
        Assert.Equal(LlmClientError.InvalidProviderResponse, error.Error);
        Assert.Equal(1, handler.CallCount);
    }

    [Fact]
    public void OptionsAndClientDoNotExposeApiKey()
    {
        var options = OptionsFor();
        var client = CreateClient(new StubHandler(_ =>
            Task.FromResult(Completed("{}"))));
        Assert.DoesNotContain(TestApiKey, options.ToString());
        Assert.DoesNotContain(TestApiKey, client.ToString());
    }

    private static GroqLlmClient CreateClient(HttpMessageHandler handler) =>
        new(new HttpClient(handler), OptionsFor());

    private static LlmOptions OptionsFor() => new()
    {
        Model = "openai/gpt-oss-120b",
        ApiKey = TestApiKey,
        TimeoutSeconds = 60,
        PromptVersion = "day13-v1"
    };

    private static HttpResponseMessage Completed(string output) =>
        JsonResponse(
            $$"""{"status":"completed","error":null,"output":[{"type":"message","content":[{"type":"output_text","text":{{JsonSerializer.Serialize(output)}}}]}]}""");

    private static HttpResponseMessage JsonResponse(string json) =>
        new(HttpStatusCode.OK)
        {
            Content = new StringContent(json, Encoding.UTF8, "application/json")
        };

    private sealed class StubHandler(
        Func<HttpRequestMessage, Task<HttpResponseMessage>> responseFactory)
        : HttpMessageHandler
    {
        public int CallCount { get; private set; }

        protected override Task<HttpResponseMessage> SendAsync(
            HttpRequestMessage request,
            CancellationToken cancellationToken)
        {
            CallCount++;
            return responseFactory(request);
        }
    }
}
