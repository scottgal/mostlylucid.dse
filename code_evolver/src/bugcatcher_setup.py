"""
BugCatcher setup and initialization.

This module provides helpers for setting up BugCatcher based on
configuration settings.
"""
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


def initialize_bugcatcher_from_config(config: Dict[str, Any]) -> Optional[object]:
    """
    Initialize BugCatcher from configuration.

    Args:
        config: Configuration dictionary (typically from ConfigManager)

    Returns:
        BugCatcher instance if enabled, None otherwise
    """
    bugcatcher_config = config.get('bugcatcher', {})

    # Check if enabled
    if not bugcatcher_config.get('enabled', False):
        logger.info("BugCatcher is disabled in configuration")
        return None

    try:
        from .bugcatcher import setup_bugcatcher_logging

        # Extract configuration
        loki_config = bugcatcher_config.get('loki', {})
        cache_config = bugcatcher_config.get('cache', {})
        file_logging_config = bugcatcher_config.get('file_logging', {})
        tracking_config = bugcatcher_config.get('tracking', {})

        # Set up BugCatcher
        bugcatcher = setup_bugcatcher_logging(
            loki_url=loki_config.get('url', 'http://localhost:3100'),
            loki_enabled=loki_config.get('enabled', True),
            cache_size=cache_config.get('max_size', 100),
            log_to_file=file_logging_config.get('enabled', True),
            log_file=file_logging_config.get('file', 'bugcatcher.log'),
            track_outputs=tracking_config.get('outputs', False)
        )

        logger.info("BugCatcher initialized successfully")
        return bugcatcher

    except ImportError:
        logger.warning("BugCatcher module not available")
        return None
    except Exception as e:
        logger.error(f"Failed to initialize BugCatcher: {e}")
        return None


def check_loki_connection(loki_url: str = "http://localhost:3100", timeout: int = 2) -> bool:
    """
    Check if Loki is available.

    Args:
        loki_url: Loki URL
        timeout: Connection timeout in seconds

    Returns:
        True if Loki is reachable, False otherwise
    """
    try:
        import requests

        # Try to reach Loki ready endpoint
        response = requests.get(
            f"{loki_url.rstrip('/')}/ready",
            timeout=timeout
        )
        return response.status_code == 200

    except Exception as e:
        logger.debug(f"Loki connection check failed: {e}")
        return False


def get_bugcatcher_stats() -> Dict[str, Any]:
    """
    Get BugCatcher statistics.

    Returns:
        Dict with stats, or empty dict if BugCatcher not available
    """
    try:
        from .bugcatcher import get_bugcatcher

        bugcatcher = get_bugcatcher()
        return bugcatcher.get_stats()

    except (ImportError, Exception) as e:
        logger.debug(f"Could not get BugCatcher stats: {e}")
        return {}


def flush_bugcatcher():
    """
    Flush any pending BugCatcher logs to Loki.

    This should be called before application shutdown to ensure
    all logs are sent.
    """
    try:
        from .bugcatcher import get_bugcatcher

        bugcatcher = get_bugcatcher()
        bugcatcher.flush()
        logger.debug("BugCatcher logs flushed")

    except (ImportError, Exception) as e:
        logger.debug(f"Could not flush BugCatcher: {e}")
