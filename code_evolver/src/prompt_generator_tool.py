"""
Prompt Generator Tool with Layered Architecture.

A sophisticated prompt builder that uses a tiered/layered approach to construct
high-quality prompts for LLM interactions. Supports weight adjustment,
role-based tiers, and dynamic tool creation.

Features:
- Layered prompt architecture (system, role, context, task, constraints, output)
- Weight adjustment for section importance
- Model selection integration for conversational queries
- Dynamic LLM tool creation from descriptions
- Quality, speed, context length metadata for safe usage

Example:
    "Create a prompt for code review with emphasis on security"
    "What fast summary models do we have?"
    "Generate a translation tool using the best multilingual model"
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional, List, Union
from enum import Enum

logger = logging.getLogger(__name__)


class PromptTier(Enum):
    """Prompt complexity tiers matching model tiers."""
    TIER_1 = "tier_1"  # Simple, fast prompts
    TIER_2 = "tier_2"  # Standard prompts
    TIER_3 = "tier_3"  # Complex, detailed prompts


class PromptLayer(Enum):
    """Layers in the prompt structure."""
    SYSTEM = "system"           # System-level instructions
    ROLE = "role"               # Role definition and persona
    CONTEXT = "context"         # Background information
    TASK = "task"               # Specific task description
    CONSTRAINTS = "constraints" # Limitations and requirements
    OUTPUT = "output"           # Output format specification
    EXAMPLES = "examples"       # Example inputs/outputs


@dataclass
class LayeredPrompt:
    """
    A prompt with multiple layers and configurable weights.

    Each layer contributes to the final prompt with an adjustable weight.
    Higher weights = more emphasis in the final prompt.
    """
    system: str = ""
    role: str = ""
    context: str = ""
    task: str = ""
    constraints: str = ""
    output: str = ""
    examples: List[Dict[str, str]] = field(default_factory=list)

    # Layer weights (0.0 to 1.0)
    weights: Dict[str, float] = field(default_factory=lambda: {
        "system": 1.0,
        "role": 0.8,
        "context": 0.7,
        "task": 1.0,
        "constraints": 0.9,
        "output": 0.8,
        "examples": 0.6
    })

    # Metadata
    tier: PromptTier = PromptTier.TIER_2
    temperature: float = 0.7
    max_tokens: int = 2048

    def build(self, format_style: str = "markdown") -> str:
        """
        Build the final prompt from all layers.

        Args:
            format_style: "markdown", "xml", or "plain"

        Returns:
            Complete prompt string
        """
        sections = []

        # Build each layer with weight consideration
        if self.system and self.weights.get("system", 0) > 0:
            sections.append(self._format_section(
                "SYSTEM", self.system, format_style, self.weights["system"]
            ))

        if self.role and self.weights.get("role", 0) > 0:
            sections.append(self._format_section(
                "ROLE", self.role, format_style, self.weights["role"]
            ))

        if self.context and self.weights.get("context", 0) > 0:
            sections.append(self._format_section(
                "CONTEXT", self.context, format_style, self.weights["context"]
            ))

        if self.task and self.weights.get("task", 0) > 0:
            sections.append(self._format_section(
                "TASK", self.task, format_style, self.weights["task"]
            ))

        if self.constraints and self.weights.get("constraints", 0) > 0:
            sections.append(self._format_section(
                "CONSTRAINTS", self.constraints, format_style, self.weights["constraints"]
            ))

        if self.output and self.weights.get("output", 0) > 0:
            sections.append(self._format_section(
                "OUTPUT FORMAT", self.output, format_style, self.weights["output"]
            ))

        if self.examples and self.weights.get("examples", 0) > 0:
            examples_text = self._format_examples(self.examples, format_style)
            sections.append(self._format_section(
                "EXAMPLES", examples_text, format_style, self.weights["examples"]
            ))

        return "\n\n".join(sections)

    def _format_section(
        self,
        title: str,
        content: str,
        style: str,
        weight: float
    ) -> str:
        """Format a section based on weight and style."""
        # Weight affects emphasis
        if weight >= 0.9:
            emphasis = "CRITICAL: " if style != "xml" else ""
        elif weight >= 0.7:
            emphasis = "IMPORTANT: " if style != "xml" else ""
        else:
            emphasis = ""

        if style == "markdown":
            return f"## {emphasis}{title}\n\n{content}"
        elif style == "xml":
            tag = title.lower().replace(" ", "_")
            weight_attr = f' weight="{weight:.2f}"' if weight != 1.0 else ""
            return f"<{tag}{weight_attr}>\n{content}\n</{tag}>"
        else:  # plain
            return f"{emphasis}{title}:\n{content}"

    def _format_examples(self, examples: List[Dict[str, str]], style: str) -> str:
        """Format examples section."""
        formatted = []
        for i, example in enumerate(examples, 1):
            if style == "markdown":
                formatted.append(
                    f"**Example {i}:**\n"
                    f"Input: {example.get('input', 'N/A')}\n"
                    f"Output: {example.get('output', 'N/A')}"
                )
            elif style == "xml":
                formatted.append(
                    f"<example>\n"
                    f"  <input>{example.get('input', 'N/A')}</input>\n"
                    f"  <output>{example.get('output', 'N/A')}</output>\n"
                    f"</example>"
                )
            else:  # plain
                formatted.append(
                    f"Example {i}:\n"
                    f"  Input: {example.get('input', 'N/A')}\n"
                    f"  Output: {example.get('output', 'N/A')}"
                )
        return "\n\n".join(formatted)

    def adjust_weight(self, layer: str, new_weight: float) -> None:
        """Adjust the weight of a specific layer."""
        if layer in self.weights:
            self.weights[layer] = max(0.0, min(1.0, new_weight))
        else:
            logger.warning(f"Unknown layer: {layer}")

    def to_dict(self) -> Dict[str, Any]:
        """Export to dictionary."""
        result = asdict(self)
        result["tier"] = self.tier.value
        return result


class PromptGeneratorTool:
    """
    Tool for generating layered prompts with weight adjustment and model selection.

    Capabilities:
    1. Generate prompts from descriptions
    2. Query available models conversationally
    3. Create dynamic LLM tools
    4. Adjust prompt weights for emphasis
    """

    def __init__(self, config_manager, tools_manager=None):
        """
        Initialize prompt generator.

        Args:
            config_manager: ConfigManager instance
            tools_manager: Optional ToolsManager for dynamic tool creation
        """
        self.config = config_manager
        self.tools_manager = tools_manager
        self.model_registry = self._load_model_registry()

    def _load_model_registry(self) -> Dict[str, Dict[str, Any]]:
        """Load available models from config."""
        llm_config = self.config.config.get("llm", {})
        models = llm_config.get("models", {})

        registry = {}
        for model_id, model_info in models.items():
            registry[model_id] = {
                "id": model_id,
                "name": model_info.get("name"),
                "backend": model_info.get("backend"),
                "context_window": model_info.get("context_window", 8192),
                "cost": model_info.get("cost", "medium"),
                "speed": model_info.get("speed", "medium"),
                "quality": model_info.get("quality", "good"),
                "specialization": model_info.get("specialization", "general"),
                "timeout": model_info.get("timeout", 120)
            }

        return registry

    def query_models(
        self,
        query: str,
        filter_by: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Query available models conversationally.

        Args:
            query: Natural language query like "what fast summary models do we have"
            filter_by: Optional filters like {"speed": "fast", "specialization": "code"}

        Returns:
            List of matching models with metadata
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
            auto_filters["quality"] = ["excellent", "exceptional"]

        # Cost keywords
        if any(kw in query_lower for kw in ["free", "cheap", "low cost"]):
            auto_filters["cost"] = ["free", "very-low", "low"]
        elif any(kw in query_lower for kw in ["expensive", "premium"]):
            auto_filters["cost"] = ["high", "very-high"]

        # Specialization keywords
        if any(kw in query_lower for kw in ["code", "programming", "coding"]):
            auto_filters["specialization"] = ["code"]
        elif any(kw in query_lower for kw in ["summary", "summarize", "summarization"]):
            auto_filters["task_type"] = ["summary", "content"]
        elif any(kw in query_lower for kw in ["content", "writing", "creative"]):
            auto_filters["specialization"] = ["content", "general"]

        # Merge with explicit filters
        if filter_by:
            auto_filters.update(filter_by)

        # Filter models
        matching = []
        for model_id, model_info in self.model_registry.items():
            match = True

            # Check each filter
            for key, values in auto_filters.items():
                model_value = model_info.get(key)
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
                matching.append(model_info)

        # Sort by relevance (quality, speed, cost)
        matching.sort(
            key=lambda m: (
                -{"exceptional": 4, "excellent": 3, "good": 2, "fair": 1}.get(m.get("quality", "good"), 2),
                -{"very-fast": 4, "fast": 3, "medium": 2, "slow": 1}.get(m.get("speed", "medium"), 2)
            ),
            reverse=False
        )

        return matching

    def generate_prompt(
        self,
        description: str,
        task_type: Optional[str] = None,
        tier: Optional[str] = None,
        weights: Optional[Dict[str, float]] = None,
        format_style: str = "markdown"
    ) -> Dict[str, Any]:
        """
        Generate a layered prompt from a description.

        Args:
            description: Task description
            task_type: Optional task type (code, content, analysis, etc.)
            tier: Optional tier (tier_1, tier_2, tier_3)
            weights: Optional weight overrides
            format_style: Output format (markdown, xml, plain)

        Returns:
            Dict with prompt, metadata, and suggested models
        """
        # Infer task type if not provided
        if not task_type:
            task_type = self._infer_task_type(description)

        # Infer tier if not provided
        if not tier:
            tier = self._infer_tier(description)

        # Build layered prompt
        prompt = LayeredPrompt(tier=PromptTier(tier))

        # System layer
        prompt.system = self._generate_system_layer(task_type)

        # Role layer
        prompt.role = self._generate_role_layer(task_type)

        # Context layer
        prompt.context = self._generate_context_layer(description, task_type)

        # Task layer
        prompt.task = description

        # Constraints layer
        prompt.constraints = self._generate_constraints_layer(task_type, tier)

        # Output layer
        prompt.output = self._generate_output_layer(task_type)

        # Apply weight overrides
        if weights:
            for layer, weight in weights.items():
                prompt.adjust_weight(layer, weight)

        # Build final prompt
        final_prompt = prompt.build(format_style)

        # Suggest models
        suggested_models = self._suggest_models(task_type, tier)

        return {
            "prompt": final_prompt,
            "layers": prompt.to_dict(),
            "metadata": {
                "task_type": task_type,
                "tier": tier,
                "format_style": format_style,
                "temperature": prompt.temperature,
                "max_tokens": prompt.max_tokens
            },
            "suggested_models": suggested_models
        }

    def _infer_task_type(self, description: str) -> str:
        """Infer task type from description."""
        desc_lower = description.lower()

        if any(kw in desc_lower for kw in ["code", "function", "script", "debug", "refactor"]):
            return "code"
        elif any(kw in desc_lower for kw in ["write", "article", "story", "content"]):
            return "content"
        elif any(kw in desc_lower for kw in ["analyze", "review", "assess", "evaluate"]):
            return "analysis"
        elif any(kw in desc_lower for kw in ["summary", "summarize", "tldr"]):
            return "summary"
        elif any(kw in desc_lower for kw in ["translate", "translation"]):
            return "translation"
        else:
            return "general"

    def _infer_tier(self, description: str) -> str:
        """Infer complexity tier from description."""
        desc_lower = description.lower()

        # Check for complexity indicators
        if any(kw in desc_lower for kw in ["complex", "detailed", "thorough", "deep", "comprehensive"]):
            return "tier_3"
        elif any(kw in desc_lower for kw in ["simple", "quick", "basic", "fast"]):
            return "tier_1"
        else:
            return "tier_2"

    def _generate_system_layer(self, task_type: str) -> str:
        """Generate system layer based on task type."""
        templates = {
            "code": "You are an expert software engineer specializing in clean, efficient, and maintainable code.",
            "content": "You are a creative content writer skilled in producing engaging, high-quality text.",
            "analysis": "You are an analytical expert capable of deep evaluation and assessment.",
            "summary": "You are a summarization specialist focused on extracting key information concisely.",
            "translation": "You are a professional translator with expertise in multiple languages.",
            "general": "You are a helpful AI assistant designed to assist with a wide range of tasks."
        }
        return templates.get(task_type, templates["general"])

    def _generate_role_layer(self, task_type: str) -> str:
        """Generate role layer based on task type."""
        templates = {
            "code": "Your role is to write, review, or optimize code with attention to best practices and performance.",
            "content": "Your role is to create compelling content that meets the user's specifications.",
            "analysis": "Your role is to provide thorough analysis with clear reasoning and evidence.",
            "summary": "Your role is to distill information into clear, concise summaries.",
            "translation": "Your role is to accurately translate text while preserving meaning and tone.",
            "general": "Your role is to understand the user's needs and provide helpful, accurate responses."
        }
        return templates.get(task_type, templates["general"])

    def _generate_context_layer(self, description: str, task_type: str) -> str:
        """Generate context layer."""
        return f"The user requires assistance with: {description}"

    def _generate_constraints_layer(self, task_type: str, tier: str) -> str:
        """Generate constraints layer."""
        base_constraints = [
            "Provide accurate and helpful responses",
            "Follow best practices for the task type",
            "Be concise yet thorough"
        ]

        if tier == "tier_1":
            base_constraints.append("Prioritize speed and simplicity")
        elif tier == "tier_3":
            base_constraints.append("Provide comprehensive, detailed responses")

        if task_type == "code":
            base_constraints.extend([
                "Include error handling",
                "Add appropriate comments",
                "Follow language-specific conventions"
            ])

        return "\n".join(f"- {c}" for c in base_constraints)

    def _generate_output_layer(self, task_type: str) -> str:
        """Generate output format layer."""
        templates = {
            "code": "Provide code in markdown code blocks with language specification. Include brief explanations.",
            "content": "Provide the content directly without meta-commentary. Format appropriately.",
            "analysis": "Structure your analysis with clear sections: Overview, Key Points, Conclusion.",
            "summary": "Provide a concise summary with bullet points for key information.",
            "translation": "Provide the translation directly. Indicate the target language.",
            "general": "Format your response clearly and appropriately for the task."
        }
        return templates.get(task_type, templates["general"])

    def _suggest_models(self, task_type: str, tier: str) -> List[Dict[str, Any]]:
        """Suggest appropriate models for the task and tier."""
        # Determine desired characteristics
        if tier == "tier_1":
            speed_pref = ["very-fast", "fast"]
            quality_pref = ["good", "excellent"]
        elif tier == "tier_3":
            speed_pref = ["slow", "medium", "fast"]
            quality_pref = ["exceptional", "excellent"]
        else:  # tier_2
            speed_pref = ["fast", "medium"]
            quality_pref = ["excellent", "good"]

        # Filter by specialization
        specialization_map = {
            "code": "code",
            "content": "content",
            "summary": "general",
            "translation": "general",
            "analysis": "general",
            "general": "general"
        }

        preferred_spec = specialization_map.get(task_type, "general")

        # Find matching models
        suggestions = []
        for model_info in self.model_registry.values():
            score = 0

            # Speed match
            if model_info.get("speed") in speed_pref:
                score += 30

            # Quality match
            if model_info.get("quality") in quality_pref:
                score += 40

            # Specialization match
            if model_info.get("specialization") == preferred_spec:
                score += 30

            if score > 0:
                suggestions.append({
                    **model_info,
                    "match_score": score
                })

        # Sort by score
        suggestions.sort(key=lambda x: x["match_score"], reverse=True)

        return suggestions[:5]  # Top 5 suggestions

    def create_dynamic_tool(
        self,
        tool_name: str,
        description: str,
        task_type: Optional[str] = None,
        model_preference: Optional[str] = None,
        tier: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a dynamic LLM tool from a description.

        Args:
            tool_name: Name for the new tool
            description: What the tool should do
            task_type: Optional task type
            model_preference: Optional specific model
            tier: Optional tier

        Returns:
            Tool definition dict
        """
        # Generate prompt
        prompt_result = self.generate_prompt(description, task_type, tier)

        # Select model
        if model_preference:
            # Find specific model
            model = self.model_registry.get(model_preference)
            if not model:
                # Try to find by name
                for m in self.model_registry.values():
                    if m["name"] == model_preference:
                        model = m
                        break
        else:
            # Use top suggestion
            model = prompt_result["suggested_models"][0] if prompt_result["suggested_models"] else None

        if not model:
            raise ValueError(f"Could not find suitable model for tool: {tool_name}")

        # Build tool definition
        tool_def = {
            "name": tool_name,
            "type": "llm",
            "description": description,
            "llm": {
                "model": model["name"],
                "backend": model["backend"],
                "temperature": prompt_result["metadata"]["temperature"],
                "max_tokens": prompt_result["metadata"]["max_tokens"],
                "system_prompt": prompt_result["layers"]["system"],
                "prompt_template": prompt_result["prompt"]
            },
            "metadata": {
                "cost_tier": model["cost"],
                "speed_tier": model["speed"],
                "quality_tier": model["quality"],
                "context_window": model["context_window"],
                "timeout": model["timeout"],
                "generated_by": "prompt_generator",
                "task_type": prompt_result["metadata"]["task_type"],
                "tier": prompt_result["metadata"]["tier"]
            },
            "tags": [
                "dynamic",
                "generated",
                task_type or "general",
                model["specialization"]
            ]
        }

        return tool_def


def create_prompt_generator_tool(config_manager, tools_manager):
    """
    Factory function to create and register prompt generator tool.

    Args:
        config_manager: ConfigManager instance
        tools_manager: ToolsManager instance

    Returns:
        PromptGeneratorTool instance
    """
    from .tools_manager import Tool, ToolType

    generator = PromptGeneratorTool(config_manager, tools_manager)

    tool = Tool(
        tool_id="prompt_generator",
        name="Layered Prompt Generator",
        tool_type=ToolType.CUSTOM,
        description=(
            "Generates sophisticated layered prompts with weight adjustment and model selection. "
            "Supports conversational model queries like 'what fast summary models do we have'. "
            "Can create dynamic LLM tools from descriptions. "
            "Uses tiered architecture matching the system's model tiers (tier_1, tier_2, tier_3)."
        ),
        tags=["prompt-engineering", "prompt-generation", "layered", "dynamic", "tool-creation"],
        implementation=generator,
        parameters={
            "description": {
                "type": "string",
                "description": "Description of the task or tool to create"
            },
            "task_type": {
                "type": "string",
                "description": "Optional task type (code, content, analysis, summary, translation, general)"
            },
            "tier": {
                "type": "string",
                "description": "Optional complexity tier (tier_1, tier_2, tier_3)"
            },
            "weights": {
                "type": "object",
                "description": "Optional weight overrides for layers (system, role, context, task, constraints, output, examples)"
            },
            "format_style": {
                "type": "string",
                "description": "Output format style (markdown, xml, plain)"
            },
            "model_query": {
                "type": "string",
                "description": "Conversational model query like 'what fast code models do we have'"
            },
            "create_tool": {
                "type": "boolean",
                "description": "Whether to create a dynamic tool definition"
            },
            "tool_name": {
                "type": "string",
                "description": "Name for the dynamic tool (if create_tool is true)"
            }
        },
        metadata={
            "speed_tier": "fast",
            "cost_tier": "free",
            "quality_tier": "excellent",
            "capability": "Layered prompt generation with model selection and dynamic tool creation"
        }
    )

    tools_manager.register_tool(tool)
    logger.info("Registered prompt_generator tool")
    return generator
