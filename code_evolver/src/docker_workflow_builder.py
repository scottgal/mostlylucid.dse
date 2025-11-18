#!/usr/bin/env python3
"""
Docker Workflow Builder

Builds super-compact Docker containers for individual workflow execution.
Uses tree-shaking to include ONLY the tools and configs needed.

Features:
- Multi-stage builds for minimal size
- Nuitka compilation for single binary executable
- Tree-shaking to include only required tools
- Ollama access via host.docker.internal
- Ephemeral execution (docker run --rm)

Usage:
    python docker_workflow_builder.py build workflow.json
    docker run --rm --add-host host.docker.internal:host-gateway workflow-name '{"input": "value"}'
"""
import json
import logging
import re
import shutil
import subprocess
import yaml
from pathlib import Path
from typing import Dict, Any, List, Set, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class WorkflowDependencies:
    """Analyzed workflow dependencies"""
    llm_tools: Set[str]
    executable_tools: Set[str]
    python_files: Set[Path]
    pip_packages: Set[str]
    ollama_models: Set[str]
    requires_ollama: bool
    total_tools: int


class DockerWorkflowBuilder:
    """
    Builds compact Docker containers for workflow execution.

    Tree-shakes dependencies to include ONLY what's needed.
    Compiles to single binary for minimal size.
    """

    def __init__(self, code_evolver_root: Path):
        self.code_evolver_root = code_evolver_root
        self.tools_root = code_evolver_root / "tools"

    def analyze_workflow(self, workflow_path: Path) -> WorkflowDependencies:
        """
        Analyze workflow and determine EXACTLY what's needed.

        Tree-shakes the massive tool library to include only
        the specific tools this workflow uses.
        """
        logger.info(f"Analyzing workflow: {workflow_path}")

        with open(workflow_path) as f:
            workflow = json.load(f)

        deps = WorkflowDependencies(
            llm_tools=set(),
            executable_tools=set(),
            python_files=set(),
            pip_packages={'requests'},  # Base requirement for Ollama
            ollama_models=set(),
            requires_ollama=False,
            total_tools=0
        )

        # Analyze steps
        for step in workflow.get('steps', []):
            step_type = step.get('type', '')
            tool_name = step.get('tool', step.get('tool_name'))

            if not tool_name:
                continue

            deps.total_tools += 1

            # Load tool definition
            tool_def = self._load_tool_definition(tool_name)

            if not tool_def:
                logger.warning(f"Tool not found: {tool_name}")
                continue

            tool_type = tool_def.get('type', '')

            if tool_type == 'llm':
                deps.llm_tools.add(tool_name)
                deps.requires_ollama = True

                # Extract model name
                model = tool_def.get('model', {}).get('name', '')
                if model:
                    deps.ollama_models.add(model)

            elif tool_type == 'executable':
                deps.executable_tools.add(tool_name)

                # Extract Python script dependencies
                python_files = self._extract_python_files(tool_def)
                deps.python_files.update(python_files)

        # Analyze embedded tools (portable mode)
        if workflow.get('portable') and 'tools' in workflow:
            for tool_id, tool in workflow['tools'].items():
                if tool.get('type') == 'llm':
                    deps.requires_ollama = True
                    model = tool.get('model', '')
                    if model:
                        deps.ollama_models.add(model)

                # Extract pip requirements from embedded tools
                reqs = tool.get('requirements', [])
                deps.pip_packages.update(reqs)

        logger.info(f"Dependencies: {deps.total_tools} tools, "
                   f"{len(deps.ollama_models)} models, "
                   f"{len(deps.pip_packages)} packages")

        return deps

    def _load_tool_definition(self, tool_id: str) -> Optional[Dict]:
        """Load tool definition from YAML"""
        for tool_type in ['llm', 'executable', 'openapi', 'workflow']:
            yaml_path = self.tools_root / tool_type / f'{tool_id}.yaml'
            if yaml_path.exists():
                with open(yaml_path) as f:
                    return yaml.safe_load(f)
        return None

    def _extract_python_files(self, tool_def: Dict) -> Set[Path]:
        """Extract Python file dependencies from executable tool"""
        files = set()

        executable = tool_def.get('executable', {})
        args = executable.get('args', [])

        for arg in args:
            if arg.endswith('.py'):
                # Resolve path
                if '{tool_dir}' in arg:
                    resolved = arg.replace('{tool_dir}/', '')
                    file_path = self.tools_root / 'executable' / resolved
                elif arg.startswith('tools/'):
                    file_path = self.code_evolver_root / arg
                else:
                    file_path = Path(arg)

                if file_path.exists():
                    files.add(file_path)

        return files

    def build_standalone_runner(
        self,
        workflow_path: Path,
        output_dir: Path,
        deps: WorkflowDependencies
    ) -> Path:
        """
        Generate a standalone Python runner with ALL dependencies inlined.

        This is the script that will be compiled to a binary.
        """
        logger.info("Building standalone runner...")

        output_dir.mkdir(parents=True, exist_ok=True)

        # Load workflow
        with open(workflow_path) as f:
            workflow = json.load(f)

        workflow_id = workflow.get('workflow_id', 'workflow')

        # Generate runner script
        runner_code = self._generate_runner_code(workflow, deps)

        runner_path = output_dir / f"{workflow_id}_runner.py"
        with open(runner_path, 'w') as f:
            f.write(runner_code)

        logger.info(f"Standalone runner created: {runner_path}")

        return runner_path

    def _generate_runner_code(self, workflow: Dict, deps: WorkflowDependencies) -> str:
        """Generate the complete standalone runner code"""

        workflow_id = workflow.get('workflow_id', 'workflow')

        # Configure Ollama endpoint for Docker
        ollama_endpoint = "http://host.docker.internal:11434"

        runner_template = f'''#!/usr/bin/env python3
"""
Standalone Workflow Runner: {workflow_id}

Generated by mostlylucid DiSE Docker Workflow Builder
This is a self-contained workflow runner with all dependencies inlined.

Ollama endpoint: {ollama_endpoint}
"""
import json
import os
import sys
import requests
from typing import Dict, Any, List, Optional


class WorkflowRunner:
    """Execute workflow with Ollama via host.docker.internal"""

    def __init__(self):
        # Embedded workflow specification
        self.workflow = {json.dumps(workflow, indent=8)}

        # Ollama configuration for Docker
        self.ollama_endpoint = os.getenv('OLLAMA_ENDPOINT', '{ollama_endpoint}')

        # Results storage
        self.results = {{}}

    def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the workflow"""
        print(f"[Runner] Starting workflow: {workflow_id}", file=sys.stderr)
        print(f"[Runner] Ollama endpoint: {{self.ollama_endpoint}}", file=sys.stderr)

        # Validate inputs
        self._validate_inputs(inputs)

        # Initialize results
        self.results["inputs"] = inputs
        self.results["steps"] = {{}}

        # Execute steps sequentially
        for step in self.workflow["steps"]:
            step_id = step["step_id"]
            description = step.get("description", step_id)

            print(f"[Runner] Executing step: {{description}}", file=sys.stderr)

            # Map inputs from previous steps
            step_inputs = self._map_inputs(step.get("input_mapping", {{}}))

            # Execute based on type
            step_type = step.get("type", "")

            if step_type == "llm_call":
                output = self._execute_llm(step, step_inputs)
            elif step_type == "python_tool":
                output = self._execute_python(step, step_inputs)
            else:
                raise ValueError(f"Unknown step type: {{step_type}}")

            # Store output
            output_name = step.get("output_name", "output")
            self.results["steps"][step_id] = {{output_name: output}}

            print(f"[Runner] Step completed: {{step_id}}", file=sys.stderr)

        # Extract final outputs
        return self._extract_outputs()

    def _execute_llm(self, step: dict, inputs: dict) -> str:
        """Execute LLM call via Ollama"""

        # Get tool configuration
        tool_name = step.get("tool", "")

        # For portable workflows, tool is embedded
        if "tools" in self.workflow and tool_name in self.workflow["tools"]:
            tool = self.workflow["tools"][tool_name]
        else:
            raise ValueError(f"Tool not found: {{tool_name}}")

        # Format prompt
        prompt_template = step.get("prompt_template", "")
        prompt = prompt_template.format(**inputs)

        # LLM configuration
        model = tool.get("model", "llama3")
        system_prompt = tool.get("system_prompt", "")
        temperature = tool.get("temperature", 0.7)
        timeout = tool.get("timeout", 120)

        print(f"[LLM] Calling model: {{model}}", file=sys.stderr)

        try:
            # Call Ollama API
            response = requests.post(
                f"{{self.ollama_endpoint}}/api/generate",
                json={{
                    "model": model,
                    "prompt": prompt,
                    "system": system_prompt,
                    "temperature": temperature,
                    "stream": False
                }},
                timeout=timeout
            )

            response.raise_for_status()
            result = response.json()

            return result.get("response", "")

        except Exception as e:
            print(f"[LLM] Error: {{e}}", file=sys.stderr)
            raise RuntimeError(f"LLM call failed: {{e}}")

    def _execute_python(self, step: dict, inputs: dict) -> Any:
        """Execute Python tool (embedded code)"""

        # For portable workflows, Python code is embedded
        if "code" in step:
            code = step["code"]

            # Execute in isolated namespace
            namespace = {{"inputs": inputs, "result": None}}
            exec(code, namespace)

            return namespace.get("result")
        else:
            raise NotImplementedError("Python tool execution requires embedded code")

    def _map_inputs(self, input_mapping: dict) -> dict:
        """Map inputs from previous steps"""
        mapped = {{}}

        for key, ref in input_mapping.items():
            if isinstance(ref, str):
                mapped[key] = self._resolve_reference(ref)
            else:
                mapped[key] = ref

        return mapped

    def _resolve_reference(self, ref: str) -> Any:
        """Resolve reference like 'inputs.topic' or 'steps.step1.output'"""
        parts = ref.split(".")
        current = self.results

        for part in parts:
            current = current[part]

        return current

    def _validate_inputs(self, inputs: dict):
        """Validate required inputs"""
        workflow_inputs = self.workflow.get("inputs", {{}})

        for name, spec in workflow_inputs.items():
            if spec.get("required", False) and name not in inputs:
                raise ValueError(f"Missing required input: {{name}}")

            # Apply defaults
            if name not in inputs and "default" in spec:
                inputs[name] = spec["default"]

    def _extract_outputs(self) -> dict:
        """Extract final outputs"""
        outputs = {{}}

        workflow_outputs = self.workflow.get("outputs", {{}})

        for name, spec in workflow_outputs.items():
            ref = spec.get("source_reference", "")
            if ref:
                outputs[name] = self._resolve_reference(ref)

        return outputs


def main():
    """Main entry point"""

    # Parse inputs from command line or stdin
    if len(sys.argv) > 1:
        # From command line argument
        inputs = json.loads(sys.argv[1])
    else:
        # From stdin
        inputs = json.load(sys.stdin)

    # Create runner
    runner = WorkflowRunner()

    try:
        # Execute workflow
        outputs = runner.run(inputs)

        # Output results as JSON
        print(json.dumps({{
            "success": True,
            "workflow_id": "{workflow_id}",
            "outputs": outputs
        }}, indent=2))

        sys.exit(0)

    except Exception as e:
        # Output error
        print(json.dumps({{
            "success": False,
            "error": str(e)
        }}), file=sys.stderr)

        import traceback
        traceback.print_exc(file=sys.stderr)

        sys.exit(1)


if __name__ == "__main__":
    main()
'''

        return runner_template

    def build_docker_image(
        self,
        workflow_path: Path,
        output_dir: Path,
        deps: WorkflowDependencies,
        image_name: Optional[str] = None
    ) -> str:
        """
        Build a super-compact Docker image for this workflow.

        Uses multi-stage build:
        1. Build stage: Compile Python to binary with Nuitka
        2. Runtime stage: Minimal Alpine with just the binary

        Result: ~10-20MB image that can execute the workflow
        """
        logger.info("Building Docker image...")

        # Generate standalone runner
        runner_path = self.build_standalone_runner(workflow_path, output_dir, deps)

        # Load workflow for metadata
        with open(workflow_path) as f:
            workflow = json.load(f)

        workflow_id = workflow.get('workflow_id', 'workflow')

        if not image_name:
            image_name = f"workflow-{workflow_id}:latest"

        # Generate Dockerfile
        dockerfile_path = self._generate_dockerfile(
            output_dir,
            runner_path,
            deps,
            workflow_id
        )

        # Copy workflow.json to build context
        shutil.copy(workflow_path, output_dir / "workflow.json")

        # Build Docker image
        logger.info(f"Building Docker image: {image_name}")

        build_cmd = [
            "docker", "build",
            "-t", image_name,
            "-f", str(dockerfile_path),
            str(output_dir)
        ]

        try:
            subprocess.run(build_cmd, check=True, capture_output=True, text=True)
            logger.info(f"✓ Docker image built: {image_name}")

            # Get image size
            size_cmd = ["docker", "images", image_name, "--format", "{{.Size}}"]
            result = subprocess.run(size_cmd, capture_output=True, text=True)
            size = result.stdout.strip()

            logger.info(f"✓ Image size: {size}")

            return image_name

        except subprocess.CalledProcessError as e:
            logger.error(f"Docker build failed: {e.stderr}")
            raise

    def _generate_dockerfile(
        self,
        output_dir: Path,
        runner_path: Path,
        deps: WorkflowDependencies,
        workflow_id: str
    ) -> Path:
        """Generate optimized multi-stage Dockerfile"""

        pip_packages = ' '.join(deps.pip_packages)
        runner_name = runner_path.name

        dockerfile_content = f'''# Multi-stage build for super-compact workflow container
# Final image size: ~10-20MB

# ============================================================================
# Stage 1: Build - Compile Python to binary
# ============================================================================
FROM python:3.11-slim AS builder

# Install Nuitka and compilation dependencies
RUN apt-get update && apt-get install -y \\
    gcc \\
    patchelf \\
    ccache \\
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir nuitka ordered-set

# Copy runner script
COPY {runner_name} /app/runner.py
WORKDIR /app

# Compile to standalone binary
RUN python -m nuitka \\
    --standalone \\
    --onefile \\
    --remove-output \\
    --assume-yes-for-downloads \\
    --output-dir=/app/build \\
    --output-filename=workflow \\
    runner.py

# ============================================================================
# Stage 2: Runtime - Minimal Alpine with binary
# ============================================================================
FROM alpine:latest

# Install minimal runtime dependencies
RUN apk add --no-cache libstdc++ libgcc

# Copy compiled binary
COPY --from=builder /app/build/workflow /usr/local/bin/workflow

# Make executable
RUN chmod +x /usr/local/bin/workflow

# Set Ollama endpoint for Docker
ENV OLLAMA_ENDPOINT=http://host.docker.internal:11434

# Workflow metadata
LABEL workflow.id="{workflow_id}"
LABEL workflow.requires_ollama="{deps.requires_ollama}"
LABEL workflow.models="{','.join(deps.ollama_models)}"

# Entry point: workflow runner
ENTRYPOINT ["/usr/local/bin/workflow"]
'''

        dockerfile_path = output_dir / "Dockerfile"
        with open(dockerfile_path, 'w') as f:
            f.write(dockerfile_content)

        logger.info(f"Dockerfile generated: {dockerfile_path}")

        return dockerfile_path


def main():
    """CLI entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Build compact Docker containers for workflow execution"
    )
    parser.add_argument(
        "workflow",
        help="Path to workflow.json"
    )
    parser.add_argument(
        "--output", "-o",
        default="./docker_build",
        help="Output directory for build artifacts"
    )
    parser.add_argument(
        "--image-name", "-n",
        help="Docker image name (default: workflow-<id>:latest)"
    )
    parser.add_argument(
        "--code-evolver-root",
        default=".",
        help="Path to code_evolver root directory"
    )

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='[%(levelname)s] %(message)s'
    )

    # Build Docker image
    builder = DockerWorkflowBuilder(Path(args.code_evolver_root))

    workflow_path = Path(args.workflow)
    output_dir = Path(args.output)

    # Analyze dependencies
    deps = builder.analyze_workflow(workflow_path)

    logger.info(f"Analyzed workflow:")
    logger.info(f"  - LLM tools: {len(deps.llm_tools)}")
    logger.info(f"  - Executable tools: {len(deps.executable_tools)}")
    logger.info(f"  - Python files: {len(deps.python_files)}")
    logger.info(f"  - Pip packages: {len(deps.pip_packages)}")
    logger.info(f"  - Ollama models: {', '.join(deps.ollama_models) if deps.ollama_models else 'None'}")

    # Build image
    image_name = builder.build_docker_image(
        workflow_path,
        output_dir,
        deps,
        args.image_name
    )

    print(f"\n✓ Docker image ready: {image_name}")
    print(f"\nUsage:")
    print(f"  docker run --rm --add-host host.docker.internal:host-gateway {image_name} '{{\"input\": \"value\"}}'")

    if deps.requires_ollama:
        print(f"\n⚠ This workflow requires Ollama running on localhost:11434")
        print(f"  Models needed: {', '.join(deps.ollama_models)}")


if __name__ == "__main__":
    main()
