#!/usr/bin/env python3
"""
Bulk Data Store Tool
Provides high-level bulk data storage using Postgres for logs, bugs, ancestry, etc.
Complements RAG by handling detailed bulk data while RAG does semantic search.
"""
import json
import sys
import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import logging
from pathlib import Path

# Load .env file if it exists
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    # dotenv not available, will use system environment variables
    pass

# Import the postgres client
from postgres_client import PostgresClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BulkDataStore:
    """High-level bulk data storage operations."""

    @staticmethod
    def initialize_schema() -> Dict[str, Any]:
        """
        Initialize database schema for bulk data storage.

        Creates tables for:
        - tool_logs: Detailed log messages
        - tool_bugs: Bug reports and histories
        - tool_ancestry: Tool lineage and relationships
        - tool_performance: Performance data
        - generated_tools: Generated tool definitions and code
        """
        schemas = [
            # Tool logs table
            """
            CREATE TABLE IF NOT EXISTS tool_logs (
                id SERIAL PRIMARY KEY,
                tool_id VARCHAR(255) NOT NULL,
                log_level VARCHAR(50) NOT NULL,
                message TEXT NOT NULL,
                details JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_tool_logs_tool_id (tool_id),
                INDEX idx_tool_logs_level (log_level),
                INDEX idx_tool_logs_created_at (created_at DESC)
            )
            """,

            # Bug reports table
            """
            CREATE TABLE IF NOT EXISTS tool_bugs (
                id SERIAL PRIMARY KEY,
                bug_id VARCHAR(255) UNIQUE NOT NULL,
                tool_id VARCHAR(255) NOT NULL,
                severity VARCHAR(50) NOT NULL,
                message TEXT NOT NULL,
                stack_trace TEXT,
                details JSONB,
                resolved BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved_at TIMESTAMP,
                INDEX idx_tool_bugs_tool_id (tool_id),
                INDEX idx_tool_bugs_severity (severity),
                INDEX idx_tool_bugs_resolved (resolved)
            )
            """,

            # Tool ancestry/lineage table
            """
            CREATE TABLE IF NOT EXISTS tool_ancestry (
                id SERIAL PRIMARY KEY,
                parent_tool_id VARCHAR(255) NOT NULL,
                child_tool_id VARCHAR(255) NOT NULL,
                relationship_type VARCHAR(100) NOT NULL,
                details JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_tool_ancestry_parent (parent_tool_id),
                INDEX idx_tool_ancestry_child (child_tool_id),
                INDEX idx_tool_ancestry_type (relationship_type)
            )
            """,

            # Performance data table
            """
            CREATE TABLE IF NOT EXISTS tool_performance (
                id SERIAL PRIMARY KEY,
                tool_id VARCHAR(255) NOT NULL,
                metric_name VARCHAR(100) NOT NULL,
                metric_value NUMERIC,
                unit VARCHAR(50),
                details JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_tool_perf_tool_id (tool_id),
                INDEX idx_tool_perf_metric (metric_name),
                INDEX idx_tool_perf_created_at (created_at DESC)
            )
            """,

            # Generated tools table
            """
            CREATE TABLE IF NOT EXISTS generated_tools (
                id SERIAL PRIMARY KEY,
                tool_id VARCHAR(255) UNIQUE NOT NULL,
                tool_name VARCHAR(255) NOT NULL,
                tool_type VARCHAR(50) NOT NULL,
                tool_yaml TEXT,
                tool_code TEXT,
                metadata JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_generated_tools_type (tool_type),
                INDEX idx_generated_tools_created_at (created_at DESC)
            )
            """
        ]

        results = []
        for schema in schemas:
            try:
                PostgresClient.execute(schema)
                table_name = schema.split("TABLE IF NOT EXISTS")[1].split("(")[0].strip()
                results.append({"table": table_name, "status": "created"})
            except Exception as e:
                logger.error(f"Failed to create schema: {e}")
                results.append({"table": "unknown", "status": "failed", "error": str(e)})

        return {"success": True, "data": results, "count": len(results)}

    @staticmethod
    def store_log(tool_id: str, log_level: str, message: str, details: Optional[Dict] = None) -> Dict[str, Any]:
        """Store a detailed log message."""
        data = {
            "tool_id": tool_id,
            "log_level": log_level.lower(),
            "message": message,
            "details": json.dumps(details) if details else None,
            "created_at": datetime.now(timezone.utc)
        }

        rows = PostgresClient.insert("tool_logs", data)
        return {"success": True, "count": rows}

    @staticmethod
    def store_bug(
        bug_id: str,
        tool_id: str,
        severity: str,
        message: str,
        stack_trace: Optional[str] = None,
        details: Optional[Dict] = None,
        resolved: bool = False
    ) -> Dict[str, Any]:
        """Store a bug report with full history."""
        data = {
            "bug_id": bug_id,
            "tool_id": tool_id,
            "severity": severity.lower(),
            "message": message,
            "stack_trace": stack_trace,
            "details": json.dumps(details) if details else None,
            "resolved": resolved,
            "created_at": datetime.now(timezone.utc)
        }

        if resolved:
            data["resolved_at"] = datetime.now(timezone.utc)

        rows = PostgresClient.insert("tool_bugs", data)
        return {"success": True, "count": rows}

    @staticmethod
    def store_ancestry(
        parent_tool_id: str,
        child_tool_id: str,
        relationship_type: str,
        details: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Store tool ancestry/lineage information."""
        data = {
            "parent_tool_id": parent_tool_id,
            "child_tool_id": child_tool_id,
            "relationship_type": relationship_type,
            "details": json.dumps(details) if details else None,
            "created_at": datetime.now(timezone.utc)
        }

        rows = PostgresClient.insert("tool_ancestry", data)
        return {"success": True, "count": rows}

    @staticmethod
    def store_perf_data(
        tool_id: str,
        metric_name: str,
        metric_value: float,
        unit: str = "",
        details: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Store performance data."""
        data = {
            "tool_id": tool_id,
            "metric_name": metric_name,
            "metric_value": metric_value,
            "unit": unit,
            "details": json.dumps(details) if details else None,
            "created_at": datetime.now(timezone.utc)
        }

        rows = PostgresClient.insert("tool_performance", data)
        return {"success": True, "count": rows}

    @staticmethod
    def store_tool(
        tool_id: str,
        tool_name: str,
        tool_type: str,
        tool_yaml: Optional[str] = None,
        tool_code: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Store a generated tool with its definition and code."""
        data = {
            "tool_id": tool_id,
            "tool_name": tool_name,
            "tool_type": tool_type,
            "tool_yaml": tool_yaml,
            "tool_code": tool_code,
            "metadata": json.dumps(metadata) if metadata else None,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }

        # Try insert, if tool exists, update it
        try:
            rows = PostgresClient.insert("generated_tools", data)
            return {"success": True, "count": rows, "action": "inserted"}
        except Exception as e:
            if "duplicate key" in str(e).lower():
                # Update existing tool
                update_data = {k: v for k, v in data.items() if k != "tool_id" and k != "created_at"}
                rows = PostgresClient.update("generated_tools", update_data, {"tool_id": tool_id})
                return {"success": True, "count": rows, "action": "updated"}
            else:
                raise

    @staticmethod
    def query_logs(filters: Optional[Dict] = None, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
        """Query tool logs with filters."""
        where_clause = ""
        params = {}

        if filters:
            conditions = []
            for key, value in filters.items():
                conditions.append(f"{key} = %({key})s")
                params[key] = value
            where_clause = "WHERE " + " AND ".join(conditions)

        sql = f"SELECT * FROM tool_logs {where_clause} ORDER BY created_at DESC LIMIT %(limit)s OFFSET %(offset)s"
        params.update({"limit": limit, "offset": offset})

        results = PostgresClient.query(sql, params)
        return {"success": True, "data": results, "count": len(results)}

    @staticmethod
    def query_bugs(filters: Optional[Dict] = None, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
        """Query bug reports with filters."""
        where_clause = ""
        params = {}

        if filters:
            conditions = []
            for key, value in filters.items():
                conditions.append(f"{key} = %({key})s")
                params[key] = value
            where_clause = "WHERE " + " AND ".join(conditions)

        sql = f"SELECT * FROM tool_bugs {where_clause} ORDER BY created_at DESC LIMIT %(limit)s OFFSET %(offset)s"
        params.update({"limit": limit, "offset": offset})

        results = PostgresClient.query(sql, params)
        return {"success": True, "data": results, "count": len(results)}

    @staticmethod
    def get_ancestry(tool_id: str, depth: int = 10) -> Dict[str, Any]:
        """
        Get full ancestry tree for a tool (parents and children).

        Args:
            tool_id: Tool ID to get ancestry for
            depth: Maximum depth to traverse

        Returns:
            Dict with parents and children lists
        """
        # Get all ancestors (parents)
        parents_sql = """
            WITH RECURSIVE ancestry AS (
                SELECT parent_tool_id, child_tool_id, relationship_type, details, 1 as level
                FROM tool_ancestry
                WHERE child_tool_id = %(tool_id)s
                UNION ALL
                SELECT ta.parent_tool_id, ta.child_tool_id, ta.relationship_type, ta.details, a.level + 1
                FROM tool_ancestry ta
                INNER JOIN ancestry a ON ta.child_tool_id = a.parent_tool_id
                WHERE a.level < %(depth)s
            )
            SELECT * FROM ancestry ORDER BY level
        """

        # Get all descendants (children)
        children_sql = """
            WITH RECURSIVE descendants AS (
                SELECT parent_tool_id, child_tool_id, relationship_type, details, 1 as level
                FROM tool_ancestry
                WHERE parent_tool_id = %(tool_id)s
                UNION ALL
                SELECT ta.parent_tool_id, ta.child_tool_id, ta.relationship_type, ta.details, d.level + 1
                FROM tool_ancestry ta
                INNER JOIN descendants d ON ta.parent_tool_id = d.child_tool_id
                WHERE d.level < %(depth)s
            )
            SELECT * FROM descendants ORDER BY level
        """

        parents = PostgresClient.query(parents_sql, {"tool_id": tool_id, "depth": depth})
        children = PostgresClient.query(children_sql, {"tool_id": tool_id, "depth": depth})

        return {
            "success": True,
            "data": {
                "tool_id": tool_id,
                "parents": parents,
                "children": children
            },
            "count": len(parents) + len(children)
        }


def main():
    """Main entry point for the tool."""
    try:
        # Read input from stdin
        input_data = json.loads(sys.stdin.read())
        operation = input_data.get("operation")

        if operation == "initialize_schema":
            result = BulkDataStore.initialize_schema()

        elif operation == "store_log":
            result = BulkDataStore.store_log(
                input_data["tool_id"],
                input_data["log_level"],
                input_data["message"],
                input_data.get("details")
            )

        elif operation == "store_bug":
            result = BulkDataStore.store_bug(
                input_data["bug_id"],
                input_data["tool_id"],
                input_data["severity"],
                input_data["message"],
                input_data.get("stack_trace"),
                input_data.get("details"),
                input_data.get("resolved", False)
            )

        elif operation == "store_ancestry":
            result = BulkDataStore.store_ancestry(
                input_data["parent_tool_id"],
                input_data["child_tool_id"],
                input_data["relationship_type"],
                input_data.get("details")
            )

        elif operation == "store_perf_data":
            result = BulkDataStore.store_perf_data(
                input_data["tool_id"],
                input_data["metric_name"],
                input_data["metric_value"],
                input_data.get("unit", ""),
                input_data.get("details")
            )

        elif operation == "store_tool":
            result = BulkDataStore.store_tool(
                input_data["tool_id"],
                input_data["tool_name"],
                input_data["tool_type"],
                input_data.get("tool_yaml"),
                input_data.get("tool_code"),
                input_data.get("metadata")
            )

        elif operation == "query_logs":
            result = BulkDataStore.query_logs(
                input_data.get("filters"),
                input_data.get("limit", 100),
                input_data.get("offset", 0)
            )

        elif operation == "query_bugs":
            result = BulkDataStore.query_bugs(
                input_data.get("filters"),
                input_data.get("limit", 100),
                input_data.get("offset", 0)
            )

        elif operation == "get_ancestry":
            result = BulkDataStore.get_ancestry(
                input_data["tool_id"],
                input_data.get("depth", 10)
            )

        else:
            result = {
                "success": False,
                "error": f"Unknown operation: {operation}"
            }

        print(json.dumps(result))

    except Exception as e:
        logger.error(f"Error in bulk_data_store: {e}", exc_info=True)
        print(json.dumps({
            "success": False,
            "error": str(e)
        }))
        sys.exit(1)


if __name__ == "__main__":
    main()
