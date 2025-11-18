# Interactive Workflow Runner

The Interactive Workflow Runner makes it easy to execute workflows by automatically prompting users for required inputs using LLM-generated natural language questions.

## Features

- **LLM-Powered Prompts**: Uses a fast 1B LLM (gemma3:1b) to generate friendly, conversational prompts from workflow input specifications
- **Rich Terminal UI**: Beautiful, colorful interface with panels, tables, and progress indicators
- **Type Validation**: Automatically validates inputs based on type specifications (string, number, boolean, array, object)
- **Smart Defaults**: Applies default values and allows optional parameters
- **Constraint Checking**: Validates min/max values, string lengths, patterns, and enum values

## How It Works

### 1. Input Parameter Specs

Workflows define their inputs in the `inputs` section:

```json
{
  "inputs": {
    "url": {
      "type": "string",
      "required": true,
      "description": "URL to fetch and analyze"
    },
    "max_length": {
      "type": "number",
      "required": false,
      "default": 100,
      "description": "Maximum summary length in words"
    }
  }
}
```

### 2. LLM Prompt Generation

For each input parameter, the system:

1. **Reads** the parameter name and description from the workflow spec
2. **Calls** the 1B LLM with a prompt like:
   ```
   Parameter: url
   Type: string
   Description: URL to fetch and analyze
   Required: true

   Generate a friendly prompt:
   ```
3. **Receives** a natural language question like:
   ```
   Please enter the URL you want me to analyze
   ```
4. **Displays** the question to the user and collects their input

### 3. Example Flow

#### Input Specification:
```json
{
  "url": {
    "type": "string",
    "required": true,
    "description": "URL to fetch and analyze"
  }
}
```

#### Generated Prompt:
```
Please enter the URL you want me to analyze
```

#### User Interaction:
```
┌─ Workflow Inputs Required ─────────────────┐
│  url_analyzer                              │
│  Analyze a URL and generate a report       │
└────────────────────────────────────────────┘

Please enter the URL you want me to analyze: https://example.com
```

## Usage

### Basic Usage

Run a workflow interactively:

```bash
python run_workflow.py workflows/simple_summarizer.json
```

This will:
1. Load the workflow specification
2. Prompt for each required input using LLM-generated questions
3. Execute the workflow with the collected inputs
4. Display the results

### With Pre-Provided Inputs

Skip some prompts by providing inputs via CLI:

```bash
python run_workflow.py workflows/url_analyzer.json --input '{"url": "https://example.com"}'
```

Only missing required inputs will be prompted for.

### Non-Interactive Mode

Provide all inputs without prompts:

```bash
python run_workflow.py workflows/simple_summarizer.json \
  --input '{"text": "Long article...", "max_length": 50}' \
  --no-interactive
```

### Save Results

Save execution results to a JSON file:

```bash
python run_workflow.py workflows/simple_summarizer.json \
  --output results.json
```

## Input Types

The system supports various input types with automatic validation:

### String
```json
{
  "name": {
    "type": "string",
    "required": true,
    "description": "Your name",
    "min_length": 2,
    "max_length": 50
  }
}
```

### Number
```json
{
  "age": {
    "type": "number",
    "required": true,
    "description": "Your age in years",
    "minimum": 0,
    "maximum": 150
  }
}
```

### Boolean
```json
{
  "enabled": {
    "type": "boolean",
    "required": false,
    "default": true,
    "description": "Enable feature"
  }
}
```

### Enum (Choices)
```json
{
  "format": {
    "type": "string",
    "required": true,
    "description": "Output format",
    "enum": ["json", "csv", "xml"]
  }
}
```

### Array
```json
{
  "tags": {
    "type": "array",
    "required": false,
    "description": "List of tags"
  }
}
```

### Object
```json
{
  "config": {
    "type": "object",
    "required": false,
    "description": "Configuration object"
  }
}
```

## Example Workflows

### Simple Summarizer

```bash
python run_workflow.py workflows/simple_summarizer.json
```

Prompts:
- "Please enter the text you want me to summarize"
- "How many words should the summary be? (maximum)" [default: 100]

### URL Analyzer

```bash
python run_workflow.py workflows/url_analyzer.json
```

Prompts:
- "Please enter the URL you want me to analyze"
- "What depth of analysis would you like? (basic, detailed, or comprehensive)" [default: basic]

## Architecture

### InteractiveInputCollector

The core component responsible for:

1. **Loading workflow specs** - Reads input definitions
2. **Generating prompts** - Uses gemma3:1b to create friendly questions
3. **Collecting input** - Prompts user with rich terminal UI
4. **Validating input** - Checks types, constraints, patterns
5. **Returning values** - Provides validated inputs to workflow

Located in: `code_evolver/src/interactive_input_collector.py`

### WorkflowRunner

Executes the complete workflow:

1. **Loads workflow** - Parses JSON specification
2. **Collects inputs** - Uses InteractiveInputCollector
3. **Executes steps** - Runs each workflow step in order
4. **Collects outputs** - Maps step outputs to workflow outputs
5. **Displays results** - Shows formatted results in terminal

Located in: `code_evolver/run_workflow.py`

## LLM Prompt Examples

The system uses carefully crafted prompts to generate natural questions:

**System Prompt:**
```
You are a helpful assistant that creates clear, friendly prompts
for collecting user input.

Given a parameter name and description, create a natural,
conversational question to ask the user.

Rules:
- Be concise and friendly
- Use natural language
- Don't include technical jargon unless necessary
- Make it sound like a conversation, not a form
- Keep it to one sentence if possible
```

**Example Transformations:**

| Parameter | Description | Generated Prompt |
|-----------|-------------|------------------|
| `url` | "URL to fetch and analyze" | "Please enter the URL you want me to analyze" |
| `max_length` | "Maximum summary length in words" | "How many words should the summary be? (maximum)" |
| `topic` | "Topic for blog post generation" | "What topic would you like me to write about?" |
| `api_key` | "API key for authentication" | "Please provide your API key" |

## Fallback Behavior

If the LLM fails to generate a good prompt:

1. Uses the description directly: "Please enter {description}"
2. If no description, converts parameter name: "url" → "Please enter Url"
3. Always provides a sensible fallback

## Benefits

### For Users

- **No need to remember parameter names** - Natural language questions
- **Visual feedback** - Rich terminal UI shows progress
- **Input validation** - Catches errors before execution
- **Smart defaults** - Optional parameters have sensible defaults

### For Workflow Developers

- **Just define the spec** - No need to write prompt text
- **Automatic generation** - LLM creates friendly prompts
- **Type safety** - Automatic validation based on spec
- **Consistent experience** - All workflows use the same UI

## Integration

The interactive input collector can be integrated into other tools:

```python
from src.ollama_client import OllamaClient
from src.interactive_input_collector import InteractiveInputCollector

# Initialize
client = OllamaClient()
collector = InteractiveInputCollector(client)

# Collect inputs
workflow_spec = {...}  # Load from JSON
inputs = collector.collect_inputs(workflow_spec)

# Use inputs
print(inputs)  # {'url': 'https://example.com', 'max_length': 100}
```

## Future Enhancements

Potential improvements:

- **Multi-step validation** - Validate inputs against each other
- **Conditional inputs** - Show/hide inputs based on previous answers
- **Input suggestions** - LLM suggests common values
- **History** - Remember previous inputs
- **Batch mode** - Run multiple workflows with saved input sets
- **Web UI** - Browser-based interface for remote execution

## Troubleshooting

### LLM Not Available

If gemma3:1b is not available:

```bash
ollama pull gemma3:1b
```

The system will fallback to basic prompts if LLM fails.

### Invalid Input Type

If you see validation errors, check the workflow spec:

```json
{
  "type": "number",  // Must be a number
  "minimum": 0,      // Must be >= 0
  "maximum": 100     // Must be <= 100
}
```

### Workflow Not Found

Ensure the workflow path is correct:

```bash
# Absolute path
python run_workflow.py /path/to/workflow.json

# Relative to current directory
python run_workflow.py workflows/simple_summarizer.json
```

## See Also

- [Workflow Specification](code_evolver/src/workflow_spec.py) - Complete workflow format
- [Workflow Runner Tool](code_evolver/tools/executable/workflow_runner.py) - Standalone script generation
- [Docker Workflow Builder](code_evolver/src/docker_workflow_builder.py) - Containerized workflows
