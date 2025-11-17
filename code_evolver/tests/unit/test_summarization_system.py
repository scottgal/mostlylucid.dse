#!/usr/bin/env python3
"""
Unit Tests for Summarization System
"""

import pytest
from unittest.mock import Mock, patch
from src.summarization_system import (
    SummarizationSystem,
    SummarizerTier,
    TierSelector
)


@pytest.fixture
def mock_client():
    """Create mock Ollama client."""
    client = Mock()
    client.generate = Mock(return_value="Test summary")
    return client


@pytest.fixture
def summarization_system(mock_client):
    """Create SummarizationSystem instance."""
    return SummarizationSystem(ollama_client=mock_client)


def test_tier_selection_small_content(summarization_system):
    """Test tier selection for small content."""
    # Content < 8k tokens should use fast tier
    content_length = 2000  # tokens
    quality_req = 0.6
    speed_req = 0.8

    tier = summarization_system.choose_tier(content_length, quality_req, speed_req)

    assert tier.name == "fast"
    assert tier.model == "gemma2:2b"


def test_tier_selection_medium_content(summarization_system):
    """Test tier selection for medium content."""
    # Content 8k-32k tokens should use medium tier
    content_length = 16000  # tokens
    quality_req = 0.7
    speed_req = 0.5

    tier = summarization_system.choose_tier(content_length, quality_req, speed_req)

    assert tier.name == "medium"
    assert tier.model == "llama3"


def test_tier_selection_large_content(summarization_system):
    """Test tier selection for large content."""
    # Content > 32k tokens should use large tier
    content_length = 64000  # tokens
    quality_req = 0.8
    speed_req = 0.3

    tier = summarization_system.choose_tier(content_length, quality_req, speed_req)

    assert tier.name == "large"
    assert tier.model == "mistral-nemo"


def test_tier_selection_high_quality_requirement(summarization_system):
    """Test tier selection with high quality requirement."""
    # High quality requirement should prefer larger models
    content_length = 5000  # Could fit in fast tier
    quality_req = 0.9  # But quality is very important
    speed_req = 0.3

    tier = summarization_system.choose_tier(content_length, quality_req, speed_req)

    # Should escalate to higher tier for quality
    assert tier.quality_score >= quality_req


def test_tier_selection_high_speed_requirement(summarization_system):
    """Test tier selection with high speed requirement."""
    # High speed requirement should prefer smaller models
    content_length = 15000
    quality_req = 0.6
    speed_req = 0.9  # Very important speed

    tier = summarization_system.choose_tier(content_length, quality_req, speed_req)

    # Should prefer faster tier
    assert tier.speed_score >= 0.7


def test_summarizer_tier_properties():
    """Test SummarizerTier properties."""
    tier = SummarizerTier(
        name="test",
        model="test_model",
        context_window=8192,
        speed_score=0.9,
        quality_score=0.7,
        avg_time_per_1k=2.0
    )

    assert tier.name == "test"
    assert tier.model == "test_model"
    assert tier.context_window == 8192
    assert tier.speed_score == 0.9
    assert tier.quality_score == 0.7
    assert tier.avg_time_per_1k == 2.0


def test_summarize_single_shot(summarization_system):
    """Test single-shot summarization."""
    content = "Short content that fits in one chunk. " * 50
    quality_req = 0.7
    speed_req = 0.5

    result = summarization_system.summarize(content, quality_req, speed_req)

    assert "summary" in result
    assert "tier_used" in result
    assert "method" in result
    assert result["method"] == "single_shot"


def test_summarize_with_mantra(summarization_system):
    """Test summarization with mantra hints."""
    content = "Test content"

    # Test "quickly" mantra
    result_fast = summarization_system.summarize_with_mantra(content, "quickly summarize")

    assert result_fast["tier_used"] == "fast"

    # Test "carefully" mantra
    result_careful = summarization_system.summarize_with_mantra(content, "carefully summarize")

    assert result_careful["tier_used"] == "large"


def test_content_length_estimation():
    """Test content length estimation."""
    system = SummarizationSystem(ollama_client=Mock())

    # Rough estimation: 4 chars ~= 1 token
    content_1k = "word " * 800  # ~4000 chars ~= 1000 tokens
    estimated = system._estimate_tokens(content_1k)

    assert 900 <= estimated <= 1100  # Allow 10% variance


def test_tier_capabilities():
    """Test that tiers have correct capabilities."""
    system = SummarizationSystem(ollama_client=Mock())

    assert system.TIERS["fast"].context_window == 8192
    assert system.TIERS["medium"].context_window == 32768
    assert system.TIERS["large"].context_window == 131072

    assert system.TIERS["fast"].speed_score > system.TIERS["medium"].speed_score
    assert system.TIERS["medium"].speed_score > system.TIERS["large"].speed_score

    assert system.TIERS["large"].quality_score > system.TIERS["medium"].quality_score
    assert system.TIERS["medium"].quality_score > system.TIERS["fast"].quality_score


def test_progressive_summarization_trigger(summarization_system):
    """Test when progressive summarization is triggered."""
    # Create content larger than any tier's capacity
    very_large_content = "word " * 50000  # ~200k tokens

    result = summarization_system.summarize(very_large_content, 0.7, 0.5)

    # Should use progressive method
    assert result["method"] == "progressive"
    assert "num_chunks" in result
    assert result["num_chunks"] > 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
