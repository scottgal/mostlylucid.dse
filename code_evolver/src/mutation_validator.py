"""
Mutation Validator - Validates mutations during workflow execution and optimization.

CRITICAL: Always validate mutations before using them in workflows to ensure:
1. The mutation was optimized for a compatible LLM
2. The mutation is still appropriate for the current context
3. The mutation hasn't degraded over time

This prevents using Claude-optimized prompts on Llama, or stale mutations.
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class MutationValidator:
    """
    Validates mutations for use in workflows and optimization.

    Ensures mutations are compatible with current LLM configuration
    and haven't degraded over time.
    """

    def __init__(
        self,
        prompt_mutator=None,
        max_mutation_age_days: int = 90,
        min_usage_count: int = 3
    ):
        """
        Initialize validator.

        Args:
            prompt_mutator: PromptMutator instance
            max_mutation_age_days: Maximum age for mutations (default 90 days)
            min_usage_count: Minimum usage count for quality assessment
        """
        self.prompt_mutator = prompt_mutator
        self.max_mutation_age_days = max_mutation_age_days
        self.min_usage_count = min_usage_count

    def validate_for_workflow(
        self,
        mutation,
        current_llm_config: Dict[str, Any],
        strict: bool = False,
        check_age: bool = True,
        check_performance: bool = True
    ) -> Tuple[bool, List[str]]:
        """
        Comprehensive validation for workflow execution.

        Args:
            mutation: MutatedPrompt to validate
            current_llm_config: Current LLM configuration
            strict: If True, require exact LLM match
            check_age: If True, reject mutations older than max_age
            check_performance: If True, check performance metrics

        Returns:
            (is_valid, warnings) tuple where warnings contains issues found
        """
        warnings = []
        is_valid = True

        # 1. Check LLM compatibility
        if self.prompt_mutator:
            is_compatible, reason = self.prompt_mutator.check_mutation_compatibility(
                mutation,
                current_llm_config,
                strict=strict
            )

            if not is_compatible:
                warnings.append(f"LLM incompatibility: {reason}")
                is_valid = False
            elif "mismatch" in reason.lower() or "suboptimal" in reason.lower():
                warnings.append(f"Potential issue: {reason}")

        # 2. Check mutation age
        if check_age:
            try:
                created = datetime.fromisoformat(mutation.created_at.replace("Z", "+00:00"))
                age_days = (datetime.utcnow() - created.replace(tzinfo=None)).days

                if age_days > self.max_mutation_age_days:
                    warnings.append(
                        f"Mutation is {age_days} days old (max {self.max_mutation_age_days}). "
                        f"Consider regenerating for current best practices."
                    )
                    # Don't fail, just warn
                elif age_days > self.max_mutation_age_days / 2:
                    warnings.append(
                        f"Mutation is {age_days} days old. May need refresh."
                    )
            except Exception as e:
                warnings.append(f"Could not check mutation age: {e}")

        # 3. Check performance metrics
        if check_performance:
            usage_count = len(mutation.performance_metrics)

            if usage_count == 0:
                warnings.append(
                    "Mutation has never been used. Performance unknown."
                )
            elif usage_count < self.min_usage_count:
                warnings.append(
                    f"Mutation has only {usage_count} uses (min {self.min_usage_count}). "
                    f"Quality metrics may be unreliable."
                )
            else:
                avg_quality = mutation.get_average_quality()

                if avg_quality < 0.5:
                    warnings.append(
                        f"Low quality score: {avg_quality:.2f}. "
                        f"Consider using a different mutation."
                    )
                    is_valid = False
                elif avg_quality < 0.7:
                    warnings.append(
                        f"Below average quality: {avg_quality:.2f}"
                    )

                # Check for degradation (recent performance worse than historical)
                if len(mutation.performance_metrics) >= 5:
                    recent_metrics = mutation.performance_metrics[-3:]
                    historical_metrics = mutation.performance_metrics[:-3]

                    recent_quality = sum(
                        m["quality"] for m in recent_metrics if m["success"]
                    ) / max(1, sum(1 for m in recent_metrics if m["success"]))

                    historical_quality = sum(
                        m["quality"] for m in historical_metrics if m["success"]
                    ) / max(1, sum(1 for m in historical_metrics if m["success"]))

                    if recent_quality < historical_quality * 0.8:
                        warnings.append(
                            f"Performance degradation detected: "
                            f"recent {recent_quality:.2f} vs historical {historical_quality:.2f}"
                        )

        # 4. Check for rollbacks
        if mutation.rollback_count > 0:
            warnings.append(
                f"Mutation has been rolled back {mutation.rollback_count} time(s). "
                f"May be problematic."
            )

        return is_valid, warnings

    def select_best_compatible_mutation(
        self,
        tool_id: str,
        use_case: str,
        current_llm_config: Dict[str, Any],
        min_quality: float = 0.7,
        strict_compatibility: bool = False
    ) -> Optional[Any]:
        """
        Select the best mutation that's compatible with current LLM.

        WORKFLOW INTEGRATION: Use this in workflows to select mutations
        during optimization.

        Args:
            tool_id: Original tool ID
            use_case: Specific use case
            current_llm_config: Current LLM configuration
            min_quality: Minimum quality threshold
            strict_compatibility: If True, require exact LLM match

        Returns:
            Best compatible mutation or None
        """
        if not self.prompt_mutator:
            logger.warning("No PromptMutator available for mutation selection")
            return None

        # Get best mutation with compatibility filtering
        mutation = self.prompt_mutator.get_best_mutation_for_use_case(
            tool_id=tool_id,
            use_case=use_case,
            min_quality=min_quality,
            current_llm_config=current_llm_config,
            strict_compatibility=strict_compatibility
        )

        if not mutation:
            logger.info(
                f"No compatible mutation found for {tool_id} "
                f"on {current_llm_config.get('backend')}/{current_llm_config.get('model')}"
            )
            return None

        # Validate the selected mutation
        is_valid, warnings = self.validate_for_workflow(
            mutation,
            current_llm_config,
            strict=strict_compatibility
        )

        if not is_valid:
            logger.warning(
                f"Selected mutation {mutation.mutation_id} failed validation: "
                f"{'; '.join(warnings)}"
            )
            return None

        if warnings:
            logger.info(
                f"Using mutation {mutation.mutation_id} with warnings: "
                f"{'; '.join(warnings)}"
            )

        return mutation

    def validate_mutation_before_use(
        self,
        mutation,
        current_llm_config: Dict[str, Any],
        fail_on_warnings: bool = False
    ) -> bool:
        """
        Quick validation check before using a mutation.

        Use this in workflow execution to validate mutations at runtime.

        Args:
            mutation: MutatedPrompt to validate
            current_llm_config: Current LLM configuration
            fail_on_warnings: If True, reject mutations with any warnings

        Returns:
            True if mutation should be used, False otherwise

        Example:
            >>> validator = MutationValidator(mutator)
            >>> if validator.validate_mutation_before_use(mutation, llm_config):
            >>>     use_mutation(mutation)
            >>> else:
            >>>     use_original_prompt()
        """
        is_valid, warnings = self.validate_for_workflow(
            mutation,
            current_llm_config
        )

        if not is_valid:
            logger.warning(
                f"Mutation {mutation.mutation_id} is invalid: {'; '.join(warnings)}"
            )
            return False

        if fail_on_warnings and warnings:
            logger.warning(
                f"Mutation {mutation.mutation_id} rejected due to warnings: "
                f"{'; '.join(warnings)}"
            )
            return False

        return True


def validate_mutation_for_optimization(
    mutation,
    current_llm_config: Dict[str, Any],
    prompt_mutator=None
) -> Tuple[bool, str]:
    """
    Standalone validation function for use during optimization.

    OPTIMIZATION INTEGRATION: Call this during workflow optimization
    to ensure mutations are still appropriate.

    Args:
        mutation: MutatedPrompt to validate
        current_llm_config: Current LLM configuration
        prompt_mutator: Optional PromptMutator for compatibility checking

    Returns:
        (should_use, reason) tuple

    Example:
        >>> # During optimization
        >>> for potential_mutation in candidate_mutations:
        >>>     should_use, reason = validate_mutation_for_optimization(
        >>>         potential_mutation,
        >>>         workflow_llm_config,
        >>>         mutator
        >>>     )
        >>>     if should_use:
        >>>         apply_mutation(potential_mutation)
        >>>     else:
        >>>         logger.info(f"Skipping mutation: {reason}")
    """
    validator = MutationValidator(prompt_mutator)

    is_valid, warnings = validator.validate_for_workflow(
        mutation,
        current_llm_config,
        strict=False,  # Allow compatible models during optimization
        check_age=True,
        check_performance=True
    )

    if not is_valid:
        return False, f"Validation failed: {'; '.join(warnings)}"

    if warnings:
        return True, f"Valid with warnings: {'; '.join(warnings)}"

    return True, "Fully compatible and validated"


def get_validated_mutation_for_workflow(
    tool_id: str,
    use_case: str,
    current_llm_config: Dict[str, Any],
    prompt_mutator,
    fallback_to_original: bool = True
) -> Tuple[Optional[Any], bool]:
    """
    High-level function to get a validated mutation for workflow use.

    WORKFLOW HELPER: Use this in workflows to safely get mutations.

    Args:
        tool_id: Original tool ID
        use_case: Specific use case
        current_llm_config: Current LLM configuration
        prompt_mutator: PromptMutator instance
        fallback_to_original: If True, use original prompt if no valid mutation

    Returns:
        (mutation_or_none, is_mutation) tuple

    Example:
        >>> # In workflow execution
        >>> mutation, is_mutated = get_validated_mutation_for_workflow(
        >>>     "code_reviewer",
        >>>     "security audit",
        >>>     {"backend": "anthropic", "model": "claude-sonnet-4"},
        >>>     mutator
        >>> )
        >>>
        >>> if is_mutated:
        >>>     prompt = mutation.mutated_prompt_template
        >>> else:
        >>>     prompt = original_tool.prompt_template
    """
    validator = MutationValidator(prompt_mutator)

    mutation = validator.select_best_compatible_mutation(
        tool_id=tool_id,
        use_case=use_case,
        current_llm_config=current_llm_config,
        min_quality=0.7,
        strict_compatibility=False
    )

    if mutation:
        logger.info(
            f"Using validated mutation {mutation.mutation_id} for {tool_id} "
            f"(quality: {mutation.get_average_quality():.2f})"
        )
        return mutation, True

    if fallback_to_original:
        logger.info(
            f"No valid mutation found for {tool_id}, "
            f"falling back to original prompt"
        )
        return None, False

    return None, False
