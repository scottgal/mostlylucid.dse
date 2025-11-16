# Docker Packaging - Quick Start

Get started packaging tools as Docker APIs in 5 minutes.

## TL;DR

```bash
# Package a tool
/tool-compile basic_calculator ./calc-api docker

# Build and run
cd ./calc-api
chmod +x *.sh
./build.sh && ./run.sh

# Test
curl http://localhost:8080/api/health
```

## Commands

### Package Tool as Docker API
```bash
/tool-compile <tool_name> <output_dir> docker
```

### Package Tool as Standalone Exe
```bash
/tool-compile <tool_name> <output_dir> exe
```

### Natural Language
```
"Dockerize the code_review workflow"
"Make an executable of my_tool"
"Create an API for basic_calculator on port 9000"
```

## Build & Run

### Quick Method
```bash
cd <output_dir>
chmod +x *.sh
./build.sh  # Build image
./run.sh    # Run container
./test.sh   # Test API
./stop.sh   # Stop container
```

### Docker Compose Method
```bash
cd <output_dir>
docker-compose up -d      # Start
docker-compose logs -f    # View logs
docker-compose down       # Stop
```

## API Endpoints

### Health Check
```bash
curl http://localhost:8080/api/health
```

### Get Tool Info
```bash
curl http://localhost:8080/api/info
```

### Invoke Tool
```bash
curl -X POST http://localhost:8080/api/invoke \
  -H "Content-Type: application/json" \
  -d '{"prompt": "your input here"}'
```

## Configuration

Edit `.env` file:

```env
# Change port
API_PORT=9000

# Change LLM
LLM_PROVIDER=openai
OPENAI_API_KEY=your-key

# Change vector DB
VECTOR_DB_TYPE=qdrant
QDRANT_URL=http://localhost:6333
```

## Generated Files

```
output-dir/
├── Dockerfile           # Container definition
├── docker-compose.yml   # Orchestration
├── api_server.py       # Flask API
├── .env                # Configuration
├── .env.example        # Config template
├── build.sh            # Build script
├── run.sh              # Run script
├── test.sh             # Test script
├── stop.sh             # Stop script
└── README.md           # Documentation
```

## Common Issues

### Port in use
```env
# Change in .env
API_PORT=9000
```

### LLM not found
```bash
# For Ollama
ollama serve
ollama pull qwen2.5-coder:3b

# Update .env
LLM_BASE_URL=http://host.docker.internal:11434
```

### Permission denied
```bash
chmod +x *.sh
```

## Next Steps

- Read full guide: `docs/DOCKER_PACKAGING_GUIDE.md`
- Customize configuration: Edit `.env`
- Deploy to production: See guide for security tips
- Create standalone exe: Use `exe` format instead of `docker`

## Examples

### Example 1: Calculator API
```bash
/tool-compile basic_calculator ./calc-api docker
cd ./calc-api
./build.sh && ./run.sh
curl -X POST http://localhost:8080/api/invoke \
  -H "Content-Type: application/json" \
  -d '{"operation": "add", "a": 5, "b": 3"}'
```

### Example 2: Code Generator API
```bash
/tool-compile general_code_generator ./codegen-api docker
cd ./codegen-api
./build.sh && ./run.sh
curl -X POST http://localhost:8080/api/invoke \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Write a Python hello world", "temperature": 0.7}'
```

### Example 3: Standalone Exe
```bash
/tool-compile my_tool ./my-exe exe
cd ./my-exe
pip install pyinstaller
pyinstaller --onefile my_tool_standalone.py
./dist/my_tool --prompt "test"
```

---

**Full Documentation**: See `docs/DOCKER_PACKAGING_GUIDE.md`
