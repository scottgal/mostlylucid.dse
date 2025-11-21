using System.Text.Json.Nodes;
using System.Text.Json.Serialization;

namespace mostlylucid.mcpregistry.Core.Models;

/// <summary>
/// Represents a test case for an MCPKG tool
/// </summary>
public class TestCase
{
    [JsonPropertyName("name")]
    [JsonRequired]
    public string Name { get; set; } = string.Empty;

    [JsonPropertyName("description")]
    [JsonRequired]
    public string Description { get; set; } = string.Empty;

    [JsonPropertyName("input")]
    [JsonRequired]
    public JsonNode Input { get; set; } = JsonNode.Parse("{}")!;

    [JsonPropertyName("expected")]
    public JsonNode? Expected { get; set; }

    [JsonPropertyName("assertions")]
    [JsonRequired]
    public List<Assertion> Assertions { get; set; } = new();

    [JsonPropertyName("timeoutMs")]
    public int? TimeoutMs { get; set; }
}

/// <summary>
/// Represents an assertion to evaluate against test results
/// </summary>
public class Assertion
{
    [JsonPropertyName("path")]
    [JsonRequired]
    public string Path { get; set; } = string.Empty;

    [JsonPropertyName("equals")]
    public JsonNode? Equals { get; set; }

    [JsonPropertyName("notEquals")]
    public JsonNode? NotEquals { get; set; }

    [JsonPropertyName("exists")]
    public bool? Exists { get; set; }

    [JsonPropertyName("notExists")]
    public bool? NotExists { get; set; }
}

/// <summary>
/// Result of running a test case
/// </summary>
public class TestResult
{
    public string TestName { get; set; } = string.Empty;
    public bool Passed { get; set; }
    public string? ErrorMessage { get; set; }
    public List<AssertionResult> AssertionResults { get; set; } = new();
    public long DurationMs { get; set; }
    public JsonNode? ActualOutput { get; set; }
}

/// <summary>
/// Result of evaluating an assertion
/// </summary>
public class AssertionResult
{
    public string Path { get; set; } = string.Empty;
    public bool Passed { get; set; }
    public string? Message { get; set; }
    public JsonNode? ExpectedValue { get; set; }
    public JsonNode? ActualValue { get; set; }
}
