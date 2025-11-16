"""
PyInstrument-based profiling for performance analysis.

Provides decorators, context managers, and integration with the optimization system.
Profiles can be used to:
1. Compare tool versions (old vs new)
2. Evaluate workflow alternatives
3. Make data-driven optimization decisions
4. Support automatic code migration when tools are updated

Usage:
    # Environment variable control
    export CODE_EVOLVER_PROFILE=1  # Enable profiling
    export PROFILE_OUTPUT_DIR=/path/to/profiles  # Custom output directory

    # Decorator
    @profile_function(name="my_function")
    def my_function():
        pass

    # Context manager
    with ProfileContext("operation_name"):
        # code to profile
        pass

    # Manual
    profiler = Profiler()
    profiler.start()
    # ... code ...
    profile_data = profiler.stop()
"""
import os
import json
import logging
import functools
import time
from pathlib import Path
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Check if profiling is enabled via environment variable
PROFILING_ENABLED = os.getenv("CODE_EVOLVER_PROFILE", "0") == "1"
PROFILE_OUTPUT_DIR = Path(os.getenv("PROFILE_OUTPUT_DIR", "./profiles"))

# Try to import pyinstrument
try:
    from pyinstrument import Profiler as PyInstrumentProfiler
    PYINSTRUMENT_AVAILABLE = True
except ImportError:
    PYINSTRUMENT_AVAILABLE = False
    if PROFILING_ENABLED:
        logger.warning(
            "PyInstrument profiling is enabled but pyinstrument is not installed. "
            "Install with: pip install pyinstrument"
        )


class ProfileData:
    """Container for profile results."""

    def __init__(
        self,
        name: str,
        duration_ms: float,
        profile_text: Optional[str] = None,
        profile_html: Optional[str] = None,
        profile_json: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize profile data.

        Args:
            name: Name of the profiled operation
            duration_ms: Total duration in milliseconds
            profile_text: Text representation of profile
            profile_html: HTML representation of profile
            profile_json: JSON representation of profile
            metadata: Additional metadata (model, version, etc.)
        """
        self.name = name
        self.duration_ms = duration_ms
        self.profile_text = profile_text
        self.profile_html = profile_html
        self.profile_json = profile_json
        self.metadata = metadata or {}
        self.timestamp = datetime.utcnow().isoformat()

    def save(self, output_dir: Optional[Path] = None) -> Path:
        """
        Save profile data to disk.

        Args:
            output_dir: Directory to save profiles (uses PROFILE_OUTPUT_DIR if None)

        Returns:
            Path to saved profile directory
        """
        if output_dir is None:
            output_dir = PROFILE_OUTPUT_DIR

        output_dir.mkdir(parents=True, exist_ok=True)

        # Create timestamped directory for this profile
        timestamp_str = self.timestamp.replace(":", "-").replace(".", "-")
        safe_name = self.name.replace("/", "_").replace(":", "_")
        profile_dir = output_dir / f"{timestamp_str}_{safe_name}"
        profile_dir.mkdir(parents=True, exist_ok=True)

        # Save text profile
        if self.profile_text:
            text_path = profile_dir / "profile.txt"
            text_path.write_text(self.profile_text)

        # Save HTML profile
        if self.profile_html:
            html_path = profile_dir / "profile.html"
            html_path.write_text(self.profile_html)

        # Save JSON profile
        if self.profile_json:
            json_path = profile_dir / "profile.json"
            with open(json_path, 'w') as f:
                json.dump(self.profile_json, f, indent=2)

        # Save metadata
        metadata_path = profile_dir / "metadata.json"
        metadata = {
            "name": self.name,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp,
            **self.metadata
        }
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"✓ Saved profile '{self.name}' to {profile_dir}")
        return profile_dir

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage in metrics."""
        return {
            "name": self.name,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
            "has_text": self.profile_text is not None,
            "has_html": self.profile_html is not None,
            "has_json": self.profile_json is not None
        }


class Profiler:
    """
    Wrapper around PyInstrument profiler.
    Falls back to simple timing if PyInstrument is not available.
    """

    def __init__(self, name: str = "unnamed", metadata: Optional[Dict[str, Any]] = None):
        """
        Initialize profiler.

        Args:
            name: Name for this profiling session
            metadata: Additional metadata to store
        """
        self.name = name
        self.metadata = metadata or {}
        self.profiler = None
        self.start_time = None
        # Re-check environment variable each time (allows dynamic enable/disable)
        self.enabled = os.getenv("CODE_EVOLVER_PROFILE", "0") == "1"

    def start(self):
        """Start profiling."""
        if not self.enabled:
            return

        self.start_time = time.time()

        if PYINSTRUMENT_AVAILABLE:
            self.profiler = PyInstrumentProfiler()
            self.profiler.start()
            logger.debug(f"Started PyInstrument profiling for '{self.name}'")
        else:
            logger.debug(f"Started basic timing for '{self.name}' (PyInstrument not available)")

    def stop(self, save: bool = True) -> Optional[ProfileData]:
        """
        Stop profiling and return results.

        Args:
            save: Whether to save profile to disk

        Returns:
            ProfileData object or None if profiling disabled
        """
        if not self.enabled or self.start_time is None:
            return None

        duration_ms = (time.time() - self.start_time) * 1000

        profile_text = None
        profile_html = None
        profile_json = None

        if PYINSTRUMENT_AVAILABLE and self.profiler:
            self.profiler.stop()

            # Generate different output formats
            try:
                profile_text = self.profiler.output_text(unicode=True, color=False)
            except Exception as e:
                logger.warning(f"Failed to generate text profile: {e}")

            try:
                profile_html = self.profiler.output_html()
            except Exception as e:
                logger.warning(f"Failed to generate HTML profile: {e}")

            try:
                # Check if output_json method exists (added in newer versions)
                if hasattr(self.profiler, 'output_json'):
                    profile_json = json.loads(self.profiler.output_json())
                else:
                    logger.debug("output_json() not available in this PyInstrument version")
            except Exception as e:
                logger.warning(f"Failed to generate JSON profile: {e}")

            logger.info(f"✓ Profiled '{self.name}': {duration_ms:.2f}ms")
        else:
            logger.info(f"✓ Timed '{self.name}': {duration_ms:.2f}ms")

        profile_data = ProfileData(
            name=self.name,
            duration_ms=duration_ms,
            profile_text=profile_text,
            profile_html=profile_html,
            profile_json=profile_json,
            metadata=self.metadata
        )

        if save:
            profile_data.save()

        return profile_data


@contextmanager
def ProfileContext(
    name: str,
    metadata: Optional[Dict[str, Any]] = None,
    save: bool = True
):
    """
    Context manager for profiling code blocks.

    Usage:
        with ProfileContext("my_operation", metadata={"version": "1.0"}):
            # code to profile
            expensive_operation()

    Args:
        name: Name for this profiling session
        metadata: Additional metadata to store
        save: Whether to save profile to disk

    Yields:
        ProfileData object (or None if profiling disabled)
    """
    profiler = Profiler(name=name, metadata=metadata)
    profiler.start()

    profile_data = None
    try:
        yield profile_data
    finally:
        profile_data = profiler.stop(save=save)


def profile_function(
    name: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    save: bool = True
):
    """
    Decorator for profiling functions.

    Usage:
        @profile_function(name="my_function", metadata={"version": "1.0"})
        def my_function(x, y):
            return x + y

    Args:
        name: Name for profiling (uses function name if None)
        metadata: Additional metadata to store
        save: Whether to save profile to disk

    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            profile_name = name or f"{func.__module__}.{func.__name__}"

            with ProfileContext(profile_name, metadata=metadata, save=save):
                result = func(*args, **kwargs)

            return result

        return wrapper

    return decorator


class ProfileRegistry:
    """
    Global registry for collecting profiles across a session.
    Used by the optimization system to compare alternatives.
    """

    def __init__(self):
        """Initialize registry."""
        self.profiles: List[ProfileData] = []
        self.profiles_by_name: Dict[str, List[ProfileData]] = {}

    def add_profile(self, profile_data: ProfileData):
        """
        Add a profile to the registry.

        Args:
            profile_data: Profile data to add
        """
        self.profiles.append(profile_data)

        if profile_data.name not in self.profiles_by_name:
            self.profiles_by_name[profile_data.name] = []

        self.profiles_by_name[profile_data.name].append(profile_data)

        logger.debug(f"Added profile '{profile_data.name}' to registry")

    def get_profiles(self, name: Optional[str] = None) -> List[ProfileData]:
        """
        Get profiles from registry.

        Args:
            name: Optional name filter

        Returns:
            List of ProfileData objects
        """
        if name is None:
            return self.profiles

        return self.profiles_by_name.get(name, [])

    def compare_profiles(
        self,
        name: str,
        version1: str,
        version2: str
    ) -> Optional[Dict[str, Any]]:
        """
        Compare profiles for different versions of the same operation.
        Used for evaluating tool upgrades.

        Args:
            name: Operation name
            version1: First version to compare
            version2: Second version to compare

        Returns:
            Comparison results or None if not enough data
        """
        profiles = self.get_profiles(name)

        v1_profiles = [p for p in profiles if p.metadata.get("version") == version1]
        v2_profiles = [p for p in profiles if p.metadata.get("version") == version2]

        if not v1_profiles or not v2_profiles:
            return None

        v1_avg_duration = sum(p.duration_ms for p in v1_profiles) / len(v1_profiles)
        v2_avg_duration = sum(p.duration_ms for p in v2_profiles) / len(v2_profiles)

        improvement_pct = ((v1_avg_duration - v2_avg_duration) / v1_avg_duration) * 100

        return {
            "name": name,
            "version1": {
                "version": version1,
                "avg_duration_ms": v1_avg_duration,
                "sample_count": len(v1_profiles)
            },
            "version2": {
                "version": version2,
                "avg_duration_ms": v2_avg_duration,
                "sample_count": len(v2_profiles)
            },
            "improvement_pct": improvement_pct,
            "recommendation": "upgrade" if improvement_pct > 10 else "keep_current"
        }

    def export_summary(self, output_path: Optional[Path] = None) -> Dict[str, Any]:
        """
        Export summary of all profiles.

        Args:
            output_path: Optional path to save summary JSON

        Returns:
            Summary dictionary
        """
        summary = {
            "total_profiles": len(self.profiles),
            "operations": list(self.profiles_by_name.keys()),
            "profiles_by_operation": {
                name: {
                    "count": len(profiles),
                    "avg_duration_ms": sum(p.duration_ms for p in profiles) / len(profiles),
                    "min_duration_ms": min(p.duration_ms for p in profiles),
                    "max_duration_ms": max(p.duration_ms for p in profiles)
                }
                for name, profiles in self.profiles_by_name.items()
            }
        }

        if output_path:
            with open(output_path, 'w') as f:
                json.dump(summary, f, indent=2)
            logger.info(f"✓ Saved profile summary to {output_path}")

        return summary

    def clear(self):
        """Clear all profiles from registry."""
        self.profiles.clear()
        self.profiles_by_name.clear()
        logger.info("Cleared profile registry")


# Global registry instance
_global_registry = ProfileRegistry()


def get_global_registry() -> ProfileRegistry:
    """Get the global profile registry."""
    return _global_registry
