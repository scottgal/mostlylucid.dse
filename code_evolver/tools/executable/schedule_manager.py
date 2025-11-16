#!/usr/bin/env python3
"""
Schedule Manager Tool

Executable tool for managing scheduled tasks and workflows.
Interfaces with the SchedulerService to create, manage, and execute schedules.
"""

import sys
import json
import os
import logging

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.scheduler_service import SchedulerService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_schedule(params: dict) -> dict:
    """Create a new schedule."""
    required = ['name', 'description', 'cron_expression', 'tool_name']
    for field in required:
        if field not in params:
            return {'success': False, 'error': f'Missing required field: {field}'}

    try:
        scheduler = SchedulerService()
        schedule = scheduler.create_schedule(
            name=params['name'],
            description=params['description'],
            cron_expression=params['cron_expression'],
            tool_name=params['tool_name'],
            tool_inputs=params.get('tool_inputs', {})
        )

        return {
            'success': True,
            'data': schedule
        }

    except ValueError as e:
        return {'success': False, 'error': str(e)}
    except Exception as e:
        logger.error(f"Failed to create schedule: {e}", exc_info=True)
        return {'success': False, 'error': str(e)}


def list_schedules(params: dict) -> dict:
    """List all schedules, optionally filtered by status."""
    try:
        scheduler = SchedulerService()
        status = params.get('status')
        schedules = scheduler.list_schedules(status=status)

        return {
            'success': True,
            'data': {
                'schedules': schedules,
                'count': len(schedules)
            }
        }

    except Exception as e:
        logger.error(f"Failed to list schedules: {e}", exc_info=True)
        return {'success': False, 'error': str(e)}


def get_schedule(params: dict) -> dict:
    """Get a specific schedule by ID."""
    if 'schedule_id' not in params:
        return {'success': False, 'error': 'Missing required field: schedule_id'}

    try:
        scheduler = SchedulerService()
        schedule = scheduler.get_schedule(params['schedule_id'])

        if schedule is None:
            return {'success': False, 'error': f"Schedule not found: {params['schedule_id']}"}

        return {
            'success': True,
            'data': schedule
        }

    except Exception as e:
        logger.error(f"Failed to get schedule: {e}", exc_info=True)
        return {'success': False, 'error': str(e)}


def pause_schedule(params: dict) -> dict:
    """Pause a schedule."""
    if 'schedule_id' not in params:
        return {'success': False, 'error': 'Missing required field: schedule_id'}

    try:
        scheduler = SchedulerService()
        scheduler.pause_schedule(params['schedule_id'])

        return {
            'success': True,
            'data': {'message': f"Schedule {params['schedule_id']} paused"}
        }

    except ValueError as e:
        return {'success': False, 'error': str(e)}
    except Exception as e:
        logger.error(f"Failed to pause schedule: {e}", exc_info=True)
        return {'success': False, 'error': str(e)}


def resume_schedule(params: dict) -> dict:
    """Resume a paused schedule."""
    if 'schedule_id' not in params:
        return {'success': False, 'error': 'Missing required field: schedule_id'}

    try:
        scheduler = SchedulerService()
        scheduler.resume_schedule(params['schedule_id'])

        return {
            'success': True,
            'data': {'message': f"Schedule {params['schedule_id']} resumed"}
        }

    except ValueError as e:
        return {'success': False, 'error': str(e)}
    except Exception as e:
        logger.error(f"Failed to resume schedule: {e}", exc_info=True)
        return {'success': False, 'error': str(e)}


def delete_schedule(params: dict) -> dict:
    """Delete a schedule permanently."""
    if 'schedule_id' not in params:
        return {'success': False, 'error': 'Missing required field: schedule_id'}

    try:
        scheduler = SchedulerService()
        scheduler.delete_schedule(params['schedule_id'])

        return {
            'success': True,
            'data': {'message': f"Schedule {params['schedule_id']} deleted"}
        }

    except ValueError as e:
        return {'success': False, 'error': str(e)}
    except Exception as e:
        logger.error(f"Failed to delete schedule: {e}", exc_info=True)
        return {'success': False, 'error': str(e)}


def trigger_schedule(params: dict) -> dict:
    """Trigger a schedule to run immediately."""
    if 'schedule_id' not in params:
        return {'success': False, 'error': 'Missing required field: schedule_id'}

    try:
        scheduler = SchedulerService()
        result = scheduler.trigger_now(params['schedule_id'])

        return {
            'success': True,
            'data': result
        }

    except ValueError as e:
        return {'success': False, 'error': str(e)}
    except Exception as e:
        logger.error(f"Failed to trigger schedule: {e}", exc_info=True)
        return {'success': False, 'error': str(e)}


def get_history(params: dict) -> dict:
    """Get execution history for a schedule."""
    if 'schedule_id' not in params:
        return {'success': False, 'error': 'Missing required field: schedule_id'}

    try:
        scheduler = SchedulerService()
        limit = params.get('limit', 50)
        history = scheduler.get_execution_history(params['schedule_id'], limit)

        return {
            'success': True,
            'data': {
                'executions': history,
                'count': len(history)
            }
        }

    except Exception as e:
        logger.error(f"Failed to get execution history: {e}", exc_info=True)
        return {'success': False, 'error': str(e)}


def main():
    """Main entry point for the schedule manager tool."""
    if len(sys.argv) < 3:
        print(json.dumps({
            'success': False,
            'error': 'Usage: schedule_manager.py <operation> <params_json>'
        }))
        sys.exit(1)

    operation = sys.argv[1]
    params_json = sys.argv[2]

    try:
        params = json.loads(params_json)
    except json.JSONDecodeError as e:
        print(json.dumps({
            'success': False,
            'error': f'Invalid JSON parameters: {e}'
        }))
        sys.exit(1)

    # Dispatch to appropriate operation
    operations = {
        'create': create_schedule,
        'list': list_schedules,
        'get': get_schedule,
        'pause': pause_schedule,
        'resume': resume_schedule,
        'delete': delete_schedule,
        'trigger': trigger_schedule,
        'history': get_history
    }

    if operation not in operations:
        print(json.dumps({
            'success': False,
            'error': f'Unknown operation: {operation}. Valid operations: {", ".join(operations.keys())}'
        }))
        sys.exit(1)

    # Execute operation and print result
    result = operations[operation](params)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
