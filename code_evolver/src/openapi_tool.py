"""
OpenAPI tool integration for Code Evolver.
Allows tools to be defined by OpenAPI specifications and invoked dynamically.
"""
import json
import logging
import requests
from typing import Dict, Any, Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)


class OpenAPITool:
    """
    Handles OpenAPI-based tools that can call REST APIs.

    Features:
    - Load OpenAPI/Swagger specs (JSON or YAML)
    - Parse available endpoints and operations
    - Generate LLM-friendly descriptions of API capabilities
    - Execute API calls with proper authentication
    - Handle request/response transformation
    """

    def __init__(
        self,
        tool_id: str,
        name: str,
        spec_path: Optional[str] = None,
        spec_url: Optional[str] = None,
        spec_dict: Optional[Dict[str, Any]] = None,
        base_url_override: Optional[str] = None,
        auth_config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize OpenAPI tool.

        Args:
            tool_id: Unique tool identifier
            name: Human-readable name
            spec_path: Path to OpenAPI spec file (.json or .yaml)
            spec_url: URL to fetch OpenAPI spec from
            spec_dict: OpenAPI spec as dictionary
            base_url_override: Override the base URL from spec
            auth_config: Authentication configuration
                {
                    "type": "bearer|api_key|basic",
                    "token": "...",
                    "api_key_name": "X-API-Key",
                    "username": "...",
                    "password": "..."
                }
        """
        self.tool_id = tool_id
        self.name = name
        self.base_url_override = base_url_override
        self.auth_config = auth_config or {}
        self.spec: Dict[str, Any] = {}
        self.operations: Dict[str, Dict[str, Any]] = {}

        # Load spec from one of the sources
        if spec_dict:
            self.spec = spec_dict
        elif spec_path:
            self._load_spec_from_file(spec_path)
        elif spec_url:
            self._load_spec_from_url(spec_url)
        else:
            raise ValueError("Must provide spec_path, spec_url, or spec_dict")

        # Parse operations
        self._parse_operations()

    def _load_spec_from_file(self, spec_path: str):
        """Load OpenAPI spec from file."""
        path = Path(spec_path)

        if not path.exists():
            raise FileNotFoundError(f"OpenAPI spec not found: {spec_path}")

        with open(path, 'r', encoding='utf-8') as f:
            if path.suffix == '.json':
                self.spec = json.load(f)
            elif path.suffix in ['.yaml', '.yml']:
                try:
                    import yaml
                    self.spec = yaml.safe_load(f)
                except ImportError:
                    raise ImportError("PyYAML required for YAML specs: pip install pyyaml")
            else:
                raise ValueError(f"Unsupported spec format: {path.suffix}")

        logger.info(f"Loaded OpenAPI spec from {spec_path}")

    def _load_spec_from_url(self, spec_url: str):
        """Load OpenAPI spec from URL."""
        try:
            response = requests.get(spec_url, timeout=30)
            response.raise_for_status()
            self.spec = response.json()
            logger.info(f"Loaded OpenAPI spec from {spec_url}")
        except Exception as e:
            raise Exception(f"Failed to load OpenAPI spec from {spec_url}: {e}")

    def _parse_operations(self):
        """Parse operations from OpenAPI spec."""
        paths = self.spec.get("paths", {})

        for path, path_item in paths.items():
            for method in ["get", "post", "put", "patch", "delete"]:
                if method in path_item:
                    operation = path_item[method]
                    operation_id = operation.get("operationId", f"{method}_{path.replace('/', '_')}")

                    self.operations[operation_id] = {
                        "path": path,
                        "method": method.upper(),
                        "summary": operation.get("summary", ""),
                        "description": operation.get("description", ""),
                        "parameters": operation.get("parameters", []),
                        "requestBody": operation.get("requestBody", {}),
                        "responses": operation.get("responses", {}),
                        "tags": operation.get("tags", [])
                    }

        logger.info(f"Parsed {len(self.operations)} operations from OpenAPI spec")

    def get_base_url(self) -> str:
        """Get base URL for API calls."""
        if self.base_url_override:
            return self.base_url_override

        # Try to get from servers array (OpenAPI 3.0)
        servers = self.spec.get("servers", [])
        if servers:
            return servers[0].get("url", "")

        # Fallback to host + basePath (OpenAPI 2.0/Swagger)
        host = self.spec.get("host", "")
        base_path = self.spec.get("basePath", "")
        schemes = self.spec.get("schemes", ["https"])

        if host:
            return f"{schemes[0]}://{host}{base_path}"

        raise ValueError("Could not determine base URL from OpenAPI spec")

    def get_capabilities_description(self) -> str:
        """
        Generate LLM-friendly description of API capabilities.
        This can be passed to the LLM to help it understand what the API can do.
        """
        lines = [f"API: {self.name}"]
        lines.append(f"Base URL: {self.get_base_url()}")
        lines.append(f"\nAvailable Operations ({len(self.operations)}):")

        for op_id, op in self.operations.items():
            lines.append(f"\n- {op_id}:")
            lines.append(f"  Method: {op['method']} {op['path']}")
            if op['summary']:
                lines.append(f"  Summary: {op['summary']}")
            if op['description']:
                lines.append(f"  Description: {op['description']}")

            # Parameters
            if op['parameters']:
                param_strs = []
                for param in op['parameters']:
                    param_name = param.get('name', '')
                    param_in = param.get('in', '')
                    required = ' (required)' if param.get('required') else ''
                    param_strs.append(f"{param_name} ({param_in}){required}")
                lines.append(f"  Parameters: {', '.join(param_strs)}")

        return "\n".join(lines)

    def invoke(
        self,
        operation_id: str,
        parameters: Optional[Dict[str, Any]] = None,
        body: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Invoke an API operation.

        Args:
            operation_id: The operation ID from OpenAPI spec
            parameters: Query/path/header parameters
            body: Request body for POST/PUT/PATCH

        Returns:
            Response data as dictionary
        """
        if operation_id not in self.operations:
            raise ValueError(f"Unknown operation: {operation_id}")

        op = self.operations[operation_id]
        url = self._build_url(op, parameters or {})
        headers = self._build_headers(op, parameters or {})

        logger.info(f"Invoking {op['method']} {url}")

        try:
            response = requests.request(
                method=op['method'],
                url=url,
                headers=headers,
                json=body if body else None,
                timeout=30
            )

            # Return response data
            result = {
                "status_code": response.status_code,
                "success": response.status_code < 400,
                "headers": dict(response.headers),
                "data": None,
                "error": None
            }

            # Try to parse JSON response
            try:
                result["data"] = response.json()
            except:
                result["data"] = response.text

            if not result["success"]:
                result["error"] = f"HTTP {response.status_code}: {response.text[:200]}"

            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"API call failed: {e}")
            return {
                "status_code": 0,
                "success": False,
                "data": None,
                "error": str(e)
            }

    def _build_url(self, operation: Dict[str, Any], parameters: Dict[str, Any]) -> str:
        """Build complete URL with path parameters and query string."""
        base_url = self.get_base_url()
        path = operation['path']

        # Substitute path parameters
        for param in operation.get('parameters', []):
            if param.get('in') == 'path':
                param_name = param['name']
                if param_name in parameters:
                    path = path.replace(f"{{{param_name}}}", str(parameters[param_name]))

        url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"

        # Add query parameters
        query_params = {}
        for param in operation.get('parameters', []):
            if param.get('in') == 'query':
                param_name = param['name']
                if param_name in parameters:
                    query_params[param_name] = parameters[param_name]

        if query_params:
            query_string = "&".join([f"{k}={v}" for k, v in query_params.items()])
            url = f"{url}?{query_string}"

        return url

    def _build_headers(self, operation: Dict[str, Any], parameters: Dict[str, Any]) -> Dict[str, str]:
        """Build request headers including authentication."""
        headers = {"Content-Type": "application/json"}

        # Add header parameters from operation
        for param in operation.get('parameters', []):
            if param.get('in') == 'header':
                param_name = param['name']
                if param_name in parameters:
                    headers[param_name] = str(parameters[param_name])

        # Add authentication
        auth_type = self.auth_config.get('type')

        if auth_type == 'bearer':
            token = self.auth_config.get('token', '')
            headers['Authorization'] = f'Bearer {token}'

        elif auth_type == 'api_key':
            api_key_name = self.auth_config.get('api_key_name', 'X-API-Key')
            api_key = self.auth_config.get('token', '')
            headers[api_key_name] = api_key

        elif auth_type == 'basic':
            import base64
            username = self.auth_config.get('username', '')
            password = self.auth_config.get('password', '')
            credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
            headers['Authorization'] = f'Basic {credentials}'

        return headers

    def list_operations(self) -> List[Dict[str, str]]:
        """List all available operations."""
        return [
            {
                "operation_id": op_id,
                "method": op['method'],
                "path": op['path'],
                "summary": op['summary']
            }
            for op_id, op in self.operations.items()
        ]
