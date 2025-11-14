# Qdrant Integration Fixes

## Issues Found and Fixed

### 1. **Not Using Qdrant When Configured** ✅ FIXED

**Problem:** The system had `QdrantRAGMemory` implementation but wasn't using it even when `use_qdrant: true` was set in config.

**Root Cause:** `chat_cli.py` was hardcoded to always use `RAGMemory` (NumPy-based) instead of checking the configuration.

**Fix:**
- Created `create_rag_memory()` factory function in `src/__init__.py`
- Factory checks `config.use_qdrant` and returns appropriate implementation
- Updated `chat_cli.py` to use the factory function
- Added visual feedback when Qdrant is enabled

**Files Changed:**
- `src/__init__.py` - Added factory function
- `chat_cli.py` - Uses factory instead of direct instantiation

### 2. **Wrong Default Vector Size** ✅ FIXED

**Problem:** `QdrantRAGMemory` defaulted to 4096 dimensions (llama3) but config specifies `nomic-embed-text` which produces 768-dimensional vectors.

**Impact:** This mismatch would cause errors when storing/searching vectors in Qdrant.

**Fix:** Changed default vector size from 4096 to 768 to match nomic-embed-text.

**File Changed:**
- `src/qdrant_rag_memory.py:47` - Updated default from 4096 to 768

### 3. **Missing ConfigManager Integration** ✅ FIXED

**Problem:** No centralized way to create RAG memory with proper configuration.

**Fix:** Created factory function that:
- Reads `use_qdrant` from config
- Passes correct embedding model
- Handles missing qdrant-client gracefully
- Uses configured vector size

### 4. **Qdrant URL Confirmation** ✅ VERIFIED

**Status:** User confirmed Qdrant is running on `http://localhost:6333`

**Configuration:** Already correctly set in `config.yaml`

## How It Works Now

### Automatic Selection

```python
from src import create_rag_memory, ConfigManager, OllamaClient

config = ConfigManager("config.yaml")
client = OllamaClient(config.ollama_url, config_manager=config)

# Automatically uses Qdrant if config.use_qdrant = true
rag = create_rag_memory(config, client)
```

### Configuration

```yaml
rag_memory:
  path: "./rag_memory"
  use_qdrant: true  # Set to true to enable Qdrant
  qdrant_url: "http://localhost:6333"
  collection_name: "code_evolver_artifacts"

ollama:
  embedding:
    model: "nomic-embed-text"
    vector_size: 768  # Must match embedding model dimensions
```

### Vector Size by Model

| Model | Dimensions | Use For |
|-------|------------|---------|
| `nomic-embed-text` | 768 | **Recommended** - Fast, efficient |
| `llama3` | 4096 | High quality, slower |
| `codellama` | 4096 | Code-specific embeddings |

## Testing

### Test NumPy-based RAG (Default)

```yaml
rag_memory:
  use_qdrant: false
```

```bash
python chat_cli.py
# Should show: "✓ Indexed 0 tools in RAG memory"
```

### Test Qdrant-based RAG

**1. Start Qdrant:**
```bash
docker run -p 6333:6333 qdrant/qdrant
```

**2. Enable in config:**
```yaml
rag_memory:
  use_qdrant: true
  qdrant_url: "http://localhost:6333"
```

**3. Run:**
```bash
python chat_cli.py
# Should show: "✓ Using Qdrant for RAG memory"
```

### Verify Qdrant Integration

```python
from src import create_rag_memory, ConfigManager, OllamaClient
from src.rag_memory import ArtifactType

config = ConfigManager("config.yaml")
client = OllamaClient(config.ollama_url, config_manager=config)
rag = create_rag_memory(config, client)

# Store an artifact
rag.store_artifact(
    artifact_id="test_001",
    artifact_type=ArtifactType.FUNCTION,
    name="Test Function",
    description="A test function for validation",
    content="def test(): pass",
    tags=["test", "validation"],
    auto_embed=True
)

# Search semantically
results = rag.find_similar(
    query="testing and validation functions",
    artifact_type=ArtifactType.FUNCTION,
    top_k=5
)

for artifact, similarity in results:
    print(f"{artifact.name}: {similarity:.2f}")

# Check statistics
stats = rag.get_statistics()
print(f"Total artifacts: {stats['total_artifacts']}")
print(f"Vectors in Qdrant: {stats.get('vectors_in_qdrant', 'N/A')}")
```

## Benefits of Qdrant Integration

### Performance
- **Scalable**: Handle millions of embeddings
- **Fast Search**: Optimized vector similarity search
- **Filtering**: Efficient metadata filtering

### Production Ready
- **Persistent**: Data survives restarts
- **Distributed**: Can run on separate server
- **Battle-tested**: Used in production systems

### Features
- **Real-time Updates**: No rebuild required
- **Multiple Collections**: Organize by project/domain
- **Quality Tracking**: Update scores without re-embedding

## Migration Path

### From NumPy to Qdrant

**1. Export existing artifacts:**
```python
from src import RAGMemory

old_rag = RAGMemory(memory_path="./rag_memory")
artifacts = old_rag.list_all()

# Save to JSON for migration
import json
with open("artifacts_export.json", "w") as f:
    json.dump([a.to_dict() for a in artifacts], f)
```

**2. Import to Qdrant:**
```python
from src import QdrantRAGMemory, Artifact
import json

new_rag = QdrantRAGMemory(
    qdrant_url="http://localhost:6333",
    vector_size=768
)

with open("artifacts_export.json", "r") as f:
    artifacts_data = json.load(f)

for artifact_data in artifacts_data:
    artifact = Artifact.from_dict(artifact_data)
    new_rag.store_artifact(
        artifact_id=artifact.artifact_id,
        artifact_type=artifact.artifact_type,
        name=artifact.name,
        description=artifact.description,
        content=artifact.content,
        tags=artifact.tags,
        auto_embed=True  # Re-generate embeddings
    )
```

## Troubleshooting

### Issue: "qdrant-client not installed"

**Solution:**
```bash
pip install qdrant-client>=1.7.0
```

### Issue: "Cannot connect to Qdrant"

**Check Qdrant is running:**
```bash
curl http://localhost:6333/collections
```

**Start Qdrant:**
```bash
# Using Docker
docker run -p 6333:6333 qdrant/qdrant

# Or download standalone from https://qdrant.tech
```

### Issue: "Embedding size mismatch"

**Symptoms:** Errors when storing vectors

**Fix:** Ensure `vector_size` in config matches your embedding model:
```yaml
ollama:
  embedding:
    model: "nomic-embed-text"
    vector_size: 768  # Must match model output
```

### Issue: "No results from semantic search"

**Check:**
1. Embeddings are being generated (auto_embed=True)
2. Ollama embedding model is available
3. Similarity threshold not too high (try min_similarity=0.3)

**Debug:**
```python
# Check if embedding generation works
embedding = rag._generate_embedding("test query")
print(f"Embedding length: {len(embedding) if embedding else 'None'}")

# Check collection exists
from qdrant_client import QdrantClient
client = QdrantClient(url="http://localhost:6333")
collections = client.get_collections()
print(f"Collections: {collections}")
```

## Summary

All Qdrant integration issues have been fixed:

✅ Factory function automatically selects implementation
✅ Correct vector dimensions (768 for nomic-embed-text)
✅ Proper configuration integration
✅ Graceful fallback when Qdrant unavailable
✅ Visual feedback for active backend
✅ Tested and working

The system now properly uses Qdrant when configured, with automatic fallback to NumPy-based storage if Qdrant is unavailable.
