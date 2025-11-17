# Using Pip Packages in Workflows

This guide explains how to use trusted pip packages in your mostlylucid DiSE workflows to extend tool capabilities.

## Overview

mostlylucid DiSE now supports declarative pip package dependencies in workflows. This allows your generated tools to leverage powerful Python libraries like:

- **Web scraping**: requests, beautifulsoup4, httpx
- **Data analysis**: pandas, numpy, scipy
- **Visualization**: matplotlib, pillow
- **NLP**: nltk, textblob
- **File handling**: openpyxl, PyPDF2, python-docx
- And many more!

## Security Model

All pip packages are validated against a **trusted package allowlist** to ensure security:

- ✅ **Allowlist-based**: Only pre-approved packages can be installed
- ✅ **Version constraints**: Packages must match approved version ranges
- ✅ **Audit logging**: All installation attempts are logged
- ✅ **Blocked packages**: Dangerous packages are explicitly blocked

### Configuration File

The allowlist is defined in `code_evolver/trusted_packages.yaml`:

```yaml
trusted_packages:
  - name: "requests"
    versions: [">=2.31.0", "<3.0.0"]
    purpose: "HTTP client for API calls"
    categories: ["http", "api", "web"]
```

## Using Pip Packages in Workflows

### Method 1: Declarative Dependencies in Workflow JSON

Add pip packages to your workflow's `dependencies` section:

```json
{
  "workflow_id": "my_workflow",
  "description": "My awesome workflow",
  "dependencies": {
    "llm_tools": ["content_generator"],
    "python_tools": [],
    "pip_packages": [
      {
        "name": "requests",
        "version": ">=2.31.0"
      },
      {
        "name": "beautifulsoup4",
        "version": ">=4.12.0"
      }
    ]
  },
  "steps": [...]
}
```

### Method 2: Programmatic API (Python)

Use the WorkflowSpec builder pattern:

```python
from src.workflow_spec import WorkflowSpec, WorkflowStep, StepType

workflow = WorkflowSpec(
    workflow_id="web_scraper",
    description="Scrapes and analyzes web content"
)

# Add pip package dependencies
workflow.add_pip_package("requests", ">=2.31.0")
workflow.add_pip_package("beautifulsoup4", ">=4.12.0")

# Add workflow steps that use these packages
workflow.add_step(WorkflowStep(
    step_id="fetch_page",
    step_type=StepType.PYTHON_TOOL,
    description="Fetch web page using requests",
    generate_tool=True,
    input_mapping={"url": "${inputs.url}"}
))

# Save to JSON
with open("workflows/my_workflow.json", "w") as f:
    f.write(workflow.to_json())
```

### Method 3: Direct Installation via pip_install_tool

For one-off installations, use the pip install tool:

```bash
echo '{"package": "requests>=2.31.0", "context": "my_workflow"}' | \
  python pip_install_tool.py
```

Response:
```json
{
  "status": "installed",
  "package": "requests>=2.31.0",
  "package_name": "requests",
  "version": ">=2.31.0",
  "validated": true
}
```

Batch installation:
```bash
echo '{
  "packages": ["requests>=2.31.0", "beautifulsoup4>=4.12.0"],
  "context": "web_scraper_workflow"
}' | python pip_install_tool.py
```

## Package Validation API

### Python API

```python
from src.package_validator import validate_package, validate_packages, list_packages

# Validate a single package
is_valid, message = validate_package("requests", ">=2.31.0", "my_context")
print(f"Valid: {is_valid}, Message: {message}")

# Validate multiple packages
packages = [
    {"name": "requests", "version": ">=2.31.0"},
    {"name": "pandas", "version": ">=2.0.0"}
]
all_valid, errors = validate_packages(packages, "data_workflow")

# List all trusted packages
all_packages = list_packages()
for pkg in all_packages:
    print(f"{pkg['name']}: {pkg['purpose']}")

# List packages by category
web_packages = list_packages(category="web")
```

### Validation Response Codes

- **installed**: Package successfully installed
- **rejected**: Package not in allowlist or version mismatch
- **failed**: Installation error (network, pip failure, etc.)

## Example Workflows

### Web Scraping Workflow

File: `workflows/web_scraper_workflow.json`

Uses `requests` and `beautifulsoup4` to fetch and parse web pages:

```json
{
  "workflow_id": "web_scraper_workflow",
  "dependencies": {
    "pip_packages": [
      {"name": "requests", "version": ">=2.31.0"},
      {"name": "beautifulsoup4", "version": ">=4.12.0"}
    ]
  },
  "steps": [
    {
      "step_id": "fetch_webpage",
      "type": "python_tool",
      "description": "Fetch web page using requests",
      "generate_tool": true
    },
    {
      "step_id": "extract_data",
      "type": "python_tool",
      "description": "Parse HTML with BeautifulSoup",
      "generate_tool": true
    }
  ]
}
```

### Data Analysis Workflow

File: `workflows/data_analysis_workflow.json`

Uses `pandas`, `numpy`, and `matplotlib` for data analysis:

```json
{
  "workflow_id": "data_analysis_workflow",
  "dependencies": {
    "pip_packages": [
      {"name": "pandas", "version": ">=2.0.0"},
      {"name": "matplotlib", "version": ">=3.7.0"},
      {"name": "numpy", "version": ">=1.24.0"}
    ]
  },
  "steps": [
    {
      "step_id": "load_data",
      "type": "python_tool",
      "description": "Load CSV with pandas"
    },
    {
      "step_id": "analyze_data",
      "type": "python_tool",
      "description": "Statistical analysis"
    },
    {
      "step_id": "create_visualization",
      "type": "python_tool",
      "description": "Generate charts with matplotlib"
    }
  ]
}
```

## Adding New Trusted Packages

### Manual Addition

Edit `trusted_packages.yaml`:

```yaml
trusted_packages:
  - name: "your-package"
    versions: [">=1.0.0"]
    purpose: "Description of what this package does"
    categories: ["category1", "category2"]
```

### Programmatic Addition

```python
from src.package_validator import get_validator

validator = get_validator()
validator.add_trusted_package(
    name="your-package",
    versions=[">=1.0.0"],
    purpose="Your package description",
    categories=["utility"]
)
```

## Tool Definition with Requirements

When creating portable workflows, embed package requirements in tool definitions:

```json
{
  "portable": true,
  "tools": {
    "web_scraper": {
      "tool_id": "web_scraper",
      "name": "Web Scraper",
      "type": "python",
      "source_code": "import requests\n...",
      "requirements": ["requests>=2.31.0", "beautifulsoup4>=4.12.0"]
    }
  }
}
```

## Integration with Code Generation

When the mostlylucid DiSE generates tools that need pip packages:

1. **Declare dependencies** in the workflow spec
2. **Validation** occurs automatically before installation
3. **Installation** happens before tool execution
4. **Audit log** records all package operations

Example codegen flow:

```
User Request → Overseer Plans Workflow → Declares pip_packages
    ↓
Package Validator Checks Allowlist
    ↓
pip_install_tool Installs Packages
    ↓
Code Generator Creates Tools Using Packages
    ↓
Workflow Executor Runs Tools
```

## Security Best Practices

1. **Review the allowlist** before adding new packages
2. **Use version constraints** to avoid unexpected updates
3. **Check audit logs** regularly: `logs/pip_installations.log`
4. **Limit packages per workflow** (default: 10 max)
5. **Only add packages you trust** - they have full system access

### Blocked Operations

The following are automatically rejected:

- Packages not in `trusted_packages.yaml`
- Version specifiers outside allowed ranges
- Packages in the `blocked_packages` list
- Batch requests exceeding `max_packages_per_workflow`

## Audit Logging

All installation attempts are logged to `logs/pip_installations.log`:

```
[2025-01-17T10:30:00] SUCCESS | Package: requests | Version: >=2.31.0 | Context: web_scraper_workflow | Message: Package 'requests' validated successfully
[2025-01-17T10:30:15] FAILED | Package: malicious-pkg | Version: any | Context: unknown | Message: Package validation failed: Package 'malicious-pkg' is not in the trusted packages list
```

## Troubleshooting

### Package Rejected

**Error**: `Package validation failed: Package 'xyz' is not in the trusted packages list`

**Solution**: Add the package to `trusted_packages.yaml` or choose an alternative from the allowlist.

### Version Mismatch

**Error**: `Version '>=3.0.0' does not match trusted versions: ['>=2.31.0', '<3.0.0']`

**Solution**: Adjust your version constraint to match the allowed range.

### Installation Timeout

**Error**: `Installation timeout after 120 seconds`

**Solution**: Check your network connection or increase timeout in the workflow step.

### Import Errors in Generated Code

**Error**: `ModuleNotFoundError: No module named 'requests'`

**Solution**: Ensure the package is declared in `pip_packages` before the step that uses it.

## API Reference

### PackageValidator Class

```python
class PackageValidator:
    def validate_package(package_name: str, version_spec: Optional[str], context: str) -> Tuple[bool, str]
    def validate_batch(packages: List[Dict], context: str) -> Tuple[bool, List[str]]
    def get_package_info(package_name: str) -> Optional[Dict]
    def list_trusted_packages(category: Optional[str]) -> List[Dict]
    def add_trusted_package(name: str, versions: List[str], purpose: str, categories: List[str])
```

### WorkflowSpec Methods

```python
class WorkflowSpec:
    def add_pip_package(name: str, version: Optional[str] = None) -> WorkflowSpec
    # Returns self for method chaining
```

### pip_install_tool Input Format

```json
// Single package
{
  "package": "package-name>=1.0.0",
  "context": "workflow_id"
}

// Batch installation
{
  "packages": ["pkg1>=1.0.0", "pkg2>=2.0.0"],
  "context": "workflow_id"
}
```

## Configuration Reference

### trusted_packages.yaml Structure

```yaml
trusted_packages:
  - name: "package-name"          # Required: PyPI package name
    versions: [">=1.0.0"]          # Required: List of version specifiers
    purpose: "What it does"        # Required: Human-readable description
    categories: ["web", "data"]    # Required: List of category tags

security:
  blocked_packages: ["dangerous"]  # Packages that cannot be installed
  requires_approval: ["system"]    # Packages needing explicit approval
  max_packages_per_workflow: 10    # Max packages per workflow
  log_installations: true          # Enable audit logging
  log_file: "logs/pip_installations.log"

sources:
  default_index: "https://pypi.org/simple"
  pypi_only: true
  install_timeout: 300
```

## Next Steps

- Review example workflows in `code_evolver/workflows/`
- Check the trusted package list in `trusted_packages.yaml`
- Add packages you need for your use case
- Create workflows that leverage these capabilities
- Monitor `logs/pip_installations.log` for security

## Related Files

- `/home/user/mostlylucid.dse/code_evolver/trusted_packages.yaml` - Package allowlist
- `/home/user/mostlylucid.dse/code_evolver/src/package_validator.py` - Validation service
- `/home/user/mostlylucid.dse/code_evolver/pip_install_tool.py` - Installation tool
- `/home/user/mostlylucid.dse/code_evolver/src/workflow_spec.py` - Workflow specifications
- `/home/user/mostlylucid.dse/code_evolver/workflows/web_scraper_workflow.json` - Example workflow
- `/home/user/mostlylucid.dse/code_evolver/workflows/data_analysis_workflow.json` - Example workflow
