"""
Hybrid Debug Store: LMDB (fast writes) + DuckDB (analytics)

Provides ultra-fast request/response recording for debug sessions with
rich analytics capabilities for optimization and analysis.

Architecture:
- LMDB: Write-optimized layer for raw request/response data
- DuckDB: Analytics-optimized layer for queries and aggregations
- Background sync: Periodically transfers LMDB data to DuckDB
"""

import json
import lmdb
import duckdb
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
import uuid
import msgpack  # More efficient than JSON for binary storage


@dataclass
class DebugRecord:
    """Represents a single debug request/response record"""
    id: str
    timestamp: str
    context_type: str  # 'tool', 'workflow', 'step', 'node'
    context_id: str  # The specific tool/workflow/step/node ID
    context_name: str
    parent_context: Optional[str]  # For hierarchical tracking
    request_data: Dict[str, Any]
    response_data: Dict[str, Any]
    metadata: Dict[str, Any]  # Flexible metadata storage

    # Performance metrics (OTEL-like)
    duration_ms: float
    memory_mb: float
    cpu_percent: float

    # Status
    status: str  # 'success', 'error', 'timeout', 'retry'
    error: Optional[str] = None

    # Code tracking
    code_snapshot: Optional[str] = None  # The code that was executed
    code_hash: Optional[str] = None  # Hash for deduplication
    variant_id: Optional[str] = None  # Links to code variants


class DebugStore:
    """
    Hybrid debug store with LMDB for fast writes and DuckDB for analytics.

    Usage:
        store = DebugStore(session_id="workflow_123")

        # Fast write
        record_id = store.write_record(
            context_type="tool",
            context_id="http_fetch",
            request_data={...},
            response_data={...},
            duration_ms=123.45
        )

        # Analytics
        stats = store.query_analytics(
            "SELECT context_name, AVG(duration_ms) FROM records GROUP BY context_name"
        )

        # Export for analysis
        data = store.export_for_analysis(context_type="tool", limit=100)
    """

    def __init__(
        self,
        session_id: str,
        base_path: str = "debug_data",
        auto_sync_interval: int = 30,  # seconds
        enable_auto_sync: bool = True
    ):
        """
        Initialize hybrid debug store.

        Args:
            session_id: Unique identifier for this debug session
            base_path: Base directory for storing debug data
            auto_sync_interval: How often to sync LMDB to DuckDB (seconds)
            enable_auto_sync: Whether to automatically sync in background
        """
        self.session_id = session_id
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

        # LMDB setup (fast writes)
        self.lmdb_path = self.base_path / f"{session_id}.lmdb"
        self.lmdb_env = lmdb.open(
            str(self.lmdb_path),
            map_size=10 * 1024 * 1024 * 1024,  # 10GB max
            max_dbs=10,
            writemap=True,
            sync=False,  # Async for speed, fsync on close
            metasync=False
        )

        # Create LMDB databases (sub-databases within the environment)
        self.records_db = self.lmdb_env.open_db(b'records')
        self.index_db = self.lmdb_env.open_db(b'index')  # For quick lookups
        self.pending_db = self.lmdb_env.open_db(b'pending_sync')  # Tracks what needs sync

        # DuckDB setup (analytics)
        self.duckdb_path = self.base_path / f"{session_id}.duckdb"
        self.duckdb_conn = duckdb.connect(str(self.duckdb_path))
        self._init_duckdb_schema()

        # Sync tracking
        self._last_sync_id = self._get_last_sync_id()
        self._sync_lock = threading.Lock()
        self._sync_thread = None
        self._stop_sync = threading.Event()

        # Start auto-sync if enabled
        if enable_auto_sync:
            self._start_auto_sync(auto_sync_interval)

    def _init_duckdb_schema(self):
        """Initialize DuckDB schema for analytics"""
        self.duckdb_conn.execute("""
            CREATE TABLE IF NOT EXISTS records (
                id VARCHAR PRIMARY KEY,
                timestamp TIMESTAMP,
                context_type VARCHAR,
                context_id VARCHAR,
                context_name VARCHAR,
                parent_context VARCHAR,
                request_data JSON,
                response_data JSON,
                metadata JSON,
                duration_ms DOUBLE,
                memory_mb DOUBLE,
                cpu_percent DOUBLE,
                status VARCHAR,
                error TEXT,
                code_snapshot TEXT,
                code_hash VARCHAR,
                variant_id VARCHAR
            )
        """)

        # Create indices for fast queries
        self.duckdb_conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_context_type ON records(context_type)
        """)
        self.duckdb_conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_context_id ON records(context_id)
        """)
        self.duckdb_conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp ON records(timestamp)
        """)
        self.duckdb_conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_status ON records(status)
        """)
        self.duckdb_conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_variant ON records(variant_id)
        """)

        # Create materialized views for common queries
        self.duckdb_conn.execute("""
            CREATE OR REPLACE VIEW performance_summary AS
            SELECT
                context_type,
                context_name,
                COUNT(*) as total_calls,
                AVG(duration_ms) as avg_duration,
                MIN(duration_ms) as min_duration,
                MAX(duration_ms) as max_duration,
                AVG(memory_mb) as avg_memory,
                AVG(cpu_percent) as avg_cpu,
                SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as error_count,
                SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success_count
            FROM records
            GROUP BY context_type, context_name
        """)

    def write_record(
        self,
        context_type: str,
        context_id: str,
        context_name: str,
        request_data: Dict[str, Any],
        response_data: Dict[str, Any],
        duration_ms: float,
        memory_mb: float = 0.0,
        cpu_percent: float = 0.0,
        status: str = "success",
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        parent_context: Optional[str] = None,
        code_snapshot: Optional[str] = None,
        code_hash: Optional[str] = None,
        variant_id: Optional[str] = None
    ) -> str:
        """
        Write a debug record (ultra-fast LMDB write).

        Returns:
            record_id: Unique ID for this record
        """
        record_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()

        record = DebugRecord(
            id=record_id,
            timestamp=timestamp,
            context_type=context_type,
            context_id=context_id,
            context_name=context_name,
            parent_context=parent_context,
            request_data=request_data,
            response_data=response_data,
            metadata=metadata or {},
            duration_ms=duration_ms,
            memory_mb=memory_mb,
            cpu_percent=cpu_percent,
            status=status,
            error=error,
            code_snapshot=code_snapshot,
            code_hash=code_hash,
            variant_id=variant_id
        )

        # Serialize with msgpack (faster and more compact than JSON)
        record_bytes = msgpack.packb(asdict(record), use_bin_type=True)

        with self.lmdb_env.begin(write=True) as txn:
            # Write main record
            txn.put(record_id.encode(), record_bytes, db=self.records_db)

            # Update index for quick lookups by context
            index_key = f"{context_type}:{context_id}:{record_id}".encode()
            txn.put(index_key, record_id.encode(), db=self.index_db)

            # Mark as pending sync
            txn.put(record_id.encode(), b'1', db=self.pending_db)

        return record_id

    def get_record(self, record_id: str) -> Optional[DebugRecord]:
        """Retrieve a specific record (from LMDB for speed)"""
        with self.lmdb_env.begin(db=self.records_db) as txn:
            record_bytes = txn.get(record_id.encode())
            if record_bytes:
                record_dict = msgpack.unpackb(record_bytes, raw=False)
                return DebugRecord(**record_dict)
        return None

    def get_records_by_context(
        self,
        context_type: str,
        context_id: str,
        limit: int = 100
    ) -> List[DebugRecord]:
        """Get records for a specific context (fast LMDB lookup)"""
        records = []
        prefix = f"{context_type}:{context_id}:".encode()

        with self.lmdb_env.begin(db=self.index_db) as txn:
            cursor = txn.cursor()
            if cursor.set_range(prefix):
                count = 0
                for key, value in cursor:
                    if not key.startswith(prefix) or count >= limit:
                        break

                    record_id = value.decode()
                    record = self.get_record(record_id)
                    if record:
                        records.append(record)
                    count += 1

        return records

    def sync_to_duckdb(self, batch_size: int = 1000) -> int:
        """
        Sync pending LMDB records to DuckDB.

        Returns:
            Number of records synced
        """
        with self._sync_lock:
            synced_count = 0
            batch = []

            with self.lmdb_env.begin(write=True) as txn:
                cursor = txn.cursor(db=self.pending_db)

                for record_id_bytes, _ in cursor:
                    record_id = record_id_bytes.decode()

                    # Get the full record
                    record_bytes = txn.get(record_id.encode(), db=self.records_db)
                    if not record_bytes:
                        continue

                    record_dict = msgpack.unpackb(record_bytes, raw=False)
                    batch.append(record_dict)

                    # Remove from pending
                    cursor.delete()

                    # Insert batch when full
                    if len(batch) >= batch_size:
                        self._insert_batch_to_duckdb(batch)
                        synced_count += len(batch)
                        batch = []

                # Insert remaining
                if batch:
                    self._insert_batch_to_duckdb(batch)
                    synced_count += len(batch)

            return synced_count

    def _insert_batch_to_duckdb(self, records: List[Dict[str, Any]]):
        """Insert a batch of records into DuckDB"""
        if not records:
            return

        # Convert to format DuckDB can insert efficiently
        placeholders = ", ".join(["?" for _ in range(17)])  # 17 columns

        values = []
        for record in records:
            values.append((
                record['id'],
                record['timestamp'],
                record['context_type'],
                record['context_id'],
                record['context_name'],
                record['parent_context'],
                json.dumps(record['request_data']),
                json.dumps(record['response_data']),
                json.dumps(record['metadata']),
                record['duration_ms'],
                record['memory_mb'],
                record['cpu_percent'],
                record['status'],
                record['error'],
                record['code_snapshot'],
                record['code_hash'],
                record['variant_id']
            ))

        # Use executemany for batch insert
        self.duckdb_conn.executemany(f"""
            INSERT OR REPLACE INTO records VALUES ({placeholders})
        """, values)

    def query_analytics(self, sql: str, params: Optional[List] = None):
        """
        Execute SQL query on DuckDB analytics layer.

        Returns:
            DuckDB result (can be converted to pandas with .df())
        """
        if params:
            return self.duckdb_conn.execute(sql, params)
        return self.duckdb_conn.execute(sql)

    def get_performance_summary(self):
        """Get performance summary using materialized view"""
        return self.query_analytics("SELECT * FROM performance_summary ORDER BY total_calls DESC").fetchdf()

    def get_error_records(self, limit: int = 100):
        """Get all error records for debugging"""
        return self.query_analytics(
            "SELECT * FROM records WHERE status = 'error' ORDER BY timestamp DESC LIMIT ?",
            [limit]
        ).fetchdf()

    def get_slow_operations(self, threshold_ms: float = 1000.0, limit: int = 50):
        """Get operations that exceeded duration threshold"""
        return self.query_analytics(
            "SELECT * FROM records WHERE duration_ms > ? ORDER BY duration_ms DESC LIMIT ?",
            [threshold_ms, limit]
        ).fetchdf()

    def _get_last_sync_id(self) -> str:
        """Get the last synced record ID from DuckDB"""
        result = self.duckdb_conn.execute(
            "SELECT id FROM records ORDER BY timestamp DESC LIMIT 1"
        ).fetchone()
        return result[0] if result else ""

    def _start_auto_sync(self, interval: int):
        """Start background sync thread"""
        def sync_worker():
            while not self._stop_sync.wait(interval):
                try:
                    synced = self.sync_to_duckdb()
                    if synced > 0:
                        print(f"[DebugStore] Synced {synced} records to DuckDB")
                except Exception as e:
                    print(f"[DebugStore] Sync error: {e}")

        self._sync_thread = threading.Thread(target=sync_worker, daemon=True)
        self._sync_thread.start()

    def close(self):
        """Close the store and ensure all data is synced"""
        # Stop auto-sync
        if self._sync_thread:
            self._stop_sync.set()
            self._sync_thread.join(timeout=5)

        # Final sync
        print(f"[DebugStore] Final sync...")
        synced = self.sync_to_duckdb()
        print(f"[DebugStore] Synced {synced} records")

        # Close connections
        self.lmdb_env.sync()
        self.lmdb_env.close()
        self.duckdb_conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def get_stats(self) -> Dict[str, Any]:
        """Get store statistics"""
        # LMDB stats
        lmdb_stat = self.lmdb_env.stat()

        # DuckDB stats
        duckdb_count = self.duckdb_conn.execute(
            "SELECT COUNT(*) FROM records"
        ).fetchone()[0]

        # Pending sync count
        with self.lmdb_env.begin(db=self.pending_db) as txn:
            pending_count = txn.stat()['entries']

        return {
            'session_id': self.session_id,
            'lmdb_entries': lmdb_stat['entries'],
            'duckdb_entries': duckdb_count,
            'pending_sync': pending_count,
            'lmdb_size_mb': self.lmdb_path.stat().st_size / (1024 * 1024) if self.lmdb_path.exists() else 0,
            'duckdb_size_mb': self.duckdb_path.stat().st_size / (1024 * 1024) if self.duckdb_path.exists() else 0
        }


# Context manager for easy scoped recording
class DebugContext:
    """
    Context manager for recording debug data within a scope.

    Usage:
        with DebugContext(store, "tool", "http_fetch", "HTTP Fetch") as ctx:
            result = do_work()
            ctx.set_response(result)
    """

    def __init__(
        self,
        store: DebugStore,
        context_type: str,
        context_id: str,
        context_name: str,
        parent_context: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        code_snapshot: Optional[str] = None,
        variant_id: Optional[str] = None
    ):
        self.store = store
        self.context_type = context_type
        self.context_id = context_id
        self.context_name = context_name
        self.parent_context = parent_context
        self.metadata = metadata or {}
        self.code_snapshot = code_snapshot
        self.variant_id = variant_id

        self.request_data = {}
        self.response_data = {}
        self.start_time = None
        self.error = None
        self.record_id = None

    def set_request(self, data: Any):
        """Set request data"""
        self.request_data = data if isinstance(data, dict) else {"value": data}

    def set_response(self, data: Any):
        """Set response data"""
        self.response_data = data if isinstance(data, dict) else {"value": data}

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.time() - self.start_time) * 1000

        status = "success"
        error = None
        if exc_type is not None:
            status = "error"
            error = str(exc_val)

        # Record the debug data
        self.record_id = self.store.write_record(
            context_type=self.context_type,
            context_id=self.context_id,
            context_name=self.context_name,
            request_data=self.request_data,
            response_data=self.response_data,
            duration_ms=duration_ms,
            status=status,
            error=error,
            metadata=self.metadata,
            parent_context=self.parent_context,
            code_snapshot=self.code_snapshot,
            variant_id=self.variant_id
        )

        # Don't suppress exception
        return False
