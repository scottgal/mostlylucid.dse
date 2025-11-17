"""
Code Contract System - Enforce Rules on Generated Code

This module provides a comprehensive code contract system that allows you to specify
and enforce rules on generated code, such as:
- Required logging calls
- Maximum function length before refactoring
- Forbidden libraries
- Required imports/patterns
- Structural requirements (e.g., call_tool at start/end)

Contracts are specified in YAML format and can be:
1. Validated during code generation
2. Tested after code generation
3. Documented with compliance reports

Inspired by Design by Contract (DbC) but adapted for code generation workflows.
"""

from __future__ import annotations

import ast
import re
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set, Tuple, Union
from pathlib import Path
from enum import Enum
import yaml

logger = logging.getLogger(__name__)


class ContractSeverity(Enum):
    """Severity level for contract violations."""
    ERROR = "error"  # Must be fixed
    WARNING = "warning"  # Should be fixed
    INFO = "info"  # Nice to have


class ContractType(Enum):
    """Types of contracts that can be enforced."""
    STRUCTURAL = "structural"  # Code structure requirements
    BEHAVIORAL = "behavioral"  # Runtime behavior requirements
    LIBRARY = "library"  # Import/dependency requirements
    METRIC = "metric"  # Code metrics (complexity, length, etc.)
    PATTERN = "pattern"  # Required patterns/anti-patterns
    DOCUMENTATION = "documentation"  # Documentation requirements


@dataclass
class ContractRule:
    """A single contract rule."""
    rule_id: str
    name: str
    description: str
    rule_type: ContractType
    severity: ContractSeverity

    # Rule configuration
    pattern: Optional[str] = None  # Regex pattern to match/avoid
    max_value: Optional[float] = None  # For metric rules
    min_value: Optional[float] = None  # For metric rules
    required: bool = True  # If True, pattern must be present; if False, must be absent

    # Context
    applies_to: List[str] = field(default_factory=list)  # e.g., ["function", "class", "module"]
    exceptions: List[str] = field(default_factory=list)  # Patterns to exclude

    # Validation function name (for custom validators)
    validator: Optional[str] = None
    validator_config: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'rule_id': self.rule_id,
            'name': self.name,
            'description': self.description,
            'rule_type': self.rule_type.value,
            'severity': self.severity.value,
            'pattern': self.pattern,
            'max_value': self.max_value,
            'min_value': self.min_value,
            'required': self.required,
            'applies_to': self.applies_to,
            'exceptions': self.exceptions,
            'validator': self.validator,
            'validator_config': self.validator_config
        }


@dataclass
class ContractViolation:
    """Represents a contract violation found in code."""
    rule: ContractRule
    location: str  # File path or function name
    line_number: Optional[int] = None
    message: str = ""
    code_snippet: Optional[str] = None
    suggestion: Optional[str] = None

    def __str__(self) -> str:
        """Format violation for display."""
        loc = f"{self.location}:{self.line_number}" if self.line_number else self.location
        return (
            f"[{self.rule.severity.value.upper()}] {self.rule.name} ({self.rule.rule_id})\n"
            f"  Location: {loc}\n"
            f"  Message: {self.message}\n"
            f"  {self.suggestion if self.suggestion else ''}"
        )


@dataclass
class CodeContract:
    """
    A complete code contract specification.

    Defines all rules that must be satisfied by generated code.
    """
    contract_id: str
    name: str
    description: str
    version: str = "1.0.0"

    rules: List[ContractRule] = field(default_factory=list)

    # Metadata
    tags: List[str] = field(default_factory=list)
    author: Optional[str] = None
    created_at: Optional[str] = None

    def get_rules_by_type(self, rule_type: ContractType) -> List[ContractRule]:
        """Get all rules of a specific type."""
        return [rule for rule in self.rules if rule.rule_type == rule_type]

    def get_rules_by_severity(self, severity: ContractSeverity) -> List[ContractRule]:
        """Get all rules of a specific severity."""
        return [rule for rule in self.rules if rule.severity == severity]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'contract_id': self.contract_id,
            'name': self.name,
            'description': self.description,
            'version': self.version,
            'rules': [rule.to_dict() for rule in self.rules],
            'tags': self.tags,
            'author': self.author,
            'created_at': self.created_at
        }

    def to_yaml(self) -> str:
        """Export contract to YAML format."""
        return yaml.dump(self.to_dict(), default_flow_style=False, sort_keys=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CodeContract':
        """Load contract from dictionary."""
        rules = []
        for rule_data in data.get('rules', []):
            rules.append(ContractRule(
                rule_id=rule_data['rule_id'],
                name=rule_data['name'],
                description=rule_data['description'],
                rule_type=ContractType(rule_data['rule_type']),
                severity=ContractSeverity(rule_data['severity']),
                pattern=rule_data.get('pattern'),
                max_value=rule_data.get('max_value'),
                min_value=rule_data.get('min_value'),
                required=rule_data.get('required', True),
                applies_to=rule_data.get('applies_to', []),
                exceptions=rule_data.get('exceptions', []),
                validator=rule_data.get('validator'),
                validator_config=rule_data.get('validator_config', {})
            ))

        return cls(
            contract_id=data['contract_id'],
            name=data['name'],
            description=data['description'],
            version=data.get('version', '1.0.0'),
            rules=rules,
            tags=data.get('tags', []),
            author=data.get('author'),
            created_at=data.get('created_at')
        )

    @classmethod
    def from_yaml(cls, yaml_path: Union[str, Path]) -> 'CodeContract':
        """Load contract from YAML file."""
        with open(yaml_path, 'r') as f:
            data = yaml.safe_load(f)
        return cls.from_dict(data)


@dataclass
class ComplianceReport:
    """Report on code contract compliance."""
    contract: CodeContract
    code_path: str
    violations: List[ContractViolation] = field(default_factory=list)
    passed_rules: List[ContractRule] = field(default_factory=list)

    @property
    def is_compliant(self) -> bool:
        """Check if code is fully compliant (no ERROR violations)."""
        return not any(v.rule.severity == ContractSeverity.ERROR for v in self.violations)

    @property
    def error_count(self) -> int:
        """Count ERROR violations."""
        return sum(1 for v in self.violations if v.rule.severity == ContractSeverity.ERROR)

    @property
    def warning_count(self) -> int:
        """Count WARNING violations."""
        return sum(1 for v in self.violations if v.rule.severity == ContractSeverity.WARNING)

    @property
    def info_count(self) -> int:
        """Count INFO violations."""
        return sum(1 for v in self.violations if v.rule.severity == ContractSeverity.INFO)

    @property
    def compliance_score(self) -> float:
        """Calculate compliance score (0.0 - 1.0)."""
        total_rules = len(self.contract.rules)
        if total_rules == 0:
            return 1.0
        return len(self.passed_rules) / total_rules

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'contract_id': self.contract.contract_id,
            'code_path': self.code_path,
            'is_compliant': self.is_compliant,
            'compliance_score': self.compliance_score,
            'error_count': self.error_count,
            'warning_count': self.warning_count,
            'info_count': self.info_count,
            'violations': [
                {
                    'rule_id': v.rule.rule_id,
                    'rule_name': v.rule.name,
                    'severity': v.rule.severity.value,
                    'location': v.location,
                    'line_number': v.line_number,
                    'message': v.message,
                    'suggestion': v.suggestion
                }
                for v in self.violations
            ],
            'passed_rules': [rule.rule_id for rule in self.passed_rules]
        }

    def to_markdown(self) -> str:
        """Generate markdown compliance report."""
        lines = [
            f"# Code Contract Compliance Report",
            f"",
            f"**Contract:** {self.contract.name} (v{self.contract.version})",
            f"**Code Path:** {self.code_path}",
            f"**Compliance Score:** {self.compliance_score:.1%}",
            f"",
            f"## Summary",
            f"",
            f"- ❌ Errors: {self.error_count}",
            f"- ⚠️  Warnings: {self.warning_count}",
            f"- ℹ️  Info: {self.info_count}",
            f"- ✅ Passed: {len(self.passed_rules)}",
            f"",
        ]

        if self.violations:
            lines.extend([
                f"## Violations",
                f"",
            ])

            for v in sorted(self.violations, key=lambda x: x.rule.severity.value):
                emoji = "❌" if v.rule.severity == ContractSeverity.ERROR else "⚠️" if v.rule.severity == ContractSeverity.WARNING else "ℹ️"
                loc = f"{v.location}:{v.line_number}" if v.line_number else v.location

                lines.extend([
                    f"### {emoji} {v.rule.name}",
                    f"",
                    f"- **Rule ID:** {v.rule.rule_id}",
                    f"- **Severity:** {v.rule.severity.value.upper()}",
                    f"- **Location:** {loc}",
                    f"- **Message:** {v.message}",
                ])

                if v.suggestion:
                    lines.extend([
                        f"- **Suggestion:** {v.suggestion}",
                    ])

                if v.code_snippet:
                    lines.extend([
                        f"",
                        f"```python",
                        v.code_snippet,
                        f"```",
                    ])

                lines.append("")

        if self.passed_rules:
            lines.extend([
                f"## Passed Rules",
                f"",
            ])
            for rule in self.passed_rules:
                lines.append(f"- ✅ {rule.name} ({rule.rule_id})")

        return "\n".join(lines)

    def __str__(self) -> str:
        """String representation."""
        status = "✅ COMPLIANT" if self.is_compliant else "❌ NON-COMPLIANT"
        return (
            f"{status}\n"
            f"Contract: {self.contract.name}\n"
            f"Score: {self.compliance_score:.1%}\n"
            f"Errors: {self.error_count}, Warnings: {self.warning_count}, Info: {self.info_count}"
        )


class ContractLoader:
    """Loads and manages code contracts."""

    def __init__(self, contract_dir: Optional[Union[str, Path]] = None):
        """
        Initialize contract loader.

        Args:
            contract_dir: Directory containing contract YAML files
        """
        self.contract_dir = Path(contract_dir) if contract_dir else Path("contracts")
        self.contracts: Dict[str, CodeContract] = {}

    def load_contract(self, contract_path: Union[str, Path]) -> CodeContract:
        """Load a single contract from YAML file."""
        contract = CodeContract.from_yaml(contract_path)
        self.contracts[contract.contract_id] = contract
        logger.info(f"Loaded contract: {contract.name} ({contract.contract_id})")
        return contract

    def load_all_contracts(self) -> List[CodeContract]:
        """Load all contracts from the contract directory."""
        if not self.contract_dir.exists():
            logger.warning(f"Contract directory not found: {self.contract_dir}")
            return []

        contracts = []
        for yaml_file in self.contract_dir.glob("*.yaml"):
            try:
                contract = self.load_contract(yaml_file)
                contracts.append(contract)
            except Exception as e:
                logger.error(f"Failed to load contract from {yaml_file}: {e}")

        return contracts

    def get_contract(self, contract_id: str) -> Optional[CodeContract]:
        """Get a loaded contract by ID."""
        return self.contracts.get(contract_id)

    def get_contracts_by_tag(self, tag: str) -> List[CodeContract]:
        """Get all contracts with a specific tag."""
        return [c for c in self.contracts.values() if tag in c.tags]
