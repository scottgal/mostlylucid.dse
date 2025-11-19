"""
IP Geolocation Tool
Get geolocation information for any IP address using ip-api.com
"""
import requests
import json
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class IpGeolocationTool:
    """Get geolocation information for IP addresses."""

    def __init__(self):
        self.api_base = "http://ip-api.com/json"
        self.cache_ttl_hours = 168  # 1 week

    def execute(self, params: Dict[str, Any]) -> str:
        """
        Get geolocation for an IP address.

        Args:
            params: Dictionary with optional fields:
                - ip_address: IP to lookup (empty/None for current IP)
                - fields: List of specific fields to return

        Returns:
            JSON string with geolocation data
        """
        try:
            ip_address = params.get('ip_address', '')
            fields = params.get('fields', [])

            # Build URL
            url = f"{self.api_base}/{ip_address}" if ip_address else self.api_base

            # Add fields parameter if specified
            if fields:
                fields_param = ','.join(fields)
                url += f"?fields={fields_param}"

            # Make request
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()

            # Check if successful
            if data.get('status') == 'fail':
                return json.dumps({
                    "success": False,
                    "error": data.get('message', 'Unknown error')
                })

            # Return successful result
            return json.dumps({
                "success": True,
                **data
            })

        except requests.exceptions.RequestException as e:
            logger.error(f"IP geolocation request failed: {e}")
            return json.dumps({
                "success": False,
                "error": str(e)
            })
        except Exception as e:
            logger.error(f"IP geolocation tool error: {e}")
            return json.dumps({
                "success": False,
                "error": str(e)
            })


def main():
    """CLI entry point for testing."""
    import sys

    # Read input from stdin
    input_data = json.loads(sys.stdin.read()) if not sys.stdin.isatty() else {}

    tool = IpGeolocationTool()
    result = tool.execute(input_data)
    print(result)


if __name__ == "__main__":
    main()
