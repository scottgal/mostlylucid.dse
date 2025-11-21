using System.Text.Json.Nodes;
using System.Text.Json.Serialization;

namespace mostlylucid.mcpregistry.Core.Models;

/// <summary>
/// Tool definition for LLM runtime (tools.json)
/// </summary>
public class ToolDefinition
{
    [JsonPropertyName("name")]
    public string Name { get; set; } = string.Empty;

    [JsonPropertyName("description")]
    public string Description { get; set; } = string.Empty;

    [JsonPropertyName("input_schema")]
    public JsonNode InputSchema { get; set; } = JsonNode.Parse("{}")!;

    [JsonPropertyName("capabilities")]
    public List<string> Capabilities { get; set; } = new();

    [JsonPropertyName("examples")]
    public List<string>? Examples { get; set; }

    [JsonPropertyName("test_summary")]
    public TestSummary? TestSummary { get; set; }
}

/// <summary>
/// Summary of test results for a tool
/// </summary>
public class TestSummary
{
    [JsonPropertyName("total")]
    public int Total { get; set; }

    [JsonPropertyName("passed")]
    public int Passed { get; set; }

    [JsonPropertyName("failed")]
    public int Failed { get; set; }

    [JsonPropertyName("average_latency_ms")]
    public double AverageLatencyMs { get; set; }
}
