#!/bin/bash
# Example: Generate a tool execution flow diagram

echo "=========================================="
echo "Tool Flow Example - Build Pipeline"
echo "=========================================="
echo ""

# Build diagram showing tool execution
echo "Building tool execution flow diagram..."

TOOL_FLOW_JSON=$(cat <<'EOF'
{
  "diagram_type": "tool_flow",
  "title": "CI/CD Build Pipeline",
  "tool_calls": [
    {
      "name": "Clone Repository",
      "trigger": "Git Push",
      "result": {"success": true}
    },
    {
      "name": "Install Dependencies",
      "trigger": "npm install",
      "result": {"success": true}
    },
    {
      "name": "Run Linter",
      "trigger": "npm run lint",
      "result": {"success": true}
    },
    {
      "name": "Run Unit Tests",
      "trigger": "npm test",
      "result": {"success": true, "tests_passed": 145, "tests_failed": 0}
    },
    {
      "name": "Build Application",
      "trigger": "npm run build",
      "result": {"success": false, "error": "Type error in module auth.ts:42"}
    },
    {
      "name": "Fix Type Errors",
      "trigger": "manual fix",
      "result": {"success": true}
    },
    {
      "name": "Rebuild Application",
      "trigger": "npm run build",
      "result": {"success": true}
    },
    {
      "name": "Deploy to Staging",
      "trigger": "deploy script",
      "result": {"success": true, "url": "https://staging.example.com"}
    }
  ]
}
EOF
)

RESULT=$(echo "$TOOL_FLOW_JSON" | python code_evolver/tools/visualization/mermaid_builder.py)

if [ $? -eq 0 ]; then
    echo "✓ Tool flow diagram built successfully"
    MERMAID=$(echo "$RESULT" | jq -r '.mermaid')
    echo ""
    echo "Mermaid syntax:"
    echo "----------------------------------------"
    echo "$MERMAID"
    echo "----------------------------------------"

    # Render to SVG
    echo ""
    echo "Rendering to SVG..."
    RENDER_JSON=$(cat <<EOF
{
  "mermaid": $(echo "$MERMAID" | jq -Rs .),
  "format": "svg",
  "theme": "default",
  "output_path": "/tmp/tool_flow.svg"
}
EOF
)

    RENDER_RESULT=$(echo "$RENDER_JSON" | python code_evolver/tools/visualization/mermaid_renderer.py)

    if [ $? -eq 0 ]; then
        OUTPUT_PATH=$(echo "$RENDER_RESULT" | jq -r '.output_path')
        echo "✓ Diagram rendered successfully"
        echo "  Output: $OUTPUT_PATH"
    fi
else
    echo "✗ Failed to build diagram"
    echo "$RESULT"
    exit 1
fi

echo ""
echo "=========================================="
echo "Example completed!"
echo "=========================================="
echo ""
echo "View the diagram: xdg-open /tmp/tool_flow.svg"
echo ""
