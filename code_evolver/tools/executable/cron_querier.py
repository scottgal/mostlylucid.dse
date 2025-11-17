#!/usr/bin/env python3
"""
Cron Query Parser.

Converts natural language queries about scheduled tasks into structured
filters for RAG-based semantic search.

Examples:
- "all tasks which will run in the next three hours"
- "backup jobs running tonight"
- "weekly reports on monday morning"
- "monitoring tasks that run every 5 minutes"
"""
import json
import logging
import sys
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple

logger = logging.getLogger(__name__)


class CronQuerier:
    """
    Converts natural language queries into structured task search filters.

    Uses LLM to parse complex queries and map them to the structured
    cron metadata format used in RAG embeddings.
    """

    def __init__(self, llm_client=None, model: str = "llama3.2"):
        """
        Initialize cron querier.

        Args:
            llm_client: LLM client for query parsing
            model: Model to use (medium-sized for efficiency)
        """
        self.llm_client = llm_client
        self.model = model

    def parse_query(
        self,
        query: str,
        current_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Parse natural language query into structured search filters.

        Args:
            query: Natural language query
            current_time: Reference time (defaults to now)

        Returns:
            Structured query filters

        Example:
            Input: "all backup tasks running tonight"
            Output: {
                "search_query": "backup tasks",
                "filters": {
                    "group": "backups",
                    "time_of_day": "evening"
                },
                "time_window": {
                    "start": "2025-01-16T18:00:00",
                    "end": "2025-01-16T23:59:59",
                    "window_minutes": 360
                }
            }
        """
        current_time = current_time or datetime.now()

        # Try simple pattern matching first (fast path)
        simple_result = self._simple_parse(query, current_time)
        if simple_result and not self.llm_client:
            return simple_result

        # Use LLM for complex queries
        if self.llm_client:
            llm_result = self._llm_parse(query, current_time)
            if llm_result:
                return llm_result

        # Fallback to simple parse
        return simple_result or self._fallback_parse(query, current_time)

    def _simple_parse(
        self,
        query: str,
        current_time: datetime
    ) -> Optional[Dict[str, Any]]:
        """Fast pattern matching for common queries."""
        query_lower = query.lower()

        # Extract group keywords
        group = None
        group_keywords = {
            'backup': 'backups',
            'report': 'reports',
            'monitoring': 'monitoring',
            'monitor': 'monitoring',
            'poll': 'monitoring',
            'clean': 'maintenance',
            'maintenance': 'maintenance',
            'sync': 'synchronization',
            'notification': 'notifications',
            'notify': 'notifications',
            'alert': 'notifications'
        }

        for keyword, grp in group_keywords.items():
            if keyword in query_lower:
                group = grp
                break

        # Extract frequency keywords
        frequency = None
        freq_keywords = {
            'every minute': 'every_minute',
            'every 5 minutes': 'every_5_minutes',
            'every 10 minutes': 'every_10_minutes',
            'every 15 minutes': 'every_15_minutes',
            'every 30 minutes': 'every_30_minutes',
            'hourly': 'hourly',
            'daily': 'daily',
            'weekly': 'weekly',
            'monthly': 'monthly'
        }

        for keyword, freq in freq_keywords.items():
            if keyword in query_lower:
                frequency = freq
                break

        # Extract time of day
        time_of_day = None
        time_keywords = {
            'morning': 'morning',
            'afternoon': 'afternoon',
            'evening': 'evening',
            'night': 'night',
            'tonight': 'evening'
        }

        for keyword, tod in time_keywords.items():
            if keyword in query_lower:
                time_of_day = tod
                break

        # Extract day names
        day_names = []
        days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        for day in days:
            if day in query_lower:
                day_names.append(day.capitalize())

        # Extract time windows
        time_window = self._parse_time_window(query_lower, current_time)

        # Build filters
        filters = {}
        if group:
            filters['group'] = group
        if frequency:
            filters['frequency'] = frequency
        if time_of_day:
            filters['time_of_day'] = time_of_day

        # Build search query (extract meaningful words)
        search_words = []
        if group:
            search_words.append(group)
        if frequency:
            search_words.append(frequency.replace('_', ' '))
        if time_of_day:
            search_words.append(time_of_day)
        for day in day_names:
            search_words.append(day)

        search_query = ' '.join(search_words) if search_words else query

        result = {
            'search_query': search_query,
            'filters': filters,
            'time_window': time_window,
            'day_names': day_names,
            'parsed_method': 'simple'
        }

        return result

    def _parse_time_window(
        self,
        query_lower: str,
        current_time: datetime
    ) -> Optional[Dict[str, Any]]:
        """Parse time window from query."""
        # "next N hours/minutes"
        if 'next' in query_lower:
            if 'hour' in query_lower:
                # Extract number
                import re
                match = re.search(r'next (\d+) hour', query_lower)
                if match:
                    hours = int(match.group(1))
                    end_time = current_time + timedelta(hours=hours)
                    return {
                        'start': current_time.isoformat(),
                        'end': end_time.isoformat(),
                        'window_minutes': hours * 60
                    }

            if 'minute' in query_lower:
                import re
                match = re.search(r'next (\d+) minute', query_lower)
                if match:
                    minutes = int(match.group(1))
                    end_time = current_time + timedelta(minutes=minutes)
                    return {
                        'start': current_time.isoformat(),
                        'end': end_time.isoformat(),
                        'window_minutes': minutes
                    }

        # "today"
        if 'today' in query_lower:
            end_of_day = current_time.replace(hour=23, minute=59, second=59)
            minutes_remaining = int((end_of_day - current_time).total_seconds() / 60)
            return {
                'start': current_time.isoformat(),
                'end': end_of_day.isoformat(),
                'window_minutes': minutes_remaining
            }

        # "tonight"
        if 'tonight' in query_lower:
            start_evening = current_time.replace(hour=18, minute=0, second=0)
            if current_time.hour < 18:
                start_time = start_evening
            else:
                start_time = current_time

            end_time = current_time.replace(hour=23, minute=59, second=59)
            minutes = int((end_time - start_time).total_seconds() / 60)
            return {
                'start': start_time.isoformat(),
                'end': end_time.isoformat(),
                'window_minutes': minutes
            }

        # "tomorrow"
        if 'tomorrow' in query_lower:
            tomorrow = current_time + timedelta(days=1)
            start_time = tomorrow.replace(hour=0, minute=0, second=0)
            end_time = tomorrow.replace(hour=23, minute=59, second=59)
            return {
                'start': start_time.isoformat(),
                'end': end_time.isoformat(),
                'window_minutes': 24 * 60
            }

        # "this week"
        if 'this week' in query_lower or 'this weekend' in query_lower:
            # Until end of week (Sunday)
            days_until_sunday = (6 - current_time.weekday()) % 7
            end_of_week = current_time + timedelta(days=days_until_sunday)
            end_of_week = end_of_week.replace(hour=23, minute=59, second=59)
            minutes = int((end_of_week - current_time).total_seconds() / 60)
            return {
                'start': current_time.isoformat(),
                'end': end_of_week.isoformat(),
                'window_minutes': minutes
            }

        return None

    def _llm_parse(
        self,
        query: str,
        current_time: datetime
    ) -> Optional[Dict[str, Any]]:
        """Use LLM to parse complex queries."""
        prompt = f"""Parse the following natural language query about scheduled tasks into structured filters.

Current time: {current_time.isoformat()}
Current day: {current_time.strftime("%A")}
Current hour: {current_time.hour}

Query: "{query}"

Extract the following information:
1. Task group (reports, backups, maintenance, monitoring, synchronization, notifications, general)
2. Frequency (every_minute, every_5_minutes, hourly, daily, weekly, monthly)
3. Time of day (morning, afternoon, evening, night)
4. Day names (Monday, Tuesday, etc.)
5. Time window (start time, end time, duration in minutes)

Respond ONLY with JSON in this format:
{{
  "search_query": "meaningful search terms",
  "filters": {{
    "group": "backups",
    "frequency": "daily",
    "time_of_day": "night"
  }},
  "time_window": {{
    "start": "ISO timestamp",
    "end": "ISO timestamp",
    "window_minutes": 180
  }},
  "day_names": ["Monday", "Tuesday"]
}}

Examples:

Query: "all backup tasks running tonight"
{{
  "search_query": "backup tasks night",
  "filters": {{"group": "backups", "time_of_day": "evening"}},
  "time_window": {{"start": "2025-01-16T18:00:00", "end": "2025-01-16T23:59:59", "window_minutes": 360}},
  "day_names": []
}}

Query: "weekly reports on monday morning"
{{
  "search_query": "weekly reports monday morning",
  "filters": {{"group": "reports", "frequency": "weekly", "time_of_day": "morning"}},
  "time_window": null,
  "day_names": ["Monday"]
}}

Query: "tasks running in the next 3 hours"
{{
  "search_query": "tasks next 3 hours",
  "filters": {{}},
  "time_window": {{"start": "{current_time.isoformat()}", "end": "{(current_time + timedelta(hours=3)).isoformat()}", "window_minutes": 180}},
  "day_names": []
}}

Now parse: "{query}"
"""

        try:
            response = self.llm_client.generate(
                model=self.model,
                prompt=prompt,
                options={'temperature': 0.1}
            )

            response_text = response.get('response', '').strip()

            # Extract JSON
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            if start >= 0 and end > start:
                json_str = response_text[start:end]
                result = json.loads(json_str)
                result['parsed_method'] = 'llm'
                return result

        except Exception as e:
            logger.warning(f"LLM query parsing failed: {e}")

        return None

    def _fallback_parse(
        self,
        query: str,
        current_time: datetime
    ) -> Dict[str, Any]:
        """Fallback parsing when everything else fails."""
        return {
            'search_query': query,
            'filters': {},
            'time_window': None,
            'day_names': [],
            'parsed_method': 'fallback'
        }


def query_scheduled_tasks(
    query: str,
    current_time: Optional[str] = None,
    llm_client=None
) -> Dict[str, Any]:
    """
    Query scheduled tasks using natural language.

    Args:
        query: Natural language query
        current_time: Optional ISO timestamp for reference time
        llm_client: Optional LLM client for parsing

    Returns:
        Structured query filters
    """
    if current_time:
        current_time = datetime.fromisoformat(current_time)
    else:
        current_time = datetime.now()

    querier = CronQuerier(llm_client=llm_client)
    return querier.parse_query(query, current_time)


def main():
    """
    Main entry point for cron querier tool.

    Reads JSON input:
    {
        "query": "all backup tasks running tonight",
        "current_time": "2025-01-16T14:30:00"
    }

    Returns structured query filters.
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
    query = input_data.get('query')
    if not query:
        print(json.dumps({
            'status': 'error',
            'message': 'Missing required parameter: query'
        }))
        sys.exit(1)

    current_time = input_data.get('current_time')

    # Get LLM client if available
    llm_client = None
    try:
        from src import OllamaClient, ConfigManager
        config = ConfigManager()
        llm_client = OllamaClient(config_manager=config)
    except Exception:
        pass

    # Parse query
    try:
        result = query_scheduled_tasks(
            query,
            current_time=current_time,
            llm_client=llm_client
        )

        result['status'] = 'success'
        print(json.dumps(result, indent=2))

    except Exception as e:
        logger.exception(f"Failed to parse query: {e}")
        print(json.dumps({
            'status': 'error',
            'message': f'Failed to parse query: {str(e)}'
        }))
        sys.exit(1)


if __name__ == '__main__':
    main()
