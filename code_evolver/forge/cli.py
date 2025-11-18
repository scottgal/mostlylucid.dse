"""
Forge CLI - Command-line interface for forge management.

Provides commands for:
- Tool registration
- Validation
- Query and discovery
- Execution
- Optimization
"""
import json
import logging
import yaml
from typing import Dict, Any, Optional, List
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from datetime import datetime

# Import forge components
from .core.registry import ForgeRegistry, ToolManifest
from .core.director import ForgeDirector, IntentRequest
from .core.runtime import ForgeRuntime
from .core.validator import ValidationCouncil
from .core.consensus import ConsensusEngine
from .core.optimizer import IntegrationOptimizer

# Import existing systems
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.rag_memory import RAGMemory
from src.tools_manager import ToolsManager
from src.config_manager import ConfigManager
from src.llm_client_factory import LLMClientFactory

logger = logging.getLogger(__name__)
console = Console()


class ForgeCLI:
    """Command-line interface for forge operations."""

    def __init__(self, config_manager: ConfigManager):
        """
        Initialize forge CLI.

        Args:
            config_manager: Configuration manager
        """
        self.config_manager = config_manager

        # Initialize forge components
        self._init_forge_components()

        logger.info("ForgeCLI initialized")

    def _init_forge_components(self):
        """Initialize all forge components."""
        # Get existing systems
        self.rag_memory = RAGMemory(self.config_manager)
        self.tools_manager = ToolsManager(self.config_manager)

        # Create forge components
        self.registry = ForgeRegistry(
            rag_memory=self.rag_memory,
            tools_manager=self.tools_manager
        )

        self.runtime = ForgeRuntime(registry=self.registry)

        # Get LLM client
        self.llm_client = LLMClientFactory.create_client_from_config(
            self.config_manager,
            model_role='base'
        )

        self.validator = ValidationCouncil(
            registry=self.registry,
            config=self.config_manager.config,
            llm_clients={'base': self.llm_client}
        )

        self.consensus = ConsensusEngine(
            registry=self.registry,
            config=self.config_manager.config
        )

        self.optimizer = IntegrationOptimizer(
            registry=self.registry,
            runtime=self.runtime,
            consensus=self.consensus
        )

        self.director = ForgeDirector(
            registry=self.registry,
            runtime=self.runtime,
            validator=self.validator,
            consensus=self.consensus,
            llm_client=self.llm_client,
            config=self.config_manager.config
        )

    def cmd_register(self, args: List[str]):
        """Register new tool in forge (/forge_register)."""
        if len(args) < 2:
            console.print("[red]Usage: /forge_register <tool_name> <type>[/red]")
            return

        tool_name = args[0]
        tool_type = args[1]

        console.print(f"\n[bold]Registering Tool: {tool_name}[/bold]")
        console.print(f"Type: {tool_type}\n")

        # Interactive prompts
        description = console.input("Description: ")
        tags = console.input("Tags (comma-separated): ").split(',')
        tags = [t.strip() for t in tags if t.strip()]

        # Create manifest
        manifest = ToolManifest(
            tool_id=tool_name,
            version="1.0.0",
            name=tool_name.replace('_', ' ').title(),
            type=tool_type,
            description=description,
            origin={
                'author': 'user',
                'source_model': 'manual',
                'created_at': datetime.utcnow().isoformat() + "Z"
            },
            lineage={
                'ancestor_tool_id': None,
                'mutation_reason': 'initial_registration',
                'commits': []
            },
            trust={
                'level': 'experimental',
                'validation_score': 0.0,
                'risk_score': 1.0
            },
            tags=tags + ['forge', tool_type]
        )

        # Register
        success = self.registry.register_tool_manifest(manifest)

        if success:
            console.print(f"\n[green]✓ Tool registered successfully[/green]")
            console.print(f"Manifest: code_evolver/forge/data/manifests/{tool_name}_v1.0.0.yaml")
            console.print(f"Trust level: experimental")
            console.print(f"\nNext steps:")
            console.print(f"  1. Run validation: /forge_validate {tool_name}")
            console.print(f"  2. Upgrade trust level based on validation results")
        else:
            console.print("[red]✗ Registration failed[/red]")

    def cmd_validate(self, args: List[str]):
        """Validate tool (/forge_validate)."""
        if len(args) < 1:
            console.print("[red]Usage: /forge_validate <tool_id> [version][/red]")
            return

        tool_id = args[0]
        version = args[1] if len(args) > 1 else None

        console.print(f"\n[bold]Validating Tool: {tool_id}[/bold]")
        if version:
            console.print(f"Version: {version}\n")

        # Get manifest
        manifest = self.registry.get_tool_manifest(tool_id, version)
        if not manifest:
            console.print(f"[red]✗ Tool not found: {tool_id}[/red]")
            return

        # Run validation
        result = self.validator.validate_tool(tool_id, manifest.version)

        # Display results
        console.print("\n[bold]Validation Results:[/bold]\n")

        for stage in result.get('stages', []):
            status = "✓" if stage['success'] else "✗"
            color = "green" if stage['success'] else "red"
            console.print(f"[{color}]{status}[/{color}] Stage: {stage['name']}")
            console.print(f"  Score: {stage['score']:.2f}")
            if stage.get('errors'):
                for error in stage['errors']:
                    console.print(f"  [red]Error: {error}[/red]")

        overall_score = result.get('validation_score', 0.0)
        console.print(f"\n[bold]Overall Score: {overall_score:.3f}[/bold]")

        # Show trust level
        trust_level = manifest.trust.get('level', 'experimental')
        console.print(f"Trust Level: {trust_level.upper()}")

        if result['success']:
            console.print("\n[green]✓ Validation passed[/green]")
        else:
            console.print("\n[red]✗ Validation failed[/red]")

    def cmd_query(self, args: List[str]):
        """Query forge registry (/forge_query)."""
        if len(args) < 1:
            console.print("[red]Usage: /forge_query <capability> [--latency <ms>] [--risk <score>] [--trust <level>][/red]")
            return

        capability = args[0]
        constraints = {}

        # Parse options
        i = 1
        while i < len(args):
            if args[i] == '--latency' and i + 1 < len(args):
                constraints['latency_ms_p95'] = float(args[i + 1])
                i += 2
            elif args[i] == '--risk' and i + 1 < len(args):
                constraints['risk_score'] = float(args[i + 1])
                i += 2
            else:
                i += 1

        console.print(f"\n[bold]Querying Forge Registry[/bold]")
        console.print(f"Capability: {capability}")
        if constraints:
            console.print(f"Constraints: {json.dumps(constraints, indent=2)}\n")

        # Query registry
        results = self.registry.query_tools(
            capability=capability,
            constraints=constraints
        )

        # Display results
        if results['best_tool']:
            best = results['best_tool']
            console.print("\n[bold green]Best Tool:[/bold green]")
            console.print(f"  tool_id: {best['tool_id']}")
            console.print(f"  version: {best['version']}")
            console.print(f"  trust_level: {best['trust_level']}")
            console.print(f"  weight: {best['weight']:.2f}")

            if best.get('metrics'):
                console.print(f"\n  Metrics:")
                for key, value in best['metrics'].items():
                    console.print(f"    {key}: {value}")

        if results['alternatives']:
            console.print("\n[bold]Alternatives:[/bold]")
            for i, alt in enumerate(results['alternatives'], 1):
                console.print(f"  {i}. {alt['tool_id']} (weight: {alt['weight']:.2f})")

        if not results['best_tool']:
            console.print("\n[yellow]No tools found matching criteria[/yellow]")

    def cmd_execute(self, args: List[str]):
        """Execute tool (/forge_execute)."""
        if len(args) < 2 or '--input' not in args:
            console.print("[red]Usage: /forge_execute <tool_id> [version] --input <json>[/red]")
            return

        tool_id = args[0]
        version = None
        input_data = {}

        # Parse args
        i = 1
        while i < len(args):
            if args[i] == '--input' and i + 1 < len(args):
                input_data = json.loads(args[i + 1])
                i += 2
            elif args[i] != tool_id:
                version = args[i]
                i += 1
            else:
                i += 1

        console.print(f"\n[bold]Executing Tool: {tool_id}[/bold]")
        if version:
            console.print(f"Version: {version}")

        # Execute via runtime
        result = self.runtime.execute(
            tool_id=tool_id,
            version=version or 'latest',
            input_data=input_data
        )

        # Display results
        if result['success']:
            console.print("\n[green]✓ Execution successful[/green]")
            console.print(f"\nResult:")
            console.print(json.dumps(result['result'], indent=2))

            console.print(f"\nMetrics:")
            for key, value in result['metrics'].items():
                console.print(f"  {key}: {value}")

            console.print(f"\nProvenance:")
            console.print(f"  call_id: {result['provenance']['call_id']}")
        else:
            console.print("\n[red]✗ Execution failed[/red]")
            if result.get('errors'):
                for error in result['errors']:
                    console.print(f"  [red]{error}[/red]")

    def cmd_optimize(self, args: List[str]):
        """Optimize workflow (/forge_optimize)."""
        if len(args) < 1:
            console.print("[red]Usage: /forge_optimize <workflow_id> [--runs <n>][/red]")
            return

        workflow_id = args[0]
        runs = 50

        # Parse options
        i = 1
        while i < len(args):
            if args[i] == '--runs' and i + 1 < len(args):
                runs = int(args[i + 1])
                i += 2
            else:
                i += 1

        console.print(f"\n[bold]Optimizing Workflow: {workflow_id}[/bold]")
        console.print(f"Characterization runs: {runs}\n")

        # This would load actual workflow config
        # For demo, show placeholder
        console.print("[yellow]Note: Full workflow optimization requires workflow config[/yellow]")
        console.print("Example workflow structure needed:")
        console.print("""
{
  "tasks": [
    {
      "id": "task1",
      "role": "translator",
      "candidates": [
        {"tool_id": "nmt_v1", "variant_tag": "fast"},
        {"tool_id": "nmt_v2", "variant_tag": "accurate"}
      ]
    }
  ],
  "runs": {"count": 50, "constraints": {...}}
}
        """)

    def cmd_list(self, args: List[str]):
        """List forge tools (/forge_list)."""
        trust_level = None
        tool_type = None
        tags = None

        # Parse options
        i = 0
        while i < len(args):
            if args[i] == '--trust' and i + 1 < len(args):
                trust_level = args[i + 1]
                i += 2
            elif args[i] == '--type' and i + 1 < len(args):
                tool_type = args[i + 1]
                i += 2
            elif args[i] == '--tags' and i + 1 < len(args):
                tags = args[i + 1].split(',')
                i += 2
            else:
                i += 1

        console.print("\n[bold]Forge Registry Tools[/bold]\n")

        # Get tools
        manifests = self.registry.list_tools(
            trust_level=trust_level,
            tool_type=tool_type,
            tags=tags
        )

        if not manifests:
            console.print("[yellow]No tools found[/yellow]")
            return

        # Group by trust level
        core_tools = [m for m in manifests if m.trust.get('level') == 'core']
        third_party = [m for m in manifests if m.trust.get('level') == 'third_party']
        experimental = [m for m in manifests if m.trust.get('level') == 'experimental']

        # Display tables
        for level_name, tools in [
            ("CORE", core_tools),
            ("THIRD_PARTY", third_party),
            ("EXPERIMENTAL", experimental)
        ]:
            if not tools:
                continue

            table = Table(title=f"{level_name} TOOLS ({len(tools)} total)")
            table.add_column("Tool ID", style="cyan")
            table.add_column("Version")
            table.add_column("Type")
            table.add_column("Tags")

            for tool in tools[:10]:  # Limit to 10 per level
                table.add_row(
                    tool.tool_id,
                    tool.version,
                    tool.type,
                    ", ".join(tool.tags[:3])
                )

            console.print(table)
            console.print()


def create_forge_cli(config_manager: ConfigManager) -> ForgeCLI:
    """Create forge CLI instance."""
    return ForgeCLI(config_manager)
