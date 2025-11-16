"""
Unit tests for profiling module.
Tests the PyInstrument profiling integration, decorators, context managers,
and profile registry.
"""
import unittest
import time
import os
import tempfile
from pathlib import Path

# Set up environment for testing
os.environ["CODE_EVOLVER_PROFILE"] = "1"

from src.profiling import (
    Profiler,
    ProfileContext,
    profile_function,
    ProfileRegistry,
    get_global_registry,
    PYINSTRUMENT_AVAILABLE
)


class TestProfiler(unittest.TestCase):
    """Test the Profiler class."""

    def test_profiler_basic_timing(self):
        """Test basic profiler timing functionality."""
        profiler = Profiler(name="test_operation")
        profiler.start()

        # Simulate some work
        time.sleep(0.1)

        profile_data = profiler.stop(save=False)

        # Check that timing is reasonable (100ms +/- 50ms tolerance)
        self.assertIsNotNone(profile_data)
        self.assertGreater(profile_data.duration_ms, 50)
        self.assertLess(profile_data.duration_ms, 200)
        self.assertEqual(profile_data.name, "test_operation")

    def test_profiler_with_metadata(self):
        """Test profiler with custom metadata."""
        metadata = {
            "version": "1.0",
            "tool": "test_tool",
            "model": "test_model"
        }

        profiler = Profiler(name="test_with_metadata", metadata=metadata)
        profiler.start()
        time.sleep(0.05)
        profile_data = profiler.stop(save=False)

        self.assertEqual(profile_data.metadata["version"], "1.0")
        self.assertEqual(profile_data.metadata["tool"], "test_tool")
        self.assertEqual(profile_data.metadata["model"], "test_model")

    def test_profiler_disabled(self):
        """Test profiler when disabled."""
        # Temporarily disable profiling
        original_enabled = os.environ.get("CODE_EVOLVER_PROFILE")
        os.environ["CODE_EVOLVER_PROFILE"] = "0"

        profiler = Profiler(name="test_disabled")
        profiler.start()
        time.sleep(0.05)
        profile_data = profiler.stop(save=False)

        # Restore original setting
        if original_enabled:
            os.environ["CODE_EVOLVER_PROFILE"] = original_enabled
        else:
            del os.environ["CODE_EVOLVER_PROFILE"]

        # Should return None when disabled
        self.assertIsNone(profile_data)

    @unittest.skipIf(not PYINSTRUMENT_AVAILABLE, "PyInstrument not installed")
    def test_profiler_with_pyinstrument(self):
        """Test profiler with PyInstrument installed."""
        profiler = Profiler(name="test_pyinstrument")
        profiler.start()

        # Do some actual work to profile
        result = sum(i ** 2 for i in range(10000))

        profile_data = profiler.stop(save=False)

        self.assertIsNotNone(profile_data)
        # PyInstrument should generate text output
        if PYINSTRUMENT_AVAILABLE:
            self.assertIsNotNone(profile_data.profile_text)
            # Profile text should contain something (the actual content varies)
            self.assertGreater(len(profile_data.profile_text), 0)


class TestProfileContext(unittest.TestCase):
    """Test the ProfileContext context manager."""

    def test_profile_context_basic(self):
        """Test basic context manager usage."""
        with ProfileContext("test_context", save=False) as profile_data:
            time.sleep(0.05)

        # Note: profile_data is set after the context exits, so we can't check it here
        # But we can verify no exceptions were raised

    def test_profile_context_with_exception(self):
        """Test context manager with exception handling."""
        try:
            with ProfileContext("test_exception", save=False):
                time.sleep(0.02)
                raise ValueError("Test exception")
        except ValueError:
            pass  # Expected

        # Profile should still be saved despite exception


class TestProfileFunction(unittest.TestCase):
    """Test the profile_function decorator."""

    def test_profile_function_decorator(self):
        """Test function profiling with decorator."""

        @profile_function(name="decorated_function", save=False)
        def slow_function(n):
            time.sleep(0.05)
            return sum(i for i in range(n))

        result = slow_function(100)
        self.assertEqual(result, sum(i for i in range(100)))

    def test_profile_function_with_metadata(self):
        """Test decorator with metadata."""
        metadata = {"version": "2.0", "category": "test"}

        @profile_function(name="decorated_with_metadata", metadata=metadata, save=False)
        def another_function():
            return "result"

        result = another_function()
        self.assertEqual(result, "result")


class TestProfileRegistry(unittest.TestCase):
    """Test the ProfileRegistry for collecting and comparing profiles."""

    def setUp(self):
        """Set up a fresh registry for each test."""
        self.registry = ProfileRegistry()

    def test_add_profile(self):
        """Test adding profiles to registry."""
        profiler = Profiler(name="test_op", metadata={"version": "1.0"})
        profiler.start()
        time.sleep(0.02)
        profile_data = profiler.stop(save=False)

        self.registry.add_profile(profile_data)

        profiles = self.registry.get_profiles("test_op")
        self.assertEqual(len(profiles), 1)
        self.assertEqual(profiles[0].name, "test_op")

    def test_compare_profiles(self):
        """Test comparing profiles between versions."""
        # Create v1 profile (slower)
        profiler_v1 = Profiler(name="operation", metadata={"version": "1.0"})
        profiler_v1.start()
        time.sleep(0.1)
        profile_v1 = profiler_v1.stop(save=False)
        self.registry.add_profile(profile_v1)

        # Create v2 profile (faster)
        profiler_v2 = Profiler(name="operation", metadata={"version": "2.0"})
        profiler_v2.start()
        time.sleep(0.05)
        profile_v2 = profiler_v2.stop(save=False)
        self.registry.add_profile(profile_v2)

        # Compare versions
        comparison = self.registry.compare_profiles("operation", "1.0", "2.0")

        self.assertIsNotNone(comparison)
        self.assertEqual(comparison["name"], "operation")
        self.assertGreater(comparison["improvement_pct"], 0)  # v2 should be faster
        self.assertEqual(comparison["recommendation"], "upgrade")

    def test_export_summary(self):
        """Test exporting summary of all profiles."""
        # Add multiple profiles
        for i in range(3):
            profiler = Profiler(name=f"op_{i % 2}", metadata={"run": i})
            profiler.start()
            time.sleep(0.02)
            profile_data = profiler.stop(save=False)
            self.registry.add_profile(profile_data)

        summary = self.registry.export_summary()

        self.assertEqual(summary["total_profiles"], 3)
        self.assertIn("op_0", summary["operations"])
        self.assertIn("op_1", summary["operations"])

        # Test with file output
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = Path(f.name)

        try:
            self.registry.export_summary(temp_path)
            self.assertTrue(temp_path.exists())
        finally:
            if temp_path.exists():
                temp_path.unlink()

    def test_clear_registry(self):
        """Test clearing the registry."""
        profiler = Profiler(name="test")
        profiler.start()
        time.sleep(0.01)
        profile_data = profiler.stop(save=False)
        self.registry.add_profile(profile_data)

        self.assertEqual(len(self.registry.profiles), 1)

        self.registry.clear()

        self.assertEqual(len(self.registry.profiles), 0)
        self.assertEqual(len(self.registry.profiles_by_name), 0)


class TestGlobalRegistry(unittest.TestCase):
    """Test the global registry instance."""

    def test_global_registry_singleton(self):
        """Test that global registry is a singleton."""
        registry1 = get_global_registry()
        registry2 = get_global_registry()

        self.assertIs(registry1, registry2)

    def test_global_registry_persistence(self):
        """Test that global registry persists across calls."""
        registry = get_global_registry()
        initial_count = len(registry.profiles)

        profiler = Profiler(name="global_test")
        profiler.start()
        time.sleep(0.01)
        profile_data = profiler.stop(save=False)
        registry.add_profile(profile_data)

        # Get registry again
        registry2 = get_global_registry()
        self.assertEqual(len(registry2.profiles), initial_count + 1)

        # Clean up
        registry.clear()


class TestProfileDataStorage(unittest.TestCase):
    """Test profile data storage and retrieval."""

    def setUp(self):
        """Set up temporary directory for test profiles."""
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        """Clean up temporary directory."""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_save_profile_data(self):
        """Test saving profile data to disk."""
        profiler = Profiler(name="save_test", metadata={"test": "data"})
        profiler.start()
        time.sleep(0.02)
        profile_data = profiler.stop(save=False)

        # Save to temp directory
        saved_path = profile_data.save(output_dir=self.temp_dir)

        self.assertTrue(saved_path.exists())
        self.assertTrue((saved_path / "metadata.json").exists())

    def test_profile_data_to_dict(self):
        """Test converting profile data to dictionary."""
        profiler = Profiler(name="dict_test", metadata={"version": "1.0"})
        profiler.start()
        time.sleep(0.01)
        profile_data = profiler.stop(save=False)

        data_dict = profile_data.to_dict()

        self.assertEqual(data_dict["name"], "dict_test")
        self.assertIn("duration_ms", data_dict)
        self.assertIn("timestamp", data_dict)
        self.assertEqual(data_dict["metadata"]["version"], "1.0")


if __name__ == "__main__":
    unittest.main()
