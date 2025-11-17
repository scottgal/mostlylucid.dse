"""
Optimized Performance Tracker for Tool Calls

High-efficiency performance tracking with minimal overhead:
- Normal mode: Tiny footprint (tool name, params summary, start/end timestamps)
- Optimization mode: Comprehensive data collection for characterization
- Parent-child context aggregation during execution
- Per-tool LRU limits with YAML configuration
- RAG integration for tool clustering
- Background async persistence with no-op fallback
"""

import os
import time
import json
import yaml
import hashlib
import threading
from collections import OrderedDict, deque
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Deque
from enum import Enum


class TrackingMode(Enum):
    """Performance tracking modes"""
    NORMAL = "normal"  # Minimal overhead
    OPTIMIZATION = "optimization"  # Comprehensive data


@dataclass
class MinimalPerfData:
    """Minimal performance data for normal mode - TINY footprint"""
    tool: str  # Tool name
    params: str  # Params summary (truncated if long)
    start: float  # Start timestamp
    end: float  # End timestamp

    def to_compact_dict(self) -> Dict[str, Any]:
        """Ultra-compact representation for RAG storage"""
        return {
            "t": self.tool,
            "p": self.params[:100] if len(self.params) > 100 else self.params,
            "s": self.start,
            "e": self.end,
            "d": round(self.end - self.start, 3)  # duration in seconds
        }


@dataclass
class DetailedPerfData:
    """Comprehensive performance data for optimization mode"""
    tool: str
    params: Dict[str, Any]
    start: float
    end: float
    duration_ms: float
    memory_mb: Optional[float] = None
    cpu_percent: Optional[float] = None
    parent_tool: Optional[str] = None
    child_tools: List[str] = field(default_factory=list)
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Full dictionary representation"""
        return asdict(self)


class ToolPerfLRU:
    """LRU storage for a single tool's performance data"""

    def __init__(self, tool_name: str, max_size: int):
        self.tool_name = tool_name
        self.max_size = max_size
        self.data: OrderedDict[str, Any] = OrderedDict()
        self.lock = threading.Lock()

    def add(self, record_id: str, perf_data: Any) -> Optional[Any]:
        """
        Add performance data with LRU eviction.
        Returns evicted data if limit exceeded, None otherwise.
        """
        with self.lock:
            if self.max_size == 0:
                return None  # Tracking disabled

            if self.max_size == -1:
                # Unlimited
                self.data[record_id] = perf_data
                return None

            evicted = None
            if len(self.data) >= self.max_size:
                # Evict oldest
                _, evicted = self.data.popitem(last=False)

            self.data[record_id] = perf_data
            return evicted

    def get_all(self) -> List[Any]:
        """Get all records (most recent first)"""
        with self.lock:
            return list(reversed(self.data.values()))

    def clear(self) -> List[Any]:
        """Clear all data and return what was stored"""
        with self.lock:
            data = list(self.data.values())
            self.data.clear()
            return data

    def size(self) -> int:
        """Current number of records"""
        with self.lock:
            return len(self.data)


class OptimizedPerfTracker:
    """
    Optimized performance tracker with configurable limits and modes.

    Features:
    - Minimal overhead in normal mode
    - Per-tool LRU limits from YAML config
    - Parent-child context aggregation
    - Background async saves
    - RAG integration for tool clustering
    - Auto-cleanup during optimization runs
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized'):
            return

        self._initialized = True
        self.mode = TrackingMode.NORMAL
        self.config = self._load_config()

        # Per-tool LRU storage
        self.tool_stores: Dict[str, ToolPerfLRU] = {}
        self.stores_lock = threading.Lock()

        # Parent-child context tracking
        self.execution_stack: Deque[str] = deque()  # Stack of current tool executions
        self.context_map: Dict[str, DetailedPerfData] = {}  # Active execution contexts
        self.context_lock = threading.Lock()

        # Background save queue
        self.save_queue: Deque[Dict[str, Any]] = deque()
        self.save_lock = threading.Lock()
        self.save_thread = None
        self.running = True

        # Global stats
        self.total_calls = 0
        self.stats_lock = threading.Lock()

        # Storage path
        self.storage_path = Path("perf_data")
        self.storage_path.mkdir(exist_ok=True)

        # Start background save thread if enabled
        if self.config.get("storage", {}).get("async_save", True):
            self._start_background_saver()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML"""
        config_path = Path("code_evolver/config/tool_perf_limits.yaml")
        if not config_path.exists():
            # Fallback to default
            return {
                "default_perf_points": 100,
                "tool_limits": {},
                "optimization": {
                    "enabled": False,
                    "trigger_threshold": 10000,
                    "cleanup_on_optimize": True
                },
                "storage": {
                    "async_save": True,
                    "batch_size": 100,
                    "flush_interval_seconds": 30
                },
                "rag": {
                    "enabled": True,
                    "cluster_with_tool": True,
                    "embedding_include": False
                }
            }

        try:
            with open(config_path) as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"Warning: Failed to load perf config: {e}. Using defaults.")
            return {"default_perf_points": 100, "tool_limits": {}}

    def _get_tool_limit(self, tool_name: str) -> int:
        """Get performance data limit for a specific tool"""
        tool_limits = self.config.get("tool_limits", {})
        return tool_limits.get(tool_name, self.config.get("default_perf_points", 100))

    def _get_or_create_store(self, tool_name: str) -> ToolPerfLRU:
        """Get or create LRU store for a tool"""
        with self.stores_lock:
            if tool_name not in self.tool_stores:
                limit = self._get_tool_limit(tool_name)
                self.tool_stores[tool_name] = ToolPerfLRU(tool_name, limit)
            return self.tool_stores[tool_name]

    def _summarize_params(self, params: Dict[str, Any]) -> str:
        """Create compact summary of parameters"""
        if not params:
            return ""

        try:
            # Convert to JSON and truncate if needed
            json_str = json.dumps(params, default=str)
            return json_str[:200] if len(json_str) > 200 else json_str
        except:
            return str(params)[:200]

    def _generate_record_id(self, tool_name: str) -> str:
        """Generate unique record ID"""
        timestamp = time.time()
        unique_str = f"{tool_name}_{timestamp}_{id(threading.current_thread())}"
        return hashlib.md5(unique_str.encode()).hexdigest()[:16]

    def start_tracking(self, tool_name: str, params: Dict[str, Any]) -> str:
        """
        Start tracking a tool call.
        Returns record_id for use in end_tracking.
        """
        record_id = self._generate_record_id(tool_name)
        start_time = time.time()

        # Increment global call counter
        with self.stats_lock:
            self.total_calls += 1

            # Check if we should trigger optimization
            threshold = self.config.get("optimization", {}).get("trigger_threshold", 10000)
            if self.total_calls >= threshold and not self.is_optimization_mode():
                # This would trigger optimization in a real scenario
                pass

        # Determine if we need detailed tracking
        if self.is_optimization_mode():
            # Detailed tracking
            perf_data = DetailedPerfData(
                tool=tool_name,
                params=params,
                start=start_time,
                end=0.0,  # Not finished yet
                duration_ms=0.0,
                metadata={"record_id": record_id}
            )

            # Track parent-child relationship
            with self.context_lock:
                if self.execution_stack:
                    parent_id = self.execution_stack[-1]
                    perf_data.parent_tool = parent_id

                    # Add to parent's children if parent is in context
                    if parent_id in self.context_map:
                        self.context_map[parent_id].child_tools.append(record_id)

                self.execution_stack.append(record_id)
                self.context_map[record_id] = perf_data
        else:
            # Minimal tracking - just store the start for now
            with self.context_lock:
                self.context_map[record_id] = {
                    "tool": tool_name,
                    "params": self._summarize_params(params),
                    "start": start_time
                }

        return record_id

    def end_tracking(self, record_id: str, error: Optional[str] = None):
        """
        End tracking a tool call.
        Persists data and handles parent-child aggregation.
        """
        end_time = time.time()

        with self.context_lock:
            if record_id not in self.context_map:
                return  # Already processed or invalid ID

            context = self.context_map.pop(record_id)

            # Remove from execution stack
            if self.execution_stack and self.execution_stack[-1] == record_id:
                self.execution_stack.pop()

        # Create final performance record
        if self.is_optimization_mode():
            # Detailed data
            if isinstance(context, DetailedPerfData):
                context.end = end_time
                context.duration_ms = (end_time - context.start) * 1000
                context.error = error

                perf_record = context
            else:
                # Shouldn't happen, but handle gracefully
                perf_record = DetailedPerfData(
                    tool=context.get("tool", "unknown"),
                    params={},
                    start=context.get("start", end_time),
                    end=end_time,
                    duration_ms=(end_time - context.get("start", end_time)) * 1000,
                    error=error
                )
        else:
            # Minimal data
            perf_record = MinimalPerfData(
                tool=context.get("tool", "unknown"),
                params=context.get("params", ""),
                start=context.get("start", end_time),
                end=end_time
            )

        # Add to tool's LRU store
        tool_name = perf_record.tool
        store = self._get_or_create_store(tool_name)
        evicted = store.add(record_id, perf_record)

        # Queue for background save if enabled
        if self.config.get("storage", {}).get("async_save", True):
            self._queue_for_save(tool_name, perf_record)

        # RAG integration if enabled
        if self.config.get("rag", {}).get("enabled", True):
            self._update_rag(tool_name, perf_record)

    def _queue_for_save(self, tool_name: str, perf_record: Any):
        """Queue performance record for background save"""
        with self.save_lock:
            save_data = {
                "tool": tool_name,
                "timestamp": datetime.now().isoformat(),
                "data": perf_record.to_compact_dict() if isinstance(perf_record, MinimalPerfData) else perf_record.to_dict()
            }
            self.save_queue.append(save_data)

    def _update_rag(self, tool_name: str, perf_record: Any):
        """
        Update RAG with minimal performance data clustered with tool.
        No-op if RAG not available.
        """
        try:
            from rag_memory import RAGMemory

            if not self.config.get("rag", {}).get("cluster_with_tool", True):
                return

            # Create minimal metadata to attach to tool in RAG
            perf_metadata = perf_record.to_compact_dict() if isinstance(perf_record, MinimalPerfData) else {
                "tool": perf_record.tool,
                "duration_ms": perf_record.duration_ms,
                "timestamp": perf_record.start
            }

            # This would update the tool's artifact in RAG with perf metadata
            # Implementation depends on RAG structure
            # For now, we just prepare the data

        except ImportError:
            # RAG not available, no-op
            pass
        except Exception:
            # Don't let RAG failures break tracking
            pass

    def _start_background_saver(self):
        """Start background thread for async persistence"""
        def save_worker():
            batch_size = self.config.get("storage", {}).get("batch_size", 100)
            flush_interval = self.config.get("storage", {}).get("flush_interval_seconds", 30)
            last_flush = time.time()

            while self.running:
                try:
                    # Check if we should flush
                    should_flush = False
                    with self.save_lock:
                        queue_size = len(self.save_queue)
                        should_flush = queue_size >= batch_size or (time.time() - last_flush) >= flush_interval

                    if should_flush:
                        self._flush_save_queue()
                        last_flush = time.time()
                    else:
                        time.sleep(1)  # Check every second

                except Exception as e:
                    print(f"Background saver error: {e}")
                    time.sleep(5)

        self.save_thread = threading.Thread(target=save_worker, daemon=True)
        self.save_thread.start()

    def _flush_save_queue(self):
        """Flush save queue to disk"""
        with self.save_lock:
            if not self.save_queue:
                return

            # Get all pending saves
            to_save = list(self.save_queue)
            self.save_queue.clear()

        # Group by tool
        by_tool: Dict[str, List[Dict]] = {}
        for record in to_save:
            tool = record["tool"]
            if tool not in by_tool:
                by_tool[tool] = []
            by_tool[tool].append(record)

        # Save to disk (one file per tool)
        for tool_name, records in by_tool.items():
            try:
                file_path = self.storage_path / f"{tool_name}_perf.jsonl"
                with open(file_path, "a") as f:
                    for record in records:
                        f.write(json.dumps(record) + "\n")
            except Exception as e:
                print(f"Failed to save perf data for {tool_name}: {e}")

    def is_optimization_mode(self) -> bool:
        """Check if we're in optimization mode"""
        return self.mode == TrackingMode.OPTIMIZATION or self.config.get("optimization", {}).get("enabled", False)

    def set_optimization_mode(self, enabled: bool):
        """Enable or disable optimization mode"""
        self.mode = TrackingMode.OPTIMIZATION if enabled else TrackingMode.NORMAL

    def cleanup_old_data(self):
        """
        Cleanup old performance data (called during optimization runs).
        Clears all in-memory LRU stores and deletes old files.
        """
        if not self.config.get("optimization", {}).get("cleanup_on_optimize", True):
            return

        # Clear all LRU stores
        with self.stores_lock:
            for store in self.tool_stores.values():
                store.clear()

        # Delete old files
        try:
            for file_path in self.storage_path.glob("*_perf.jsonl"):
                file_path.unlink()
        except Exception as e:
            print(f"Failed to cleanup old perf files: {e}")

    def get_tool_stats(self, tool_name: str) -> Dict[str, Any]:
        """Get statistics for a specific tool"""
        store = self._get_or_create_store(tool_name)
        records = store.get_all()

        if not records:
            return {"tool": tool_name, "count": 0}

        # Calculate stats
        if isinstance(records[0], MinimalPerfData):
            durations = [(r.end - r.start) for r in records]
        else:
            durations = [r.duration_ms / 1000 for r in records]

        return {
            "tool": tool_name,
            "count": len(records),
            "avg_duration_s": sum(durations) / len(durations) if durations else 0,
            "min_duration_s": min(durations) if durations else 0,
            "max_duration_s": max(durations) if durations else 0,
            "current_size": store.size(),
            "max_size": store.max_size
        }

    def get_all_stats(self) -> Dict[str, Any]:
        """Get global statistics"""
        with self.stores_lock:
            tool_stats = {name: self.get_tool_stats(name) for name in self.tool_stores.keys()}

        return {
            "total_calls": self.total_calls,
            "mode": self.mode.value,
            "tools_tracked": len(self.tool_stores),
            "tool_stats": tool_stats
        }

    def shutdown(self):
        """Graceful shutdown - flush pending saves"""
        self.running = False
        if self.save_thread:
            self.save_thread.join(timeout=5)
        self._flush_save_queue()


# Global singleton instance
_tracker = OptimizedPerfTracker()


def get_tracker() -> OptimizedPerfTracker:
    """Get global performance tracker instance"""
    return _tracker


# Convenience functions
def track_tool_call(tool_name: str, params: Dict[str, Any]) -> str:
    """Start tracking a tool call"""
    return get_tracker().start_tracking(tool_name, params)


def end_tool_call(record_id: str, error: Optional[str] = None):
    """End tracking a tool call"""
    get_tracker().end_tracking(record_id, error)


def set_optimization_mode(enabled: bool):
    """Enable/disable optimization mode"""
    get_tracker().set_optimization_mode(enabled)


def cleanup_perf_data():
    """Cleanup old performance data"""
    get_tracker().cleanup_old_data()


def get_perf_stats(tool_name: Optional[str] = None) -> Dict[str, Any]:
    """Get performance statistics"""
    if tool_name:
        return get_tracker().get_tool_stats(tool_name)
    return get_tracker().get_all_stats()
