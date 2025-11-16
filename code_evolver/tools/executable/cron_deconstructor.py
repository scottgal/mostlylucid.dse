#!/usr/bin/env python3
"""
Cron Expression Deconstructor.

Analyzes cron expressions and creates structured metadata for semantic embedding.
This enables better RAG-based searching and grouping of scheduled tasks.
"""
import json
import logging
import os
import sys
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

try:
    from croniter import croniter
except ImportError:
    croniter = None

logger = logging.getLogger(__name__)


class CronDeconstructor:
    """
    Deconstructs cron expressions into structured metadata.

    Converts cron expressions into rich semantic descriptions that can be
    embedded in RAG for better searching and grouping.
    """

    def __init__(self, llm_client=None, model: str = "llama3.2"):
        """
        Initialize cron deconstructor.

        Args:
            llm_client: LLM client for generating descriptions
            model: Model to use (medium-sized for efficiency)
        """
        self.llm_client = llm_client
        self.model = model

    def deconstruct(
        self,
        cron_expression: str,
        tool_name: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Deconstruct a cron expression into structured metadata.

        Args:
            cron_expression: Cron expression to deconstruct
            tool_name: Name of the tool/function to execute
            description: Optional human description
            metadata: Additional metadata

        Returns:
            Structured cron metadata dictionary

        Example output:
        {
            "cron": "0 9 * * MON",
            "description": "Run bugcatcher logs every Monday at 9am",
            "tool": "bugcatcher_logs",
            "group": "weekly_reports",
            "pattern": {
                "minute": "0",
                "hour": "9",
                "day_of_month": "*",
                "month": "*",
                "day_of_week": "MON"
            },
            "frequency": "weekly",
            "time_of_day": "morning",
            "day_names": ["Monday"],
            "next_runs": ["2025-01-20T09:00:00", "2025-01-27T09:00:00"],
            "semantic_tags": ["weekly", "morning", "monday", "reports"]
        }
        """
        metadata = metadata or {}

        # Validate cron expression
        if not croniter:
            raise ImportError("croniter library required")

        try:
            cron = croniter(cron_expression)
        except Exception as e:
            raise ValueError(f"Invalid cron expression '{cron_expression}': {e}")

        # Parse cron fields
        pattern = self._parse_cron_fields(cron_expression)

        # Determine frequency
        frequency = self._determine_frequency(pattern)

        # Determine time of day
        time_of_day = self._determine_time_of_day(pattern)

        # Get day names if specified
        day_names = self._get_day_names(pattern)

        # Get next run times
        next_runs = self._get_next_runs(cron_expression, count=3)

        # Generate human description if not provided
        if not description and self.llm_client:
            description = self._generate_description(
                cron_expression,
                pattern,
                frequency,
                time_of_day,
                day_names,
                tool_name
            )
        elif not description:
            description = self._simple_description(
                pattern,
                frequency,
                time_of_day,
                day_names
            )

        # Infer group from tool name and description
        group = self._infer_group(tool_name, description, metadata)

        # Generate semantic tags
        semantic_tags = self._generate_semantic_tags(
            pattern,
            frequency,
            time_of_day,
            day_names,
            group,
            tool_name,
            description
        )

        # Build structured output
        result = {
            "cron": cron_expression,
            "description": description,
            "tool": tool_name or "unknown",
            "group": group,
            "pattern": pattern,
            "frequency": frequency,
            "time_of_day": time_of_day,
            "day_names": day_names,
            "next_runs": next_runs,
            "semantic_tags": semantic_tags
        }

        return result

    def _parse_cron_fields(self, cron_expression: str) -> Dict[str, str]:
        """Parse cron expression into fields."""
        fields = cron_expression.split()

        if len(fields) != 5:
            raise ValueError(f"Cron must have 5 fields, got {len(fields)}")

        return {
            "minute": fields[0],
            "hour": fields[1],
            "day_of_month": fields[2],
            "month": fields[3],
            "day_of_week": fields[4]
        }

    def _determine_frequency(self, pattern: Dict[str, str]) -> str:
        """Determine execution frequency from pattern."""
        minute = pattern["minute"]
        hour = pattern["hour"]
        day_of_month = pattern["day_of_month"]
        month = pattern["month"]
        day_of_week = pattern["day_of_week"]

        # Every minute
        if all(f == "*" for f in [minute, hour, day_of_month, month, day_of_week]):
            return "every_minute"

        # Hourly
        if hour == "*" and day_of_month == "*" and month == "*" and day_of_week == "*":
            if "/" in minute:
                return f"every_{minute.split('/')[1]}_minutes"
            elif minute == "*":
                return "every_minute"
            else:
                return "hourly"

        # Daily
        if day_of_month == "*" and month == "*" and day_of_week == "*":
            return "daily"

        # Weekly (specific day of week)
        if day_of_week != "*" and day_of_month == "*" and month == "*":
            return "weekly"

        # Monthly
        if day_of_month != "*" and month == "*":
            return "monthly"

        # Yearly
        if month != "*":
            return "yearly"

        return "custom"

    def _determine_time_of_day(self, pattern: Dict[str, str]) -> Optional[str]:
        """Determine time of day from hour."""
        hour = pattern["hour"]

        if hour == "*":
            return None

        try:
            hour_int = int(hour)

            if 0 <= hour_int < 6:
                return "night"
            elif 6 <= hour_int < 12:
                return "morning"
            elif 12 <= hour_int < 18:
                return "afternoon"
            else:
                return "evening"
        except ValueError:
            return None

    def _get_day_names(self, pattern: Dict[str, str]) -> List[str]:
        """Get day names if specified."""
        day_of_week = pattern["day_of_week"]

        if day_of_week == "*":
            return []

        day_map = {
            "0": "Sunday", "SUN": "Sunday",
            "1": "Monday", "MON": "Monday",
            "2": "Tuesday", "TUE": "Tuesday",
            "3": "Wednesday", "WED": "Wednesday",
            "4": "Thursday", "THU": "Thursday",
            "5": "Friday", "FRI": "Friday",
            "6": "Saturday", "SAT": "Saturday"
        }

        days = []
        for part in day_of_week.split(","):
            day = day_map.get(part.strip().upper())
            if day:
                days.append(day)

        return days

    def _get_next_runs(self, cron_expression: str, count: int = 3) -> List[str]:
        """Get next N run times."""
        cron = croniter(cron_expression, datetime.now())
        next_runs = []

        for _ in range(count):
            next_run = cron.get_next(datetime)
            next_runs.append(next_run.isoformat())

        return next_runs

    def _generate_description(
        self,
        cron_expression: str,
        pattern: Dict[str, str],
        frequency: str,
        time_of_day: Optional[str],
        day_names: List[str],
        tool_name: Optional[str]
    ) -> str:
        """Generate human description using LLM."""
        prompt = f"""Generate a concise, natural language description of this cron schedule.

Cron: {cron_expression}
Frequency: {frequency}
Time of day: {time_of_day or 'any'}
Days: {', '.join(day_names) if day_names else 'any'}
Tool: {tool_name or 'unknown'}

Respond with ONLY a single sentence description starting with "Run" or "Execute".
Keep it under 60 characters if possible.

Examples:
- "0 9 * * MON" -> "Run every Monday at 9am"
- "*/5 * * * *" -> "Run every 5 minutes"
- "0 2 * * *" -> "Run daily at 2am"
- "0 12 * * SUN" -> "Run every Sunday at noon"

Now describe: {cron_expression}
"""

        try:
            response = self.llm_client.generate(
                model=self.model,
                prompt=prompt,
                options={'temperature': 0.1}
            )

            description = response.get('response', '').strip()

            # Clean up the response
            if description.startswith('"') and description.endswith('"'):
                description = description[1:-1]

            # Ensure it starts with Run/Execute
            if not (description.startswith('Run') or description.startswith('Execute')):
                description = f"Run {description.lower()}"

            return description

        except Exception as e:
            logger.warning(f"Failed to generate description: {e}")
            return self._simple_description(pattern, frequency, time_of_day, day_names)

    def _simple_description(
        self,
        pattern: Dict[str, str],
        frequency: str,
        time_of_day: Optional[str],
        day_names: List[str]
    ) -> str:
        """Generate simple description without LLM."""
        parts = ["Run"]

        # Frequency
        if frequency == "every_minute":
            parts.append("every minute")
        elif frequency.startswith("every_") and "_minutes" in frequency:
            minutes = frequency.replace("every_", "").replace("_minutes", "")
            parts.append(f"every {minutes} minutes")
        elif frequency == "hourly":
            parts.append("hourly")
        elif frequency == "daily":
            parts.append("daily")
        elif frequency == "weekly":
            if day_names:
                parts.append(f"every {', '.join(day_names)}")
            else:
                parts.append("weekly")
        elif frequency == "monthly":
            parts.append("monthly")
        elif frequency == "yearly":
            parts.append("yearly")

        # Time of day
        if time_of_day and pattern["hour"] != "*":
            hour = pattern["hour"]
            minute = pattern["minute"]
            if minute == "0":
                parts.append(f"at {hour}:00")
            else:
                parts.append(f"at {hour}:{minute}")

        return " ".join(parts)

    def _infer_group(
        self,
        tool_name: Optional[str],
        description: Optional[str],
        metadata: Dict[str, Any]
    ) -> str:
        """Infer group/category from context."""
        # Check explicit group in metadata
        if "group" in metadata:
            return metadata["group"]

        # Infer from tool name
        if tool_name:
            tool_lower = tool_name.lower()

            if any(word in tool_lower for word in ["report", "analytics", "summary"]):
                return "reports"
            elif any(word in tool_lower for word in ["backup", "archive", "snapshot"]):
                return "backups"
            elif any(word in tool_lower for word in ["clean", "purge", "delete", "remove"]):
                return "maintenance"
            elif any(word in tool_lower for word in ["poll", "check", "monitor", "watch"]):
                return "monitoring"
            elif any(word in tool_lower for word in ["sync", "update", "refresh"]):
                return "synchronization"
            elif any(word in tool_lower for word in ["email", "notify", "alert"]):
                return "notifications"

        # Infer from description
        if description:
            desc_lower = description.lower()

            if any(word in desc_lower for word in ["report", "analytics"]):
                return "reports"
            elif any(word in desc_lower for word in ["backup", "archive"]):
                return "backups"
            elif any(word in desc_lower for word in ["clean", "delete"]):
                return "maintenance"
            elif any(word in desc_lower for word in ["poll", "check", "monitor"]):
                return "monitoring"

        return "general"

    def _generate_semantic_tags(
        self,
        pattern: Dict[str, str],
        frequency: str,
        time_of_day: Optional[str],
        day_names: List[str],
        group: str,
        tool_name: Optional[str],
        description: Optional[str]
    ) -> List[str]:
        """Generate semantic tags for embedding."""
        tags = []

        # Frequency tags
        tags.append(frequency)

        # Time of day
        if time_of_day:
            tags.append(time_of_day)

        # Day names
        tags.extend([day.lower() for day in day_names])

        # Group
        tags.append(group)

        # Tool-based tags
        if tool_name:
            tags.append(tool_name.lower().replace("_", " "))

        # Description-based tags
        if description:
            # Extract key words
            keywords = ["report", "backup", "clean", "monitor", "sync", "notify"]
            desc_lower = description.lower()
            tags.extend([kw for kw in keywords if kw in desc_lower])

        # Deduplicate and sort
        tags = sorted(list(set(tags)))

        return tags


def deconstruct_cron(
    cron_expression: str,
    tool_name: Optional[str] = None,
    description: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    llm_client=None
) -> Dict[str, Any]:
    """
    Deconstruct a cron expression into structured metadata.

    Args:
        cron_expression: Cron expression to deconstruct
        tool_name: Name of the tool/function
        description: Optional description
        metadata: Additional metadata
        llm_client: Optional LLM client for description generation

    Returns:
        Structured cron metadata
    """
    deconstructor = CronDeconstructor(llm_client=llm_client)
    return deconstructor.deconstruct(
        cron_expression,
        tool_name=tool_name,
        description=description,
        metadata=metadata
    )


def main():
    """
    Main entry point for cron deconstructor tool.

    Reads JSON input from stdin with:
    {
        "cron": "0 9 * * MON",
        "tool_name": "bugcatcher_logs",
        "description": "Generate bugcatcher report",
        "metadata": {"category": "reports"}
    }

    Returns structured cron metadata.
    """
    # Read input
    try:
        input_data = json.loads(sys.stdin.read())
    except Exception as e:
        print(json.dumps({
            'status': 'error',
            'message': f'Invalid JSON input: {str(e)}'
        }))
        sys.exit(1)

    # Extract parameters
    cron_expression = input_data.get('cron')
    if not cron_expression:
        print(json.dumps({
            'status': 'error',
            'message': 'Missing required parameter: cron'
        }))
        sys.exit(1)

    tool_name = input_data.get('tool_name')
    description = input_data.get('description')
    metadata = input_data.get('metadata', {})

    # Get LLM client if available
    llm_client = None
    try:
        from src import OllamaClient, ConfigManager
        config = ConfigManager()
        llm_client = OllamaClient(config_manager=config)
    except Exception:
        pass  # Will use simple description

    # Deconstruct cron
    try:
        result = deconstruct_cron(
            cron_expression,
            tool_name=tool_name,
            description=description,
            metadata=metadata,
            llm_client=llm_client
        )

        result['status'] = 'success'
        print(json.dumps(result, indent=2))

    except Exception as e:
        logger.exception(f"Failed to deconstruct cron: {e}")
        print(json.dumps({
            'status': 'error',
            'message': f'Failed to deconstruct cron: {str(e)}'
        }))
        sys.exit(1)


if __name__ == '__main__':
    main()
