namespace mostlylucid.mcpregistry.Core.Models;

/// <summary>
/// Information about an installed MCPKG package
/// </summary>
public class PackageInfo
{
    public string ToolId { get; set; } = string.Empty;
    public string Version { get; set; } = string.Empty;
    public string Name { get; set; } = string.Empty;
    public string Description { get; set; } = string.Empty;
    public string InstallPath { get; set; } = string.Empty;
    public DateTime InstalledAt { get; set; }
    public List<string> Capabilities { get; set; } = new();
}

/// <summary>
/// Validation result for a manifest or package
/// </summary>
public class ValidationResult
{
    public bool IsValid { get; set; }
    public List<string> Errors { get; set; } = new();
    public List<string> Warnings { get; set; } = new();

    public static ValidationResult Success() => new() { IsValid = true };

    public static ValidationResult Failure(params string[] errors) => new()
    {
        IsValid = false,
        Errors = errors.ToList()
    };
}
