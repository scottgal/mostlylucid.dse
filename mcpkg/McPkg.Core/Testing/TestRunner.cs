using System.Diagnostics;
using System.Net.Http.Headers;
using System.Text.Json;
using System.Text.Json.Nodes;
using Json.Path;
using mostlylucid.mcpregistry.Core.Models;

namespace mostlylucid.mcpregistry.Core.Testing;

/// <summary>
/// Runs tests for MCPKG tools
/// </summary>
public class TestRunner
{
    private readonly HttpClient _httpClient;
    private readonly Dictionary<string, string> _environmentAuth;

    public TestRunner(HttpClient? httpClient = null, Dictionary<string, string>? environmentAuth = null)
    {
        _httpClient = httpClient ?? new HttpClient();
        _environmentAuth = environmentAuth ?? new Dictionary<string, string>();
    }

    /// <summary>
    /// Runs all tests for a tool
    /// </summary>
    public async Task<List<TestResult>> RunTestsAsync(
        Manifest manifest,
        List<TestCase> testCases,
        CancellationToken cancellationToken = default)
    {
        var results = new List<TestResult>();

        foreach (var testCase in testCases)
        {
            var result = await RunTestAsync(manifest, testCase, cancellationToken);
            results.Add(result);
        }

        return results;
    }

    /// <summary>
    /// Runs a single test case
    /// </summary>
    public async Task<TestResult> RunTestAsync(
        Manifest manifest,
        TestCase testCase,
        CancellationToken cancellationToken = default)
    {
        var stopwatch = Stopwatch.StartNew();
        var result = new TestResult
        {
            TestName = testCase.Name
        };

        try
        {
            // Execute the tool endpoint
            var response = await ExecuteToolAsync(manifest, testCase.Input, testCase.TimeoutMs, cancellationToken);

            result.ActualOutput = response;

            // Evaluate assertions
            result.AssertionResults = EvaluateAssertions(testCase.Assertions, response);

            // Check if all assertions passed
            result.Passed = result.AssertionResults.All(a => a.Passed);
        }
        catch (Exception ex)
        {
            result.Passed = false;
            result.ErrorMessage = ex.Message;
        }
        finally
        {
            stopwatch.Stop();
            result.DurationMs = stopwatch.ElapsedMilliseconds;
        }

        return result;
    }

    private async Task<JsonNode> ExecuteToolAsync(
        Manifest manifest,
        JsonNode input,
        int? testTimeout,
        CancellationToken cancellationToken)
    {
        var endpoint = manifest.Endpoint;
        var timeout = testTimeout ?? endpoint.TimeoutMs ?? 30000;

        using var cts = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        cts.CancelAfter(timeout);

        // Create HTTP request
        var request = new HttpRequestMessage
        {
            Method = new HttpMethod(endpoint.Method),
            RequestUri = new Uri(endpoint.Url),
            Content = new StringContent(
                input.ToJsonString(),
                System.Text.Encoding.UTF8,
                "application/json")
        };

        // Add authentication if configured
        if (manifest.Auth != null)
        {
            ApplyAuthentication(request, manifest.Auth);
        }

        // Execute request
        var response = await _httpClient.SendAsync(request, cts.Token);

        // Read response
        var responseContent = await response.Content.ReadAsStringAsync(cts.Token);

        // Parse as JSON
        if (string.IsNullOrWhiteSpace(responseContent))
        {
            return JsonNode.Parse("{}")!;
        }

        try
        {
            var jsonResponse = JsonNode.Parse(responseContent);
            return jsonResponse ?? JsonNode.Parse("{}")!;
        }
        catch
        {
            // If not valid JSON, wrap in an object
            return JsonNode.Parse($$"""
            {
                "response": "{{responseContent}}",
                "statusCode": {{(int)response.StatusCode}}
            }
            """)!;
        }
    }

    private void ApplyAuthentication(HttpRequestMessage request, AuthConfig auth)
    {
        switch (auth.Type.ToLowerInvariant())
        {
            case "bearer":
                // Look for bearer token in environment hints
                if (auth.ConfigHints?.Env != null)
                {
                    foreach (var envVar in auth.ConfigHints.Env)
                    {
                        if (_environmentAuth.TryGetValue(envVar, out var token))
                        {
                            request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", token);
                            return;
                        }
                    }
                }
                break;

            case "api_key":
                // Look for API key in environment hints
                if (auth.ConfigHints?.Env != null)
                {
                    foreach (var envVar in auth.ConfigHints.Env)
                    {
                        if (_environmentAuth.TryGetValue(envVar, out var apiKey))
                        {
                            request.Headers.Add("X-API-Key", apiKey);
                            return;
                        }
                    }
                }
                break;
        }
    }

    private List<AssertionResult> EvaluateAssertions(List<Assertion> assertions, JsonNode actualOutput)
    {
        var results = new List<AssertionResult>();

        foreach (var assertion in assertions)
        {
            var assertionResult = EvaluateAssertion(assertion, actualOutput);
            results.Add(assertionResult);
        }

        return results;
    }

    private AssertionResult EvaluateAssertion(Assertion assertion, JsonNode actualOutput)
    {
        var result = new AssertionResult
        {
            Path = assertion.Path
        };

        try
        {
            // Use JsonPath.Net to query the path
            var path = JsonPath.Parse(assertion.Path);
            var match = path.Evaluate(actualOutput);

            // Check if path exists
            if (match.Matches == null || !match.Matches.Any())
            {
                // Path doesn't exist
                if (assertion.NotExists == true)
                {
                    result.Passed = true;
                    result.Message = $"Path '{assertion.Path}' does not exist (as expected)";
                }
                else if (assertion.Exists == true)
                {
                    result.Passed = false;
                    result.Message = $"Path '{assertion.Path}' does not exist (expected to exist)";
                }
                else
                {
                    result.Passed = false;
                    result.Message = $"Path '{assertion.Path}' does not exist";
                }
                return result;
            }

            // Get the actual value
            var matchedValue = match.Matches.First().Value;
            result.ActualValue = matchedValue != null
                ? JsonNode.Parse(JsonSerializer.Serialize(matchedValue))
                : null;

            // Evaluate assertion type
            if (assertion.Exists == true)
            {
                result.Passed = true;
                result.Message = $"Path '{assertion.Path}' exists (as expected)";
            }
            else if (assertion.NotExists == true)
            {
                result.Passed = false;
                result.Message = $"Path '{assertion.Path}' exists (expected not to exist)";
            }
            else if (assertion.Equals != null)
            {
                result.ExpectedValue = assertion.Equals;
                result.Passed = JsonNode.DeepEquals(result.ActualValue, assertion.Equals);
                result.Message = result.Passed
                    ? $"Value at '{assertion.Path}' equals expected value"
                    : $"Value at '{assertion.Path}' does not equal expected value. Expected: {assertion.Equals?.ToJsonString()}, Actual: {result.ActualValue?.ToJsonString()}";
            }
            else if (assertion.NotEquals != null)
            {
                result.ExpectedValue = assertion.NotEquals;
                result.Passed = !JsonNode.DeepEquals(result.ActualValue, assertion.NotEquals);
                result.Message = result.Passed
                    ? $"Value at '{assertion.Path}' does not equal {assertion.NotEquals.ToJsonString()} (as expected)"
                    : $"Value at '{assertion.Path}' equals {assertion.NotEquals.ToJsonString()} (expected to be different)";
            }
            else
            {
                result.Passed = false;
                result.Message = "No assertion type specified";
            }
        }
        catch (Exception ex)
        {
            result.Passed = false;
            result.Message = $"Error evaluating assertion: {ex.Message}";
        }

        return result;
    }
}
