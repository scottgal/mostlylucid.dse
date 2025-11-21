using System.IO.Compression;
using System.Text.Json;
using mostlylucid.mcpregistry.Core.Models;
using mostlylucid.mcpregistry.Core.Validation;

namespace mostlylucid.mcpregistry.Core.PackageManager;

/// <summary>
/// Creates .mcpkg packages from source folders
/// </summary>
public class PackageCreator
{
    private readonly ManifestValidator _manifestValidator = new();
    private readonly TestCaseValidator _testCaseValidator = new();

    /// <summary>
    /// Creates a .mcpkg file from a source folder
    /// </summary>
    /// <param name="sourceFolder">Path to folder containing manifest.json and other files</param>
    /// <param name="outputPath">Path for the output .mcpkg file</param>
    /// <param name="validate">Whether to validate before creating package</param>
    public async Task<ValidationResult> CreatePackageAsync(
        string sourceFolder,
        string outputPath,
        bool validate = true)
    {
        // Validate source folder exists
        if (!Directory.Exists(sourceFolder))
        {
            return ValidationResult.Failure($"Source folder not found: {sourceFolder}");
        }

        // Check for manifest.json
        var manifestPath = Path.Combine(sourceFolder, "manifest.json");
        if (!File.Exists(manifestPath))
        {
            return ValidationResult.Failure("manifest.json not found in source folder");
        }

        // Read and validate manifest
        var manifestJson = await File.ReadAllTextAsync(manifestPath);
        var manifest = JsonSerializer.Deserialize(manifestJson, McpkgJsonContext.Default.Manifest);
        if (manifest == null)
        {
            return ValidationResult.Failure("Failed to parse manifest.json");
        }

        if (validate)
        {
            var validationResult = _manifestValidator.Validate(manifest);
            if (!validationResult.IsValid)
            {
                return validationResult;
            }

            // Validate test cases if they exist
            if (manifest.Tests != null && manifest.Tests.Count > 0)
            {
                var testValidation = await ValidateTestCasesAsync(sourceFolder, manifest);
                if (!testValidation.IsValid)
                {
                    return testValidation;
                }
            }
        }

        // Create output directory if needed
        var outputDir = Path.GetDirectoryName(outputPath);
        if (!string.IsNullOrEmpty(outputDir) && !Directory.Exists(outputDir))
        {
            Directory.CreateDirectory(outputDir);
        }

        // Delete existing package if it exists
        if (File.Exists(outputPath))
        {
            File.Delete(outputPath);
        }

        // Create ZIP archive
        try
        {
            ZipFile.CreateFromDirectory(
                sourceFolder,
                outputPath,
                CompressionLevel.Optimal,
                includeBaseDirectory: false);

            return ValidationResult.Success();
        }
        catch (Exception ex)
        {
            return ValidationResult.Failure($"Failed to create package: {ex.Message}");
        }
    }

    private async Task<ValidationResult> ValidateTestCasesAsync(string sourceFolder, Manifest manifest)
    {
        var errors = new List<string>();

        foreach (var testPath in manifest.Tests!)
        {
            var fullTestPath = Path.Combine(sourceFolder, testPath.Replace('/', Path.DirectorySeparatorChar));

            if (!File.Exists(fullTestPath))
            {
                errors.Add($"Test file not found: {testPath}");
                continue;
            }

            try
            {
                var testJson = await File.ReadAllTextAsync(fullTestPath);
                var testCase = JsonSerializer.Deserialize(testJson, McpkgJsonContext.Default.TestCase);

                if (testCase == null)
                {
                    errors.Add($"Failed to parse test case: {testPath}");
                    continue;
                }

                // Validate test case structure
                var testValidation = _testCaseValidator.Validate(testCase);
                if (!testValidation.IsValid)
                {
                    errors.Add($"Test case '{testPath}' is invalid:");
                    errors.AddRange(testValidation.Errors);
                    continue;
                }

                // Validate test input against manifest input_schema
                var schemaValidation = _testCaseValidator.ValidateAgainstSchema(testCase, manifest.InputSchema);
                if (!schemaValidation.IsValid)
                {
                    errors.AddRange(schemaValidation.Errors);
                }
            }
            catch (Exception ex)
            {
                errors.Add($"Error validating test '{testPath}': {ex.Message}");
            }
        }

        return errors.Count == 0
            ? ValidationResult.Success()
            : new ValidationResult { IsValid = false, Errors = errors };
    }

    /// <summary>
    /// Generates a suggested output filename based on the manifest
    /// </summary>
    public static string GeneratePackageFileName(Manifest manifest)
    {
        // Replace dots with dashes for readability (except before version)
        var sanitizedToolId = manifest.ToolId.Replace('.', '-');
        return $"{sanitizedToolId}-{manifest.Version}.mcpkg";
    }
}
