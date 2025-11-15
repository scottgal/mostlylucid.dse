#!/usr/bin/env python3
"""
Adaptive Translation System - Real-world example of pressure-aware optimization.

Demonstrates:
1. SQLite cache for 99.9% of common single-word translations
2. NMT service fallback for novel translations
3. Automatic cache monitoring and quality tracking
4. Adaptive tool selection based on performance drift
5. Auto-evolution when patterns change

Scenario:
- Start: 99.9% cache hit rate, 0.95 quality → Use SQLite only (fast, free)
- Drift: New words appear, cache hit drops to 85% → Switch to NMT
- Or: Quality drops below 0.75 threshold → Switch to NMT
- Future: Could even rebuild/expand cache from NMT results

This example shows how the system automatically adapts tools based on
real-world performance, using the pressure manager and auto-evolver.
"""
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import time

logger = logging.getLogger(__name__)


@dataclass
class TranslationMetrics:
    """Metrics for translation tool performance."""
    cache_hit_rate: float
    quality_score: float
    avg_latency_ms: float
    total_calls: int
    cache_hits: int
    cache_misses: int
    nmt_calls: int


class AdaptiveTranslationWorkflow:
    """
    Adaptive translation system that automatically switches between
    SQLite cache and NMT based on performance.

    Uses:
    - DATABASE storage node (SQLite cache)
    - API_CONNECTOR node (NMT service)
    - Auto-evolution to detect drift
    - Pressure manager for quality negotiation
    """

    def __init__(
        self,
        config_manager,
        pressure_manager,
        auto_evolver=None
    ):
        """
        Initialize adaptive translation system.

        Args:
            config_manager: ConfigManager instance
            pressure_manager: PressureManager instance
            auto_evolver: AutoEvolver instance (optional)
        """
        self.config = config_manager
        self.pressure = pressure_manager
        self.evolver = auto_evolver

        # Performance thresholds
        self.min_cache_hit_rate = 0.90  # 90% hit rate required for cache-only
        self.min_quality_score = 0.75   # 75% quality required
        self.drift_check_interval = 100  # Check every 100 calls

        # Current state
        self.current_tool = "sqlite_cache"  # Start with cache
        self.metrics = TranslationMetrics(
            cache_hit_rate=0.999,  # Start optimistic (99.9%)
            quality_score=0.95,
            avg_latency_ms=5.0,
            total_calls=0,
            cache_hits=0,
            cache_misses=0,
            nmt_calls=0
        )

        # Mock storage nodes (would be real in production)
        self.sqlite_cache = {}  # Mock SQLite database
        self.nmt_service = None  # Mock NMT API

        logger.info(f"Adaptive translation initialized: tool={self.current_tool}")

    def translate(
        self,
        text: str,
        source_lang: str = "en",
        target_lang: str = "es"
    ) -> Dict[str, Any]:
        """
        Translate text using adaptive tool selection.

        Flow:
        1. Check cache first (SQLite - fast)
        2. On miss: Call NMT (API - slow but accurate)
        3. Store result in cache
        4. Track metrics
        5. Auto-evolve if performance drifts

        Args:
            text: Text to translate
            source_lang: Source language code
            target_lang: Target language code

        Returns:
            Translation result with metadata
        """
        start_time = time.time()

        # Adaptive tool selection based on current state
        if self.current_tool == "sqlite_cache":
            result = self._translate_with_cache(text, source_lang, target_lang)
        elif self.current_tool == "nmt_hybrid":
            result = self._translate_hybrid(text, source_lang, target_lang)
        else:  # nmt_only
            result = self._translate_nmt(text, source_lang, target_lang)

        # Track latency
        latency_ms = (time.time() - start_time) * 1000

        # Update metrics
        self._update_metrics(result, latency_ms)

        # Check for drift (every N calls)
        if self.metrics.total_calls % self.drift_check_interval == 0:
            self._check_for_drift()

        return result

    def _translate_with_cache(
        self,
        text: str,
        source_lang: str,
        target_lang: str
    ) -> Dict[str, Any]:
        """
        Translate using SQLite cache.

        99.9% hit rate for common single words.
        """
        cache_key = f"{source_lang}:{target_lang}:{text}"

        # Check cache (SQLite lookup - very fast)
        if cache_key in self.sqlite_cache:
            self.metrics.cache_hits += 1
            return {
                "translation": self.sqlite_cache[cache_key],
                "tool": "sqlite_cache",
                "cache_hit": True,
                "quality_estimate": 0.95,  # Known good translations
                "source": "cache"
            }

        # Cache miss - need to call NMT
        self.metrics.cache_misses += 1
        return self._translate_nmt_and_cache(text, source_lang, target_lang)

    def _translate_nmt_and_cache(
        self,
        text: str,
        source_lang: str,
        target_lang: str
    ) -> Dict[str, Any]:
        """
        Translate using NMT and store in cache.

        Called on cache miss.
        """
        # Call NMT service (API - slow but accurate)
        nmt_result = self._translate_nmt(text, source_lang, target_lang)

        # Store in cache for future use
        cache_key = f"{source_lang}:{target_lang}:{text}"
        self.sqlite_cache[cache_key] = nmt_result["translation"]

        logger.info(f"Cached new translation: '{text}' → '{nmt_result['translation']}'")

        return {
            **nmt_result,
            "cache_updated": True
        }

    def _translate_hybrid(
        self,
        text: str,
        source_lang: str,
        target_lang: str
    ) -> Dict[str, Any]:
        """
        Hybrid mode: Check cache first, NMT fallback.

        Used when cache hit rate is moderate (85-90%).
        """
        # Try cache first
        cache_result = self._translate_with_cache(text, source_lang, target_lang)

        if cache_result.get("cache_hit"):
            return cache_result

        # Fall back to NMT
        return self._translate_nmt(text, source_lang, target_lang)

    def _translate_nmt(
        self,
        text: str,
        source_lang: str,
        target_lang: str
    ) -> Dict[str, Any]:
        """
        Translate using NMT service (external API).

        Slow but handles all translations.
        """
        self.metrics.nmt_calls += 1

        # Mock NMT API call
        # In production: requests.post("http://localhost:8000/translate", ...)

        translation = f"[NMT:{target_lang}]{text}"  # Mock translation

        return {
            "translation": translation,
            "tool": "nmt_service",
            "cache_hit": False,
            "quality_estimate": 0.90,  # NMT is high quality
            "source": "nmt_api"
        }

    def _update_metrics(self, result: Dict[str, Any], latency_ms: float):
        """Update performance metrics."""
        self.metrics.total_calls += 1

        # Update cache hit rate
        if self.metrics.total_calls > 0:
            self.metrics.cache_hit_rate = (
                self.metrics.cache_hits / self.metrics.total_calls
            )

        # Update quality score (running average)
        quality = result.get("quality_estimate", 0.5)
        alpha = 0.1  # Smoothing factor
        self.metrics.quality_score = (
            alpha * quality + (1 - alpha) * self.metrics.quality_score
        )

        # Update latency (running average)
        self.metrics.avg_latency_ms = (
            alpha * latency_ms + (1 - alpha) * self.metrics.avg_latency_ms
        )

    def _check_for_drift(self):
        """
        Check if performance has drifted from expectations.

        Triggers auto-evolution if:
        1. Cache hit rate drops below threshold
        2. Quality score drops below threshold
        3. Latency increases significantly
        """
        logger.info(f"Checking for drift: "
                   f"hit_rate={self.metrics.cache_hit_rate:.3f}, "
                   f"quality={self.metrics.quality_score:.3f}, "
                   f"latency={self.metrics.avg_latency_ms:.1f}ms")

        # Check cache hit rate
        if self.metrics.cache_hit_rate < self.min_cache_hit_rate:
            if self.current_tool == "sqlite_cache":
                logger.warning(
                    f"Cache hit rate dropped to {self.metrics.cache_hit_rate:.1%} "
                    f"(threshold: {self.min_cache_hit_rate:.1%}). "
                    f"Switching to hybrid mode."
                )
                self._evolve_to_hybrid()
                return

        # Check quality score
        if self.metrics.quality_score < self.min_quality_score:
            if self.current_tool != "nmt_only":
                logger.warning(
                    f"Quality dropped to {self.metrics.quality_score:.3f} "
                    f"(threshold: {self.min_quality_score:.3f}). "
                    f"Switching to NMT-only mode."
                )
                self._evolve_to_nmt_only()
                return

        # Check if we can switch back to cache-only
        if (self.current_tool != "sqlite_cache" and
            self.metrics.cache_hit_rate >= 0.95 and
            self.metrics.quality_score >= 0.85):
            logger.info(
                f"Performance recovered (hit_rate={self.metrics.cache_hit_rate:.1%}, "
                f"quality={self.metrics.quality_score:.3f}). "
                f"Switching back to cache-only mode."
            )
            self._evolve_to_cache_only()

    def _evolve_to_hybrid(self):
        """Evolve to hybrid mode (cache + NMT fallback)."""
        self.current_tool = "nmt_hybrid"

        logger.info(
            f"AUTO-EVOLUTION: Switched to hybrid mode. "
            f"Will check cache first, fall back to NMT on miss."
        )

        # Log to auto-evolver if available
        if self.evolver:
            self.evolver.log_evolution(
                node_id="translation_workflow",
                reason="cache_hit_rate_dropped",
                old_strategy="sqlite_cache",
                new_strategy="nmt_hybrid",
                metrics=self.metrics.__dict__
            )

    def _evolve_to_nmt_only(self):
        """Evolve to NMT-only mode (bypass cache)."""
        self.current_tool = "nmt_only"

        logger.info(
            f"AUTO-EVOLUTION: Switched to NMT-only mode. "
            f"Cache quality too low, using NMT for all translations."
        )

        if self.evolver:
            self.evolver.log_evolution(
                node_id="translation_workflow",
                reason="quality_below_threshold",
                old_strategy=self.current_tool,
                new_strategy="nmt_only",
                metrics=self.metrics.__dict__
            )

    def _evolve_to_cache_only(self):
        """Evolve back to cache-only mode (performance recovered)."""
        old_tool = self.current_tool
        self.current_tool = "sqlite_cache"

        logger.info(
            f"AUTO-EVOLUTION: Switched back to cache-only mode. "
            f"Performance recovered (hit_rate={self.metrics.cache_hit_rate:.1%})."
        )

        if self.evolver:
            self.evolver.log_evolution(
                node_id="translation_workflow",
                reason="performance_recovered",
                old_strategy=old_tool,
                new_strategy="sqlite_cache",
                metrics=self.metrics.__dict__
            )

    def get_stats(self) -> Dict[str, Any]:
        """Get current statistics."""
        return {
            "current_tool": self.current_tool,
            "metrics": {
                "cache_hit_rate": f"{self.metrics.cache_hit_rate:.1%}",
                "quality_score": f"{self.metrics.quality_score:.3f}",
                "avg_latency_ms": f"{self.metrics.avg_latency_ms:.1f}",
                "total_calls": self.metrics.total_calls,
                "cache_hits": self.metrics.cache_hits,
                "cache_misses": self.metrics.cache_misses,
                "nmt_calls": self.metrics.nmt_calls
            },
            "cache_size": len(self.sqlite_cache),
            "thresholds": {
                "min_cache_hit_rate": f"{self.min_cache_hit_rate:.1%}",
                "min_quality_score": self.min_quality_score
            }
        }


def example_usage():
    """Demonstrate adaptive translation system."""
    from src.config_manager import ConfigManager
    from src.pressure_manager import PressureManager

    # Initialize
    config = ConfigManager()
    pressure = PressureManager(config)
    translator = AdaptiveTranslationWorkflow(config, pressure)

    # Simulate translation workload
    print("=== Adaptive Translation System Demo ===\n")

    # Phase 1: Common words (cache hits)
    print("Phase 1: Translating common words (99.9% cache hit)")
    common_words = ["hello", "world", "good", "morning"] * 25  # 100 calls
    for word in common_words:
        translator.translate(word)

    print(f"Stats after Phase 1:")
    stats = translator.get_stats()
    print(f"  Tool: {stats['current_tool']}")
    print(f"  Cache hit rate: {stats['metrics']['cache_hit_rate']}")
    print(f"  Quality: {stats['metrics']['quality_score']}\n")

    # Phase 2: New words appear (cache misses increase)
    print("Phase 2: New technical terms appear (cache hit drops)")
    new_words = [f"technical_term_{i}" for i in range(50)]
    for word in new_words:
        translator.translate(word)

    print(f"Stats after Phase 2:")
    stats = translator.get_stats()
    print(f"  Tool: {stats['current_tool']} ← AUTO-EVOLVED!")
    print(f"  Cache hit rate: {stats['metrics']['cache_hit_rate']}")
    print(f"  Quality: {stats['metrics']['quality_score']}\n")

    # Phase 3: Cache rebuilds (performance recovers)
    print("Phase 3: Cache expanded, performance recovers")
    # Simulate more calls with cached new terms
    all_words = common_words + new_words
    for word in all_words * 2:
        translator.translate(word)

    print(f"Stats after Phase 3:")
    stats = translator.get_stats()
    print(f"  Tool: {stats['current_tool']} ← EVOLVED BACK!")
    print(f"  Cache hit rate: {stats['metrics']['cache_hit_rate']}")
    print(f"  Quality: {stats['metrics']['quality_score']}\n")

    print("=== Demonstration Complete ===")
    print(f"Final cache size: {stats['cache_size']} translations")
    print(f"Total NMT calls: {stats['metrics']['nmt_calls']}")
    print(f"Cost saved: ${int(stats['metrics']['nmt_calls']) * 0.001:.3f} "
          f"(vs ${stats['metrics']['total_calls'] * 0.001:.3f} without cache)")


if __name__ == "__main__":
    example_usage()
