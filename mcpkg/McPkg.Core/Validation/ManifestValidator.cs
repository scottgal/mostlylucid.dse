using System.Text.Json;
using System.Text.RegularExpressions;
using Json.Schema;
using mostlylucid.mcpregistry.Core.Models;

namespace mostlylucid.mcpregistry.Core.Validation;

/// <summary>
/// Validates MCPKG manifest files
/// </summary>
public partial class ManifestValidator
{
    [GeneratedRegex(@"^[a-z0-9]+(\.[a-z0-9]+){2,}$", RegexOptions.Compiled)]
    private static partial Regex ToolIdPattern();

    [GeneratedRegex(@"^\d+\.\d+\.\d+(-[a-zA-Z0-9.-]+)?(\+[a-zA-Z0-9.-]+)?$", RegexOptions.Compiled)]
    private static partial Regex SemVerPattern();

    /// <summary>
    /// Validates a manifest object
    /// </summary>
    public ValidationResult Validate(Manifest manifest)
    {
        var errors = new List<string>();
        var warnings = new List<string>();

        // Validate toolId format
        if (string.IsNullOrWhiteSpace(manifest.ToolId))
        {
            errors.Add("toolId is required");
        }
        else if (!ToolIdPattern().IsMatch(manifest.ToolId))
        {
            errors.Add($"toolId '{manifest.ToolId}' must follow format 'publisher.domain.capability.name'");
        }

        // Validate name
        if (string.IsNullOrWhiteSpace(manifest.Name))
        {
            errors.Add("name is required");
        }

        // Validate version (SemVer)
        if (string.IsNullOrWhiteSpace(manifest.Version))
        {
            errors.Add("version is required");
        }
        else if (!SemVerPattern().IsMatch(manifest.Version))
        {
            errors.Add($"version '{manifest.Version}' must be valid SemVer (e.g., 1.0.0)");
        }

        // Validate description
        if (string.IsNullOrWhiteSpace(manifest.Description))
        {
            errors.Add("description is required");
        }

        // Validate capabilities
        if (manifest.Capabilities == null || manifest.Capabilities.Count == 0)
        {
            errors.Add("capabilities array must contain at least one capability");
        }

        // Validate endpoint
        if (manifest.Endpoint == null)
        {
            errors.Add("endpoint is required");
        }
        else
        {
            errors.AddRange(ValidateEndpoint(manifest.Endpoint));
        }

        // Validate schemas
        if (manifest.InputSchema == null)
        {
            errors.Add("input_schema is required");
        }
        else
        {
            errors.AddRange(ValidateJsonSchema(manifest.InputSchema, "input_schema"));
        }

        if (manifest.OutputSchema == null)
        {
            errors.Add("output_schema is required");
        }
        else
        {
            errors.AddRange(ValidateJsonSchema(manifest.OutputSchema, "output_schema"));
        }

        // Validate auth (optional but must be valid if present)
        if (manifest.Auth != null)
        {
            errors.AddRange(ValidateAuth(manifest.Auth));
        }

        // Warnings for missing optional but recommended fields
        if (manifest.Tests == null || manifest.Tests.Count == 0)
        {
            warnings.Add("No tests defined - consider adding test cases");
        }

        if (manifest.Examples == null || manifest.Examples.Count == 0)
        {
            warnings.Add("No examples defined - consider adding usage examples");
        }

        if (manifest.Meta == null)
        {
            warnings.Add("No meta information defined - consider adding publisher info");
        }

        return new ValidationResult
        {
            IsValid = errors.Count == 0,
            Errors = errors,
            Warnings = warnings
        };
    }

    private static List<string> ValidateEndpoint(Endpoint endpoint)
    {
        var errors = new List<string>();

        if (string.IsNullOrWhiteSpace(endpoint.Type))
        {
            errors.Add("endpoint.type is required");
        }
        else if (endpoint.Type != "http")
        {
            errors.Add($"endpoint.type '{endpoint.Type}' is not supported (only 'http' is supported in v0.1)");
        }

        if (string.IsNullOrWhiteSpace(endpoint.Method))
        {
            errors.Add("endpoint.method is required");
        }
        else
        {
            string[] validMethods = ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"];
            if (!validMethods.Contains(endpoint.Method.ToUpperInvariant()))
            {
                errors.Add($"endpoint.method '{endpoint.Method}' is not a valid HTTP method");
            }
        }

        if (string.IsNullOrWhiteSpace(endpoint.Url))
        {
            errors.Add("endpoint.url is required");
        }
        else if (!Uri.TryCreate(endpoint.Url, UriKind.Absolute, out var uri) ||
                 (uri.Scheme != "http" && uri.Scheme != "https"))
        {
            errors.Add($"endpoint.url '{endpoint.Url}' must be a valid HTTP(S) URL");
        }

        if (endpoint.TimeoutMs.HasValue && endpoint.TimeoutMs.Value <= 0)
        {
            errors.Add("endpoint.timeoutMs must be positive if specified");
        }

        return errors;
    }

    private static List<string> ValidateJsonSchema(System.Text.Json.Nodes.JsonNode schema, string fieldName)
    {
        var errors = new List<string>();

        try
        {
            // Try to parse as JSON Schema
            var jsonSchema = JsonSchema.FromText(schema.ToJsonString());

            // Basic validation - check for 'type' property
            var schemaObj = JsonSerializer.Deserialize<Dictionary<string, JsonElement>>(schema.ToJsonString());
            if (schemaObj == null || !schemaObj.ContainsKey("type"))
            {
                errors.Add($"{fieldName} should have a 'type' property");
            }
        }
        catch (Exception ex)
        {
            errors.Add($"{fieldName} is not a valid JSON Schema: {ex.Message}");
        }

        return errors;
    }

    private static List<string> ValidateAuth(AuthConfig auth)
    {
        var errors = new List<string>();

        string[] validTypes = ["none", "bearer", "api_key", "oauth2"];
        if (!validTypes.Contains(auth.Type))
        {
            errors.Add($"auth.type '{auth.Type}' must be one of: {string.Join(", ", validTypes)}");
        }

        return errors;
    }

    /// <summary>
    /// Validates a manifest from JSON string
    /// </summary>
    public ValidationResult ValidateJson(string json)
    {
        try
        {
            var manifest = JsonSerializer.Deserialize(json, McpkgJsonContext.Default.Manifest);
            if (manifest == null)
            {
                return ValidationResult.Failure("Failed to parse manifest JSON");
            }

            return Validate(manifest);
        }
        catch (JsonException ex)
        {
            return ValidationResult.Failure($"Invalid JSON: {ex.Message}");
        }
    }
}
