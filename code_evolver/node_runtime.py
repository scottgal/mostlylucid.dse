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

    def call_tool(self, tool_name: str, prompt: str, **kwargs) -> str:
        """
        Call any tool by name (LLM, OpenAPI, or Executable).

        Args:
            tool_name: Name of the tool (e.g., "technical_writer", "nmt_translator")
            prompt: The prompt to send to the tool (or template variables)
            **kwargs: Additional arguments (temperature, system_prompt, template variables)

        Returns:
            Tool output as string

        Examples:
            runtime = NodeRuntime.get_instance()

            # LLM tool usage
            article = runtime.call_tool(
                "technical_writer",
                "Write a blog post about Python decorators",
                temperature=0.7
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

        # Find tool
        tool = self.tools.get_tool(tool_name)
        if not tool:
            # Try to find best matching tool (LLM only)
            tool = self.tools.get_best_llm_for_task(prompt)

        if not tool:
            raise ValueError(f"Tool '{tool_name}' not found")

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
