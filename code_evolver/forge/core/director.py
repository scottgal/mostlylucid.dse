"""
Forge Director - Orchestrates tool discovery, generation, validation, and execution.

The Director Shell coordinates:
- Intent analysis and decomposition
- Tool discovery via RAG registry
- Fallback tool generation
- Validation pipeline execution
- Runtime execution
- Metrics collection and registry updates
"""
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, field, asdict
from pathlib import Path

# Import existing systems
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.rag_memory import RAGMemory
from src.tools_manager import ToolsManager
from src.llm_client_factory import LLMClientFactory

from .registry import ForgeRegistry, ToolManifest
from .runtime import ForgeRuntime
from .validator import ValidationCouncil
from .consensus import ConsensusEngine

logger = logging.getLogger(__name__)


@dataclass
class IntentRequest:
    """Request for tool orchestration."""
    intent: str
    context_docs: Optional[List[str]] = None
    constraints: Optional[Dict[str, Any]] = None
    preferences: Optional[Dict[str, str]] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


@dataclass
class ExecutionResult:
    """Result from tool execution."""
    success: bool
    tool_id: str
    version: str
    result: Any
    provenance: Dict[str, Any]
    metrics: Dict[str, Any]
    errors: Optional[List[str]] = None


class ForgeDirector:
    """
    Forge Director - Central orchestrator for tool lifecycle.

    Responsibilities:
    1. Analyze intents and decompose into requirements
    2. Discover tools via RAG-backed registry
    3. Generate tools when gaps exist
    4. Coordinate validation pipeline
    5. Execute tools via runtime
    6. Collect metrics and update registry
    """

    def __init__(
        self,
        registry: ForgeRegistry,
        runtime: ForgeRuntime,
        validator: ValidationCouncil,
        consensus: ConsensusEngine,
        llm_client: Any,
        config: Dict[str, Any]
    ):
        """
        Initialize forge director.

        Args:
            registry: Forge registry for tool discovery
            runtime: Tool runtime for execution
            validator: Validation council for quality checks
            consensus: Consensus engine for scoring
            llm_client: LLM client for generation
            config: Configuration dictionary
        """
        self.registry = registry
        self.runtime = runtime
        self.validator = validator
        self.consensus = consensus
        self.llm_client = llm_client
        self.config = config

        logger.info("ForgeDirector initialized")

    def submit_intent(self, request: IntentRequest) -> ExecutionResult:
        """
        Process intent and execute appropriate tool(s).

        Workflow:
        1. Discover existing tools
        2. Generate if needed
        3. Validate tool
        4. Execute tool
        5. Update metrics

        Args:
            request: Intent request with constraints

        Returns:
            Execution result
        """
        logger.info(f"Processing intent: {request.intent}")

        # Step 1: Discover tools
        discovery_result = self._discover_tools(request)

        if discovery_result['best_tool']:
            # Use existing tool
            tool = discovery_result['best_tool']
            logger.info(f"Using existing tool: {tool['tool_id']} v{tool['version']}")
        else:
            # Step 2: Generate new tool
            logger.info("No suitable tool found, generating new tool")
            tool = self._generate_tool(request)

            if not tool:
                return ExecutionResult(
                    success=False,
                    tool_id="",
                    version="",
                    result=None,
                    provenance={},
                    metrics={},
                    errors=["Failed to generate tool"]
                )

            # Step 3: Validate new tool
            validation_result = self.validator.validate_tool(
                tool_id=tool['tool_id'],
                version=tool['version']
            )

            if not validation_result['success']:
                return ExecutionResult(
                    success=False,
                    tool_id=tool['tool_id'],
                    version=tool['version'],
                    result=None,
                    provenance={},
                    metrics={},
                    errors=validation_result.get('errors', [])
                )

        # Step 4: Execute tool
        execution_result = self._execute_tool(tool, request)

        # Step 5: Update metrics and consensus
        if execution_result.success:
            self._update_metrics(execution_result)

        return execution_result

    def _discover_tools(self, request: IntentRequest) -> Dict[str, Any]:
        """
        Discover tools matching the intent.

        Args:
            request: Intent request

        Returns:
            Discovery result with best_tool and alternatives
        """
        # Extract capability from intent using LLM
        capability = self._extract_capability(request.intent)

        # Query registry
        return self.registry.query_tools(
            capability=capability,
            constraints=request.constraints,
            context_tags=self._extract_tags(request.intent)
        )

    def _extract_capability(self, intent: str) -> str:
        """Extract capability requirement from intent."""
        # Use LLM to parse intent
        prompt = f"""Extract the primary capability from this intent:
Intent: {intent}

Respond with just the capability name (e.g., "summarize_pdf", "translate_text", "generate_code").
"""
        try:
            response = self.llm_client.generate(
                model=self.config.get('capability_extraction_model', 'base'),
                prompt=prompt,
                temperature=0.1
            )
            capability = response.strip().lower().replace(' ', '_')
            return capability
        except Exception as e:
            logger.error(f"Failed to extract capability: {e}")
            return "unknown_capability"

    def _extract_tags(self, intent: str) -> List[str]:
        """Extract relevant tags from intent."""
        # Simple keyword extraction
        tags = []
        keywords = ['finance', 'security', 'data', 'api', 'translation', 'summarization']
        intent_lower = intent.lower()

        for keyword in keywords:
            if keyword in intent_lower:
                tags.append(keyword)

        return tags

    def _generate_tool(self, request: IntentRequest) -> Optional[Dict[str, Any]]:
        """
        Generate a new tool for the intent.

        Args:
            request: Intent request

        Returns:
            Tool metadata or None
        """
        logger.info(f"Generating tool for intent: {request.intent}")

        # Use LLM to generate tool specification
        prompt = f"""Generate an MCP tool specification for the following intent:

Intent: {request.intent}
Constraints: {json.dumps(request.constraints or {}, indent=2)}
Preferences: {json.dumps(request.preferences or {}, indent=2)}

Generate a tool manifest in YAML format following the forge specification.
Include:
- tool_id, version, name, type, description
- capabilities and interfaces
- basic test cases
- estimated metrics

Respond with valid YAML only.
"""

        try:
            response = self.llm_client.generate(
                model=self.config.get('generation_model', 'powerful'),
                prompt=prompt,
                temperature=0.7
            )

            # Parse YAML and create manifest
            import yaml
            manifest_data = yaml.safe_load(response)

            # Add forge metadata
            manifest_data['origin'] = {
                'author': 'system',
                'source_model': self.config.get('generation_model', 'powerful'),
                'created_at': datetime.utcnow().isoformat() + "Z"
            }

            manifest_data['lineage'] = {
                'ancestor_tool_id': None,
                'mutation_reason': 'initial_generation',
                'commits': []
            }

            manifest_data['trust'] = {
                'level': 'experimental',
                'validation_score': 0.0,
                'risk_score': 1.0
            }

            # Create manifest object
            manifest = ToolManifest.from_dict(manifest_data)

            # Register in forge registry
            self.registry.register_tool_manifest(manifest)

            return {
                'tool_id': manifest.tool_id,
                'version': manifest.version
            }

        except Exception as e:
            logger.error(f"Failed to generate tool: {e}")
            return None

    def _execute_tool(self, tool: Dict[str, Any], request: IntentRequest) -> ExecutionResult:
        """
        Execute tool via runtime.

        Args:
            tool: Tool metadata
            request: Original request

        Returns:
            Execution result
        """
        try:
            # Get manifest
            manifest = self.registry.get_tool_manifest(tool['tool_id'], tool['version'])

            if not manifest:
                return ExecutionResult(
                    success=False,
                    tool_id=tool['tool_id'],
                    version=tool['version'],
                    result=None,
                    provenance={},
                    metrics={},
                    errors=["Tool manifest not found"]
                )

            # Prepare input from intent
            input_data = self._prepare_input(request.intent, manifest)

            # Execute via runtime
            result = self.runtime.execute(
                tool_id=tool['tool_id'],
                version=tool['version'],
                input_data=input_data,
                sandbox_config={
                    'network': 'restricted',
                    'fs': 'readonly'
                }
            )

            return ExecutionResult(
                success=result['success'],
                tool_id=tool['tool_id'],
                version=tool['version'],
                result=result.get('result'),
                provenance=result.get('provenance', {}),
                metrics=result.get('metrics', {}),
                errors=result.get('errors')
            )

        except Exception as e:
            logger.error(f"Failed to execute tool: {e}")
            return ExecutionResult(
                success=False,
                tool_id=tool['tool_id'],
                version=tool['version'],
                result=None,
                provenance={},
                metrics={},
                errors=[str(e)]
            )

    def _prepare_input(self, intent: str, manifest: ToolManifest) -> Dict[str, Any]:
        """Prepare input data from intent."""
        # Use LLM to extract parameters
        prompt = f"""Extract parameters for this tool from the intent:

Intent: {intent}

Tool capabilities: {json.dumps([c['name'] for c in manifest.capabilities], indent=2)}

Respond with JSON object mapping parameter names to values.
"""

        try:
            response = self.llm_client.generate(
                model=self.config.get('parameter_extraction_model', 'base'),
                prompt=prompt,
                temperature=0.1
            )
            return json.loads(response)
        except Exception as e:
            logger.error(f"Failed to extract parameters: {e}")
            return {'intent': intent}

    def _update_metrics(self, result: ExecutionResult):
        """Update tool metrics and consensus scores."""
        try:
            # Update consensus engine
            self.consensus.record_execution(
                tool_id=result.tool_id,
                version=result.version,
                metrics=result.metrics,
                success=result.success
            )

            # Update manifest metrics
            manifest = self.registry.get_tool_manifest(result.tool_id, result.version)
            if manifest:
                if 'latest' not in manifest.metrics:
                    manifest.metrics['latest'] = {}

                manifest.metrics['latest'].update(result.metrics)
                self.registry.register_tool_manifest(manifest)

            logger.info(f"Updated metrics for {result.tool_id} v{result.version}")

        except Exception as e:
            logger.error(f"Failed to update metrics: {e}")
