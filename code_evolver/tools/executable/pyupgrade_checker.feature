Feature: Pyupgrade Checker Tool
  As a developer
  I want to modernize Python syntax automatically
  So that my code uses the latest Python features

  Background:
    Given pyupgrade is installed
    And the tool is properly configured

  @happy-path @deterministic
  Scenario: Check modern Python code
    Given a Python file with modern syntax
    When the pyupgrade checker executes
    Then the check should pass
    And the output should indicate no changes needed
    And the exit code should be 0

  @happy-path @auto-fix
  Scenario: Upgrade to f-strings from format()
    Given a Python file using .format() method
    When the pyupgrade checker executes with --fix flag
    Then the code should be upgraded to f-strings
    And the file should be modified in-place
    And the exit code should be 0

  @happy-path @auto-fix
  Scenario: Upgrade to f-strings from % formatting
    Given a Python file using % string formatting
    When the pyupgrade checker executes with --fix flag
    Then the code should be upgraded to f-strings
    And the file should be modified in-place
    And the exit code should be 0

  @happy-path @auto-fix
  Scenario: Modernize type annotations
    Given a Python file with old-style type annotations
    When the pyupgrade checker executes with --fix and --py39-plus flags
    Then the type annotations should be modernized
    And the file should use newer syntax
    And the exit code should be 0

  @happy-path @auto-fix
  Scenario: Upgrade dict() to {}
    Given a Python file using dict() constructor
    When the pyupgrade checker executes with --fix flag
    Then dict() should be replaced with {}
    And the file should be modified in-place
    And the exit code should be 0

  @edge-case
  Scenario: Handle non-existent file
    Given a non-existent file path
    When the pyupgrade checker executes
    Then the check should fail
    And the output should indicate file not found
    And the exit code should be 2

  @performance
  Scenario: Fast execution on large file
    Given a Python file with 1000 lines of code
    When the pyupgrade checker executes
    Then the execution time should be less than 1000 milliseconds
    And the memory usage should be less than 30 MB

  @integration
  Scenario: Integration with static analysis pipeline
    Given a Python file with old-style syntax
    When the static analysis pipeline runs with auto-fix
    Then pyupgrade should execute with priority 125
    And the syntax should be modernized before type checking
    And mypy should see the modern code

  @dry-run
  Scenario: Check mode without modifications
    Given a Python file with old-style syntax
    When the pyupgrade checker executes without --fix flag
    Then the check should detect upgradeable code
    And the file should not be modified
    And the output should show the upgraded version
    And the exit code should be 1

  Scenario Outline: Target specific Python versions
    Given a Python file with syntax for <old_version>
    When the pyupgrade checker executes with --<target_version> flag
    Then the code should be upgraded to <target_version> syntax
    And version-specific features should be applied

    Examples:
      | old_version | target_version |
      | py36        | py38-plus      |
      | py37        | py39-plus      |
      | py38        | py310-plus     |
      | py39        | py311-plus     |

  @keep-typing
  Scenario: Keep runtime typing annotations
    Given a Python file with runtime type annotations
    When the pyupgrade checker executes with --keep-runtime-typing flag
    Then the runtime annotations should be preserved
    And only non-runtime code should be upgraded
    And the exit code should be 0

  @installation
  Scenario: Auto-install pyupgrade when missing
    Given pyupgrade is not installed
    When the pyupgrade checker executes with --install flag
    Then pyupgrade should be installed automatically
    And the check should proceed normally
