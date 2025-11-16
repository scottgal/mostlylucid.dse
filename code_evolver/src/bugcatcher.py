"""
BugCatcher - Global exception monitoring tool for Code Evolver.

This tool sits at the front of every workflow and watches for:
- Exceptions being raised/returned from code
- Exceptions being logged
- Workflow failures

It maintains an LRU cache of recent requests and logs exceptions to Loki.
"""
import logging
import time
import threading
import traceback
import sys
from typing import Dict, Any, Optional, List
from datetime import datetime
from collections import OrderedDict
from enum import Enum
import json
import requests


logger = logging.getLogger(__name__)


class ExceptionSeverity(Enum):
    """Severity levels for exceptions."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class LRUCache:
    """
    Thread-safe LRU cache for tracking recent requests.

    Stores request context so we can associate exceptions with the
    operations that caused them.
    """

    def __init__(self, max_size: int = 100):
        """
        Initialize LRU cache.

        Args:
            max_size: Maximum number of entries to keep
        """
        self.max_size = max_size
        self.cache: OrderedDict = OrderedDict()
        self._lock = threading.Lock()

    def put(self, key: str, value: Dict[str, Any]):
        """
        Add or update an entry.

        Args:
            key: Cache key (typically request_id or workflow_id)
            value: Request context data
        """
        with self._lock:
            # Remove if exists (to update order)
            if key in self.cache:
                del self.cache[key]

            # Add to end
            self.cache[key] = value

            # Evict oldest if over size
            if len(self.cache) > self.max_size:
                self.cache.popitem(last=False)

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get an entry and move to end (most recently used).

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        with self._lock:
            if key in self.cache:
                # Move to end (most recently used)
                value = self.cache.pop(key)
                self.cache[key] = value
                return value
            return None

    def clear(self):
        """Clear all entries."""
        with self._lock:
            self.cache.clear()

    def size(self) -> int:
        """Get current cache size."""
        with self._lock:
            return len(self.cache)


class LokiBackend:
    """
    Backend for sending logs to Grafana Loki.

    Loki is a log aggregation system designed for efficiency and cost.
    """

    def __init__(
        self,
        url: str = "http://localhost:3100",
        enabled: bool = True,
        timeout: int = 5,
        batch_size: int = 10
    ):
        """
        Initialize Loki backend.

        Args:
            url: Loki push endpoint URL
            enabled: Whether logging to Loki is enabled
            timeout: Request timeout in seconds
            batch_size: Number of logs to batch before sending
        """
        self.url = url.rstrip('/') + '/loki/api/v1/push'
        self.enabled = enabled
        self.timeout = timeout
        self.batch_size = batch_size
        self._batch: List[Dict[str, Any]] = []
        self._lock = threading.Lock()

    def push(
        self,
        message: str,
        labels: Dict[str, str],
        timestamp: Optional[datetime] = None
    ):
        """
        Push a log entry to Loki.

        Args:
            message: Log message
            labels: Labels for the log stream (e.g., {"job": "bugcatcher", "level": "error"})
            timestamp: Log timestamp (defaults to now)
        """
        if not self.enabled:
            return

        if timestamp is None:
            timestamp = datetime.now()

        # Convert to nanoseconds since epoch (Loki format)
        ts_ns = str(int(timestamp.timestamp() * 1e9))

        log_entry = {
            'stream': labels,
            'values': [[ts_ns, message]]
        }

        with self._lock:
            self._batch.append(log_entry)

            # Send batch if full
            if len(self._batch) >= self.batch_size:
                self._send_batch()

    def _send_batch(self):
        """Send batched logs to Loki."""
        if not self._batch:
            return

        payload = {'streams': self._batch}

        try:
            response = requests.post(
                self.url,
                json=payload,
                timeout=self.timeout,
                headers={'Content-Type': 'application/json'}
            )
            response.raise_for_status()
            self._batch.clear()

        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to send logs to Loki: {e}")
            # Don't clear batch - will try again next time

    def flush(self):
        """Flush any remaining batched logs."""
        with self._lock:
            if self._batch:
                self._send_batch()


class BugCatcher:
    """
    Global exception monitoring tool.

    Sits at the front of workflows and tracks all exceptions,
    logging them to Loki with full context.
    """

    _instance: Optional['BugCatcher'] = None
    _lock = threading.Lock()

    def __init__(
        self,
        loki_url: str = "http://localhost:3100",
        loki_enabled: bool = True,
        cache_size: int = 100,
        log_to_file: bool = True,
        log_file: str = "bugcatcher.log",
        track_outputs: bool = False
    ):
        """
        Initialize BugCatcher.

        Args:
            loki_url: Loki instance URL
            loki_enabled: Whether to send logs to Loki
            cache_size: Size of request context LRU cache
            log_to_file: Whether to also log to file
            log_file: Path to log file
            track_outputs: Whether to log all outputs to Loki (not just exceptions)
        """
        self.loki = LokiBackend(url=loki_url, enabled=loki_enabled)
        self.request_cache = LRUCache(max_size=cache_size)
        self.log_to_file = log_to_file
        self.log_file = log_file
        self.enabled = True
        self._track_outputs = track_outputs
        self._exception_count = 0
        self._lock = threading.Lock()

        # Set up file logging if enabled
        if self.log_to_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.ERROR)
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

    @classmethod
    def get_instance(cls, **kwargs) -> 'BugCatcher':
        """
        Get singleton instance of BugCatcher.

        Args:
            **kwargs: Configuration options (only used on first call)

        Returns:
            BugCatcher instance
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(**kwargs)
        return cls._instance

    def track_request(
        self,
        request_id: str,
        context: Dict[str, Any]
    ):
        """
        Track a request in the LRU cache.

        Args:
            request_id: Unique request identifier
            context: Request context (workflow_id, step_id, tool_name, etc.)
        """
        context['tracked_at'] = datetime.now().isoformat()
        self.request_cache.put(request_id, context)

    def track_output(
        self,
        request_id: str,
        output: Any,
        output_type: str = "result"
    ):
        """
        Track output for a request.

        This logs all outputs (not just exceptions) so we can correlate
        successful operations with failures.

        Args:
            request_id: Request identifier
            output: Output data
            output_type: Type of output (result, log, etc.)
        """
        # Get request context from cache
        request_context = self.request_cache.get(request_id) or {}

        # Update cache with output
        request_context['last_output'] = {
            'data': str(output)[:1000],  # Truncate to prevent huge logs
            'type': output_type,
            'timestamp': datetime.now().isoformat()
        }
        self.request_cache.put(request_id, request_context)

        # Optionally log to Loki if output tracking is enabled
        if self.enabled and hasattr(self, '_track_outputs'):
            if self._track_outputs:
                self._log_output_to_loki(request_id, output, output_type, request_context)

    def _log_output_to_loki(
        self,
        request_id: str,
        output: Any,
        output_type: str,
        context: Dict[str, Any]
    ):
        """
        Log output to Loki for correlation with exceptions.

        Args:
            request_id: Request identifier
            output: Output data
            output_type: Type of output
            context: Request context
        """
        labels = {
            'job': 'code_evolver_bugcatcher_output',
            'output_type': output_type,
            'request_id': request_id
        }

        if 'workflow_id' in context:
            labels['workflow_id'] = str(context['workflow_id'])
        if 'tool_name' in context:
            labels['tool_name'] = str(context['tool_name'])

        message = json.dumps({
            'request_id': request_id,
            'output': str(output)[:1000],
            'output_type': output_type,
            'context': context,
            'timestamp': datetime.now().isoformat()
        }, indent=2, default=str)

        self.loki.push(message, labels)

    def capture_exception(
        self,
        exception: Exception,
        request_id: Optional[str] = None,
        severity: ExceptionSeverity = ExceptionSeverity.ERROR,
        additional_context: Optional[Dict[str, Any]] = None
    ):
        """
        Capture an exception with full context.

        Args:
            exception: The exception that was raised
            request_id: Associated request ID (if available)
            severity: Exception severity level
            additional_context: Additional context to log
        """
        if not self.enabled:
            return

        with self._lock:
            self._exception_count += 1

        # Get request context from cache
        request_context = {}
        if request_id:
            cached = self.request_cache.get(request_id)
            if cached:
                request_context = cached

        # Build exception context
        exc_type = type(exception).__name__
        exc_message = str(exception)
        exc_traceback = ''.join(traceback.format_exception(
            type(exception),
            exception,
            exception.__traceback__
        ))

        context = {
            'exception_type': exc_type,
            'exception_message': exc_message,
            'traceback': exc_traceback,
            'severity': severity.value,
            'timestamp': datetime.now().isoformat(),
            'request_id': request_id,
            **request_context
        }

        if additional_context:
            context.update(additional_context)

        # Log to standard logger
        logger.error(
            f"BugCatcher captured {exc_type}: {exc_message}",
            extra={'context': context}
        )

        # Send to Loki
        self._send_to_loki(context, severity)

    def capture_logged_exception(
        self,
        log_record: logging.LogRecord,
        request_id: Optional[str] = None
    ):
        """
        Capture an exception from a log record.

        This is called by a custom logging handler to catch
        exceptions that are logged but not necessarily raised.

        Args:
            log_record: Logging record containing exception info
            request_id: Associated request ID
        """
        if not self.enabled:
            return

        if not log_record.exc_info:
            return

        exc_type, exc_value, exc_traceback = log_record.exc_info

        if exc_value:
            # Determine severity from log level
            severity = self._log_level_to_severity(log_record.levelno)

            # Capture the exception
            self.capture_exception(
                exc_value,
                request_id=request_id,
                severity=severity,
                additional_context={
                    'logger_name': log_record.name,
                    'log_level': log_record.levelname,
                    'log_message': log_record.getMessage()
                }
            )

    def _log_level_to_severity(self, level: int) -> ExceptionSeverity:
        """Convert logging level to exception severity."""
        if level >= logging.CRITICAL:
            return ExceptionSeverity.CRITICAL
        elif level >= logging.ERROR:
            return ExceptionSeverity.ERROR
        elif level >= logging.WARNING:
            return ExceptionSeverity.WARNING
        elif level >= logging.INFO:
            return ExceptionSeverity.INFO
        else:
            return ExceptionSeverity.DEBUG

    def _send_to_loki(
        self,
        context: Dict[str, Any],
        severity: ExceptionSeverity
    ):
        """
        Send exception context to Loki.

        Args:
            context: Exception context
            severity: Exception severity
        """
        # Build Loki labels (used for indexing/filtering)
        labels = {
            'job': 'code_evolver_bugcatcher',
            'severity': severity.value,
            'exception_type': context.get('exception_type', 'unknown'),
        }

        # Add workflow/tool context to labels if available
        if 'workflow_id' in context:
            labels['workflow_id'] = str(context['workflow_id'])
        if 'tool_name' in context:
            labels['tool_name'] = str(context['tool_name'])

        # Create log message (JSON)
        message = json.dumps(context, indent=2, default=str)

        # Push to Loki
        self.loki.push(message, labels)

    def flush(self):
        """Flush any pending logs to Loki."""
        self.loki.flush()

    def get_stats(self) -> Dict[str, Any]:
        """
        Get BugCatcher statistics.

        Returns:
            Dict with stats (exception count, cache size, etc.)
        """
        return {
            'total_exceptions': self._exception_count,
            'cache_size': self.request_cache.size(),
            'cache_max_size': self.request_cache.max_size,
            'loki_enabled': self.loki.enabled,
            'enabled': self.enabled
        }

    def reset_stats(self):
        """Reset statistics counters."""
        with self._lock:
            self._exception_count = 0
        self.request_cache.clear()


class BugCatcherLoggingHandler(logging.Handler):
    """
    Custom logging handler that captures exceptions from log records.

    This allows BugCatcher to catch exceptions that are logged but
    not necessarily propagated up the call stack.
    """

    def __init__(self, bugcatcher: Optional[BugCatcher] = None):
        """
        Initialize handler.

        Args:
            bugcatcher: BugCatcher instance (uses singleton if not provided)
        """
        super().__init__()
        self.bugcatcher = bugcatcher or BugCatcher.get_instance()

    def emit(self, record: logging.LogRecord):
        """
        Handle a log record.

        Args:
            record: Log record to handle
        """
        # Only process records with exception info
        if record.exc_info:
            self.bugcatcher.capture_logged_exception(record)


def setup_bugcatcher_logging(
    loki_url: str = "http://localhost:3100",
    loki_enabled: bool = True,
    cache_size: int = 100,
    log_to_file: bool = True,
    log_file: str = "bugcatcher.log",
    track_outputs: bool = False
) -> BugCatcher:
    """
    Set up BugCatcher with logging integration.

    This installs:
    1. A custom logging handler to catch logged exceptions
    2. A global exception hook to catch uncaught exceptions

    Args:
        loki_url: Loki instance URL
        loki_enabled: Whether to send logs to Loki
        cache_size: Size of request context cache
        log_to_file: Whether to log to file
        log_file: Path to log file
        track_outputs: Whether to log all outputs (disabled by default)

    Returns:
        Configured BugCatcher instance
    """
    # Get or create BugCatcher instance
    bugcatcher = BugCatcher.get_instance(
        loki_url=loki_url,
        loki_enabled=loki_enabled,
        cache_size=cache_size,
        log_to_file=log_to_file,
        log_file=log_file,
        track_outputs=track_outputs
    )

    # Install logging handler
    handler = BugCatcherLoggingHandler(bugcatcher)
    handler.setLevel(logging.WARNING)  # Only catch WARNING and above
    logging.root.addHandler(handler)

    # Install global exception hook
    original_excepthook = sys.excepthook

    def bugcatcher_excepthook(exc_type, exc_value, exc_traceback):
        """Global exception hook that captures uncaught exceptions."""
        if exc_value:
            bugcatcher.capture_exception(
                exc_value,
                severity=ExceptionSeverity.CRITICAL,
                additional_context={
                    'uncaught': True,
                    'exception_source': 'global_excepthook'
                }
            )

        # Call original exception hook
        original_excepthook(exc_type, exc_value, exc_traceback)

    sys.excepthook = bugcatcher_excepthook

    logger.info("BugCatcher logging and exception hooks installed")

    return bugcatcher


def get_bugcatcher() -> BugCatcher:
    """
    Get the global BugCatcher instance.

    Returns:
        BugCatcher singleton
    """
    return BugCatcher.get_instance()


# Context manager for tracking requests
class track_request:
    """
    Context manager for tracking a request through BugCatcher.

    Usage:
        with track_request('request_123', workflow_id='wf_1', step_id='step_1'):
            # Your code here
            pass
    """

    def __init__(self, request_id: str, **context):
        """
        Initialize request tracker.

        Args:
            request_id: Unique request ID
            **context: Request context (workflow_id, step_id, etc.)
        """
        self.request_id = request_id
        self.context = context
        self.bugcatcher = get_bugcatcher()

    def __enter__(self):
        """Enter context - track request."""
        self.bugcatcher.track_request(self.request_id, self.context)
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        """Exit context - capture exception if raised."""
        if exc_value:
            self.bugcatcher.capture_exception(
                exc_value,
                request_id=self.request_id
            )
        return False  # Don't suppress exception
