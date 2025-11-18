"""
Resilience Layer for Networking

Provides retry logic, circuit breaker pattern, and rate limiting
for network operations to improve reliability and prevent overload.
"""

import time
import logging
import threading
import random
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime, timedelta
from enum import Enum
from collections import deque

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Circuit is open, failing fast
    HALF_OPEN = "half_open"  # Testing if service recovered


class ResilientCaller:
    """
    Wrap any network call with retry logic and circuit breaker.

    Features:
    - Configurable retry strategies (exponential backoff, linear, constant)
    - Jitter to prevent thundering herd
    - Circuit breaker pattern
    - Timeout handling
    - Error classification (retriable vs non-retriable)
    """

    def __init__(self, config_manager=None):
        """
        Initialize resilient caller.

        Args:
            config_manager: Optional configuration manager
        """
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)
        self.circuit_breakers = {}

    def execute(
        self,
        tool_name: str,
        tool_params: Dict[str, Any],
        max_retries: int = 3,
        backoff: str = "exponential",
        initial_delay: float = 1.0,
        max_delay: float = 30.0,
        jitter: bool = True,
        timeout: Optional[float] = None,
        circuit_breaker: bool = False,
        circuit_breaker_config: Optional[Dict] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute a tool call with retry logic.

        Args:
            tool_name: Name of the tool to call
            tool_params: Parameters to pass to the tool
            max_retries: Maximum number of retry attempts
            backoff: Backoff strategy (exponential, linear, constant)
            initial_delay: Initial delay in seconds
            max_delay: Maximum delay between retries
            jitter: Add random jitter to delays
            timeout: Overall timeout for all retries
            circuit_breaker: Enable circuit breaker
            circuit_breaker_config: Circuit breaker configuration

        Returns:
            Dict with success status and result
        """
        start_time = time.time()
        attempts = []

        # Check circuit breaker
        if circuit_breaker:
            cb_key = f"{tool_name}:{tool_params.get('host', '')}:{tool_params.get('port', '')}"
            if cb_key not in self.circuit_breakers:
                self.circuit_breakers[cb_key] = CircuitBreaker(
                    **(circuit_breaker_config or {})
                )

            cb = self.circuit_breakers[cb_key]
            if not cb.allow_request():
                return {
                    "success": False,
                    "error": "Circuit breaker is OPEN",
                    "circuit_state": cb.state.value,
                    "attempts": attempts
                }

        for attempt in range(max_retries + 1):
            # Check overall timeout
            if timeout and (time.time() - start_time) > timeout:
                return {
                    "success": False,
                    "error": "Overall timeout exceeded",
                    "attempts": attempts,
                    "total_duration": time.time() - start_time
                }

            attempt_start = time.time()

            try:
                # Import here to avoid circular dependency
                from ..tools_manager import call_tool
                import json

                # Call the tool
                result = call_tool(tool_name, json.dumps(tool_params))

                # Parse result if it's a string
                if isinstance(result, str):
                    try:
                        result = json.loads(result)
                    except:
                        result = {"success": True, "data": result}

                attempt_info = {
                    "attempt": attempt + 1,
                    "duration": time.time() - attempt_start,
                    "success": result.get("success", True)
                }

                attempts.append(attempt_info)

                # Check if successful
                if result.get("success", True):
                    if circuit_breaker:
                        cb.record_success()

                    return {
                        "success": True,
                        "result": result,
                        "attempts": attempts,
                        "total_duration": time.time() - start_time
                    }
                else:
                    # Check if error is retriable
                    error_type = result.get("error_type", "")
                    if not self._is_retriable(error_type):
                        return {
                            "success": False,
                            "error": "Non-retriable error",
                            "result": result,
                            "attempts": attempts
                        }

                    attempt_info["error"] = result.get("error")
                    attempt_info["error_type"] = error_type

            except Exception as e:
                self.logger.error(f"Call attempt {attempt + 1} failed: {e}")
                attempts.append({
                    "attempt": attempt + 1,
                    "duration": time.time() - attempt_start,
                    "success": False,
                    "error": str(e),
                    "error_type": type(e).__name__
                })

            # If not the last attempt, wait before retrying
            if attempt < max_retries:
                delay = self._calculate_delay(
                    attempt,
                    backoff,
                    initial_delay,
                    max_delay,
                    jitter
                )
                self.logger.info(f"Retrying in {delay:.2f}s (attempt {attempt + 1}/{max_retries})")
                time.sleep(delay)

        # All retries exhausted
        if circuit_breaker:
            cb.record_failure()

        return {
            "success": False,
            "error": "All retry attempts exhausted",
            "attempts": attempts,
            "total_duration": time.time() - start_time
        }

    def _calculate_delay(
        self,
        attempt: int,
        backoff: str,
        initial_delay: float,
        max_delay: float,
        jitter: bool
    ) -> float:
        """Calculate delay for next retry."""
        if backoff == "exponential":
            delay = min(initial_delay * (2 ** attempt), max_delay)
        elif backoff == "linear":
            delay = min(initial_delay * (attempt + 1), max_delay)
        else:  # constant
            delay = initial_delay

        # Add jitter
        if jitter:
            delay = delay * (0.5 + random.random() * 0.5)

        return delay

    def _is_retriable(self, error_type: str) -> bool:
        """Check if an error type is retriable."""
        retriable_errors = [
            "TimeoutError",
            "ConnectionRefused",
            "DNSError",
            "OSError",
            "socket.timeout",
            ""  # Unknown errors are retriable
        ]
        return error_type in retriable_errors


class CircuitBreaker:
    """
    Circuit breaker pattern implementation.

    Prevents cascading failures by failing fast when a service is down.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        success_threshold: int = 2,
        timeout: float = 60.0,
        half_open_max_calls: int = 3
    ):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            success_threshold: Number of successes to close circuit from half-open
            timeout: Time in seconds before trying again (open -> half-open)
            half_open_max_calls: Max calls allowed in half-open state
        """
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout = timeout
        self.half_open_max_calls = half_open_max_calls

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.half_open_calls = 0
        self.lock = threading.Lock()

        self.logger = logging.getLogger(__name__)

    def allow_request(self) -> bool:
        """Check if request should be allowed."""
        with self.lock:
            if self.state == CircuitState.CLOSED:
                return True

            if self.state == CircuitState.OPEN:
                # Check if timeout has elapsed
                if self.last_failure_time and \
                   (time.time() - self.last_failure_time) > self.timeout:
                    self.logger.info("Circuit breaker transitioning to HALF_OPEN")
                    self.state = CircuitState.HALF_OPEN
                    self.half_open_calls = 0
                    self.success_count = 0
                    return True
                return False

            if self.state == CircuitState.HALF_OPEN:
                if self.half_open_calls < self.half_open_max_calls:
                    self.half_open_calls += 1
                    return True
                return False

        return False

    def record_success(self):
        """Record a successful call."""
        with self.lock:
            self.failure_count = 0

            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.success_threshold:
                    self.logger.info("Circuit breaker closing (service recovered)")
                    self.state = CircuitState.CLOSED
                    self.success_count = 0
                    self.half_open_calls = 0

    def record_failure(self):
        """Record a failed call."""
        with self.lock:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.state == CircuitState.HALF_OPEN:
                self.logger.warning("Circuit breaker opening (service still failing)")
                self.state = CircuitState.OPEN
                self.half_open_calls = 0
            elif self.state == CircuitState.CLOSED:
                if self.failure_count >= self.failure_threshold:
                    self.logger.warning(f"Circuit breaker opening (failure threshold reached: {self.failure_count})")
                    self.state = CircuitState.OPEN

    def get_state(self) -> Dict[str, Any]:
        """Get current circuit breaker state."""
        with self.lock:
            return {
                "state": self.state.value,
                "failure_count": self.failure_count,
                "success_count": self.success_count,
                "last_failure_time": self.last_failure_time
            }


class RateLimiter:
    """
    Rate limiting for network operations.

    Supports multiple algorithms:
    - Token bucket
    - Sliding window
    - Fixed window
    """

    def __init__(self, config_manager=None):
        """
        Initialize rate limiter.

        Args:
            config_manager: Optional configuration manager
        """
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)
        self.limiters = {}
        self.lock = threading.Lock()

    def execute(
        self,
        key: str,
        algorithm: str = "token_bucket",
        rate: int = 100,
        window: float = 60.0,
        burst: int = 20,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Check if request is allowed under rate limit.

        Args:
            key: Unique key for this rate limit (e.g., "user:123" or "api:endpoint")
            algorithm: Rate limiting algorithm (token_bucket, sliding_window, fixed_window)
            rate: Number of requests allowed per window
            window: Time window in seconds
            burst: Burst capacity (for token bucket)

        Returns:
            Dict with allowed status and rate limit info
        """
        with self.lock:
            if key not in self.limiters:
                if algorithm == "token_bucket":
                    self.limiters[key] = TokenBucket(rate, window, burst)
                elif algorithm == "sliding_window":
                    self.limiters[key] = SlidingWindow(rate, window)
                elif algorithm == "fixed_window":
                    self.limiters[key] = FixedWindow(rate, window)
                else:
                    return {
                        "success": False,
                        "error": f"Unknown algorithm: {algorithm}",
                        "valid_algorithms": ["token_bucket", "sliding_window", "fixed_window"]
                    }

            limiter = self.limiters[key]
            allowed = limiter.allow_request()

            return {
                "success": True,
                "allowed": allowed,
                "key": key,
                "algorithm": algorithm,
                "stats": limiter.get_stats()
            }


class TokenBucket:
    """Token bucket rate limiting algorithm."""

    def __init__(self, rate: int, window: float, burst: int):
        """
        Initialize token bucket.

        Args:
            rate: Tokens added per window
            window: Time window in seconds
            burst: Maximum bucket capacity
        """
        self.rate = rate
        self.window = window
        self.burst = burst
        self.tokens = burst
        self.last_update = time.time()
        self.lock = threading.Lock()

    def allow_request(self) -> bool:
        """Check if request is allowed."""
        with self.lock:
            now = time.time()
            elapsed = now - self.last_update

            # Add tokens based on elapsed time
            tokens_to_add = (elapsed / self.window) * self.rate
            self.tokens = min(self.burst, self.tokens + tokens_to_add)
            self.last_update = now

            # Try to consume a token
            if self.tokens >= 1:
                self.tokens -= 1
                return True
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Get current stats."""
        with self.lock:
            return {
                "tokens_available": self.tokens,
                "burst_capacity": self.burst,
                "rate": self.rate,
                "window": self.window
            }


class SlidingWindow:
    """Sliding window rate limiting algorithm."""

    def __init__(self, rate: int, window: float):
        """
        Initialize sliding window.

        Args:
            rate: Max requests per window
            window: Time window in seconds
        """
        self.rate = rate
        self.window = window
        self.requests = deque()
        self.lock = threading.Lock()

    def allow_request(self) -> bool:
        """Check if request is allowed."""
        with self.lock:
            now = time.time()
            cutoff = now - self.window

            # Remove old requests
            while self.requests and self.requests[0] < cutoff:
                self.requests.popleft()

            # Check if under limit
            if len(self.requests) < self.rate:
                self.requests.append(now)
                return True
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Get current stats."""
        with self.lock:
            return {
                "current_requests": len(self.requests),
                "max_requests": self.rate,
                "window": self.window
            }


class FixedWindow:
    """Fixed window rate limiting algorithm."""

    def __init__(self, rate: int, window: float):
        """
        Initialize fixed window.

        Args:
            rate: Max requests per window
            window: Time window in seconds
        """
        self.rate = rate
        self.window = window
        self.window_start = time.time()
        self.request_count = 0
        self.lock = threading.Lock()

    def allow_request(self) -> bool:
        """Check if request is allowed."""
        with self.lock:
            now = time.time()

            # Check if we need to reset the window
            if now - self.window_start >= self.window:
                self.window_start = now
                self.request_count = 0

            # Check if under limit
            if self.request_count < self.rate:
                self.request_count += 1
                return True
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Get current stats."""
        with self.lock:
            return {
                "current_requests": self.request_count,
                "max_requests": self.rate,
                "window": self.window,
                "window_reset": self.window_start + self.window
            }
