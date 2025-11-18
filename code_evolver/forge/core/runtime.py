"""
Forge Runtime - Executes MCP servers and tools with sandboxing and provenance.

The runtime provides:
- MCP server process management
- Tool execution with sandboxing
- Provenance logging
- Metrics collection
"""
import json
import logging
import subprocess
import time
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import hashlib

# Import existing systems
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.mcp_client_manager import get_mcp_client_manager

from .registry import ForgeRegistry

logger = logging.getLogger(__name__)


class ForgeRuntime:
    """
    Forge Runtime - Executes MCP tools with sandboxing and logging.

    Features:
    - Process management for MCP servers
    - Sandboxed execution
    - Provenance tracking
    - Metrics collection
    """

    def __init__(
        self,
        registry: ForgeRegistry,
        log_dir: Optional[Path] = None
    ):
        """
        Initialize forge runtime.

        Args:
            registry: Forge registry for tool manifests
            log_dir: Directory for provenance logs
        """
        self.registry = registry
        self.log_dir = log_dir or Path("code_evolver/forge/data/logs")
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Get MCP client manager
        self.mcp_manager = get_mcp_client_manager()

        # Execution tracking
        self._executions: Dict[str, Dict[str, Any]] = {}

        logger.info(f"ForgeRuntime initialized with log_dir: {self.log_dir}")

    def execute(
        self,
        tool_id: str,
        version: str,
        input_data: Dict[str, Any],
        sandbox_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute tool with sandboxing and provenance tracking.

        Args:
            tool_id: Tool identifier
            version: Tool version
            input_data: Input parameters
            sandbox_config: Sandbox configuration

        Returns:
            Execution result with provenance and metrics
        """
        start_time = time.time()
        call_id = self._generate_call_id(tool_id, version)

        logger.info(f"Executing tool: {tool_id} v{version} (call_id: {call_id})")

        try:
            # Get tool manifest
            manifest = self.registry.get_tool_manifest(tool_id, version)
            if not manifest:
                return self._error_result(call_id, "Tool manifest not found")

            # Start MCP server if needed
            if manifest.mcp:
                server_started = self._ensure_mcp_server(manifest)
                if not server_started:
                    return self._error_result(call_id, "Failed to start MCP server")

            # Execute tool
            result = self._execute_mcp_tool(manifest, input_data, sandbox_config)

            # Calculate metrics
            execution_time = time.time() - start_time
            metrics = {
                'latency_ms': execution_time * 1000,
                'success': True,
                'timestamp': datetime.utcnow().isoformat() + "Z"
            }

            # Create provenance record
            provenance = {
                'call_id': call_id,
                'tool_id': tool_id,
                'version': version,
                'started_at': datetime.fromtimestamp(start_time).isoformat() + "Z",
                'finished_at': datetime.utcnow().isoformat() + "Z",
                'input_hash': self._hash_input(input_data),
                'sandbox_config': sandbox_config or {}
            }

            # Log provenance
            self._log_provenance(call_id, provenance, metrics, result)

            return {
                'success': True,
                'result': result,
                'provenance': provenance,
                'metrics': metrics
            }

        except Exception as e:
            logger.error(f"Execution failed for {tool_id}: {e}")
            execution_time = time.time() - start_time

            return {
                'success': False,
                'result': None,
                'provenance': {
                    'call_id': call_id,
                    'tool_id': tool_id,
                    'version': version,
                    'error': str(e)
                },
                'metrics': {
                    'latency_ms': execution_time * 1000,
                    'success': False
                },
                'errors': [str(e)]
            }

    def _ensure_mcp_server(self, manifest: Any) -> bool:
        """Ensure MCP server is running for the tool."""
        try:
            mcp_config = manifest.mcp
            server_name = mcp_config['server_name']

            # Check if server is already running
            connection = self.mcp_manager.get_connection(server_name)
            if connection and connection.is_connected():
                return True

            # Start server
            logger.info(f"Starting MCP server: {server_name}")

            # Convert manifest MCP config to server config
            from src.mcp_client_manager import MCPServerConfig

            server_config = MCPServerConfig(
                server_name=server_name,
                command=mcp_config['command'],
                args=mcp_config.get('args', []),
                env=mcp_config.get('env', {}),
                enabled=mcp_config.get('enabled', True),
                auto_start=mcp_config.get('auto_start', True),
                tags=manifest.tags
            )

            # Add to MCP manager and start
            self.mcp_manager.add_server(server_config)
            connection = self.mcp_manager.get_connection(server_name)

            return connection is not None and connection.is_connected()

        except Exception as e:
            logger.error(f"Failed to ensure MCP server: {e}")
            return False

    def _execute_mcp_tool(
        self,
        manifest: Any,
        input_data: Dict[str, Any],
        sandbox_config: Optional[Dict[str, Any]]
    ) -> Any:
        """Execute MCP tool."""
        import asyncio

        server_name = manifest.mcp['server_name']
        tool_name = manifest.capabilities[0]['name']  # Use first capability

        # Get connection
        connection = self.mcp_manager.get_connection(server_name)
        if not connection:
            raise RuntimeError(f"MCP server not available: {server_name}")

        # Execute tool asynchronously
        loop = self.mcp_manager._get_or_create_event_loop()

        async def _call():
            result = await connection.call_tool(tool_name, arguments=input_data)
            # Extract content
            if hasattr(result, 'content'):
                if isinstance(result.content, list) and len(result.content) > 0:
                    first_content = result.content[0]
                    if hasattr(first_content, 'text'):
                        return first_content.text
                    return first_content
                return result.content
            return result

        return loop.run_until_complete(_call())

    def _generate_call_id(self, tool_id: str, version: str) -> str:
        """Generate unique call ID."""
        timestamp = datetime.utcnow().isoformat()
        combined = f"{tool_id}:{version}:{timestamp}"
        return hashlib.sha256(combined.encode()).hexdigest()[:16]

    def _hash_input(self, input_data: Dict[str, Any]) -> str:
        """Hash input data for provenance."""
        stable_json = json.dumps(input_data, sort_keys=True)
        return hashlib.sha256(stable_json.encode()).hexdigest()

    def _log_provenance(
        self,
        call_id: str,
        provenance: Dict[str, Any],
        metrics: Dict[str, Any],
        result: Any
    ):
        """Log provenance record to disk."""
        try:
            log_file = self.log_dir / f"{call_id}.json"

            log_record = {
                'provenance': provenance,
                'metrics': metrics,
                'result_hash': self._hash_result(result)
            }

            with open(log_file, 'w') as f:
                json.dump(log_record, f, indent=2)

            logger.debug(f"Logged provenance: {call_id}")

        except Exception as e:
            logger.error(f"Failed to log provenance: {e}")

    def _hash_result(self, result: Any) -> str:
        """Hash result for provenance."""
        try:
            result_str = json.dumps(result, sort_keys=True)
            return hashlib.sha256(result_str.encode()).hexdigest()
        except:
            result_str = str(result)
            return hashlib.sha256(result_str.encode()).hexdigest()

    def _error_result(self, call_id: str, error: str) -> Dict[str, Any]:
        """Create error result."""
        return {
            'success': False,
            'result': None,
            'provenance': {
                'call_id': call_id,
                'error': error
            },
            'metrics': {
                'success': False
            },
            'errors': [error]
        }
