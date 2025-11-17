# Complete Node Artifact Generation System

**Comprehensive File Generation with BDD and Performance Verification**

## Overview

Every generated tool/node now produces **5 critical files** that together form a complete, verifiable, and testable artifact. This ensures comprehensive documentation, testing, and performance validation.

## The 5 Required Files

### 1. `main.py` - Executable Code
The actual implementation of the tool/node.

**Location**: `registry/nodes/{node_id}/main.py`

**Contents**:
- Main function implementation
- Error handling
- Type hints
- Docstrings
- Example usage in `__main__`

### 2. `test_main.py` - Unit Tests
Comprehensive unit tests (generated via Pynguin or LLM).

**Location**: `registry/nodes/{node_id}/test_main.py`

**Features**:
- Uses pytest for testing
- Covers normal cases, edge cases, error handling
- Self-contained and runnable
- Generated via escalation system if needed

### 3. `{node_id}.feature` - Behave BDD Specification
Human-readable behavior specification in Gherkin format.

**Location**: `registry/nodes/{node_id}/{node_id}.feature`

**Example**:
```gherkin
Feature: Email Validator

  As a developer
  I want to validate email addresses
  So that I can ensure data quality

  Scenario: Valid email
    Given the system is initialized
    When I validate "user@example.com"
    Then the result should be True

  Scenario: Invalid email
    Given the system is initialized
    When I validate "invalid-email"
    Then the result should be False
```

**Generation**:
- Uses `behave_test_generator` tool if available
- Falls back to basic template if tool generation fails
- Based on specification and code

### 4. `locust_{node_id}.py` - Load Test Script
Runnable Locust performance test.

**Location**: `registry/nodes/{node_id}/locust_{node_id}.py`

**Example**:
```python
"""
Locust load test for email_validator

Usage:
    locust -f locust_email_validator.py --users 10 --spawn-rate 2 --run-time 30s
"""

from locust import HttpUser, task, between

class EmailValidatorUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def test_validation(self):
        response = self.client.post(
            "/api/email_validator",
            json={"email": "test@example.com"}
        )
        assert response.status_code == 200
```

**Generation**:
- Uses `locust_load_tester` tool if available
- Falls back to basic template if tool generation fails
- Includes realistic load patterns

### 5. `{node_id}_plan.txt` - Overseer's Plan
The original strategy/specification from the overseer.

**Location**: `registry/nodes/{node_id}/{node_id}_plan.txt`

**Contents**:
- Overseer's detailed planning/specification
- Approach strategy
- Implementation notes
- Critical details for code generator

**Purpose**:
- Preserves original intent
- Useful for future mutations
- Enables understanding of design decisions

## Code Generation Flow

```
User Request
    ↓
[1. Overseer Planning] → Saves to {node_id}_plan.txt
    ↓
[2. Code Generation] → Saves to main.py
    ↓
[3. Test Generation] → Saves to test_main.py
    ↓
[4. Run Tests] → Verify implementation
    ↓
[5. Save Specification] → Saves to specification.md
    ↓
[6. Generate BDD Spec] → Saves to {node_id}.feature
    ↓
[7. Generate Load Test] → Saves to locust_{node_id}.py
    ↓
[8. Execute Code] → Collect metrics
    ↓
[9. Verify BDD] → Run Behave tests
    ↓
[10. Measure Performance] → Run Locust (5s)
    ↓
[11. Calculate Quality Score] → BDD + Perf + Metrics
    ↓
[12. Register as Tool] → Store in RAG with quality score
```

## Quality Scoring System

The final quality score is calculated based on:

```python
quality_score = 1.0  # Base score

# BDD Compliance (+0.2)
if bdd_passed:
    quality_score += 0.2

# Performance Score (+0.0 to +0.3)
# Based on requests/sec from Locust:
#   0-10 req/s   → 0.0-0.15
#   10-100 req/s → 0.15-0.27
#   >100 req/s   → 0.3
quality_score += perf_score * 0.3

# Latency Bonus (+0.1)
if latency_ms < 100:
    quality_score += 0.1

# Memory Bonus (+0.1)
if memory_mb_peak < 10:
    quality_score += 0.1

# Maximum possible: 1.7
```

## BDD Verification (chat_cli.py:4345-4462)

**Method**: `_verify_bdd_and_performance()`

**Process**:
1. Look for `{node_id}.feature` file
2. Run `behave {node_id}.feature` in node directory
3. Check return code (0 = passed)
4. Record pass/fail for quality scoring

**Fallback**: If Behave not installed, skip gracefully

## Performance Measurement (chat_cli.py:4404-4456)

**Method**: `_verify_bdd_and_performance()` (same method)

**Process**:
1. Look for `locust_{node_id}.py` file
2. Run Locust headless for 5 seconds:
   ```bash
   locust -f locust_{node_id}.py --headless \
          --users 5 --spawn-rate 1 --run-time 5s
   ```
3. Parse output for `requests/s` metric
4. Normalize to 0-1 score
5. Add to quality calculation

**Fallback**: If Locust not installed, skip gracefully

## File Generation Methods

### Save Overseer Plan (chat_cli.py:4116-4139)

```python
def _save_overseer_plan(self, node_id: str, specification: str) -> None:
    """Save the overseer's plan to {node_id}_plan.txt"""
    plan_file = node_path / f"{node_id}_plan.txt"
    plan_file.write_text(specification, encoding='utf-8')
```

**Called**: Immediately after specification is generated (line 3461)

### Generate Behave Feature (chat_cli.py:4141-4219)

```python
def _generate_behave_feature(
    self, node_id, description, specification, code
) -> None:
    """Generate .feature file using behave_test_generator tool"""
    # Try tool-based generation
    result = call_tool("behave_test_generator", feature_input)

    # Fallback to basic template if tool fails
    if not result or not result.get("success"):
        basic_feature = f"""Feature: {description}
  Scenario: Basic execution
    Given the node {node_id} is loaded
    When I execute the main function
    Then the result should be valid
"""
        feature_file.write_text(basic_feature)
```

**Called**: Immediately after saving plan (line 3464)

### Generate Locust Test (chat_cli.py:4221-4343)

```python
def _generate_locust_load_test(
    self, node_id, description, code
) -> None:
    """Generate Locust test using locust_load_tester tool"""
    # Try tool-based generation
    result = call_tool("locust_load_tester", locust_input)

    # Fallback to basic template if tool fails
    if not result or not result.get("success"):
        basic_locust = f"""
from locust import HttpUser, task, between

class {node_id.title().replace('_', '')}User(HttpUser):
    @task
    def test_main_function(self):
        response = self.client.get(f"/api/{node_id}")
        assert response.status_code == 200
"""
        locust_file.write_text(basic_locust)
```

**Called**: Immediately after generating .feature (line 3467)

## Integration Points

### During Code Generation (chat_cli.py:3460-3467)

After saving specification.md:

```python
# Save the overseer's plan/specification
self._save_overseer_plan(node_id, specification)

# Generate Behave .feature file for BDD testing
self._generate_behave_feature(node_id, description, specification, code)

# Generate Locust load test script
self._generate_locust_load_test(node_id, description, code)
```

### Before Quality Scoring (chat_cli.py:3752-3766)

After execution completes:

```python
# Step 9.5: Verify BDD spec and get performance scores
bdd_passed = False
perf_score = 0.0
if metrics["success"]:
    console.print(f"\n[cyan]Verifying BDD specification and performance...[/cyan]")

    # Run BDD verification
    bdd_passed, perf_score = self._verify_bdd_and_performance(
        node_id, description, specification, code
    )

    if bdd_passed:
        console.print(f"[green]✓ BDD specification verified[/green]")
```

## Benefits

### 1. Complete Documentation
- **Plan**: Original intent and strategy
- **Specification**: Detailed requirements
- **BDD**: Behavior in human-readable format
- **Code**: Actual implementation

### 2. Comprehensive Testing
- **Unit Tests**: Code-level testing
- **BDD Tests**: Behavior verification
- **Load Tests**: Performance validation

### 3. Quality Assurance
- BDD compliance ensures behavior matches spec
- Performance tests catch regression
- Quality scores reflect real-world readiness

### 4. Mutation Safety
With all 5 files:
- Can compare BDD specs to detect breaking changes
- Can re-run performance tests to catch degradation
- Can reference original plan to understand intent
- Can verify unit tests still pass

## Example: Complete Node Structure

```
registry/nodes/email_validator/
├── main.py                      # Implementation
├── test_main.py                 # Unit tests
├── email_validator.feature      # BDD spec
├── locust_email_validator.py    # Load test
├── email_validator_plan.txt     # Overseer's plan
└── specification.md             # Detailed spec
```

## Future: Breaking Change Detection

When a tool is mutated:

1. **Load old BDD spec** from `{node_id}.feature`
2. **Generate new BDD spec** based on mutation
3. **Compare specs** using 4B classifier LLM:
   - If significantly different → **Breaking change**
   - Requires god-mode LLM confirmation
   - Version bumps to next major (e.g., 1.x.x → 2.0.0)
   - Breaking changes documented in tool entry
4. **If BDD spec unchanged**:
   - Allow performance changes
   - Minor/patch version bump
5. **If BDD fails** after mutation:
   - Automatically treat as breaking change
   - Escalate to god-mode for resolution

## Configuration

No special configuration required. The system:
- Always generates all 5 files
- Gracefully handles missing tools (behave, locust)
- Falls back to basic templates if tool generation fails
- Never blocks workflow if verification fails

## Monitoring

Check generated files:

```bash
# List all nodes and their files
ls -R registry/nodes/

# Check a specific node
tree registry/nodes/email_validator/

# Verify BDD manually
cd registry/nodes/email_validator/
behave email_validator.feature

# Run load test manually
cd registry/nodes/email_validator/
locust -f locust_email_validator.py --headless --users 10 --run-time 30s
```

## Technical Notes

- All file generation is non-blocking (errors logged but don't fail workflow)
- BDD and performance verification happen after execution succeeds
- Quality scores stored in RAG for tool selection
- Original overseer plan preserved for future reference
- Fallback templates ensure files are always created

---

**Result**: Every generated node is now a complete, testable, verifiable artifact with comprehensive documentation and performance validation!
