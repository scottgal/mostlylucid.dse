#!/usr/bin/env python3
"""
Demo script showing how to use the technical writing tools for blog content creation.
This demonstrates the specialized LLM tools for article writing and analysis.
"""
import sys
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich import box

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src import create_rag_memory, OllamaClient
from src.config_manager import ConfigManager
from src.tools_manager import ToolsManager, ToolType

console = Console()

def demo_technical_writing_tools():
    """Demonstrate the technical writing tools."""

    console.print("[bold cyan]Technical Writing Tools Demo[/bold cyan]\n")

    # Initialize
    console.print("[dim]Initializing system...[/dim]")
    config = ConfigManager("config.yaml")
    client = OllamaClient(config.ollama_url, config_manager=config)
    rag = create_rag_memory(config, client)
    tools = ToolsManager(config_manager=config, ollama_client=client, rag_memory=rag)

    console.print("[green]OK System initialized[/green]\n")

    # Demo 1: List available writing tools
    console.print("[bold]Available Technical Writing Tools:[/bold]\n")

    writing_tools = tools.search("technical writing blog article", top_k=10, use_rag=True)
    writing_tools = [t for t in writing_tools if any(tag in t.tags for tag in ["writing", "blog", "article", "seo", "analysis"])]

    for tool in writing_tools:
        console.print(f"[cyan]{tool.name}[/cyan]")
        console.print(f"  Description: {tool.description}")
        console.print(f"  Tags: {', '.join(tool.tags)}")
        console.print()

    # Demo 2: Find best tool for article writing
    console.print("\n[bold]Test 1: Finding tool for 'write a blog post about Python decorators'[/bold]\n")

    task = "write a blog post about Python decorators"
    best_tool = tools.get_best_llm_for_task(task)

    if best_tool:
        console.print(f"[green]Selected tool: {best_tool.name}[/green]")
        console.print(f"[dim]Description: {best_tool.description}[/dim]")
    else:
        console.print("[yellow]No specialized tool found, would use general fallback[/yellow]")

    # Demo 3: Find tool for SEO optimization
    console.print("\n[bold]Test 2: Finding tool for 'optimize my article for search engines'[/bold]\n")

    task = "optimize my article for search engines"
    best_tool = tools.get_best_llm_for_task(task)

    if best_tool:
        console.print(f"[green]Selected tool: {best_tool.name}[/green]")
        console.print(f"[dim]Description: {best_tool.description}[/dim]")
    else:
        console.print("[yellow]No specialized tool found[/yellow]")

    # Demo 4: Find tool for content analysis
    console.print("\n[bold]Test 3: Finding tool for 'analyze my blog post for readability'[/bold]\n")

    task = "analyze my blog post for readability"
    best_tool = tools.get_best_llm_for_task(task)

    if best_tool:
        console.print(f"[green]Selected tool: {best_tool.name}[/green]")
        console.print(f"[dim]Description: {best_tool.description}[/dim]")
    else:
        console.print("[yellow]No specialized tool found[/yellow]")

    # Demo 5: Example workflow for creating a blog post
    console.print("\n[bold cyan]Example Workflow: Creating a Technical Blog Post[/bold cyan]\n")

    workflow_steps = [
        ("1. Outline Generator", "Create article structure and flow"),
        ("2. Technical Writer", "Write the main content"),
        ("3. Code Explainer", "Add clear explanations and examples"),
        ("4. SEO Optimizer", "Optimize for search engines"),
        ("5. Article Analyzer", "Review clarity and technical accuracy"),
        ("6. Proofreader", "Final grammar and style check")
    ]

    for step, description in workflow_steps:
        console.print(f"[cyan]{step}[/cyan]: {description}")

    console.print("\n[green]OK All writing tools are ready to use![/green]")

    # Demo 6: Show how to invoke a tool
    console.print("\n[bold]Example: Invoking the Technical Writer tool[/bold]\n")

    console.print("[dim]Example code:[/dim]")
    console.print(Panel(
        """from src import OllamaClient, ToolsManager
from src.config_manager import ConfigManager

config = ConfigManager("config.yaml")
client = OllamaClient(config.ollama_url, config_manager=config)
tools = ToolsManager(config_manager=config, ollama_client=client)

# Invoke the technical writer
result = tools.invoke_llm_tool(
    tool_id="technical_writer",
    prompt=\"\"\"Write a blog post introduction about Python decorators.

    Target audience: Intermediate Python developers
    Tone: Professional but friendly
    Length: 200-300 words
    \"\"\",
    temperature=0.7
)

print(result)""",
        title="[cyan]Code Example[/cyan]",
        box=box.ROUNDED
    ))

    # Summary
    console.print("\n[bold green]Summary[/bold green]")
    console.print("\nThe following specialized tools are now available:")
    console.print("  - Technical Article Writer: Create blog posts and tutorials")
    console.print("  - Article Content Analyzer: Review and improve content")
    console.print("  - SEO Optimizer: Improve search engine visibility")
    console.print("  - Code Concept Explainer: Simplify complex topics")
    console.print("  - Article Outline Generator: Structure your content")
    console.print("  - Technical Proofreader: Polish your writing")

    console.print("\n[bold cyan]Next Steps:[/bold cyan]")
    console.print("1. These tools are automatically selected based on your task")
    console.print("2. In chat_cli.py, just describe what you want:")
    console.print("   'generate write a blog post about async/await in Python'")
    console.print("3. The system will choose the Technical Article Writer tool")
    console.print("4. Future: Add blog content ingestion for analysis")

    return True

if __name__ == "__main__":
    try:
        demo_technical_writing_tools()
        sys.exit(0)
    except KeyboardInterrupt:
        console.print("\n[yellow]Demo interrupted[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]Demo failed: {e}[/red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)
