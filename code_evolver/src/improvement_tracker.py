"""
Improvement Tracker - Leave Hints for Future Optimization

When the system makes a "good enough" fix in interactive mode,
it leaves hints for future optimization:

INTERACTIVE MODE (fast):
- Uses mid-range LLM or simple approach
- Marks code with TODOs
- Creates improvement hints in tool MD files
- Balances "result now" vs "upgradable later"

OPTIMIZE MODE (later):
- Reads improvement hints
- Applies better solutions (NMT, dictionaries, specialized algorithms)
- Upgrades code while maintaining compatibility

Example:
  Interactive: "Use regex for email validation"
  → Works, but leaves hint: "TODO: Replace with email-validator library"

  Optimize: Reads hint, upgrades to proper validation library
"""

import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class ImprovementHint:
    """A hint for future optimization."""

    def __init__(
        self,
        hint_id: str,
        node_id: str,
        description: str,
        current_approach: str,
        suggested_improvement: str,
        priority: str = "medium",
        estimated_effort: str = "medium"
    ):
        self.hint_id = hint_id
        self.node_id = node_id
        self.description = description
        self.current_approach = current_approach
        self.suggested_improvement = suggested_improvement
        self.priority = priority  # low, medium, high, critical
        self.estimated_effort = estimated_effort  # low, medium, high
        self.created_at = datetime.now().isoformat()


class ImprovementTracker:
    """
    Tracks improvements that can be made later.

    Interactive Mode:
    1. Code generated quickly (mid-range LLM)
    2. Works, but not optimal
    3. Leaves hints: "This could be better"
    4. User gets result NOW

    Optimize Mode:
    1. Reads all improvement hints
    2. Applies better solutions
    3. Tests compatibility
    4. Upgrades code
    """

    def __init__(self, rag_memory, nodes_path: Path):
        """
        Initialize improvement tracker.

        Args:
            rag_memory: RAGMemory for storing hints
            nodes_path: Path to nodes directory
        """
        self.rag = rag_memory
        self.nodes_path = Path(nodes_path)

    def mark_for_improvement(
        self,
        node_id: str,
        code: str,
        description: str,
        current_approach: str,
        suggested_improvement: str,
        priority: str = "medium"
    ) -> str:
        """
        Mark code for future improvement.

        Args:
            node_id: Node ID
            code: Generated code
            description: What needs improvement
            current_approach: Current implementation
            suggested_improvement: Better approach for later
            priority: low/medium/high/critical

        Returns:
            Updated code with TODO comments
        """

        # Create improvement hint
        hint = ImprovementHint(
            hint_id=f"{node_id}_{datetime.now().timestamp()}",
            node_id=node_id,
            description=description,
            current_approach=current_approach,
            suggested_improvement=suggested_improvement,
            priority=priority
        )

        # Add TODO comment to code
        todo_comment = self._create_todo_comment(hint)
        code_with_todo = self._inject_todo(code, todo_comment, current_approach)

        # Store hint in RAG for later
        self._store_hint(hint)

        # Create improvement hint file in node directory
        self._create_hint_file(hint)

        logger.info(f"Marked {node_id} for improvement: {description}")

        return code_with_todo

    def get_improvement_opportunities(
        self,
        priority_min: str = "low",
        limit: int = 10
    ) -> List[ImprovementHint]:
        """
        Get list of improvement opportunities for optimize mode.

        Args:
            priority_min: Minimum priority (low/medium/high/critical)
            limit: Max number of hints to return

        Returns:
            List of improvement hints, sorted by priority
        """

        try:
            from src.rag_memory import ArtifactType

            # Search RAG for improvement hints
            results = self.rag.find_by_tags(
                tags=["improvement_hint"],
                limit=limit * 2
            )

            hints = []
            for artifact in results:
                data = json.loads(artifact.content)

                # Filter by priority
                priority = data.get("priority", "medium")
                if not self._meets_priority(priority, priority_min):
                    continue

                hint = ImprovementHint(
                    hint_id=data["hint_id"],
                    node_id=data["node_id"],
                    description=data["description"],
                    current_approach=data["current_approach"],
                    suggested_improvement=data["suggested_improvement"],
                    priority=priority,
                    estimated_effort=data.get("estimated_effort", "medium")
                )

                hints.append(hint)

            # Sort by priority (critical > high > medium > low)
            priority_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
            hints.sort(key=lambda h: priority_order.get(h.priority, 0), reverse=True)

            return hints[:limit]

        except Exception as e:
            logger.warning(f"Could not get improvement opportunities: {e}")
            return []

    def apply_improvement(
        self,
        hint: ImprovementHint,
        improved_code: str
    ) -> bool:
        """
        Apply an improvement and mark hint as resolved.

        Args:
            hint: Improvement hint to resolve
            improved_code: New improved code

        Returns:
            True if successful
        """

        try:
            # Save improved code
            node_path = self.nodes_path / hint.node_id
            code_file = node_path / "main.py"

            if code_file.exists():
                with open(code_file, 'w', encoding='utf-8') as f:
                    f.write(improved_code)

            # Mark hint as resolved in RAG
            self._mark_hint_resolved(hint.hint_id)

            # Update hint file
            hint_file = node_path / "IMPROVEMENTS.md"
            if hint_file.exists():
                self._update_hint_file(hint_file, hint.hint_id, "RESOLVED")

            logger.info(f"Applied improvement: {hint.description}")
            return True

        except Exception as e:
            logger.error(f"Could not apply improvement: {e}")
            return False

    def _create_todo_comment(self, hint: ImprovementHint) -> str:
        """Create a TODO comment for the hint."""

        return f"""# TODO [{hint.priority.upper()}]: {hint.description}
# Current: {hint.current_approach}
# Suggested: {hint.suggested_improvement}
# Hint ID: {hint.hint_id}"""

    def _inject_todo(self, code: str, todo_comment: str, near_text: str) -> str:
        """Inject TODO comment near the relevant code."""

        lines = code.split('\n')

        # Find line containing the current approach
        insert_line = 0
        for i, line in enumerate(lines):
            if near_text in line:
                insert_line = i
                break

        # Insert TODO comment before that line
        lines.insert(insert_line, todo_comment)

        return '\n'.join(lines)

    def _store_hint(self, hint: ImprovementHint):
        """Store hint in RAG for later retrieval."""

        try:
            from src.rag_memory import ArtifactType

            self.rag.store_artifact(
                artifact_id=f"improvement_hint_{hint.hint_id}",
                artifact_type=ArtifactType.PATTERN,
                name=f"Improvement: {hint.description}",
                description=hint.suggested_improvement,
                content=json.dumps({
                    "hint_id": hint.hint_id,
                    "node_id": hint.node_id,
                    "description": hint.description,
                    "current_approach": hint.current_approach,
                    "suggested_improvement": hint.suggested_improvement,
                    "priority": hint.priority,
                    "estimated_effort": hint.estimated_effort,
                    "created_at": hint.created_at,
                    "status": "pending"
                }),
                tags=["improvement_hint", hint.priority, hint.node_id],
                auto_embed=True  # Enable semantic search
            )

        except Exception as e:
            logger.warning(f"Could not store hint in RAG: {e}")

    def _create_hint_file(self, hint: ImprovementHint):
        """Create IMPROVEMENTS.md file in node directory."""

        node_path = self.nodes_path / hint.node_id
        if not node_path.exists():
            return

        hint_file = node_path / "IMPROVEMENTS.md"

        # Read existing hints if file exists
        existing_content = ""
        if hint_file.exists():
            with open(hint_file, 'r', encoding='utf-8') as f:
                existing_content = f.read()

        # Append new hint
        new_hint = f"""
## {hint.description}

**Priority:** {hint.priority.upper()}
**Hint ID:** {hint.hint_id}
**Created:** {hint.created_at}
**Status:** PENDING

### Current Approach
```python
{hint.current_approach}
```

### Suggested Improvement
{hint.suggested_improvement}

### Estimated Effort
{hint.estimated_effort}

---
"""

        with open(hint_file, 'w', encoding='utf-8') as f:
            if existing_content:
                f.write(existing_content)
            f.write(new_hint)

        logger.debug(f"Created hint file: {hint_file}")

    def _meets_priority(self, priority: str, min_priority: str) -> bool:
        """Check if priority meets minimum threshold."""

        priority_levels = {"low": 1, "medium": 2, "high": 3, "critical": 4}

        return priority_levels.get(priority, 0) >= priority_levels.get(min_priority, 0)

    def _mark_hint_resolved(self, hint_id: str):
        """Mark hint as resolved in RAG."""

        try:
            # Update artifact with resolved status
            artifact = self.rag.get_artifact(f"improvement_hint_{hint_id}")

            if artifact:
                data = json.loads(artifact.content)
                data["status"] = "resolved"
                data["resolved_at"] = datetime.now().isoformat()

                # Update artifact
                self.rag.update_artifact(
                    artifact_id=artifact.artifact_id,
                    content=json.dumps(data)
                )

        except Exception as e:
            logger.warning(f"Could not mark hint as resolved: {e}")

    def _update_hint_file(self, hint_file: Path, hint_id: str, status: str):
        """Update hint status in IMPROVEMENTS.md file."""

        try:
            with open(hint_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Replace status for this hint
            content = content.replace(
                f"**Hint ID:** {hint_id}\n**Created:**",
                f"**Hint ID:** {hint_id}\n**Status:** {status}\n**Created:**"
            )

            with open(hint_file, 'w', encoding='utf-8') as f:
                f.write(content)

        except Exception as e:
            logger.warning(f"Could not update hint file: {e}")

    def get_node_improvements(self, node_id: str) -> List[ImprovementHint]:
        """Get all improvement hints for a specific node."""

        try:
            from src.rag_memory import ArtifactType

            results = self.rag.find_by_tags(
                tags=["improvement_hint", node_id],
                limit=100
            )

            hints = []
            for artifact in results:
                data = json.loads(artifact.content)

                # Skip resolved hints
                if data.get("status") == "resolved":
                    continue

                hint = ImprovementHint(
                    hint_id=data["hint_id"],
                    node_id=data["node_id"],
                    description=data["description"],
                    current_approach=data["current_approach"],
                    suggested_improvement=data["suggested_improvement"],
                    priority=data.get("priority", "medium")
                )

                hints.append(hint)

            return hints

        except Exception as e:
            logger.warning(f"Could not get node improvements: {e}")
            return []


# Example usage in interactive mode
def example_interactive_mode():
    """
    Example: Generate code quickly, mark for improvement.
    """

    # Generate code with simple approach (fast)
    code = """
import re

def validate_email(email: str) -> bool:
    # Simple regex validation
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))
"""

    # Mark for improvement
    tracker = ImprovementTracker(rag_memory, nodes_path)

    improved_code = tracker.mark_for_improvement(
        node_id="email_validator",
        code=code,
        description="Email validation could use specialized library",
        current_approach="re.match(pattern, email)",
        suggested_improvement="Use email-validator library for proper RFC 5322 validation",
        priority="medium"
    )

    # Returns code with TODO comment:
    """
    import re

    # TODO [MEDIUM]: Email validation could use specialized library
    # Current: re.match(pattern, email)
    # Suggested: Use email-validator library for proper RFC 5322 validation
    # Hint ID: email_validator_1234567890
    def validate_email(email: str) -> bool:
        # Simple regex validation
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    """


# Example usage in optimize mode
def example_optimize_mode():
    """
    Example: Read hints, apply improvements.
    """

    tracker = ImprovementTracker(rag_memory, nodes_path)

    # Get improvement opportunities
    hints = tracker.get_improvement_opportunities(priority_min="medium")

    for hint in hints:
        print(f"Improvement: {hint.description}")
        print(f"Suggested: {hint.suggested_improvement}")

        # Generate improved code (using better approach)
        improved_code = """
from email_validator import validate_email, EmailNotValidError

def validate_email(email: str) -> bool:
    try:
        # Use proper RFC 5322 validation
        validate_email(email)
        return True
    except EmailNotValidError:
        return False
"""

        # Apply improvement
        tracker.apply_improvement(hint, improved_code)
