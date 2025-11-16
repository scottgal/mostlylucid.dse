"""
SQLite persistence layer for the scheduler system.

Manages schedules, execution history, and results.
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from contextlib import contextmanager


class SchedulerDB:
    """Database manager for scheduler persistence."""

    def __init__(self, db_path: str = None):
        """Initialize the scheduler database.

        Args:
            db_path: Path to SQLite database file. Defaults to scheduler.db in project root.
        """
        if db_path is None:
            db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'scheduler.db')

        self.db_path = db_path
        self._initialize_db()

    @contextmanager
    def _get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _initialize_db(self):
        """Create database tables if they don't exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Schedules table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS schedules (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    cron_expression TEXT NOT NULL,
                    tool_name TEXT NOT NULL,
                    tool_inputs TEXT,
                    status TEXT NOT NULL DEFAULT 'active',
                    created_at TEXT NOT NULL,
                    last_run TEXT,
                    next_run TEXT,
                    run_count INTEGER DEFAULT 0
                )
            ''')

            # Executions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS executions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    schedule_id TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    status TEXT NOT NULL,
                    result TEXT,
                    error TEXT,
                    FOREIGN KEY (schedule_id) REFERENCES schedules (id)
                        ON DELETE CASCADE
                )
            ''')

            # Create indexes for better query performance
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_schedules_status
                ON schedules(status)
            ''')

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_executions_schedule_id
                ON executions(schedule_id)
            ''')

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_executions_started_at
                ON executions(started_at DESC)
            ''')

    def create_schedule(
        self,
        schedule_id: str,
        name: str,
        description: str,
        cron_expression: str,
        tool_name: str,
        tool_inputs: Dict[str, Any],
        next_run: str = None
    ) -> Dict[str, Any]:
        """Create a new schedule.

        Args:
            schedule_id: Unique identifier for the schedule
            name: Human-readable name
            description: Natural language description (e.g., "every 20 minutes")
            cron_expression: CRON expression for scheduling
            tool_name: Name of the tool to execute
            tool_inputs: Dictionary of tool input parameters
            next_run: ISO format datetime string for next scheduled run

        Returns:
            Dictionary containing the created schedule
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.utcnow().isoformat()

            cursor.execute('''
                INSERT INTO schedules
                (id, name, description, cron_expression, tool_name, tool_inputs,
                 status, created_at, next_run)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                schedule_id,
                name,
                description,
                cron_expression,
                tool_name,
                json.dumps(tool_inputs),
                'active',
                now,
                next_run
            ))

            # Get the created schedule from the same connection
            cursor.execute('SELECT * FROM schedules WHERE id = ?', (schedule_id,))
            row = cursor.fetchone()
            return self._row_to_schedule(row) if row else None

    def get_schedule(self, schedule_id: str) -> Optional[Dict[str, Any]]:
        """Get a schedule by ID.

        Args:
            schedule_id: Unique identifier for the schedule

        Returns:
            Dictionary containing schedule data, or None if not found
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM schedules WHERE id = ?', (schedule_id,))
            row = cursor.fetchone()

            if row is None:
                return None

            return self._row_to_schedule(row)

    def list_schedules(
        self,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List schedules with optional filtering.

        Args:
            status: Filter by status ('active', 'paused', 'error')
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of schedule dictionaries
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            if status:
                cursor.execute('''
                    SELECT * FROM schedules
                    WHERE status = ?
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                ''', (status, limit, offset))
            else:
                cursor.execute('''
                    SELECT * FROM schedules
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                ''', (limit, offset))

            return [self._row_to_schedule(row) for row in cursor.fetchall()]

    def update_schedule_status(
        self,
        schedule_id: str,
        status: str,
        last_run: str = None,
        next_run: str = None
    ) -> bool:
        """Update schedule status and run times.

        Args:
            schedule_id: Unique identifier for the schedule
            status: New status ('active', 'paused', 'error')
            last_run: ISO format datetime string for last run
            next_run: ISO format datetime string for next run

        Returns:
            True if update succeeded, False if schedule not found
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            updates = ['status = ?']
            params = [status]

            if last_run is not None:
                updates.append('last_run = ?')
                params.append(last_run)

            if next_run is not None:
                updates.append('next_run = ?')
                params.append(next_run)

            params.append(schedule_id)

            cursor.execute(f'''
                UPDATE schedules
                SET {', '.join(updates)}
                WHERE id = ?
            ''', params)

            return cursor.rowcount > 0

    def increment_run_count(self, schedule_id: str):
        """Increment the run count for a schedule.

        Args:
            schedule_id: Unique identifier for the schedule
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE schedules
                SET run_count = run_count + 1
                WHERE id = ?
            ''', (schedule_id,))

    def delete_schedule(self, schedule_id: str) -> bool:
        """Delete a schedule and its execution history.

        Args:
            schedule_id: Unique identifier for the schedule

        Returns:
            True if deletion succeeded, False if schedule not found
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM schedules WHERE id = ?', (schedule_id,))
            return cursor.rowcount > 0

    def create_execution(
        self,
        schedule_id: str,
        status: str = 'running'
    ) -> int:
        """Create a new execution record.

        Args:
            schedule_id: ID of the schedule being executed
            status: Execution status ('running', 'success', 'failed')

        Returns:
            ID of the created execution record
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.utcnow().isoformat()

            cursor.execute('''
                INSERT INTO executions (schedule_id, started_at, status)
                VALUES (?, ?, ?)
            ''', (schedule_id, now, status))

            return cursor.lastrowid

    def update_execution(
        self,
        execution_id: int,
        status: str,
        result: Any = None,
        error: str = None
    ):
        """Update an execution record with results.

        Args:
            execution_id: ID of the execution record
            status: Final status ('success', 'failed')
            result: Execution result (will be JSON serialized)
            error: Error message if failed
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.utcnow().isoformat()

            result_json = json.dumps(result) if result is not None else None

            cursor.execute('''
                UPDATE executions
                SET finished_at = ?, status = ?, result = ?, error = ?
                WHERE id = ?
            ''', (now, status, result_json, error, execution_id))

    def get_execution_history(
        self,
        schedule_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get execution history for a schedule.

        Args:
            schedule_id: ID of the schedule
            limit: Maximum number of results

        Returns:
            List of execution dictionaries
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM executions
                WHERE schedule_id = ?
                ORDER BY started_at DESC
                LIMIT ?
            ''', (schedule_id, limit))

            return [self._row_to_execution(row) for row in cursor.fetchall()]

    def _row_to_schedule(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Convert a database row to a schedule dictionary."""
        return {
            'id': row['id'],
            'name': row['name'],
            'description': row['description'],
            'cron_expression': row['cron_expression'],
            'tool_name': row['tool_name'],
            'tool_inputs': json.loads(row['tool_inputs']) if row['tool_inputs'] else {},
            'status': row['status'],
            'created_at': row['created_at'],
            'last_run': row['last_run'],
            'next_run': row['next_run'],
            'run_count': row['run_count']
        }

    def _row_to_execution(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Convert a database row to an execution dictionary."""
        return {
            'id': row['id'],
            'schedule_id': row['schedule_id'],
            'started_at': row['started_at'],
            'finished_at': row['finished_at'],
            'status': row['status'],
            'result': json.loads(row['result']) if row['result'] else None,
            'error': row['error']
        }
