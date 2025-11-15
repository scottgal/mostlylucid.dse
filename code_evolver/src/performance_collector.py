"""
Performance Data Collector

Dedicated tool for collecting entry/exit data and performance metrics
from each layer/tool in the system for optimization analysis.

Features:
- Automatic entry/exit tracking with decorators
- Performance metrics (duration, memory, CPU)
- Layer-aware tracking (tool, workflow, step, node)
- Tool-specific instrumentation
- Optimization report generation
- Integration with debug store for persistence
"""

import time
import functools
import psutil
import inspect
import hashlib
from typing import Any, Callable, Dict, Optional, List
from dataclasses import dataclass, asdict
from pathlib import Path
import threading
from contextlib import contextmanager

from debug_store import DebugStore


@dataclass
class PerformanceMetrics:
    """Performance metrics for a single execution"""
    duration_ms: float
    memory_mb: float
    cpu_percent: float
    memory_peak_mb: float
    io_read_mb: float
    io_write_mb: float
    thread_count: int


@dataclass
class ToolExecutionData:
    """Complete execution data for a tool"""
    tool_name: str
    layer: str  # 'tool', 'workflow', 'step', 'node', 'function'
    entry_data: Dict[str, Any]
    exit_data: Dict[str, Any]
    metrics: PerformanceMetrics
    success: bool
    error: Optional[str]
    timestamp: float
    code_hash: Optional[str] = None


class PerformanceCollector:
    """
    Collects performance data from all layers of the system.

    Usage:
        collector = PerformanceCollector(session_id="perf_analysis_run_1")

        # Instrument a tool
        @collector.instrument(layer="tool", tool_name="http_fetcher")
        def fetch_data(url):
            return requests.get(url)

        # Or use context manager
        with collector.track_execution("tool", "data_processor") as tracker:
            tracker.set_entry({"input": data})
            result = process(data)
            tracker.set_exit({"output": result})

        # Generate optimization report
        report = collector.generate_optimization_report()
    """

    def __init__(
        self,
        session_id: str,
        base_path: str = "debug_data",
        enable_io_tracking: bool = True,
        enable_memory_profiling: bool = True
    ):
        """
        Initialize performance collector.

        Args:
            session_id: Unique session identifier
            base_path: Base path for storing performance data
            enable_io_tracking: Track disk I/O operations
            enable_memory_profiling: Track detailed memory usage
        """
        self.session_id = session_id
        self.store = DebugStore(
            session_id=session_id,
            base_path=base_path,
            enable_auto_sync=True,
            auto_sync_interval=15  # Sync more frequently for perf data
        )
        self.enable_io_tracking = enable_io_tracking
        self.enable_memory_profiling = enable_memory_profiling

        # Process handle for metrics
        self.process = psutil.Process()

        # Thread-local storage for nested tracking
        self._thread_local = threading.local()

    def instrument(
        self,
        layer: str,
        tool_name: Optional[str] = None,
        capture_args: bool = True,
        capture_result: bool = True,
        track_code_changes: bool = True
    ):
        """
        Decorator to instrument a function/tool for performance tracking.

        Args:
            layer: Layer name ('tool', 'workflow', 'step', 'node', 'function')
            tool_name: Optional tool name (defaults to function name)
            capture_args: Capture function arguments
            capture_result: Capture function result
            track_code_changes: Track code changes via hash

        Example:
            @collector.instrument(layer="tool", tool_name="image_processor")
            def process_image(image_path, filters):
                # Processing logic
                return processed_image
        """
        def decorator(func: Callable) -> Callable:
            actual_tool_name = tool_name or func.__name__

            # Get code hash if tracking
            code_hash = None
            if track_code_changes:
                try:
                    source = inspect.getsource(func)
                    code_hash = hashlib.md5(source.encode()).hexdigest()
                except (OSError, TypeError):
                    pass

            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                # Prepare entry data
                entry_data = {}
                if capture_args:
                    try:
                        sig = inspect.signature(func)
                        bound_args = sig.bind(*args, **kwargs)
                        bound_args.apply_defaults()
                        entry_data = {
                            k: self._serialize_value(v)
                            for k, v in bound_args.arguments.items()
                        }
                    except Exception as e:
                        entry_data = {"_error": f"Failed to capture args: {e}"}

                # Start tracking
                with self.track_execution(layer, actual_tool_name, code_hash) as tracker:
                    tracker.set_entry(entry_data)

                    try:
                        # Execute function
                        result = func(*args, **kwargs)

                        # Capture exit data
                        if capture_result:
                            exit_data = {"result": self._serialize_value(result)}
                        else:
                            exit_data = {"result_type": type(result).__name__}

                        tracker.set_exit(exit_data)
                        return result

                    except Exception as e:
                        # Record error
                        tracker.set_error(str(e))
                        raise

            return wrapper
        return decorator

    @contextmanager
    def track_execution(
        self,
        layer: str,
        tool_name: str,
        code_hash: Optional[str] = None
    ):
        """
        Context manager for tracking tool execution.

        Yields:
            ExecutionTracker instance

        Example:
            with collector.track_execution("tool", "data_processor") as tracker:
                tracker.set_entry({"input": data})
                result = process(data)
                tracker.set_exit({"output": result})
        """
        tracker = ExecutionTracker(
            self,
            layer,
            tool_name,
            code_hash,
            self.enable_io_tracking,
            self.enable_memory_profiling
        )

        try:
            yield tracker
        finally:
            # Tracker will record data in its __exit__
            pass

    def record_execution(self, execution_data: ToolExecutionData):
        """Record a tool execution"""
        self.store.write_record(
            context_type=execution_data.layer,
            context_id=execution_data.tool_name,
            context_name=execution_data.tool_name,
            request_data={
                "entry": execution_data.entry_data,
                "layer": execution_data.layer
            },
            response_data={
                "exit": execution_data.exit_data,
                "success": execution_data.success
            },
            duration_ms=execution_data.metrics.duration_ms,
            memory_mb=execution_data.metrics.memory_mb,
            cpu_percent=execution_data.metrics.cpu_percent,
            status="success" if execution_data.success else "error",
            error=execution_data.error,
            code_hash=execution_data.code_hash,
            metadata={
                "memory_peak_mb": execution_data.metrics.memory_peak_mb,
                "io_read_mb": execution_data.metrics.io_read_mb,
                "io_write_mb": execution_data.metrics.io_write_mb,
                "thread_count": execution_data.metrics.thread_count,
                "timestamp": execution_data.timestamp
            }
        )

    def generate_optimization_report(
        self,
        output_path: Optional[str] = None,
        min_executions: int = 3,
        max_tokens: int = 100000
    ) -> str:
        """
        Generate comprehensive optimization report.

        Args:
            output_path: Optional file path to save report
            min_executions: Minimum executions to include in report
            max_tokens: Maximum tokens for LLM consumption

        Returns:
            Markdown-formatted optimization report
        """
        from debug_analyzer import DebugAnalyzer

        # Sync all pending data
        self.store.sync_to_duckdb()

        # Get all layers
        layers_df = self.store.query_analytics("""
            SELECT DISTINCT context_type, context_id, context_name, COUNT(*) as count
            FROM records
            GROUP BY context_type, context_id, context_name
            HAVING count >= ?
            ORDER BY count DESC
        """, [min_executions]).fetchdf()

        sections = []

        # Header
        sections.append("# System Performance Optimization Report")
        sections.append(f"\n**Session:** {self.session_id}\n")

        # Overall statistics
        overall_stats = self.store.query_analytics("""
            SELECT
                COUNT(*) as total_executions,
                AVG(duration_ms) as avg_duration,
                SUM(duration_ms) as total_duration,
                AVG(memory_mb) as avg_memory,
                MAX(memory_mb) as peak_memory,
                AVG(cpu_percent) as avg_cpu,
                SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as total_errors
            FROM records
        """).fetchone()

        sections.append("## Overall System Performance\n")
        sections.append(f"- **Total Executions:** {overall_stats[0]}")
        sections.append(f"- **Total Time Spent:** {overall_stats[2]:.2f}ms")
        sections.append(f"- **Average Duration:** {overall_stats[1]:.2f}ms")
        sections.append(f"- **Average Memory:** {overall_stats[3]:.2f}MB")
        sections.append(f"- **Peak Memory:** {overall_stats[4]:.2f}MB")
        sections.append(f"- **Average CPU:** {overall_stats[5]:.1f}%")
        sections.append(f"- **Total Errors:** {overall_stats[6]}\n")

        # Performance by layer
        sections.append("## Performance by Layer\n")

        layer_stats = self.store.query_analytics("""
            SELECT
                context_type as layer,
                COUNT(*) as executions,
                AVG(duration_ms) as avg_duration,
                SUM(duration_ms) as total_duration,
                AVG(memory_mb) as avg_memory,
                AVG(cpu_percent) as avg_cpu,
                SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END)::FLOAT / COUNT(*) as error_rate
            FROM records
            GROUP BY context_type
            ORDER BY total_duration DESC
        """).fetchdf()

        sections.append("| Layer | Executions | Avg Duration | Total Time | Avg Memory | Avg CPU | Error Rate |")
        sections.append("|-------|-----------|--------------|------------|------------|---------|------------|")

        for _, row in layer_stats.iterrows():
            sections.append(
                f"| {row['layer']} | {row['executions']} | "
                f"{row['avg_duration']:.2f}ms | {row['total_duration']:.2f}ms | "
                f"{row['avg_memory']:.2f}MB | {row['avg_cpu']:.1f}% | "
                f"{row['error_rate']:.1%} |"
            )

        # Top time-consuming tools
        sections.append("\n## Top Time-Consuming Tools\n")

        top_tools = self.store.query_analytics("""
            SELECT
                context_name,
                context_type as layer,
                COUNT(*) as executions,
                AVG(duration_ms) as avg_duration,
                SUM(duration_ms) as total_duration,
                PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration_ms) as p95_duration
            FROM records
            GROUP BY context_name, context_type
            HAVING COUNT(*) >= ?
            ORDER BY total_duration DESC
            LIMIT 10
        """, [min_executions]).fetchdf()

        sections.append("| Tool | Layer | Executions | Avg | P95 | Total | % of Total |")
        sections.append("|------|-------|-----------|-----|-----|-------|------------|")

        total_time = overall_stats[2]
        for _, row in top_tools.iterrows():
            pct = (row['total_duration'] / total_time * 100) if total_time > 0 else 0
            sections.append(
                f"| {row['context_name']} | {row['layer']} | "
                f"{row['executions']} | {row['avg_duration']:.2f}ms | "
                f"{row['p95_duration']:.2f}ms | {row['total_duration']:.2f}ms | "
                f"{pct:.1f}% |"
            )

        # Memory hotspots
        sections.append("\n## Memory Hotspots\n")

        memory_hotspots = self.store.query_analytics("""
            SELECT
                context_name,
                context_type as layer,
                AVG(memory_mb) as avg_memory,
                MAX(memory_mb) as peak_memory,
                COUNT(*) as executions
            FROM records
            WHERE memory_mb > 0
            GROUP BY context_name, context_type
            HAVING COUNT(*) >= ?
            ORDER BY peak_memory DESC
            LIMIT 10
        """, [min_executions]).fetchdf()

        sections.append("| Tool | Layer | Avg Memory | Peak Memory | Executions |")
        sections.append("|------|-------|-----------|-------------|------------|")

        for _, row in memory_hotspots.iterrows():
            sections.append(
                f"| {row['context_name']} | {row['layer']} | "
                f"{row['avg_memory']:.2f}MB | {row['peak_memory']:.2f}MB | "
                f"{row['executions']} |"
            )

        # Error-prone tools
        error_tools = self.store.query_analytics("""
            SELECT
                context_name,
                context_type as layer,
                COUNT(*) as total_executions,
                SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as errors,
                SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END)::FLOAT / COUNT(*) as error_rate
            FROM records
            GROUP BY context_name, context_type
            HAVING SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) > 0
               AND COUNT(*) >= ?
            ORDER BY error_rate DESC
            LIMIT 10
        """, [min_executions]).fetchdf()

        if not error_tools.empty:
            sections.append("\n## Error-Prone Tools\n")
            sections.append("| Tool | Layer | Executions | Errors | Error Rate |")
            sections.append("|------|-------|-----------|--------|------------|")

            for _, row in error_tools.iterrows():
                sections.append(
                    f"| {row['context_name']} | {row['layer']} | "
                    f"{row['total_executions']} | {row['errors']} | "
                    f"{row['error_rate']:.1%} |"
                )

        # Optimization recommendations
        sections.append("\n## Optimization Recommendations\n")

        analyzer = DebugAnalyzer(self.store)
        candidates = analyzer.get_optimization_candidates(
            min_executions=min_executions,
            min_duration_ms=10.0  # Include tools > 10ms
        )

        if candidates:
            sections.append("Prioritized optimization targets:\n")
            for i, candidate in enumerate(candidates[:10], 1):
                impact = candidate['total_duration_ms'] / total_time * 100 if total_time > 0 else 0
                sections.append(
                    f"{i}. **{candidate['context_name']}** ({candidate['layer']})\n"
                    f"   - Avg Duration: {candidate['avg_duration_ms']:.2f}ms\n"
                    f"   - Total Impact: {candidate['total_duration_ms']:.2f}ms ({impact:.1f}% of total time)\n"
                    f"   - Executions: {candidate['execution_count']}\n"
                    f"   - Error Rate: {candidate['error_rate']:.1%}\n"
                    f"   - Optimization Score: {candidate['optimization_score']:.2f}\n"
                )

        # Detailed analysis per layer
        sections.append("\n## Detailed Layer Analysis\n")

        for layer in layer_stats['layer'].unique():
            try:
                package = analyzer.analyze_context(
                    context_type=layer,
                    include_variants=True,
                    max_samples=5
                )

                sections.append(f"### {layer.upper()} Layer\n")
                sections.append(package.summary)

                if package.recommendations:
                    sections.append("\n**Recommendations:**\n")
                    for rec in package.recommendations:
                        sections.append(f"- {rec}")

                sections.append("\n")

            except ValueError:
                # No data for this layer
                continue

        markdown = "\n".join(sections)

        # Save to file if requested
        if output_path:
            Path(output_path).write_text(markdown)

        return markdown

    @staticmethod
    def _serialize_value(value: Any) -> Any:
        """Serialize a value for storage"""
        if isinstance(value, (str, int, float, bool, type(None))):
            return value
        elif isinstance(value, (list, tuple)):
            return [PerformanceCollector._serialize_value(v) for v in value[:100]]  # Limit size
        elif isinstance(value, dict):
            return {
                k: PerformanceCollector._serialize_value(v)
                for k, v in list(value.items())[:100]  # Limit size
            }
        else:
            return {"_type": type(value).__name__, "_repr": str(value)[:200]}

    def close(self):
        """Close the collector and underlying store"""
        self.store.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class ExecutionTracker:
    """
    Tracks a single execution and collects metrics.

    Used internally by PerformanceCollector.
    """

    def __init__(
        self,
        collector: PerformanceCollector,
        layer: str,
        tool_name: str,
        code_hash: Optional[str],
        enable_io_tracking: bool,
        enable_memory_profiling: bool
    ):
        self.collector = collector
        self.layer = layer
        self.tool_name = tool_name
        self.code_hash = code_hash
        self.enable_io_tracking = enable_io_tracking
        self.enable_memory_profiling = enable_memory_profiling

        self.entry_data = {}
        self.exit_data = {}
        self.error = None

        # Metrics tracking
        self.start_time = None
        self.start_memory = None
        self.start_io = None
        self.peak_memory = 0
        self.process = collector.process

    def set_entry(self, data: Dict[str, Any]):
        """Set entry data"""
        self.entry_data = data

    def set_exit(self, data: Dict[str, Any]):
        """Set exit data"""
        self.exit_data = data

    def set_error(self, error: str):
        """Set error"""
        self.error = error

    def __enter__(self):
        # Start timing
        self.start_time = time.time()

        # Start memory tracking
        if self.enable_memory_profiling:
            try:
                mem_info = self.process.memory_info()
                self.start_memory = mem_info.rss / (1024 * 1024)  # MB
                self.peak_memory = self.start_memory
            except Exception:
                self.start_memory = 0

        # Start I/O tracking
        if self.enable_io_tracking:
            try:
                io_counters = self.process.io_counters()
                self.start_io = (
                    io_counters.read_bytes / (1024 * 1024),  # MB
                    io_counters.write_bytes / (1024 * 1024)  # MB
                )
            except Exception:
                self.start_io = (0, 0)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Capture error if occurred
        if exc_type is not None and self.error is None:
            self.error = str(exc_val)

        # Calculate duration
        duration_ms = (time.time() - self.start_time) * 1000

        # End memory tracking
        end_memory = 0
        if self.enable_memory_profiling:
            try:
                mem_info = self.process.memory_info()
                end_memory = mem_info.rss / (1024 * 1024)
                self.peak_memory = max(self.peak_memory, end_memory)
            except Exception:
                pass

        memory_mb = end_memory - self.start_memory if self.start_memory else 0

        # End I/O tracking
        io_read_mb = 0
        io_write_mb = 0
        if self.enable_io_tracking and self.start_io:
            try:
                io_counters = self.process.io_counters()
                end_io = (
                    io_counters.read_bytes / (1024 * 1024),
                    io_counters.write_bytes / (1024 * 1024)
                )
                io_read_mb = end_io[0] - self.start_io[0]
                io_write_mb = end_io[1] - self.start_io[1]
            except Exception:
                pass

        # CPU usage (approximate)
        try:
            cpu_percent = self.process.cpu_percent()
        except Exception:
            cpu_percent = 0.0

        # Thread count
        try:
            thread_count = self.process.num_threads()
        except Exception:
            thread_count = 1

        # Create metrics
        metrics = PerformanceMetrics(
            duration_ms=duration_ms,
            memory_mb=abs(memory_mb),  # Absolute value
            cpu_percent=cpu_percent,
            memory_peak_mb=self.peak_memory,
            io_read_mb=abs(io_read_mb),
            io_write_mb=abs(io_write_mb),
            thread_count=thread_count
        )

        # Create execution data
        execution = ToolExecutionData(
            tool_name=self.tool_name,
            layer=self.layer,
            entry_data=self.entry_data,
            exit_data=self.exit_data,
            metrics=metrics,
            success=exc_type is None,
            error=self.error,
            timestamp=self.start_time,
            code_hash=self.code_hash
        )

        # Record
        self.collector.record_execution(execution)

        # Don't suppress exceptions
        return False
