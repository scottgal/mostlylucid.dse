#!/usr/bin/env python3
"""
Unit tests for platform_info.py tool.
Tests platform information gathering functionality.
"""

import json
import sys
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
from io import StringIO

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.executable.platform_info import PlatformInfoGatherer, main


class TestPlatformInfoGatherer(unittest.TestCase):
    """Test cases for PlatformInfoGatherer class."""

    def setUp(self):
        """Set up test fixtures."""
        self.gatherer = PlatformInfoGatherer()

    def test_get_basic_info(self):
        """Test basic platform information gathering."""
        info = self.gatherer.get_basic_info()

        # Check that all expected keys are present
        expected_keys = [
            "platform", "platform_release", "platform_version",
            "architecture", "hostname", "processor", "python_version"
        ]

        for key in expected_keys:
            self.assertIn(key, info)
            self.assertIsNotNone(info[key])

    def test_get_cpu_info_without_psutil(self):
        """Test CPU info gathering without psutil."""
        with patch('builtins.__import__', side_effect=ImportError):
            cpu_info = self.gatherer.get_cpu_info(detailed=False)

            # Should fall back to basic info
            self.assertIn("cores", cpu_info)
            self.assertIn("note", cpu_info)

    @patch('psutil.cpu_count')
    @patch('psutil.cpu_percent')
    def test_get_cpu_info_with_psutil_basic(self, mock_cpu_percent, mock_cpu_count):
        """Test basic CPU info gathering with psutil."""
        mock_cpu_count.side_effect = lambda logical: 4 if logical else 2
        mock_cpu_percent.return_value = 45.2

        cpu_info = self.gatherer.get_cpu_info(detailed=False)

        self.assertEqual(cpu_info.get("physical_cores"), 2)
        self.assertEqual(cpu_info.get("logical_cores"), 4)
        self.assertEqual(cpu_info.get("usage_percent"), 45.2)

    @patch('psutil.cpu_count')
    @patch('psutil.cpu_percent')
    @patch('psutil.cpu_freq')
    @patch('psutil.cpu_stats')
    def test_get_cpu_info_with_psutil_detailed(
        self, mock_cpu_stats, mock_cpu_freq, mock_cpu_percent, mock_cpu_count
    ):
        """Test detailed CPU info gathering with psutil."""
        mock_cpu_count.side_effect = lambda logical: 4 if logical else 2
        mock_cpu_percent.side_effect = [
            [10.0, 20.0, 30.0, 40.0],  # Per-core usage
            25.0  # Total usage
        ]

        # Mock CPU frequency
        freq_mock = MagicMock()
        freq_mock.current = 2400.5
        freq_mock.min = 800.0
        freq_mock.max = 3200.0
        mock_cpu_freq.return_value = freq_mock

        # Mock CPU stats
        stats_mock = MagicMock()
        stats_mock.ctx_switches = 12345
        stats_mock.interrupts = 67890
        stats_mock.soft_interrupts = 11111
        stats_mock.syscalls = 22222
        mock_cpu_stats.return_value = stats_mock

        cpu_info = self.gatherer.get_cpu_info(detailed=True)

        self.assertEqual(cpu_info.get("physical_cores"), 2)
        self.assertEqual(cpu_info.get("logical_cores"), 4)
        self.assertIn("frequency_mhz", cpu_info)
        self.assertIn("usage_per_core", cpu_info)
        self.assertIn("stats", cpu_info)

    @patch('psutil.virtual_memory')
    def test_get_memory_info_basic(self, mock_virtual_memory):
        """Test basic memory info gathering."""
        mem_mock = MagicMock()
        mem_mock.total = 16 * 1024 * 1024 * 1024  # 16 GB
        mem_mock.available = 8 * 1024 * 1024 * 1024  # 8 GB
        mem_mock.percent = 50.0
        mem_mock.used = 8 * 1024 * 1024 * 1024
        mem_mock.free = 8 * 1024 * 1024 * 1024
        mock_virtual_memory.return_value = mem_mock

        mem_info = self.gatherer.get_memory_info(detailed=False)

        self.assertIn("total_bytes", mem_info)
        self.assertIn("available_bytes", mem_info)
        self.assertIn("percent_used", mem_info)

    def test_gather_info_basic_level(self):
        """Test gathering basic level information."""
        result = self.gatherer.gather_info(
            detail_level="basic",
            include_processes=False,
            include_network=False
        )

        self.assertIn("platform", result)
        self.assertIn("timestamp", result)
        self.assertIn("detail_level", result)
        self.assertEqual(result["detail_level"], "basic")

    def test_gather_info_standard_level(self):
        """Test gathering standard level information."""
        result = self.gatherer.gather_info(
            detail_level="standard",
            include_processes=False,
            include_network=False
        )

        self.assertIn("platform", result)
        self.assertIn("cpu", result)
        self.assertIn("memory", result)
        self.assertEqual(result["detail_level"], "standard")


class TestPlatformInfoMain(unittest.TestCase):
    """Test cases for main function."""

    @patch('sys.stdin', new_callable=StringIO)
    @patch('sys.stdout', new_callable=StringIO)
    def test_main_basic_input(self, mock_stdout, mock_stdin):
        """Test main function with basic input."""
        input_data = json.dumps({"detail_level": "basic"})
        mock_stdin.return_value = input_data

        try:
            with patch('sys.stdin.read', return_value=input_data):
                main()

            output = mock_stdout.getvalue()
            result = json.loads(output)

            self.assertTrue(result.get("success"))
            self.assertIn("platform_info", result)
        except SystemExit:
            pass

    @patch('sys.stdin', new_callable=StringIO)
    @patch('sys.stdout', new_callable=StringIO)
    def test_main_standard_input(self, mock_stdout, mock_stdin):
        """Test main function with standard input."""
        input_data = json.dumps({"detail_level": "standard"})
        mock_stdin.return_value = input_data

        try:
            with patch('sys.stdin.read', return_value=input_data):
                main()

            output = mock_stdout.getvalue()
            result = json.loads(output)

            self.assertTrue(result.get("success"))
            self.assertIn("platform_info", result)
        except SystemExit:
            pass

    @patch('sys.stdin', new_callable=StringIO)
    def test_main_invalid_json(self, mock_stdin):
        """Test main function with invalid JSON input."""
        mock_stdin.return_value = "invalid json"

        with patch('sys.stdin.read', return_value="invalid json"):
            with self.assertRaises(SystemExit):
                main()


class TestPlatformInfoEdgeCases(unittest.TestCase):
    """Test edge cases and error handling."""

    def setUp(self):
        """Set up test fixtures."""
        self.gatherer = PlatformInfoGatherer()

    def test_invalid_detail_level(self):
        """Test with invalid detail level."""
        result = self.gatherer.gather_info(
            detail_level="invalid",
            include_processes=False,
            include_network=False
        )

        # Should default to standard
        self.assertIn("platform", result)
        self.assertIn("cpu", result)

    def test_gather_info_all_options(self):
        """Test gathering info with all options enabled."""
        result = self.gatherer.gather_info(
            detail_level="full",
            include_processes=True,
            include_network=True
        )

        self.assertIn("platform", result)
        self.assertIn("timestamp", result)


if __name__ == "__main__":
    unittest.main()
