#!/usr/bin/env python3
"""
Postgres Client Tool
Provides PostgreSQL database connectivity and query execution.
"""
import json
import sys
import os
from pathlib import Path
import psycopg2
from psycopg2 import pool, sql
from psycopg2.extras import RealDictCursor
from typing import Dict, Any, List, Optional, Tuple
from contextlib import contextmanager
import logging

# Load .env file if it exists
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    # dotenv not available, will use system environment variables
    pass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PostgresClient:
    """PostgreSQL client with connection pooling."""

    _connection_pool = None

    @classmethod
    def get_pool(cls):
        """Get or create connection pool."""
        if cls._connection_pool is None:
            # Get connection info from environment variables
            db_config = {
                "host": os.getenv("POSTGRES_HOST", "localhost"),
                "port": int(os.getenv("POSTGRES_PORT", "5432")),
                "database": os.getenv("POSTGRES_DB", "dise"),
                "user": os.getenv("POSTGRES_USER", "postgres"),
                "password": os.getenv("POSTGRES_PASSWORD", ""),
            }

            try:
                cls._connection_pool = pool.SimpleConnectionPool(
                    minconn=1,
                    maxconn=10,
                    **db_config
                )
                logger.info("PostgreSQL connection pool created")
            except Exception as e:
                logger.error(f"Failed to create connection pool: {e}")
                raise

        return cls._connection_pool

    @classmethod
    @contextmanager
    def get_connection(cls):
        """Get a connection from the pool."""
        conn_pool = cls.get_pool()
        conn = conn_pool.getconn()
        try:
            yield conn
        finally:
            conn_pool.putconn(conn)

    @classmethod
    def query(cls, sql_query: str, params: Optional[Dict] = None, fetch_one: bool = False) -> List[Dict[str, Any]]:
        """
        Execute a SELECT query and return results.

        Args:
            sql_query: SQL query string
            params: Query parameters (dict for named parameters)
            fetch_one: Return only one result

        Returns:
            List of result dictionaries
        """
        with cls.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql_query, params)
                if fetch_one:
                    result = cur.fetchone()
                    return [dict(result)] if result else []
                else:
                    results = cur.fetchall()
                    return [dict(row) for row in results]

    @classmethod
    def execute(cls, sql_query: str, params: Optional[Dict] = None) -> int:
        """
        Execute a non-SELECT query (INSERT, UPDATE, DELETE, DDL).

        Args:
            sql_query: SQL statement
            params: Query parameters

        Returns:
            Number of rows affected
        """
        with cls.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql_query, params)
                conn.commit()
                return cur.rowcount if cur.rowcount else 0

    @classmethod
    def insert(cls, table: str, data: Dict[str, Any]) -> int:
        """
        Insert a record into a table.

        Args:
            table: Table name
            data: Dictionary of column: value pairs

        Returns:
            Number of rows inserted
        """
        columns = list(data.keys())
        values = list(data.values())

        query = sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
            sql.Identifier(table),
            sql.SQL(', ').join(map(sql.Identifier, columns)),
            sql.SQL(', ').join(sql.Placeholder() * len(values))
        )

        return cls.execute(query.as_string(cls.get_pool().getconn()), values)

    @classmethod
    def update(cls, table: str, data: Dict[str, Any], where: Dict[str, Any]) -> int:
        """
        Update records in a table.

        Args:
            table: Table name
            data: Dictionary of column: value pairs to update
            where: WHERE clause conditions

        Returns:
            Number of rows updated
        """
        set_clause = sql.SQL(', ').join(
            sql.SQL("{} = {}").format(sql.Identifier(k), sql.Placeholder())
            for k in data.keys()
        )

        where_clause = sql.SQL(' AND ').join(
            sql.SQL("{} = {}").format(sql.Identifier(k), sql.Placeholder())
            for k in where.keys()
        )

        query = sql.SQL("UPDATE {} SET {} WHERE {}").format(
            sql.Identifier(table),
            set_clause,
            where_clause
        )

        params = list(data.values()) + list(where.values())
        return cls.execute(query.as_string(cls.get_pool().getconn()), params)

    @classmethod
    def delete(cls, table: str, where: Dict[str, Any]) -> int:
        """
        Delete records from a table.

        Args:
            table: Table name
            where: WHERE clause conditions

        Returns:
            Number of rows deleted
        """
        where_clause = sql.SQL(' AND ').join(
            sql.SQL("{} = {}").format(sql.Identifier(k), sql.Placeholder())
            for k in where.keys()
        )

        query = sql.SQL("DELETE FROM {} WHERE {}").format(
            sql.Identifier(table),
            where_clause
        )

        return cls.execute(query.as_string(cls.get_pool().getconn()), list(where.values()))


def main():
    """Main entry point for the tool."""
    try:
        # Read input from stdin
        input_data = json.loads(sys.stdin.read())

        operation = input_data.get("operation")

        if operation == "query":
            results = PostgresClient.query(
                input_data["sql"],
                input_data.get("params"),
                input_data.get("fetch_one", False)
            )
            print(json.dumps({
                "success": True,
                "data": results,
                "rows_affected": len(results)
            }))

        elif operation == "execute":
            rows_affected = PostgresClient.execute(
                input_data["sql"],
                input_data.get("params")
            )
            print(json.dumps({
                "success": True,
                "rows_affected": rows_affected
            }))

        elif operation == "insert":
            rows_affected = PostgresClient.insert(
                input_data["table"],
                input_data["data"]
            )
            print(json.dumps({
                "success": True,
                "rows_affected": rows_affected
            }))

        elif operation == "update":
            rows_affected = PostgresClient.update(
                input_data["table"],
                input_data["data"],
                input_data["where"]
            )
            print(json.dumps({
                "success": True,
                "rows_affected": rows_affected
            }))

        elif operation == "delete":
            rows_affected = PostgresClient.delete(
                input_data["table"],
                input_data["where"]
            )
            print(json.dumps({
                "success": True,
                "rows_affected": rows_affected
            }))

        else:
            print(json.dumps({
                "success": False,
                "error": f"Unknown operation: {operation}"
            }))
            sys.exit(1)

    except Exception as e:
        logger.error(f"Error in postgres_client: {e}", exc_info=True)
        print(json.dumps({
            "success": False,
            "error": str(e)
        }))
        sys.exit(1)


if __name__ == "__main__":
    main()
