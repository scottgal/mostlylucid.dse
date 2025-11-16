#!/usr/bin/env python3
"""
Environment File Generator
Generates .env files with all necessary configuration for Docker containers
"""
import json
import sys
from typing import Dict, Any, List


def generate_env_file(config: Dict[str, Any]) -> str:
    """
    Generate .env file content

    Args:
        config: Configuration dictionary with:
            - tool_id: Tool/workflow ID
            - port: API port
            - llm_config: LLM configuration settings
            - additional_vars: Additional environment variables

    Returns:
        .env file content
    """
    tool_id = config.get('tool_id', 'unknown')
    port = config.get('port', 8080)
    llm_config = config.get('llm_config', {})
    additional_vars = config.get('additional_vars', {})

    env_lines = [
        "# Environment Configuration",
        f"# Generated for tool: {tool_id}",
        "# HOW TO USE: Copy to .env and edit values as needed",
        "",
        "# ======================",
        "# Application Settings",
        "# ======================",
        f"TOOL_ID={tool_id}",
        f"API_PORT={port}",
        "API_HOST=0.0.0.0",
        "PYTHONUNBUFFERED=1",
        "",
        "# ======================",
        "# Flask Settings",
        "# ======================",
        "FLASK_ENV=production",
        "FLASK_DEBUG=false",
        "",
        "# ======================",
        "# LLM Configuration",
        "# ======================",
        "# Provider: ollama (local), openai, anthropic, azure",
        f"LLM_PROVIDER={llm_config.get('provider', 'ollama')}",
        "",
        "# Model to use (for Ollama):",
        "# - tinyllama:latest (fast, lightweight, good for testing)",
        "# - llama3:latest (balanced quality/speed, recommended)",
        "# - qwen2.5-coder:3b (best for code generation)",
        f"LLM_MODEL={llm_config.get('model', 'llama3:latest')}",
        "",
        "# Ollama API base URL",
        "# Docker Mac/Windows: http://host.docker.internal:11434",
        "# Docker Linux: http://172.17.0.1:11434",
        "# Standalone: http://localhost:11434",
        f"LLM_BASE_URL={llm_config.get('base_url', 'http://localhost:11434')}",
        "",
        f"LLM_TEMPERATURE={llm_config.get('temperature', '0.7')}",
        "",
        "# API Keys (uncomment if using cloud providers)",
        "# OPENAI_API_KEY=sk-your-key-here",
        "# ANTHROPIC_API_KEY=sk-ant-your-key-here",
        "# AZURE_API_KEY=your-key-here",
        "",
        "# ======================",
        "# Vector Database",
        "# ======================",
        "VECTOR_DB_TYPE=chromadb",
        "VECTOR_DB_PATH=./rag_memory",
        "",
        "# ======================",
        "# Logging",
        "# ======================",
        "LOG_LEVEL=INFO",
        "LOG_FORMAT=%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        "",
        "# ======================",
        "# Security",
        "# ======================",
        "# IMPORTANT: Change in production!",
        "# SECRET_KEY=change-this-in-production",
        "",
        "# ======================",
        "# CORS Settings",
        "# ======================",
        "ENABLE_CORS=true",
        "# In production, set to specific domains:",
        "# CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com",
        "CORS_ORIGINS=*",
        "",
    ]

    # Add additional variables
    if additional_vars:
        env_lines.append("# Additional Configuration")
        for key, value in additional_vars.items():
            env_lines.append(f"{key}={value}")
        env_lines.append("")

    return "\n".join(env_lines)


def generate_env_example(config: Dict[str, Any]) -> str:
    """
    Generate .env.example file with documentation

    Args:
        config: Configuration dictionary

    Returns:
        .env.example file content with comments
    """
    tool_id = config.get('tool_id', 'unknown')
    port = config.get('port', 8080)

    example = f'''# Environment Configuration Example
# Copy this file to .env and configure as needed

# ======================
# Application Settings
# ======================

# Tool/Workflow ID to run
TOOL_ID={tool_id}

# API server port
API_PORT={port}

# API server host (0.0.0.0 for all interfaces)
API_HOST=0.0.0.0

# Python unbuffered output (recommended for Docker)
PYTHONUNBUFFERED=1

# ======================
# Flask Settings
# ======================

# Flask environment (development/production)
FLASK_ENV=production

# Enable Flask debug mode (true/false)
FLASK_DEBUG=false

# ======================
# LLM Configuration
# ======================

# LLM provider: ollama (local), openai, anthropic, azure
LLM_PROVIDER=ollama

# Model to use (for Ollama):
# RECOMMENDED OPTIONS:
# - tinyllama:latest       # Fast, lightweight (1.1B) - good for testing/development
# - llama3:latest          # Balanced (8B) - RECOMMENDED for production
# - qwen2.5-coder:3b       # Code specialist (3B) - best for code tasks
# - codellama:7b           # Code-focused (7B) - advanced coding
LLM_MODEL=llama3:latest

# LLM API base URL
# For Ollama on Docker (Mac/Windows): http://host.docker.internal:11434
# For Ollama on Docker (Linux): http://172.17.0.1:11434
# For Ollama standalone: http://localhost:11434
LLM_BASE_URL=http://localhost:11434

# Temperature for LLM responses (0.0-1.0)
# Lower = more focused/deterministic, Higher = more creative
LLM_TEMPERATURE=0.7

# API keys (if using cloud providers)
# OPENAI_API_KEY=your-key-here
# ANTHROPIC_API_KEY=your-key-here
# AZURE_API_KEY=your-key-here

# ======================
# Vector Database
# ======================

# Vector DB type: chromadb or qdrant
VECTOR_DB_TYPE=chromadb

# Path to vector database storage
VECTOR_DB_PATH=./rag_memory

# Qdrant settings (if using Qdrant)
# QDRANT_URL=http://localhost:6333
# QDRANT_API_KEY=your-key-here

# ======================
# Logging
# ======================

# Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL=INFO

# Log format
LOG_FORMAT=%(asctime)s - %(name)s - %(levelname)s - %(message)s

# ======================
# Security
# ======================

# Secret key for session management (CHANGE IN PRODUCTION!)
# SECRET_KEY=change-this-in-production-$(openssl rand -hex 32)

# ======================
# CORS Settings
# ======================

# Enable CORS (true/false)
ENABLE_CORS=true

# Allowed CORS origins (* for all, or comma-separated list)
CORS_ORIGINS=*

# ======================
# Performance
# ======================

# Number of worker processes
# WORKERS=4

# Request timeout in seconds
# TIMEOUT=120
'''

    return example


def generate_env_instructions(config: Dict[str, Any]) -> str:
    """Generate instructions for .env configuration"""
    tool_id = config.get('tool_id', 'unknown')

    instructions = f'''# Environment Configuration Instructions

## Quick Start

1. Copy the example file:
   ```bash
   cp .env.example .env
   ```

2. Edit .env with your settings:
   ```bash
   nano .env
   ```

3. Required settings:
   - `TOOL_ID`: Set to "{tool_id}" (already configured)
   - `API_PORT`: Port for the API server
   - `LLM_PROVIDER`: Choose your LLM provider

## LLM Provider Configuration

### Using Ollama (Default - Local)
```env
LLM_PROVIDER=ollama
LLM_MODEL=qwen2.5-coder:3b
LLM_BASE_URL=http://localhost:11434
```

Make sure Ollama is running:
```bash
ollama serve
ollama pull qwen2.5-coder:3b
```

### Using OpenAI
```env
LLM_PROVIDER=openai
LLM_MODEL=gpt-4
OPENAI_API_KEY=sk-your-api-key-here
```

### Using Anthropic
```env
LLM_PROVIDER=anthropic
LLM_MODEL=claude-3-5-sonnet-20241022
ANTHROPIC_API_KEY=your-api-key-here
```

## Vector Database Options

### ChromaDB (Default - Local)
```env
VECTOR_DB_TYPE=chromadb
VECTOR_DB_PATH=./rag_memory
```

### Qdrant (Scalable)
```env
VECTOR_DB_TYPE=qdrant
QDRANT_URL=http://localhost:6333
```

Run Qdrant with Docker:
```bash
docker run -p 6333:6333 qdrant/qdrant
```

## Security Best Practices

1. **Change the secret key** in production:
   ```bash
   SECRET_KEY=$(openssl rand -hex 32)
   ```

2. **Restrict CORS origins** in production:
   ```env
   CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
   ```

3. **Use environment-specific files**:
   - `.env.development`
   - `.env.production`
   - `.env.test`

4. **Never commit .env to git** (already in .gitignore)

## Docker Usage

The .env file is automatically loaded by docker-compose:

```bash
docker-compose up -d
```

To override settings:
```bash
docker-compose up -d -e API_PORT=9000
```

## Troubleshooting

### LLM Connection Issues
- Check `LLM_BASE_URL` is accessible
- Verify API keys are correct
- Ensure LLM service is running

### Port Conflicts
- Change `API_PORT` to an available port
- Update docker-compose.yml port mapping

### Permission Issues
- Ensure `VECTOR_DB_PATH` is writable
- Check file permissions: `chmod 755 ./rag_memory`

## Environment Variables Priority

1. System environment variables (highest)
2. .env file
3. Default values in code (lowest)

To check loaded configuration:
```bash
docker-compose config
```
'''

    return instructions


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print(json.dumps({
            'error': 'Missing configuration JSON argument'
        }))
        sys.exit(1)

    try:
        # Parse configuration
        config = json.loads(sys.argv[1])

        # Generate files
        env_content = generate_env_file(config)
        env_example = generate_env_example(config)
        instructions = generate_env_instructions(config)

        # Output result
        print(json.dumps({
            'success': True,
            'env_file': env_content,
            'env_example': env_example,
            'instructions': instructions
        }))

    except Exception as e:
        print(json.dumps({
            'error': f'Error generating environment files: {e}'
        }))
        sys.exit(1)


if __name__ == '__main__':
    main()
