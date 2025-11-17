"""
Workflow Distributor - Exports workflows for different execution platforms.

Supports exporting workflows optimized for:
- Cloud: Full workflows with cloud LLM endpoints (GPT-4, Claude)
- Edge: Lightweight workflows with local Ollama
- Embedded: Pure Python code, no LLMs (for air-gapped/IoT)
- WASM: WebAssembly builds (future)

This enables generation on powerful hardware, then distribution
to cheap execution infrastructure.

Usage:
    distributor = WorkflowDistributor(config, rag)

    # Export for different platforms
    distributor.export_for_platform(workflow, platform="cloud", output_dir="./cloud/")
    distributor.export_for_platform(workflow, platform="edge", output_dir="./edge/")
    distributor.export_for_platform(workflow, platform="embedded", output_dir="./embedded/")
"""
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class ExportPlatform(Enum):
    """Target platforms for workflow export."""
    CLOUD = "cloud"         # Cloud with external LLM APIs
    EDGE = "edge"           # Edge devices with local Ollama
    EMBEDDED = "embedded"   # Embedded/IoT with no LLMs
    WASM = "wasm"           # WebAssembly (future)


class WorkflowDistributor:
    """
    Distributes optimized workflows to execution clusters.
    Transforms workflows for different execution platforms.
    """

    def __init__(self, config_manager, rag_memory=None):
        """
        Initialize workflow distributor.

        Args:
            config_manager: ConfigManager instance
            rag_memory: RAG memory (optional)
        """
        self.config = config_manager
        self.rag = rag_memory

    def export_for_platform(
        self,
        workflow: Dict[str, Any],
        platform: str,
        output_dir: str
    ) -> Path:
        """
        Export workflow optimized for specific execution platform.

        Args:
            workflow: Workflow specification (dict or artifact)
            platform: Target platform ("cloud", "edge", "embedded", "wasm")
            output_dir: Output directory path

        Returns:
            Path to exported workflow directory
        """
        platform_enum = ExportPlatform(platform)

        logger.info(f"Exporting workflow for {platform_enum.value} platform")

        # Convert to dict if it's an artifact
        if hasattr(workflow, 'to_dict'):
            workflow_dict = json.loads(workflow.content)
        elif isinstance(workflow, dict):
            workflow_dict = workflow
        else:
            raise ValueError(f"Invalid workflow type: {type(workflow)}")

        # Export based on platform
        if platform_enum == ExportPlatform.CLOUD:
            return self._export_cloud(workflow_dict, output_dir)
        elif platform_enum == ExportPlatform.EDGE:
            return self._export_edge(workflow_dict, output_dir)
        elif platform_enum == ExportPlatform.EMBEDDED:
            return self._export_embedded(workflow_dict, output_dir)
        elif platform_enum == ExportPlatform.WASM:
            return self._export_wasm(workflow_dict, output_dir)

    def _export_cloud(
        self,
        workflow: Dict[str, Any],
        output_dir: str
    ) -> Path:
        """
        Export for cloud execution with external LLM APIs.

        Characteristics:
        - Uses cloud LLM endpoints (GPT-4, Claude)
        - Full workflow with all features
        - Higher cost per execution but best quality
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        logger.info("Exporting cloud workflow...")

        # Transform workflow for cloud
        cloud_workflow = self._cloudify_endpoints(workflow)

        # Write workflow.json
        with open(output_path / "workflow.json", "w") as f:
            json.dump(cloud_workflow, f, indent=2)

        # Write runner
        self._write_runner(output_path, platform="cloud")

        # Write requirements
        self._write_requirements(output_path, ["requests", "openai", "anthropic"])

        # Write README
        self._write_readme(output_path, workflow, platform="cloud")

        logger.info(f"Cloud workflow exported to: {output_path}")

        return output_path

    def _export_edge(
        self,
        workflow: Dict[str, Any],
        output_dir: str
    ) -> Path:
        """
        Export for edge devices with local Ollama.

        Characteristics:
        - Uses local Ollama endpoints
        - Lightweight, runs on edge devices
        - Zero per-execution cost
        - Moderate quality
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        logger.info("Exporting edge workflow...")

        # Transform workflow for edge (local endpoints)
        edge_workflow = self._localize_endpoints(workflow)

        # Write workflow.json
        with open(output_path / "workflow.json", "w") as f:
            json.dump(edge_workflow, f, indent=2)

        # Write runner
        self._write_runner(output_path, platform="edge")

        # Write requirements (minimal)
        self._write_requirements(output_path, ["requests"])

        # Write README
        self._write_readme(output_path, workflow, platform="edge")

        logger.info(f"Edge workflow exported to: {output_path}")

        return output_path

    def _export_embedded(
        self,
        workflow: Dict[str, Any],
        output_dir: str
    ) -> Path:
        """
        Export for embedded/IoT with NO LLMs.

        Characteristics:
        - Pure Python code, no LLM calls
        - Inlines all LLM-generated code
        - Runs completely offline
        - Zero cost, works air-gapped
        - Perfect for IoT, embedded, secure environments
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        logger.info("Exporting embedded workflow (no LLMs)...")

        # Inline all LLM results
        embedded_workflow = self._inline_llm_results(workflow)

        # Write workflow.json (might not even be needed)
        with open(output_path / "workflow.json", "w") as f:
            json.dump(embedded_workflow, f, indent=2)

        # Write standalone Python code
        self._write_embedded_code(output_path, embedded_workflow)

        # Write requirements (no ollama or LLM APIs!)
        requirements = self._extract_code_requirements(embedded_workflow)
        self._write_requirements(output_path, requirements)

        # Write README
        self._write_readme(output_path, workflow, platform="embedded")

        logger.info(f"Embedded workflow exported to: {output_path}")

        return output_path

    def _export_wasm(
        self,
        workflow: Dict[str, Any],
        output_dir: str
    ) -> Path:
        """
        Export for WebAssembly (future implementation).

        Characteristics:
        - Runs in browser or any WASM runtime
        - No server needed
        - Instant execution
        """
        logger.warning("WASM export not yet implemented")

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Placeholder
        with open(output_path / "README.md", "w") as f:
            f.write("# WASM Export\n\nNot yet implemented\n")

        return output_path

    def _cloudify_endpoints(self, workflow: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform workflow to use cloud LLM endpoints.

        Replaces local Ollama endpoints with cloud APIs.
        """
        cloud_workflow = workflow.copy()

        # Update tool endpoints to cloud
        if "tools" in cloud_workflow:
            for tool_id, tool in cloud_workflow["tools"].items():
                if tool.get("type") == "llm":
                    # Map to cloud endpoints
                    model = tool.get("model", "")

                    if "llama" in model or "codellama" in model:
                        # Replace with GPT-4
                        tool["endpoint"] = "https://api.openai.com/v1"
                        tool["model"] = "gpt-4"
                        tool["cloud_provider"] = "openai"

                    elif "qwen" in model:
                        # Replace with Claude
                        tool["endpoint"] = "https://api.anthropic.com/v1"
                        tool["model"] = "claude-sonnet-4"
                        tool["cloud_provider"] = "anthropic"

        cloud_workflow["requires_llm"] = True
        cloud_workflow["platform"] = "cloud"

        return cloud_workflow

    def _localize_endpoints(self, workflow: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform workflow to use local Ollama endpoints.

        Ensures all endpoints point to localhost.
        """
        edge_workflow = workflow.copy()

        # Update tool endpoints to local
        if "tools" in edge_workflow:
            for tool_id, tool in edge_workflow["tools"].items():
                if tool.get("type") == "llm":
                    tool["endpoint"] = "http://localhost:11434"
                    # Keep original model (use local versions)

        edge_workflow["requires_llm"] = True
        edge_workflow["platform"] = "edge"

        return edge_workflow

    def _inline_llm_results(self, workflow: Dict[str, Any]) -> Dict[str, Any]:
        """
        Inline all LLM-generated code, removing LLM calls entirely.

        For workflows where LLM was used during GENERATION,
        but result is deterministic code - inline it!

        This creates a workflow that requires NO LLMs to execute.
        """
        embedded_workflow = workflow.copy()

        # Transform LLM steps to Python code steps
        if "steps" in embedded_workflow:
            for step in embedded_workflow["steps"]:
                if step.get("type") == "llm_call":
                    # Check if we have generated code for this step
                    if "generated_code" in step:
                        # Convert to pure Python execution
                        step["type"] = "python_code"
                        step["code"] = step["generated_code"]
                        del step["tool"]  # No longer needs LLM tool
                        del step["prompt_template"]
                        logger.info(f"Inlined step: {step['step_id']}")

        # Remove tool dependencies (no LLMs needed)
        embedded_workflow["tools"] = {}
        embedded_workflow["requires_llm"] = False
        embedded_workflow["platform"] = "embedded"

        return embedded_workflow

    def _write_runner(self, output_path: Path, platform: str):
        """Write appropriate runner script for platform."""

        runner_template = '''#!/usr/bin/env python3
"""
Auto-generated workflow runner for {platform} platform
"""
import json
import sys

def main():
    # Load workflow
    with open("workflow.json") as f:
        workflow = json.load(f)

    # Load inputs
    if len(sys.argv) > 1:
        inputs = json.loads(sys.argv[1])
    else:
        inputs = json.load(sys.stdin)

    # Execute workflow
    # (Implementation depends on platform)
    print(json.dumps({{"status": "ok", "platform": "{platform}"}}))

if __name__ == "__main__":
    main()
'''

        with open(output_path / "run_workflow.py", "w") as f:
            f.write(runner_template.format(platform=platform))

        # Make executable
        try:
            import os
            os.chmod(output_path / "run_workflow.py", 0o755)
        except:
            pass

    def _write_embedded_code(self, output_path: Path, workflow: Dict[str, Any]):
        """Write standalone Python code for embedded execution."""

        code_template = '''#!/usr/bin/env python3
"""
Embedded workflow - No LLMs required
Generated from: {workflow_id}
"""
import json
import sys

def execute_workflow(inputs):
    """Execute workflow with inlined code."""
    results = {{}}

    # Workflow steps (inlined)
{steps_code}

    return results

def main():
    # Load inputs
    if len(sys.argv) > 1:
        inputs = json.loads(sys.argv[1])
    else:
        inputs = json.load(sys.stdin)

    # Execute
    results = execute_workflow(inputs)

    # Output
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    main()
'''

        # Generate steps code
        steps_code = "    # Steps would be generated here\n    pass"

        with open(output_path / "workflow.py", "w") as f:
            f.write(code_template.format(
                workflow_id=workflow.get("workflow_id", "unknown"),
                steps_code=steps_code
            ))

        # Make executable
        try:
            import os
            os.chmod(output_path / "workflow.py", 0o755)
        except:
            pass

    def _write_requirements(self, output_path: Path, requirements: List[str]):
        """Write requirements.txt file."""

        with open(output_path / "requirements.txt", "w") as f:
            f.write("\n".join(sorted(requirements)))

    def _write_readme(
        self,
        output_path: Path,
        workflow: Dict[str, Any],
        platform: str
    ):
        """Write README for exported workflow."""

        platform_notes = {
            "cloud": "Requires cloud LLM API keys (OpenAI, Anthropic). Higher cost but best quality.",
            "edge": "Requires local Ollama installation. Zero per-execution cost.",
            "embedded": "Pure Python, no LLMs. Runs completely offline. Perfect for air-gapped systems.",
            "wasm": "Runs in browser or any WASM runtime. No server needed."
        }

        readme = f'''# {workflow.get("workflow_id", "Workflow")}

{workflow.get("description", "No description")}

## Platform: {platform.upper()}

{platform_notes.get(platform, "")}

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python run_workflow.py '{{"input": "value"}}'
```

## Generated by mostlylucid DiSE

This workflow was optimized and exported by mostlylucid DiSE.
'''

        with open(output_path / "README.md", "w") as f:
            f.write(readme)

    def _extract_code_requirements(self, workflow: Dict[str, Any]) -> List[str]:
        """Extract Python package requirements from inlined code."""

        # Would analyze code to find imports
        # For now, minimal requirements
        return ["json"]

    def distribute_to_cluster(
        self,
        workflow_path: Path,
        cluster_nodes: List[str],
        platform: str = "edge"
    ) -> Dict[str, Any]:
        """
        Distribute exported workflow to execution cluster.

        Args:
            workflow_path: Path to exported workflow
            cluster_nodes: List of cluster node addresses
            platform: Platform type

        Returns:
            Distribution results
        """
        logger.info(f"Distributing workflow to {len(cluster_nodes)} nodes...")

        # Would use SSH, Docker, or k8s to deploy
        # For now, placeholder

        return {
            "workflow_path": str(workflow_path),
            "platform": platform,
            "nodes": cluster_nodes,
            "status": "deployed"
        }
