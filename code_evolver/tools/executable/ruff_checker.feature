Feature: Ruff Checker Tool
  As a developer
  I want to use ruff to lint and format Python code
  So that I can maintain consistent code quality automatically

  Background:
    Given ruff is installed
    And the tool is properly configured

  @happy-path @deterministic
  Scenario: Check clean Python file
    Given a Python file with no linting issues
    When the ruff checker executes
    Then the check should pass
    And the exit code should be 0
    And the output should indicate no issues found

  @happy-path @auto-fix
  Scenario: Auto-fix simple linting issues
    Given a Python file with unused imports
    When the ruff checker executes with --fix flag
    Then the check should pass
    And the unused imports should be removed
    And the file should be modified in-place
    And the exit code should be 0

  @happy-path @formatting
  Scenario: Format code with ruff
    Given a Python file with inconsistent formatting
    When the ruff checker executes with --fix and --format flags
    Then the code should be formatted correctly
    And the linting issues should be fixed
    And the exit code should be 0

  @edge-case
  Scenario: Handle file with syntax errors
    Given a Python file with syntax errors
    When the ruff checker executes
    Then the check should fail
    And the output should indicate syntax errors
    And the exit code should be 1

  @edge-case
  Scenario: Handle non-existent file
    Given a non-existent file path
    When the ruff checker executes
    Then the check should fail
    And the output should indicate file not found
    And the exit code should be 2

  @performance
  Scenario: Fast execution on large file
    Given a Python file with 1000 lines of code
    When the ruff checker executes
    Then the execution time should be less than 500 milliseconds
    And the memory usage should be less than 50 MB

  @integration
  Scenario: Integration with static analysis pipeline
    Given multiple Python files with various issues
    When the static analysis pipeline runs
    Then ruff should execute with priority 135
    And ruff should auto-fix issues before other tools
    And all fixable issues should be resolved

  @json-output
  Scenario: JSON output format
    Given a Python file with linting issues
    When the ruff checker executes with --json flag
    Then the output should be valid JSON
    And the JSON should contain issue details
    And the JSON should include file paths and line numbers

  Scenario Outline: Check different Python versions
    Given a Python file targeting <python_version>
    When the ruff checker executes
    Then the check should use rules for <python_version>
    And version-specific issues should be reported

    Examples:
      | python_version |
      | py38           |
      | py39           |
      | py310          |
      | py311          |

  @installation
  Scenario: Auto-install ruff when missing
    Given ruff is not installed
    When the ruff checker executes with --install flag
    Then ruff should be installed automatically
    And the check should proceed normally
    And the exit code should be 0 or 1 based on issues
