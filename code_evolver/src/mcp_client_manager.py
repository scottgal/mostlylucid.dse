"""
MCP Client Manager - Manages connections to Model Context Protocol servers.

This module provides a centralized manager for connecting to and managing
MCP servers. It handles server lifecycle, tool discovery, and maintains
active connections to configured MCP servers.
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path
import json

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)


@dataclass
class MCPServerConfig:
    """Configuration for an MCP server."""
    name: str
    command: str
    args: List[str]
    env: Optional[Dict[str, str]] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    enabled: bool = True


class MCPServerConnection:
    """Represents an active connection to an MCP server."""

    def __init__(self, config: MCPServerConfig):
        self.config = config
        self.session: Optional[ClientSession] = None
        self.read_stream = None
        self.write_stream = None
        self._context_manager = None
        self._session_context = None
        self._tools_cache: Optional[List[Any]] = None
        self._resources_cache: Optional[List[Any]] = None
        self._prompts_cache: Optional[List[Any]] = None
        self.is_connected = False

    async def connect(self):
        """Establish connection to the MCP server."""
        if self.is_connected:
            logger.warning(f"Already connected to {self.config.name}")
            return

        try:
            server_params = StdioServerParameters(
                command=self.config.command,
                args=self.config.args,
                env=self.config.env
            )

            # Store the context manager for proper cleanup
            self._context_manager = stdio_client(server_params)
            self.read_stream, self.write_stream = await self._context_manager.__aenter__()

            # Create and initialize session
            self._session_context = ClientSession(self.read_stream, self.write_stream)
            self.session = await self._session_context.__aenter__()
            await self.session.initialize()

            self.is_connected = True
            logger.info(f"Connected to MCP server: {self.config.name}")

        except Exception as e:
            logger.error(f"Failed to connect to {self.config.name}: {e}")
            await self.disconnect()
            raise

    async def disconnect(self):
        """Close connection to the MCP server."""
        if not self.is_connected:
            return

        try:
            # Clean up session
            if self._session_context and self.session:
                await self._session_context.__aexit__(None, None, None)

            # Clean up stdio connection
            if self._context_manager:
                await self._context_manager.__aexit__(None, None, None)

        except Exception as e:
            logger.error(f"Error disconnecting from {self.config.name}: {e}")
        finally:
            self.session = None
            self.read_stream = None
            self.write_stream = None
            self._context_manager = None
            self._session_context = None
            self.is_connected = False
            logger.info(f"Disconnected from MCP server: {self.config.name}")

    async def list_tools(self) -> List[Any]:
        """List all tools available from this MCP server."""
        if not self.is_connected or not self.session:
            raise RuntimeError(f"Not connected to {self.config.name}")

        if self._tools_cache is None:
            try:
                result = await self.session.list_tools()
                self._tools_cache = result.tools if hasattr(result, 'tools') else []
            except Exception as e:
                logger.error(f"Failed to list tools from {self.config.name}: {e}")
                return []

        return self._tools_cache

    async def list_resources(self) -> List[Any]:
        """List all resources available from this MCP server."""
        if not self.is_connected or not self.session:
            raise RuntimeError(f"Not connected to {self.config.name}")

        if self._resources_cache is None:
            try:
                result = await self.session.list_resources()
                self._resources_cache = result.resources if hasattr(result, 'resources') else []
            except Exception as e:
                logger.error(f"Failed to list resources from {self.config.name}: {e}")
                return []

        return self._resources_cache

    async def list_prompts(self) -> List[Any]:
        """List all prompts available from this MCP server."""
        if not self.is_connected or not self.session:
            raise RuntimeError(f"Not connected to {self.config.name}")

        if self._prompts_cache is None:
            try:
                result = await self.session.list_prompts()
                self._prompts_cache = result.prompts if hasattr(result, 'prompts') else []
            except Exception as e:
                logger.error(f"Failed to list prompts from {self.config.name}: {e}")
                return []

        return self._prompts_cache

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call a tool on the MCP server."""
        if not self.is_connected or not self.session:
            raise RuntimeError(f"Not connected to {self.config.name}")

        try:
            result = await self.session.call_tool(tool_name, arguments=arguments)
            return result
        except Exception as e:
            logger.error(f"Failed to call tool {tool_name} on {self.config.name}: {e}")
            raise


class MCPClientManager:
    """Manages connections to multiple MCP servers."""

    def __init__(self):
        self._servers: Dict[str, MCPServerConnection] = {}
        self._event_loop: Optional[asyncio.AbstractEventLoop] = None
        self._is_initialized = False

    def _get_or_create_event_loop(self) -> asyncio.AbstractEventLoop:
        """Get or create an event loop for async operations."""
        if self._event_loop is None or self._event_loop.is_closed():
            try:
                self._event_loop = asyncio.get_event_loop()
            except RuntimeError:
                self._event_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._event_loop)
        return self._event_loop

    def add_server(self, config: MCPServerConfig):
        """Add an MCP server configuration."""
        if config.name in self._servers:
            logger.warning(f"Server {config.name} already exists, replacing")

        self._servers[config.name] = MCPServerConnection(config)
        logger.info(f"Added MCP server configuration: {config.name}")

    def remove_server(self, server_name: str):
        """Remove an MCP server and disconnect if connected."""
        if server_name in self._servers:
            loop = self._get_or_create_event_loop()
            loop.run_until_complete(self._servers[server_name].disconnect())
            del self._servers[server_name]
            logger.info(f"Removed MCP server: {server_name}")

    async def connect_all(self):
        """Connect to all configured MCP servers."""
        tasks = []
        for name, server in self._servers.items():
            if server.config.enabled and not server.is_connected:
                tasks.append(server.connect())

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Failed to connect to server: {result}")

        self._is_initialized = True

    async def disconnect_all(self):
        """Disconnect from all MCP servers."""
        tasks = []
        for server in self._servers.values():
            if server.is_connected:
                tasks.append(server.disconnect())

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        self._is_initialized = False

    def connect_all_sync(self):
        """Synchronous wrapper for connect_all."""
        loop = self._get_or_create_event_loop()
        loop.run_until_complete(self.connect_all())

    def disconnect_all_sync(self):
        """Synchronous wrapper for disconnect_all."""
        loop = self._get_or_create_event_loop()
        loop.run_until_complete(self.disconnect_all())

    def get_server(self, server_name: str) -> Optional[MCPServerConnection]:
        """Get a server connection by name."""
        return self._servers.get(server_name)

    def list_servers(self) -> List[str]:
        """List all configured server names."""
        return list(self._servers.keys())

    def list_connected_servers(self) -> List[str]:
        """List all currently connected server names."""
        return [name for name, server in self._servers.items() if server.is_connected]

    async def get_all_tools(self) -> Dict[str, List[Any]]:
        """Get all tools from all connected servers."""
        all_tools = {}

        for name, server in self._servers.items():
            if server.is_connected:
                try:
                    tools = await server.list_tools()
                    all_tools[name] = tools
                except Exception as e:
                    logger.error(f"Failed to get tools from {name}: {e}")
                    all_tools[name] = []

        return all_tools

    def get_all_tools_sync(self) -> Dict[str, List[Any]]:
        """Synchronous wrapper for get_all_tools."""
        loop = self._get_or_create_event_loop()
        return loop.run_until_complete(self.get_all_tools())

    def is_initialized(self) -> bool:
        """Check if the manager has been initialized."""
        return self._is_initialized

    def load_from_config(self, config_data: Dict[str, Any]):
        """
        Load MCP servers from configuration data.

        Args:
            config_data: Dictionary containing 'mcp_servers' key with list of server configs
        """
        if 'mcp_servers' not in config_data:
            logger.debug("No mcp_servers configuration found")
            return

        for server_config in config_data['mcp_servers']:
            try:
                config = MCPServerConfig(
                    name=server_config['name'],
                    command=server_config['command'],
                    args=server_config.get('args', []),
                    env=server_config.get('env'),
                    description=server_config.get('description'),
                    tags=server_config.get('tags', []),
                    enabled=server_config.get('enabled', True)
                )
                self.add_server(config)
            except Exception as e:
                logger.error(f"Failed to load MCP server config: {e}")

    def __enter__(self):
        """Context manager entry."""
        self.connect_all_sync()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect_all_sync()


# Global instance
_mcp_client_manager: Optional[MCPClientManager] = None


def get_mcp_client_manager() -> MCPClientManager:
    """Get the global MCP client manager instance."""
    global _mcp_client_manager
    if _mcp_client_manager is None:
        _mcp_client_manager = MCPClientManager()
    return _mcp_client_manager
