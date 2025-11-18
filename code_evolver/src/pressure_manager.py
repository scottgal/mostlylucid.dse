"""
Pressure Manager - Dynamically adjusts optimization strategy based on system context.

Automatically detects:
- System resources (memory, CPU, load)
- Time of day (overnight = low pressure)
- Request type (user vs. background)
- Device type (Raspberry Pi, cloud server, etc.)

Adjusts optimization behavior to:
- Use cached workflows on low-memory devices
- Run expensive optimizations overnight
- Skip optimization during high load
- Collect training data in training mode

Usage:
    manager = PressureManager(config)

    # Get current pressure
    pressure = manager.get_current_pressure()

    # Execute with appropriate strategy
    settings = manager.get_optimization_settings(pressure)
"""
import logging
import psutil
from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class PressureLevel(Enum):
    """Pressure levels for optimization strategy."""
    HIGH = "high"           # Urgent, low resources, fast execution only
    MEDIUM = "medium"       # Normal operation, balanced
    LOW = "low"             # Plenty of resources, full optimization
    TRAINING = "training"   # Data collection mode


class PressureManager:
    """
    Manages optimization pressure based on system context.

    Automatically adjusts strategy for different environments:
    - Raspberry Pi: High pressure (cache-only, no optimization)
    - Cloud server: Low pressure (full optimization)
    - Overnight: Low pressure (expensive cloud optimization)
    - High load: High pressure (fast execution)
    """

    def __init__(self, config_manager):
        """
        Initialize pressure manager.

        Args:
            config_manager: ConfigManager instance
        """
        self.config = config_manager

        # Load pressure configuration
        self.pressure_config = config_manager.get("optimization_pressure", {})
        self.auto_config = self.pressure_config.get("auto", {})

        # Detect device type
        self.device_type = self._detect_device_type()

        # Get system resources
        self.total_memory_mb = psutil.virtual_memory().total / (1024 * 1024)
        self.cpu_count = psutil.cpu_count()

        logger.info(f"Pressure manager initialized: device={self.device_type}, "
                   f"memory={self.total_memory_mb:.0f}MB, cpus={self.cpu_count}")

    def get_current_pressure(
        self,
        context: Optional[Dict[str, Any]] = None
    ) -> PressureLevel:
        """
        Determine current pressure level based on system state and context.

        Args:
            context: Optional context (user_request, scheduled_task, etc.)

        Returns:
            Current pressure level
        """
        # Check if auto pressure is enabled
        if not self.auto_config.get("enabled", True):
            # Use default pressure
            default = self.auto_config.get("default", "medium")
            return PressureLevel(default)

        # Check explicit context
        if context:
            if context.get("training_mode"):
                return PressureLevel.TRAINING
            if context.get("urgent"):
                return PressureLevel.HIGH
            if context.get("background"):
                return PressureLevel.LOW

        # Low-memory device detection (Raspberry Pi, IoT)
        if self.is_low_memory_device():
            logger.debug("Low-memory device detected, using HIGH pressure")
            return PressureLevel.HIGH

        # Check system load
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory_percent = psutil.virtual_memory().percent

        if cpu_percent > 80 or memory_percent > 80:
            logger.debug(f"High system load (CPU={cpu_percent}%, MEM={memory_percent}%), "
                        f"using HIGH pressure")
            return PressureLevel.HIGH

        # Check time of day (overnight = low pressure)
        current_hour = datetime.now().hour
        if current_hour >= 22 or current_hour <= 6:
            logger.debug(f"Overnight hours (hour={current_hour}), using LOW pressure")
            return PressureLevel.LOW

        # Check rules from config
        rules = self.auto_config.get("rules", [])
        for rule in rules:
            if self._evaluate_rule(rule, context, current_hour, cpu_percent, memory_percent):
                pressure = rule.get("pressure", "medium")
                logger.debug(f"Rule matched: {rule.get('condition')}, pressure={pressure}")
                return PressureLevel(pressure)

        # Default to medium pressure
        default = self.auto_config.get("default", "medium")
        return PressureLevel(default)

    def get_optimization_settings(
        self,
        pressure: PressureLevel
    ) -> Dict[str, Any]:
        """
        Get optimization settings for given pressure level.

        Args:
            pressure: Pressure level

        Returns:
            Optimization settings dict
        """
        settings = self.pressure_config.get(pressure.value, {})

        # Add computed settings
        settings["pressure"] = pressure.value
        settings["device_type"] = self.device_type
        settings["available_memory_mb"] = psutil.virtual_memory().available / (1024 * 1024)

        logger.info(f"Optimization settings for {pressure.value} pressure: "
                   f"level={settings.get('optimization_level')}, "
                   f"max_cost=${settings.get('max_cost', 0):.2f}, "
                   f"evolutionary_pressure={settings.get('evolutionary_pressure', 'balanced')}")

        return settings

    def get_evolutionary_adjustments(
        self,
        pressure: PressureLevel,
        base_similarity: float = 0.96,
        base_max_distance: float = 0.30
    ) -> Dict[str, Any]:
        """
        Get evolutionary pressure adjustments for optimizer parameters.

        Evolutionary pressure controls whether the optimizer tends towards:
        - "granular": Smaller, more specific functions (tighter clustering, more specialized nodes)
        - "generic": Larger, more encompassing functions (looser clustering, more general nodes)
        - "balanced": Middle ground (default behavior)

        Args:
            pressure: Current pressure level
            base_similarity: Base similarity threshold for clustering (default: 0.96)
            base_max_distance: Base max distance from fittest for pruning (default: 0.30)

        Returns:
            Dict with adjusted parameters:
                - similarity_threshold: Adjusted threshold for variant clustering
                - max_distance_from_fittest: Adjusted max fitness gap for pruning
                - min_cluster_size: Minimum variants in a cluster
                - merge_similar_functions: Whether to merge similar function nodes
                - specialization_bias: Float 0.0-1.0 (0=generic, 1=specialized)
        """
        settings = self.pressure_config.get(pressure.value, {})
        evo_pressure = settings.get("evolutionary_pressure", "balanced")

        # Default adjustments for balanced evolutionary pressure
        adjustments = {
            "evolutionary_pressure": evo_pressure,
            "similarity_threshold": base_similarity,
            "max_distance_from_fittest": base_max_distance,
            "min_cluster_size": 2,
            "merge_similar_functions": False,
            "specialization_bias": 0.5
        }

        if evo_pressure == "granular":
            # Tend towards smaller, more specific functions
            # - Tighter similarity thresholds (require more similarity to cluster)
            # - Smaller distance tolerance (prune variants that deviate more)
            # - Higher minimum cluster size (avoid tiny clusters)
            # - Don't merge similar functions (keep them separate)
            # - High specialization bias
            adjustments.update({
                "similarity_threshold": min(0.98, base_similarity + 0.02),
                "max_distance_from_fittest": max(0.15, base_max_distance - 0.15),
                "min_cluster_size": 3,
                "merge_similar_functions": False,
                "specialization_bias": 0.8
            })
            logger.debug(f"Granular evolutionary pressure: tighter clustering (sim={adjustments['similarity_threshold']:.2f})")

        elif evo_pressure == "generic":
            # Tend towards larger, more encompassing functions
            # - Looser similarity thresholds (allow more variants to cluster together)
            # - Larger distance tolerance (keep more diverse variants)
            # - Lower minimum cluster size (allow smaller clusters)
            # - Merge similar functions (consolidate related functionality)
            # - Low specialization bias
            adjustments.update({
                "similarity_threshold": max(0.85, base_similarity - 0.11),
                "max_distance_from_fittest": min(0.50, base_max_distance + 0.20),
                "min_cluster_size": 1,
                "merge_similar_functions": True,
                "specialization_bias": 0.2
            })
            logger.debug(f"Generic evolutionary pressure: looser clustering (sim={adjustments['similarity_threshold']:.2f})")

        else:  # balanced
            # Keep defaults
            logger.debug(f"Balanced evolutionary pressure: standard clustering (sim={adjustments['similarity_threshold']:.2f})")

        return adjustments

    def is_low_memory_device(self) -> bool:
        """
        Detect if running on low-memory device (Raspberry Pi, IoT, etc.).

        Returns:
            True if low-memory device
        """
        # Raspberry Pi typically has <= 8GB RAM
        # Most have 1-4GB
        if self.total_memory_mb <= 8192:  # 8GB or less
            return True

        # Check if device is ARM-based (common for Pi, IoT)
        import platform
        machine = platform.machine().lower()
        if any(arch in machine for arch in ["arm", "aarch"]):
            return True

        return False

    def _detect_device_type(self) -> str:
        """
        Detect device type (raspberry_pi, cloud, workstation, etc.).

        Returns:
            Device type string
        """
        import platform

        # Check for Raspberry Pi
        try:
            with open("/proc/device-tree/model", "r") as f:
                model = f.read()
                if "raspberry pi" in model.lower():
                    return "raspberry_pi"
        except:
            pass

        # Check for cloud providers
        try:
            # AWS EC2
            import requests
            requests.get("http://169.254.169.254/latest/meta-data/", timeout=0.1)
            return "aws_ec2"
        except:
            pass

        # Check system specs
        mem_gb = self.total_memory_mb / 1024
        cpu_count = psutil.cpu_count()

        if mem_gb <= 8 and cpu_count <= 4:
            return "low_end"  # Raspberry Pi, small VM, etc.
        elif mem_gb <= 32 and cpu_count <= 16:
            return "workstation"
        else:
            return "high_end"  # Cloud server, powerful workstation

    def _evaluate_rule(
        self,
        rule: Dict[str, Any],
        context: Optional[Dict[str, Any]],
        current_hour: int,
        cpu_percent: float,
        memory_percent: float
    ) -> bool:
        """
        Evaluate a pressure rule.

        Args:
            rule: Rule dict with 'condition' and 'pressure'
            context: Execution context
            current_hour: Current hour (0-23)
            cpu_percent: CPU usage percentage
            memory_percent: Memory usage percentage

        Returns:
            True if rule matches
        """
        condition = rule.get("condition", "")

        # Simple condition evaluation
        # Would be better with a proper expression parser

        # Time-based rules
        if "hour >=" in condition or "hour <=" in condition:
            try:
                # Parse "hour >= 22 or hour <= 6"
                if "or" in condition:
                    parts = condition.split("or")
                    return any(self._eval_hour_condition(p.strip(), current_hour)
                             for p in parts)
                else:
                    return self._eval_hour_condition(condition, current_hour)
            except:
                pass

        # Load-based rules
        if "system_load" in condition:
            try:
                # Parse "system_load > 0.8"
                threshold = float(condition.split(">")[1].strip())
                avg_load = (cpu_percent + memory_percent) / 200  # Normalize to 0-1
                return avg_load > threshold
            except:
                pass

        # Context-based rules
        if context:
            if "user_request" in condition and context.get("user_request"):
                return True
            if "scheduled_task" in condition and context.get("scheduled_task"):
                return True

        return False

    def _eval_hour_condition(self, condition: str, hour: int) -> bool:
        """Evaluate hour-based condition."""
        try:
            if ">=" in condition:
                threshold = int(condition.split(">=")[1].strip())
                return hour >= threshold
            elif "<=" in condition:
                threshold = int(condition.split("<=")[1].strip())
                return hour <= threshold
        except:
            pass
        return False

    def get_raspberry_pi_settings(self) -> Dict[str, Any]:
        """
        Get optimized settings for Raspberry Pi execution.

        Returns:
            Raspberry Pi-specific settings
        """
        return {
            "pressure": "high",
            "optimization_level": "none",
            "cache_only": True,
            "max_memory_mb": min(512, self.total_memory_mb * 0.5),  # Use max 50% memory
            "use_swap": False,  # Avoid swap on SD card
            "batch_size": 1,  # Process one at a time
            "parallel_workers": 1,  # Single-threaded
            "aggressive_gc": True,  # Aggressive garbage collection
            "notes": "Optimized for low-memory ARM device (Raspberry Pi)"
        }

    def should_use_cache_only(self, pressure: PressureLevel) -> bool:
        """
        Determine if execution should use cache-only mode.

        Args:
            pressure: Current pressure level

        Returns:
            True if should use cache-only
        """
        settings = self.get_optimization_settings(pressure)
        return settings.get("cache_only", False) or self.is_low_memory_device()

    def should_store_executions(self, pressure: PressureLevel) -> bool:
        """
        Determine if executions should be tracked/stored.

        Args:
            pressure: Current pressure level

        Returns:
            True if should store executions
        """
        settings = self.get_optimization_settings(pressure)
        return settings.get("store_executions", False) or \
               settings.get("store_all_executions", False)

    def can_meet_quality_requirement(
        self,
        pressure: PressureLevel,
        required_quality: float,
        estimated_workflow_quality: Optional[float] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if given pressure can meet quality requirements.

        Args:
            pressure: Pressure level to check
            required_quality: Required quality score (0.0-1.0)
            estimated_workflow_quality: Estimated quality for cached workflow

        Returns:
            (can_meet, reason) tuple
            - can_meet: True if can meet requirements
            - reason: Explanation if cannot meet
        """
        settings = self.get_optimization_settings(pressure)
        min_threshold = settings.get("min_quality_threshold", 0.0)

        # Check if required quality is achievable under this pressure
        if required_quality > min_threshold:
            # Can't meet requirements
            fallback = settings.get("fallback_pressure")
            if fallback:
                return False, (
                    f"Required quality {required_quality:.2f} exceeds "
                    f"{pressure.value} pressure threshold {min_threshold:.2f}. "
                    f"Suggest using '{fallback}' pressure instead."
                )
            else:
                return False, (
                    f"Required quality {required_quality:.2f} cannot be met "
                    f"under {pressure.value} pressure (max: {min_threshold:.2f}). "
                    f"No alternative pressure available."
                )

        # If using cached workflow, check its quality
        if settings.get("cache_only") and estimated_workflow_quality is not None:
            if estimated_workflow_quality < required_quality:
                return False, (
                    f"Cached workflow quality {estimated_workflow_quality:.2f} "
                    f"below required {required_quality:.2f}. "
                    f"Cache-only mode cannot improve quality."
                )

        return True, None

    def negotiate_pressure(
        self,
        required_quality: float,
        max_latency_ms: Optional[float] = None,
        max_cost: Optional[float] = None
    ) -> Tuple[PressureLevel, str]:
        """
        Negotiate appropriate pressure level based on requirements.

        Tries to find the highest pressure (fastest/cheapest) that can
        meet quality requirements.

        Args:
            required_quality: Required quality score (0.0-1.0)
            max_latency_ms: Maximum acceptable latency (optional)
            max_cost: Maximum acceptable cost (optional)

        Returns:
            (pressure_level, rationale) tuple
        """
        # Try pressure levels from high to low (prefer fast/cheap)
        for pressure in [PressureLevel.HIGH, PressureLevel.MEDIUM, PressureLevel.LOW]:
            settings = self.get_optimization_settings(pressure)

            # Check quality threshold
            min_quality = settings.get("min_quality_threshold", 0.0)
            if required_quality > min_quality:
                continue  # Can't meet quality requirement

            # Check latency constraint
            max_pressure_latency = settings.get("max_latency_ms")
            if max_latency_ms and max_pressure_latency:
                if max_latency_ms < max_pressure_latency:
                    continue  # Too slow

            # Check cost constraint
            max_pressure_cost = settings.get("max_cost", 0.0)
            if max_cost and max_pressure_cost > max_cost:
                continue  # Too expensive

            # This pressure level works!
            rationale = (
                f"Selected {pressure.value} pressure: "
                f"quality threshold {min_quality:.2f} >= required {required_quality:.2f}"
            )

            if max_latency_ms:
                rationale += f", latency {max_pressure_latency}ms <= {max_latency_ms}ms"
            if max_cost:
                rationale += f", cost ${max_pressure_cost:.2f} <= ${max_cost:.2f}"

            return pressure, rationale

        # No pressure level can meet requirements
        return PressureLevel.LOW, (
            f"No pressure level can meet requirements "
            f"(quality>={required_quality:.2f}). "
            f"Using LOW pressure (best effort)."
        )

    def reject_if_quality_too_low(
        self,
        pressure: PressureLevel,
        estimated_quality: float,
        task_description: str
    ) -> Optional[str]:
        """
        Check if task should be rejected due to quality constraints.

        Args:
            pressure: Current pressure level
            estimated_quality: Estimated quality of execution
            task_description: Description of task

        Returns:
            Rejection message if should reject, None otherwise
        """
        settings = self.get_optimization_settings(pressure)

        # Check if this pressure level can reject
        can_reject = settings.get("can_reject", False)
        if not can_reject:
            return None  # This pressure level never rejects

        # Check quality threshold
        min_threshold = settings.get("min_quality_threshold", 0.0)
        if estimated_quality < min_threshold:
            fallback = settings.get("fallback_pressure")

            message = (
                f"QUALITY_TOO_LOW: Task '{task_description}' "
                f"estimated quality {estimated_quality:.2f} "
                f"below {pressure.value} pressure threshold {min_threshold:.2f}."
            )

            if fallback:
                message += (
                    f"\n\nSuggestion: Retry with '{fallback}' pressure for better quality, "
                    f"or accept lower quality by lowering requirements."
                )
            else:
                message += (
                    f"\n\nNo alternative available. "
                    f"Either accept lower quality or wait for system resources."
                )

            return message

        return None

    def get_pressure_stats(self) -> Dict[str, Any]:
        """Get statistics about pressure management."""
        current_pressure = self.get_current_pressure()

        return {
            "device_type": self.device_type,
            "is_low_memory": self.is_low_memory_device(),
            "total_memory_mb": self.total_memory_mb,
            "available_memory_mb": psutil.virtual_memory().available / (1024 * 1024),
            "cpu_count": self.cpu_count,
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
            "current_pressure": current_pressure.value,
            "current_hour": datetime.now().hour,
            "recommended_settings": self.get_optimization_settings(current_pressure)
        }
