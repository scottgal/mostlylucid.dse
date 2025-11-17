Feature: Bandit Security Scanner Tool
  As a developer
  I want to scan Python code for security vulnerabilities
  So that I can identify and fix security issues early

  Background:
    Given bandit is installed
    And the tool is properly configured

  @happy-path @deterministic
  Scenario: Scan secure Python file
    Given a Python file with no security issues
    When the bandit scanner executes
    Then the check should pass
    And the output should indicate no issues found
    And the exit code should be 0

  @unhappy-path @security
  Scenario: Detect SQL injection vulnerability
    Given a Python file with SQL injection vulnerability
    When the bandit scanner executes
    Then the check should fail
    And the output should report SQL injection risk
    And the issue should be marked as HIGH severity
    And the exit code should be 1

  @unhappy-path @security
  Scenario: Detect hardcoded passwords
    Given a Python file with hardcoded passwords
    When the bandit scanner executes
    Then the check should fail
    And the output should report hardcoded password risk
    And the issue should be marked as MEDIUM or HIGH severity
    And the exit code should be 1

  @unhappy-path @security
  Scenario: Detect use of eval()
    Given a Python file using eval() function
    When the bandit scanner executes
    Then the check should fail
    And the output should report dangerous eval() usage
    And the issue should be marked as HIGH severity
    And the exit code should be 1

  @severity-filtering
  Scenario: Filter by severity level - HIGH only
    Given a Python file with LOW, MEDIUM, and HIGH severity issues
    When the bandit scanner executes with --level=high flag
    Then only HIGH severity issues should be reported
    And MEDIUM and LOW issues should be filtered out

  @severity-filtering
  Scenario: Filter by severity level - MEDIUM and above
    Given a Python file with LOW, MEDIUM, and HIGH severity issues
    When the bandit scanner executes with --level=medium flag
    Then MEDIUM and HIGH severity issues should be reported
    And LOW issues should be filtered out

  @confidence-filtering
  Scenario: Filter by confidence level
    Given a Python file with various security issues
    When the bandit scanner executes with --confidence=high flag
    Then only HIGH confidence issues should be reported
    And lower confidence issues should be filtered out

  @edge-case
  Scenario: Handle non-existent file
    Given a non-existent file path
    When the bandit scanner executes
    Then the check should fail
    And the output should indicate file not found
    And the exit code should be 2

  @performance
  Scenario: Fast execution on large file
    Given a Python file with 1000 lines of code
    When the bandit scanner executes
    Then the execution time should be less than 3000 milliseconds
    And the memory usage should be less than 80 MB

  @recursive
  Scenario: Recursive directory scanning
    Given a directory with multiple Python files
    When the bandit scanner executes in recursive mode
    Then all Python files should be scanned
    And issues from all files should be reported
    And the summary should include all files

  @json-output
  Scenario: JSON output format
    Given a Python file with security issues
    When the bandit scanner executes with --json flag
    Then the output should be valid JSON
    And the JSON should contain issue details
    And each issue should include severity, confidence, and line number

  @integration
  Scenario: Integration with static analysis pipeline
    Given a Python file with security vulnerabilities
    When the static analysis pipeline runs
    Then bandit should execute with priority 105
    And security issues should be reported
    And the pipeline should fail if HIGH severity issues exist

  Scenario Outline: Detect common vulnerabilities
    Given a Python file with <vulnerability_type>
    When the bandit scanner executes
    Then the check should fail
    And the output should report <vulnerability_type>
    And the severity should be <severity_level>

    Examples:
      | vulnerability_type        | severity_level |
      | SQL injection             | HIGH           |
      | Command injection         | HIGH           |
      | Hardcoded password        | MEDIUM         |
      | Use of insecure random    | MEDIUM         |
      | Use of assert in prod     | LOW            |
      | Use of pickle             | MEDIUM         |
      | Weak crypto algorithm     | HIGH           |

  @installation
  Scenario: Auto-install bandit when missing
    Given bandit is not installed
    When the bandit scanner executes with --install flag
    Then bandit should be installed automatically
    And the check should proceed normally
