"""
Demo: Backend Configuration Checker

Shows how the backend configuration checker works.
Run this to see which backends are configured and ready.
"""

from rich.console import Console
from rich.table import Table
from rich import box

from src.config_manager import ConfigManager
from src.backend_config_checker import BackendConfigChecker, BackendStatus

console = Console()


def main():
    """Demo the backend configuration checker."""
    console.print("\n[bold cyan]Backend Configuration Checker Demo[/bold cyan]\n")

    # Initialize
    config = ConfigManager()
    checker = BackendConfigChecker(config)

    # Check all backends
    console.print("[dim]Checking all backend configurations...[/dim]\n")
    results = checker.check_all_backends(test_connection=False)

    # Display results
    table = Table(
        title="Backend Status",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold magenta"
    )
    table.add_column("Backend", style="cyan", no_wrap=True)
    table.add_column("Status", justify="center")
    table.add_column("Message")
    table.add_column("Ready", justify="center")

    for backend, result in sorted(results.items()):
        # Status and color (Windows-safe, no Unicode)
        if result.status == BackendStatus.READY:
            status_str = "[green]OK READY[/green]"
            ready_str = "[green]YES[/green]"
        elif result.status == BackendStatus.MISSING_API_KEY:
            status_str = "[yellow]WARN NO API KEY[/yellow]"
            ready_str = "[red]NO[/red]"
        elif result.status == BackendStatus.MISSING_CONFIG:
            status_str = "[dim]- NOT CONFIGURED[/dim]"
            ready_str = "[dim]NO[/dim]"
        elif result.status == BackendStatus.UNAVAILABLE:
            status_str = "[red]FAIL UNAVAILABLE[/red]"
            ready_str = "[red]NO[/red]"
        else:
            status_str = "[yellow]WARN INVALID[/yellow]"
            ready_str = "[red]NO[/red]"

        table.add_row(backend, status_str, result.message, ready_str)

    console.print(table)

    # Summary
    ready_backends = checker.get_ready_backends()
    primary = checker.get_primary_backend()

    console.print()
    console.print(f"[bold]Summary:[/bold]")
    console.print(f"  • Total backends: {len(results)}")
    console.print(f"  • Ready backends: {len(ready_backends)}")
    if primary:
        console.print(f"  • Primary backend: {primary}")

    if ready_backends:
        console.print(f"\n[green]OK Ready to use:[/green] {', '.join(ready_backends)}")
    else:
        console.print(f"\n[yellow]WARNING: No backends are fully configured[/yellow]")

    # Show setup suggestions for missing backends
    not_ready = [b for b, r in results.items()
                 if not r.ready and r.status != BackendStatus.MISSING_CONFIG]

    if not_ready:
        console.print(f"\n[bold]Setup Suggestions:[/bold]")
        for backend in not_ready[:2]:  # Show first 2
            result = results[backend]
            console.print(f"\n[cyan]{backend.upper()}[/cyan]: {result.message}")
            suggestions = checker.suggest_setup_commands(backend)
            if suggestions:
                console.print(f"[dim]{suggestions[0]}[/dim]")

    console.print("\n[dim]Tip: Run 'backends --test' in chat_cli to test connections[/dim]\n")


if __name__ == "__main__":
    main()
