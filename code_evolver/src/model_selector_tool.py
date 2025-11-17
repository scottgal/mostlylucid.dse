"""
Model Selector Tool for dynamic backend and model selection.

Enables workflows to intelligently select the best backend and model
for a given task based on requirements and constraints.

Example usage in workflow:
    "Using my OpenAPI settings use gpt-4 for this operation"
    "Select the best model for code generation with low latency"
    "Use Anthropic Claude for this analysis"
"""
import logging
from typing import Dict, Any, Optional, List

from .tools_manager import Tool, ToolType
from .llm_client_factory import LLMClientFactory

logger = logging.getLogger(__name__)


class ModelSelectorTool:
    """
    Tool that intelligently selects backends and models for tasks.

    Features:
    - Analyzes task requirements
    - Evaluates available backends and models
    - Considers constraints (speed, cost, quality, context window)
    - Supports natural language selection (e.g., "use GPT-4")
    - Returns ranked recommendations
    """

    def __init__(self, config_manager):
        """
        Initialize model selector.

        Args:
            config_manager: ConfigManager with backend configurations
        """
        self.config = config_manager
        self.backends = self._load_backend_configs()

    def _load_backend_configs(self) -> Dict[str, Dict[str, Any]]:
        """Load backend and model configurations."""
        llm_config = self.config.config.get("llm", {})

        backends = {}

        # Ollama models
        if "ollama" in llm_config:
            ollama_models = llm_config.get("ollama", {}).get("models", {})
            for model_key, model_name in ollama_models.items():
                backends[f"ollama:{model_name}"] = {
                    "backend": "ollama",
                    "model": model_name,
                    "cost": "free",
                    "speed": self._infer_speed(model_name),
                    "quality": self._infer_quality(model_name),
                    "context_window": self._get_context_window("ollama", model_name),
                    "best_for": self._infer_use_cases(model_name)
                }

        # OpenAI models
        if "openai" in llm_config:
            openai_models = [
                "gpt-4", "gpt-4-turbo", "gpt-4o", "gpt-4o-mini",
                "gpt-3.5-turbo"
            ]
            for model in openai_models:
                backends[f"openai:{model}"] = {
                    "backend": "openai",
                    "model": model,
                    "cost": self._infer_openai_cost(model),
                    "speed": self._infer_speed(model),
                    "quality": "excellent" if "gpt-4" in model else "good",
                    "context_window": self._get_context_window("openai", model),
                    "best_for": self._infer_use_cases(model)
                }

        # Anthropic models
        if "anthropic" in llm_config:
            anthropic_models = [
                "claude-3-5-sonnet-20241022",
                "claude-3-opus-20240229",
                "claude-3-haiku-20240307"
            ]
            for model in anthropic_models:
                backends[f"anthropic:{model}"] = {
                    "backend": "anthropic",
                    "model": model,
                    "cost": self._infer_anthropic_cost(model),
                    "speed": self._infer_speed(model),
                    "quality": "excellent",
                    "context_window": 200000,
                    "best_for": self._infer_use_cases(model)
                }

        # Azure models
        if "azure" in llm_config:
            azure_config = llm_config.get("azure", {})
            deployments = azure_config.get("deployments", {})
            for deployment_name, model_info in deployments.items():
                backends[f"azure:{deployment_name}"] = {
                    "backend": "azure",
                    "model": deployment_name,
                    "cost": "paid",
                    "speed": self._infer_speed(deployment_name),
                    "quality": "excellent",
                    "context_window": self._get_context_window("azure", deployment_name),
                    "best_for": self._infer_use_cases(deployment_name)
                }

        # LM Studio models
        if "lmstudio" in llm_config:
            # Try to get models dynamically
            try:
                from .lmstudio_client import LMStudioClient
                client = LMStudioClient(
                    base_url=llm_config.get("lmstudio", {}).get("base_url", "http://localhost:1234/v1")
                )
                lmstudio_models = client.list_models()
                for model in lmstudio_models:
                    backends[f"lmstudio:{model}"] = {
                        "backend": "lmstudio",
                        "model": model,
                        "cost": "free",
                        "speed": self._infer_speed(model),
                        "quality": self._infer_quality(model),
                        "context_window": self._get_context_window("lmstudio", model),
                        "best_for": self._infer_use_cases(model)
                    }
            except Exception as e:
                logger.debug(f"Could not fetch LM Studio models: {e}")

        return backends

    def _infer_speed(self, model_name: str) -> str:
        """Infer speed tier from model name."""
        model_lower = model_name.lower()

        if any(kw in model_lower for kw in ["tiny", "small", "haiku", "mini", "2b", "3b"]):
            return "very-fast"
        elif any(kw in model_lower for kw in ["7b", "8b", "turbo", "3.5"]):
            return "fast"
        elif any(kw in model_lower for kw in ["13b", "14b", "llama3", "mistral"]):
            return "medium"
        elif any(kw in model_lower for kw in ["34b", "opus", "gpt-4"]):
            return "slow"
        else:
            return "medium"

    def _infer_quality(self, model_name: str) -> str:
        """Infer quality tier from model name."""
        model_lower = model_name.lower()

        if any(kw in model_lower for kw in ["opus", "gpt-4", "claude-3-5"]):
            return "excellent"
        elif any(kw in model_lower for kw in ["sonnet", "gpt-3.5", "llama3", "qwen"]):
            return "good"
        else:
            return "fair"

    def _infer_use_cases(self, model_name: str) -> List[str]:
        """Infer best use cases from model name."""
        model_lower = model_name.lower()
        use_cases = []

        if any(kw in model_lower for kw in ["code", "coder"]):
            use_cases.extend(["code-generation", "debugging", "refactoring"])
        if any(kw in model_lower for kw in ["gpt-4", "opus", "sonnet"]):
            use_cases.extend(["analysis", "reasoning", "complex-tasks"])
        if any(kw in model_lower for kw in ["tiny", "haiku", "mini"]):
            use_cases.extend(["quick-responses", "simple-tasks", "triage"])
        if any(kw in model_lower for kw in ["128k", "200k", "nemo"]):
            use_cases.extend(["long-context", "documents", "books"])

        return use_cases or ["general-tasks"]

    def _infer_openai_cost(self, model_name: str) -> str:
        """Infer cost tier for OpenAI models."""
        if "gpt-4" in model_name and "mini" not in model_name:
            return "high"
        elif "gpt-3.5" in model_name or "mini" in model_name:
            return "low"
        else:
            return "medium"

    def _infer_anthropic_cost(self, model_name: str) -> str:
        """Infer cost tier for Anthropic models."""
        if "opus" in model_name:
            return "high"
        elif "haiku" in model_name:
            return "low"
        else:
            return "medium"

    def _get_context_window(self, backend: str, model: str) -> int:
        """Get context window for a model."""
        # Use config manager if available
        if hasattr(self.config, 'get_context_window'):
            try:
                return self.config.get_context_window(model)
            except:
                pass

        # Hardcoded defaults
        defaults = {
            "gpt-4": 8192,
            "gpt-4-turbo": 128000,
            "gpt-4o": 128000,
            "gpt-3.5-turbo": 16385,
            "claude-3": 200000,
            "llama3": 8192,
            "qwen": 32768,
            "mistral-nemo": 128000,
        }

        model_lower = model.lower()
        for key, window in defaults.items():
            if key in model_lower:
                return window

        return 8192

    def select_model(
        self,
        task_description: str,
        constraints: Optional[Dict[str, Any]] = None,
        backend_preference: Optional[str] = None,
        model_preference: Optional[str] = None,
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Select the best models for a task.

        Args:
            task_description: Description of what needs to be done
            constraints: Optional constraints like {"max_cost": "medium", "min_speed": "fast"}
            backend_preference: Preferred backend (openai, anthropic, etc.)
            model_preference: Preferred specific model
            top_k: Number of recommendations to return

        Returns:
            List of model recommendations with scores
        """
        constraints = constraints or {}
        task_lower = task_description.lower()

        # Parse natural language preferences from task description
        if not backend_preference:
            if any(kw in task_lower for kw in ["openai", "gpt", "chatgpt"]):
                backend_preference = "openai"
            elif any(kw in task_lower for kw in ["anthropic", "claude"]):
                backend_preference = "anthropic"
            elif any(kw in task_lower for kw in ["azure"]):
                backend_preference = "azure"
            elif any(kw in task_lower for kw in ["lmstudio", "lm studio", "local"]):
                backend_preference = "lmstudio"
            elif any(kw in task_lower for kw in ["ollama"]):
                backend_preference = "ollama"

        # Parse model preference from task description
        if not model_preference:
            if "gpt-4o" in task_lower or "gpt4o" in task_lower:
                model_preference = "gpt-4o"
            elif "gpt-4" in task_lower or "gpt4" in task_lower:
                model_preference = "gpt-4"
            elif "gpt-3.5" in task_lower or "gpt3.5" in task_lower:
                model_preference = "gpt-3.5-turbo"
            elif "claude-3.5" in task_lower or "claude 3.5" in task_lower:
                model_preference = "claude-3-5-sonnet"
            elif "opus" in task_lower:
                model_preference = "opus"
            elif "sonnet" in task_lower:
                model_preference = "sonnet"
            elif "haiku" in task_lower:
                model_preference = "haiku"

        # Analyze task characteristics
        needs_long_context = any(w in task_lower for w in
                                 ["book", "novel", "document", "large", "long"])
        needs_coding = any(w in task_lower for w in
                          ["code", "function", "script", "program", "debug"])
        needs_speed = any(w in task_lower for w in
                         ["quick", "fast", "immediate", "urgent"])
        needs_quality = any(w in task_lower for w in
                           ["complex", "analysis", "reasoning", "difficult"])

        # Score each backend/model
        scores = {}
        for backend_model_id, info in self.backends.items():
            score = 50.0  # Base score

            # Backend preference
            if backend_preference and info["backend"] == backend_preference:
                score += 50

            # Model preference
            if model_preference:
                if model_preference.lower() in info["model"].lower():
                    score += 100  # Strong boost for exact model match

            # Context window scoring
            if needs_long_context:
                context = info.get("context_window", 8192)
                if context >= 100000:
                    score += 40
                elif context >= 50000:
                    score += 25
                elif context >= 20000:
                    score += 15

            # Speed scoring
            if needs_speed:
                speed = info.get("speed", "medium")
                if speed == "very-fast":
                    score += 30
                elif speed == "fast":
                    score += 20
                elif speed == "slow":
                    score -= 15

            # Quality scoring
            if needs_quality:
                quality = info.get("quality", "good")
                if quality == "excellent":
                    score += 30
                elif quality == "good":
                    score += 15

            # Task specialization
            best_for = info.get("best_for", [])
            if needs_coding:
                if any("code" in bf for bf in best_for):
                    score += 35

            # Cost constraints
            max_cost = constraints.get("max_cost")
            if max_cost:
                cost = info.get("cost", "medium")
                cost_values = {"free": 0, "low": 1, "medium": 2, "high": 3}
                if cost_values.get(cost, 2) > cost_values.get(max_cost, 2):
                    score -= 50  # Heavy penalty for exceeding cost

            # Speed constraints
            min_speed = constraints.get("min_speed")
            if min_speed:
                speed = info.get("speed", "medium")
                speed_values = {"very-fast": 4, "fast": 3, "medium": 2, "slow": 1, "very-slow": 0}
                if speed_values.get(speed, 2) < speed_values.get(min_speed, 2):
                    score -= 50

            scores[backend_model_id] = score

        # Sort and return top_k
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        return [
            {
                "rank": i + 1,
                "backend": self.backends[backend_model_id]["backend"],
                "model": self.backends[backend_model_id]["model"],
                "score": score,
                "info": self.backends[backend_model_id],
                "reasoning": self._generate_reasoning(
                    backend_model_id, task_description, score
                )
            }
            for i, (backend_model_id, score) in enumerate(ranked[:top_k])
        ]

    def _generate_reasoning(
        self,
        backend_model_id: str,
        task: str,
        score: float
    ) -> str:
        """Generate explanation for why a model was selected."""
        info = self.backends[backend_model_id]
        return (
            f"{info['backend']}:{info['model']} selected with score {score:.1f}. "
            f"Characteristics: speed={info['speed']}, quality={info['quality']}, "
            f"cost={info['cost']}, context={info['context_window']} tokens. "
            f"Best for: {', '.join(info['best_for'])}"
        )

    def query_models(
        self,
        query: str,
        filter_by: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Query available models conversationally.

        Args:
            query: Natural language query like "what fast summary models do we have"
            filter_by: Optional filters like {"speed": "fast", "cost": "free"}

        Returns:
            List of matching models with metadata

        Examples:
            >>> selector.query_models("what fast code models do we have")
            >>> selector.query_models("show me free models with large context")
            >>> selector.query_models("which models are best for summarization")
        """
        query_lower = query.lower()

        # Parse query for filters
        auto_filters = {}

        # Speed keywords
        if any(kw in query_lower for kw in ["fast", "quick", "rapid"]):
            auto_filters["speed"] = ["fast", "very-fast"]
        elif any(kw in query_lower for kw in ["slow", "thorough", "powerful"]):
            auto_filters["speed"] = ["slow", "medium"]

        # Quality keywords
        if any(kw in query_lower for kw in ["best", "high quality", "excellent"]):
            auto_filters["quality"] = ["excellent"]

        # Cost keywords
        if any(kw in query_lower for kw in ["free", "cheap", "low cost", "local"]):
            auto_filters["cost"] = ["free"]
        elif any(kw in query_lower for kw in ["expensive", "premium", "cloud"]):
            auto_filters["cost"] = ["high", "very-high", "medium"]

        # Task keywords
        if any(kw in query_lower for kw in ["code", "coding", "programming"]):
            auto_filters["best_for_contains"] = "code"
        elif any(kw in query_lower for kw in ["summary", "summarize", "summarization"]):
            auto_filters["task_type"] = "summary"
        elif any(kw in query_lower for kw in ["content", "writing", "creative"]):
            auto_filters["best_for_contains"] = "content"

        # Context window keywords
        if any(kw in query_lower for kw in ["large context", "long context", "big context"]):
            auto_filters["min_context_window"] = 50000

        # Merge with explicit filters
        if filter_by:
            auto_filters.update(filter_by)

        # Filter models
        matching = []
        for backend_model_id, info in self.backends.items():
            match = True

            # Check each filter
            for key, values in auto_filters.items():
                if key == "best_for_contains":
                    # Special case: check if any best_for item contains the value
                    if not any(values in bf for bf in info.get("best_for", [])):
                        match = False
                        break
                elif key == "min_context_window":
                    # Special case: minimum context window
                    if info.get("context_window", 0) < values:
                        match = False
                        break
                elif key == "task_type":
                    # Special case: check best_for list
                    if not any(values in bf for bf in info.get("best_for", [])):
                        match = False
                        break
                else:
                    # Standard filter
                    model_value = info.get(key)
                    if model_value:
                        if isinstance(values, list):
                            if model_value not in values:
                                match = False
                                break
                        else:
                            if model_value != values:
                                match = False
                                break

            if match:
                matching.append({
                    "backend_model_id": backend_model_id,
                    **info
                })

        # Sort by quality and speed
        matching.sort(
            key=lambda m: (
                {"excellent": 3, "good": 2, "fair": 1}.get(m.get("quality", "good"), 2),
                {"very-fast": 4, "fast": 3, "medium": 2, "slow": 1}.get(m.get("speed", "medium"), 2)
            ),
            reverse=True
        )

        return matching

    def get_client_for_selection(self, selection: Dict[str, Any]):
        """
        Create an LLM client for a model selection.

        Args:
            selection: Selection dict from select_model()

        Returns:
            LLM client instance
        """
        backend = selection["backend"]
        return LLMClientFactory.create_from_config(self.config, backend)


def create_model_selector_tool(config_manager, tools_manager):
    """
    Factory function to create and register model selector tool.

    Args:
        config_manager: ConfigManager instance
        tools_manager: ToolsManager instance

    Returns:
        Registered Tool instance
    """
    selector = ModelSelectorTool(config_manager)

    tool = Tool(
        tool_id="model_selector",
        name="Model Selector",
        tool_type=ToolType.CUSTOM,
        description=(
            "Intelligently select the best backend and model for a given task. "
            "Supports natural language selection like 'use GPT-4' or 'use Claude'. "
            "Considers speed, cost, quality, and context window requirements. "
            "Available backends: Ollama, OpenAI, Anthropic, Azure, LM Studio."
        ),
        tags=["selection", "optimization", "model-management", "planning", "backend"],
        implementation=selector,
        parameters={
            "task_description": {
                "type": "string",
                "description": "Description of the task to perform"
            },
            "constraints": {
                "type": "object",
                "description": "Optional constraints like max_cost, min_speed"
            },
            "backend_preference": {
                "type": "string",
                "description": "Preferred backend (openai, anthropic, azure, etc.)"
            },
            "model_preference": {
                "type": "string",
                "description": "Preferred specific model name"
            },
            "top_k": {
                "type": "number",
                "description": "Number of recommendations to return (default: 3)"
            },
            "query": {
                "type": "string",
                "description": "Conversational query like 'what fast summary models do we have'"
            },
            "filter_by": {
                "type": "object",
                "description": "Optional filters for query_models"
            }
        },
        metadata={
            "speed_tier": "very-fast",
            "cost_tier": "free",
            "quality_tier": "excellent",
            "latency_ms": 50,
            "capability": "Model and backend selection with multi-backend support"
        }
    )

    tools_manager.register_tool(tool)
    logger.info("Registered model_selector tool")
    return tool
