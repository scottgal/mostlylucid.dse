"""
Performance Drift Detector

Uses pattern_clusterer.py to detect performance drift and anomalies.
Analyzes telemetry data to identify:
1. Performance degradation over time
2. Anomalous behavior patterns
3. Tool usage pattern changes
4. Optimization opportunities

Integrates with TelemetryTracker to consume OpenTelemetry data.
"""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
import json
import logging
from collections import defaultdict, deque

from pattern_clusterer import PatternClusterer, OperationCluster


@dataclass
class DriftEvent:
    """Represents a detected drift event"""
    timestamp: datetime
    tool_name: str
    drift_type: str  # performance, pattern, anomaly
    severity: str  # low, medium, high, critical
    baseline_value: float
    current_value: float
    deviation_percent: float
    description: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "tool_name": self.tool_name,
            "drift_type": self.drift_type,
            "severity": self.severity,
            "baseline_value": self.baseline_value,
            "current_value": self.current_value,
            "deviation_percent": self.deviation_percent,
            "description": self.description,
            "metadata": self.metadata
        }


@dataclass
class PerformanceBaseline:
    """Statistical baseline for a tool's performance"""
    tool_name: str
    sample_count: int
    mean_duration_ms: float
    std_duration_ms: float
    p50_duration_ms: float
    p95_duration_ms: float
    p99_duration_ms: float
    last_updated: datetime
    samples: deque = field(default_factory=lambda: deque(maxlen=1000))

    def update(self, duration_ms: float):
        """Update baseline with new sample"""
        self.samples.append(duration_ms)
        self.sample_count = len(self.samples)

        if self.sample_count > 0:
            self.mean_duration_ms = np.mean(self.samples)
            self.std_duration_ms = np.std(self.samples)
            self.p50_duration_ms = np.percentile(self.samples, 50)
            self.p95_duration_ms = np.percentile(self.samples, 95)
            self.p99_duration_ms = np.percentile(self.samples, 99)
            self.last_updated = datetime.now()

    def is_anomalous(self, duration_ms: float, threshold_std: float = 3.0) -> bool:
        """Check if duration is anomalous using z-score"""
        if self.sample_count < 10 or self.std_duration_ms == 0:
            return False

        z_score = abs((duration_ms - self.mean_duration_ms) / self.std_duration_ms)
        return z_score > threshold_std

    def calculate_drift(self, recent_samples: List[float]) -> float:
        """Calculate drift score between baseline and recent samples"""
        if not recent_samples or self.sample_count < 10:
            return 0.0

        recent_mean = np.mean(recent_samples)
        drift = abs(recent_mean - self.mean_duration_ms) / self.mean_duration_ms
        return drift


class DriftDetector:
    """
    Detects performance drift and anomalies using statistical analysis
    and pattern clustering.

    Monitors:
    - Performance degradation over time
    - Anomalous tool behavior
    - Pattern changes in tool usage
    - Optimization opportunities
    """

    def __init__(
        self,
        telemetry_tracker,
        rag_memory=None,
        drift_threshold: float = 0.15,
        anomaly_threshold_std: float = 3.0,
        window_size: int = 50
    ):
        """
        Initialize drift detector.

        Args:
            telemetry_tracker: TelemetryTracker instance
            rag_memory: Optional RAG memory for pattern analysis
            drift_threshold: Threshold for drift detection (0.15 = 15%)
            anomaly_threshold_std: Standard deviations for anomaly detection
            window_size: Number of recent samples for drift calculation
        """
        self.tracker = telemetry_tracker
        self.rag = rag_memory
        self.drift_threshold = drift_threshold
        self.anomaly_threshold_std = anomaly_threshold_std
        self.window_size = window_size

        # Performance baselines per tool
        self.baselines: Dict[str, PerformanceBaseline] = {}

        # Recent samples for drift calculation
        self.recent_samples: Dict[str, deque] = defaultdict(lambda: deque(maxlen=window_size))

        # Detected drift events
        self.drift_events: List[DriftEvent] = []

        # Pattern clusterer for advanced analysis
        self.pattern_clusterer = None
        if rag_memory:
            self.pattern_clusterer = PatternClusterer(
                rag_memory,
                min_cluster_size=3,
                similarity_threshold=0.75
            )

        logging.info(f"Drift detector initialized (threshold={drift_threshold}, window={window_size})")

    def record_measurement(self, tool_name: str, duration_ms: float, metadata: Optional[Dict] = None):
        """
        Record a performance measurement for drift detection.

        Args:
            tool_name: Name of the tool
            duration_ms: Duration in milliseconds
            metadata: Optional additional metadata
        """
        # Get or create baseline
        if tool_name not in self.baselines:
            self.baselines[tool_name] = PerformanceBaseline(
                tool_name=tool_name,
                sample_count=0,
                mean_duration_ms=0.0,
                std_duration_ms=0.0,
                p50_duration_ms=0.0,
                p95_duration_ms=0.0,
                p99_duration_ms=0.0,
                last_updated=datetime.now()
            )

        baseline = self.baselines[tool_name]

        # Check for anomaly BEFORE updating baseline
        if baseline.sample_count >= 10:
            if baseline.is_anomalous(duration_ms, self.anomaly_threshold_std):
                self._record_drift_event(
                    tool_name=tool_name,
                    drift_type="anomaly",
                    severity="high",
                    baseline_value=baseline.mean_duration_ms,
                    current_value=duration_ms,
                    description=f"Anomalous duration: {duration_ms:.2f}ms vs baseline {baseline.mean_duration_ms:.2f}ms"
                )

        # Update baseline
        baseline.update(duration_ms)

        # Add to recent samples
        self.recent_samples[tool_name].append(duration_ms)

        # Check for drift if we have enough recent samples
        if len(self.recent_samples[tool_name]) >= self.window_size:
            drift_score = baseline.calculate_drift(list(self.recent_samples[tool_name]))

            if drift_score > self.drift_threshold:
                severity = self._calculate_severity(drift_score)
                self._record_drift_event(
                    tool_name=tool_name,
                    drift_type="performance",
                    severity=severity,
                    baseline_value=baseline.mean_duration_ms,
                    current_value=np.mean(self.recent_samples[tool_name]),
                    description=f"Performance drift detected: {drift_score*100:.1f}% deviation from baseline"
                )

    def _calculate_severity(self, drift_score: float) -> str:
        """Calculate severity level based on drift score"""
        if drift_score > 0.5:  # >50% drift
            return "critical"
        elif drift_score > 0.3:  # >30% drift
            return "high"
        elif drift_score > 0.15:  # >15% drift
            return "medium"
        else:
            return "low"

    def _record_drift_event(
        self,
        tool_name: str,
        drift_type: str,
        severity: str,
        baseline_value: float,
        current_value: float,
        description: str,
        metadata: Optional[Dict] = None
    ):
        """Record a drift event"""
        deviation = abs(current_value - baseline_value) / baseline_value if baseline_value > 0 else 0

        event = DriftEvent(
            timestamp=datetime.now(),
            tool_name=tool_name,
            drift_type=drift_type,
            severity=severity,
            baseline_value=baseline_value,
            current_value=current_value,
            deviation_percent=deviation * 100,
            description=description,
            metadata=metadata or {}
        )

        self.drift_events.append(event)

        # Log the event
        logging.warning(
            f"Drift detected: {tool_name} - {description}",
            extra={
                "tool_name": tool_name,
                "drift_type": drift_type,
                "severity": severity,
                "deviation_percent": deviation * 100
            }
        )

        # Keep only recent events (last 1000)
        if len(self.drift_events) > 1000:
            self.drift_events = self.drift_events[-1000:]

    def analyze_patterns(self, target_tool: Optional[str] = None) -> List[OperationCluster]:
        """
        Use pattern clusterer to analyze tool usage patterns.

        Args:
            target_tool: Optional specific tool to analyze

        Returns:
            List of operation clusters with optimization suggestions
        """
        if not self.pattern_clusterer:
            logging.warning("Pattern clusterer not available (RAG not configured)")
            return []

        try:
            clusters = self.pattern_clusterer.analyze_patterns(target_filter=target_tool)

            # Record pattern drift if clusters have changed significantly
            # This could be implemented by comparing cluster centroids over time

            return clusters
        except Exception as e:
            logging.error(f"Pattern analysis failed: {e}", exc_info=True)
            return []

    def get_drift_report(
        self,
        tool_name: Optional[str] = None,
        severity: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> List[DriftEvent]:
        """
        Get drift events matching filters.

        Args:
            tool_name: Filter by tool name
            severity: Filter by severity (low, medium, high, critical)
            since: Only events after this timestamp
            limit: Maximum number of events to return

        Returns:
            List of drift events
        """
        events = self.drift_events

        # Apply filters
        if tool_name:
            events = [e for e in events if e.tool_name == tool_name]

        if severity:
            events = [e for e in events if e.severity == severity]

        if since:
            events = [e for e in events if e.timestamp >= since]

        # Sort by timestamp (newest first) and limit
        events = sorted(events, key=lambda e: e.timestamp, reverse=True)[:limit]

        return events

    def get_baseline_stats(self, tool_name: Optional[str] = None) -> Dict[str, Any]:
        """Get baseline statistics for tools"""
        if tool_name:
            baseline = self.baselines.get(tool_name)
            if not baseline:
                return {"tool_name": tool_name, "status": "no_baseline"}

            return {
                "tool_name": tool_name,
                "sample_count": baseline.sample_count,
                "mean_duration_ms": baseline.mean_duration_ms,
                "std_duration_ms": baseline.std_duration_ms,
                "p50_duration_ms": baseline.p50_duration_ms,
                "p95_duration_ms": baseline.p95_duration_ms,
                "p99_duration_ms": baseline.p99_duration_ms,
                "last_updated": baseline.last_updated.isoformat()
            }
        else:
            # Return all baselines
            return {
                name: {
                    "sample_count": b.sample_count,
                    "mean_duration_ms": b.mean_duration_ms,
                    "std_duration_ms": b.std_duration_ms,
                    "p50_duration_ms": b.p50_duration_ms,
                    "p95_duration_ms": b.p95_duration_ms,
                    "p99_duration_ms": b.p99_duration_ms,
                    "last_updated": b.last_updated.isoformat()
                }
                for name, b in self.baselines.items()
            }

    def export_drift_report(self, output_path: Path):
        """Export drift events to JSON file"""
        report = {
            "generated_at": datetime.now().isoformat(),
            "total_events": len(self.drift_events),
            "events": [e.to_dict() for e in self.drift_events],
            "baselines": self.get_baseline_stats()
        }

        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)

        logging.info(f"Drift report exported to {output_path}")

    def clear_events(self, tool_name: Optional[str] = None):
        """Clear drift events"""
        if tool_name:
            self.drift_events = [e for e in self.drift_events if e.tool_name != tool_name]
        else:
            self.drift_events.clear()

    def reset_baseline(self, tool_name: str):
        """Reset baseline for a specific tool"""
        if tool_name in self.baselines:
            del self.baselines[tool_name]
        if tool_name in self.recent_samples:
            del self.recent_samples[tool_name]

        logging.info(f"Reset baseline for {tool_name}")


# Global instance
_detector = None


def get_detector(telemetry_tracker=None, rag_memory=None) -> DriftDetector:
    """Get global drift detector instance"""
    global _detector
    if _detector is None:
        if telemetry_tracker is None:
            from telemetry_tracker import get_tracker
            telemetry_tracker = get_tracker()

        _detector = DriftDetector(telemetry_tracker, rag_memory)
    return _detector
