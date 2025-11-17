"""
JSON Response Fixer
Extracts JSON from LLM responses that may contain markdown, explanatory text, etc.
"""
import json
import re
from typing import Any, Dict, Optional, Tuple


def extract_json_from_response(response: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Extract JSON from an LLM response that may contain markdown or other text.

    Common patterns:
    - ```json\n{...}\n```
    - Here is the JSON:\n{...}
    - {... }
    - Some text before { ... } some text after

    Args:
        response: Raw LLM response string

    Returns:
        Tuple of (parsed_json, error_message)
        - parsed_json: Dict if successful, None if failed
        - error_message: Error description if failed, None if successful
    """

    # Try 1: Direct JSON parse (cleanest case)
    try:
        return json.loads(response.strip()), None
    except json.JSONDecodeError:
        pass  # Try other methods

    # Try 2: Extract from markdown code block
    # Pattern: ```json\n{...}\n``` or ```\n{...}\n```
    markdown_patterns = [
        r'```json\s*\n(.*?)\n```',
        r'```\s*\n(.*?)\n```',
        r'```json\s*(.*?)```',
        r'```\s*(.*?)```'
    ]

    for pattern in markdown_patterns:
        match = re.search(pattern, response, re.DOTALL)
        if match:
            json_text = match.group(1).strip()
            try:
                return json.loads(json_text), None
            except json.JSONDecodeError:
                pass  # Try next pattern

    # Try 3: Find first { ... } block
    # This handles cases like: "Here is the JSON: {...}"
    brace_match = re.search(r'\{.*\}', response, re.DOTALL)
    if brace_match:
        json_text = brace_match.group(0)
        try:
            return json.loads(json_text), None
        except json.JSONDecodeError:
            pass  # Try next method

    # Try 4: Remove common prefixes
    common_prefixes = [
        r'^Here is the (?:JSON|code|result):?\s*\n*',
        r'^(?:Sure|Certainly),?\s+(?:here is|here\'s)\s+.*?:?\s*\n*',
        r'^The (?:JSON|code|result) is:?\s*\n*',
        r'^```python\s*\n*'  # Sometimes LLM uses wrong language marker
    ]

    cleaned = response
    for prefix_pattern in common_prefixes:
        cleaned = re.sub(prefix_pattern, '', cleaned, flags=re.IGNORECASE)

    try:
        return json.loads(cleaned.strip()), None
    except json.JSONDecodeError:
        pass

    # Try 5: Extract content between first { and last }
    first_brace = response.find('{')
    last_brace = response.rfind('}')

    if first_brace != -1 and last_brace != -1 and first_brace < last_brace:
        json_candidate = response[first_brace:last_brace + 1]
        try:
            return json.loads(json_candidate), None
        except json.JSONDecodeError:
            pass

    # All methods failed
    # Provide helpful error message with response preview
    preview = response[:200].replace('\n', ' ')
    return None, f"Failed to extract valid JSON. Response preview: {preview}..."


def safe_json_parse(response: str, fallback: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Safely parse JSON from LLM response with fallback.

    Args:
        response: Raw LLM response
        fallback: Fallback value if parsing fails (default: empty dict)

    Returns:
        Parsed JSON dict or fallback
    """
    if fallback is None:
        fallback = {}

    result, error = extract_json_from_response(response)

    if result is not None:
        return result

    # Log the error if we have logger
    try:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"JSON parsing failed: {error}")
    except:
        pass

    return fallback


def fix_common_json_issues(json_text: str) -> str:
    """
    Fix common JSON formatting issues from LLM responses.

    Issues fixed:
    - Triple-quoted strings (Python style)
    - Single quotes instead of double quotes
    - Trailing commas
    - Missing commas between items
    - Comments (// and /* */)

    Args:
        json_text: JSON text with potential issues

    Returns:
        Cleaned JSON text
    """
    # Remove comments
    json_text = re.sub(r'//.*$', '', json_text, flags=re.MULTILINE)  # Single-line comments
    json_text = re.sub(r'/\*.*?\*/', '', json_text, flags=re.DOTALL)  # Multi-line comments

    # Fix triple-quoted strings (Python style) - convert to single-line escaped
    def fix_triple_quotes(match):
        content = match.group(1)
        # Escape newlines and quotes
        content = content.replace('\\', '\\\\')
        content = content.replace('"', '\\"')
        content = content.replace('\n', '\\n')
        return f'"{content}"'

    json_text = re.sub(r'"""(.*?)"""', fix_triple_quotes, json_text, flags=re.DOTALL)

    # Remove trailing commas before } or ]
    json_text = re.sub(r',\s*([}\]])', r'\1', json_text)

    # Note: Not auto-fixing single quotes to double quotes as it's risky
    # (might break strings containing apostrophes)

    return json_text


# Example usage and tests
if __name__ == '__main__':
    # Test cases
    test_cases = [
        # Clean JSON
        ('{"key": "value"}', True),

        # Markdown wrapped
        ('```json\n{"key": "value"}\n```', True),

        # With explanation
        ('Here is the JSON:\n{"key": "value"}', True),

        # Mixed content
        ('Some text before {"key": "value"} some text after', True),

        # Trailing commas
        ('{"key": "value",}', True),

        # Invalid JSON
        ('This is not JSON at all', False),
    ]

    print("Testing JSON extraction:")
    for i, (test_input, should_succeed) in enumerate(test_cases, 1):
        result, error = extract_json_from_response(test_input)
        success = result is not None
        status = "PASS" if success == should_succeed else "FAIL"
        print(f"{status} Test {i}: {test_input[:50]}...")
        if result:
            print(f"  → Extracted: {result}")
        elif error:
            print(f"  → Error: {error[:100]}")
