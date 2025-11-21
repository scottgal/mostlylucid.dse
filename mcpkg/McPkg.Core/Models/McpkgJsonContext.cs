using System.Text.Json;
using System.Text.Json.Serialization;

namespace mostlylucid.mcpregistry.Core.Models;

/// <summary>
/// JSON source generation context for MCPKG models
/// </summary>
[JsonSourceGenerationOptions(
    WriteIndented = true,
    PropertyNamingPolicy = JsonKnownNamingPolicy.CamelCase,
    DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
    GenerationMode = JsonSourceGenerationMode.Default)]
[JsonSerializable(typeof(Manifest))]
[JsonSerializable(typeof(TestCase))]
[JsonSerializable(typeof(TestResult))]
[JsonSerializable(typeof(ToolDefinition))]
[JsonSerializable(typeof(PackageInfo))]
[JsonSerializable(typeof(ValidationResult))]
[JsonSerializable(typeof(ProvenanceInfo))]
[JsonSerializable(typeof(List<PackageInfo>))]
[JsonSerializable(typeof(List<ToolDefinition>))]
[JsonSerializable(typeof(List<TestResult>))]
public partial class McpkgJsonContext : JsonSerializerContext
{
}
