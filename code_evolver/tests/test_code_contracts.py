"""
Tests for Code Contract System
"""
import pytest
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.code_contract import (
    CodeContract,
    ContractRule,
    ContractType,
    ContractSeverity,
    ContractLoader,
)
from src.contract_validator import ContractValidator


class TestContractLoading:
    """Test contract loading functionality."""

    def test_load_enterprise_logging_contract(self):
        """Test loading the enterprise logging contract."""
        contract_path = Path(__file__).parent.parent / "contracts" / "enterprise_logging.yaml"

        if not contract_path.exists():
            pytest.skip(f"Contract file not found: {contract_path}")

        contract = CodeContract.from_yaml(contract_path)

        assert contract.contract_id == "enterprise_logging"
        assert contract.name == "Enterprise Logging Requirements"
        assert len(contract.rules) > 0
        assert "logging" in contract.tags

    def test_load_call_tool_wrapper_contract(self):
        """Test loading the call tool wrapper contract."""
        contract_path = Path(__file__).parent.parent / "contracts" / "call_tool_wrapper.yaml"

        if not contract_path.exists():
            pytest.skip(f"Contract file not found: {contract_path}")

        contract = CodeContract.from_yaml(contract_path)

        assert contract.contract_id == "call_tool_wrapper"
        assert len(contract.rules) > 0

    def test_load_all_contracts(self):
        """Test loading all contracts from directory."""
        contracts_dir = Path(__file__).parent.parent / "contracts"

        if not contracts_dir.exists():
            pytest.skip(f"Contracts directory not found: {contracts_dir}")

        loader = ContractLoader(contracts_dir)
        contracts = loader.load_all_contracts()

        assert len(contracts) >= 4  # We created 4 contracts


class TestLoggingContract:
    """Test validation against logging contract."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = ContractValidator()

        # Create a minimal logging contract
        self.contract = CodeContract(
            contract_id="test_logging",
            name="Test Logging Contract",
            description="Test contract for logging",
            rules=[
                ContractRule(
                    rule_id="LOG-001",
                    name="Logging Import Required",
                    description="Must import logging",
                    rule_type=ContractType.LIBRARY,
                    severity=ContractSeverity.ERROR,
                    pattern="^logging$",
                    required=True
                ),
                ContractRule(
                    rule_id="LOG-002",
                    name="Logger Instance Required",
                    description="Must create logger",
                    rule_type=ContractType.STRUCTURAL,
                    severity=ContractSeverity.ERROR,
                    validator="has_logging"
                )
            ]
        )

    def test_valid_logging_code(self):
        """Test code that satisfies logging contract."""
        code = """
import logging

logger = logging.getLogger(__name__)

def process_data(data):
    logger.info("Processing data")
    return data
"""
        report = self.validator.validate(code, self.contract)

        assert report.is_compliant
        assert report.error_count == 0
        assert report.compliance_score == 1.0

    def test_missing_logging_import(self):
        """Test code without logging import."""
        code = """
def process_data(data):
    return data
"""
        report = self.validator.validate(code, self.contract)

        assert not report.is_compliant
        assert report.error_count > 0
        assert any("import" in v.message.lower() for v in report.violations)

    def test_missing_logger_instance(self):
        """Test code without logger instance."""
        code = """
import logging

def process_data(data):
    return data
"""
        report = self.validator.validate(code, self.contract)

        # Should have logging import but no logger instance
        violations = [v for v in report.violations if "instance" in v.message.lower()]
        assert len(violations) > 0


class TestFunctionLengthContract:
    """Test validation against function length contract."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = ContractValidator()

        self.contract = CodeContract(
            contract_id="test_length",
            name="Test Function Length Contract",
            description="Test contract for function length",
            rules=[
                ContractRule(
                    rule_id="LEN-001",
                    name="Max Function Length",
                    description="Functions must not exceed 10 lines",
                    rule_type=ContractType.METRIC,
                    severity=ContractSeverity.WARNING,
                    validator="max_function_length",
                    max_value=10
                )
            ]
        )

    def test_short_function(self):
        """Test function within length limit."""
        code = """
def short_function():
    x = 1
    y = 2
    return x + y
"""
        report = self.validator.validate(code, self.contract)

        assert report.is_compliant
        assert report.warning_count == 0

    def test_long_function(self):
        """Test function exceeding length limit."""
        code = """
def long_function():
    line_1 = 1
    line_2 = 2
    line_3 = 3
    line_4 = 4
    line_5 = 5
    line_6 = 6
    line_7 = 7
    line_8 = 8
    line_9 = 9
    line_10 = 10
    line_11 = 11
    return sum([line_1, line_2, line_3, line_4, line_5])
"""
        report = self.validator.validate(code, self.contract)

        assert report.warning_count > 0
        assert any("length" in v.message.lower() for v in report.violations)


class TestLibraryContract:
    """Test validation against library restrictions contract."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = ContractValidator()

        self.contract = CodeContract(
            contract_id="test_library",
            name="Test Library Contract",
            description="Test contract for library restrictions",
            rules=[
                ContractRule(
                    rule_id="LIB-001",
                    name="No Eval",
                    description="Never use eval",
                    rule_type=ContractType.PATTERN,
                    severity=ContractSeverity.ERROR,
                    pattern=r'\beval\s*\(',
                    required=False  # Must NOT be present
                ),
                ContractRule(
                    rule_id="LIB-002",
                    name="No Pickle",
                    description="Do not import pickle",
                    rule_type=ContractType.LIBRARY,
                    severity=ContractSeverity.WARNING,
                    pattern="^pickle$",
                    required=False  # Must NOT be present
                )
            ]
        )

    def test_clean_code(self):
        """Test code without forbidden patterns."""
        code = """
import json

def load_data(filename):
    with open(filename) as f:
        return json.load(f)
"""
        report = self.validator.validate(code, self.contract)

        assert report.is_compliant
        assert report.error_count == 0

    def test_forbidden_eval(self):
        """Test code with forbidden eval."""
        code = """
def dangerous_function(code_string):
    return eval(code_string)
"""
        report = self.validator.validate(code, self.contract)

        assert report.error_count > 0
        assert any("eval" in v.message.lower() for v in report.violations)

    def test_forbidden_library(self):
        """Test code with forbidden library import."""
        code = """
import pickle

def load_data(filename):
    with open(filename, 'rb') as f:
        return pickle.load(f)
"""
        report = self.validator.validate(code, self.contract)

        assert report.warning_count > 0
        assert any("pickle" in v.message.lower() for v in report.violations)


class TestComplianceReport:
    """Test compliance report generation."""

    def test_report_to_markdown(self):
        """Test markdown report generation."""
        validator = ContractValidator()

        contract = CodeContract(
            contract_id="test",
            name="Test Contract",
            description="Test",
            rules=[
                ContractRule(
                    rule_id="TEST-001",
                    name="Test Rule",
                    description="A test rule",
                    rule_type=ContractType.PATTERN,
                    severity=ContractSeverity.ERROR,
                    pattern="import.*",
                    required=True
                )
            ]
        )

        code = "# Empty file"
        report = validator.validate(code, contract, "test.py")

        markdown = report.to_markdown()

        assert "# Code Contract Compliance Report" in markdown
        assert "Test Contract" in markdown
        assert "test.py" in markdown

    def test_compliance_score(self):
        """Test compliance score calculation."""
        validator = ContractValidator()

        contract = CodeContract(
            contract_id="test",
            name="Test Contract",
            description="Test",
            rules=[
                ContractRule(
                    rule_id="R1",
                    name="Rule 1",
                    description="",
                    rule_type=ContractType.PATTERN,
                    severity=ContractSeverity.ERROR,
                    pattern="import logging",
                    required=True
                ),
                ContractRule(
                    rule_id="R2",
                    name="Rule 2",
                    description="",
                    rule_type=ContractType.PATTERN,
                    severity=ContractSeverity.ERROR,
                    pattern="def ",
                    required=True
                )
            ]
        )

        # Code satisfies one rule but not the other
        code = "import logging"
        report = validator.validate(code, contract)

        assert report.compliance_score == 0.5  # 1 out of 2 rules passed


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
