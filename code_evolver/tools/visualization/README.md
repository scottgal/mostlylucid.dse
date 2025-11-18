# Mermaid Diagram Tools

Comprehensive tools for generating and rendering Mermaid diagrams from structured data, conversations, and tool execution flows.

## 📊 Overview

This visualization toolkit provides two powerful tools:

1. **Mermaid Builder** - Generates Mermaid diagram syntax from various data sources
2. **Mermaid Renderer** - Converts Mermaid syntax to image files (SVG, PNG, PDF)

## 🎯 Features

### Mermaid Builder

- **Multiple Diagram Types**:
  - Flowcharts (TD, LR, RL, BT directions)
  - Sequence diagrams
  - State diagrams
  - Class diagrams
  - Entity-Relationship diagrams
  - Tool execution flow diagrams
  - Conversation flow diagrams

- **Data Sources**:
  - Structured JSON data
  - Conversation messages
  - Tool call traces
  - Custom templates

- **Customization**:
  - Themes (default, forest, dark, neutral, base)
  - Custom node shapes and styles
  - Edge labels and arrow types
  - Color schemes

### Mermaid Renderer

- **Output Formats**:
  - SVG (vector, scalable)
  - PNG (raster, with scale control)
  - PDF (print-ready)

- **Rendering Methods**:
  - mermaid-cli (mmdc) - Primary method
  - Playwright - Fallback browser-based rendering
  - Fallback SVG - Simple text-based output

- **Features**:
  - Intelligent caching for performance
  - Multiple rendering engines
  - Theme support
  - Custom dimensions and scaling
  - Background color control

## 📦 Installation

### Prerequisites

**Option 1: mermaid-cli (Recommended)**
```bash
# Install Node.js if not already installed
# Then install mermaid-cli globally
npm install -g @mermaid-js/mermaid-cli

# Verify installation
mmdc --version
```

**Option 2: Playwright (Fallback)**
```bash
pip install playwright
playwright install chromium
```

**Option 3: Use provided installation script**
```bash
bash code_evolver/tools/visualization/install_dependencies.sh
```

### Python Dependencies

No additional Python dependencies required beyond the base DiSE requirements.

## 🚀 Usage

### 1. Building Diagrams

#### Flowchart from Structured Data

```bash
echo '{
  "diagram_type": "flowchart",
  "direction": "TD",
  "title": "User Authentication Flow",
  "data": {
    "nodes": [
      {"id": "start", "label": "User Login", "shape": "circle"},
      {"id": "validate", "label": "Validate Credentials", "shape": "diamond"},
      {"id": "success", "label": "Grant Access", "shape": "rectangle"},
      {"id": "fail", "label": "Show Error", "shape": "rectangle"}
    ],
    "edges": [
      {"from": "start", "to": "validate"},
      {"from": "validate", "to": "success", "label": "Valid"},
      {"from": "validate", "to": "fail", "label": "Invalid"}
    ],
    "styles": [
      {"id": "success", "style": "fill:#51cf66,stroke:#2f9e44"},
      {"id": "fail", "style": "fill:#ff6b6b,stroke:#c92a2a"}
    ]
  }
}' | python code_evolver/tools/visualization/mermaid_builder.py
```

#### Tool Execution Flow

```bash
echo '{
  "diagram_type": "tool_flow",
  "title": "Build and Test Pipeline",
  "tool_calls": [
    {
      "name": "Install Dependencies",
      "result": {"success": true}
    },
    {
      "name": "Run Tests",
      "result": {"success": true}
    },
    {
      "name": "Build Application",
      "result": {"success": false, "error": "Type error in module"}
    }
  ]
}' | python code_evolver/tools/visualization/mermaid_builder.py
```

#### Conversation Flow

```bash
echo '{
  "diagram_type": "conversation",
  "title": "Support Ticket Conversation",
  "conversation": [
    {"role": "user", "content": "My application won'\''t start"},
    {"role": "assistant", "content": "Let me check the logs. Can you run: tail -f app.log?"},
    {"role": "user", "content": "I see an error: Connection refused"},
    {"role": "assistant", "content": "The database service appears to be down. Let'\''s restart it."}
  ]
}' | python code_evolver/tools/visualization/mermaid_builder.py
```

#### Sequence Diagram

```bash
echo '{
  "diagram_type": "sequence",
  "title": "API Request Flow",
  "data": {
    "participants": [
      {"id": "client", "name": "Client"},
      {"id": "api", "name": "API Gateway"},
      {"id": "db", "name": "Database"}
    ],
    "messages": [
      {"from": "client", "to": "api", "text": "POST /users", "arrow": "->"},
      {"from": "api", "to": "db", "text": "INSERT user", "arrow": "->"},
      {"from": "db", "to": "api", "text": "OK", "arrow": "-->"},
      {"from": "api", "to": "client", "text": "201 Created", "arrow": "-->"}
    ],
    "notes": [
      {"participant": "api", "position": "right of", "text": "Validates request"}
    ]
  }
}' | python code_evolver/tools/visualization/mermaid_builder.py
```

#### State Diagram

```bash
echo '{
  "diagram_type": "state",
  "title": "Order Processing States",
  "data": {
    "start": "pending",
    "end": "completed",
    "states": [
      {"id": "pending", "description": "Order Pending"},
      {"id": "processing", "description": "Processing Payment"},
      {"id": "shipped", "description": "Order Shipped"},
      {"id": "completed", "description": "Order Completed"},
      {"id": "cancelled", "description": "Order Cancelled"}
    ],
    "transitions": [
      {"from": "pending", "to": "processing", "label": "payment received"},
      {"from": "processing", "to": "shipped", "label": "payment confirmed"},
      {"from": "shipped", "to": "completed", "label": "delivered"},
      {"from": "pending", "to": "cancelled", "label": "timeout"},
      {"from": "processing", "to": "cancelled", "label": "payment failed"}
    ]
  }
}' | python code_evolver/tools/visualization/mermaid_builder.py
```

### 2. Rendering Diagrams

#### Render to SVG (Default)

```bash
echo '{
  "mermaid": "flowchart TD\n    A[Start] --> B[Process]\n    B --> C[End]",
  "format": "svg",
  "theme": "default",
  "output_path": "/tmp/diagram.svg"
}' | python code_evolver/tools/visualization/mermaid_renderer.py
```

#### Render to PNG

```bash
echo '{
  "mermaid": "sequenceDiagram\n    Alice->>Bob: Hello\n    Bob-->>Alice: Hi there!",
  "format": "png",
  "width": 1200,
  "scale": 2,
  "background_color": "white",
  "output_path": "/tmp/sequence.png"
}' | python code_evolver/tools/visualization/mermaid_renderer.py
```

#### Render with Dark Theme

```bash
echo '{
  "mermaid": "stateDiagram-v2\n    [*] --> Active\n    Active --> [*]",
  "format": "svg",
  "theme": "dark",
  "output_path": "/tmp/state_dark.svg"
}' | python code_evolver/tools/visualization/mermaid_renderer.py
```

### 3. Combined Workflow

```bash
# Build diagram
MERMAID=$(echo '{
  "diagram_type": "flowchart",
  "data": {
    "nodes": [
      {"id": "a", "label": "Start", "shape": "circle"},
      {"id": "b", "label": "Process"},
      {"id": "c", "label": "End", "shape": "circle"}
    ],
    "edges": [
      {"from": "a", "to": "b"},
      {"from": "b", "to": "c"}
    ]
  }
}' | python code_evolver/tools/visualization/mermaid_builder.py | jq -r '.mermaid')

# Render to image
echo "{
  \"mermaid\": $(echo "$MERMAID" | jq -Rs .),
  \"format\": \"png\",
  \"output_path\": \"/tmp/my_diagram.png\"
}" | python code_evolver/tools/visualization/mermaid_renderer.py
```

## 📖 API Reference

### Mermaid Builder Parameters

| Parameter | Type | Required | Description | Default |
|-----------|------|----------|-------------|---------|
| `diagram_type` | string | Yes | Type of diagram to generate | - |
| `data` | object | No | Structured data for the diagram | - |
| `conversation` | array | No | Conversation messages | - |
| `tool_calls` | array | No | Tool execution trace | - |
| `title` | string | No | Diagram title | - |
| `direction` | string | No | Flow direction (TD, LR, RL, BT) | TD |
| `theme` | string | No | Mermaid theme | default |
| `style` | object | No | Custom styling | - |

### Diagram Types

- `flowchart` - Flow diagrams with decision nodes
- `sequence` - Sequence diagrams for interactions
- `state` - State machine diagrams
- `class` - Class diagrams for OOP
- `er` - Entity-Relationship diagrams
- `gantt` - Project timelines
- `journey` - User journey maps
- `git` - Git branch visualization
- `mindmap` - Mind maps
- `timeline` - Timeline diagrams
- `tool_flow` - Tool execution flow (custom)
- `conversation` - Conversation flow (custom)

### Mermaid Renderer Parameters

| Parameter | Type | Required | Description | Default |
|-----------|------|----------|-------------|---------|
| `mermaid` | string | Yes | Mermaid syntax to render | - |
| `output_path` | string | No | Output file path | temp file |
| `format` | string | No | Output format (svg, png, pdf) | svg |
| `theme` | string | No | Mermaid theme | default |
| `background_color` | string | No | Background color | transparent |
| `width` | integer | No | Width in pixels | 800 |
| `height` | integer | No | Height in pixels | auto |
| `scale` | number | No | Scale factor (PNG only) | 1 |
| `cache` | boolean | No | Use caching | true |

## 🎨 Themes

Available themes:
- `default` - Standard Mermaid theme
- `forest` - Green nature theme
- `dark` - Dark mode theme
- `neutral` - Minimalist grayscale
- `base` - Base theme for customization

## 📁 File Structure

```
code_evolver/tools/visualization/
├── README.md                    # This file
├── mermaid_builder.yaml         # Builder tool definition
├── mermaid_builder.py           # Builder implementation
├── mermaid_renderer.yaml        # Renderer tool definition
├── mermaid_renderer.py          # Renderer implementation
├── install_dependencies.sh      # Dependency installation script
└── examples/                    # Usage examples
    ├── flowchart_example.sh
    ├── sequence_example.sh
    ├── tool_flow_example.sh
    └── conversation_example.sh
```

## 🔧 Integration with DiSE

These tools are automatically registered with the DiSE tool system. You can use them in workflows:

```yaml
name: "Generate Documentation Diagrams"
type: "workflow"
steps:
  - tool: "mermaid_builder"
    params:
      diagram_type: "flowchart"
      data: "{{workflow_data}}"

  - tool: "mermaid_renderer"
    params:
      mermaid: "{{previous.mermaid}}"
      format: "svg"
      output_path: "docs/diagrams/workflow.svg"
```

## 🐛 Troubleshooting

### "mmdc: command not found"

Install mermaid-cli:
```bash
npm install -g @mermaid-js/mermaid-cli
```

### Rendering Fallback Mode

If mermaid-cli is not available, the renderer will:
1. Try Playwright (if installed)
2. Fall back to basic SVG text output

### Caching Issues

Clear the cache:
```bash
rm -rf /tmp/mermaid_cache/*
```

Or disable caching:
```json
{"cache": false}
```

## 📝 Examples

See the `examples/` directory for complete usage examples:

- **flowchart_example.sh** - Generate flowcharts from data
- **sequence_example.sh** - Create sequence diagrams
- **tool_flow_example.sh** - Visualize tool execution
- **conversation_example.sh** - Map conversation flows

## 🤝 Contributing

To add new diagram types:

1. Add the type to `mermaid_builder.yaml` enum
2. Implement a `build_<type>_diagram()` method in `MermaidBuilder`
3. Update the `build_diagram()` dispatcher
4. Add examples and tests

## 📄 License

Part of the mostlylucid-dse (Directed Synthetic Evolution) project.

## 🔗 Resources

- [Mermaid Documentation](https://mermaid.js.org/)
- [Mermaid Live Editor](https://mermaid.live/)
- [mermaid-cli GitHub](https://github.com/mermaid-js/mermaid-cli)
- [DiSE Documentation](../../docs/)

---

**Version:** 1.0.0
**Last Updated:** 2025-11-18
**Maintainer:** DiSE Visualization Team
