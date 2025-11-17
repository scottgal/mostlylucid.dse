"""
Dynamic Tool Registry for creating and managing LLM tools at runtime.

Enables other tools to create new LLM tools dynamically, with proper
safety checks, metadata tracking, and quality assurance.

Features:
- Dynamic tool creation from prompts
- Tool validation and safety checks
- Automatic metadata assignment
- Integration with existing tools_manager
- Tool lifecycle management
"""

import json
import logging
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class ToolMetadata:
    """Metadata for a dynamically created tool."""
    generated_by: str
    created_at: str
    task_type: str
    tier: str
    quality_tier: str
    speed_tier: str
    cost_tier: str
    context_window: int
    timeout: int
    version: str = "1.0.0"
    validated: bool = False
    usage_count: int = 0


class DynamicToolRegistry:
    """
    Registry for dynamically created LLM tools.

    Manages the lifecycle of tools created by prompt_generator and other
    meta-tools. Ensures safety, quality, and efficient usage.
    """

    def __init__(self, config_manager, tools_manager, storage_path: Optional[str] = None):
        """
        Initialize dynamic tool registry.

        Args:
            config_manager: ConfigManager instance
            tools_manager: ToolsManager instance
            storage_path: Optional path to store dynamic tools
        """
        self.config = config_manager
        self.tools_manager = tools_manager
        self.storage_path = Path(storage_path or "./tools/dynamic")
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.dynamic_tools = {}  # tool_id -> tool_def
        self._load_existing_tools()

    def _load_existing_tools(self):
        """Load previously created dynamic tools from storage."""
        if not self.storage_path.exists():
            return

        for tool_file in self.storage_path.glob("*.yaml"):
            try:
                with open(tool_file, 'r') as f:
                    tool_def = yaml.safe_load(f)
                    tool_id = tool_file.stem
                    self.dynamic_tools[tool_id] = tool_def
                    logger.info(f"Loaded dynamic tool: {tool_id}")
            except Exception as e:
                logger.warning(f"Failed to load dynamic tool {tool_file}: {e}")

    def register_tool(
        self,
        tool_name: str,
        tool_definition: Dict[str, Any],
        validate: bool = True,
        persist: bool = True
    ) -> Optional[str]:
        """
        Register a dynamically created tool.

        Args:
            tool_name: Name for the tool
            tool_definition: Tool definition dict from prompt_generator
            validate: Whether to validate the tool before registration
            persist: Whether to persist to disk

        Returns:
            Tool ID if successful, None otherwise
        """
        # Sanitize tool name for ID
        tool_id = self._sanitize_tool_id(tool_name)

        # Check if already exists
        if tool_id in self.dynamic_tools:
            logger.warning(f"Tool {tool_id} already exists. Use update_tool instead.")
            return None

        # Validate if requested
        if validate:
            is_valid, errors = self._validate_tool_definition(tool_definition)
            if not is_valid:
                logger.error(f"Tool validation failed: {errors}")
                return None

        # Ensure required fields
        tool_definition = self._ensure_required_fields(tool_definition, tool_name)

        # Store in memory
        self.dynamic_tools[tool_id] = tool_definition

        # Persist to disk if requested
        if persist:
            self._persist_tool(tool_id, tool_definition)

        # Register with tools_manager
        try:
            self._register_with_tools_manager(tool_id, tool_definition)
            logger.info(f"Successfully registered dynamic tool: {tool_id}")
            return tool_id
        except Exception as e:
            logger.error(f"Failed to register tool with tools_manager: {e}")
            # Rollback
            del self.dynamic_tools[tool_id]
            if persist:
                self._delete_persisted_tool(tool_id)
            return None

    def _sanitize_tool_id(self, tool_name: str) -> str:
        """Convert tool name to valid tool ID."""
        # Replace spaces and special chars with underscores
        sanitized = tool_name.lower().replace(" ", "_")
        sanitized = "".join(c if c.isalnum() or c == "_" else "_" for c in sanitized)
        # Remove consecutive underscores
        while "__" in sanitized:
            sanitized = sanitized.replace("__", "_")
        return f"dynamic_{sanitized}"

    def _validate_tool_definition(self, tool_def: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        Validate tool definition structure and safety.

        Returns:
            (is_valid, list of errors)
        """
        errors = []

        # Required fields
        required = ["name", "type", "description"]
        for field in required:
            if field not in tool_def:
                errors.append(f"Missing required field: {field}")

        # Type check
        if tool_def.get("type") not in ["llm", "custom", "executable", "openapi"]:
            errors.append(f"Invalid tool type: {tool_def.get('type')}")

        # LLM tools must have llm config
        if tool_def.get("type") == "llm":
            if "llm" not in tool_def:
                errors.append("LLM tool missing 'llm' configuration")
            else:
                llm_config = tool_def["llm"]
                if "model" not in llm_config and "tier" not in llm_config:
                    errors.append("LLM config must specify 'model' or 'tier'")

        # Safety checks
        if tool_def.get("type") == "executable":
            # Check for dangerous commands
            if "executable" in tool_def:
                command = tool_def["executable"].get("command", "")
                dangerous = ["rm", "del", "format", "mkfs", "dd"]
                if any(cmd in command.lower() for cmd in dangerous):
                    errors.append(f"Potentially dangerous command detected: {command}")

        # Metadata checks
        if "metadata" in tool_def:
            metadata = tool_def["metadata"]
            # Ensure safety tiers are valid
            valid_tiers = ["free", "very-low", "low", "medium", "high", "very-high"]
            if "cost_tier" in metadata and metadata["cost_tier"] not in valid_tiers:
                errors.append(f"Invalid cost_tier: {metadata['cost_tier']}")

        return len(errors) == 0, errors

    def _ensure_required_fields(
        self,
        tool_def: Dict[str, Any],
        tool_name: str
    ) -> Dict[str, Any]:
        """Ensure all required fields are present with defaults."""
        # Ensure name
        if "name" not in tool_def:
            tool_def["name"] = tool_name

        # Ensure type
        if "type" not in tool_def:
            tool_def["type"] = "llm"

        # Ensure tags
        if "tags" not in tool_def:
            tool_def["tags"] = ["dynamic", "generated"]
        elif "dynamic" not in tool_def["tags"]:
            tool_def["tags"].append("dynamic")

        # Ensure metadata
        if "metadata" not in tool_def:
            tool_def["metadata"] = {}

        if "generated_by" not in tool_def["metadata"]:
            tool_def["metadata"]["generated_by"] = "prompt_generator"

        # Add timestamp
        from datetime import datetime
        tool_def["metadata"]["created_at"] = datetime.utcnow().isoformat()

        # Default quality/speed/cost if not specified
        defaults = {
            "quality_tier": "good",
            "speed_tier": "medium",
            "cost_tier": "medium"
        }
        for key, value in defaults.items():
            if key not in tool_def["metadata"]:
                tool_def["metadata"][key] = value

        return tool_def

    def _persist_tool(self, tool_id: str, tool_def: Dict[str, Any]):
        """Persist tool definition to disk."""
        tool_path = self.storage_path / f"{tool_id}.yaml"
        try:
            with open(tool_path, 'w') as f:
                yaml.dump(tool_def, f, default_flow_style=False, sort_keys=False)
            logger.debug(f"Persisted tool to {tool_path}")
        except Exception as e:
            logger.error(f"Failed to persist tool {tool_id}: {e}")

    def _delete_persisted_tool(self, tool_id: str):
        """Delete persisted tool from disk."""
        tool_path = self.storage_path / f"{tool_id}.yaml"
        if tool_path.exists():
            tool_path.unlink()

    def _register_with_tools_manager(self, tool_id: str, tool_def: Dict[str, Any]):
        """Register tool with the system's tools_manager."""
        from .tools_manager import Tool, ToolType

        # Map type string to ToolType enum
        type_map = {
            "llm": ToolType.LLM,
            "custom": ToolType.CUSTOM,
            "executable": ToolType.EXECUTABLE,
            "openapi": ToolType.OPENAPI
        }

        tool_type = type_map.get(tool_def.get("type", "llm"), ToolType.LLM)

        # Create Tool object
        tool = Tool(
            tool_id=tool_id,
            name=tool_def["name"],
            tool_type=tool_type,
            description=tool_def.get("description", "Dynamically generated tool"),
            tags=tool_def.get("tags", ["dynamic"]),
            implementation=None,  # Will be created by tools_manager
            parameters=tool_def.get("input_schema", {}),
            metadata=tool_def.get("metadata", {})
        )

        # Register
        self.tools_manager.register_tool(tool)

    def get_tool(self, tool_id: str) -> Optional[Dict[str, Any]]:
        """Get tool definition by ID."""
        return self.dynamic_tools.get(tool_id)

    def list_tools(
        self,
        filter_by: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        List all dynamic tools.

        Args:
            filter_by: Optional filters like {"task_type": "code"}

        Returns:
            List of tool definitions
        """
        tools = list(self.dynamic_tools.values())

        if filter_by:
            filtered = []
            for tool in tools:
                match = True
                for key, value in filter_by.items():
                    # Check in metadata
                    if key not in tool.get("metadata", {}):
                        match = False
                        break
                    if tool["metadata"][key] != value:
                        match = False
                        break
                if match:
                    filtered.append(tool)
            return filtered

        return tools

    def update_tool(
        self,
        tool_id: str,
        updates: Dict[str, Any],
        validate: bool = True
    ) -> bool:
        """
        Update an existing dynamic tool.

        Args:
            tool_id: Tool ID to update
            updates: Dict of updates to apply
            validate: Whether to validate after update

        Returns:
            True if successful
        """
        if tool_id not in self.dynamic_tools:
            logger.error(f"Tool {tool_id} not found")
            return False

        # Get current definition
        tool_def = self.dynamic_tools[tool_id].copy()

        # Apply updates
        tool_def.update(updates)

        # Validate if requested
        if validate:
            is_valid, errors = self._validate_tool_definition(tool_def)
            if not is_valid:
                logger.error(f"Updated tool validation failed: {errors}")
                return False

        # Update in memory
        self.dynamic_tools[tool_id] = tool_def

        # Persist
        self._persist_tool(tool_id, tool_def)

        # Re-register with tools_manager
        try:
            # Unregister old version
            self.tools_manager.unregister_tool(tool_id)
            # Register new version
            self._register_with_tools_manager(tool_id, tool_def)
            logger.info(f"Successfully updated dynamic tool: {tool_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to update tool in tools_manager: {e}")
            return False

    def delete_tool(self, tool_id: str) -> bool:
        """
        Delete a dynamic tool.

        Args:
            tool_id: Tool ID to delete

        Returns:
            True if successful
        """
        if tool_id not in self.dynamic_tools:
            logger.error(f"Tool {tool_id} not found")
            return False

        # Unregister from tools_manager
        try:
            self.tools_manager.unregister_tool(tool_id)
        except Exception as e:
            logger.warning(f"Failed to unregister from tools_manager: {e}")

        # Remove from memory
        del self.dynamic_tools[tool_id]

        # Delete from disk
        self._delete_persisted_tool(tool_id)

        logger.info(f"Deleted dynamic tool: {tool_id}")
        return True

    def increment_usage(self, tool_id: str):
        """Increment usage counter for a tool."""
        if tool_id in self.dynamic_tools:
            metadata = self.dynamic_tools[tool_id].get("metadata", {})
            metadata["usage_count"] = metadata.get("usage_count", 0) + 1
            self.dynamic_tools[tool_id]["metadata"] = metadata
            # Persist updated count periodically (every 10 uses)
            if metadata["usage_count"] % 10 == 0:
                self._persist_tool(tool_id, self.dynamic_tools[tool_id])


def create_dynamic_tool_registry(config_manager, tools_manager):
    """
    Factory function to create dynamic tool registry.

    Args:
        config_manager: ConfigManager instance
        tools_manager: ToolsManager instance

    Returns:
        DynamicToolRegistry instance
    """
    registry = DynamicToolRegistry(config_manager, tools_manager)
    logger.info(f"Created dynamic tool registry with {len(registry.dynamic_tools)} existing tools")
    return registry
