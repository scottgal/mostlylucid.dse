"""
Tools Manager - Registry for reusable components (functions, LLMs, workflows).
Provides a system for storing and retrieving tools that can be used by the coordinator.
Future: Will integrate with RAG for semantic search.
"""
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ToolType(Enum):
    """Types of tools that can be registered."""
    FUNCTION = "function"              # Python function
    LLM = "llm"                       # Specialized LLM model
    WORKFLOW = "workflow"             # Complete workflow
    COMMUNITY = "community"           # Sub-workflow (community of agents)
    PROMPT_TEMPLATE = "prompt_template"  # Reusable prompt
    DATA_PROCESSOR = "data_processor"    # Data transformation tool
    VALIDATOR = "validator"              # Validation tool
    CUSTOM = "custom"                    # Custom tool type


class Tool:
    """Represents a reusable tool."""

    def __init__(
        self,
        tool_id: str,
        name: str,
        tool_type: ToolType,
        description: str,
        tags: List[str],
        implementation: Any = None,
        parameters: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize a tool.

        Args:
            tool_id: Unique identifier
            name: Human-readable name
            tool_type: Type of tool
            description: Detailed description
            tags: List of tags for categorization
            implementation: The actual implementation (function, code, config, etc.)
            parameters: Parameter schema
            metadata: Additional metadata
        """
        self.tool_id = tool_id
        self.name = name
        self.tool_type = tool_type
        self.description = description
        self.tags = tags
        self.implementation = implementation
        self.parameters = parameters or {}
        self.metadata = metadata or {}
        self.created_at = datetime.utcnow().isoformat() + "Z"
        self.usage_count = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert tool to dictionary (for serialization)."""
        return {
            "tool_id": self.tool_id,
            "name": self.name,
            "tool_type": self.tool_type.value,
            "description": self.description,
            "tags": self.tags,
            "parameters": self.parameters,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "usage_count": self.usage_count
        }

    def to_prompt_format(self) -> str:
        """
        Format tool information for inclusion in prompts.

        Returns:
            Formatted string describing the tool
        """
        params_str = ""
        if self.parameters:
            params_list = [f"  - {name}: {info.get('type', 'any')} - {info.get('description', '')}"
                          for name, info in self.parameters.items()]
            params_str = "\nParameters:\n" + "\n".join(params_list)

        return f"""Tool: {self.name} ({self.tool_id})
Type: {self.tool_type.value}
Description: {self.description}
Tags: {', '.join(self.tags)}{params_str}
"""

    @staticmethod
    def from_dict(data: Dict[str, Any], implementation: Any = None) -> 'Tool':
        """Create tool from dictionary."""
        tool = Tool(
            tool_id=data["tool_id"],
            name=data["name"],
            tool_type=ToolType(data["tool_type"]),
            description=data["description"],
            tags=data["tags"],
            implementation=implementation,
            parameters=data.get("parameters", {}),
            metadata=data.get("metadata", {})
        )
        tool.created_at = data.get("created_at", tool.created_at)
        tool.usage_count = data.get("usage_count", 0)
        return tool


class ToolsManager:
    """Manages registry of reusable tools."""

    def __init__(
        self,
        tools_path: str = "./tools",
        config_manager: Optional[Any] = None,
        ollama_client: Optional[Any] = None
    ):
        """
        Initialize tools manager.

        Args:
            tools_path: Path to tools storage directory
            config_manager: Optional ConfigManager for loading tools from config
            ollama_client: Optional OllamaClient for invoking LLM-based tools
        """
        self.tools_path = Path(tools_path)
        self.tools_path.mkdir(parents=True, exist_ok=True)

        self.index_path = self.tools_path / "index.json"
        self.config_manager = config_manager
        self.ollama_client = ollama_client

        # In-memory registry
        self.tools: Dict[str, Tool] = {}

        self._load_tools()

        # Load tools from config if available
        if config_manager:
            self._load_tools_from_config()

    def _load_tools(self):
        """Load tools from disk into memory."""
        if not self.index_path.exists():
            self._save_index()
            return

        try:
            with open(self.index_path, 'r', encoding='utf-8') as f:
                index = json.load(f)

            for tool_id, tool_data in index.items():
                # Load implementation if it's a file reference
                implementation = None
                if "implementation_file" in tool_data.get("metadata", {}):
                    impl_file = self.tools_path / tool_data["metadata"]["implementation_file"]
                    if impl_file.exists():
                        with open(impl_file, 'r', encoding='utf-8') as f:
                            implementation = f.read()

                tool = Tool.from_dict(tool_data, implementation)
                self.tools[tool_id] = tool

            logger.info(f"✓ Loaded {len(self.tools)} tools")

        except Exception as e:
            logger.error(f"Error loading tools: {e}")

    def _save_index(self):
        """Save tools index to disk."""
        try:
            index = {tool_id: tool.to_dict() for tool_id, tool in self.tools.items()}

            with open(self.index_path, 'w', encoding='utf-8') as f:
                json.dump(index, f, indent=2)

        except Exception as e:
            logger.error(f"Error saving tools index: {e}")

    def _load_tools_from_config(self):
        """Load tools defined in configuration."""
        if not self.config_manager:
            return

        tools_config = self.config_manager.get("tools", {})

        for tool_id, tool_def in tools_config.items():
            if tool_id in self.tools:
                continue  # Skip if already loaded

            tool_type_str = tool_def.get("type", "custom")
            try:
                tool_type = ToolType(tool_type_str)
            except ValueError:
                tool_type = ToolType.CUSTOM

            # Extract LLM configuration if present
            llm_config = tool_def.get("llm", {})

            tool = Tool(
                tool_id=tool_id,
                name=tool_def.get("name", tool_id),
                tool_type=tool_type,
                description=tool_def.get("description", ""),
                tags=tool_def.get("tags", []),
                implementation=llm_config if llm_config else None,
                metadata={
                    "from_config": True,
                    "llm_model": llm_config.get("model"),
                    "llm_endpoint": llm_config.get("endpoint")
                }
            )

            self.tools[tool_id] = tool
            logger.info(f"✓ Loaded tool from config: {tool_id}")

    def invoke_llm_tool(
        self,
        tool_id: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7
    ) -> str:
        """
        Invoke an LLM-based tool.

        Args:
            tool_id: Tool identifier
            prompt: Prompt to send to the LLM
            system_prompt: Optional system prompt
            temperature: Sampling temperature

        Returns:
            LLM response
        """
        tool = self.get_tool(tool_id)

        if not tool:
            logger.error(f"Tool not found: {tool_id}")
            return ""

        if tool.tool_type != ToolType.LLM:
            logger.error(f"Tool {tool_id} is not an LLM tool")
            return ""

        if not self.ollama_client:
            logger.error("OllamaClient not configured")
            return ""

        # Extract LLM configuration
        llm_config = tool.implementation or tool.metadata
        model = llm_config.get("llm_model") or llm_config.get("model", "llama3")
        endpoint = llm_config.get("llm_endpoint") or llm_config.get("endpoint")

        # Increment usage counter
        self.increment_usage(tool_id)

        # Log tool invocation
        logger.info(f"Invoking LLM tool '{tool.name}' (model: {model}, endpoint: {endpoint or 'default'})")

        # Invoke the LLM
        response = self.ollama_client.generate(
            model=model,
            prompt=prompt,
            system=system_prompt,
            temperature=temperature,
            endpoint=endpoint
        )

        return response

    def register_function(
        self,
        tool_id: str,
        name: str,
        description: str,
        function: Callable,
        parameters: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None
    ) -> Tool:
        """
        Register a Python function as a tool.

        Args:
            tool_id: Unique identifier
            name: Function name
            description: What the function does
            function: The actual Python function
            parameters: Parameter schema
            tags: Tags for categorization

        Returns:
            Created Tool object
        """
        # Get function source code
        import inspect
        source_code = inspect.getsource(function)

        # Save source code to file
        impl_file = f"{tool_id}.py"
        impl_path = self.tools_path / impl_file

        with open(impl_path, 'w', encoding='utf-8') as f:
            f.write(source_code)

        tool = Tool(
            tool_id=tool_id,
            name=name,
            tool_type=ToolType.FUNCTION,
            description=description,
            tags=tags or ["function"],
            implementation=function,
            parameters=parameters,
            metadata={"implementation_file": impl_file}
        )

        self.tools[tool_id] = tool
        self._save_index()

        logger.info(f"✓ Registered function tool: {tool_id}")
        return tool

    def register_llm(
        self,
        tool_id: str,
        name: str,
        description: str,
        model_name: str,
        system_prompt: str,
        tags: Optional[List[str]] = None
    ) -> Tool:
        """
        Register a specialized LLM as a tool.

        Args:
            tool_id: Unique identifier
            name: LLM name
            description: What the LLM specializes in
            model_name: Ollama model name
            system_prompt: System prompt for the LLM
            tags: Tags for categorization

        Returns:
            Created Tool object
        """
        tool = Tool(
            tool_id=tool_id,
            name=name,
            tool_type=ToolType.LLM,
            description=description,
            tags=tags or ["llm"],
            implementation={"model": model_name, "system_prompt": system_prompt},
            metadata={"model_name": model_name}
        )

        self.tools[tool_id] = tool
        self._save_index()

        logger.info(f"✓ Registered LLM tool: {tool_id}")
        return tool

    def register_workflow(
        self,
        tool_id: str,
        name: str,
        description: str,
        steps: List[Dict[str, Any]],
        tags: Optional[List[str]] = None
    ) -> Tool:
        """
        Register a workflow as a tool.

        Args:
            tool_id: Unique identifier
            name: Workflow name
            description: What the workflow does
            steps: List of workflow steps
            tags: Tags for categorization

        Returns:
            Created Tool object
        """
        # Save workflow definition
        workflow_file = f"{tool_id}_workflow.json"
        workflow_path = self.tools_path / workflow_file

        with open(workflow_path, 'w', encoding='utf-8') as f:
            json.dump({"steps": steps}, f, indent=2)

        tool = Tool(
            tool_id=tool_id,
            name=name,
            tool_type=ToolType.WORKFLOW,
            description=description,
            tags=tags or ["workflow"],
            implementation=steps,
            metadata={"workflow_file": workflow_file}
        )

        self.tools[tool_id] = tool
        self._save_index()

        logger.info(f"✓ Registered workflow tool: {tool_id}")
        return tool

    def register_community(
        self,
        tool_id: str,
        name: str,
        description: str,
        sub_workflows: List[str],
        coordination_strategy: str,
        tags: Optional[List[str]] = None
    ) -> Tool:
        """
        Register a community (sub-workflow system) as a tool.

        Args:
            tool_id: Unique identifier
            name: Community name
            description: What the community does
            sub_workflows: List of sub-workflow IDs
            coordination_strategy: How sub-workflows are coordinated
            tags: Tags for categorization

        Returns:
            Created Tool object
        """
        tool = Tool(
            tool_id=tool_id,
            name=name,
            tool_type=ToolType.COMMUNITY,
            description=description,
            tags=tags or ["community"],
            implementation={
                "sub_workflows": sub_workflows,
                "coordination_strategy": coordination_strategy
            },
            metadata={"sub_workflow_count": len(sub_workflows)}
        )

        self.tools[tool_id] = tool
        self._save_index()

        logger.info(f"✓ Registered community tool: {tool_id}")
        return tool

    def get_tool(self, tool_id: str) -> Optional[Tool]:
        """
        Get a tool by ID.

        Args:
            tool_id: Tool identifier

        Returns:
            Tool object or None
        """
        return self.tools.get(tool_id)

    def find_by_tags(self, tags: List[str]) -> List[Tool]:
        """
        Find tools by tags.

        Args:
            tags: List of tags to search for

        Returns:
            List of matching tools
        """
        matches = []
        search_tags = set(tags)

        for tool in self.tools.values():
            tool_tags = set(tool.tags)
            if tool_tags & search_tags:  # Intersection
                matches.append(tool)

        return sorted(matches, key=lambda t: t.usage_count, reverse=True)

    def find_by_type(self, tool_type: ToolType) -> List[Tool]:
        """
        Find tools by type.

        Args:
            tool_type: Type of tool

        Returns:
            List of matching tools
        """
        return [tool for tool in self.tools.values() if tool.tool_type == tool_type]

    def search(self, query: str) -> List[Tool]:
        """
        Search tools by keyword (simple text search for now).

        Args:
            query: Search query

        Returns:
            List of matching tools

        Note:
            Future: Will use RAG/embeddings for semantic search
        """
        query_lower = query.lower()
        matches = []

        for tool in self.tools.values():
            # Search in name, description, tags
            if (query_lower in tool.name.lower() or
                query_lower in tool.description.lower() or
                any(query_lower in tag.lower() for tag in tool.tags)):
                matches.append(tool)

        return sorted(matches, key=lambda t: t.usage_count, reverse=True)

    def get_tools_for_prompt(
        self,
        task_description: str,
        max_tools: int = 5
    ) -> str:
        """
        Get relevant tools formatted for inclusion in a prompt.

        Args:
            task_description: Description of the task
            max_tools: Maximum number of tools to include

        Returns:
            Formatted string with tool descriptions
        """
        # Simple keyword matching for now
        # Future: Use RAG/embeddings for better matching
        relevant_tools = self.search(task_description)[:max_tools]

        if not relevant_tools:
            return "No specific tools available for this task."

        tools_text = "Available Tools:\n\n"
        for i, tool in enumerate(relevant_tools, 1):
            tools_text += f"{i}. {tool.to_prompt_format()}\n"

        return tools_text

    def increment_usage(self, tool_id: str):
        """Increment usage counter for a tool."""
        if tool_id in self.tools:
            self.tools[tool_id].usage_count += 1
            self._save_index()

    def list_all(self) -> List[Tool]:
        """Get all tools."""
        return list(self.tools.values())

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the tools registry.

        Returns:
            Statistics dictionary
        """
        type_counts = {}
        for tool in self.tools.values():
            type_name = tool.tool_type.value
            type_counts[type_name] = type_counts.get(type_name, 0) + 1

        # Get tag distribution
        tag_counts = {}
        for tool in self.tools.values():
            for tag in tool.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        # Most used tools
        most_used = sorted(self.tools.values(), key=lambda t: t.usage_count, reverse=True)[:5]

        return {
            "total_tools": len(self.tools),
            "by_type": type_counts,
            "tag_distribution": tag_counts,
            "most_used": [{"id": t.tool_id, "name": t.name, "usage": t.usage_count} for t in most_used]
        }

    def delete_tool(self, tool_id: str) -> bool:
        """
        Delete a tool from the registry.

        Args:
            tool_id: Tool identifier

        Returns:
            True if deleted successfully
        """
        if tool_id not in self.tools:
            return False

        tool = self.tools[tool_id]

        # Delete implementation file if it exists
        if "implementation_file" in tool.metadata:
            impl_file = self.tools_path / tool.metadata["implementation_file"]
            if impl_file.exists():
                impl_file.unlink()

        # Remove from registry
        del self.tools[tool_id]
        self._save_index()

        logger.info(f"✓ Deleted tool: {tool_id}")
        return True
