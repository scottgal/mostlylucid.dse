#!/bin/bash
# Example: Generate a sequence diagram

echo "=========================================="
echo "Sequence Diagram Example - API Flow"
echo "=========================================="
echo ""

# Build sequence diagram
echo "Building sequence diagram..."

SEQUENCE_JSON=$(cat <<'EOF'
{
  "diagram_type": "sequence",
  "title": "REST API Request Flow",
  "data": {
    "participants": [
      {"id": "client", "name": "Client App"},
      {"id": "gateway", "name": "API Gateway"},
      {"id": "auth", "name": "Auth Service"},
      {"id": "api", "name": "API Server"},
      {"id": "db", "name": "Database"}
    ],
    "messages": [
      {"from": "client", "to": "gateway", "text": "POST /api/users", "arrow": "->"},
      {"from": "gateway", "to": "auth", "text": "Validate JWT", "arrow": "->"},
      {"from": "auth", "to": "gateway", "text": "Token Valid", "arrow": "-->"},
      {"from": "gateway", "to": "api", "text": "Create User", "arrow": "->"},
      {"from": "api", "to": "db", "text": "INSERT INTO users", "arrow": "->"},
      {"from": "db", "to": "api", "text": "OK (user_id: 123)", "arrow": "-->"},
      {"from": "api", "to": "gateway", "text": "User Created", "arrow": "-->"},
      {"from": "gateway", "to": "client", "text": "201 Created", "arrow": "-->"}
    ],
    "notes": [
      {"participant": "gateway", "position": "right of", "text": "Rate limiting applied"},
      {"participant": "api", "position": "right of", "text": "Validate input data"}
    ]
  }
}
EOF
)

RESULT=$(echo "$SEQUENCE_JSON" | python code_evolver/tools/visualization/mermaid_builder.py)

if [ $? -eq 0 ]; then
    echo "✓ Sequence diagram built successfully"
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
  "theme": "neutral",
  "output_path": "/tmp/sequence_diagram.svg"
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
echo "View the diagram: xdg-open /tmp/sequence_diagram.svg"
echo ""
