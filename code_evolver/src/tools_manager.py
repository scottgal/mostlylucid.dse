"""
Tools Manager - Registry for reusable components (functions, LLMs, workflows).
Provides a system for storing and retrieving tools that can be used by the coordinator.
Future: Will integrate with RAG for semantic search.
"""
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from enum import Enum
from .openapi_tool import OpenAPITool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ToolType(Enum):
    """Types of tools that can be registered."""
    FUNCTION = "function"              # Python function
    LLM = "llm"                       # Specialized LLM model
    WORKFLOW = "workflow"             # Complete workflow
    COMMUNITY = "community"           # Sub-workflow (community of agents)
    PROMPT_TEMPLATE = "prompt_template"  # Reusable prompt
    DATA_PROCESSOR = "data_processor"    # Data transformation tool
    VALIDATOR = "validator"              # Validation tool
    OPENAPI = "openapi"               # OpenAPI/REST API tool
    EXECUTABLE = "executable"         # Executable command-line tool
    CUSTOM = "custom"                    # Custom tool type

    # Storage & Data Nodes
    DATABASE = "database"             # SQL/NoSQL database connections
    FILE_SYSTEM = "file_system"       # Persistent file storage
    VECTOR_STORE = "vector_store"     # RAG/embedding storage (Qdrant, Pinecone, etc.)
    API_CONNECTOR = "api_connector"   # External data sources (REST APIs, etc.)
    CACHE = "cache"                   # In-memory/Redis cache
    MESSAGE_QUEUE = "message_queue"   # Kafka/RabbitMQ for streaming

    # Optimization & Fine-tuning
    FINE_TUNED_LLM = "fine_tuned_llm" # Fine-tuned specialist model
    TRAINING_PIPELINE = "training_pipeline"  # Model training/fine-tuning pipeline
    OPTIMIZER = "optimizer"           # Code/workflow optimizer


class Tool:
    """Represents a reusable tool."""

    def __init__(
        self,
        tool_id: str,
        name: str,
        tool_type: ToolType,
        description: str,
        tags: List[str],
        implementation: Any = None,
        parameters: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        constraints: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize a tool.

        Args:
            tool_id: Unique identifier
            name: Human-readable name
            tool_type: Type of tool
            description: Detailed description
            tags: List of tags for categorization
            implementation: The actual implementation (function, code, config, etc.)
            parameters: Parameter schema
            metadata: Additional metadata
            constraints: Platform/resource constraints
                Examples:
                - max_db_size_mb: 100 (for Raspberry Pi SQLite)
                - max_memory_mb: 512
                - max_calls_per_hour: 1000
                - device_type: "raspberry_pi" (platform constraint)
        """
        self.tool_id = tool_id
        self.name = name
        self.tool_type = tool_type
        self.description = description
        self.tags = tags
        self.implementation = implementation
        self.parameters = parameters or {}
        self.metadata = metadata or {}
        self.constraints = constraints or {}
        self.created_at = datetime.utcnow().isoformat() + "Z"
        self.usage_count = 0

        # Current usage tracking (for constraint checking)
        self.current_usage = {
            "storage_mb": 0.0,
            "memory_mb": 0.0,
            "calls_count": 0,
            "last_reset": datetime.utcnow().isoformat() + "Z"
        }

    def check_constraints(self, proposed_usage: Optional[Dict[str, float]] = None) -> tuple[bool, Optional[str]]:
        """
        Check if tool constraints are satisfied.

        Args:
            proposed_usage: Proposed additional usage (optional)

        Returns:
            (is_valid, violation_message) tuple

        Example:
            >>> tool = Tool(..., constraints={"max_db_size_mb": 100})
            >>> tool.current_usage["storage_mb"] = 95
            >>> is_valid, msg = tool.check_constraints({"storage_mb": 10})
            >>> print(is_valid)  # False
            >>> print(msg)  # "Storage would exceed max_db_size_mb: 105 > 100"
        """
        if not self.constraints:
            return True, None  # No constraints

        # Calculate total usage (current + proposed)
        total_usage = self.current_usage.copy()
        if proposed_usage:
            for key, value in proposed_usage.items():
                total_usage[key] = total_usage.get(key, 0) + value

        # Check each constraint
        if "max_db_size_mb" in self.constraints:
            max_size = self.constraints["max_db_size_mb"]
            current_size = total_usage.get("storage_mb", 0)
            if current_size > max_size:
                return False, (
                    f"Storage would exceed max_db_size_mb constraint: "
                    f"{current_size:.1f}MB > {max_size}MB. "
                    f"Consider pruning data, compression, or upgrading to cloud storage."
                )

        if "max_memory_mb" in self.constraints:
            max_mem = self.constraints["max_memory_mb"]
            current_mem = total_usage.get("memory_mb", 0)
            if current_mem > max_mem:
                return False, (
                    f"Memory would exceed max_memory_mb constraint: "
                    f"{current_mem:.1f}MB > {max_mem}MB"
                )

        if "max_calls_per_hour" in self.constraints:
            max_calls = self.constraints["max_calls_per_hour"]
            current_calls = total_usage.get("calls_count", 0)
            if current_calls > max_calls:
                return False, (
                    f"Calls would exceed max_calls_per_hour constraint: "
                    f"{current_calls} > {max_calls}"
                )

        return True, None

    def update_usage(self, usage: Dict[str, float]):
        """
        Update current usage metrics.

        Args:
            usage: Usage update dict (e.g., {"storage_mb": 5.2, "calls_count": 1})
        """
        for key, value in usage.items():
            if key in self.current_usage:
                self.current_usage[key] += value
            else:
                self.current_usage[key] = value

    def to_dict(self) -> Dict[str, Any]:
        """Convert tool to dictionary (for serialization)."""
        return {
            "tool_id": self.tool_id,
            "name": self.name,
            "tool_type": self.tool_type.value,
            "description": self.description,
            "tags": self.tags,
            "parameters": self.parameters,
            "metadata": self.metadata,
            "constraints": self.constraints,
            "current_usage": self.current_usage,
            "created_at": self.created_at,
            "usage_count": self.usage_count
        }

    def to_prompt_format(self) -> str:
        """
        Format tool information for inclusion in prompts.

        Returns:
            Formatted string describing the tool
        """
        params_str = ""
        if self.parameters:
            params_list = [f"  - {name}: {info.get('type', 'any')} - {info.get('description', '')}"
                          for name, info in self.parameters.items()]
            params_str = "\nParameters:\n" + "\n".join(params_list)

        return f"""Tool: {self.name} ({self.tool_id})
Type: {self.tool_type.value}
Description: {self.description}
Tags: {', '.join(self.tags)}{params_str}
"""

    @staticmethod
    def from_dict(data: Dict[str, Any], implementation: Any = None) -> 'Tool':
        """Create tool from dictionary."""
        tool = Tool(
            tool_id=data["tool_id"],
            name=data["name"],
            tool_type=ToolType(data["tool_type"]),
            description=data["description"],
            tags=data["tags"],
            implementation=implementation,
            parameters=data.get("parameters", {}),
            metadata=data.get("metadata", {})
        )
        tool.created_at = data.get("created_at", tool.created_at)
        tool.usage_count = data.get("usage_count", 0)
        return tool


class ToolsManager:
    """Manages registry of reusable tools."""

    def __init__(
        self,
        tools_path: str = "./tools",
        config_manager: Optional[Any] = None,
        ollama_client: Optional[Any] = None,
        rag_memory: Optional[Any] = None
    ):
        """
        Initialize tools manager.

        Args:
            tools_path: Path to tools storage directory
            config_manager: Optional ConfigManager for loading tools from config
            ollama_client: Optional OllamaClient for invoking LLM-based tools
            rag_memory: Optional RAGMemory for semantic tool search
        """
        self.tools_path = Path(tools_path)
        self.tools_path.mkdir(parents=True, exist_ok=True)

        self.index_path = self.tools_path / "index.json"
        self.config_manager = config_manager
        self.ollama_client = ollama_client
        self.rag_memory = rag_memory

        # In-memory registry
        self.tools: Dict[str, Tool] = {}

        self._load_tools()

        # Load tools from config if available
        if config_manager:
            self._load_tools_from_config()

        # Index tools in RAG if available
        if rag_memory:
            self._index_tools_in_rag()

    def _load_tools(self):
        """Load tools from disk into memory."""
        if not self.index_path.exists():
            self._save_index()
            return

        try:
            with open(self.index_path, 'r', encoding='utf-8') as f:
                index = json.load(f)

            for tool_id, tool_data in index.items():
                # Load implementation if it's a file reference
                implementation = None
                if "implementation_file" in tool_data.get("metadata", {}):
                    impl_file = self.tools_path / tool_data["metadata"]["implementation_file"]
                    if impl_file.exists():
                        with open(impl_file, 'r', encoding='utf-8') as f:
                            implementation = f.read()

                tool = Tool.from_dict(tool_data, implementation)
                self.tools[tool_id] = tool

            logger.info(f"✓ Loaded {len(self.tools)} tools")

        except Exception as e:
            logger.error(f"Error loading tools: {e}")

    def _save_index(self):
        """Save tools index to disk."""
        try:
            index = {tool_id: tool.to_dict() for tool_id, tool in self.tools.items()}

            with open(self.index_path, 'w', encoding='utf-8') as f:
                json.dump(index, f, indent=2)

        except Exception as e:
            logger.error(f"Error saving tools index: {e}")

    def _load_tools_from_config(self):
        """Load tools defined in configuration."""
        if not self.config_manager:
            return

        tools_config = self.config_manager.get("tools", {})

        for tool_id, tool_def in tools_config.items():
            tool_type_str = tool_def.get("type", "custom")
            try:
                tool_type = ToolType(tool_type_str)
            except ValueError:
                tool_type = ToolType.CUSTOM

            # Handle OpenAPI tools
            if tool_type == ToolType.OPENAPI:
                openapi_config = tool_def.get("openapi", {})
                try:
                    openapi_tool = OpenAPITool(
                        tool_id=tool_id,
                        name=tool_def.get("name", tool_id),
                        spec_path=openapi_config.get("spec_path"),
                        spec_url=openapi_config.get("spec_url"),
                        spec_dict=openapi_config.get("spec_dict"),
                        base_url_override=openapi_config.get("base_url"),
                        auth_config=openapi_config.get("auth")
                    )

                    tool = Tool(
                        tool_id=tool_id,
                        name=tool_def.get("name", tool_id),
                        tool_type=tool_type,
                        description=tool_def.get("description", ""),
                        tags=tool_def.get("tags", []),
                        implementation=openapi_tool,
                        metadata={
                            "from_config": True,
                            "api_base_url": openapi_tool.get_base_url(),
                            "operations_count": len(openapi_tool.operations),
                            "capabilities": openapi_tool.get_capabilities_description(),
                            # Performance/cost attributes
                            "cost_tier": tool_def.get("cost_tier", "medium"),
                            "speed_tier": tool_def.get("speed_tier", "medium"),
                            "quality_tier": tool_def.get("quality_tier", "good"),
                            "max_output_length": tool_def.get("max_output_length", "medium"),
                            # Python code template for using the API
                            "code_template": tool_def.get("code_template", "")
                        }
                    )
                    self.tools[tool_id] = tool
                    logger.info(f"✓ Loaded OpenAPI tool from config: {tool_id} ({len(openapi_tool.operations)} operations)")
                except Exception as e:
                    logger.error(f"Failed to load OpenAPI tool {tool_id}: {e}")
                continue

            # Handle Executable tools (Python analysis/testing tools)
            if tool_type == ToolType.EXECUTABLE:
                executable_config = tool_def.get("executable", {})
                tool = Tool(
                    tool_id=tool_id,
                    name=tool_def.get("name", tool_id),
                    tool_type=tool_type,
                    description=tool_def.get("description", ""),
                    tags=tool_def.get("tags", []),
                    implementation=executable_config,
                    metadata={
                        "from_config": True,
                        "command": executable_config.get("command"),
                        "args": executable_config.get("args", []),
                        "install_command": executable_config.get("install_command")
                    }
                )
                self.tools[tool_id] = tool
                logger.info(f"✓ Loaded executable tool from config: {tool_id} ({executable_config.get('command')})")
                continue

            # Extract LLM configuration if present
            llm_config = tool_def.get("llm", {})

            # Build metadata with performance/cost attributes for planner
            metadata = {
                "from_config": True,
                "llm_model": llm_config.get("model"),
                "llm_endpoint": llm_config.get("endpoint"),
                "system_prompt": llm_config.get("system_prompt"),
                "prompt_template": llm_config.get("prompt_template"),
                # Performance/cost attributes for intelligent tool selection
                "cost_tier": tool_def.get("cost_tier", "medium"),
                "speed_tier": tool_def.get("speed_tier", "medium"),
                "quality_tier": tool_def.get("quality_tier", "good"),
                "max_output_length": tool_def.get("max_output_length", "medium")
            }

            tool = Tool(
                tool_id=tool_id,
                name=tool_def.get("name", tool_id),
                tool_type=tool_type,
                description=tool_def.get("description", ""),
                tags=tool_def.get("tags", []),
                implementation=llm_config if llm_config else None,
                metadata=metadata
            )

            self.tools[tool_id] = tool
            logger.info(f"✓ Loaded tool from config: {tool_id}")

    def _index_tools_in_rag(self):
        """Index all tools in RAG memory for semantic search."""
        if not self.rag_memory:
            return

        try:
            from .rag_memory import ArtifactType

            for tool_id, tool in self.tools.items():
                # Create a comprehensive description for embedding
                tool_content = f"""Tool: {tool.name}
Type: {tool.tool_type.value}
Description: {tool.description}
Tags: {', '.join(tool.tags)}

{tool.to_prompt_format()}"""

                # Store in RAG with type PATTERN (representing a reusable tool pattern)
                self.rag_memory.store_artifact(
                    artifact_id=f"tool_{tool_id}",
                    artifact_type=ArtifactType.PATTERN,
                    name=tool.name,
                    description=tool.description,
                    content=tool_content,
                    tags=["tool", tool.tool_type.value] + tool.tags,
                    metadata={
                        "tool_id": tool_id,
                        "tool_type": tool.tool_type.value,
                        "is_tool": True
                    },
                    auto_embed=True
                )

            logger.info(f"✓ Indexed {len(self.tools)} tools in RAG memory")

        except Exception as e:
            logger.error(f"Error indexing tools in RAG: {e}")

    def invoke_llm_tool(
        self,
        tool_id: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        **template_vars
    ) -> str:
        """
        Invoke an LLM-based tool.

        Args:
            tool_id: Tool identifier
            prompt: Prompt to send to the LLM (or variables for prompt_template)
            system_prompt: Optional system prompt override
            temperature: Sampling temperature
            **template_vars: Variables to format the tool's prompt_template

        Returns:
            LLM response
        """
        tool = self.get_tool(tool_id)

        if not tool:
            logger.error(f"Tool not found: {tool_id}")
            return ""

        if tool.tool_type != ToolType.LLM:
            logger.error(f"Tool {tool_id} is not an LLM tool")
            return ""

        if not self.ollama_client:
            logger.error("OllamaClient not configured")
            return ""

        # Extract LLM configuration
        llm_config = tool.implementation or tool.metadata
        model = llm_config.get("llm_model") or llm_config.get("model", "llama3")
        endpoint = llm_config.get("llm_endpoint") or llm_config.get("endpoint")

        # Use tool's stored system prompt if not overridden
        if system_prompt is None:
            system_prompt = tool.metadata.get("system_prompt")

        # Use tool's prompt template if available
        prompt_template = tool.metadata.get("prompt_template")
        if prompt_template:
            # If template exists, try to format it with provided variables
            # If no variables provided, use prompt as-is for backward compatibility
            if template_vars:
                try:
                    prompt = prompt_template.format(prompt=prompt, **template_vars)
                except KeyError as e:
                    logger.warning(f"Missing template variable {e}, using prompt as-is")
            # Otherwise just use the prompt as-is (backward compatibility)

        # Increment usage counter
        self.increment_usage(tool_id)

        # Log tool invocation
        logger.info(f"Invoking LLM tool '{tool.name}' (model: {model}, endpoint: {endpoint or 'default'})")

        # Invoke the LLM
        response = self.ollama_client.generate(
            model=model,
            prompt=prompt,
            system=system_prompt,
            temperature=temperature,
            endpoint=endpoint
        )

        # Store the actual prompt used in RAG for learning and optimization
        if self.rag_memory and response:
            try:
                from .rag_memory import ArtifactType
                import time

                # Create unique artifact ID for this invocation
                invocation_id = f"invocation_{tool_id}_{int(time.time()*1000)}"

                # Store the prompt/response pair with full context
                self.rag_memory.store_artifact(
                    artifact_id=invocation_id,
                    artifact_type=ArtifactType.PATTERN,
                    name=f"{tool.name} Invocation",
                    description=f"Actual prompt and response for {tool.name}",
                    content=f"SYSTEM PROMPT:\n{system_prompt or 'None'}\n\nPROMPT:\n{prompt}\n\nRESPONSE:\n{response}",
                    tags=["tool_invocation", "prompt", tool_id, model],
                    metadata={
                        "tool_id": tool_id,
                        "tool_name": tool.name,
                        "model": model,
                        "endpoint": endpoint or "default",
                        "system_prompt": system_prompt,
                        "user_prompt": prompt,
                        "temperature": temperature,
                        "response_length": len(response),
                        "template_vars": template_vars
                    },
                    auto_embed=True
                )
                logger.debug(f"Stored prompt/response for {tool_id} in RAG")
            except Exception as e:
                logger.warning(f"Could not store tool invocation in RAG: {e}")

        return response

    def invoke_openapi_tool(
        self,
        tool_id: str,
        operation_id: str,
        parameters: Optional[Dict[str, Any]] = None,
        body: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Invoke an OpenAPI tool operation.

        Args:
            tool_id: The tool identifier
            operation_id: The operation ID from OpenAPI spec
            parameters: Query/path/header parameters
            body: Request body for POST/PUT/PATCH

        Returns:
            Response data as dictionary with status, data, error fields

        Example:
            result = tools_manager.invoke_openapi_tool(
                "github_api",
                "getUserRepos",
                parameters={"username": "octocat"}
            )
            if result["success"]:
                repos = result["data"]
        """
        tool = self.get_tool(tool_id)
        if not tool:
            raise ValueError(f"Tool not found: {tool_id}")

        if tool.tool_type != ToolType.OPENAPI:
            raise ValueError(f"Tool {tool_id} is not an OpenAPI tool (type: {tool.tool_type})")

        openapi_tool: OpenAPITool = tool.implementation
        if not isinstance(openapi_tool, OpenAPITool):
            raise ValueError(f"Tool {tool_id} has invalid OpenAPI implementation")

        # Increment usage counter
        tool.usage_count += 1

        # Invoke the API
        logger.info(f"Invoking OpenAPI tool {tool_id} operation {operation_id}")
        result = openapi_tool.invoke(operation_id, parameters, body)

        # Store invocation in RAG if available
        if self.rag_memory:
            try:
                from .rag_memory import ArtifactType
                import time

                invocation_id = f"api_invocation_{tool_id}_{operation_id}_{int(time.time()*1000)}"

                self.rag_memory.store_artifact(
                    artifact_id=invocation_id,
                    artifact_type=ArtifactType.PATTERN,
                    name=f"{tool.name} API Call",
                    description=f"API invocation: {operation_id}",
                    content=f"OPERATION: {operation_id}\n\nPARAMETERS:\n{json.dumps(parameters, indent=2)}\n\nBODY:\n{json.dumps(body, indent=2)}\n\nRESPONSE:\n{json.dumps(result, indent=2)}",
                    tags=["api_invocation", "openapi", tool_id, operation_id],
                    metadata={
                        "tool_id": tool_id,
                        "tool_name": tool.name,
                        "operation_id": operation_id,
                        "status_code": result.get("status_code"),
                        "success": result.get("success"),
                        "parameters": parameters,
                        "body": body
                    },
                    auto_embed=True
                )
                logger.debug(f"Stored API invocation for {tool_id}/{operation_id} in RAG")
            except Exception as e:
                logger.warning(f"Could not store API invocation in RAG: {e}")

        return result

    def invoke_executable_tool(
        self,
        tool_id: str,
        source_file: str,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        Invoke an executable tool (like pylint, mypy, pytest, etc.)

        Args:
            tool_id: The tool identifier
            source_file: Path to source file to analyze/test
            **kwargs: Additional placeholder values (e.g., test_file, source_module)

        Returns:
            Dictionary with:
                - success: bool (True if command executed successfully)
                - exit_code: int
                - stdout: str
                - stderr: str
                - command: str (full command that was run)

        Example:
            result = tools_manager.invoke_executable_tool(
                "pylint_checker",
                source_file="./nodes/my_func/main.py"
            )
            if result["exit_code"] == 0:
                print(f"Pylint passed: {result['stdout']}")
        """
        tool = self.get_tool(tool_id)
        if not tool:
            raise ValueError(f"Tool not found: {tool_id}")

        if tool.tool_type != ToolType.EXECUTABLE:
            raise ValueError(f"Tool {tool_id} is not an executable tool (type: {tool.tool_type})")

        executable_config = tool.implementation
        if not isinstance(executable_config, dict):
            raise ValueError(f"Tool {tool_id} has invalid executable configuration")

        command = executable_config.get("command")
        args_template = executable_config.get("args", [])
        install_command = executable_config.get("install_command")

        if not command:
            raise ValueError(f"Tool {tool_id} missing command")

        # Build arguments with placeholder substitution
        substitutions = {"source_file": source_file, **kwargs}
        args = []
        for arg in args_template:
            # Replace placeholders like {source_file}, {test_file}, {source_module}
            for key, value in substitutions.items():
                arg = arg.replace(f"{{{key}}}", str(value))
            args.append(arg)

        full_command = [command] + args

        # Increment usage counter
        tool.usage_count += 1

        logger.info(f"Invoking executable tool {tool_id}: {' '.join(full_command)}")

        # Execute the command
        import subprocess
        try:
            result_obj = subprocess.run(
                full_command,
                capture_output=True,
                text=True,
                timeout=60  # 60 second timeout
            )

            result = {
                "success": result_obj.returncode == 0,
                "exit_code": result_obj.returncode,
                "stdout": result_obj.stdout,
                "stderr": result_obj.stderr,
                "command": " ".join(full_command)
            }

            logger.info(f"Tool {tool_id} completed with exit code {result_obj.returncode}")

        except FileNotFoundError:
            # Command not found - provide installation instructions
            result = {
                "success": False,
                "exit_code": 127,
                "stdout": "",
                "stderr": f"Command '{command}' not found. Install with: {install_command}",
                "command": " ".join(full_command)
            }
            logger.warning(f"Tool {tool_id} command not found: {command}")

        except subprocess.TimeoutExpired:
            result = {
                "success": False,
                "exit_code": 124,
                "stdout": "",
                "stderr": f"Command timed out after 60 seconds",
                "command": " ".join(full_command)
            }
            logger.warning(f"Tool {tool_id} timed out")

        except Exception as e:
            result = {
                "success": False,
                "exit_code": 1,
                "stdout": "",
                "stderr": str(e),
                "command": " ".join(full_command)
            }
            logger.error(f"Tool {tool_id} failed: {e}")

        # Store invocation in RAG if available
        if self.rag_memory:
            try:
                from .rag_memory import ArtifactType
                import time

                invocation_id = f"exec_invocation_{tool_id}_{int(time.time()*1000)}"

                self.rag_memory.store_artifact(
                    artifact_id=invocation_id,
                    artifact_type=ArtifactType.PATTERN,
                    name=f"{tool.name} Execution",
                    description=f"Executable tool invocation: {command}",
                    content=f"COMMAND: {result['command']}\n\nSOURCE FILE: {source_file}\n\nEXIT CODE: {result['exit_code']}\n\nSTDOUT:\n{result['stdout']}\n\nSTDERR:\n{result['stderr']}",
                    tags=["executable_invocation", "tool_execution", tool_id, command],
                    metadata={
                        "tool_id": tool_id,
                        "tool_name": tool.name,
                        "command": command,
                        "exit_code": result["exit_code"],
                        "success": result["success"],
                        "source_file": source_file
                    },
                    auto_embed=True
                )
                logger.debug(f"Stored executable invocation for {tool_id} in RAG")
            except Exception as e:
                logger.warning(f"Could not store executable invocation in RAG: {e}")

        return result

    def register_tool(self, tool: Tool) -> Tool:
        """
        Register a Tool object directly.

        Args:
            tool: Tool object to register

        Returns:
            The registered Tool object
        """
        self.tools[tool.tool_id] = tool
        self._save_index()
        logger.info(f"✓ Registered tool: {tool.tool_id} ({tool.tool_type.value})")
        return tool

    def register_function(
        self,
        tool_id: str,
        name: str,
        description: str,
        function: Callable,
        parameters: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None
    ) -> Tool:
        """
        Register a Python function as a tool.

        Args:
            tool_id: Unique identifier
            name: Function name
            description: What the function does
            function: The actual Python function
            parameters: Parameter schema
            tags: Tags for categorization

        Returns:
            Created Tool object
        """
        # Get function source code
        import inspect
        source_code = inspect.getsource(function)

        # Save source code to file
        impl_file = f"{tool_id}.py"
        impl_path = self.tools_path / impl_file

        with open(impl_path, 'w', encoding='utf-8') as f:
            f.write(source_code)

        tool = Tool(
            tool_id=tool_id,
            name=name,
            tool_type=ToolType.FUNCTION,
            description=description,
            tags=tags or ["function"],
            implementation=function,
            parameters=parameters,
            metadata={"implementation_file": impl_file}
        )

        self.tools[tool_id] = tool
        self._save_index()

        logger.info(f"✓ Registered function tool: {tool_id}")
        return tool

    def register_llm(
        self,
        tool_id: str,
        name: str,
        description: str,
        model_name: str,
        system_prompt: str,
        tags: Optional[List[str]] = None
    ) -> Tool:
        """
        Register a specialized LLM as a tool.

        Args:
            tool_id: Unique identifier
            name: LLM name
            description: What the LLM specializes in
            model_name: Ollama model name
            system_prompt: System prompt for the LLM
            tags: Tags for categorization

        Returns:
            Created Tool object
        """
        tool = Tool(
            tool_id=tool_id,
            name=name,
            tool_type=ToolType.LLM,
            description=description,
            tags=tags or ["llm"],
            implementation={"model": model_name, "system_prompt": system_prompt},
            metadata={"model_name": model_name}
        )

        self.tools[tool_id] = tool
        self._save_index()

        logger.info(f"✓ Registered LLM tool: {tool_id}")
        return tool

    def register_workflow(
        self,
        tool_id: str,
        name: str,
        description: str,
        steps: List[Dict[str, Any]],
        tags: Optional[List[str]] = None
    ) -> Tool:
        """
        Register a workflow as a tool.

        Args:
            tool_id: Unique identifier
            name: Workflow name
            description: What the workflow does
            steps: List of workflow steps
            tags: Tags for categorization

        Returns:
            Created Tool object
        """
        # Save workflow definition
        workflow_file = f"{tool_id}_workflow.json"
        workflow_path = self.tools_path / workflow_file

        with open(workflow_path, 'w', encoding='utf-8') as f:
            json.dump({"steps": steps}, f, indent=2)

        tool = Tool(
            tool_id=tool_id,
            name=name,
            tool_type=ToolType.WORKFLOW,
            description=description,
            tags=tags or ["workflow"],
            implementation=steps,
            metadata={"workflow_file": workflow_file}
        )

        self.tools[tool_id] = tool
        self._save_index()

        logger.info(f"✓ Registered workflow tool: {tool_id}")
        return tool

    def register_community(
        self,
        tool_id: str,
        name: str,
        description: str,
        sub_workflows: List[str],
        coordination_strategy: str,
        tags: Optional[List[str]] = None
    ) -> Tool:
        """
        Register a community (sub-workflow system) as a tool.

        Args:
            tool_id: Unique identifier
            name: Community name
            description: What the community does
            sub_workflows: List of sub-workflow IDs
            coordination_strategy: How sub-workflows are coordinated
            tags: Tags for categorization

        Returns:
            Created Tool object
        """
        tool = Tool(
            tool_id=tool_id,
            name=name,
            tool_type=ToolType.COMMUNITY,
            description=description,
            tags=tags or ["community"],
            implementation={
                "sub_workflows": sub_workflows,
                "coordination_strategy": coordination_strategy
            },
            metadata={"sub_workflow_count": len(sub_workflows)}
        )

        self.tools[tool_id] = tool
        self._save_index()

        logger.info(f"✓ Registered community tool: {tool_id}")
        return tool

    def get_tool(self, tool_id: str) -> Optional[Tool]:
        """
        Get a tool by ID.

        Args:
            tool_id: Tool identifier

        Returns:
            Tool object or None
        """
        return self.tools.get(tool_id)

    def find_by_tags(self, tags: List[str]) -> List[Tool]:
        """
        Find tools by tags.

        Args:
            tags: List of tags to search for

        Returns:
            List of matching tools
        """
        matches = []
        search_tags = set(tags)

        for tool in self.tools.values():
            tool_tags = set(tool.tags)
            if tool_tags & search_tags:  # Intersection
                matches.append(tool)

        return sorted(matches, key=lambda t: t.usage_count, reverse=True)

    def find_by_type(self, tool_type: ToolType) -> List[Tool]:
        """
        Find tools by type.

        Args:
            tool_type: Type of tool

        Returns:
            List of matching tools
        """
        return [tool for tool in self.tools.values() if tool.tool_type == tool_type]

    def search(self, query: str, top_k: int = 5, use_rag: bool = True) -> List[Tool]:
        """
        Search tools using semantic search (RAG) or keyword matching.

        Args:
            query: Search query
            top_k: Maximum number of results to return
            use_rag: Whether to use RAG semantic search (fallback to keyword if unavailable)

        Returns:
            List of matching tools
        """
        # Try RAG semantic search first if available
        if use_rag and self.rag_memory:
            try:
                from .rag_memory import ArtifactType

                # Search for tools using semantic similarity
                results = self.rag_memory.find_similar(
                    query=query,
                    artifact_type=ArtifactType.PATTERN,
                    top_k=top_k * 2  # Get more results to filter
                )

                # Filter for actual tools and extract Tool objects
                # HIERARCHICAL PRIORITY (highest to lowest):
                # 1. Complete WORKFLOW nodes (pre-generated, tested, working solutions)
                # 2. COMMUNITY/committee tools (composite workflows)
                # 3. Specialized LLM tools from config
                # 4. General fallback tools

                workflows = []      # Priority 1: Complete workflow nodes
                communities = []    # Priority 2: Composite workflows
                specialized = []    # Priority 3: Specialized LLM tools
                general = []        # Priority 4: General tools

                seen_tool_ids = set()  # Deduplicate

                for artifact, similarity in results:
                    if artifact.metadata.get("is_tool"):
                        tool_id = artifact.metadata.get("tool_id")
                        if tool_id and tool_id in self.tools and tool_id not in seen_tool_ids:
                            tool = self.tools[tool_id]
                            seen_tool_ids.add(tool_id)

                            # Categorize by priority
                            if tool.tool_type == ToolType.WORKFLOW:
                                workflows.append((tool, similarity))
                            elif tool.tool_type == ToolType.COMMUNITY:
                                communities.append((tool, similarity))
                            elif tool.tool_type == ToolType.LLM:
                                if 'general' in tool.tool_id.lower() or 'fallback' in tool.tags:
                                    general.append((tool, similarity))
                                else:
                                    specialized.append((tool, similarity))
                            else:
                                general.append((tool, similarity))

                # MULTI-DIMENSIONAL FITNESS FUNCTION
                # Goal: Minimum effort for maximum fitness
                # Factors: semantic similarity, speed, cost, quality, past success

                def calculate_fitness(tool, similarity):
                    """
                    Calculate overall fitness score for a tool.
                    Higher score = better choice for this task.

                    Factors:
                    - Semantic similarity (0-1): How well it matches the task
                    - Speed: Fast tools get bonus points
                    - Cost: Cheap tools get bonus points
                    - Quality: High quality tools get bonus
                    - Success rate: Tools with good track record get bonus
                    - Effort: Reusing existing code requires less effort
                    """
                    fitness = similarity * 100  # Base score from semantic match (0-100)

                    metadata = tool.metadata or {}

                    # Speed bonus (faster = better)
                    speed_tier = metadata.get('speed_tier', 'medium')
                    if speed_tier == 'very-fast':
                        fitness += 20
                    elif speed_tier == 'fast':
                        fitness += 10
                    elif speed_tier == 'slow':
                        fitness -= 10
                    elif speed_tier == 'very-slow':
                        fitness -= 20

                    # Cost bonus (cheaper = better)
                    cost_tier = metadata.get('cost_tier', 'medium')
                    if cost_tier == 'free':
                        fitness += 15
                    elif cost_tier == 'low':
                        fitness += 10
                    elif cost_tier == 'high':
                        fitness -= 10
                    elif cost_tier == 'very-high':
                        fitness -= 15

                    # Quality bonus
                    quality_tier = metadata.get('quality_tier', 'good')
                    if quality_tier == 'excellent':
                        fitness += 15
                    elif quality_tier == 'very-good':
                        fitness += 10
                    elif quality_tier == 'poor':
                        fitness -= 15

                    # Success rate bonus (from past runs)
                    quality_score = metadata.get('quality_score', 0)
                    if quality_score > 0:
                        fitness += quality_score * 10  # 0-10 bonus points

                    # Performance metrics bonus
                    latency_ms = metadata.get('latency_ms', 0)
                    if latency_ms > 0:
                        if latency_ms < 100:
                            fitness += 15  # Very fast execution
                        elif latency_ms < 500:
                            fitness += 10  # Fast execution
                        elif latency_ms > 5000:
                            fitness -= 10  # Slow execution

                    # Effort bonus: Reusing existing workflow requires less effort
                    if tool.tool_type == ToolType.WORKFLOW:
                        if similarity >= 0.90:
                            fitness += 30  # Exact match, minimal effort
                        elif similarity >= 0.70:
                            fitness += 15  # Template modification, moderate effort
                        # Below 0.70: no effort bonus, might be more work to adapt

                    return fitness

                # Calculate fitness for all tools
                workflows_with_fitness = [(t, s, calculate_fitness(t, s)) for t, s in workflows]
                communities_with_fitness = [(t, s, calculate_fitness(t, s)) for t, s in communities]
                specialized_with_fitness = [(t, s, calculate_fitness(t, s)) for t, s in specialized]
                general_with_fitness = [(t, s, calculate_fitness(t, s)) for t, s in general]

                # Combine all candidates
                all_candidates = (
                    workflows_with_fitness +
                    communities_with_fitness +
                    specialized_with_fitness +
                    general_with_fitness
                )

                # Sort by FITNESS score (highest first), not just similarity
                all_candidates.sort(key=lambda x: x[2], reverse=True)

                # Filter by minimum thresholds
                MINIMUM_SIMILARITY = 0.50  # Don't use anything below 50% similarity
                MINIMUM_FITNESS = 40        # Don't use tools with very low fitness

                usable_candidates = [
                    (tool, sim, fitness) for tool, sim, fitness in all_candidates
                    if sim >= MINIMUM_SIMILARITY or fitness >= MINIMUM_FITNESS
                ]

                # Extract just the tools in fitness order
                tool_matches = [tool for tool, _, _ in usable_candidates]

                # Log top choice with reasoning
                if usable_candidates:
                    top_tool, top_sim, top_fitness = usable_candidates[0]
                    logger.info(f"Top choice: {top_tool.name} (similarity: {top_sim:.1%}, fitness: {top_fitness:.0f})")


                # If no high-level workflows found, ensure relevant config tools are included
                query_lower = query.lower()

                if len(workflows) == 0:  # Only add config tools if no workflows exist
                    # For writing/story tasks, include long_form_writer
                    if any(keyword in query_lower for keyword in ['story', 'novel', 'book', 'funny', 'creative']):
                        if 'long_form_writer' in self.tools and 'long_form_writer' not in seen_tool_ids:
                            # Add after communities but before other specialized tools
                            insert_pos = len([t for t, _ in workflows]) + len([t for t, _ in communities])
                            tool_matches.insert(insert_pos, self.tools['long_form_writer'])
                            seen_tool_ids.add('long_form_writer')

                    # For technical writing, include technical_writer
                    if 'technical' in query_lower and 'article' in query_lower:
                        if 'technical_writer' in self.tools and 'technical_writer' not in seen_tool_ids:
                            insert_pos = len([t for t, _ in workflows]) + len([t for t, _ in communities])
                            tool_matches.insert(insert_pos, self.tools['technical_writer'])
                            seen_tool_ids.add('technical_writer')

                # Return top_k unique tools in priority order
                return tool_matches[:top_k]

            except Exception as e:
                logger.warning(f"RAG search failed, falling back to keyword search: {e}")

        # Fallback to keyword-based search
        query_lower = query.lower()
        matches = []

        for tool in self.tools.values():
            # Search in name, description, tags
            if (query_lower in tool.name.lower() or
                query_lower in tool.description.lower() or
                any(query_lower in tag.lower() for tag in tool.tags)):
                matches.append(tool)

        return sorted(matches, key=lambda t: t.usage_count, reverse=True)[:top_k]

    def get_tools_for_prompt(
        self,
        task_description: str,
        max_tools: int = 5,
        filter_type: Optional[ToolType] = None
    ) -> str:
        """
        Get relevant tools formatted for inclusion in a prompt using RAG semantic search.

        Args:
            task_description: Description of the task
            max_tools: Maximum number of tools to include
            filter_type: Optional tool type filter (e.g., ToolType.LLM for code generation)

        Returns:
            Formatted string with tool descriptions
        """
        # Use RAG-powered semantic search
        relevant_tools = self.search(task_description, top_k=max_tools, use_rag=True)

        # Apply type filter if specified
        if filter_type:
            relevant_tools = [t for t in relevant_tools if t.tool_type == filter_type][:max_tools]

        if not relevant_tools:
            return "No specific tools available for this task."

        tools_text = "Available Tools:\n\n"
        for i, tool in enumerate(relevant_tools, 1):
            tools_text += f"{i}. {tool.to_prompt_format()}\n"

        return tools_text

    def get_best_llm_for_task(self, task_description: str, min_similarity: float = 0.6) -> Optional[Tool]:
        """
        Get the best LLM tool for a given task using fitness-based RAG semantic search.
        Falls back to 'general' tool if no good matches found.

        IMPORTANT: NEVER use the wrong model for the wrong job:
        - Code tasks ONLY get code-specialized tools (NO creative writing tools)
        - Writing tasks ONLY get writing tools (NO code tools)
        - ONLY fall back to general if nothing close enough (similarity < 0.6)

        Args:
            task_description: Description of the task
            min_similarity: Minimum similarity threshold (0.0-1.0, default 0.6)

        Returns:
            Best matching tool (by fitness), 'general' fallback tool, or None
        """
        task_lower = task_description.lower()

        # Detect if this is a code generation task
        code_keywords = ['code', 'function', 'class', 'script', 'program', 'algorithm', 'implement',
                        'add', 'multiply', 'calculate', 'compute', 'parse', 'process', 'validate',
                        'fibonacci', 'prime', 'sort', 'search', 'sum', 'subtract', 'divide']
        is_code_task = any(keyword in task_lower for keyword in code_keywords)

        # Detect if this is a creative writing task
        writing_keywords = ['write', 'story', 'article', 'novel', 'essay', 'blog', 'content',
                           'haiku', 'poem', 'narrative', 'chapter', 'book', 'novella', 'tale']
        is_writing_task = any(keyword in task_lower for keyword in writing_keywords) and not is_code_task

        # Get fitness-ranked tools from search (already sorted by fitness score)
        # This returns ALL tool types sorted by multi-dimensional fitness
        all_tools = self.search(task_description, top_k=10, use_rag=True)

        # Filter to ONLY LLM tools (exclude workflows/communities for this method)
        llm_tools = [t for t in all_tools if t.tool_type == ToolType.LLM]

        # CRITICAL: Apply task-type filtering to prevent wrong tool for wrong job
        if is_code_task:
            # For code tasks, EXCLUDE ALL creative writing tools
            excluded_keywords = ['long_form_writer', 'long-form', 'content writer', 'creative',
                                'writer', 'story', 'article', 'novel', 'essay']
            llm_tools = [t for t in llm_tools
                        if not any(excl in t.tool_id.lower() or excl in t.name.lower() or excl in t.description.lower()
                                  for excl in excluded_keywords)]

            logger.info(f"Code task detected, filtered to {len(llm_tools)} code-appropriate tools")

        elif is_writing_task:
            # For writing tasks, EXCLUDE code generation tools
            excluded_keywords = ['code', 'coder', 'generator', 'compiler', 'parser']
            llm_tools = [t for t in llm_tools
                        if not any(excl in t.tool_id.lower() or excl in t.name.lower() or excl in t.description.lower()
                                  for excl in excluded_keywords)]

            logger.info(f"Writing task detected, filtered to {len(llm_tools)} writing-appropriate tools")

        # Check if we have a good match above minimum similarity threshold
        # The search() method already uses fitness, so the first result is the best by fitness
        if llm_tools:
            best_tool = llm_tools[0]

            # Get similarity score if available in metadata
            # Note: search() returns tools sorted by fitness, but doesn't expose similarity score
            # For now, trust the fitness-based ranking
            logger.info(f"Selected best tool: {best_tool.name} (fitness-ranked #1)")
            return best_tool

        # No appropriate specialized tool found - look for 'general' fallback tool
        if 'general' in self.tools:
            logger.info(f"No specialized tool found for '{task_description}', using general fallback")
            return self.tools['general']

        # No tools found at all
        logger.warning(f"No tools available for task: {task_description}")
        return None

    def compose_novel_workflow(self, task_description: str) -> Optional[Dict[str, Any]]:
        """
        Intelligently compose a new workflow for novel tasks by analyzing requirements
        and combining available models/tools based on their capabilities.

        Examples:
        - "write a romance novel" -> Use mistral-nemo (large context) + summarizer for chapters
        - "analyze large dataset" -> Use chunking + fast models + aggregator
        - "translate technical docs" -> Use nmt_translator + quality_checker + technical_writer

        Args:
            task_description: Description of the novel task

        Returns:
            Workflow composition plan with tool recommendations, or None if can't compose
        """
        task_lower = task_description.lower()

        # Analyze task characteristics
        characteristics = {
            "needs_large_context": any(word in task_lower for word in [
                'novel', 'book', 'story', 'long', 'chapter', 'document', 'essay', 'article'
            ]),
            "needs_creativity": any(word in task_lower for word in [
                'creative', 'novel', 'story', 'poem', 'fiction', 'write'
            ]),
            "needs_speed": any(word in task_lower for word in [
                'quick', 'fast', 'rapid', 'immediate'
            ]),
            "needs_summarization": any(word in task_lower for word in [
                'novel', 'book', 'long', 'chapter', 'summarize', 'condense'
            ]),
            "needs_translation": any(word in task_lower for word in [
                'translate', 'translation', 'language', 'multilingual'
            ]),
            "needs_iteration": any(word in task_lower for word in [
                'iterative', 'refine', 'improve', 'optimize', 'chapter', 'section'
            ]),
            "needs_quality_check": any(word in task_lower for word in [
                'quality', 'validate', 'check', 'verify', 'review'
            ])
        }

        # Get all available tools with their metadata
        available_tools = self.list_all()

        # Rank tools by suitability for this task
        def score_tool(tool: Tool) -> float:
            score = 0.0
            metadata = tool.metadata or {}

            # Context window scoring
            if characteristics["needs_large_context"]:
                if 'mistral-nemo' in str(metadata.get('llm_model', '')):
                    score += 10.0  # 128K context!
                elif 'qwen' in str(metadata.get('llm_model', '')):
                    score += 5.0   # 32K context
                elif metadata.get('max_output_length') == 'very-long':
                    score += 3.0

            # Speed scoring
            if characteristics["needs_speed"]:
                speed_tier = metadata.get('speed_tier', 'medium')
                if speed_tier == 'very-fast':
                    score += 5.0
                elif speed_tier == 'fast':
                    score += 3.0

            # Cost scoring (prefer cheap for iterative tasks)
            if characteristics["needs_iteration"]:
                cost_tier = metadata.get('cost_tier', 'medium')
                if cost_tier == 'low':
                    score += 3.0

            # Tag matching
            tool_tags_str = ' '.join(tool.tags).lower()
            if characteristics["needs_summarization"] and 'summariz' in tool_tags_str:
                score += 8.0
            if characteristics["needs_translation"] and 'translat' in tool_tags_str:
                score += 8.0
            if characteristics["needs_quality_check"] and any(word in tool_tags_str for word in ['quality', 'check', 'validat']):
                score += 5.0

            return score

        # Rank and select tools
        ranked_tools = sorted(available_tools, key=score_tool, reverse=True)
        selected_tools = [t for t in ranked_tools if score_tool(t) > 0][:5]

        if not selected_tools:
            return None

        # Build workflow composition plan
        workflow_plan = {
            "task_description": task_description,
            "characteristics": {k: v for k, v in characteristics.items() if v},
            "recommended_tools": [],
            "workflow_steps": [],
            "rationale": []
        }

        # Add tools to plan
        for tool in selected_tools:
            metadata = tool.metadata or {}
            workflow_plan["recommended_tools"].append({
                "tool_id": tool.tool_id,
                "name": tool.name,
                "type": tool.tool_type.value,
                "model": metadata.get('llm_model'),
                "cost_tier": metadata.get('cost_tier'),
                "speed_tier": metadata.get('speed_tier'),
                "quality_tier": metadata.get('quality_tier'),
                "tags": tool.tags,
                "score": score_tool(tool)
            })

        # Build workflow steps based on characteristics
        if characteristics["needs_large_context"] and characteristics["needs_summarization"]:
            # Example: Romance novel writing
            workflow_plan["workflow_steps"] = [
                {
                    "step": 1,
                    "action": "Initialize context",
                    "tool": next((t["tool_id"] for t in workflow_plan["recommended_tools"] if 'mistral-nemo' in str(t.get('model', ''))), None),
                    "description": "Start with empty context for story continuity"
                },
                {
                    "step": 2,
                    "action": "Generate content iteratively",
                    "tool": next((t["tool_id"] for t in workflow_plan["recommended_tools"] if 'mistral-nemo' in str(t.get('model', ''))), None),
                    "description": "Generate each chapter/section using large context window"
                },
                {
                    "step": 3,
                    "action": "Summarize for context",
                    "tool": next((t["tool_id"] for t in workflow_plan["recommended_tools"] if 'summariz' in ' '.join(t.get('tags', []))), None),
                    "description": "Summarize previous content to maintain continuity in limited context"
                },
                {
                    "step": 4,
                    "action": "Append to running summary",
                    "description": "Add new summary to master summary for next iteration"
                },
                {
                    "step": 5,
                    "action": "Repeat steps 2-4",
                    "description": "Continue until complete"
                }
            ]
            workflow_plan["rationale"].append(
                "Large context task detected: Using mistral-nemo (128K context) for generation"
            )
            workflow_plan["rationale"].append(
                "Iterative summarization: Each chapter summarized and added to context for next chapter"
            )

        elif characteristics["needs_translation"]:
            # Translation workflow
            translator_tool = next((t for t in workflow_plan["recommended_tools"] if 'translat' in ' '.join(t.get('tags', []))), None)
            quality_tool = next((t for t in workflow_plan["recommended_tools"] if 'quality' in ' '.join(t.get('tags', [])) or 'check' in ' '.join(t.get('tags', []))), None)

            workflow_plan["workflow_steps"] = [
                {
                    "step": 1,
                    "action": "Translate content",
                    "tool": translator_tool["tool_id"] if translator_tool else None,
                    "description": "Use fast translation service"
                },
                {
                    "step": 2,
                    "action": "Quality check",
                    "tool": quality_tool["tool_id"] if quality_tool else None,
                    "description": "Validate translation for errors (repeated chars, encoding issues)"
                },
                {
                    "step": 3,
                    "action": "Retry if needed",
                    "description": "Re-translate problematic sections if quality check fails"
                }
            ]
            workflow_plan["rationale"].append(
                "Translation workflow: Fast translator + quality validation"
            )

        logger.info(f"✓ Composed novel workflow with {len(selected_tools)} tools for: {task_description[:50]}...")
        return workflow_plan

    def increment_usage(self, tool_id: str):
        """Increment usage counter for a tool."""
        if tool_id in self.tools:
            self.tools[tool_id].usage_count += 1
            self._save_index()

    def list_all(self) -> List[Tool]:
        """Get all tools."""
        return list(self.tools.values())

    def get_all_tools(self) -> List[Tool]:
        """Get all tools (alias for list_all)."""
        return self.list_all()

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the tools registry.

        Returns:
            Statistics dictionary
        """
        type_counts = {}
        for tool in self.tools.values():
            type_name = tool.tool_type.value
            type_counts[type_name] = type_counts.get(type_name, 0) + 1

        # Get tag distribution
        tag_counts = {}
        for tool in self.tools.values():
            for tag in tool.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        # Most used tools
        most_used = sorted(self.tools.values(), key=lambda t: t.usage_count, reverse=True)[:5]

        return {
            "total_tools": len(self.tools),
            "by_type": type_counts,
            "tag_distribution": tag_counts,
            "most_used": [{"id": t.tool_id, "name": t.name, "usage": t.usage_count} for t in most_used]
        }

    def delete_tool(self, tool_id: str) -> bool:
        """
        Delete a tool from the registry.

        Args:
            tool_id: Tool identifier

        Returns:
            True if deleted successfully
        """
        if tool_id not in self.tools:
            return False

        tool = self.tools[tool_id]

        # Delete implementation file if it exists
        if "implementation_file" in tool.metadata:
            impl_file = self.tools_path / tool.metadata["implementation_file"]
            if impl_file.exists():
                impl_file.unlink()

        # Remove from registry
        del self.tools[tool_id]
        self._save_index()

        logger.info(f"✓ Deleted tool: {tool_id}")
        return True
