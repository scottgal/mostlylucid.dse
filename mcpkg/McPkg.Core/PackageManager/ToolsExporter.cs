using System.Text.Json;
using System.Text.Json.Nodes;
using mostlylucid.mcpregistry.Core.Models;
using mostlylucid.mcpregistry.Core.Testing;

namespace mostlylucid.mcpregistry.Core.PackageManager;

/// <summary>
/// Exports installed tools to tools.json format for LLM runtimes
/// </summary>
public class ToolsExporter
{
    private readonly PackageInstaller _installer;
    private readonly TestRunner _testRunner;

    public ToolsExporter(PackageInstaller installer, TestRunner? testRunner = null)
    {
        _installer = installer;
        _testRunner = testRunner ?? new TestRunner();
    }

    /// <summary>
    /// Exports all installed tools to a tools.json file
    /// </summary>
    /// <param name="outputPath">Path for output tools.json file</param>
    /// <param name="runTests">Whether to run tests and include test summaries</param>
    public async Task<List<ToolDefinition>> ExportToolsAsync(string? outputPath = null, bool runTests = false)
    {
        var packages = await _installer.ListInstalledPackagesAsync();
        var toolDefinitions = new List<ToolDefinition>();

        foreach (var package in packages)
        {
            var manifest = await _installer.LoadManifestAsync(package.ToolId);
            if (manifest == null)
            {
                continue;
            }

            var toolDef = new ToolDefinition
            {
                Name = manifest.Name,
                Description = manifest.Description,
                InputSchema = manifest.InputSchema,
                Capabilities = manifest.Capabilities
            };

            // Include examples if available
            if (manifest.Examples != null && manifest.Examples.Count > 0)
            {
                toolDef.Examples = await LoadExamplesAsync(package.InstallPath, manifest.Examples);
            }

            // Run tests if requested
            if (runTests && manifest.Tests != null && manifest.Tests.Count > 0)
            {
                var testSummary = await RunTestsAndGenerateSummaryAsync(package.InstallPath, manifest);
                toolDef.TestSummary = testSummary;
            }

            toolDefinitions.Add(toolDef);
        }

        // Write to file if path provided
        if (!string.IsNullOrEmpty(outputPath))
        {
            var json = JsonSerializer.Serialize(toolDefinitions, McpkgJsonContext.Default.ListToolDefinition);
            await File.WriteAllTextAsync(outputPath, json);
        }

        return toolDefinitions;
    }

    private async Task<List<string>> LoadExamplesAsync(string installPath, List<string> examplePaths)
    {
        var examples = new List<string>();

        foreach (var examplePath in examplePaths)
        {
            var fullPath = Path.Combine(installPath, examplePath.Replace('/', Path.DirectorySeparatorChar));
            if (File.Exists(fullPath))
            {
                try
                {
                    var content = await File.ReadAllTextAsync(fullPath);
                    examples.Add(content);
                }
                catch
                {
                    // Skip files that can't be read
                }
            }
        }

        return examples;
    }

    private async Task<TestSummary?> RunTestsAndGenerateSummaryAsync(string installPath, Manifest manifest)
    {
        if (manifest.Tests == null || manifest.Tests.Count == 0)
        {
            return null;
        }

        var testCases = new List<TestCase>();

        // Load test cases
        foreach (var testPath in manifest.Tests)
        {
            var fullPath = Path.Combine(installPath, testPath.Replace('/', Path.DirectorySeparatorChar));
            if (File.Exists(fullPath))
            {
                try
                {
                    var testJson = await File.ReadAllTextAsync(fullPath);
                    var testCase = JsonSerializer.Deserialize(testJson, McpkgJsonContext.Default.TestCase);
                    if (testCase != null)
                    {
                        testCases.Add(testCase);
                    }
                }
                catch
                {
                    // Skip invalid test cases
                }
            }
        }

        if (testCases.Count == 0)
        {
            return null;
        }

        // Run tests
        var results = await _testRunner.RunTestsAsync(manifest, testCases);

        // Generate summary
        var summary = new TestSummary
        {
            Total = results.Count,
            Passed = results.Count(r => r.Passed),
            Failed = results.Count(r => !r.Passed),
            AverageLatencyMs = results.Average(r => r.DurationMs)
        };

        return summary;
    }

    /// <summary>
    /// Exports a single tool to a ToolDefinition
    /// </summary>
    public async Task<ToolDefinition?> ExportToolAsync(string toolId, bool runTests = false)
    {
        var manifest = await _installer.LoadManifestAsync(toolId);
        if (manifest == null)
        {
            return null;
        }

        var packages = await _installer.ListInstalledPackagesAsync();
        var package = packages.FirstOrDefault(p => p.ToolId == toolId);
        if (package == null)
        {
            return null;
        }

        var toolDef = new ToolDefinition
        {
            Name = manifest.Name,
            Description = manifest.Description,
            InputSchema = manifest.InputSchema,
            Capabilities = manifest.Capabilities
        };

        // Include examples if available
        if (manifest.Examples != null && manifest.Examples.Count > 0)
        {
            toolDef.Examples = await LoadExamplesAsync(package.InstallPath, manifest.Examples);
        }

        // Run tests if requested
        if (runTests && manifest.Tests != null && manifest.Tests.Count > 0)
        {
            var testSummary = await RunTestsAndGenerateSummaryAsync(package.InstallPath, manifest);
            toolDef.TestSummary = testSummary;
        }

        return toolDef;
    }
}
