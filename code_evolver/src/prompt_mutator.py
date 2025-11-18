"""
Prompt Mutator - Treats LLM tools like code tools, enabling mutation for specialization.

Core Philosophy:
- Prefer mutating prompts over using overly general prompts
- Ask overseer whether mutation is beneficial (efficiency, necessity)
- Track lineage and enable rollback
- Robust versioning and metadata tracking

Mutation enables:
1. Specialization - Make prompt specific for a use case
2. Optimization - Improve clarity and effectiveness
3. Constraint - Add requirements/constraints
4. Simplification - Remove unnecessary complexity
5. Expansion - Add more detail/context
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class MutationStrategy(Enum):
    """Types of prompt mutations."""
    SPECIALIZE = "specialize"        # Make more specific for a use case
    OPTIMIZE = "optimize"            # Improve clarity and effectiveness
    CONSTRAIN = "constrain"          # Add requirements/constraints
    SIMPLIFY = "simplify"            # Remove unnecessary complexity
    EXPAND = "expand"                # Add more detail/context
    REFRAME = "reframe"              # Change approach while keeping intent
    HYBRID = "hybrid"                # Combination of strategies


class MutationDecision:
    """Represents overseer's decision about whether to mutate."""

    def __init__(
        self,
        should_mutate: bool,
        reasoning: str,
        recommended_strategy: Optional[MutationStrategy] = None,
        efficiency_gain: float = 0.0,
        cost_benefit_ratio: float = 0.0
    ):
        """
        Initialize mutation decision.

        Args:
            should_mutate: Whether to mutate
            reasoning: Why or why not
            recommended_strategy: Suggested mutation strategy
            efficiency_gain: Expected efficiency improvement (0.0-1.0)
            cost_benefit_ratio: Cost of mutation vs benefit
        """
        self.should_mutate = should_mutate
        self.reasoning = reasoning
        self.recommended_strategy = recommended_strategy
        self.efficiency_gain = efficiency_gain
        self.cost_benefit_ratio = cost_benefit_ratio
        self.timestamp = datetime.utcnow().isoformat() + "Z"


class MutatedPrompt:
    """Represents a mutated prompt with full lineage and metadata."""

    def __init__(
        self,
        mutation_id: str,
        parent_tool_id: str,
        parent_system_prompt: str,
        parent_prompt_template: str,
        mutated_system_prompt: str,
        mutated_prompt_template: str,
        strategy: MutationStrategy,
        use_case: str,
        llm_backend: Optional[str] = None,
        llm_model: Optional[str] = None,
        llm_tier: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize mutated prompt.

        Args:
            mutation_id: Unique ID for this mutation
            parent_tool_id: Original tool ID
            parent_system_prompt: Original system prompt
            parent_prompt_template: Original prompt template
            mutated_system_prompt: New system prompt
            mutated_prompt_template: New prompt template
            strategy: Mutation strategy used
            use_case: Specific use case for this mutation
            llm_backend: LLM backend used (ollama, anthropic, openai, etc.)
            llm_model: Specific model (llama3, claude-sonnet-4, gpt-4, etc.)
            llm_tier: Tier configuration (quality.tier_2, coding.tier_3, etc.)
            metadata: Additional metadata
        """
        self.mutation_id = mutation_id
        self.parent_tool_id = parent_tool_id
        self.parent_system_prompt = parent_system_prompt
        self.parent_prompt_template = parent_prompt_template
        self.mutated_system_prompt = mutated_system_prompt
        self.mutated_prompt_template = mutated_prompt_template
        self.strategy = strategy
        self.use_case = use_case

        # LLM-specific tracking - CRITICAL for mutation portability
        self.llm_backend = llm_backend  # e.g., "ollama", "anthropic", "openai"
        self.llm_model = llm_model      # e.g., "llama3", "claude-sonnet-4", "gpt-4"
        self.llm_tier = llm_tier        # e.g., "quality.tier_2", "coding.tier_3"

        self.metadata = metadata or {}
        self.created_at = datetime.utcnow().isoformat() + "Z"

        # Performance tracking
        self.performance_metrics: List[Dict[str, Any]] = []
        self.rollback_count = 0

    def record_performance(
        self,
        quality: float,
        speed_ms: int,
        success: bool,
        context: Optional[str] = None
    ):
        """Record performance of this mutated prompt."""
        self.performance_metrics.append({
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "quality": quality,
            "speed_ms": speed_ms,
            "success": success,
            "context": context
        })

    def get_average_quality(self) -> float:
        """Get average quality across all uses."""
        if not self.performance_metrics:
            return 0.0
        successful = [m for m in self.performance_metrics if m["success"]]
        if not successful:
            return 0.0
        return sum(m["quality"] for m in successful) / len(successful)

    def get_average_speed(self) -> float:
        """Get average speed across all uses."""
        if not self.performance_metrics:
            return 0.0
        successful = [m for m in self.performance_metrics if m["success"]]
        if not successful:
            return 0.0
        return sum(m["speed_ms"] for m in successful) / len(successful)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "mutation_id": self.mutation_id,
            "parent_tool_id": self.parent_tool_id,
            "parent_system_prompt": self.parent_system_prompt,
            "parent_prompt_template": self.parent_prompt_template,
            "mutated_system_prompt": self.mutated_system_prompt,
            "mutated_prompt_template": self.mutated_prompt_template,
            "strategy": self.strategy.value,
            "use_case": self.use_case,
            # LLM-specific metadata - tracks what this mutation was optimized for
            "llm_backend": self.llm_backend,
            "llm_model": self.llm_model,
            "llm_tier": self.llm_tier,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "performance_metrics": self.performance_metrics,
            "rollback_count": self.rollback_count,
            "avg_quality": self.get_average_quality(),
            "avg_speed": self.get_average_speed()
        }


class PromptMutator:
    """
    Core prompt mutation engine.

    Treats LLM tools like code - enables mutation/specialization instead of
    forcing general prompts to fit all scenarios.
    """

    def __init__(
        self,
        ollama_client=None,
        overseer_llm=None,
        rag_memory=None,
        storage_path: Optional[Path] = None
    ):
        """
        Initialize prompt mutator.

        Args:
            ollama_client: OllamaClient for LLM calls
            overseer_llm: OverseerLlm for decision-making
            rag_memory: RAG memory for storing mutations
            storage_path: Path to store mutation history
        """
        self.ollama_client = ollama_client
        self.overseer_llm = overseer_llm
        self.rag_memory = rag_memory
        self.storage_path = storage_path or Path("mutations")
        self.storage_path.mkdir(exist_ok=True, parents=True)

        # Mutation cache
        self.mutations: Dict[str, MutatedPrompt] = {}

        # Load existing mutations
        self._load_mutations()

    def should_mutate(
        self,
        tool_id: str,
        use_case: str,
        context: Optional[Dict[str, Any]] = None
    ) -> MutationDecision:
        """
        Ask overseer whether prompt mutation is beneficial.

        This is the intelligence layer - prevents unnecessary mutations while
        enabling beneficial specialization.

        Args:
            tool_id: ID of tool to potentially mutate
            use_case: Specific use case to optimize for
            context: Additional context (frequency, performance data, etc.)

        Returns:
            MutationDecision with overseer's recommendation
        """
        if not self.overseer_llm:
            # No overseer - default to conservative approach
            logger.warning("No overseer available - using conservative mutation decision")
            return MutationDecision(
                should_mutate=False,
                reasoning="No overseer available for intelligent decision-making"
            )

        # Build decision prompt for overseer
        prompt = self._build_mutation_decision_prompt(tool_id, use_case, context or {})

        try:
            # Get overseer's decision
            response = self.overseer_llm.client.generate(
                model=self.overseer_llm.model,
                prompt=prompt,
                temperature=0.3  # Lower temp for consistent decisions
            )

            # Parse response
            decision_data = self._parse_decision_response(response)

            # Create MutationDecision
            decision = MutationDecision(
                should_mutate=decision_data.get("should_mutate", False),
                reasoning=decision_data.get("reasoning", ""),
                recommended_strategy=MutationStrategy(decision_data.get("strategy", "optimize"))
                    if decision_data.get("strategy") else None,
                efficiency_gain=decision_data.get("efficiency_gain", 0.0),
                cost_benefit_ratio=decision_data.get("cost_benefit_ratio", 0.0)
            )

            logger.info(f"Overseer decision for {tool_id}: {'MUTATE' if decision.should_mutate else 'SKIP'}")
            logger.info(f"Reasoning: {decision.reasoning}")

            return decision

        except Exception as e:
            logger.error(f"Error getting overseer decision: {e}")
            return MutationDecision(
                should_mutate=False,
                reasoning=f"Error during decision-making: {e}"
            )

    def mutate_prompt(
        self,
        tool_id: str,
        system_prompt: str,
        prompt_template: str,
        use_case: str,
        strategy: MutationStrategy,
        additional_constraints: Optional[List[str]] = None,
        additional_context: Optional[str] = None,
        llm_config: Optional[Dict[str, Any]] = None
    ) -> MutatedPrompt:
        """
        Mutate a prompt using specified strategy.

        Args:
            tool_id: Original tool ID
            system_prompt: Original system prompt
            prompt_template: Original prompt template
            use_case: Specific use case to optimize for
            strategy: Mutation strategy to apply
            additional_constraints: Extra constraints to add
            additional_context: Extra context to include
            llm_config: LLM configuration (backend, model, tier) this mutation is for

        Returns:
            MutatedPrompt with new prompts and full lineage
        """
        logger.info(f"Mutating {tool_id} with {strategy.value} strategy for: {use_case}")

        # Extract LLM-specific metadata from config
        llm_backend = None
        llm_model = None
        llm_tier = None

        if llm_config:
            llm_backend = llm_config.get("backend")
            llm_model = llm_config.get("model")
            llm_tier = llm_config.get("tier")

        # Build mutation prompt based on strategy
        mutation_prompt = self._build_mutation_prompt(
            system_prompt=system_prompt,
            prompt_template=prompt_template,
            use_case=use_case,
            strategy=strategy,
            constraints=additional_constraints or [],
            context=additional_context or "",
            llm_backend=llm_backend,
            llm_model=llm_model,
            llm_tier=llm_tier
        )

        try:
            # Get mutation from LLM
            response = self.ollama_client.generate(
                model="llama3",  # Use capable model for prompt engineering
                prompt=mutation_prompt,
                temperature=0.4  # Balanced creativity and consistency
            )

            # Parse mutated prompts
            mutation_data = self._parse_mutation_response(response)

            # Generate mutation ID
            mutation_id = self._generate_mutation_id(tool_id, use_case, strategy)

            # Create MutatedPrompt with LLM tracking
            mutated = MutatedPrompt(
                mutation_id=mutation_id,
                parent_tool_id=tool_id,
                parent_system_prompt=system_prompt,
                parent_prompt_template=prompt_template,
                mutated_system_prompt=mutation_data.get("system_prompt", system_prompt),
                mutated_prompt_template=mutation_data.get("prompt_template", prompt_template),
                strategy=strategy,
                use_case=use_case,
                llm_backend=llm_backend,
                llm_model=llm_model,
                llm_tier=llm_tier,
                metadata={
                    "constraints": additional_constraints,
                    "context": additional_context,
                    "mutation_reasoning": mutation_data.get("reasoning", "")
                }
            )

            # Cache mutation
            self.mutations[mutation_id] = mutated

            # Store in RAG if available
            if self.rag_memory:
                self._store_mutation_in_rag(mutated)

            # Save to disk
            self._save_mutation(mutated)

            logger.info(f"✓ Created mutation {mutation_id}")
            return mutated

        except Exception as e:
            logger.error(f"Error during mutation: {e}")
            # Return unchanged prompts on error
            mutation_id = f"{tool_id}_failed_{int(datetime.utcnow().timestamp())}"
            return MutatedPrompt(
                mutation_id=mutation_id,
                parent_tool_id=tool_id,
                parent_system_prompt=system_prompt,
                parent_prompt_template=prompt_template,
                mutated_system_prompt=system_prompt,
                mutated_prompt_template=prompt_template,
                strategy=strategy,
                use_case=use_case,
                metadata={"error": str(e)}
            )

    def auto_mutate(
        self,
        tool_id: str,
        system_prompt: str,
        prompt_template: str,
        use_case: str,
        context: Optional[Dict[str, Any]] = None,
        llm_config: Optional[Dict[str, Any]] = None
    ) -> Optional[MutatedPrompt]:
        """
        Automatically decide and mutate if beneficial.

        This is the high-level API that:
        1. Asks overseer if mutation is beneficial
        2. Uses recommended strategy if yes
        3. Returns mutated prompt or None

        Args:
            tool_id: Original tool ID
            system_prompt: Original system prompt
            prompt_template: Original prompt template
            use_case: Specific use case
            context: Additional context for decision
            llm_config: LLM configuration (backend, model, tier) to optimize for

        Returns:
            MutatedPrompt if mutation was beneficial, None otherwise
        """
        # Ask overseer
        decision = self.should_mutate(tool_id, use_case, context)

        if not decision.should_mutate:
            logger.info(f"Overseer recommends NOT mutating {tool_id}: {decision.reasoning}")
            return None

        # Mutate with recommended strategy
        strategy = decision.recommended_strategy or MutationStrategy.OPTIMIZE
        return self.mutate_prompt(
            tool_id=tool_id,
            system_prompt=system_prompt,
            prompt_template=prompt_template,
            use_case=use_case,
            strategy=strategy,
            llm_config=llm_config
        )

    def get_mutation(self, mutation_id: str) -> Optional[MutatedPrompt]:
        """Retrieve a mutation by ID."""
        return self.mutations.get(mutation_id)

    def get_mutations_for_tool(self, tool_id: str) -> List[MutatedPrompt]:
        """Get all mutations of a specific tool."""
        return [
            m for m in self.mutations.values()
            if m.parent_tool_id == tool_id
        ]

    def get_best_mutation_for_use_case(
        self,
        tool_id: str,
        use_case: str,
        min_quality: float = 0.7
    ) -> Optional[MutatedPrompt]:
        """
        Find the best mutation for a specific use case based on performance.

        Args:
            tool_id: Original tool ID
            use_case: Use case to optimize for
            min_quality: Minimum quality threshold

        Returns:
            Best performing mutation or None
        """
        mutations = self.get_mutations_for_tool(tool_id)

        # Filter by use case similarity and quality
        candidates = [
            m for m in mutations
            if self._use_case_similarity(m.use_case, use_case) > 0.7
            and m.get_average_quality() >= min_quality
        ]

        if not candidates:
            return None

        # Return highest quality
        return max(candidates, key=lambda m: m.get_average_quality())

    def _use_case_similarity(self, use_case1: str, use_case2: str) -> float:
        """Simple similarity check between use cases."""
        # TODO: Use embeddings for better similarity
        words1 = set(use_case1.lower().split())
        words2 = set(use_case2.lower().split())
        if not words1 or not words2:
            return 0.0
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        return intersection / union if union > 0 else 0.0

    def _generate_mutation_id(
        self,
        tool_id: str,
        use_case: str,
        strategy: MutationStrategy
    ) -> str:
        """Generate unique mutation ID."""
        # Create readable ID from use case
        use_case_slug = "_".join(use_case.lower().split()[:3])
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        return f"{tool_id}_{strategy.value}_{use_case_slug}_{timestamp}"

    def _build_mutation_decision_prompt(
        self,
        tool_id: str,
        use_case: str,
        context: Dict[str, Any]
    ) -> str:
        """Build prompt for overseer to decide on mutation."""
        return f"""You are an AI Overseer deciding whether to mutate a prompt for specialization.

Tool ID: {tool_id}
Use Case: {use_case}

Context:
{json.dumps(context, indent=2)}

Analyze whether creating a specialized mutation would be beneficial.

Consider:
1. **Efficiency**: Would a specialized prompt be more efficient than adapting general prompt?
2. **Necessity**: Is the use case different enough to warrant specialization?
3. **Cost/Benefit**: Is the effort of creating/maintaining a mutation worth it?
4. **Frequency**: How often will this specialized version be used?

Guidelines:
- MUTATE if use case is specific, frequent, and would benefit from optimization
- SKIP if general prompt is already well-suited
- SKIP if use case is one-off or very rare

Respond in JSON format:
{{
  "should_mutate": true/false,
  "reasoning": "Clear explanation of decision",
  "strategy": "specialize|optimize|constrain|simplify|expand|reframe",
  "efficiency_gain": 0.0-1.0,
  "cost_benefit_ratio": 0.0-1.0,
  "confidence": 0.0-1.0
}}
"""

    def _build_mutation_prompt(
        self,
        system_prompt: str,
        prompt_template: str,
        use_case: str,
        strategy: MutationStrategy,
        constraints: List[str],
        context: str,
        llm_backend: Optional[str] = None,
        llm_model: Optional[str] = None,
        llm_tier: Optional[str] = None
    ) -> str:
        """Build prompt for LLM to perform mutation."""
        strategy_instructions = {
            MutationStrategy.SPECIALIZE: "Make the prompt MORE SPECIFIC for the use case. Add domain-specific language and requirements.",
            MutationStrategy.OPTIMIZE: "Improve clarity, structure, and effectiveness. Remove ambiguity.",
            MutationStrategy.CONSTRAIN: "Add the specified constraints and requirements.",
            MutationStrategy.SIMPLIFY: "Remove unnecessary complexity while keeping core functionality.",
            MutationStrategy.EXPAND: "Add more detail, context, and examples.",
            MutationStrategy.REFRAME: "Change the approach while keeping the same intent and goals."
        }

        instruction = strategy_instructions.get(
            strategy,
            "Optimize the prompt for the specific use case."
        )

        constraints_text = "\n".join(f"- {c}" for c in constraints) if constraints else "None"

        # Build LLM target info
        llm_info_parts = []
        if llm_backend:
            llm_info_parts.append(f"Backend: {llm_backend}")
        if llm_model:
            llm_info_parts.append(f"Model: {llm_model}")
        if llm_tier:
            llm_info_parts.append(f"Tier: {llm_tier}")

        llm_info = "\n".join(llm_info_parts) if llm_info_parts else "Not specified (mutation will be backend-agnostic)"

        # Add model-specific guidance
        model_guidance = ""
        if llm_model:
            if "gpt" in llm_model.lower():
                model_guidance = "\n\nNOTE: Optimizing for OpenAI GPT models - prefer clear instructions, examples work well, supports function calling."
            elif "claude" in llm_model.lower():
                model_guidance = "\n\nNOTE: Optimizing for Anthropic Claude - prefers detailed context, works well with XML tags, excels at chain-of-thought."
            elif "llama" in llm_model.lower() or "ollama" in str(llm_backend).lower():
                model_guidance = "\n\nNOTE: Optimizing for Llama/local models - prefer concise prompts, clear structure, may need more explicit instructions."
            elif "gemini" in llm_model.lower():
                model_guidance = "\n\nNOTE: Optimizing for Google Gemini - supports multimodal, prefers structured formats, good at reasoning tasks."

        return f"""You are a prompt engineering expert specializing in mutation and optimization.

**Original System Prompt:**
{system_prompt}

**Original Prompt Template:**
{prompt_template}

**Target Use Case:**
{use_case}

**Target LLM Configuration:**
{llm_info}{model_guidance}

**Mutation Strategy:**
{strategy.value.upper()}: {instruction}

**Additional Constraints:**
{constraints_text}

**Additional Context:**
{context or "None"}

IMPORTANT: Create a mutated version optimized for the specific use case AND the target LLM configuration.
Different LLMs have different strengths - tailor the prompt accordingly.

Respond in JSON format:
{{
  "system_prompt": "Mutated system prompt (optimized for target LLM)",
  "prompt_template": "Mutated prompt template (optimized for target LLM)",
  "reasoning": "Explanation of changes made and LLM-specific optimizations",
  "improvements": ["List of specific improvements, including LLM-specific ones"],
  "tradeoffs": ["Any tradeoffs or limitations introduced"]
}}
"""

    def _parse_decision_response(self, response: str) -> Dict[str, Any]:
        """Parse overseer's decision response."""
        import re
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        # Fallback - conservative decision
        return {
            "should_mutate": False,
            "reasoning": "Could not parse overseer response",
            "efficiency_gain": 0.0,
            "cost_benefit_ratio": 0.0
        }

    def _parse_mutation_response(self, response: str) -> Dict[str, Any]:
        """Parse mutation response from LLM."""
        import re
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        # Fallback - return original text
        return {
            "system_prompt": "",
            "prompt_template": response,
            "reasoning": "Could not parse mutation response"
        }

    def _store_mutation_in_rag(self, mutation: MutatedPrompt):
        """Store mutation in RAG memory."""
        try:
            from .rag_memory import ArtifactType

            self.rag_memory.store_artifact(
                artifact_id=mutation.mutation_id,
                artifact_type=ArtifactType.PATTERN,
                name=f"Mutated Prompt: {mutation.parent_tool_id}",
                description=f"Mutation for use case: {mutation.use_case}",
                content=json.dumps(mutation.to_dict(), indent=2),
                tags=["mutation", "prompt", mutation.parent_tool_id, mutation.strategy.value],
                metadata={
                    "parent_tool_id": mutation.parent_tool_id,
                    "use_case": mutation.use_case,
                    "strategy": mutation.strategy.value,
                    "is_mutation": True
                }
            )
            logger.debug(f"Stored mutation {mutation.mutation_id} in RAG")
        except Exception as e:
            logger.warning(f"Could not store mutation in RAG: {e}")

    def _save_mutation(self, mutation: MutatedPrompt):
        """Save mutation to disk."""
        try:
            mutation_file = self.storage_path / f"{mutation.mutation_id}.json"
            with open(mutation_file, 'w') as f:
                json.dump(mutation.to_dict(), f, indent=2)
            logger.debug(f"Saved mutation to {mutation_file}")
        except Exception as e:
            logger.warning(f"Could not save mutation to disk: {e}")

    def _load_mutations(self):
        """Load existing mutations from disk."""
        try:
            for mutation_file in self.storage_path.glob("*.json"):
                with open(mutation_file, 'r') as f:
                    data = json.load(f)

                mutation = MutatedPrompt(
                    mutation_id=data["mutation_id"],
                    parent_tool_id=data["parent_tool_id"],
                    parent_system_prompt=data["parent_system_prompt"],
                    parent_prompt_template=data["parent_prompt_template"],
                    mutated_system_prompt=data["mutated_system_prompt"],
                    mutated_prompt_template=data["mutated_prompt_template"],
                    strategy=MutationStrategy(data["strategy"]),
                    use_case=data["use_case"],
                    llm_backend=data.get("llm_backend"),
                    llm_model=data.get("llm_model"),
                    llm_tier=data.get("llm_tier"),
                    metadata=data.get("metadata", {})
                )
                mutation.performance_metrics = data.get("performance_metrics", [])
                mutation.rollback_count = data.get("rollback_count", 0)
                mutation.created_at = data.get("created_at", mutation.created_at)

                self.mutations[mutation.mutation_id] = mutation

            if self.mutations:
                logger.info(f"Loaded {len(self.mutations)} existing mutation(s)")
        except Exception as e:
            logger.warning(f"Error loading mutations: {e}")
