#!/usr/bin/env python3
"""
Workflow Exporter

Packages a workflow.json into a standalone Python application that can run anywhere.

Usage:
    python export_workflow.py workflow.json --output ./exported_app/

Output structure:
    exported_app/
    ├── run_workflow.py      # Main executable
    ├── workflow.json        # Workflow specification
    ├── requirements.txt     # Python dependencies
    └── README.md            # Usage instructions
"""
import json
import argparse
from pathlib import Path
from typing import Dict, Any


WORKFLOW_RUNNER_TEMPLATE = '''#!/usr/bin/env python3
"""
Auto-generated workflow runner
Generated from: {workflow_id}
"""
import json
import sys
import requests
from typing import Any, Dict

class WorkflowRunner:
    """Executes workflow steps"""

    def __init__(self, workflow_file: str):
        with open(workflow_file) as f:
            self.workflow = json.load(f)

        if not self.workflow.get("portable"):
            raise ValueError("This workflow is not portable. Use --portable mode when generating.")

        self.tools = self.workflow.get("tools", {{}})
        self.results = {{}}

    def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the workflow"""
        self._validate_inputs(inputs)
        self.results["inputs"] = inputs
        self.results["steps"] = {{}}

        for step in self.workflow["steps"]:
            step_id = step["step_id"]
            print(f"Executing: {{step['description']}}", file=sys.stderr)

            # Map inputs from previous steps
            step_inputs = self._map_inputs(step["input_mapping"])

            # Execute based on type
            if step["type"] == "llm_call":
                output = self._execute_llm(step, step_inputs)
            elif step["type"] == "python_tool":
                output = self._execute_python(step, step_inputs)
            else:
                raise ValueError(f"Unknown step type: {{step['type']}}")

            # Store output
            self.results["steps"][step_id] = {{step["output_name"]: output}}

        # Extract final outputs
        return self._extract_outputs()

    def _execute_llm(self, step: dict, inputs: dict) -> str:
        """Call LLM tool"""
        tool_name = step["tool"]

        if tool_name not in self.tools:
            raise ValueError(f"Tool not found: {{tool_name}}")

        tool = self.tools[tool_name]

        # Format prompt
        prompt_template = step["prompt_template"]
        prompt = prompt_template.format(**inputs)

        # Call Ollama API
        endpoint = tool.get("endpoint", "http://localhost:11434")
        model = tool["model"]
        system_prompt = tool.get("system_prompt", "")
        temperature = tool.get("temperature", 0.7)
        timeout = tool.get("timeout", 120)

        try:
            response = requests.post(
                f"{{endpoint}}/api/generate",
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
            # Try fallback tool if configured
            fallback = tool.get("fallback_tool")
            if fallback and fallback in self.tools:
                print(f"Tool {{tool_name}} failed, using fallback {{fallback}}", file=sys.stderr)
                step["tool"] = fallback
                return self._execute_llm(step, inputs)
            else:
                raise RuntimeError(f"LLM call failed: {{e}}")

    def _execute_python(self, step: dict, inputs: dict) -> Any:
        """Execute Python tool (from embedded source)"""
        tool_path = step["tool_path"]

        # In portable mode, Python tools would be extracted to files
        # For now, just raise an error
        raise NotImplementedError("Python tool execution not yet implemented in portable mode")

    def _map_inputs(self, input_mapping: dict) -> dict:
        """Map inputs from previous steps"""
        mapped = {{}}

        for key, ref in input_mapping.items():
            if isinstance(ref, list):
                mapped[key] = [self._resolve_reference(r) for r in ref]
            else:
                mapped[key] = self._resolve_reference(ref)

        return mapped

    def _resolve_reference(self, ref: str) -> Any:
        """Resolve reference like 'inputs.topic' or 'steps.outline.output'"""
        parts = ref.split(".")
        current = self.results

        for part in parts:
            current = current[part]

        return current

    def _validate_inputs(self, inputs: dict):
        """Validate required inputs"""
        for name, spec in self.workflow["inputs"].items():
            if spec.get("required", False) and name not in inputs:
                raise ValueError(f"Missing required input: {{name}}")

            # Apply defaults
            if name not in inputs and "default" in spec:
                inputs[name] = spec["default"]

    def _extract_outputs(self) -> dict:
        """Extract final outputs"""
        outputs = {{}}

        for name, spec in self.workflow["outputs"].items():
            ref = spec["source_reference"]
            outputs[name] = self._resolve_reference(ref)

        return outputs

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Run workflow")
    parser.add_argument("--input", help="Input JSON string")
    parser.add_argument("--input-file", help="Input JSON file")

    args = parser.parse_args()

    # Load inputs
    if args.input:
        inputs = json.loads(args.input)
    elif args.input_file:
        with open(args.input_file) as f:
            inputs = json.load(f)
    else:
        inputs = json.load(sys.stdin)

    # Run workflow
    runner = WorkflowRunner("workflow.json")
    outputs = runner.run(inputs)

    # Print outputs
    print(json.dumps(outputs, indent=2))

if __name__ == "__main__":
    main()
'''

README_TEMPLATE = '''# {workflow_id}

{description}

## Requirements

- Python 3.7+
- Access to Ollama API endpoint (default: http://localhost:11434)

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Run with JSON input:

```bash
python run_workflow.py --input '{{"topic": "Your Topic"}}'
```

### Run with input file:

```bash
python run_workflow.py --input-file inputs.json
```

### Run with stdin:

```bash
echo '{{"topic": "Your Topic"}}' | python run_workflow.py
```

## Inputs

{inputs_doc}

## Outputs

{outputs_doc}

## Tools Used

{tools_doc}

## Generated by mostlylucid DiSE

This workflow was automatically generated by mostlylucid DiSE.
'''


def export_workflow(workflow_path: str, output_dir: str):
    """Export workflow as standalone app"""

    # Load workflow
    with open(workflow_path) as f:
        workflow = json.load(f)

    if not workflow.get("portable"):
        print("WARNING: Workflow is not marked as portable. Tool definitions may be missing.")

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Copy workflow.json
    with open(output_path / "workflow.json", "w") as f:
        json.dump(workflow, f, indent=2)

    # Generate run_workflow.py
    runner_code = WORKFLOW_RUNNER_TEMPLATE.format(
        workflow_id=workflow["workflow_id"]
    )
    with open(output_path / "run_workflow.py", "w") as f:
        f.write(runner_code)

    # Make executable on Unix
    try:
        import os
        os.chmod(output_path / "run_workflow.py", 0o755)
    except:
        pass

    # Generate requirements.txt
    requirements = ["requests"]  # Base requirement

    # Add requirements from embedded tools
    for tool in workflow.get("tools", {}).values():
        tool_reqs = tool.get("requirements", [])
        requirements.extend(tool_reqs)

    with open(output_path / "requirements.txt", "w") as f:
        f.write("\\n".join(sorted(set(requirements))))

    # Generate README.md
    readme = README_TEMPLATE.format(
        workflow_id=workflow["workflow_id"],
        description=workflow["description"],
        inputs_doc=_format_inputs_doc(workflow.get("inputs", {})),
        outputs_doc=_format_outputs_doc(workflow.get("outputs", {})),
        tools_doc=_format_tools_doc(workflow.get("tools", {}))
    )

    with open(output_path / "README.md", "w") as f:
        f.write(readme)

    print(f"OK Exported to: {output_path}")
    print(f"  - run_workflow.py")
    print(f"  - workflow.json")
    print(f"  - requirements.txt")
    print(f"  - README.md")


def _format_inputs_doc(inputs: dict) -> str:
    """Format inputs for README"""
    lines = []
    for name, spec in inputs.items():
        required = "**Required**" if spec.get("required") else "Optional"
        default = f" (default: `{spec['default']}`)" if "default" in spec else ""
        lines.append(f"- `{name}` ({spec['type']}) - {required}{default}")
        if spec.get("description"):
            lines.append(f"  {spec['description']}")
    return "\\n".join(lines) if lines else "No inputs"


def _format_outputs_doc(outputs: dict) -> str:
    """Format outputs for README"""
    lines = []
    for name, spec in outputs.items():
        lines.append(f"- `{name}` ({spec['type']})")
        if spec.get("description"):
            lines.append(f"  {spec['description']}")
    return "\\n".join(lines) if lines else "No outputs"


def _format_tools_doc(tools: dict) -> str:
    """Format tools for README"""
    lines = []
    for tool_id, tool in tools.items():
        lines.append(f"### {tool['name']}")
        lines.append(f"{tool['description']}")
        lines.append(f"- **Type**: {tool['type']}")
        if tool.get("model"):
            lines.append(f"- **Model**: {tool['model']}")
        if tool.get("endpoint"):
            lines.append(f"- **Endpoint**: {tool['endpoint']}")
        lines.append("")
    return "\\n".join(lines) if lines else "No tools"


def main():
    parser = argparse.ArgumentParser(description="Export workflow as standalone app")
    parser.add_argument("workflow", help="Path to workflow.json")
    parser.add_argument("--output", "-o", default="./exported_workflow",
                        help="Output directory (default: ./exported_workflow)")
    parser.add_argument("--platform", "-p", choices=["cloud", "edge", "embedded", "wasm"],
                        default="edge",
                        help="Target platform (default: edge)")

    args = parser.parse_args()

    # Use new workflow_distributor if platform is specified
    if args.platform and args.platform != "edge":
        try:
            from code_evolver.src.workflow_distributor import WorkflowDistributor
            from code_evolver.src.config_manager import ConfigManager

            # Load config
            config = ConfigManager()

            # Create distributor
            distributor = WorkflowDistributor(config)

            # Load workflow
            with open(args.workflow) as f:
                workflow = json.load(f)

            # Export for platform
            output_path = distributor.export_for_platform(
                workflow,
                platform=args.platform,
                output_dir=args.output
            )

            print(f"OK Exported for {args.platform} platform to: {output_path}")

        except ImportError:
            print("WARNING: workflow_distributor not available, using legacy export")
            export_workflow(args.workflow, args.output)
    else:
        # Use legacy export
        export_workflow(args.workflow, args.output)


if __name__ == "__main__":
    main()
