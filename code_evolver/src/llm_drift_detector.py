"""
LLM-Based Drift Detector - Uses Small LLM to Detect Semantic Drift

Uses a 4B parameter class LLM (e.g., qwen2.5-coder:4b) to detect drift between:
- Specification vs Implementation
- Interface vs Tests
- Tests vs Code
- Spec vs Interface

The LLM provides a drift score from 0-100:
- 0: Perfectly aligned
- 100: Nothing alike

This provides more nuanced detection than pure metric-based approaches.
"""

import logging
import json
import subprocess
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
import re

logger = logging.getLogger(__name__)


@dataclass
class DriftScore:
    """Drift score between two artifacts."""
    score: float  # 0-100 (0=aligned, 100=completely different)
    confidence: float  # 0-1.0 (how confident is the LLM)
    reasoning: str  # Why this score was given
    key_differences: list[str]  # Specific differences found


@dataclass
class ToolSplitRecommendation:
    """Recommendation on whether to split a tool."""
    should_split: bool
    confidence: float  # 0-1.0
    suggested_name: str  # Suggested new tool name (must be unique)
    reasoning: str  # Why split or not split
    drift_score: float  # 0-100 overall drift score


@dataclass
class ComprehensiveDrift:
    """Complete drift analysis for a tool."""
    spec_vs_code: DriftScore
    spec_vs_interface: DriftScore
    interface_vs_tests: DriftScore
    tests_vs_code: DriftScore

    @property
    def overall_drift(self) -> float:
        """Calculate overall drift score (weighted average)."""
        weights = {
            'spec_vs_code': 0.35,      # Most important
            'spec_vs_interface': 0.25,
            'interface_vs_tests': 0.20,
            'tests_vs_code': 0.20
        }

        return (
            weights['spec_vs_code'] * self.spec_vs_code.score +
            weights['spec_vs_interface'] * self.spec_vs_interface.score +
            weights['interface_vs_tests'] * self.interface_vs_tests.score +
            weights['tests_vs_code'] * self.tests_vs_code.score
        )

    def is_drifted(self, threshold: float = 40.0) -> bool:
        """Check if overall drift exceeds threshold."""
        return self.overall_drift > threshold


class LLMDriftDetector:
    """
    Uses a small local LLM to detect semantic drift.

    Designed for fast, local execution with 4B parameter models like:
    - qwen2.5-coder:4b
    - codellama:7b
    - deepseek-coder:6.7b
    """

    def __init__(
        self,
        model: str = "qwen2.5-coder:4b",
        ollama_host: str = "http://localhost:11434"
    ):
        """
        Initialize LLM drift detector.

        Args:
            model: Ollama model name (default: qwen2.5-coder:4b)
            ollama_host: Ollama API host
        """
        self.model = model
        self.ollama_host = ollama_host

    def _call_llm(self, prompt: str) -> str:
        """
        Call local LLM via Ollama.

        Args:
            prompt: Prompt to send

        Returns:
            LLM response text
        """
        try:
            # Use ollama CLI for simplicity
            result = subprocess.run(
                ['ollama', 'run', self.model],
                input=prompt,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                logger.error(f"Ollama error: {result.stderr}")
                return ""

            return result.stdout.strip()

        except subprocess.TimeoutExpired:
            logger.error("LLM call timed out")
            return ""
        except FileNotFoundError:
            logger.error("Ollama not found - install from https://ollama.ai/")
            return ""
        except Exception as e:
            logger.error(f"Error calling LLM: {e}")
            return ""

    def detect_drift(
        self,
        artifact1_name: str,
        artifact1_content: str,
        artifact2_name: str,
        artifact2_content: str
    ) -> DriftScore:
        """
        Detect drift between two artifacts using LLM.

        Args:
            artifact1_name: Name of first artifact (e.g., "specification")
            artifact1_content: Content of first artifact
            artifact2_name: Name of second artifact (e.g., "implementation")
            artifact2_content: Content of second artifact

        Returns:
            DriftScore with 0-100 score and reasoning
        """
        prompt = f"""You are a code analysis expert. Compare these two artifacts and detect semantic drift.

ARTIFACT 1 ({artifact1_name}):
```
{artifact1_content[:2000]}  # Truncate for context window
```

ARTIFACT 2 ({artifact2_name}):
```
{artifact2_content[:2000]}
```

TASK:
Analyze the semantic alignment between these artifacts.

OUTPUT FORMAT (JSON):
{{
  "drift_score": <0-100, where 0=perfectly aligned, 100=nothing alike>,
  "confidence": <0.0-1.0, how confident you are>,
  "reasoning": "<brief explanation>",
  "key_differences": [
    "<difference 1>",
    "<difference 2>",
    ...
  ]
}}

SCORING GUIDE:
- 0-20: Minor differences (naming, formatting, comments)
- 21-40: Moderate differences (some logic changes, added features)
- 41-60: Significant differences (major refactoring, changed behavior)
- 61-80: Very different (different algorithms, different purpose)
- 81-100: Completely unrelated (nothing in common)

IMPORTANT: Output ONLY the JSON, no extra text.
"""

        response = self._call_llm(prompt)

        if not response:
            # Fallback if LLM fails
            return DriftScore(
                score=50.0,
                confidence=0.1,
                reasoning="LLM unavailable - using fallback",
                key_differences=["Could not analyze"]
            )

        # Parse JSON response
        try:
            # Extract JSON from response (handle markdown code blocks)
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                data = json.loads(json_match.group())
            else:
                data = json.loads(response)

            return DriftScore(
                score=float(data.get('drift_score', 50.0)),
                confidence=float(data.get('confidence', 0.5)),
                reasoning=data.get('reasoning', ''),
                key_differences=data.get('key_differences', [])
            )

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(f"Failed to parse LLM response: {e}")
            logger.debug(f"Response was: {response}")

            # Fallback scoring
            return DriftScore(
                score=50.0,
                confidence=0.3,
                reasoning=f"Parse error: {str(e)}",
                key_differences=["Could not parse LLM response"]
            )

    def detect_spec_vs_code_drift(
        self,
        specification: str,
        implementation: str
    ) -> DriftScore:
        """Detect drift between specification and implementation."""
        return self.detect_drift(
            "Specification",
            specification,
            "Implementation",
            implementation
        )

    def detect_spec_vs_interface_drift(
        self,
        specification: str,
        interface: str
    ) -> DriftScore:
        """Detect drift between specification and interface definition."""
        return self.detect_drift(
            "Specification",
            specification,
            "Interface",
            interface
        )

    def detect_interface_vs_tests_drift(
        self,
        interface: str,
        tests: str
    ) -> DriftScore:
        """Detect drift between interface and test cases."""
        return self.detect_drift(
            "Interface Definition",
            interface,
            "Test Suite",
            tests
        )

    def detect_tests_vs_code_drift(
        self,
        tests: str,
        implementation: str
    ) -> DriftScore:
        """Detect drift between tests and implementation."""
        return self.detect_drift(
            "Test Suite",
            tests,
            "Implementation",
            implementation
        )

    def comprehensive_drift_analysis(
        self,
        specification: str,
        interface: str,
        tests: str,
        implementation: str
    ) -> ComprehensiveDrift:
        """
        Perform comprehensive drift analysis across all artifact pairs.

        Args:
            specification: Tool specification (docstring, requirements)
            interface: Function signature, type hints, parameters
            tests: Unit tests for the tool
            implementation: Actual implementation code

        Returns:
            ComprehensiveDrift with all drift scores
        """
        logger.info("Running comprehensive drift analysis...")

        # Detect all drift dimensions
        spec_vs_code = self.detect_spec_vs_code_drift(specification, implementation)
        logger.info(f"  Spec vs Code: {spec_vs_code.score:.1f}/100")

        spec_vs_interface = self.detect_spec_vs_interface_drift(specification, interface)
        logger.info(f"  Spec vs Interface: {spec_vs_interface.score:.1f}/100")

        interface_vs_tests = self.detect_interface_vs_tests_drift(interface, tests)
        logger.info(f"  Interface vs Tests: {interface_vs_tests.score:.1f}/100")

        tests_vs_code = self.detect_tests_vs_code_drift(tests, implementation)
        logger.info(f"  Tests vs Code: {tests_vs_code.score:.1f}/100")

        drift = ComprehensiveDrift(
            spec_vs_code=spec_vs_code,
            spec_vs_interface=spec_vs_interface,
            interface_vs_tests=interface_vs_tests,
            tests_vs_code=tests_vs_code
        )

        logger.info(f"  Overall Drift: {drift.overall_drift:.1f}/100")

        return drift

    def should_split_tool(
        self,
        prime_tool_name: str,
        prime_tool: Dict[str, str],
        variant_tool: Dict[str, str],
        existing_tool_names: list[str]
    ) -> ToolSplitRecommendation:
        """
        Ask LLM: Is variant different enough from prime to be a new tool?

        Args:
            prime_tool_name: Name of the prime tool
            prime_tool: Dict with keys: spec, interface, tests, implementation
            variant_tool: Dict with keys: spec, interface, tests, implementation
            existing_tool_names: List of existing tool names (for uniqueness check)

        Returns:
            ToolSplitRecommendation with split decision and suggested name
        """
        prompt = f"""You are a tool architecture expert. Compare these two tool implementations.

PRIME TOOL: {prime_tool_name}

PRIME - Specification:
```
{prime_tool.get('spec', '')[:1000]}
```

PRIME - Interface:
```
{prime_tool.get('interface', '')[:500]}
```

PRIME - Tests:
```
{prime_tool.get('tests', '')[:1000]}
```

VARIANT - Specification:
```
{variant_tool.get('spec', '')[:1000]}
```

VARIANT - Interface:
```
{variant_tool.get('interface', '')[:500]}
```

VARIANT - Tests:
```
{variant_tool.get('tests', '')[:1000]}
```

EXISTING TOOL NAMES (must avoid):
{', '.join(existing_tool_names[:20])}

TASK:
1. Compare the prime tool and variant
2. Determine if variant is different enough to be a NEW TOOL (not just a version)
3. If yes, suggest a UNIQUE name that describes the variant's purpose

SPLIT CRITERIA (should split if ANY apply):
- Different purpose/use case
- Fundamentally different algorithm
- Incompatible interfaces (different parameters/returns)
- Serves different user needs
- Tests validate completely different behaviors

OUTPUT FORMAT (JSON):
{{
  "should_split": <true/false>,
  "confidence": <0.0-1.0>,
  "drift_score": <0-100, how different they are>,
  "suggested_name": "<unique tool name, or empty string if no split>",
  "reasoning": "<why split or not split>",
  "key_differences": [
    "<difference 1>",
    "<difference 2>"
  ]
}}

NAMING RULES:
- Base name on what the variant DOES differently
- Must NOT be in existing tools list
- Use snake_case
- Be descriptive but concise
- Examples: "parse_cron_advanced", "format_date_iso", "validate_email_strict"

IMPORTANT: Output ONLY the JSON, no extra text.
"""

        response = self._call_llm(prompt)

        if not response:
            # Fallback
            return ToolSplitRecommendation(
                should_split=False,
                confidence=0.1,
                suggested_name="",
                reasoning="LLM unavailable",
                drift_score=50.0
            )

        # Parse response
        try:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                data = json.loads(json_match.group())
            else:
                data = json.loads(response)

            suggested_name = data.get('suggested_name', '').strip()

            # Ensure name is unique
            if suggested_name and suggested_name in existing_tool_names:
                # Append _v2, _v3, etc. until unique
                counter = 2
                while f"{suggested_name}_v{counter}" in existing_tool_names:
                    counter += 1
                suggested_name = f"{suggested_name}_v{counter}"

            return ToolSplitRecommendation(
                should_split=bool(data.get('should_split', False)),
                confidence=float(data.get('confidence', 0.5)),
                suggested_name=suggested_name,
                reasoning=data.get('reasoning', ''),
                drift_score=float(data.get('drift_score', 50.0))
            )

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(f"Failed to parse split recommendation: {e}")
            return ToolSplitRecommendation(
                should_split=False,
                confidence=0.2,
                suggested_name="",
                reasoning=f"Parse error: {str(e)}",
                drift_score=50.0
            )


def analyze_tool_drift(
    tool_name: str,
    tool_version: str,
    specification: str,
    interface: str,
    tests: str,
    implementation: str,
    model: str = "qwen2.5-coder:4b"
) -> ComprehensiveDrift:
    """
    Convenience function to analyze drift for a single tool.

    Args:
        tool_name: Tool name
        tool_version: Tool version
        specification: Tool specification
        interface: Tool interface definition
        tests: Tool test suite
        implementation: Tool implementation
        model: LLM model to use

    Returns:
        ComprehensiveDrift analysis
    """
    detector = LLMDriftDetector(model=model)

    logger.info(f"Analyzing drift for {tool_name} v{tool_version}...")

    drift = detector.comprehensive_drift_analysis(
        specification=specification,
        interface=interface,
        tests=tests,
        implementation=implementation
    )

    if drift.is_drifted:
        logger.warning(
            f"⚠️  {tool_name} v{tool_version} has SIGNIFICANT DRIFT: "
            f"{drift.overall_drift:.1f}/100"
        )
    else:
        logger.info(
            f"✓ {tool_name} v{tool_version} is well-aligned: "
            f"{drift.overall_drift:.1f}/100"
        )

    return drift


def should_trim_variant(
    drift: ComprehensiveDrift,
    max_acceptable_drift: float = 60.0
) -> Tuple[bool, str]:
    """
    Determine if a variant should be trimmed based on drift.

    Args:
        drift: Comprehensive drift analysis
        max_acceptable_drift: Maximum acceptable drift (default: 60/100)

    Returns:
        (should_trim, reason) tuple
    """
    if drift.overall_drift > max_acceptable_drift:
        return True, f"Excessive drift: {drift.overall_drift:.1f}/100 (max: {max_acceptable_drift})"

    # Check critical dimensions individually
    if drift.spec_vs_code.score > 70:
        return True, f"Spec-Code drift too high: {drift.spec_vs_code.score:.1f}/100"

    if drift.tests_vs_code.score > 75:
        return True, f"Tests-Code drift too high: {drift.tests_vs_code.score:.1f}/100"

    return False, "Drift within acceptable range"


# Example usage
if __name__ == "__main__":
    # Example specification
    spec = """
    Parse a cron expression and return a dictionary of fields.

    Parameters:
        expression (str): Cron expression like "0 0 * * *"

    Returns:
        dict: Dictionary with keys: minute, hour, day, month, weekday
    """

    # Example interface
    interface = """
    def parse_cron(expression: str) -> dict:
        pass
    """

    # Example tests
    tests = """
    def test_parse_cron_simple():
        result = parse_cron("0 0 * * *")
        assert result == {"minute": "0", "hour": "0", "day": "*", "month": "*", "weekday": "*"}

    def test_parse_cron_complex():
        result = parse_cron("*/5 9-17 * * 1-5")
        assert result["minute"] == "*/5"
        assert result["hour"] == "9-17"
    """

    # Example implementation
    implementation = """
    def parse_cron(expression: str) -> dict:
        parts = expression.split()
        return {
            "minute": parts[0],
            "hour": parts[1],
            "day": parts[2],
            "month": parts[3],
            "weekday": parts[4]
        }
    """

    # Analyze drift
    drift = analyze_tool_drift(
        tool_name="parse_cron",
        tool_version="1.0.0",
        specification=spec,
        interface=interface,
        tests=tests,
        implementation=implementation
    )

    print(f"\nOverall Drift: {drift.overall_drift:.1f}/100")
    print(f"Should Trim: {should_trim_variant(drift)}")
