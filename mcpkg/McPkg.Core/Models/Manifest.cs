using System.Text.Json;
using System.Text.Json.Nodes;
using System.Text.Json.Serialization;

namespace mostlylucid.mcpregistry.Core.Models;

/// <summary>
/// Represents an MCPKG manifest.json file
/// </summary>
public class Manifest
{
    [JsonPropertyName("toolId")]
    [JsonRequired]
    public string ToolId { get; set; } = string.Empty;

    [JsonPropertyName("name")]
    [JsonRequired]
    public string Name { get; set; } = string.Empty;

    [JsonPropertyName("version")]
    [JsonRequired]
    public string Version { get; set; } = string.Empty;

    [JsonPropertyName("description")]
    [JsonRequired]
    public string Description { get; set; } = string.Empty;

    [JsonPropertyName("capabilities")]
    [JsonRequired]
    public List<string> Capabilities { get; set; } = new();

    [JsonPropertyName("endpoint")]
    [JsonRequired]
    public Endpoint Endpoint { get; set; } = new();

    [JsonPropertyName("input_schema")]
    [JsonRequired]
    public JsonNode InputSchema { get; set; } = JsonNode.Parse("{}")!;

    [JsonPropertyName("output_schema")]
    [JsonRequired]
    public JsonNode OutputSchema { get; set; } = JsonNode.Parse("{}")!;

    [JsonPropertyName("auth")]
    public AuthConfig? Auth { get; set; }

    [JsonPropertyName("tests")]
    public List<string>? Tests { get; set; }

    [JsonPropertyName("examples")]
    public List<string>? Examples { get; set; }

    [JsonPropertyName("meta")]
    public MetaInfo? Meta { get; set; }
}

/// <summary>
/// Endpoint configuration
/// </summary>
public class Endpoint
{
    [JsonPropertyName("type")]
    [JsonRequired]
    public string Type { get; set; } = "http";

    [JsonPropertyName("method")]
    [JsonRequired]
    public string Method { get; set; } = "POST";

    [JsonPropertyName("url")]
    [JsonRequired]
    public string Url { get; set; } = string.Empty;

    [JsonPropertyName("timeoutMs")]
    public int? TimeoutMs { get; set; }
}

/// <summary>
/// Authentication configuration
/// </summary>
public class AuthConfig
{
    [JsonPropertyName("type")]
    [JsonRequired]
    public string Type { get; set; } = "none";

    [JsonPropertyName("scopes")]
    public List<string>? Scopes { get; set; }

    [JsonPropertyName("configHints")]
    public ConfigHints? ConfigHints { get; set; }
}

/// <summary>
/// Configuration hints for authentication setup
/// </summary>
public class ConfigHints
{
    [JsonPropertyName("env")]
    public List<string>? Env { get; set; }

    [JsonPropertyName("docsUrl")]
    public string? DocsUrl { get; set; }
}

/// <summary>
/// Package metadata
/// </summary>
public class MetaInfo
{
    [JsonPropertyName("publisher")]
    public PublisherInfo? Publisher { get; set; }

    [JsonPropertyName("license")]
    public string? License { get; set; }

    [JsonPropertyName("homepage")]
    public string? Homepage { get; set; }

    [JsonPropertyName("tags")]
    public List<string>? Tags { get; set; }
}

/// <summary>
/// Publisher information
/// </summary>
public class PublisherInfo
{
    [JsonPropertyName("id")]
    [JsonRequired]
    public string Id { get; set; } = string.Empty;

    [JsonPropertyName("name")]
    [JsonRequired]
    public string Name { get; set; } = string.Empty;

    [JsonPropertyName("website")]
    public string? Website { get; set; }

    [JsonPropertyName("contact")]
    public string? Contact { get; set; }
}

/// <summary>
/// Provenance information
/// </summary>
public class ProvenanceInfo
{
    [JsonPropertyName("sourceRepo")]
    public string? SourceRepo { get; set; }

    [JsonPropertyName("commit")]
    public string? Commit { get; set; }

    [JsonPropertyName("builtAt")]
    public DateTime? BuiltAt { get; set; }

    [JsonPropertyName("builtBy")]
    public string? BuiltBy { get; set; }
}
