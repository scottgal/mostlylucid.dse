"""
MCP Tool Adapter - Converts MCP tools to system Tool objects.

This module provides adapters to convert MCP server tools, resources, and prompts
into the system's Tool format, enabling seamless integration of MCP servers.
"""
import logging
import asyncio
from typing import Dict, Any, List, Optional, Callable
import json

from .tools_manager import Tool, ToolType
from .mcp_client_manager import get_mcp_client_manager, MCPServerConnection

logger = logging.getLogger(__name__)


class MCPToolAdapter:
    """Adapts MCP tools to system Tool objects."""

    def __init__(self):
        self._tool_cache: Dict[str, Tool] = {}
        self._mcp_manager = get_mcp_client_manager()

    def _mcp_tool_to_system_tool(
        self,
        mcp_tool: Any,
        server_name: str,
        server_connection: MCPServerConnection
    ) -> Tool:
        """
        Convert an MCP tool to a system Tool object.

        Args:
            mcp_tool: MCP tool object from list_tools()
            server_name: Name of the MCP server
            server_connection: The MCP server connection

        Returns:
            System Tool object
        """
        # Extract tool information from MCP tool
        tool_name = mcp_tool.name if hasattr(mcp_tool, 'name') else str(mcp_tool)
        description = mcp_tool.description if hasattr(mcp_tool, 'description') else ""
        input_schema = mcp_tool.inputSchema if hasattr(mcp_tool, 'inputSchema') else {}

        # Create unique tool ID
        tool_id = f"mcp_{server_name}_{tool_name}"

        # Create the implementation function that calls the MCP server
        async def mcp_tool_implementation(**kwargs) -> Any:
            """Implementation that calls the MCP server tool."""
            try:
                result = await server_connection.call_tool(tool_name, arguments=kwargs)
                # Extract content from result
                if hasattr(result, 'content'):
                    if isinstance(result.content, list) and len(result.content) > 0:
                        # Return first content item's text if available
                        first_content = result.content[0]
                        if hasattr(first_content, 'text'):
                            return first_content.text
                        return first_content
                    return result.content
                return result
            except Exception as e:
                logger.error(f"Error calling MCP tool {tool_name}: {e}")
                raise

        # Create synchronous wrapper
        def sync_wrapper(**kwargs) -> Any:
            """Synchronous wrapper for the MCP tool."""
            loop = self._mcp_manager._get_or_create_event_loop()
            return loop.run_until_complete(mcp_tool_implementation(**kwargs))

        # Extract parameters from input schema
        parameters = {}
        if isinstance(input_schema, dict):
            properties = input_schema.get('properties', {})
            required = input_schema.get('required', [])

            for param_name, param_info in properties.items():
                parameters[param_name] = {
                    'type': param_info.get('type', 'string'),
                    'description': param_info.get('description', ''),
                    'required': param_name in required
                }

        # Create metadata
        metadata = {
            'mcp_server': server_name,
            'mcp_tool_name': tool_name,
            'version': '1.0.0',
            'source': 'mcp'
        }

        # Extract tags from server config and tool description
        server_config = server_connection.config
        tags = ['mcp', server_name]
        if server_config.tags:
            tags.extend(server_config.tags)

        # Create and return Tool object
        tool = Tool(
            tool_id=tool_id,
            name=f"{server_name}_{tool_name}",
            tool_type=ToolType.CUSTOM,  # MCP tools are custom tools
            description=f"[MCP: {server_name}] {description}",
            tags=tags,
            implementation=sync_wrapper,
            parameters=parameters,
            metadata=metadata
        )

        return tool

    def _mcp_resource_to_system_tool(
        self,
        mcp_resource: Any,
        server_name: str,
        server_connection: MCPServerConnection
    ) -> Tool:
        """
        Convert an MCP resource to a system Tool object.

        Args:
            mcp_resource: MCP resource object from list_resources()
            server_name: Name of the MCP server
            server_connection: The MCP server connection

        Returns:
            System Tool object
        """
        # Extract resource information
        resource_uri = mcp_resource.uri if hasattr(mcp_resource, 'uri') else str(mcp_resource)
        resource_name = mcp_resource.name if hasattr(mcp_resource, 'name') else resource_uri.split('/')[-1]
        description = mcp_resource.description if hasattr(mcp_resource, 'description') else ""

        # Create unique tool ID
        tool_id = f"mcp_{server_name}_resource_{resource_name}"

        # Create the implementation function that reads the resource
        async def mcp_resource_implementation(**kwargs) -> Any:
            """Implementation that reads the MCP resource."""
            try:
                result = await server_connection.session.read_resource(resource_uri)
                # Extract content from result
                if hasattr(result, 'contents') and len(result.contents) > 0:
                    return [
                        {'uri': c.uri, 'text': c.text if hasattr(c, 'text') else str(c)}
                        for c in result.contents
                    ]
                return result
            except Exception as e:
                logger.error(f"Error reading MCP resource {resource_uri}: {e}")
                raise

        # Create synchronous wrapper
        def sync_wrapper(**kwargs) -> Any:
            """Synchronous wrapper for the MCP resource."""
            loop = self._mcp_manager._get_or_create_event_loop()
            return loop.run_until_complete(mcp_resource_implementation(**kwargs))

        # Create metadata
        metadata = {
            'mcp_server': server_name,
            'mcp_resource_uri': resource_uri,
            'version': '1.0.0',
            'source': 'mcp_resource'
        }

        # Create tags
        tags = ['mcp', 'resource', server_name]
        if server_connection.config.tags:
            tags.extend(server_connection.config.tags)

        # Create and return Tool object
        tool = Tool(
            tool_id=tool_id,
            name=f"{server_name}_resource_{resource_name}",
            tool_type=ToolType.CUSTOM,
            description=f"[MCP Resource: {server_name}] {description}",
            tags=tags,
            implementation=sync_wrapper,
            parameters={},
            metadata=metadata
        )

        return tool

    async def load_tools_from_server(self, server_name: str) -> List[Tool]:
        """
        Load all tools from an MCP server and convert to system Tools.

        Args:
            server_name: Name of the MCP server

        Returns:
            List of system Tool objects
        """
        server = self._mcp_manager.get_server(server_name)
        if not server:
            logger.error(f"MCP server {server_name} not found")
            return []

        if not server.is_connected:
            logger.warning(f"MCP server {server_name} is not connected")
            return []

        tools = []

        try:
            # Load tools
            mcp_tools = await server.list_tools()
            for mcp_tool in mcp_tools:
                try:
                    tool = self._mcp_tool_to_system_tool(mcp_tool, server_name, server)
                    tools.append(tool)
                    self._tool_cache[tool.tool_id] = tool
                    logger.debug(f"Loaded MCP tool: {tool.name}")
                except Exception as e:
                    logger.error(f"Failed to convert MCP tool: {e}")

            # Load resources as tools
            mcp_resources = await server.list_resources()
            for mcp_resource in mcp_resources:
                try:
                    tool = self._mcp_resource_to_system_tool(mcp_resource, server_name, server)
                    tools.append(tool)
                    self._tool_cache[tool.tool_id] = tool
                    logger.debug(f"Loaded MCP resource: {tool.name}")
                except Exception as e:
                    logger.error(f"Failed to convert MCP resource: {e}")

        except Exception as e:
            logger.error(f"Failed to load tools from {server_name}: {e}")

        logger.info(f"Loaded {len(tools)} tools from MCP server {server_name}")
        return tools

    def load_tools_from_server_sync(self, server_name: str) -> List[Tool]:
        """Synchronous wrapper for load_tools_from_server."""
        loop = self._mcp_manager._get_or_create_event_loop()
        return loop.run_until_complete(self.load_tools_from_server(server_name))

    async def load_all_tools(self) -> List[Tool]:
        """
        Load all tools from all connected MCP servers.

        Returns:
            List of all system Tool objects from all MCP servers
        """
        all_tools = []

        for server_name in self._mcp_manager.list_connected_servers():
            tools = await self.load_tools_from_server(server_name)
            all_tools.extend(tools)

        return all_tools

    def load_all_tools_sync(self) -> List[Tool]:
        """Synchronous wrapper for load_all_tools."""
        loop = self._mcp_manager._get_or_create_event_loop()
        return loop.run_until_complete(self.load_all_tools())

    def get_tool(self, tool_id: str) -> Optional[Tool]:
        """Get a cached tool by ID."""
        return self._tool_cache.get(tool_id)

    def list_tools(self) -> List[Tool]:
        """List all cached tools."""
        return list(self._tool_cache.values())

    def clear_cache(self):
        """Clear the tool cache."""
        self._tool_cache.clear()


# Global instance
_mcp_tool_adapter: Optional[MCPToolAdapter] = None


def get_mcp_tool_adapter() -> MCPToolAdapter:
    """Get the global MCP tool adapter instance."""
    global _mcp_tool_adapter
    if _mcp_tool_adapter is None:
        _mcp_tool_adapter = MCPToolAdapter()
    return _mcp_tool_adapter
