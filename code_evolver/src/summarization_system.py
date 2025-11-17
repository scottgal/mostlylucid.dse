"""
Layered Summarization System - Smart Content Summarization

Multi-tier summarization with intelligent routing based on:
- Content size
- Quality requirements
- Context window capacity
- Speed vs quality tradeoffs

Tiers:
- Fast: gemma2:2b (small context, 8k tokens)
- Medium: llama3 (medium context, 32k tokens)
- Large: mistral-nemo (large context, 128k tokens)

Features:
- Automatic tier selection
- Progressive summarization for large content
- Split-summarize-merge for very large documents
- Caching of intermediate results
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class SummarizerTier:
    """Configuration for a summarizer tier."""
    name: str
    model: str
    context_window: int  # tokens
    speed_score: float   # 0-1 (higher = faster)
    quality_score: float # 0-1 (higher = better)
    cost_score: float    # 0-1 (higher = cheaper)


class SummarizationSystem:
    """
    Hierarchical summarization system with intelligent routing.

    Automatically selects best tier based on content size and requirements.
    """

    # Define summarizer tiers
    TIERS = {
        "fast": SummarizerTier(
            name="fast",
            model="gemma2:2b",
            context_window=8192,
            speed_score=0.95,
            quality_score=0.65,
            cost_score=0.95
        ),
        "medium": SummarizerTier(
            name="medium",
            model="llama3",
            context_window=32768,
            speed_score=0.70,
            quality_score=0.80,
            cost_score=0.70
        ),
        "large": SummarizerTier(
            name="large",
            model="mistral-nemo",
            context_window=131072,  # 128k
            speed_score=0.40,
            quality_score=0.90,
            cost_score=0.40
        )
    }

    def __init__(self, ollama_client, cache=None):
        """
        Initialize summarization system.

        Args:
            ollama_client: OllamaClient for generation
            cache: Optional cache for intermediate results
        """
        self.client = ollama_client
        self.cache = cache or {}

    def choose_tier(
        self,
        content_length: int,
        quality_requirement: float = 0.7,
        speed_requirement: float = 0.5
    ) -> SummarizerTier:
        """
        Choose best summarizer tier for content.

        Args:
            content_length: Number of tokens in content
            quality_requirement: Required quality (0-1)
            speed_requirement: Required speed (0-1)

        Returns:
            Best tier for this content
        """

        # Filter tiers that can handle this content size
        capable_tiers = [
            tier for tier in self.TIERS.values()
            if tier.context_window >= content_length
        ]

        if not capable_tiers:
            # Content too large for any single tier → need splitting
            logger.warning(f"Content ({content_length} tokens) exceeds largest context window")
            return self.TIERS["large"]  # Use largest for splits

        # Score each tier
        scored_tiers = []
        for tier in capable_tiers:
            # Check if tier meets minimum requirements
            if tier.quality_score < quality_requirement:
                continue
            if tier.speed_score < speed_requirement:
                continue

            # Combined score: balance quality, speed, cost
            score = (
                tier.quality_score * 0.4 +
                tier.speed_score * 0.3 +
                tier.cost_score * 0.3
            )

            scored_tiers.append((score, tier))

        if not scored_tiers:
            # No tier meets requirements, use best quality
            logger.warning("No tier meets requirements, using highest quality")
            return max(capable_tiers, key=lambda t: t.quality_score)

        # Return highest scoring tier
        best_tier = max(scored_tiers, key=lambda x: x[0])[1]
        logger.info(f"Selected tier: {best_tier.name} (context: {best_tier.context_window})")

        return best_tier

    def summarize(
        self,
        content: str,
        quality_requirement: float = 0.7,
        speed_requirement: float = 0.5,
        max_summary_length: int = 500
    ) -> Dict[str, Any]:
        """
        Summarize content with appropriate tier.

        Args:
            content: Content to summarize
            quality_requirement: Required quality (0-1)
            speed_requirement: Required speed (0-1)
            max_summary_length: Max tokens in summary

        Returns:
            Dict with summary and metadata
        """

        # Estimate content length in tokens (~4 chars per token)
        content_length = len(content) // 4

        # Check cache
        cache_key = self._cache_key(content, quality_requirement)
        if cache_key in self.cache:
            logger.info("Using cached summary")
            return self.cache[cache_key]

        # Choose tier
        tier = self.choose_tier(content_length, quality_requirement, speed_requirement)

        # Check if content needs splitting
        if content_length > tier.context_window * 0.8:  # 80% of context window
            logger.info(f"Content too large ({content_length} tokens), using progressive summarization")
            return self._progressive_summarize(
                content=content,
                tier=tier,
                max_summary_length=max_summary_length
            )

        # Single-shot summarization
        summary = self._single_summarize(
            content=content,
            tier=tier,
            max_summary_length=max_summary_length
        )

        result = {
            "summary": summary,
            "tier_used": tier.name,
            "content_length": content_length,
            "summary_length": len(summary) // 4,
            "method": "single_shot"
        }

        # Cache result
        self.cache[cache_key] = result

        return result

    def _single_summarize(
        self,
        content: str,
        tier: SummarizerTier,
        max_summary_length: int
    ) -> str:
        """Single-shot summarization."""

        prompt = f"""Summarize this content concisely (max {max_summary_length} tokens):

CONTENT:
{content}

SUMMARY:"""

        summary = self.client.generate(
            model=tier.model,
            prompt=prompt,
            temperature=0.3,
            max_tokens=max_summary_length
        )

        return summary.strip()

    def _progressive_summarize(
        self,
        content: str,
        tier: SummarizerTier,
        max_summary_length: int
    ) -> Dict[str, Any]:
        """
        Progressive summarization for large content.

        Strategy:
        1. Split content into chunks
        2. Summarize each chunk
        3. Merge summaries
        4. Final summary of merged summaries
        """

        logger.info("Starting progressive summarization...")

        # Split content
        chunks = self._split_content(
            content=content,
            max_chunk_size=tier.context_window // 2  # 50% of context for safety
        )

        logger.info(f"Split into {len(chunks)} chunks")

        # Summarize each chunk
        chunk_summaries = []
        for i, chunk in enumerate(chunks):
            logger.info(f"Summarizing chunk {i+1}/{len(chunks)}...")

            summary = self._single_summarize(
                content=chunk,
                tier=tier,
                max_summary_length=max_summary_length // len(chunks)
            )

            chunk_summaries.append(summary)

        # Merge chunk summaries
        merged = "\n\n".join(chunk_summaries)

        # Final summary of merged summaries
        logger.info("Creating final summary...")
        final_summary = self._single_summarize(
            content=merged,
            tier=tier,
            max_summary_length=max_summary_length
        )

        return {
            "summary": final_summary,
            "tier_used": tier.name,
            "content_length": len(content) // 4,
            "summary_length": len(final_summary) // 4,
            "method": "progressive",
            "num_chunks": len(chunks),
            "chunk_summaries": chunk_summaries  # For debugging
        }

    def _split_content(
        self,
        content: str,
        max_chunk_size: int
    ) -> List[str]:
        """
        Split content into chunks.

        Args:
            content: Content to split
            max_chunk_size: Max size per chunk (tokens)

        Returns:
            List of content chunks
        """

        # Estimate chars per chunk (4 chars ~= 1 token)
        max_chars = max_chunk_size * 4

        # Split on paragraphs first
        paragraphs = content.split('\n\n')

        chunks = []
        current_chunk = []
        current_length = 0

        for para in paragraphs:
            para_length = len(para)

            if current_length + para_length > max_chars:
                # Start new chunk
                if current_chunk:
                    chunks.append('\n\n'.join(current_chunk))
                current_chunk = [para]
                current_length = para_length
            else:
                current_chunk.append(para)
                current_length += para_length

        # Add last chunk
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))

        return chunks

    def _cache_key(self, content: str, quality: float) -> str:
        """Generate cache key for content."""
        content_hash = hashlib.md5(content.encode()).hexdigest()
        return f"{content_hash}_{quality:.2f}"

    def summarize_with_context(
        self,
        content: str,
        previous_summary: Optional[str] = None,
        quality_requirement: float = 0.7
    ) -> Dict[str, Any]:
        """
        Summarize with awareness of previous summary.

        Use case: Incremental summarization of streaming content.

        Args:
            content: New content to add
            previous_summary: Summary so far
            quality_requirement: Required quality

        Returns:
            Updated summary
        """

        if not previous_summary:
            # First chunk, regular summarization
            return self.summarize(content, quality_requirement)

        # Combine previous summary with new content
        combined = f"""PREVIOUS SUMMARY:
{previous_summary}

NEW CONTENT:
{content}

Create a comprehensive summary that incorporates both the previous summary
and the new content. Maintain continuity and avoid redundancy."""

        # Estimate length
        combined_length = len(combined) // 4

        # Choose tier
        tier = self.choose_tier(combined_length, quality_requirement)

        # Summarize
        summary = self._single_summarize(
            content=combined,
            tier=tier,
            max_summary_length=500
        )

        return {
            "summary": summary,
            "tier_used": tier.name,
            "method": "incremental",
            "previous_length": len(previous_summary) // 4,
            "new_content_length": len(content) // 4
        }


class SummarizationChooser:
    """
    Smart router for summarization requests.

    Analyzes request and determines:
    - Which tier to use
    - Whether to split
    - Whether to use progressive summarization
    """

    def __init__(self, summarization_system: SummarizationSystem):
        self.system = summarization_system

    def analyze_and_route(
        self,
        content: str,
        requirements: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze content and determine best summarization strategy.

        Args:
            content: Content to summarize
            requirements: Optional requirements dict

        Returns:
            Routing decision with strategy
        """

        req = requirements or {}

        # Analyze content
        content_length = len(content) // 4  # tokens
        has_structure = '\n\n' in content  # Paragraphs
        is_code = content.count('def ') + content.count('class ') > 5

        # Determine requirements
        quality_req = req.get("quality", 0.7)
        speed_req = req.get("speed", 0.5)

        # Adjust for content type
        if is_code:
            quality_req = max(quality_req, 0.8)  # Code needs higher quality

        # Choose tier
        tier = self.system.choose_tier(
            content_length=content_length,
            quality_requirement=quality_req,
            speed_requirement=speed_req
        )

        # Determine strategy
        if content_length < tier.context_window * 0.5:
            strategy = "single_shot"
        elif content_length < tier.context_window * 0.8:
            strategy = "single_shot_careful"  # Near limit
        else:
            strategy = "progressive"

        return {
            "strategy": strategy,
            "tier": tier.name,
            "content_length": content_length,
            "requires_splitting": strategy == "progressive",
            "estimated_chunks": max(1, content_length // (tier.context_window // 2)),
            "quality_requirement": quality_req,
            "reasoning": self._explain_choice(tier, strategy, content_length)
        }

    def _explain_choice(
        self,
        tier: SummarizerTier,
        strategy: str,
        content_length: int
    ) -> str:
        """Explain why this tier and strategy were chosen."""

        reasons = []

        reasons.append(f"Content: {content_length} tokens")
        reasons.append(f"Tier: {tier.name} ({tier.context_window} context)")
        reasons.append(f"Strategy: {strategy}")

        if strategy == "progressive":
            reasons.append("Content too large for single pass")

        return " | ".join(reasons)


# Example usage
def example_usage():
    """Example of layered summarization."""

    from src.ollama_client import OllamaClient

    client = OllamaClient("http://localhost:11434")
    system = SummarizationSystem(client)

    # Example 1: Small content → fast tier
    small_content = "Python is a programming language. " * 100  # ~400 tokens
    result = system.summarize(small_content, quality_requirement=0.6)
    print(f"Small content: {result['tier_used']} tier, {result['method']} method")
    # Uses: gemma2:2b (fast)

    # Example 2: Medium content → medium tier
    medium_content = "Python is a programming language. " * 2000  # ~8k tokens
    result = system.summarize(medium_content, quality_requirement=0.8)
    print(f"Medium content: {result['tier_used']} tier, {result['method']} method")
    # Uses: llama3 (medium)

    # Example 3: Large content → progressive with large tier
    large_content = "Python is a programming language. " * 10000  # ~40k tokens
    result = system.summarize(large_content, quality_requirement=0.9)
    print(f"Large content: {result['tier_used']} tier, {result['method']} method")
    # Uses: mistral-nemo (large), progressive method

    # Example 4: Smart routing
    chooser = SummarizationChooser(system)
    decision = chooser.analyze_and_route(large_content)
    print(f"Routing: {decision['strategy']} with {decision['tier']} tier")
    print(f"Reasoning: {decision['reasoning']}")


if __name__ == "__main__":
    example_usage()
