#!/usr/bin/env python3
"""
Loki Manager - Manages Grafana Loki instances for log aggregation.

This tool provides:
- Automatic stand-up of Loki instances (Docker or standalone)
- Persistent data storage to configurable directory
- Log pushing and querying capabilities
- Health monitoring and status checks
- Support for tool-scoped and global deployment
"""
import json
import logging
import os
import subprocess
import sys
import time
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import OrderedDict

try:
    import requests
except ImportError:
    requests = None

try:
    import docker
    DOCKER_AVAILABLE = True
except ImportError:
    docker = None
    DOCKER_AVAILABLE = False


logger = logging.getLogger(__name__)


class LokiManager:
    """
    Manages Grafana Loki instances for log aggregation.

    Supports both Docker-based and standalone deployments with
    configurable data persistence and scope management.
    """

    _instances: Dict[str, 'LokiManager'] = {}
    _lock = threading.Lock()

    def __init__(
        self,
        url: str = "http://localhost:3100",
        data_path: str = "./data/loki",
        scope: str = "tool",
        docker_image: str = "grafana/loki:2.9.3",
        container_name: str = "code_evolver_loki_standalone",
        port: int = 3100,
        config_file: Optional[str] = None,
        default_labels: Optional[Dict[str, str]] = None,
        batch_size: int = 10,
        timeout_seconds: int = 5
    ):
        """
        Initialize Loki Manager.

        Args:
            url: Loki instance URL
            data_path: Path to persist Loki data
            scope: Deployment scope ('tool' or 'global')
            docker_image: Docker image to use
            container_name: Docker container name
            port: Loki HTTP port
            config_file: Path to Loki config YAML
            default_labels: Default labels for all log entries
            batch_size: Number of logs to batch before sending
            timeout_seconds: Request timeout
        """
        self.url = url.rstrip('/')
        self.push_url = f"{self.url}/loki/api/v1/push"
        self.query_url = f"{self.url}/loki/api/v1/query_range"
        self.labels_url = f"{self.url}/loki/api/v1/labels"
        self.ready_url = f"{self.url}/ready"

        self.data_path = Path(data_path)
        self.scope = scope
        self.docker_image = docker_image
        self.container_name = container_name
        self.port = port
        self.config_file = config_file or "./loki-config.yaml"
        self.default_labels = default_labels or {
            "application": "code_evolver",
            "environment": "development"
        }
        self.batch_size = batch_size
        self.timeout = timeout_seconds

        # Batch storage
        self._batch: List[Dict[str, Any]] = []
        self._batch_lock = threading.Lock()

        # Docker client
        self._docker_client = None
        if DOCKER_AVAILABLE:
            try:
                self._docker_client = docker.from_env()
            except Exception as e:
                logger.warning(f"Docker client unavailable: {e}")

        # Ensure data directory exists
        self.data_path.mkdir(parents=True, exist_ok=True)

        # Statistics
        self._stats = {
            'logs_pushed': 0,
            'logs_queried': 0,
            'push_errors': 0,
            'query_errors': 0,
            'started_at': datetime.now().isoformat()
        }
        self._stats_lock = threading.Lock()

    @classmethod
    def get_instance(
        cls,
        scope: str = "tool",
        **kwargs
    ) -> 'LokiManager':
        """
        Get or create a LokiManager instance.

        Args:
            scope: Instance scope (creates separate instances per scope)
            **kwargs: Arguments for LokiManager constructor

        Returns:
            LokiManager instance
        """
        with cls._lock:
            if scope not in cls._instances:
                cls._instances[scope] = cls(scope=scope, **kwargs)
            return cls._instances[scope]

    def start(self) -> Dict[str, Any]:
        """
        Start Loki instance.

        Returns:
            Status dictionary with result
        """
        # Check if already running
        if self.is_healthy():
            return {
                'status': 'success',
                'message': f'Loki already running at {self.url}',
                'instance_info': self.get_info()
            }

        # Try to start via Docker
        if self._docker_client:
            return self._start_docker()
        else:
            return {
                'status': 'error',
                'message': 'Docker not available. Please start Loki manually or install Docker.',
                'instance_info': None
            }

    def _start_docker(self) -> Dict[str, Any]:
        """
        Start Loki via Docker.

        Returns:
            Status dictionary
        """
        try:
            # Check if container exists
            try:
                container = self._docker_client.containers.get(self.container_name)
                # Container exists - start if stopped
                if container.status != 'running':
                    container.start()
                    time.sleep(2)  # Wait for startup
                    return {
                        'status': 'success',
                        'message': f'Started existing Loki container: {self.container_name}',
                        'instance_info': self.get_info()
                    }
                else:
                    return {
                        'status': 'success',
                        'message': f'Loki container already running: {self.container_name}',
                        'instance_info': self.get_info()
                    }
            except docker.errors.NotFound:
                # Container doesn't exist - create it
                pass

            # Resolve config file path
            config_path = Path(self.config_file).resolve()
            if not config_path.exists():
                return {
                    'status': 'error',
                    'message': f'Config file not found: {config_path}',
                    'instance_info': None
                }

            # Create container
            container = self._docker_client.containers.run(
                self.docker_image,
                name=self.container_name,
                ports={'3100/tcp': self.port},
                volumes={
                    str(self.data_path.resolve()): {'bind': '/loki', 'mode': 'rw'},
                    str(config_path): {'bind': '/etc/loki/local-config.yaml', 'mode': 'ro'}
                },
                command=['-config.file=/etc/loki/local-config.yaml'],
                detach=True,
                restart_policy={'Name': 'unless-stopped'}
            )

            # Wait for Loki to be ready
            max_retries = 30
            for i in range(max_retries):
                if self.is_healthy():
                    return {
                        'status': 'success',
                        'message': f'Loki started successfully at {self.url}',
                        'instance_info': self.get_info()
                    }
                time.sleep(1)

            return {
                'status': 'error',
                'message': f'Loki started but not responding after {max_retries}s',
                'instance_info': None
            }

        except Exception as e:
            logger.exception(f"Failed to start Loki: {e}")
            return {
                'status': 'error',
                'message': f'Failed to start Loki: {str(e)}',
                'instance_info': None
            }

    def stop(self) -> Dict[str, Any]:
        """
        Stop Loki instance.

        Returns:
            Status dictionary
        """
        # Flush pending logs first
        self.flush()

        if not self._docker_client:
            return {
                'status': 'error',
                'message': 'Docker not available. Cannot stop container.',
                'instance_info': None
            }

        try:
            container = self._docker_client.containers.get(self.container_name)
            container.stop()
            return {
                'status': 'success',
                'message': f'Loki stopped: {self.container_name}',
                'instance_info': None
            }
        except docker.errors.NotFound:
            return {
                'status': 'success',
                'message': 'Loki container not running',
                'instance_info': None
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Failed to stop Loki: {str(e)}',
                'instance_info': None
            }

    def restart(self) -> Dict[str, Any]:
        """
        Restart Loki instance.

        Returns:
            Status dictionary
        """
        stop_result = self.stop()
        if stop_result['status'] == 'error':
            return stop_result

        time.sleep(2)
        return self.start()

    def is_healthy(self) -> bool:
        """
        Check if Loki is healthy.

        Returns:
            True if Loki is responding
        """
        if not requests:
            return False

        try:
            response = requests.get(self.ready_url, timeout=2)
            return response.status_code == 200
        except Exception:
            return False

    def get_info(self) -> Dict[str, Any]:
        """
        Get Loki instance information.

        Returns:
            Instance info dictionary
        """
        info = {
            'url': self.url,
            'data_path': str(self.data_path),
            'scope': self.scope,
            'healthy': self.is_healthy(),
            'version': None,
            'container_name': self.container_name,
            'port': self.port
        }

        # Try to get version
        if requests and self.is_healthy():
            try:
                # Loki doesn't have a version endpoint, but we can check metrics
                metrics_url = f"{self.url}/metrics"
                response = requests.get(metrics_url, timeout=2)
                if response.status_code == 200:
                    # Parse version from metrics if available
                    for line in response.text.split('\n'):
                        if 'loki_build_info' in line and 'version=' in line:
                            version = line.split('version="')[1].split('"')[0]
                            info['version'] = version
                            break
            except Exception:
                pass

        return info

    def status(self) -> Dict[str, Any]:
        """
        Get Loki status.

        Returns:
            Status dictionary
        """
        instance_info = self.get_info()

        with self._stats_lock:
            stats = self._stats.copy()

        return {
            'status': 'success' if instance_info['healthy'] else 'unhealthy',
            'message': 'Loki is healthy' if instance_info['healthy'] else 'Loki is not responding',
            'instance_info': instance_info,
            'stats': stats,
            'batch_size': len(self._batch)
        }

    def push(
        self,
        logs: List[Dict[str, Any]],
        labels: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Push log entries to Loki.

        Args:
            logs: List of log entries with 'timestamp' (ns) and 'message'
            labels: Labels for this log stream (merged with default labels)

        Returns:
            Status dictionary
        """
        if not requests:
            return {
                'status': 'error',
                'message': 'requests library not available'
            }

        # Merge labels
        stream_labels = {**self.default_labels}
        if labels:
            stream_labels.update(labels)

        # Add logs to batch
        with self._batch_lock:
            for log in logs:
                timestamp = log.get('timestamp')
                message = log.get('message', '')

                # Convert timestamp to nanoseconds if needed
                if timestamp is None:
                    timestamp = int(time.time() * 1e9)
                elif isinstance(timestamp, datetime):
                    timestamp = int(timestamp.timestamp() * 1e9)
                elif isinstance(timestamp, (int, float)):
                    # Assume seconds if < 1e12, else assume already in nanoseconds
                    if timestamp < 1e12:
                        timestamp = int(timestamp * 1e9)
                    else:
                        timestamp = int(timestamp)

                self._batch.append({
                    'stream': stream_labels,
                    'values': [[str(timestamp), message]]
                })

            # Send batch if full
            if len(self._batch) >= self.batch_size:
                return self._send_batch()

        return {
            'status': 'success',
            'message': f'Added {len(logs)} logs to batch (size: {len(self._batch)})'
        }

    def _send_batch(self) -> Dict[str, Any]:
        """
        Send batched logs to Loki.

        Returns:
            Status dictionary
        """
        if not self._batch:
            return {
                'status': 'success',
                'message': 'No logs to send'
            }

        payload = {'streams': self._batch}

        try:
            response = requests.post(
                self.push_url,
                json=payload,
                timeout=self.timeout,
                headers={'Content-Type': 'application/json'}
            )
            response.raise_for_status()

            batch_count = len(self._batch)
            self._batch.clear()

            with self._stats_lock:
                self._stats['logs_pushed'] += batch_count

            return {
                'status': 'success',
                'message': f'Pushed {batch_count} logs to Loki'
            }

        except Exception as e:
            with self._stats_lock:
                self._stats['push_errors'] += 1

            logger.warning(f"Failed to push logs to Loki: {e}")
            return {
                'status': 'error',
                'message': f'Failed to push logs: {str(e)}'
            }

    def flush(self) -> Dict[str, Any]:
        """
        Flush any pending batched logs.

        Returns:
            Status dictionary
        """
        with self._batch_lock:
            if self._batch:
                return self._send_batch()

        return {
            'status': 'success',
            'message': 'No logs to flush'
        }

    def query(
        self,
        query: str,
        start_time: str = "1h",
        end_time: str = "now",
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Query logs from Loki.

        Args:
            query: LogQL query string (e.g., '{application="code_evolver"}')
            start_time: Start time (ISO8601 or relative like '1h', '30m')
            end_time: End time (ISO8601 or 'now')
            limit: Maximum number of entries

        Returns:
            Status dictionary with logs
        """
        if not requests:
            return {
                'status': 'error',
                'message': 'requests library not available',
                'logs': []
            }

        try:
            # Parse times
            end_ts = self._parse_time(end_time)
            start_ts = self._parse_time(start_time, relative_to=end_ts)

            # Query Loki
            params = {
                'query': query,
                'start': int(start_ts.timestamp() * 1e9),
                'end': int(end_ts.timestamp() * 1e9),
                'limit': limit
            }

            response = requests.get(
                self.query_url,
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()

            data = response.json()

            # Extract logs
            logs = []
            if data.get('status') == 'success':
                for result in data.get('data', {}).get('result', []):
                    stream_labels = result.get('stream', {})
                    for ts_ns, message in result.get('values', []):
                        logs.append({
                            'timestamp': int(ts_ns),
                            'message': message,
                            'labels': stream_labels
                        })

            with self._stats_lock:
                self._stats['logs_queried'] += len(logs)

            return {
                'status': 'success',
                'message': f'Found {len(logs)} log entries',
                'logs': logs
            }

        except Exception as e:
            with self._stats_lock:
                self._stats['query_errors'] += 1

            logger.exception(f"Failed to query Loki: {e}")
            return {
                'status': 'error',
                'message': f'Query failed: {str(e)}',
                'logs': []
            }

    def tail(
        self,
        query: str = '{application="code_evolver"}',
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Tail recent logs.

        Args:
            query: LogQL query string
            limit: Number of recent entries

        Returns:
            Status dictionary with logs
        """
        return self.query(
            query=query,
            start_time="5m",
            end_time="now",
            limit=limit
        )

    def get_labels(self) -> Dict[str, Any]:
        """
        Get available label names from Loki.

        Returns:
            Status dictionary with labels list
        """
        if not requests:
            return {
                'status': 'error',
                'message': 'requests library not available',
                'labels_list': []
            }

        try:
            response = requests.get(self.labels_url, timeout=self.timeout)
            response.raise_for_status()

            data = response.json()
            labels = data.get('data', [])

            return {
                'status': 'success',
                'message': f'Found {len(labels)} labels',
                'labels_list': labels
            }

        except Exception as e:
            logger.exception(f"Failed to get labels: {e}")
            return {
                'status': 'error',
                'message': f'Failed to get labels: {str(e)}',
                'labels_list': []
            }

    def _parse_time(
        self,
        time_str: str,
        relative_to: Optional[datetime] = None
    ) -> datetime:
        """
        Parse time string to datetime.

        Args:
            time_str: Time string (ISO8601, 'now', or relative like '1h', '30m')
            relative_to: Reference time for relative times

        Returns:
            Parsed datetime
        """
        if time_str == 'now':
            return datetime.now()

        # Try relative time (e.g., '1h', '30m', '2d')
        if time_str[-1] in ('h', 'm', 's', 'd'):
            unit = time_str[-1]
            value = int(time_str[:-1])

            ref_time = relative_to or datetime.now()

            if unit == 's':
                delta = timedelta(seconds=value)
            elif unit == 'm':
                delta = timedelta(minutes=value)
            elif unit == 'h':
                delta = timedelta(hours=value)
            elif unit == 'd':
                delta = timedelta(days=value)

            return ref_time - delta

        # Try ISO8601
        try:
            return datetime.fromisoformat(time_str)
        except Exception:
            pass

        # Default to now
        return datetime.now()


def main():
    """
    Main entry point for Loki tool.

    Reads JSON input from stdin and executes the requested operation.
    """
    # Read input from stdin
    try:
        input_data = json.loads(sys.stdin.read())
    except Exception as e:
        print(json.dumps({
            'status': 'error',
            'message': f'Invalid JSON input: {str(e)}'
        }))
        sys.exit(1)

    # Extract parameters
    operation = input_data.get('operation')
    if not operation:
        print(json.dumps({
            'status': 'error',
            'message': 'Missing required parameter: operation'
        }))
        sys.exit(1)

    # Get or create LokiManager instance
    scope = input_data.get('scope', 'tool')
    url = input_data.get('url', 'http://localhost:3100')
    data_path = input_data.get('data_path', './data/loki')

    manager = LokiManager.get_instance(
        scope=scope,
        url=url,
        data_path=data_path
    )

    # Execute operation
    result = None

    if operation == 'start':
        result = manager.start()

    elif operation == 'stop':
        result = manager.stop()

    elif operation == 'restart':
        result = manager.restart()

    elif operation == 'status':
        result = manager.status()

    elif operation == 'push':
        logs = input_data.get('logs', [])
        labels = input_data.get('labels')
        result = manager.push(logs, labels)

    elif operation == 'query':
        query = input_data.get('query', '{application="code_evolver"}')
        start_time = input_data.get('start_time', '1h')
        end_time = input_data.get('end_time', 'now')
        limit = input_data.get('limit', 100)
        result = manager.query(query, start_time, end_time, limit)

    elif operation == 'tail':
        query = input_data.get('query', '{application="code_evolver"}')
        limit = input_data.get('limit', 50)
        result = manager.tail(query, limit)

    elif operation == 'labels':
        result = manager.get_labels()

    else:
        result = {
            'status': 'error',
            'message': f'Unknown operation: {operation}'
        }

    # Output result
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
