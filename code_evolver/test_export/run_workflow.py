#!/usr/bin/env python3
"""
Auto-generated workflow runner
Generated from: article_writer_portable
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

        self.tools = self.workflow.get("tools", {})
        self.results = {}

    def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the workflow"""
        self._validate_inputs(inputs)
        self.results["inputs"] = inputs
        self.results["steps"] = {}

        for step in self.workflow["steps"]:
            step_id = step["step_id"]
            print(f"Executing: {step['description']}", file=sys.stderr)

            # Map inputs from previous steps
            step_inputs = self._map_inputs(step["input_mapping"])

            # Execute based on type
            if step["type"] == "llm_call":
                output = self._execute_llm(step, step_inputs)
            elif step["type"] == "python_tool":
                output = self._execute_python(step, step_inputs)
            else:
                raise ValueError(f"Unknown step type: {step['type']}")

            # Store output
            self.results["steps"][step_id] = {step["output_name"]: output}

        # Extract final outputs
        return self._extract_outputs()

    def _execute_llm(self, step: dict, inputs: dict) -> str:
        """Call LLM tool"""
        tool_name = step["tool"]

        if tool_name not in self.tools:
            raise ValueError(f"Tool not found: {tool_name}")

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
                f"{endpoint}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "system": system_prompt,
                    "temperature": temperature,
                    "stream": False
                },
                timeout=timeout
            )
            response.raise_for_status()

            result = response.json()
            return result.get("response", "")

        except Exception as e:
            # Try fallback tool if configured
            fallback = tool.get("fallback_tool")
            if fallback and fallback in self.tools:
                print(f"Tool {tool_name} failed, using fallback {fallback}", file=sys.stderr)
                step["tool"] = fallback
                return self._execute_llm(step, inputs)
            else:
                raise RuntimeError(f"LLM call failed: {e}")

    def _execute_python(self, step: dict, inputs: dict) -> Any:
        """Execute Python tool (from embedded source)"""
        tool_path = step["tool_path"]

        # In portable mode, Python tools would be extracted to files
        # For now, just raise an error
        raise NotImplementedError("Python tool execution not yet implemented in portable mode")

    def _map_inputs(self, input_mapping: dict) -> dict:
        """Map inputs from previous steps"""
        mapped = {}

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
                raise ValueError(f"Missing required input: {name}")

            # Apply defaults
            if name not in inputs and "default" in spec:
                inputs[name] = spec["default"]

    def _extract_outputs(self) -> dict:
        """Extract final outputs"""
        outputs = {}

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
