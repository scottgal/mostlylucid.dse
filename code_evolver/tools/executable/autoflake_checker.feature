Feature: Autoflake Checker Tool
  As a developer
  I want to remove unused imports and variables automatically
  So that my code stays clean and maintainable

  Background:
    Given autoflake is installed
    And the tool is properly configured

  @happy-path @deterministic
  Scenario: Check file with no unused imports
    Given a Python file with all imports used
    When the autoflake checker executes
    Then the check should pass
    And the output should indicate no changes needed
    And the exit code should be 0

  @happy-path @auto-fix
  Scenario: Remove unused stdlib imports
    Given a Python file with unused stdlib imports
    When the autoflake checker executes with --fix flag
    Then the unused imports should be removed
    And the file should be modified in-place
    And the exit code should be 0

  @happy-path @aggressive
  Scenario: Remove all unused imports (aggressive mode)
    Given a Python file with unused third-party imports
    When the autoflake checker executes with --fix and --aggressive flags
    Then all unused imports should be removed
    And the file should be cleaned up
    And the exit code should be 0

  @happy-path
  Scenario: Remove unused variables
    Given a Python file with unused variables
    When the autoflake checker executes with --fix flag
    Then the unused variables should be removed
    And the file should be modified in-place
    And the exit code should be 0

  @edge-case
  Scenario: Handle file with duplicate dictionary keys
    Given a Python file with duplicate dictionary keys
    When the autoflake checker executes with --fix flag
    Then the duplicate keys should be removed
    And only the last occurrence should remain
    And the exit code should be 0

  @edge-case
  Scenario: Handle non-existent file
    Given a non-existent file path
    When the autoflake checker executes
    Then the check should fail
    And the output should indicate file not found
    And the exit code should be 2

  @performance
  Scenario: Fast execution on large file
    Given a Python file with 1000 lines of code
    When the autoflake checker executes
    Then the execution time should be less than 1000 milliseconds
    And the memory usage should be less than 30 MB

  @integration
  Scenario: Integration with static analysis pipeline
    Given a Python file with unused imports
    When the static analysis pipeline runs with auto-fix
    Then autoflake should execute with priority 130
    And unused imports should be removed before other checks
    And the file should be clean for subsequent validators

  @dry-run
  Scenario: Check mode without modifications
    Given a Python file with unused imports
    When the autoflake checker executes without --fix flag
    Then the check should detect issues
    And the file should not be modified
    And the output should show what would be changed
    And the exit code should be 1

  @installation
  Scenario: Auto-install autoflake when missing
    Given autoflake is not installed
    When the autoflake checker executes with --install flag
    Then autoflake should be installed automatically
    And the check should proceed normally
