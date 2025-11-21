using System.CommandLine;
using Spectre.Console;
using mostlylucid.mcpregistry.Core.Models;
using mostlylucid.mcpregistry.Core.PackageManager;
using mostlylucid.mcpregistry.Core.Testing;
using mostlylucid.mcpregistry.Core.Validation;
using System.Text.Json;

var rootCommand = new RootCommand("mcpkg - AI-native package manager for MCP tools");

// CREATE command
var createCommand = new Command("create", "Create a .mcpkg package from a source folder");
var sourceArg = new Argument<string>("source", "Source folder containing manifest.json");
var outputOpt = new Option<string?>(["--output", "-o"], "Output .mcpkg file path");
var noValidateOpt = new Option<bool>("--no-validate", "Skip validation");

createCommand.AddArgument(sourceArg);
createCommand.AddOption(outputOpt);
createCommand.AddOption(noValidateOpt);

createCommand.SetHandler(async (string source, string? output, bool noValidate) =>
{
    await AnsiConsole.Status()
        .StartAsync("Creating package...", async ctx =>
        {
            var creator = new PackageCreator();

            // Determine output path
            if (string.IsNullOrEmpty(output))
            {
                // Try to load manifest to get suggested filename
                var manifestPath = Path.Combine(source, "manifest.json");
                if (File.Exists(manifestPath))
                {
                    try
                    {
                        var json = await File.ReadAllTextAsync(manifestPath);
                        var manifest = JsonSerializer.Deserialize(json, McpkgJsonContext.Default.Manifest);
                        if (manifest != null)
                        {
                            output = PackageCreator.GeneratePackageFileName(manifest);
                        }
                    }
                    catch
                    {
                        output = "package.mcpkg";
                    }
                }
                else
                {
                    output = "package.mcpkg";
                }
            }

            ctx.Status($"Creating package: {output}...");
            var result = await creator.CreatePackageAsync(source, output, !noValidate);

            if (result.IsValid)
            {
                AnsiConsole.MarkupLine($"[green]✓[/] Package created successfully: [cyan]{output}[/]");

                if (result.Warnings.Count > 0)
                {
                    AnsiConsole.MarkupLine("\n[yellow]Warnings:[/]");
                    foreach (var warning in result.Warnings)
                    {
                        AnsiConsole.MarkupLine($"  [yellow]![/] {warning}");
                    }
                }
            }
            else
            {
                AnsiConsole.MarkupLine("[red]✗ Package creation failed:[/]");
                foreach (var error in result.Errors)
                {
                    AnsiConsole.MarkupLine($"  [red]•[/] {error}");
                }
                Environment.ExitCode = 1;
            }
        });
}, sourceArg, outputOpt, noValidateOpt);

// INSTALL command
var installCommand = new Command("install", "Install a .mcpkg package");
var packageArg = new Argument<string>("package", "Path or URL to .mcpkg file");
var installRootOpt = new Option<string>("--root", () => ".mcp/tools", "Installation root directory");

installCommand.AddArgument(packageArg);
installCommand.AddOption(installRootOpt);
installCommand.AddOption(noValidateOpt);

installCommand.SetHandler(async (string package, string installRoot, bool noValidate) =>
{
    await AnsiConsole.Status()
        .StartAsync("Installing package...", async ctx =>
        {
            var installer = new PackageInstaller(installRoot);
            (ValidationResult validation, PackageInfo? packageInfo) result;

            // Check if it's a URL
            if (package.StartsWith("http://") || package.StartsWith("https://"))
            {
                ctx.Status($"Downloading from {package}...");
                result = await installer.InstallFromUrlAsync(package, !noValidate);
            }
            else
            {
                result = await installer.InstallPackageAsync(package, !noValidate);
            }

            if (result.validation.IsValid && result.packageInfo != null)
            {
                AnsiConsole.MarkupLine($"[green]✓[/] Package installed successfully!");
                AnsiConsole.MarkupLine($"  [cyan]Tool ID:[/] {result.packageInfo.ToolId}");
                AnsiConsole.MarkupLine($"  [cyan]Version:[/] {result.packageInfo.Version}");
                AnsiConsole.MarkupLine($"  [cyan]Location:[/] {result.packageInfo.InstallPath}");
            }
            else
            {
                AnsiConsole.MarkupLine("[red]✗ Installation failed:[/]");
                foreach (var error in result.validation.Errors)
                {
                    AnsiConsole.MarkupLine($"  [red]•[/] {error}");
                }
                Environment.ExitCode = 1;
            }
        });
}, packageArg, installRootOpt, noValidateOpt);

// LIST command
var listCommand = new Command("list", "List installed packages");
listCommand.AddOption(installRootOpt);

listCommand.SetHandler(async (string installRoot) =>
{
    var installer = new PackageInstaller(installRoot);
    var packages = await installer.ListInstalledPackagesAsync();

    if (packages.Count == 0)
    {
        AnsiConsole.MarkupLine("[yellow]No packages installed[/]");
        return;
    }

    var table = new Table()
        .Border(TableBorder.Rounded)
        .AddColumn("[cyan]Tool ID[/]")
        .AddColumn("[cyan]Name[/]")
        .AddColumn("[cyan]Version[/]")
        .AddColumn("[cyan]Capabilities[/]")
        .AddColumn("[cyan]Installed[/]");

    foreach (var pkg in packages)
    {
        table.AddRow(
            pkg.ToolId,
            pkg.Name,
            pkg.Version,
            string.Join(", ", pkg.Capabilities),
            pkg.InstalledAt.ToLocalTime().ToString("yyyy-MM-dd HH:mm")
        );
    }

    AnsiConsole.Write(table);
    AnsiConsole.MarkupLine($"\n[green]{packages.Count}[/] package(s) installed");
}, installRootOpt);

// TEST command
var testCommand = new Command("test", "Run tests for an installed tool");
var toolIdArg = new Argument<string>("toolId", "Tool ID to test");
testCommand.AddArgument(toolIdArg);
testCommand.AddOption(installRootOpt);

testCommand.SetHandler(async (string toolId, string installRoot) =>
{
    await AnsiConsole.Status()
        .StartAsync($"Running tests for {toolId}...", async ctx =>
        {
            var installer = new PackageInstaller(installRoot);
            var manifest = await installer.LoadManifestAsync(toolId);

            if (manifest == null)
            {
                AnsiConsole.MarkupLine($"[red]✗ Tool '{toolId}' not found[/]");
                Environment.ExitCode = 1;
                return;
            }

            if (manifest.Tests == null || manifest.Tests.Count == 0)
            {
                AnsiConsole.MarkupLine("[yellow]No tests defined for this tool[/]");
                return;
            }

            var packages = await installer.ListInstalledPackagesAsync();
            var package = packages.FirstOrDefault(p => p.ToolId == toolId);
            if (package == null)
            {
                AnsiConsole.MarkupLine($"[red]✗ Package info not found[/]");
                Environment.ExitCode = 1;
                return;
            }

            // Load test cases
            var testCases = new List<TestCase>();
            foreach (var testPath in manifest.Tests)
            {
                var fullPath = Path.Combine(package.InstallPath, testPath.Replace('/', Path.DirectorySeparatorChar));
                if (File.Exists(fullPath))
                {
                    var testJson = await File.ReadAllTextAsync(fullPath);
                    var testCase = JsonSerializer.Deserialize(testJson, McpkgJsonContext.Default.TestCase);
                    if (testCase != null)
                    {
                        testCases.Add(testCase);
                    }
                }
            }

            if (testCases.Count == 0)
            {
                AnsiConsole.MarkupLine("[yellow]No valid test cases found[/]");
                return;
            }

            ctx.Status($"Running {testCases.Count} test(s)...");
            var runner = new TestRunner();
            var results = await runner.RunTestsAsync(manifest, testCases);

            // Display results
            var table = new Table()
                .Border(TableBorder.Rounded)
                .AddColumn("[cyan]Test[/]")
                .AddColumn("[cyan]Status[/]")
                .AddColumn("[cyan]Duration[/]")
                .AddColumn("[cyan]Details[/]");

            foreach (var result in results)
            {
                var status = result.Passed ? "[green]PASS[/]" : "[red]FAIL[/]";
                var details = result.Passed
                    ? $"{result.AssertionResults.Count} assertion(s) passed"
                    : result.ErrorMessage ?? $"{result.AssertionResults.Count(a => !a.Passed)} assertion(s) failed";

                table.AddRow(
                    result.TestName,
                    status,
                    $"{result.DurationMs}ms",
                    details
                );
            }

            AnsiConsole.Write(table);

            var passed = results.Count(r => r.Passed);
            var failed = results.Count(r => !r.Passed);
            var avgLatency = results.Average(r => r.DurationMs);

            AnsiConsole.MarkupLine($"\n[green]{passed}[/] passed, [red]{failed}[/] failed, avg latency: {avgLatency:F1}ms");

            if (failed > 0)
            {
                Environment.ExitCode = 1;
            }
        });
}, toolIdArg, installRootOpt);

// EXPORT command
var exportCommand = new Command("export", "Export installed tools to tools.json");
var exportOutputOpt = new Option<string>("--output", () => "tools.json", "Output file path");
var runTestsOpt = new Option<bool>("--run-tests", "Run tests and include test summaries");
exportCommand.AddOption(exportOutputOpt);
exportCommand.AddOption(installRootOpt);
exportCommand.AddOption(runTestsOpt);

exportCommand.SetHandler(async (string output, string installRoot, bool runTests) =>
{
    await AnsiConsole.Status()
        .StartAsync("Exporting tools...", async ctx =>
        {
            var installer = new PackageInstaller(installRoot);
            var exporter = new ToolsExporter(installer);

            if (runTests)
            {
                ctx.Status("Running tests...");
            }

            var tools = await exporter.ExportToolsAsync(output, runTests);

            AnsiConsole.MarkupLine($"[green]✓[/] Exported {tools.Count} tool(s) to [cyan]{output}[/]");
        });
}, exportOutputOpt, installRootOpt, runTestsOpt);

// VALIDATE command
var validateCommand = new Command("validate", "Validate a manifest.json file");
var manifestArg = new Argument<string>("manifest", "Path to manifest.json");
validateCommand.AddArgument(manifestArg);

validateCommand.SetHandler(async (string manifestPath) =>
{
    if (!File.Exists(manifestPath))
    {
        AnsiConsole.MarkupLine($"[red]✗ File not found: {manifestPath}[/]");
        Environment.ExitCode = 1;
        return;
    }

    var validator = new ManifestValidator();
    var json = await File.ReadAllTextAsync(manifestPath);
    var result = validator.ValidateJson(json);

    if (result.IsValid)
    {
        AnsiConsole.MarkupLine("[green]✓[/] Manifest is valid");

        if (result.Warnings.Count > 0)
        {
            AnsiConsole.MarkupLine("\n[yellow]Warnings:[/]");
            foreach (var warning in result.Warnings)
            {
                AnsiConsole.MarkupLine($"  [yellow]![/] {warning}");
            }
        }
    }
    else
    {
        AnsiConsole.MarkupLine("[red]✗ Manifest is invalid:[/]");
        foreach (var error in result.Errors)
        {
            AnsiConsole.MarkupLine($"  [red]•[/] {error}");
        }
        Environment.ExitCode = 1;
    }
}, manifestArg);

// UNINSTALL command
var uninstallCommand = new Command("uninstall", "Uninstall a package");
uninstallCommand.AddArgument(toolIdArg);
uninstallCommand.AddOption(installRootOpt);

uninstallCommand.SetHandler(async (string toolId, string installRoot) =>
{
    var installer = new PackageInstaller(installRoot);

    if (!AnsiConsole.Confirm($"Are you sure you want to uninstall '{toolId}'?"))
    {
        return;
    }

    var success = installer.UninstallPackage(toolId);

    if (success)
    {
        AnsiConsole.MarkupLine($"[green]✓[/] Package '{toolId}' uninstalled successfully");
    }
    else
    {
        AnsiConsole.MarkupLine($"[red]✗[/] Failed to uninstall '{toolId}' (not found or in use)");
        Environment.ExitCode = 1;
    }

    await Task.CompletedTask;
}, toolIdArg, installRootOpt);

// Add all commands
rootCommand.AddCommand(createCommand);
rootCommand.AddCommand(installCommand);
rootCommand.AddCommand(listCommand);
rootCommand.AddCommand(testCommand);
rootCommand.AddCommand(exportCommand);
rootCommand.AddCommand(validateCommand);
rootCommand.AddCommand(uninstallCommand);

// Display banner
AnsiConsole.Write(
    new FigletText("MCPKG")
        .LeftJustified()
        .Color(Color.Cyan1));

AnsiConsole.MarkupLine("[dim]AI-native package manager for MCP tools v0.1.0[/]\n");

// Parse and execute
return await rootCommand.InvokeAsync(args);
