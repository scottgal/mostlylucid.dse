Feature: MyPy Type Checker Tool
  As a developer
  I want to check Python code for type errors
  So that I can catch bugs before runtime

  Background:
    Given mypy is installed
    And the tool is properly configured

  @happy-path @deterministic
  Scenario: Check well-typed Python file
    Given a Python file with correct type annotations
    When the mypy checker executes in strict mode
    Then the check should pass
    And the output should indicate no issues found
    And the exit code should be 0

  @unhappy-path
  Scenario: Detect type errors
    Given a Python file with type mismatches
    When the mypy checker executes in strict mode
    Then the check should fail
    And the output should list all type errors
    And each error should include file, line, and column
    And the exit code should be 1

  @error-codes
  Scenario: Show error codes with suggestions
    Given a Python file with type errors
    When the mypy checker executes with --show-error-codes flag
    Then each error should include an error code
    And the error codes should help identify the issue type
    And the exit code should be 1

  @strict-mode
  Scenario: Strict mode catches all issues
    Given a Python file with missing type annotations
    When the mypy checker executes in strict mode
    Then all missing annotations should be reported
    And all type errors should be caught
    And the exit code should be 1

  @non-strict
  Scenario: Non-strict mode is more lenient
    Given a Python file with some missing annotations
    When the mypy checker executes without strict mode
    Then only explicit type errors should be reported
    And missing annotations may be ignored
    And the exit code depends on errors found

  @ignore-imports
  Scenario: Ignore missing import stubs
    Given a Python file importing third-party libraries without stubs
    When the mypy checker executes with --ignore-missing-imports flag
    Then missing import errors should be ignored
    And only actual type errors should be reported

  @edge-case
  Scenario: Handle non-existent file
    Given a non-existent file path
    When the mypy checker executes
    Then the check should fail
    And the output should indicate file not found
    And the exit code should be 2

  @performance
  Scenario: Reasonable performance on large file
    Given a Python file with 1000 lines of typed code
    When the mypy checker executes
    Then the execution time should be less than 5000 milliseconds
    And the memory usage should be less than 100 MB

  @integration
  Scenario: Integration with static analysis pipeline
    Given a Python file with type errors
    When the static analysis pipeline runs
    Then mypy should execute with priority 115
    Then mypy should run after code modernization
    And type errors should be reported
    And the pipeline should fail if types don't match

  @json-output
  Scenario: JSON output format
    Given a Python file with type errors
    When the mypy checker executes with --json flag
    Then the output should be valid JSON
    And the JSON should contain error details
    And each error should have file, line, column, and message

  @incremental
  Scenario: Incremental type checking with cache
    Given a Python project with mypy cache
    When the mypy checker executes on unchanged files
    Then the cache should be used for faster checking
    And only changed files should be re-checked
    And the results should be consistent

  @installation
  Scenario: Auto-install mypy when missing
    Given mypy is not installed
    When the mypy checker executes with --install flag
    Then mypy should be installed automatically
    And the check should proceed normally
