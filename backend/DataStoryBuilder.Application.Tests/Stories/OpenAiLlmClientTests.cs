using System.Net;
using System.Text;
using System.Text.Json;
using DataStoryBuilder.Application.Stories;
using DataStoryBuilder.Infrastructure.Generation;
using Xunit;

namespace DataStoryBuilder.Application.Tests.Stories;

public sealed class OpenAiLlmClientTests
{
    [Fact]
    public async Task RequestUsesResponsesEndpointPostAuthorizationModelPromptAndStrictSchema()
    {
        HttpRequestMessage? captured = null;
        string? body = null;
        var handler = new StubHandler(async request =>
        {
            captured = request;
            body = await request.Content!.ReadAsStringAsync();
            return Completed("{\"title\":\"Story\"}");
        });
        var client = CreateClient(handler);

        await client.GenerateStructuredAsync("grounded prompt", GeneratedExecutiveStorySchema.Build());

        Assert.Equal(HttpMethod.Post, captured!.Method);
        Assert.Equal("https://api.openai.com/v1/responses", captured.RequestUri!.ToString());
        Assert.Equal("Bearer", captured.Headers.Authorization!.Scheme);
        Assert.False(string.IsNullOrWhiteSpace(captured.Headers.Authorization.Parameter));
        using var document = JsonDocument.Parse(body!);
        var root = document.RootElement;
        Assert.Equal("approved-model", root.GetProperty("model").GetString());
        Assert.Equal("grounded prompt", root.GetProperty("input").GetString());
        var format = root.GetProperty("text").GetProperty("format");
        Assert.Equal("json_schema", format.GetProperty("type").GetString());
        Assert.True(format.GetProperty("strict").GetBoolean());
        Assert.Equal("object", format.GetProperty("schema").GetProperty("type").GetString());
    }

    [Fact]
    public async Task CompletedEnvelopeReturnsStructuredJson()
    {
        var client = CreateClient(new StubHandler(_ => Task.FromResult(
            Completed("{\"title\":\"Story\"}"))));
        Assert.Equal(
            "{\"title\":\"Story\"}",
            await client.GenerateStructuredAsync("prompt", GeneratedExecutiveStorySchema.Build()));
    }

    [Theory]
    [InlineData(HttpStatusCode.TooManyRequests, LlmClientError.RateLimited)]
    [InlineData(HttpStatusCode.InternalServerError, LlmClientError.ProviderUnavailable)]
    [InlineData(HttpStatusCode.ServiceUnavailable, LlmClientError.ProviderUnavailable)]
    [InlineData(HttpStatusCode.RequestTimeout, LlmClientError.ProviderUnavailable)]
    public async Task HttpFailuresAreMapped(HttpStatusCode status, LlmClientError expected)
    {
        var handler = new StubHandler(_ =>
            Task.FromResult(new HttpResponseMessage(status)));
        var client = CreateClient(handler);
        var error = await Assert.ThrowsAsync<LlmClientException>(() =>
            client.GenerateStructuredAsync("prompt", GeneratedExecutiveStorySchema.Build()));
        Assert.Equal(expected, error.Error);
        Assert.Equal(1, handler.CallCount);
    }

    [Fact]
    public async Task ConnectionFailureMapsProviderUnavailable()
    {
        var client = CreateClient(new StubHandler(_ => throw new HttpRequestException()));
        var error = await Assert.ThrowsAsync<LlmClientException>(() =>
            client.GenerateStructuredAsync("prompt", GeneratedExecutiveStorySchema.Build()));
        Assert.Equal(LlmClientError.ProviderUnavailable, error.Error);
    }

    [Fact]
    public async Task TimeoutMapsTimeout()
    {
        var client = CreateClient(new StubHandler(_ => throw new TaskCanceledException()));
        var error = await Assert.ThrowsAsync<LlmClientException>(() =>
            client.GenerateStructuredAsync("prompt", GeneratedExecutiveStorySchema.Build()));
        Assert.Equal(LlmClientError.Timeout, error.Error);
    }

    [Fact]
    public async Task CallerCancellationRemainsCancellation()
    {
        using var source = new CancellationTokenSource();
        source.Cancel();
        var client = CreateClient(new StubHandler(request =>
            Task.FromCanceled<HttpResponseMessage>(source.Token)));
        await Assert.ThrowsAnyAsync<OperationCanceledException>(() =>
            client.GenerateStructuredAsync("prompt", GeneratedExecutiveStorySchema.Build(), source.Token));
    }

    [Theory]
    [InlineData("not-json")]
    [InlineData("{\"status\":\"completed\",\"output\":[]}")]
    [InlineData("{\"status\":\"incomplete\",\"output\":[]}")]
    [InlineData("{\"status\":\"failed\",\"error\":{\"code\":\"server_error\"},\"output\":[]}")]
    public async Task InvalidProviderEnvelopeIsRejected(string responseJson)
    {
        var client = CreateClient(new StubHandler(_ => Task.FromResult(JsonResponse(responseJson))));
        var error = await Assert.ThrowsAsync<LlmClientException>(() =>
            client.GenerateStructuredAsync("prompt", GeneratedExecutiveStorySchema.Build()));
        Assert.Equal(LlmClientError.InvalidProviderResponse, error.Error);
    }

    [Fact]
    public async Task RefusalIsRejected()
    {
        var response = """{"status":"completed","error":null,"output":[{"content":[{"type":"refusal","refusal":"Cannot comply"}]}]}""";
        var client = CreateClient(new StubHandler(_ => Task.FromResult(JsonResponse(response))));
        var error = await Assert.ThrowsAsync<LlmClientException>(() =>
            client.GenerateStructuredAsync("prompt", GeneratedExecutiveStorySchema.Build()));
        Assert.Equal(LlmClientError.InvalidProviderResponse, error.Error);
    }

    [Fact]
    public void OptionsValidationRejectsInvalidValuesAndDoesNotExposeApiKey()
    {
        Assert.Throws<InvalidOperationException>(() => OptionsFor(model: " ").Validate());
        Assert.Throws<InvalidOperationException>(() => OptionsFor(apiKey: " ").Validate());
        Assert.Throws<InvalidOperationException>(() => OptionsFor(timeout: 0).Validate());
        Assert.Throws<InvalidOperationException>(() => OptionsFor(timeout: 301).Validate());
        Assert.Throws<InvalidOperationException>(() => OptionsFor(promptVersion: " ").Validate());
        Assert.DoesNotContain("test-secret-value", OptionsFor().ToString());
    }

    private static OpenAiLlmClient CreateClient(HttpMessageHandler handler) =>
        new(new HttpClient(handler), OptionsFor());

    private static LlmOptions OptionsFor(
        string model = "approved-model",
        string apiKey = "test-secret-value",
        int timeout = 60,
        string promptVersion = "day13-v1") =>
        new() { Model = model, ApiKey = apiKey, TimeoutSeconds = timeout, PromptVersion = promptVersion };

    private static HttpResponseMessage Completed(string output) =>
        JsonResponse($$"""{"status":"completed","error":null,"output":[{"type":"message","content":[{"type":"output_text","text":{{JsonSerializer.Serialize(output)}}}]}]}""");

    private static HttpResponseMessage JsonResponse(string json) =>
        new(HttpStatusCode.OK) { Content = new StringContent(json, Encoding.UTF8, "application/json") };

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
