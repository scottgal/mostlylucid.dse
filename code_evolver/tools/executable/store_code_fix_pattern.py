#!/usr/bin/env python3
"""
Store Code Fix Pattern

Stores code breaks and their fixes as reusable patterns.
Learns from errors so similar issues can be fixed earlier next time.
"""

import json
import sys
import os
from typing import Dict, Any
from datetime import datetime
import hashlib


def store_code_fix_pattern(
    error_message: str,
    broken_code: str,
    fixed_code: str,
    fix_description: str,
    error_type: str = "unknown",
    language: str = "python",
    context: Dict[str, Any] = None,
    debug_info: Dict[str, Any] = None,
    scope: str = "global",
    tool_id: str = ""
) -> Dict[str, Any]:
    """
    Store a code fix pattern for future reuse

    Each fix is stored as a SEPARATE node, even for the same error.
    This allows multiple solutions to be ranked by usage/effectiveness.

    Args:
        error_message: The error message that occurred
        broken_code: The code that caused the error
        fixed_code: The corrected code
        fix_description: Description of what was wrong and how it was fixed
        error_type: Category of error (syntax, runtime, logic, etc.)
        language: Programming language
        context: Additional context (framework, tool_id, etc.)
        debug_info: Full debug information (stack trace, variables, etc.)
        scope: Data store scope - "tool", "tool_subttools", "hierarchy", or "global"
        tool_id: Current tool identifier (required for scoped storage)

    Returns:
        Result with pattern ID and storage confirmation
    """
    sys.path.insert(0, '.')

    try:
        from src.config_manager import ConfigManager
        from src.ollama_client import OllamaClient
        from src.rag_memory import RAGMemory, ArtifactType

        # Initialize
        config = ConfigManager()
        client = OllamaClient(config_manager=config)
        rag = RAGMemory(ollama_client=client)

        # Generate UNIQUE pattern ID (includes timestamp to allow multiple fixes for same error)
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        fix_signature = f"{error_type}:{error_message[:50]}:{timestamp}"
        pattern_id = f"fix_pattern_{hashlib.md5(fix_signature.encode()).hexdigest()[:12]}"

        # Build comprehensive pattern content with ALL debug info
        pattern_content = f"""# Code Fix Pattern

## Error Type: {error_type}
## Language: {language}

### Error Message
```
{error_message}
```

### Broken Code
```{language}
{broken_code}
```

### Fixed Code
```{language}
{fixed_code}
```

### Fix Description
{fix_description}

### Debug Information
```json
{json.dumps(debug_info or {}, indent=2)}
```

### How to Apply This Fix
1. Identify similar error pattern
2. Look for the same code structure
3. Apply the transformation shown above
4. Test thoroughly
5. If successful, increment usage count for this pattern

### Context
```json
{json.dumps(context or {}, indent=2)}
```

---
**Stored:** {datetime.utcnow().isoformat()}Z
**Pattern ID:** {pattern_id}
**Usage Count:** 0 (will increment when successfully applied)
**Quality Score:** 0.95 (proven fix)
"""

        # Extract key phrases from error for tags
        error_keywords = []
        common_errors = {
            'SyntaxError': 'syntax-error',
            'IndentationError': 'indentation-error',
            'NameError': 'undefined-name',
            'TypeError': 'type-error',
            'AttributeError': 'attribute-error',
            'ImportError': 'import-error',
            'ModuleNotFoundError': 'module-not-found',
            'KeyError': 'key-error',
            'IndexError': 'index-error',
            'ValueError': 'value-error',
            'RuntimeError': 'runtime-error',
            'FileNotFoundError': 'file-not-found',
            'PermissionError': 'permission-error',
            'UnicodeError': 'unicode-error',
            'JSONDecodeError': 'json-error'
        }

        for error_name, tag in common_errors.items():
            if error_name in error_message:
                error_keywords.append(tag)

        # Build tags
        tags = [
            'code-fix-pattern',
            error_type,
            language,
            *error_keywords
        ]

        # Add scope tags for filtering
        if scope != "global" and tool_id:
            if scope == "tool":
                # Pattern only accessible by this specific tool
                tags.append(f"scope:tool:{tool_id}")
            elif scope == "tool_subttools":
                # Pattern accessible by this tool and its sub-tools
                tags.append(f"scope:hierarchy:{tool_id}")
            elif scope == "hierarchy":
                # Pattern accessible by all tools in hierarchy
                tags.append(f"scope:hierarchy:{tool_id}")
        # else: global scope - no scope tag (accessible by all)

        if context:
            if 'tool_id' in context:
                tags.append(f"tool:{context['tool_id']}")
            if 'framework' in context:
                tags.append(f"framework:{context['framework']}")

        # Store in RAG with high quality score (it's a proven fix)
        # Each fix is a separate node to allow ranking by usage
        rag.store_artifact(
            artifact_id=pattern_id,
            artifact_type=ArtifactType.PATTERN,
            name=f"Fix: {error_type} - {error_message[:60]}",
            description=fix_description,
            content=pattern_content,
            tags=tags,
            metadata={
                'error_message': error_message,
                'error_type': error_type,
                'language': language,
                'context': context or {},
                'debug_info': debug_info or {},
                'fix_applied': True,
                'pattern_type': 'code_fix',
                'broken_code': broken_code,
                'fixed_code': fixed_code,
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            },
            auto_embed=True  # Create embedding for semantic search
        )

        # Set quality score to high since this is a proven fix
        rag.update_quality_score(pattern_id, 0.95)

        # Increment usage counter
        rag.increment_usage(pattern_id)

        return {
            'success': True,
            'pattern_id': pattern_id,
            'error_type': error_type,
            'tags': tags,
            'message': f'Stored code fix pattern: {pattern_id}',
            'searchable_by': [
                'Error message similarity',
                'Code structure similarity',
                'Tags and keywords',
                'Error type'
            ]
        }

    except Exception as e:
        import traceback
        return {
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }


def main():
    """Main entry point"""
    try:
        # Read input from stdin
        input_text = sys.stdin.read().strip()

        try:
            input_data = json.loads(input_text)
        except json.JSONDecodeError as e:
            print(json.dumps({
                'success': False,
                'error': f'Invalid JSON input: {str(e)}'
            }))
            sys.exit(1)

        # Extract parameters
        error_message = input_data.get('error_message', '')
        broken_code = input_data.get('broken_code', '')
        fixed_code = input_data.get('fixed_code', '')
        fix_description = input_data.get('fix_description', '')
        error_type = input_data.get('error_type', 'unknown')
        language = input_data.get('language', 'python')
        context = input_data.get('context', {})
        debug_info = input_data.get('debug_info', {})
        scope = input_data.get('scope', 'global')
        tool_id = input_data.get('tool_id', '')

        if not error_message or not broken_code or not fixed_code:
            print(json.dumps({
                'success': False,
                'error': 'Missing required parameters: error_message, broken_code, fixed_code'
            }))
            sys.exit(1)

        # Store pattern
        result = store_code_fix_pattern(
            error_message=error_message,
            broken_code=broken_code,
            fixed_code=fixed_code,
            fix_description=fix_description,
            error_type=error_type,
            language=language,
            context=context,
            debug_info=debug_info,
            scope=scope,
            tool_id=tool_id
        )

        # Output result
        print(json.dumps(result, indent=2))

        if not result['success']:
            sys.exit(1)

    except Exception as e:
        print(json.dumps({
            'success': False,
            'error': f'Fatal error: {str(e)}'
        }), file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
