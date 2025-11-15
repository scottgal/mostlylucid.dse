"""
Workflow Builder

Converts overseer output into structured WorkflowSpec objects.
Handles both simple (single-step) and complex (multi-step) workflows.
"""
import json
import re
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from .workflow_spec import (
    WorkflowSpec, WorkflowStep, WorkflowInput, WorkflowOutput,
    ToolDefinition, StepType, OperationType,
    create_simple_workflow
)


class WorkflowBuilder:
    """Builds WorkflowSpec from overseer output"""

    def __init__(self, tools_manager=None):
        """
        Initialize builder.

        Args:
            tools_manager: Optional ToolsManager for looking up existing tools
        """
        self.tools_manager = tools_manager

    def build_from_text(self, description: str, overseer_output: str,
                        task_id: str = None) -> WorkflowSpec:
        """
        Build workflow from overseer's text output.

        Args:
            description: User's original task description
            overseer_output: Overseer's planning output
            task_id: Optional workflow ID (generated if not provided)

        Returns:
            WorkflowSpec object
        """
        # Try to parse as JSON first
        try:
            workflow_dict = self._extract_json(overseer_output)
            if workflow_dict:
                return self._build_from_json(workflow_dict, description, task_id)
        except:
            pass

        # Fallback: Parse as text and infer workflow structure
        return self._build_from_text_analysis(description, overseer_output, task_id)

    def build_from_json(self, json_str: str, description: str = None,
                       task_id: str = None) -> WorkflowSpec:
        """
        Build workflow from JSON string.

        Args:
            json_str: JSON workflow specification
            description: Optional description override
            task_id: Optional workflow ID override

        Returns:
            WorkflowSpec object
        """
        workflow_dict = json.loads(json_str)
        return self._build_from_json(workflow_dict, description, task_id)

    def create_simple_workflow(self, description: str, task_id: str = None,
                               tool_name: str = "content_generator") -> WorkflowSpec:
        """
        Create a simple single-step workflow.

        Args:
            description: Task description
            task_id: Optional workflow ID
            tool_name: Tool to use (default: content_generator)

        Returns:
            WorkflowSpec with single LLM call step
        """
        if not task_id:
            task_id = self._generate_task_id(description)

        workflow = create_simple_workflow(task_id, description)

        # Add input
        workflow.add_input(
            name="description",
            type="string",
            required=True,
            description="Task description"
        )

        # Add single step
        workflow.add_step(WorkflowStep(
            step_id="execute",
            step_type=StepType.LLM_CALL,
            description=description,
            tool_name=tool_name,
            prompt_template="{description}",
            input_mapping={"description": "inputs.description"},
            output_name="result"
        ))

        # Add output
        workflow.add_output(
            name="result",
            type="string",
            source_reference="steps.execute.result",
            description="Task result"
        )

        return workflow

    def _extract_json(self, text: str) -> Optional[dict]:
        """Extract JSON from text (may be wrapped in markdown, etc)"""
        # Remove markdown code fences
        text = text.strip()
        if text.startswith('```json'):
            text = text.split('```json')[1].split('```')[0].strip()
        elif text.startswith('```'):
            text = text.split('```')[1].split('```')[0].strip()

        # Try to find JSON object
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except:
                pass

        return None

    def _build_from_json(self, workflow_dict: dict, description: str = None,
                        task_id: str = None) -> WorkflowSpec:
        """Build workflow from parsed JSON dictionary"""

        # Use provided task_id or extract from dict or generate
        workflow_id = task_id or workflow_dict.get("workflow_id") or self._generate_task_id(description or "workflow")

        # Use provided description or extract from dict
        desc = description or workflow_dict.get("description", "Generated workflow")

        # Parse inputs
        inputs = []
        for name, spec in workflow_dict.get("inputs", {}).items():
            inputs.append(WorkflowInput(
                name=name,
                type=spec.get("type", "string"),
                required=spec.get("required", True),
                default=spec.get("default"),
                description=spec.get("description", "")
            ))

        # Parse outputs
        outputs = []
        for name, spec in workflow_dict.get("outputs", {}).items():
            outputs.append(WorkflowOutput(
                name=name,
                type=spec.get("type", "string"),
                source_reference=spec.get("source_reference", ""),
                description=spec.get("description", "")
            ))

        # Parse steps
        steps = []
        for step_data in workflow_dict.get("steps", []):
            steps.append(self._parse_step(step_data))

        # Create workflow
        workflow = WorkflowSpec(
            workflow_id=workflow_id,
            description=desc,
            version=workflow_dict.get("version", "1.0.0"),
            portable=workflow_dict.get("portable", False),
            inputs=inputs,
            outputs=outputs,
            steps=steps,
            created_at=datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            tags=workflow_dict.get("tags", [])
        )

        # Parse tool definitions if portable
        if workflow.portable and "tools" in workflow_dict:
            for tool_id, tool_data in workflow_dict["tools"].items():
                workflow.add_tool_definition(ToolDefinition.from_dict(tool_data))

        return workflow

    def _build_from_text_analysis(self, description: str, overseer_output: str,
                                  task_id: str = None) -> WorkflowSpec:
        """
        Build workflow by analyzing text output.
        This is a fallback when overseer doesn't return JSON.
        """
        if not task_id:
            task_id = self._generate_task_id(description)

        # For now, create a simple workflow
        # In the future, this could use NLP to extract steps from text
        workflow = self.create_simple_workflow(description, task_id)

        # Store the overseer's plan as metadata
        workflow.tags.append("text_based")

        return workflow

    def _parse_step(self, step_data: dict) -> WorkflowStep:
        """Parse a single workflow step from dictionary"""

        step_type_str = step_data.get("type", "llm_call")
        step_type = StepType(step_type_str)

        operation_type = None
        if "operation_type" in step_data:
            operation_type = OperationType(step_data["operation_type"])

        # Create the WorkflowStep
        step = WorkflowStep(
            step_id=step_data["step_id"],
            step_type=step_type,
            description=step_data.get("description", ""),
            tool_name=step_data.get("tool"),
            prompt_template=step_data.get("prompt_template"),
            tool_path=step_data.get("tool_path"),
            generate_tool=step_data.get("generate_tool", False),
            operation_type=operation_type,
            workflow_path=step_data.get("workflow_path"),
            input_mapping=step_data.get("input_mapping", {}),
            output_name=step_data.get("output_name", "output"),
            timeout=step_data.get("timeout", 300),
            retry_on_failure=step_data.get("retry_on_failure", False),
            max_retries=step_data.get("max_retries", 3)
        )

        # Add custom field for granular task description
        if "task_for_node" in step_data:
            step.task_for_node = step_data["task_for_node"]

        # Add input_from_step for step chaining
        if "input_from_step" in step_data:
            step.input_from_step = step_data["input_from_step"]

        return step

    def _generate_task_id(self, description: str) -> str:
        """Generate a task ID from description"""
        # Clean description to create ID
        task_id = re.sub(r'[^a-z0-9_]', '_', description.lower().split('.')[0][:30])
        task_id = re.sub(r'_+', '_', task_id).strip('_')

        if not task_id:
            task_id = "workflow"

        # Add timestamp to ensure uniqueness
        import time
        task_id = f"{task_id}_{int(time.time())}"

        return task_id


# Example usage
if __name__ == "__main__":
    builder = WorkflowBuilder()

    # Example 1: Simple workflow
    print("Example 1: Simple workflow")
    simple = builder.create_simple_workflow("Write an article about Python")
    print(simple.to_json())
    print()

    # Example 2: From JSON
    print("Example 2: From JSON")
    json_spec = """
    {
      "workflow_id": "test_workflow",
      "description": "Test workflow",
      "inputs": {
        "topic": {
          "type": "string",
          "required": true
        }
      },
      "outputs": {
        "result": {
          "type": "string",
          "source_reference": "steps.generate.output"
        }
      },
      "steps": [
        {
          "step_id": "generate",
          "type": "llm_call",
          "tool": "content_generator",
          "prompt_template": "Write about {topic}",
          "input_mapping": {"topic": "inputs.topic"},
          "output_name": "output"
        }
      ]
    }
    """

    from_json = builder.build_from_json(json_spec)
    print(from_json.to_json())
