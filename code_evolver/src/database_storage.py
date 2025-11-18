"""
Database Storage Module
Integrates Postgres bulk data storage with the DiSE system.
Complements RAG by storing detailed bulk data while RAG handles semantic search.
"""
import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class DatabaseStorage:
    """
    Database storage integration for DiSE.

    Provides automatic storage of:
    - Generated tools (YAML + code)
    - Detailed log messages
    - Bug reports with stack traces
    - Tool ancestry/lineage
    - Performance metrics
    """

    def __init__(self, config_manager: Optional[Any] = None, tools_path: Optional[Path] = None):
        """
        Initialize database storage.

        Args:
            config_manager: Optional ConfigManager instance
            tools_path: Path to tools directory
        """
        self.config_manager = config_manager
        self.tools_path = tools_path or Path("./tools")
        self.enabled = False
        self.store_generated_tools = True

        # Load configuration
        if config_manager:
            try:
                db_config = config_manager.config.get("database", {})
                self.enabled = db_config.get("enabled", False)

                storage_strategy = db_config.get("storage_strategy", {})
                self.store_generated_tools = storage_strategy.get("store_generated_tools", True)

                # Set environment variables for Postgres connection
                if self.enabled:
                    os.environ["POSTGRES_HOST"] = db_config.get("host", "localhost")
                    os.environ["POSTGRES_PORT"] = str(db_config.get("port", 5432))
                    os.environ["POSTGRES_DB"] = db_config.get("database", "dise_data")
                    os.environ["POSTGRES_USER"] = db_config.get("user", "dise")
                    os.environ["POSTGRES_PASSWORD"] = db_config.get("password", "dise123")

                    logger.info("Database storage enabled")

                    # Initialize schema on first run
                    self._initialize_schema()
            except Exception as e:
                logger.warning(f"Could not load database config: {e}")
                self.enabled = False

    def _initialize_schema(self):
        """Initialize database schema using bulk_data_store tool."""
        if not self.enabled:
            return

        try:
            # Call the bulk_data_store tool to initialize schema
            tool_path = self.tools_path / "executable" / "bulk_data_store.py"

            if not tool_path.exists():
                logger.warning(f"bulk_data_store.py not found at {tool_path}")
                return

            input_data = json.dumps({"operation": "initialize_schema"})

            result = subprocess.run(
                ["python", str(tool_path)],
                input=input_data,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                response = json.loads(result.stdout)
                if response.get("success"):
                    logger.info("Database schema initialized successfully")
                else:
                    logger.error(f"Schema initialization failed: {response.get('error')}")
            else:
                logger.error(f"Schema initialization error: {result.stderr}")

        except Exception as e:
            logger.warning(f"Could not initialize database schema: {e}")

    def _call_bulk_data_store(self, operation: str, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Call the bulk_data_store tool.

        Args:
            operation: Operation to perform
            **kwargs: Additional parameters

        Returns:
            Response from the tool or None if failed
        """
        if not self.enabled:
            return None

        try:
            tool_path = self.tools_path / "executable" / "bulk_data_store.py"

            if not tool_path.exists():
                return None

            input_data = json.dumps({"operation": operation, **kwargs})

            result = subprocess.run(
                ["python", str(tool_path)],
                input=input_data,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                return json.loads(result.stdout)
            else:
                logger.error(f"bulk_data_store error: {result.stderr}")
                return None

        except Exception as e:
            logger.error(f"Error calling bulk_data_store: {e}")
            return None

    def store_generated_tool(
        self,
        tool_id: str,
        tool_name: str,
        tool_type: str,
        tool_yaml: Optional[str] = None,
        tool_code: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        Store a generated tool in the database.

        Args:
            tool_id: Tool identifier
            tool_name: Tool name
            tool_type: Tool type (llm, executable, etc.)
            tool_yaml: YAML definition
            tool_code: Implementation code
            metadata: Additional metadata

        Returns:
            True if successful
        """
        if not self.enabled or not self.store_generated_tools:
            return False

        try:
            # Read YAML and code files if not provided
            if tool_yaml is None:
                yaml_path = self.tools_path / f"{tool_type}" / f"{tool_id}.yaml"
                if yaml_path.exists():
                    tool_yaml = yaml_path.read_text()

            if tool_code is None:
                code_path = self.tools_path / f"{tool_type}" / f"{tool_id}.py"
                if code_path.exists():
                    tool_code = code_path.read_text()

            response = self._call_bulk_data_store(
                "store_tool",
                tool_id=tool_id,
                tool_name=tool_name,
                tool_type=tool_type,
                tool_yaml=tool_yaml,
                tool_code=tool_code,
                metadata=metadata or {}
            )

            if response and response.get("success"):
                logger.info(f"Stored generated tool in database: {tool_id}")
                return True
            else:
                logger.warning(f"Failed to store tool in database: {response}")
                return False

        except Exception as e:
            logger.error(f"Error storing generated tool: {e}")
            return False

    def store_log(
        self,
        tool_id: str,
        log_level: str,
        message: str,
        details: Optional[Dict] = None
    ) -> bool:
        """Store a detailed log message."""
        if not self.enabled:
            return False

        response = self._call_bulk_data_store(
            "store_log",
            tool_id=tool_id,
            log_level=log_level,
            message=message,
            details=details
        )

        return response and response.get("success", False)

    def store_bug(
        self,
        bug_id: str,
        tool_id: str,
        severity: str,
        message: str,
        stack_trace: Optional[str] = None,
        details: Optional[Dict] = None
    ) -> bool:
        """Store a bug report."""
        if not self.enabled:
            return False

        response = self._call_bulk_data_store(
            "store_bug",
            bug_id=bug_id,
            tool_id=tool_id,
            severity=severity,
            message=message,
            stack_trace=stack_trace,
            details=details
        )

        return response and response.get("success", False)

    def store_ancestry(
        self,
        parent_tool_id: str,
        child_tool_id: str,
        relationship_type: str,
        details: Optional[Dict] = None
    ) -> bool:
        """Store tool ancestry/lineage."""
        if not self.enabled:
            return False

        response = self._call_bulk_data_store(
            "store_ancestry",
            parent_tool_id=parent_tool_id,
            child_tool_id=child_tool_id,
            relationship_type=relationship_type,
            details=details
        )

        return response and response.get("success", False)

    def store_performance_data(
        self,
        tool_id: str,
        metric_name: str,
        metric_value: float,
        unit: str = "",
        details: Optional[Dict] = None
    ) -> bool:
        """Store performance metrics."""
        if not self.enabled:
            return False

        response = self._call_bulk_data_store(
            "store_perf_data",
            tool_id=tool_id,
            metric_name=metric_name,
            metric_value=metric_value,
            unit=unit,
            details=details
        )

        return response and response.get("success", False)

    def query_logs(
        self,
        filters: Optional[Dict] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict]:
        """Query log messages."""
        if not self.enabled:
            return []

        response = self._call_bulk_data_store(
            "query_logs",
            filters=filters,
            limit=limit,
            offset=offset
        )

        if response and response.get("success"):
            return response.get("data", [])
        return []

    def query_bugs(
        self,
        filters: Optional[Dict] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict]:
        """Query bug reports."""
        if not self.enabled:
            return []

        response = self._call_bulk_data_store(
            "query_bugs",
            filters=filters,
            limit=limit,
            offset=offset
        )

        if response and response.get("success"):
            return response.get("data", [])
        return []

    def get_tool_ancestry(self, tool_id: str, depth: int = 10) -> Optional[Dict]:
        """Get full ancestry tree for a tool."""
        if not self.enabled:
            return None

        response = self._call_bulk_data_store(
            "get_ancestry",
            tool_id=tool_id,
            depth=depth
        )

        if response and response.get("success"):
            return response.get("data")
        return None
