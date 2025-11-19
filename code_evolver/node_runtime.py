"""
Runtime library for generated nodes.
Provides access to LLM tools and other nodes from generated code.
"""
import os
import sys
import json
import logging
from pathlib import Path

# Suppress debug logging BEFORE importing anything
# This prevents DEBUG logs from polluting workflow output
logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')
for logger_name in ["src", "httpx", "httpcore", "urllib3", "qdrant_client", "anthropic"]:
    logging.getLogger(logger_name).setLevel(logging.WARNING)

# Add parent directory to path to import src
sys.path.insert(0, str(Path(__file__).parent))

from src import OllamaClient, ToolsManager, ConfigManager, create_rag_memory

# Disable status manager updates during workflow execution (keep output clean)
try:
    from src.status_manager import get_status_manager
    get_status_manager().set_enabled(False)
except:
    pass


class NodeRuntime:
    """Runtime environment for generated nodes."""

    _instance = None

    @classmethod
    def get_instance(cls):
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        """Initialize runtime."""
        # Load configuration
        config_path = Path(__file__).parent / "config.yaml"
        self.config = ConfigManager(str(config_path))

        # Initialize Ollama client
        self.client = OllamaClient(self.config.ollama_url, config_manager=self.config)

        # Initialize RAG
        self.rag = create_rag_memory(self.config, self.client)

        # Initialize tools manager
        self.tools = ToolsManager(
            config_manager=self.config,
            ollama_client=self.client,
            rag_memory=self.rag
        )

    def _track_tool_usage(self, tool_id: str, tool_metadata: dict = None):
        """
        Track tool usage in RAG (enabled by default).

        Increments usage counter and updates timestamp for the tool.
        This allows us to track which tools are used most frequently
        and aggregate usage across all versions and lineages.

        Can be disabled at:
        - Tool level: tool YAML has `track_usage: false`
        - Workflow level: set DISABLE_USAGE_TRACKING env var or pass disable_tracking kwarg

        Args:
            tool_id: The tool's unique identifier (e.g., "technical_writer_v2")
            tool_metadata: Tool metadata (to check for opt-out flag)
        """
        from datetime import datetime

        try:
            # Check if tracking disabled at tool level
            if tool_metadata and not tool_metadata.get('track_usage', True):
                logging.debug(f"Usage tracking disabled for tool: {tool_id}")
                return

            # Check if tracking disabled at workflow level
            if os.environ.get('DISABLE_USAGE_TRACKING', '').lower() in ('true', '1', 'yes'):
                logging.debug("Usage tracking disabled via DISABLE_USAGE_TRACKING env var")
                return

            # Increment usage count in RAG
            # The RAG artifact for a tool should have usage_count metadata
            self.rag.increment_usage(tool_id)

            # Also update last_used timestamp
            self.rag.update_artifact_metadata(
                tool_id,
                {
                    "last_used": datetime.utcnow().isoformat() + "Z"
                }
            )

        except Exception as e:
            # If increment_usage doesn't exist yet, we'll add it
            logging.debug(f"Usage tracking not available: {e}")

    def call_tool(self, tool_name: str, prompt: str, **kwargs) -> str:
        """
        Call any tool by name (LLM, OpenAPI, or Executable).

        Usage tracking is ENABLED BY DEFAULT for all tool calls. This helps:
        - Track which tools are used most frequently
        - Aggregate usage across tool versions and lineages
        - Generate learning data for optimization

        Args:
            tool_name: Name of the tool (e.g., "technical_writer", "nmt_translator")
            prompt: The prompt to send to the tool (or template variables)
            **kwargs: Additional arguments (temperature, system_prompt, template variables)
                disable_tracking (bool): Set True to disable usage tracking for this call

        Returns:
            Tool output as string

        Usage Tracking:
            Enabled by default. Can be disabled at:

            1. Tool level - Add to tool YAML:
               ```yaml
               track_usage: false
               ```

            2. Workflow level - Set environment variable:
               ```bash
               export DISABLE_USAGE_TRACKING=true
               python my_workflow.py
               ```

            3. Call level - Pass kwarg:
               ```python
               call_tool("my_tool", "prompt", disable_tracking=True)
               ```

        Examples:
            runtime = NodeRuntime.get_instance()

            # LLM tool usage (tracking enabled)
            article = runtime.call_tool(
                "technical_writer",
                "Write a blog post about Python decorators",
                temperature=0.7
            )

            # Disable tracking for this specific call
            test_result = runtime.call_tool(
                "test_validator",
                "validate",
                disable_tracking=True  # Don't track this internal test
            )

            # OpenAPI tool usage
            translation = runtime.call_tool(
                "nmt_translator",
                "Translate to German: Hello"
            )

            # Executable tool usage
            test_data = runtime.call_tool(
                "random_data_generator",
                "Generate test data for translation"
            )
        """
        from src.tools_manager import ToolType

        # Wait for tools to finish loading (if still loading)
        if hasattr(self.tools, '_loading_complete'):
            # Wait up to 30 seconds for tools to load
            if not self.tools._loading_complete.wait(timeout=30):
                logging.warning("Tools still loading after 30s, proceeding anyway...")

        # Find tool
        tool = self.tools.get_tool(tool_name)
        if not tool:
            # Try to find best matching tool (LLM only)
            tool = self.tools.get_best_llm_for_task(prompt)

        if not tool:
            raise ValueError(f"Tool '{tool_name}' not found")

        # Track tool usage in RAG (enabled by default, can be disabled)
        # Check for disable_tracking kwarg (workflow-level override)
        disable_tracking = kwargs.pop('disable_tracking', False)

        if not disable_tracking:
            try:
                # Pass tool metadata to check for tool-level opt-out
                tool_metadata = getattr(tool, 'metadata', {})
                self._track_tool_usage(tool.tool_id, tool_metadata)
            except Exception as e:
                # Don't fail if tracking fails
                logging.warning(f"Failed to track usage for {tool.tool_id}: {e}")

        # Route to appropriate invoke method based on tool type
        if tool.tool_type == ToolType.LLM:
            return self.tools.invoke_llm_tool(
                tool.tool_id,
                prompt=prompt,
                **kwargs
            )
        elif tool.tool_type == ToolType.OPENAPI:
            # For OpenAPI tools, we need to parse the prompt
            # For now, use a simple approach - look for the NMT translator
            if "nmt" in tool_name.lower() or "translat" in tool_name.lower():
                # Use the executable wrapper instead
                exec_tool = self.tools.get_tool("nmt_translate")
                if exec_tool:
                    result = self.tools.invoke_executable_tool(
                        exec_tool.tool_id,
                        source_file="",  # Not used, prompt is used instead
                        prompt=prompt,
                        **kwargs
                    )
                    return result.get("stdout", "").strip() or result.get("stderr", "")

            # Generic OpenAPI tool - needs proper implementation
            raise NotImplementedError(
                f"OpenAPI tool '{tool_name}' cannot be called with simple prompt. "
                f"Use the executable wrapper if available."
            )
        elif tool.tool_type == ToolType.EXECUTABLE:
            result = self.tools.invoke_executable_tool(
                tool.tool_id,
                source_file="",  # Not used for prompt-based tools
                prompt=prompt,
                **kwargs
            )
            # Extract stdout from result
            return result.get("stdout", "").strip() or result.get("stderr", "")
        elif tool.tool_type == ToolType.WORKFLOW:
            # Workflow tools are executed as nodes
            import subprocess
            import json
            import os

            # Convert tool_id to node directory (e.g., "translate_the_data" -> "nodes/translate_the_data")
            node_dir = os.path.join("nodes", tool.tool_id)
            main_py = os.path.join(node_dir, "main.py")

            if not os.path.exists(main_py):
                raise FileNotFoundError(f"Workflow '{tool.tool_id}' main.py not found at {main_py}")

            # Execute the workflow node with prompt as input
            try:
                # Prepare input JSON
                input_data = {"prompt": prompt}
                input_json = json.dumps(input_data)

                # Run the workflow
                result = subprocess.run(
                    ["python", main_py],
                    input=input_json,
                    capture_output=True,
                    text=True,
                    timeout=kwargs.get('timeout', 300)  # 5 minute default timeout
                )

                if result.returncode != 0:
                    raise RuntimeError(f"Workflow '{tool.tool_id}' failed: {result.stderr}")

                return result.stdout.strip()

            except subprocess.TimeoutExpired:
                raise TimeoutError(f"Workflow '{tool.tool_id}' timed out")
            except Exception as e:
                raise RuntimeError(f"Failed to execute workflow '{tool.tool_id}': {e}")
        else:
            raise ValueError(f"Unknown tool type: {tool.tool_type}")

    def call_llm(self, model: str, prompt: str, **kwargs) -> str:
        """
        Call an LLM directly.

        Args:
            model: Model name (e.g., "llama3", "codellama")
            prompt: The prompt
            **kwargs: Additional arguments (temperature, system, etc.)

        Returns:
            LLM output

        Example:
            runtime = NodeRuntime.get_instance()
            response = runtime.call_llm(
                "llama3",
                "Explain Python decorators in simple terms"
            )
        """
        return self.client.generate(
            model=model,
            prompt=prompt,
            **kwargs
        )


# Convenience function for generated code
def call_tool(tool_name: str, prompt: str, **kwargs) -> str:
    """
    Call an LLM tool from generated code.

    Usage in generated nodes:
        from node_runtime import call_tool

        article = call_tool(
            "technical_writer",
            "Write about Python async/await"
        )
    """
    runtime = NodeRuntime.get_instance()
    return runtime.call_tool(tool_name, prompt, **kwargs)


def call_llm(model: str, prompt: str, **kwargs) -> str:
    """
    Call an LLM directly from generated code.

    Usage in generated nodes:
        from node_runtime import call_llm

        response = call_llm(
            "llama3",
            "Explain decorators"
        )
    """
    runtime = NodeRuntime.get_instance()
    return runtime.call_llm(model, prompt, **kwargs)


def call_tools_parallel(tool_calls: list) -> list:
    """
    Call multiple tools in parallel using concurrent execution.

    Args:
        tool_calls: List of tuples (tool_name, prompt, kwargs_dict)
                   or dict with keys: 'tool', 'prompt', 'kwargs' (optional)

    Returns:
        List of results in the same order as tool_calls

    Usage in generated nodes:
        from node_runtime import call_tools_parallel

        # Example 1: Translate to multiple languages in parallel
        results = call_tools_parallel([
            ("nmt_translator", "Translate to french: Hello", {"target_lang": "fr"}),
            ("nmt_translator", "Translate to spanish: Hello", {"target_lang": "es"}),
            ("nmt_translator", "Translate to german: Hello", {"target_lang": "de"})
        ])
        french, spanish, german = results

        # Example 2: Generate multiple independent pieces of content
        results = call_tools_parallel([
            {"tool": "content_generator", "prompt": "Write a joke about cats"},
            {"tool": "content_generator", "prompt": "Write a joke about dogs"},
            {"tool": "content_generator", "prompt": "Write a joke about birds"}
        ])
    """
    import concurrent.futures

    runtime = NodeRuntime.get_instance()

    def execute_tool_call(call_spec):
        """Execute a single tool call from spec"""
        if isinstance(call_spec, dict):
            tool = call_spec['tool']
            prompt = call_spec['prompt']
            kwargs = call_spec.get('kwargs', {})
        else:
            # Tuple format: (tool, prompt) or (tool, prompt, kwargs)
            if len(call_spec) == 2:
                tool, prompt = call_spec
                kwargs = {}
            else:
                tool, prompt, kwargs = call_spec

        return runtime.call_tool(tool, prompt, **kwargs)

    # Execute all tool calls in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(tool_calls)) as executor:
        futures = [executor.submit(execute_tool_call, call) for call in tool_calls]
        results = [future.result() for future in futures]

    return results


# Helper for chaining tool calls
class ToolChain:
    """Chain multiple tool calls together."""

    def __init__(self):
        self.runtime = NodeRuntime.get_instance()
        self.result = ""

    def call(self, tool_name: str, prompt: str, **kwargs):
        """Call a tool and store result."""
        self.result = self.runtime.call_tool(tool_name, prompt, **kwargs)
        return self

    def then(self, tool_name: str, prompt_template: str, **kwargs):
        """
        Call another tool, passing previous result.

        Use {result} in prompt_template to reference previous result.
        """
        prompt = prompt_template.format(result=self.result)
        self.result = self.runtime.call_tool(tool_name, prompt, **kwargs)
        return self

    def get(self):
        """Get final result."""
        return self.result




def call_tool_resilient(scenario: str, input_data: dict, **kwargs) -> str:
    """
    Call a tool with automatic fallback to alternatives on failure.
    
    Self-recovering tool execution that tries alternative tools when one fails.
    Marks failures and learns from them to improve future tool selection.
    
    Args:
        scenario: Description of what needs to be done
        input_data: Input data for the selected tool
        **kwargs:
            tags (list): Optional tag filters for tool selection
            max_attempts (int): Maximum tools to try (default: 5)
            mark_failures (bool): Whether to mark failures (default: True)
    
    Returns:
        Result from successful tool (as string)
    
    Raises:
        Exception: If all tool attempts fail
    
    Example:
        # Automatic tool selection and fallback
        result = call_tool_resilient(
            "translate english to french",
            {"text": "Hello", "target": "fr"},
            tags=["translation"],
            max_attempts=5
        )
    """
    runtime = NodeRuntime.get_instance()
    
    resilient_input = {
        "scenario": scenario,
        "input": input_data,
        "tags": kwargs.get("tags", []),
        "max_attempts": kwargs.get("max_attempts", 5),
        "mark_failures": kwargs.get("mark_failures", True)
    }
    
    result = runtime.call_tool("resilient_tool_call", json.dumps(resilient_input))
    result_data = json.loads(result)
    
    if not result_data["success"]:
        raise Exception(f"All tools failed: {result_data.get('message')}")
    
    return result_data["result"]


# Example usage for generated code:
if __name__ == "__main__":
    # Example 1: Simple tool call
    article = call_tool(
        "technical_writer",
        "Write a short blog post about Python decorators"
    )
    print(article)

    # Example 2: Chained calls
    chain = ToolChain()
    final_article = (
        chain
        .call("outline_generator", "Create outline for Python decorators tutorial")
        .then("technical_writer", "Write article based on this outline:\n{result}")
        .then("proofreader", "Proofread this article:\n{result}")
        .get()
    )
    print(final_article)
