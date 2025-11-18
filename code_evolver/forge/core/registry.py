"""
Forge Registry - Tool manifest storage and RAG-backed retrieval.

Extends the existing RAG memory system with forge-specific capabilities:
- Tool manifest storage with lineage tracking
- Spec, test, and metrics management
- Semantic search with constraint filtering
- Trust level and validation scoring
"""
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, field, asdict
import yaml

# Import existing systems
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.rag_memory import RAGMemory, ArtifactType
from src.tools_manager import ToolsManager, ToolType

logger = logging.getLogger(__name__)


@dataclass
class ToolManifest:
    """Tool manifest following the forge specification."""
    tool_id: str
    version: str
    name: str
    type: str
    description: str
    origin: Dict[str, Any]
    lineage: Dict[str, Any]
    mcp: Optional[Dict[str, Any]] = None
    capabilities: List[Dict[str, Any]] = field(default_factory=list)
    interfaces: List[Dict[str, Any]] = field(default_factory=list)
    specs: Dict[str, str] = field(default_factory=dict)
    tests: Dict[str, str] = field(default_factory=dict)
    security: Dict[str, Any] = field(default_factory=dict)
    trust: Dict[str, Any] = field(default_factory=dict)
    optimization: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    embeddings: Dict[str, Any] = field(default_factory=dict)
    usage_notes_ref: Optional[str] = None
    examples: List[Dict[str, Any]] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'ToolManifest':
        """Create from dictionary."""
        return ToolManifest(**data)

    def to_yaml(self) -> str:
        """Export to YAML format."""
        return yaml.dump(self.to_dict(), sort_keys=False, default_flow_style=False)


@dataclass
class ConsensusScore:
    """Consensus scoring record for a tool."""
    tool_id: str
    version: str
    scores: Dict[str, float]
    weight: float
    evaluators: List[Dict[str, Any]]
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class ForgeRegistry:
    """
    Forge Registry - Extends RAG memory with forge-specific capabilities.

    Provides:
    - Tool manifest storage and retrieval
    - Lineage tracking
    - Consensus scoring
    - Constraint-based filtering
    - Trust level management
    """

    def __init__(
        self,
        rag_memory: RAGMemory,
        tools_manager: ToolsManager,
        manifest_dir: Optional[Path] = None
    ):
        """
        Initialize forge registry.

        Args:
            rag_memory: Existing RAG memory system
            tools_manager: Existing tools manager
            manifest_dir: Directory for storing tool manifests
        """
        self.rag_memory = rag_memory
        self.tools_manager = tools_manager
        self.manifest_dir = manifest_dir or Path("code_evolver/forge/data/manifests")
        self.manifest_dir.mkdir(parents=True, exist_ok=True)

        # In-memory cache for fast lookups
        self._manifest_cache: Dict[str, ToolManifest] = {}
        self._consensus_cache: Dict[str, ConsensusScore] = {}

        logger.info(f"ForgeRegistry initialized with manifest_dir: {self.manifest_dir}")

    def register_tool_manifest(self, manifest: ToolManifest) -> bool:
        """
        Register a tool manifest in the forge registry.

        Args:
            manifest: Tool manifest to register

        Returns:
            Success status
        """
        try:
            # Save manifest to disk
            manifest_path = self.manifest_dir / f"{manifest.tool_id}_v{manifest.version}.yaml"
            with open(manifest_path, 'w') as f:
                f.write(manifest.to_yaml())

            # Store in RAG memory for semantic search
            artifact_id = f"{manifest.tool_id}_v{manifest.version}"
            self.rag_memory.store_artifact(
                artifact_id=artifact_id,
                artifact_type=ArtifactType.TOOL,
                name=manifest.name,
                description=manifest.description,
                content=json.dumps(manifest.to_dict()),
                tags=manifest.tags + ['forge', f"trust:{manifest.trust.get('level', 'experimental')}"],
                metadata={
                    'tool_id': manifest.tool_id,
                    'version': manifest.version,
                    'type': manifest.type,
                    'trust_level': manifest.trust.get('level'),
                    'validation_score': manifest.trust.get('validation_score'),
                    'lineage': manifest.lineage
                }
            )

            # Cache in memory
            cache_key = f"{manifest.tool_id}:{manifest.version}"
            self._manifest_cache[cache_key] = manifest

            logger.info(f"Registered tool manifest: {manifest.tool_id} v{manifest.version}")
            return True

        except Exception as e:
            logger.error(f"Failed to register tool manifest: {e}")
            return False

    def query_tools(
        self,
        capability: str,
        constraints: Optional[Dict[str, Any]] = None,
        context_tags: Optional[List[str]] = None,
        limit: int = 5
    ) -> Dict[str, Any]:
        """
        Query tools by capability with constraint filtering.

        Args:
            capability: Required capability (e.g., "summarize_pdf")
            constraints: Performance/quality constraints
            context_tags: Additional context tags for filtering
            limit: Maximum results to return

        Returns:
            Query results with best_tool and alternatives
        """
        # Search RAG memory for matching tools
        search_query = f"capability: {capability}"
        if context_tags:
            search_query += f" tags: {' '.join(context_tags)}"

        results = self.rag_memory.search(
            query=search_query,
            artifact_type=ArtifactType.TOOL,
            top_k=limit * 2,  # Get more for filtering
            tags=['forge']
        )

        # Filter by constraints
        filtered_tools = []
        for result in results:
            manifest_data = json.loads(result['content'])
            manifest = ToolManifest.from_dict(manifest_data)

            # Apply constraint checks
            if constraints:
                if not self._meets_constraints(manifest, constraints):
                    continue

            # Add consensus weight
            consensus = self._get_consensus_score(manifest.tool_id, manifest.version)
            weight = consensus.weight if consensus else 0.5

            filtered_tools.append({
                'tool_id': manifest.tool_id,
                'version': manifest.version,
                'name': manifest.name,
                'weight': weight,
                'trust_level': manifest.trust.get('level'),
                'metrics': manifest.metrics.get('latest', {})
            })

        # Sort by weight
        filtered_tools.sort(key=lambda x: x['weight'], reverse=True)

        # Return best tool and alternatives
        return {
            'best_tool': filtered_tools[0] if filtered_tools else None,
            'alternatives': filtered_tools[1:limit] if len(filtered_tools) > 1 else []
        }

    def _meets_constraints(self, manifest: ToolManifest, constraints: Dict[str, Any]) -> bool:
        """Check if tool meets constraints."""
        metrics = manifest.metrics.get('latest', {})

        for key, threshold in constraints.items():
            if key == 'latency_ms_p95':
                if metrics.get('latency_ms_p95', float('inf')) > threshold:
                    return False
            elif key == 'risk_score':
                if manifest.trust.get('risk_score', 1.0) > threshold:
                    return False
            elif key == 'correctness':
                if metrics.get('correctness', 0) < threshold:
                    return False

        return True

    def store_consensus_score(self, score: ConsensusScore) -> bool:
        """
        Store consensus scoring record.

        Args:
            score: Consensus score to store

        Returns:
            Success status
        """
        try:
            cache_key = f"{score.tool_id}:{score.version}"
            self._consensus_cache[cache_key] = score

            # Store in RAG memory
            artifact_id = f"consensus_{score.tool_id}_v{score.version}_{score.timestamp}"
            self.rag_memory.store_artifact(
                artifact_id=artifact_id,
                artifact_type=ArtifactType.EVALUATION,
                name=f"Consensus score for {score.tool_id}",
                description=f"Consensus evaluation with weight {score.weight}",
                content=json.dumps(score.to_dict()),
                tags=['forge', 'consensus', score.tool_id],
                metadata={
                    'tool_id': score.tool_id,
                    'version': score.version,
                    'weight': score.weight
                }
            )

            logger.info(f"Stored consensus score for {score.tool_id} v{score.version}: weight={score.weight}")
            return True

        except Exception as e:
            logger.error(f"Failed to store consensus score: {e}")
            return False

    def _get_consensus_score(self, tool_id: str, version: str) -> Optional[ConsensusScore]:
        """Get cached consensus score."""
        cache_key = f"{tool_id}:{version}"
        return self._consensus_cache.get(cache_key)

    def get_tool_manifest(self, tool_id: str, version: Optional[str] = None) -> Optional[ToolManifest]:
        """
        Get tool manifest by ID and version.

        Args:
            tool_id: Tool identifier
            version: Specific version (or latest if None)

        Returns:
            Tool manifest or None
        """
        # Check cache first
        if version:
            cache_key = f"{tool_id}:{version}"
            if cache_key in self._manifest_cache:
                return self._manifest_cache[cache_key]

        # Load from disk
        manifest_pattern = f"{tool_id}_v*.yaml" if not version else f"{tool_id}_v{version}.yaml"
        manifests = list(self.manifest_dir.glob(manifest_pattern))

        if not manifests:
            return None

        # Get latest or specific version
        manifest_path = max(manifests, key=lambda p: p.stat().st_mtime) if not version else manifests[0]

        with open(manifest_path, 'r') as f:
            data = yaml.safe_load(f)
            manifest = ToolManifest.from_dict(data)

        # Cache it
        cache_key = f"{manifest.tool_id}:{manifest.version}"
        self._manifest_cache[cache_key] = manifest

        return manifest

    def list_tools(
        self,
        trust_level: Optional[str] = None,
        tool_type: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[ToolManifest]:
        """
        List tools with optional filtering.

        Args:
            trust_level: Filter by trust level (core, third_party, experimental)
            tool_type: Filter by tool type (mcp, llm, etc.)
            tags: Filter by tags

        Returns:
            List of tool manifests
        """
        search_tags = ['forge']
        if trust_level:
            search_tags.append(f"trust:{trust_level}")
        if tags:
            search_tags.extend(tags)

        results = self.rag_memory.search(
            query="",
            artifact_type=ArtifactType.TOOL,
            top_k=100,
            tags=search_tags
        )

        manifests = []
        for result in results:
            manifest_data = json.loads(result['content'])
            manifest = ToolManifest.from_dict(manifest_data)

            if tool_type and manifest.type != tool_type:
                continue

            manifests.append(manifest)

        return manifests
