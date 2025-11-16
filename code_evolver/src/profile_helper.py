"""
Performance profiling helper for chat-based code analysis.
Provides easy-to-use functions for profiling code snippets from user requests.
"""
import os
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import logging

from .profiling import Profiler, ProfileContext, get_global_registry

logger = logging.getLogger(__name__)


class CodeProfiler:
    """
    Helper class for profiling code snippets from chat interactions.
    """

    def __init__(self, output_dir: Optional[Path] = None):
        """
        Initialize code profiler.

        Args:
            output_dir: Directory to save profiles (uses default if None)
        """
        self.output_dir = output_dir or Path("./profiles")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def profile_code_snippet(
        self,
        code: str,
        name: str = "user_code",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Profile a code snippet and return analysis.

        Args:
            code: Python code to profile
            name: Name for this profiling session
            metadata: Additional metadata

        Returns:
            Dictionary with profile results and analysis
        """
        # Enable profiling
        os.environ["CODE_EVOLVER_PROFILE"] = "1"

        # Create temporary file for code
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            temp_file = Path(f.name)
            f.write(code)

        try:
            # Profile the execution
            profiler = Profiler(
                name=name,
                metadata=metadata or {"source": "chat", "type": "snippet"}
            )
            profiler.start()

            # Execute the code
            result = subprocess.run(
                ["python", str(temp_file)],
                capture_output=True,
                text=True,
                timeout=60  # 1 minute timeout
            )

            profile_data = profiler.stop()

            # Analyze the profile
            analysis = self._analyze_profile(profile_data, result)

            return analysis

        except subprocess.TimeoutExpired:
            logger.error(f"Code execution timed out after 60 seconds")
            return {
                "error": "Execution timed out",
                "duration_ms": 60000,
                "recommendation": "Code took too long to execute. Consider optimizing or breaking into smaller chunks."
            }

        except Exception as e:
            logger.error(f"Error profiling code: {e}")
            return {
                "error": str(e),
                "recommendation": "Check code for syntax errors or runtime issues"
            }

        finally:
            # Cleanup
            if temp_file.exists():
                temp_file.unlink()

    def profile_function(
        self,
        func_code: str,
        test_input: Any,
        name: str = "user_function"
    ) -> Dict[str, Any]:
        """
        Profile a function with test input.

        Args:
            func_code: Function definition code
            test_input: Input to pass to the function
            name: Name for profiling session

        Returns:
            Profile analysis
        """
        # Wrap function with profiling
        wrapper_code = f"""
{func_code}

# Profile the function
from src.profiling import Profiler

profiler = Profiler(name="{name}")
profiler.start()

# Call the function
result = main({repr(test_input)})

profile_data = profiler.stop()
print(f"Result: {{result}}")
"""

        return self.profile_code_snippet(wrapper_code, name=name)

    def _analyze_profile(
        self,
        profile_data: Any,
        execution_result: subprocess.CompletedProcess
    ) -> Dict[str, Any]:
        """
        Analyze profile data and extract insights.

        Args:
            profile_data: ProfileData object
            execution_result: Result from subprocess execution

        Returns:
            Analysis dictionary
        """
        if profile_data is None:
            return {
                "error": "Profiling disabled or failed",
                "stdout": execution_result.stdout,
                "stderr": execution_result.stderr
            }

        analysis = {
            "duration_ms": profile_data.duration_ms,
            "timestamp": profile_data.timestamp,
            "metadata": profile_data.metadata,
            "success": execution_result.returncode == 0,
            "stdout": execution_result.stdout,
            "stderr": execution_result.stderr,
        }

        # Extract bottlenecks from profile text
        if profile_data.profile_text:
            analysis["profile_text"] = profile_data.profile_text
            analysis["bottlenecks"] = self._extract_bottlenecks(profile_data.profile_text)

        # Add recommendations
        analysis["recommendations"] = self._generate_recommendations(
            profile_data.duration_ms,
            profile_data.profile_text,
            execution_result
        )

        return analysis

    def _extract_bottlenecks(self, profile_text: str) -> list:
        """
        Extract top bottlenecks from profile text.

        Args:
            profile_text: Text output from PyInstrument

        Returns:
            List of bottleneck descriptions
        """
        bottlenecks = []

        # Parse profile text for function lines
        # PyInstrument format shows functions with time
        lines = profile_text.split('\n')

        for line in lines:
            # Look for lines with function names and times
            if '  ' in line and not line.strip().startswith('_'):
                # Extract function name and time if present
                parts = line.strip().split()
                if len(parts) >= 2:
                    try:
                        # Check if first part is a number (time)
                        time_val = float(parts[0])
                        func_name = ' '.join(parts[1:])
                        bottlenecks.append({
                            "time": time_val,
                            "function": func_name
                        })
                    except ValueError:
                        continue

        # Sort by time and return top 5
        bottlenecks.sort(key=lambda x: x["time"], reverse=True)
        return bottlenecks[:5]

    def _generate_recommendations(
        self,
        duration_ms: float,
        profile_text: Optional[str],
        execution_result: subprocess.CompletedProcess
    ) -> list:
        """
        Generate optimization recommendations.

        Args:
            duration_ms: Execution duration
            profile_text: Profile text output
            execution_result: Execution result

        Returns:
            List of recommendations
        """
        recommendations = []

        # Duration-based recommendations
        if duration_ms > 10000:  # > 10 seconds
            recommendations.append({
                "priority": "high",
                "issue": "Long execution time",
                "suggestion": "Consider profiling individual sections to identify the slowest parts"
            })

        elif duration_ms > 1000:  # > 1 second
            recommendations.append({
                "priority": "medium",
                "issue": "Execution time could be improved",
                "suggestion": "Look for optimization opportunities in hot paths"
            })

        # Error-based recommendations
        if execution_result.returncode != 0:
            recommendations.append({
                "priority": "high",
                "issue": "Code execution failed",
                "suggestion": f"Fix errors: {execution_result.stderr[:200]}"
            })

        # Profile-based recommendations
        if profile_text:
            if "requests" in profile_text.lower() or "http" in profile_text.lower():
                recommendations.append({
                    "priority": "medium",
                    "issue": "Network I/O detected",
                    "suggestion": "Consider caching, connection pooling, or async I/O"
                })

            if "json.loads" in profile_text or "json.dumps" in profile_text:
                recommendations.append({
                    "priority": "low",
                    "issue": "JSON serialization detected",
                    "suggestion": "For large data, consider faster serialization (orjson, msgpack)"
                })

        return recommendations

    def compare_versions(
        self,
        code_v1: str,
        code_v2: str,
        name: str = "comparison"
    ) -> Dict[str, Any]:
        """
        Compare performance of two code versions.

        Args:
            code_v1: First version of code
            code_v2: Second version of code
            name: Base name for profiling sessions

        Returns:
            Comparison results
        """
        # Profile both versions
        result_v1 = self.profile_code_snippet(
            code_v1,
            name=f"{name}_v1",
            metadata={"version": "1.0"}
        )

        result_v2 = self.profile_code_snippet(
            code_v2,
            name=f"{name}_v2",
            metadata={"version": "2.0"}
        )

        # Calculate improvement
        duration_v1 = result_v1.get("duration_ms", 0)
        duration_v2 = result_v2.get("duration_ms", 0)

        if duration_v1 > 0:
            improvement_pct = ((duration_v1 - duration_v2) / duration_v1) * 100
        else:
            improvement_pct = 0

        return {
            "version_1": result_v1,
            "version_2": result_v2,
            "improvement_pct": improvement_pct,
            "recommendation": "upgrade" if improvement_pct > 5 else "keep_current",
            "summary": f"Version 2 is {abs(improvement_pct):.1f}% {'faster' if improvement_pct > 0 else 'slower'}"
        }


def profile_from_chat(code: str, name: str = "chat_code") -> str:
    """
    Convenience function to profile code from chat and return formatted results.

    Args:
        code: Python code to profile
        name: Name for the profiling session

    Returns:
        Formatted analysis string
    """
    profiler = CodeProfiler()
    result = profiler.profile_code_snippet(code, name=name)

    # Format output
    output = f"""
## Performance Profile: {name}

**Duration**: {result.get('duration_ms', 0):.2f}ms
**Status**: {'✓ Success' if result.get('success') else '✗ Failed'}

"""

    # Add bottlenecks if available
    if "bottlenecks" in result and result["bottlenecks"]:
        output += "### Top Bottlenecks\n"
        for i, bottleneck in enumerate(result["bottlenecks"], 1):
            output += f"{i}. {bottleneck['function']} - {bottleneck['time']:.3f}s\n"
        output += "\n"

    # Add recommendations
    if "recommendations" in result and result["recommendations"]:
        output += "### Recommendations\n"
        for rec in result["recommendations"]:
            priority = rec.get("priority", "medium").upper()
            output += f"- [{priority}] {rec['issue']}\n"
            output += f"  **Fix**: {rec['suggestion']}\n"
        output += "\n"

    # Add stdout if present
    if result.get("stdout"):
        output += f"### Output\n```\n{result['stdout']}\n```\n"

    # Add errors if present
    if result.get("stderr"):
        output += f"### Errors\n```\n{result['stderr']}\n```\n"

    return output
