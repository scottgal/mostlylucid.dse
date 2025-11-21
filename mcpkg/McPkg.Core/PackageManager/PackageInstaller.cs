using System.IO.Compression;
using System.Text.Json;
using mostlylucid.mcpregistry.Core.Models;
using mostlylucid.mcpregistry.Core.Validation;

namespace mostlylucid.mcpregistry.Core.PackageManager;

/// <summary>
/// Installs and manages .mcpkg packages
/// </summary>
public class PackageInstaller
{
    private readonly ManifestValidator _manifestValidator = new();
    private readonly string _installRoot;

    public PackageInstaller(string installRoot = ".mcp/tools")
    {
        _installRoot = installRoot;
    }

    /// <summary>
    /// Installs a .mcpkg file to the install root
    /// </summary>
    /// <param name="packagePath">Path to the .mcpkg file</param>
    /// <param name="validate">Whether to validate the package before installing</param>
    public async Task<(ValidationResult validation, PackageInfo? package)> InstallPackageAsync(
        string packagePath,
        bool validate = true)
    {
        // Check package exists
        if (!File.Exists(packagePath))
        {
            return (ValidationResult.Failure($"Package file not found: {packagePath}"), null);
        }

        // Create temp directory for extraction
        var tempDir = Path.Combine(Path.GetTempPath(), $"mcpkg_{Guid.NewGuid():N}");
        Directory.CreateDirectory(tempDir);

        try
        {
            // Extract package
            ZipFile.ExtractToDirectory(packagePath, tempDir);

            // Read manifest
            var manifestPath = Path.Combine(tempDir, "manifest.json");
            if (!File.Exists(manifestPath))
            {
                return (ValidationResult.Failure("Package does not contain manifest.json"), null);
            }

            var manifestJson = await File.ReadAllTextAsync(manifestPath);
            var manifest = JsonSerializer.Deserialize(manifestJson, McpkgJsonContext.Default.Manifest);

            if (manifest == null)
            {
                return (ValidationResult.Failure("Failed to parse manifest.json"), null);
            }

            // Validate if requested
            if (validate)
            {
                var validationResult = _manifestValidator.Validate(manifest);
                if (!validationResult.IsValid)
                {
                    return (validationResult, null);
                }
            }

            // Determine install path
            var installPath = Path.Combine(_installRoot, manifest.ToolId);

            // Create install directory
            if (Directory.Exists(installPath))
            {
                // Remove existing installation
                Directory.Delete(installPath, recursive: true);
            }
            Directory.CreateDirectory(installPath);

            // Copy all files from temp to install location
            CopyDirectory(tempDir, installPath);

            // Create package info
            var packageInfo = new PackageInfo
            {
                ToolId = manifest.ToolId,
                Version = manifest.Version,
                Name = manifest.Name,
                Description = manifest.Description,
                InstallPath = installPath,
                InstalledAt = DateTime.UtcNow,
                Capabilities = manifest.Capabilities
            };

            // Save package info
            var packageInfoPath = Path.Combine(installPath, "package-info.json");
            var packageInfoJson = JsonSerializer.Serialize(packageInfo, McpkgJsonContext.Default.PackageInfo);
            await File.WriteAllTextAsync(packageInfoPath, packageInfoJson);

            return (ValidationResult.Success(), packageInfo);
        }
        catch (Exception ex)
        {
            return (ValidationResult.Failure($"Installation failed: {ex.Message}"), null);
        }
        finally
        {
            // Clean up temp directory
            if (Directory.Exists(tempDir))
            {
                try
                {
                    Directory.Delete(tempDir, recursive: true);
                }
                catch
                {
                    // Ignore cleanup errors
                }
            }
        }
    }

    /// <summary>
    /// Installs a package from a URL
    /// </summary>
    /// <param name="url">URL to the .mcpkg file</param>
    /// <param name="validate">Whether to validate the package before installing</param>
    public async Task<(ValidationResult validation, PackageInfo? package)> InstallFromUrlAsync(
        string url,
        bool validate = true)
    {
        using var httpClient = new HttpClient();

        try
        {
            // Download the package to a temporary file
            var tempPackage = Path.Combine(Path.GetTempPath(), $"mcpkg_{Guid.NewGuid():N}.mcpkg");

            var response = await httpClient.GetAsync(url);
            response.EnsureSuccessStatusCode();

            await using var fileStream = File.Create(tempPackage);
            await response.Content.CopyToAsync(fileStream);
            await fileStream.FlushAsync();
            fileStream.Close();

            // Install from the downloaded file
            var result = await InstallPackageAsync(tempPackage, validate);

            // Clean up temp file
            try
            {
                File.Delete(tempPackage);
            }
            catch
            {
                // Ignore cleanup errors
            }

            return result;
        }
        catch (Exception ex)
        {
            return (ValidationResult.Failure($"Failed to download package from URL: {ex.Message}"), null);
        }
    }

    /// <summary>
    /// Lists all installed packages
    /// </summary>
    public async Task<List<PackageInfo>> ListInstalledPackagesAsync()
    {
        var packages = new List<PackageInfo>();

        if (!Directory.Exists(_installRoot))
        {
            return packages;
        }

        foreach (var toolDir in Directory.GetDirectories(_installRoot))
        {
            var packageInfoPath = Path.Combine(toolDir, "package-info.json");
            if (File.Exists(packageInfoPath))
            {
                try
                {
                    var json = await File.ReadAllTextAsync(packageInfoPath);
                    var packageInfo = JsonSerializer.Deserialize(json, McpkgJsonContext.Default.PackageInfo);
                    if (packageInfo != null)
                    {
                        packages.Add(packageInfo);
                    }
                }
                catch
                {
                    // Skip packages with invalid info
                }
            }
        }

        return packages;
    }

    /// <summary>
    /// Loads a manifest from an installed package
    /// </summary>
    public async Task<Manifest?> LoadManifestAsync(string toolId)
    {
        var manifestPath = Path.Combine(_installRoot, toolId, "manifest.json");

        if (!File.Exists(manifestPath))
        {
            return null;
        }

        try
        {
            var json = await File.ReadAllTextAsync(manifestPath);
            return JsonSerializer.Deserialize(json, McpkgJsonContext.Default.Manifest);
        }
        catch
        {
            return null;
        }
    }

    /// <summary>
    /// Uninstalls a package
    /// </summary>
    public bool UninstallPackage(string toolId)
    {
        var installPath = Path.Combine(_installRoot, toolId);

        if (!Directory.Exists(installPath))
        {
            return false;
        }

        try
        {
            Directory.Delete(installPath, recursive: true);
            return true;
        }
        catch
        {
            return false;
        }
    }

    private static void CopyDirectory(string sourceDir, string destDir)
    {
        // Create destination directory
        Directory.CreateDirectory(destDir);

        // Copy files
        foreach (var file in Directory.GetFiles(sourceDir))
        {
            var fileName = Path.GetFileName(file);
            var destFile = Path.Combine(destDir, fileName);
            File.Copy(file, destFile, overwrite: true);
        }

        // Copy subdirectories
        foreach (var subDir in Directory.GetDirectories(sourceDir))
        {
            var dirName = Path.GetFileName(subDir);
            var destSubDir = Path.Combine(destDir, dirName);
            CopyDirectory(subDir, destSubDir);
        }
    }
}
