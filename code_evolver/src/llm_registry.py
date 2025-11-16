"""
LLM Registry Manager

Manages LLM models as tools - loads LLM definitions from llm_tools/ directory
and makes them queryable via the tool registry and RAG system.

LLMs are treated as a special type of tool with additional metadata:
- Backend (anthropic, ollama, openai, etc.)
- Model ID
- Capabilities
- Quality/speed/cost tiers
- Routing keywords
"""
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import yaml
import json

logger = logging.getLogger(__name__)


class LLMRegistry:
    """Manages LLM models as special tools."""

    def __init__(self, llm_tools_path: str = "./llm_tools", tools_manager=None, rag_memory=None):
        """
        Initialize LLM registry.

        Args:
            llm_tools_path: Path to directory containing LLM YAML definitions
            tools_manager: Optional ToolsManager for integration
            rag_memory: Optional RAGMemory for storing usage/quality metrics
        """
        self.llm_tools_path = Path(llm_tools_path)
        self.tools_manager = tools_manager
        self.rag_memory = rag_memory

        # In-memory registry of LLMs
        self.llms: Dict[str, Dict[str, Any]] = {}

        # Usage and quality tracking (for learning)
        self.usage_stats_path = Path("./llm_usage_stats.json")
        self.usage_stats = self._load_usage_stats()

        # Load LLM definitions
        self._load_llms()

    def _load_llms(self):
        """Load LLM definitions from YAML files."""
        if not self.llm_tools_path.exists():
            logger.warning(f"LLM tools directory not found: {self.llm_tools_path}")
            self.llm_tools_path.mkdir(parents=True, exist_ok=True)
            return

        yaml_files = list(self.llm_tools_path.glob("*.yaml"))

        if not yaml_files:
            logger.info("No LLM definitions found in llm_tools/")
            return

        logger.info(f"Loading {len(yaml_files)} LLM definition(s)...")

        for yaml_file in yaml_files:
            try:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    llm_def = yaml.safe_load(f)

                # Validate required fields
                if not llm_def.get("type") == "llm_model":
                    continue

                llm_id = yaml_file.stem
                enabled = llm_def.get("enabled", True)

                # Skip disabled LLMs
                if not enabled:
                    logger.debug(f"LLM {llm_id} is disabled, skipping")
                    continue

                # Store LLM definition
                self.llms[llm_id] = llm_def

                logger.info(f"✓ Loaded LLM: {llm_def.get('name', llm_id)}")

                # Register with tools manager if available
                if self.tools_manager:
                    self._register_as_tool(llm_id, llm_def)

            except Exception as e:
                logger.error(f"Error loading LLM from {yaml_file}: {e}")

        logger.info(f"✓ Loaded {len(self.llms)} enabled LLM(s)")

    def _register_as_tool(self, llm_id: str, llm_def: Dict[str, Any]):
        """Register LLM as a tool in the tools manager."""
        try:
            from src.tools_manager import Tool, ToolType

            # Create tool representation
            tool = Tool(
                tool_id=f"llm_{llm_id}",
                name=llm_def.get("name", llm_id),
                tool_type=ToolType.LLM,
                description=llm_def.get("description", ""),
                tags=["llm", "model", llm_def.get("provider", "unknown")] +
                     llm_def.get("capabilities", []),
                implementation={
                    "backend": llm_def.get("provider"),
                    "model_id": llm_def.get("model_id"),
                    "metadata": llm_def.get("metadata", {})
                },
                metadata={
                    "llm_type": True,
                    "backend": llm_def.get("provider"),
                    "model_id": llm_def.get("model_id"),
                    "quality_tier": llm_def.get("quality_tier"),
                    "speed_tier": llm_def.get("speed_tier"),
                    "cost_tier": llm_def.get("cost_tier"),
                    "capabilities": llm_def.get("capabilities", []),
                    "specialization": llm_def.get("specialization", {}),
                    "routing_keywords": llm_def.get("routing_keywords", []),
                    "priority": llm_def.get("priority", 50),
                    "use_cases": llm_def.get("use_cases", []),
                    "strengths": llm_def.get("strengths", []),
                    "limitations": llm_def.get("limitations", []),
                    "context_window": llm_def.get("context_window", 0),
                    "max_output": llm_def.get("max_output", 0),
                    "role": llm_def.get("role", None)
                }
            )

            # Register with tools manager
            self.tools_manager.tools[tool.tool_id] = tool
            logger.debug(f"Registered LLM as tool: {tool.tool_id}")

        except Exception as e:
            logger.error(f"Error registering LLM as tool: {e}")

    def get_llm(self, llm_id: str) -> Optional[Dict[str, Any]]:
        """Get LLM definition by ID."""
        return self.llms.get(llm_id)

    def find_llms_by_capability(self, capability: str) -> List[Dict[str, Any]]:
        """Find LLMs that have a specific capability."""
        results = []
        for llm_id, llm_def in self.llms.items():
            capabilities = llm_def.get("capabilities", [])
            if capability in capabilities:
                results.append({
                    "llm_id": llm_id,
                    **llm_def
                })
        return results

    def find_llms_by_quality_tier(self, tier: str) -> List[Dict[str, Any]]:
        """Find LLMs by quality tier (god, escalation, general, fast, veryfast)."""
        results = []
        for llm_id, llm_def in self.llms.items():
            if llm_def.get("quality_tier") == tier:
                results.append({
                    "llm_id": llm_id,
                    **llm_def
                })
        return results

    def find_llms_by_backend(self, backend: str) -> List[Dict[str, Any]]:
        """Find LLMs by backend (anthropic, ollama, openai, etc.)."""
        results = []
        for llm_id, llm_def in self.llms.items():
            if llm_def.get("provider") == backend:
                results.append({
                    "llm_id": llm_id,
                    **llm_def
                })
        return results

    def find_llms_by_keywords(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """Find LLMs matching routing keywords."""
        results = []
        for llm_id, llm_def in self.llms.items():
            routing_keywords = llm_def.get("routing_keywords", [])
            # Check if any keyword matches
            if any(kw in routing_keywords for kw in keywords):
                results.append({
                    "llm_id": llm_id,
                    **llm_def,
                    "matched_keywords": [kw for kw in keywords if kw in routing_keywords]
                })
        return results

    def find_best_llm(
        self,
        task_type: Optional[str] = None,
        quality_requirement: Optional[str] = None,
        backend_preference: Optional[str] = None,
        keywords: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Find the best LLM matching criteria.

        Args:
            task_type: Type of task (code_review, content_generation, etc.)
            quality_requirement: Quality tier (god, escalation, general, fast)
            backend_preference: Preferred backend (anthropic, ollama, etc.)
            keywords: List of routing keywords from request

        Returns:
            Best matching LLM definition or None
        """
        candidates = list(self.llms.values())

        # Filter by backend if specified
        if backend_preference:
            candidates = [llm for llm in candidates
                         if llm.get("provider") == backend_preference]

        # Filter by quality tier if specified
        if quality_requirement:
            tier_candidates = [llm for llm in candidates
                              if llm.get("quality_tier") == quality_requirement]
            if tier_candidates:
                candidates = tier_candidates

        # Score by keywords if provided
        if keywords:
            scored_candidates = []
            for llm in candidates:
                routing_keywords = llm.get("routing_keywords", [])
                score = sum(1 for kw in keywords if kw in routing_keywords)
                if score > 0:
                    scored_candidates.append((score, llm))

            if scored_candidates:
                # Sort by score (descending) and priority
                scored_candidates.sort(
                    key=lambda x: (x[0], x[1].get("priority", 0)),
                    reverse=True
                )
                return scored_candidates[0][1]

        # Sort by priority if no keyword matches
        if candidates:
            candidates.sort(key=lambda x: x.get("priority", 0), reverse=True)
            return candidates[0]

        return None

    def get_all_llms_json(self) -> str:
        """Get all LLMs as JSON string (for model selector prompt)."""
        llms_list = []
        for llm_id, llm_def in self.llms.items():
            llms_list.append({
                "llm_id": llm_id,
                "name": llm_def.get("name"),
                "backend": llm_def.get("provider"),
                "model_id": llm_def.get("model_id"),
                "quality_tier": llm_def.get("quality_tier"),
                "speed_tier": llm_def.get("speed_tier"),
                "cost_tier": llm_def.get("cost_tier"),
                "capabilities": llm_def.get("capabilities", []),
                "routing_keywords": llm_def.get("routing_keywords", []),
                "priority": llm_def.get("priority", 50),
                "specialization": llm_def.get("specialization", {}),
                "role": llm_def.get("role")
            })

        return json.dumps(llms_list, indent=2)

    def list_all(self) -> List[Dict[str, Any]]:
        """List all loaded LLMs."""
        return [{"llm_id": llm_id, **llm_def}
                for llm_id, llm_def in self.llms.items()]

    def _load_usage_stats(self) -> Dict[str, Any]:
        """Load usage statistics from disk."""
        if not self.usage_stats_path.exists():
            return {
                "llms": {},  # llm_id -> stats
                "task_types": {}  # task_type -> llm_id -> stats
            }

        try:
            with open(self.usage_stats_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading usage stats: {e}")
            return {"llms": {}, "task_types": {}}

    def _save_usage_stats(self):
        """Save usage statistics to disk."""
        try:
            with open(self.usage_stats_path, 'w', encoding='utf-8') as f:
                json.dump(self.usage_stats, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving usage stats: {e}")

    def record_usage(
        self,
        llm_id: str,
        task_type: str,
        quality_score: Optional[float] = None,
        latency_ms: Optional[float] = None,
        success: bool = True
    ):
        """
        Record LLM usage for learning.

        Args:
            llm_id: ID of LLM used
            task_type: Type of task (code_review, content_generation, etc.)
            quality_score: Quality score 0-1 (if available)
            latency_ms: Response time in milliseconds
            success: Whether the task succeeded
        """
        # Initialize stats for this LLM if needed
        if llm_id not in self.usage_stats["llms"]:
            self.usage_stats["llms"][llm_id] = {
                "total_uses": 0,
                "successes": 0,
                "failures": 0,
                "avg_quality": 0.0,
                "avg_latency": 0.0,
                "task_performance": {}  # task_type -> metrics
            }

        # Initialize stats for this task type if needed
        if task_type not in self.usage_stats["task_types"]:
            self.usage_stats["task_types"][task_type] = {}

        if llm_id not in self.usage_stats["task_types"][task_type]:
            self.usage_stats["task_types"][task_type][llm_id] = {
                "uses": 0,
                "successes": 0,
                "avg_quality": 0.0,
                "avg_latency": 0.0
            }

        # Update global LLM stats
        llm_stats = self.usage_stats["llms"][llm_id]
        llm_stats["total_uses"] += 1

        if success:
            llm_stats["successes"] += 1
        else:
            llm_stats["failures"] += 1

        # Update quality score (running average)
        if quality_score is not None:
            prev_avg = llm_stats["avg_quality"]
            n = llm_stats["total_uses"]
            llm_stats["avg_quality"] = (prev_avg * (n - 1) + quality_score) / n

        # Update latency (running average)
        if latency_ms is not None:
            prev_avg = llm_stats["avg_latency"]
            n = llm_stats["total_uses"]
            llm_stats["avg_latency"] = (prev_avg * (n - 1) + latency_ms) / n

        # Update task-specific performance
        if task_type not in llm_stats["task_performance"]:
            llm_stats["task_performance"][task_type] = {
                "uses": 0,
                "avg_quality": 0.0
            }

        task_perf = llm_stats["task_performance"][task_type]
        task_perf["uses"] += 1

        if quality_score is not None:
            prev_avg = task_perf["avg_quality"]
            n = task_perf["uses"]
            task_perf["avg_quality"] = (prev_avg * (n - 1) + quality_score) / n

        # Update task type stats
        task_stats = self.usage_stats["task_types"][task_type][llm_id]
        task_stats["uses"] += 1

        if success:
            task_stats["successes"] += 1

        if quality_score is not None:
            prev_avg = task_stats["avg_quality"]
            n = task_stats["uses"]
            task_stats["avg_quality"] = (prev_avg * (n - 1) + quality_score) / n

        if latency_ms is not None:
            prev_avg = task_stats["avg_latency"]
            n = task_stats["uses"]
            task_stats["avg_latency"] = (prev_avg * (n - 1) + latency_ms) / n

        # Save updated stats
        self._save_usage_stats()

        logger.debug(f"Recorded usage: {llm_id} for {task_type} (quality: {quality_score}, success: {success})")

    def get_best_llm_for_task(
        self,
        task_type: str,
        min_uses: int = 5,
        quality_weight: float = 0.7,
        latency_weight: float = 0.3
    ) -> Optional[str]:
        """
        Get the best LLM for a specific task type based on learned performance.

        Args:
            task_type: Type of task
            min_uses: Minimum number of uses to consider LLM
            quality_weight: Weight for quality score (0-1)
            latency_weight: Weight for latency (0-1)

        Returns:
            LLM ID of best performer or None
        """
        if task_type not in self.usage_stats["task_types"]:
            return None

        task_llms = self.usage_stats["task_types"][task_type]

        # Filter LLMs with enough data
        candidates = {
            llm_id: stats
            for llm_id, stats in task_llms.items()
            if stats["uses"] >= min_uses
        }

        if not candidates:
            return None

        # Score each LLM
        best_llm = None
        best_score = -1

        for llm_id, stats in candidates.items():
            # Normalize quality (already 0-1)
            quality_score = stats["avg_quality"]

            # Normalize latency (invert and normalize to 0-1)
            # Assume max acceptable latency is 30000ms (30 seconds)
            latency_score = max(0, 1 - (stats["avg_latency"] / 30000))

            # Weighted score
            score = (quality_weight * quality_score) + (latency_weight * latency_score)

            if score > best_score:
                best_score = score
                best_llm = llm_id

        logger.info(f"Best LLM for {task_type}: {best_llm} (score: {best_score:.3f})")
        return best_llm

    def get_fitness_scores(self, task_type: str) -> Dict[str, float]:
        """
        Get fitness scores for all LLMs for a specific task type.

        Returns:
            Dict mapping llm_id to fitness score (0-1)
        """
        if task_type not in self.usage_stats["task_types"]:
            return {}

        task_llms = self.usage_stats["task_types"][task_type]

        scores = {}
        for llm_id, stats in task_llms.items():
            if stats["uses"] > 0:
                # Success rate
                success_rate = stats["successes"] / stats["uses"]

                # Quality score
                quality = stats["avg_quality"]

                # Combined fitness (average of success rate and quality)
                fitness = (success_rate + quality) / 2
                scores[llm_id] = fitness

        return scores

    def find_best_llm_with_learning(
        self,
        task_type: Optional[str] = None,
        quality_requirement: Optional[str] = None,
        backend_preference: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        use_learned_performance: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Find the best LLM with learning-based selection.

        If use_learned_performance is True and we have enough data for the task type,
        uses learned performance. Otherwise falls back to keyword/capability matching.

        Args:
            task_type: Type of task
            quality_requirement: Quality tier requirement
            backend_preference: Preferred backend
            keywords: Routing keywords
            use_learned_performance: Whether to use learned data (default True)

        Returns:
            Best matching LLM definition
        """
        # Try learned performance first if enabled
        if use_learned_performance and task_type:
            best_llm_id = self.get_best_llm_for_task(task_type, min_uses=5)

            if best_llm_id:
                llm_def = self.llms.get(best_llm_id)
                if llm_def:
                    logger.info(f"Selected LLM based on learned performance: {best_llm_id}")
                    return {
                        "llm_id": best_llm_id,
                        "selection_method": "learned_performance",
                        **llm_def
                    }

        # Fall back to keyword/capability matching
        result = self.find_best_llm(
            task_type=task_type,
            quality_requirement=quality_requirement,
            backend_preference=backend_preference,
            keywords=keywords
        )

        if result:
            return {
                "selection_method": "keyword_matching",
                **result
            }

        return None

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about loaded LLMs and usage."""
        backends = {}
        quality_tiers = {}
        total_enabled = len(self.llms)

        for llm_def in self.llms.values():
            backend = llm_def.get("provider", "unknown")
            backends[backend] = backends.get(backend, 0) + 1

            tier = llm_def.get("quality_tier", "unknown")
            quality_tiers[tier] = quality_tiers.get(tier, 0) + 1

        # Add usage statistics
        total_uses = sum(
            stats["total_uses"]
            for stats in self.usage_stats["llms"].values()
        )

        return {
            "total_enabled": total_enabled,
            "backends": backends,
            "quality_tiers": quality_tiers,
            "total_uses": total_uses,
            "tracked_llms": len(self.usage_stats["llms"]),
            "tracked_task_types": len(self.usage_stats["task_types"])
        }
