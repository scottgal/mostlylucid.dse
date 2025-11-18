#!/bin/bash
# Example: Generate and render a flowchart diagram

echo "=========================================="
echo "Flowchart Example - User Authentication"
echo "=========================================="
echo ""

# Step 1: Build the diagram
echo "Step 1: Building Mermaid diagram..."
MERMAID_JSON=$(cat <<'EOF'
{
  "diagram_type": "flowchart",
  "direction": "TD",
  "title": "User Authentication Flow",
  "data": {
    "nodes": [
      {"id": "start", "label": "User Visits Site", "shape": "circle"},
      {"id": "check_auth", "label": "Check Authentication", "shape": "diamond"},
      {"id": "show_login", "label": "Show Login Page", "shape": "rectangle"},
      {"id": "validate", "label": "Validate Credentials", "shape": "diamond"},
      {"id": "grant_access", "label": "Grant Access", "shape": "rectangle"},
      {"id": "show_error", "label": "Show Error", "shape": "rectangle"},
      {"id": "dashboard", "label": "User Dashboard", "shape": "rounded"},
      {"id": "end", "label": "End", "shape": "circle"}
    ],
    "edges": [
      {"from": "start", "to": "check_auth"},
      {"from": "check_auth", "to": "dashboard", "label": "Authenticated"},
      {"from": "check_auth", "to": "show_login", "label": "Not Authenticated"},
      {"from": "show_login", "to": "validate", "label": "Submit Credentials"},
      {"from": "validate", "to": "grant_access", "label": "Valid"},
      {"from": "validate", "to": "show_error", "label": "Invalid"},
      {"from": "grant_access", "to": "dashboard"},
      {"from": "show_error", "to": "show_login"},
      {"from": "dashboard", "to": "end"}
    ],
    "styles": [
      {"id": "start", "style": "fill:#4dabf7,stroke:#1971c2,stroke-width:3px"},
      {"id": "grant_access", "style": "fill:#51cf66,stroke:#2f9e44,stroke-width:2px"},
      {"id": "show_error", "style": "fill:#ff6b6b,stroke:#c92a2a,stroke-width:2px"},
      {"id": "dashboard", "style": "fill:#ffd43b,stroke:#f59f00,stroke-width:2px"},
      {"id": "end", "style": "fill:#4dabf7,stroke:#1971c2,stroke-width:3px"}
    ]
  }
}
EOF
)

RESULT=$(echo "$MERMAID_JSON" | python code_evolver/tools/visualization/mermaid_builder.py)

if [ $? -eq 0 ]; then
    echo "✓ Diagram built successfully"
    MERMAID=$(echo "$RESULT" | jq -r '.mermaid')
    echo ""
    echo "Mermaid syntax:"
    echo "----------------------------------------"
    echo "$MERMAID"
    echo "----------------------------------------"
else
    echo "✗ Failed to build diagram"
    echo "$RESULT"
    exit 1
fi

# Step 2: Render to SVG
echo ""
echo "Step 2: Rendering to SVG..."
RENDER_JSON=$(cat <<EOF
{
  "mermaid": $(echo "$MERMAID" | jq -Rs .),
  "format": "svg",
  "theme": "default",
  "output_path": "/tmp/auth_flow.svg"
}
EOF
)

RENDER_RESULT=$(echo "$RENDER_JSON" | python code_evolver/tools/visualization/mermaid_renderer.py)

if [ $? -eq 0 ]; then
    OUTPUT_PATH=$(echo "$RENDER_RESULT" | jq -r '.output_path')
    echo "✓ Diagram rendered successfully"
    echo "  Output: $OUTPUT_PATH"
    echo "  Size: $(du -h "$OUTPUT_PATH" | cut -f1)"
else
    echo "✗ Failed to render diagram"
    echo "$RENDER_RESULT"
fi

# Step 3: Also render to PNG
echo ""
echo "Step 3: Rendering to PNG..."
RENDER_PNG_JSON=$(cat <<EOF
{
  "mermaid": $(echo "$MERMAID" | jq -Rs .),
  "format": "png",
  "theme": "forest",
  "width": 1200,
  "scale": 2,
  "background_color": "white",
  "output_path": "/tmp/auth_flow.png"
}
EOF
)

RENDER_PNG_RESULT=$(echo "$RENDER_PNG_JSON" | python code_evolver/tools/visualization/mermaid_renderer.py)

if [ $? -eq 0 ]; then
    OUTPUT_PNG=$(echo "$RENDER_PNG_RESULT" | jq -r '.output_path')
    echo "✓ PNG diagram rendered successfully"
    echo "  Output: $OUTPUT_PNG"
    echo "  Size: $(du -h "$OUTPUT_PNG" | cut -f1)"
else
    echo "⚠ PNG rendering failed (mmdc may not be installed)"
fi

echo ""
echo "=========================================="
echo "Example completed!"
echo "=========================================="
echo ""
echo "View the diagrams:"
echo "  SVG: xdg-open /tmp/auth_flow.svg"
echo "  PNG: xdg-open /tmp/auth_flow.png"
echo ""
