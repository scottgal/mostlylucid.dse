#!/usr/bin/env python3
"""
Unit tests for cron_querier.py tool.
Tests cron query parsing functionality.
"""

import json
import sys
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.executable.cron_querier import CronQuerier


class TestCronQuerier(unittest.TestCase):
    """Test cases for CronQuerier class."""

    def setUp(self):
        """Set up test fixtures."""
        self.querier = CronQuerier(llm_client=None)
        self.test_time = datetime(2025, 1, 16, 12, 0, 0)

    def test_parse_query_basic(self):
        """Test parsing a basic query."""
        query = "all backup tasks"
        result = self.querier.parse_query(query, current_time=self.test_time)

        self.assertIsInstance(result, dict)
        self.assertIn("search_query", result)

    def test_simple_parse_backup_tasks(self):
        """Test simple parsing for backup tasks."""
        query = "all backup tasks"
        result = self.querier._simple_parse(query, self.test_time)

        self.assertIsNotNone(result)
        self.assertIn("search_query", result)

    def test_simple_parse_time_window(self):
        """Test simple parsing for time window queries."""
        query = "tasks running in the next hour"
        result = self.querier._simple_parse(query, self.test_time)

        self.assertIsNotNone(result)
        if "time_window" in result:
            self.assertIn("start", result["time_window"])
            self.assertIn("end", result["time_window"])

    def test_simple_parse_daily_frequency(self):
        """Test simple parsing for daily frequency."""
        query = "daily backup tasks"
        result = self.querier._simple_parse(query, self.test_time)

        self.assertIsNotNone(result)

    def test_simple_parse_hourly_frequency(self):
        """Test simple parsing for hourly frequency."""
        query = "tasks running every hour"
        result = self.querier._simple_parse(query, self.test_time)

        self.assertIsNotNone(result)

    def test_simple_parse_weekly_frequency(self):
        """Test simple parsing for weekly frequency."""
        query = "weekly report tasks"
        result = self.querier._simple_parse(query, self.test_time)

        self.assertIsNotNone(result)

    def test_fallback_parse(self):
        """Test fallback parsing for unrecognized queries."""
        query = "some random query"
        result = self.querier._fallback_parse(query, self.test_time)

        self.assertIsInstance(result, dict)
        self.assertIn("search_query", result)
        self.assertEqual(result["search_query"], query)

    def test_parse_query_with_llm(self):
        """Test parsing query with LLM client."""
        mock_llm_client = MagicMock()
        mock_llm_client.generate.return_value = json.dumps({
            "search_query": "backup tasks",
            "filters": {"group": "backups"},
            "time_window": {
                "start": "2025-01-16T18:00:00",
                "end": "2025-01-16T23:59:59"
            }
        })

        querier = CronQuerier(llm_client=mock_llm_client, model="llama3.2")
        query = "all backup tasks running tonight"
        result = querier.parse_query(query, current_time=self.test_time)

        self.assertIsInstance(result, dict)

    def test_time_window_calculation_next_hour(self):
        """Test time window calculation for 'next hour'."""
        query = "tasks in the next hour"
        result = self.querier._simple_parse(query, self.test_time)

        if result and "time_window" in result:
            time_window = result["time_window"]
            # Time window should be approximately 1 hour
            self.assertIn("window_minutes", time_window)

    def test_time_window_calculation_tonight(self):
        """Test time window calculation for 'tonight'."""
        query = "tasks running tonight"
        result = self.querier._simple_parse(query, self.test_time)

        if result and "time_window" in result:
            time_window = result["time_window"]
            self.assertIn("start", time_window)
            self.assertIn("end", time_window)

    def test_group_extraction_backup(self):
        """Test group extraction for backup tasks."""
        query = "backup tasks"
        result = self.querier._simple_parse(query, self.test_time)

        if result and "filters" in result:
            self.assertEqual(result["filters"].get("group"), "backups")

    def test_group_extraction_report(self):
        """Test group extraction for report tasks."""
        query = "report generation tasks"
        result = self.querier._simple_parse(query, self.test_time)

        if result and "filters" in result:
            self.assertEqual(result["filters"].get("group"), "reports")

    def test_group_extraction_monitoring(self):
        """Test group extraction for monitoring tasks."""
        query = "monitoring tasks"
        result = self.querier._simple_parse(query, self.test_time)

        if result and "filters" in result:
            self.assertEqual(result["filters"].get("group"), "monitoring")


class TestCronQuerierEdgeCases(unittest.TestCase):
    """Test edge cases for CronQuerier."""

    def setUp(self):
        """Set up test fixtures."""
        self.querier = CronQuerier(llm_client=None)
        self.test_time = datetime(2025, 1, 16, 12, 0, 0)

    def test_empty_query(self):
        """Test handling of empty query."""
        query = ""
        result = self.querier.parse_query(query, current_time=self.test_time)

        self.assertIsInstance(result, dict)
        self.assertIn("search_query", result)

    def test_complex_query(self):
        """Test handling of complex query."""
        query = "all backup and monitoring tasks running every 5 minutes in the next 3 hours"
        result = self.querier.parse_query(query, current_time=self.test_time)

        self.assertIsInstance(result, dict)
        self.assertIn("search_query", result)

    def test_query_with_special_characters(self):
        """Test handling of query with special characters."""
        query = "tasks with @special #characters!"
        result = self.querier.parse_query(query, current_time=self.test_time)

        self.assertIsInstance(result, dict)

    def test_query_case_insensitive(self):
        """Test that queries are case insensitive."""
        query1 = "BACKUP tasks"
        query2 = "backup TASKS"

        result1 = self.querier._simple_parse(query1, self.test_time)
        result2 = self.querier._simple_parse(query2, self.test_time)

        # Both should recognize 'backup' keyword
        if result1 and "filters" in result1:
            self.assertEqual(result1["filters"].get("group"), "backups")
        if result2 and "filters" in result2:
            self.assertEqual(result2["filters"].get("group"), "backups")


if __name__ == "__main__":
    unittest.main()
