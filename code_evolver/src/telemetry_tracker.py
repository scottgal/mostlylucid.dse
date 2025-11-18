"""
OpenTelemetry-based Performance Tracker

Replaces optimized_perf_tracker.py with industry-standard observability:
- OpenTelemetry for traces, metrics, and logs
- Configurable exporters (Loki, OTLP, Jaeger, etc.)
- Context propagation for parent-child relationships
- Automatic instrumentation for tool calls
- Drift detection integration
"""

import time
import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from contextlib import contextmanager

# OpenTelemetry imports
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader, ConsoleMetricExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter as GRPCSpanExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter as HTTPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter as GRPCMetricExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter as HTTPMetricExporter
from opentelemetry.trace import Status, StatusCode
from opentelemetry.metrics import CallbackOptions, Observation


# Loki logging handler
import logging
import logging_loki


@dataclass
class TelemetryConfig:
    """Configuration for telemetry system"""
    enabled: bool = True
    service_name: str = "code-evolver"
    environment: str = "development"

    # Trace configuration
    traces_enabled: bool = True
    traces_exporter: str = "otlp"  # otlp, console, jaeger
    traces_endpoint: Optional[str] = None  # e.g., http://localhost:4318/v1/traces
    traces_protocol: str = "http"  # http or grpc
    traces_sample_rate: float = 1.0  # 0.0 to 1.0

    # Metrics configuration
    metrics_enabled: bool = True
    metrics_exporter: str = "otlp"  # otlp, console, prometheus
    metrics_endpoint: Optional[str] = None
    metrics_protocol: str = "http"
    metrics_export_interval_ms: int = 30000  # 30 seconds

    # Loki configuration
    loki_enabled: bool = True
    loki_url: str = "http://localhost:3100/loki/api/v1/push"
    loki_labels: Dict[str, str] = field(default_factory=lambda: {"application": "code-evolver"})
    log_level: str = "INFO"

    # Drift detection configuration
    drift_detection_enabled: bool = True
    drift_threshold: float = 0.15  # 15% deviation triggers drift alert
    drift_window_size: int = 100  # Number of samples for baseline

    # Performance thresholds (for anomaly detection)
    thresholds: Dict[str, float] = field(default_factory=dict)

    @classmethod
    def from_yaml(cls, config_path: str) -> 'TelemetryConfig':
        """Load configuration from YAML file"""
        path = Path(config_path)
        if not path.exists():
            return cls()  # Return defaults

        try:
            with open(path) as f:
                data = yaml.safe_load(f)
                telemetry_config = data.get('telemetry', {})
                return cls(**telemetry_config)
        except Exception as e:
            logging.warning(f"Failed to load telemetry config: {e}. Using defaults.")
            return cls()


class TelemetryTracker:
    """
    OpenTelemetry-based performance and observability tracker.

    Features:
    - Distributed tracing with context propagation
    - Metrics collection (counters, histograms, gauges)
    - Structured logging to Loki
    - Configurable exporters
    - Drift detection integration
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, config_path: str = "code_evolver/config/telemetry.yaml"):
        if hasattr(self, '_initialized'):
            return

        self._initialized = True
        self.config = TelemetryConfig.from_yaml(config_path)

        # Initialize OpenTelemetry
        self._setup_tracing()
        self._setup_metrics()
        self._setup_logging()

        # Drift detection storage
        self.drift_baselines: Dict[str, List[float]] = {}
        self.drift_alerts: List[Dict[str, Any]] = []

    def _setup_tracing(self):
        """Setup OpenTelemetry tracing"""
        if not self.config.traces_enabled:
            self.tracer = None
            return

        # Create resource with service information
        resource = Resource.create({
            "service.name": self.config.service_name,
            "deployment.environment": self.config.environment,
        })

        # Create tracer provider
        tracer_provider = TracerProvider(resource=resource)

        # Add span processors based on configuration
        if self.config.traces_exporter == "console":
            tracer_provider.add_span_processor(
                BatchSpanProcessor(ConsoleSpanExporter())
            )
        elif self.config.traces_exporter == "otlp":
            # Determine exporter based on protocol
            if self.config.traces_protocol == "grpc":
                exporter = GRPCSpanExporter(
                    endpoint=self.config.traces_endpoint or "localhost:4317"
                )
            else:  # http
                exporter = HTTPSpanExporter(
                    endpoint=self.config.traces_endpoint or "http://localhost:4318/v1/traces"
                )

            tracer_provider.add_span_processor(BatchSpanProcessor(exporter))

        # Set as global tracer provider
        trace.set_tracer_provider(tracer_provider)
        self.tracer = trace.get_tracer(__name__)

        logging.info(f"OpenTelemetry tracing initialized: {self.config.traces_exporter}")

    def _setup_metrics(self):
        """Setup OpenTelemetry metrics"""
        if not self.config.metrics_enabled:
            self.meter = None
            return

        # Create resource
        resource = Resource.create({
            "service.name": self.config.service_name,
            "deployment.environment": self.config.environment,
        })

        # Create metric exporter
        if self.config.metrics_exporter == "console":
            exporter = ConsoleMetricExporter()
        elif self.config.metrics_exporter == "otlp":
            if self.config.metrics_protocol == "grpc":
                exporter = GRPCMetricExporter(
                    endpoint=self.config.metrics_endpoint or "localhost:4317"
                )
            else:  # http
                exporter = HTTPMetricExporter(
                    endpoint=self.config.metrics_endpoint or "http://localhost:4318/v1/metrics"
                )
        else:
            exporter = ConsoleMetricExporter()

        # Create meter provider with periodic export
        reader = PeriodicExportingMetricReader(
            exporter,
            export_interval_millis=self.config.metrics_export_interval_ms
        )
        meter_provider = MeterProvider(resource=resource, metric_readers=[reader])
        metrics.set_meter_provider(meter_provider)

        # Create meter and instruments
        self.meter = metrics.get_meter(__name__)

        # Create instruments
        self.tool_call_counter = self.meter.create_counter(
            name="tool.calls.total",
            description="Total number of tool calls",
            unit="1"
        )

        self.tool_duration_histogram = self.meter.create_histogram(
            name="tool.duration",
            description="Tool call duration",
            unit="ms"
        )

        self.tool_error_counter = self.meter.create_counter(
            name="tool.errors.total",
            description="Total number of tool errors",
            unit="1"
        )

        self.drift_gauge = self.meter.create_gauge(
            name="tool.drift.score",
            description="Performance drift score for tool",
            unit="1"
        )

        logging.info(f"OpenTelemetry metrics initialized: {self.config.metrics_exporter}")

    def _setup_logging(self):
        """Setup Loki logging handler"""
        if not self.config.loki_enabled:
            return

        try:
            # Create Loki handler
            handler = logging_loki.LokiHandler(
                url=self.config.loki_url,
                tags=self.config.loki_labels,
                version="1",
            )

            # Add to root logger
            logger = logging.getLogger()
            logger.addHandler(handler)
            logger.setLevel(getattr(logging, self.config.log_level.upper()))

            logging.info(f"Loki logging initialized: {self.config.loki_url}")
        except Exception as e:
            logging.warning(f"Failed to initialize Loki logging: {e}")

    @contextmanager
    def track_tool_call(self, tool_name: str, params: Dict[str, Any], parent_context: Optional[Any] = None):
        """
        Context manager for tracking tool calls with OpenTelemetry.

        Usage:
            with tracker.track_tool_call("my_tool", {"param": "value"}) as span:
                # Do work
                span.set_attribute("result.count", 42)
        """
        start_time = time.time()
        span = None

        try:
            # Create span if tracing enabled
            if self.tracer:
                span = self.tracer.start_span(
                    name=f"tool.{tool_name}",
                    context=parent_context
                )

                # Add attributes
                span.set_attribute("tool.name", tool_name)
                span.set_attribute("tool.params.count", len(params))

                # Add sanitized parameters (avoid large values)
                for key, value in params.items():
                    str_value = str(value)
                    if len(str_value) > 200:
                        str_value = str_value[:200] + "..."
                    span.set_attribute(f"tool.param.{key}", str_value)

            # Increment call counter
            if self.meter:
                self.tool_call_counter.add(
                    1,
                    {"tool.name": tool_name, "environment": self.config.environment}
                )

            # Log tool call
            logging.info(
                f"Tool call started: {tool_name}",
                extra={
                    "tool_name": tool_name,
                    "param_count": len(params),
                    "environment": self.config.environment
                }
            )

            yield span

            # Success path
            duration_ms = (time.time() - start_time) * 1000

            if span:
                span.set_status(Status(StatusCode.OK))
                span.set_attribute("tool.duration_ms", duration_ms)

            # Record duration metric
            if self.meter:
                self.tool_duration_histogram.record(
                    duration_ms,
                    {"tool.name": tool_name, "status": "success"}
                )

            # Check for drift
            if self.config.drift_detection_enabled:
                self._check_drift(tool_name, duration_ms)

            logging.info(
                f"Tool call completed: {tool_name} ({duration_ms:.2f}ms)",
                extra={
                    "tool_name": tool_name,
                    "duration_ms": duration_ms,
                    "status": "success"
                }
            )

        except Exception as e:
            # Error path
            duration_ms = (time.time() - start_time) * 1000

            if span:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.set_attribute("error.type", type(e).__name__)
                span.set_attribute("error.message", str(e))
                span.set_attribute("tool.duration_ms", duration_ms)

            # Record error metric
            if self.meter:
                self.tool_error_counter.add(
                    1,
                    {
                        "tool.name": tool_name,
                        "error.type": type(e).__name__
                    }
                )

                self.tool_duration_histogram.record(
                    duration_ms,
                    {"tool.name": tool_name, "status": "error"}
                )

            logging.error(
                f"Tool call failed: {tool_name} ({duration_ms:.2f}ms) - {str(e)}",
                extra={
                    "tool_name": tool_name,
                    "duration_ms": duration_ms,
                    "status": "error",
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                },
                exc_info=True
            )

            raise

        finally:
            if span:
                span.end()

    def _check_drift(self, tool_name: str, duration_ms: float):
        """
        Check for performance drift using statistical analysis.

        Compares current performance against historical baseline.
        """
        # Initialize baseline if needed
        if tool_name not in self.drift_baselines:
            self.drift_baselines[tool_name] = []

        baseline = self.drift_baselines[tool_name]
        baseline.append(duration_ms)

        # Keep only recent window
        if len(baseline) > self.config.drift_window_size:
            baseline.pop(0)

        # Need enough samples for drift detection
        if len(baseline) < 10:
            return

        # Calculate baseline stats
        import numpy as np
        baseline_mean = np.mean(baseline[:-1])  # Exclude current sample
        baseline_std = np.std(baseline[:-1])

        if baseline_std == 0:
            return  # No variance, can't detect drift

        # Calculate z-score for current sample
        z_score = abs((duration_ms - baseline_mean) / baseline_std)

        # Check if drift threshold exceeded
        if z_score > (self.config.drift_threshold * 10):  # Scale threshold
            drift_alert = {
                "timestamp": datetime.now().isoformat(),
                "tool_name": tool_name,
                "current_duration_ms": duration_ms,
                "baseline_mean_ms": baseline_mean,
                "baseline_std_ms": baseline_std,
                "z_score": z_score,
                "drift_severity": "high" if z_score > 3 else "medium"
            }

            self.drift_alerts.append(drift_alert)

            # Log drift alert
            logging.warning(
                f"Performance drift detected: {tool_name}",
                extra=drift_alert
            )

            # Record drift metric
            if self.meter:
                # This requires creating observable gauge with callback
                pass  # Simplified for now

    def get_drift_alerts(self, tool_name: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent drift alerts"""
        alerts = self.drift_alerts[-limit:]

        if tool_name:
            alerts = [a for a in alerts if a["tool_name"] == tool_name]

        return alerts

    def clear_drift_alerts(self, tool_name: Optional[str] = None):
        """Clear drift alerts"""
        if tool_name:
            self.drift_alerts = [a for a in self.drift_alerts if a["tool_name"] != tool_name]
        else:
            self.drift_alerts.clear()

    def get_statistics(self, tool_name: Optional[str] = None) -> Dict[str, Any]:
        """Get performance statistics"""
        if tool_name:
            baseline = self.drift_baselines.get(tool_name, [])
            if not baseline:
                return {"tool": tool_name, "samples": 0}

            import numpy as np
            return {
                "tool": tool_name,
                "samples": len(baseline),
                "mean_duration_ms": np.mean(baseline),
                "std_duration_ms": np.std(baseline),
                "min_duration_ms": np.min(baseline),
                "max_duration_ms": np.max(baseline),
                "median_duration_ms": np.median(baseline)
            }
        else:
            # Return stats for all tools
            import numpy as np
            stats = {}
            for name, baseline in self.drift_baselines.items():
                if baseline:
                    stats[name] = {
                        "samples": len(baseline),
                        "mean_duration_ms": np.mean(baseline),
                        "std_duration_ms": np.std(baseline),
                        "min_duration_ms": np.min(baseline),
                        "max_duration_ms": np.max(baseline),
                        "median_duration_ms": np.median(baseline)
                    }
            return stats

    def shutdown(self):
        """Graceful shutdown"""
        logging.info("Shutting down telemetry tracker")

        # Flush any pending data
        if self.tracer:
            trace.get_tracer_provider().shutdown()

        if self.meter:
            metrics.get_meter_provider().shutdown()


# Global instance
_tracker = None


def get_tracker() -> TelemetryTracker:
    """Get global telemetry tracker instance"""
    global _tracker
    if _tracker is None:
        _tracker = TelemetryTracker()
    return _tracker


# Convenience function for backward compatibility
def track_tool_call(tool_name: str, params: Dict[str, Any]):
    """Context manager for tracking tool calls"""
    return get_tracker().track_tool_call(tool_name, params)
