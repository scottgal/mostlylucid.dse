"""
Runtime library for generated nodes.
Provides access to LLM tools and other nodes from generated code.
"""
import os
import sys
import json
from pathlib import Path

# Add parent directory to path to import src
sys.path.insert(0, str(Path(__file__).parent))

from src import OllamaClient, ToolsManager, ConfigManager, create_rag_memory


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
        Call an LLM tool by name.

        Args:
            tool_name: Name of the tool (e.g., "technical_writer", "code_explainer")
            prompt: The prompt to send to the tool (or template variables)
            **kwargs: Additional arguments (temperature, system_prompt, template variables)

        Returns:
            Tool output as string

        Examples:
            runtime = NodeRuntime.get_instance()

            # Simple usage (prompt as-is)
            article = runtime.call_tool(
                "technical_writer",
                "Write a blog post about Python decorators",
                temperature=0.7
            )

            # Using prompt template variables
            article = runtime.call_tool(
                "technical_writer",
                topic="Python decorators and metaclasses",
                audience="intermediate developers",
                length="1500 words",
                temperature=0.7
            )

            # Proofreading with template
            corrected = runtime.call_tool(
                "proofreader",
                content=my_article_text
            )
        """
        # Find tool
        tool = self.tools.get_tool(tool_name)
        if not tool:
            # Try to find best matching tool
            tool = self.tools.get_best_llm_for_task(prompt)

        if not tool:
            raise ValueError(f"Tool '{tool_name}' not found")

        # Call tool (supports both prompt string and template variables)
        return self.tools.invoke_llm_tool(
            tool.tool_id,
            prompt=prompt,
            **kwargs
        )

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
