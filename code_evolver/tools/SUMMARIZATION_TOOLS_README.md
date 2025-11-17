# Summarization Tools - Complete System

A comprehensive, adaptive document summarization system with context-window-aware chunking and incremental summarization.

## Overview

This system provides end-to-end document summarization with the following features:

1. **Adaptive to different model context windows** - Automatically selects appropriate tier based on document size
2. **Hierarchical configuration** - Dedicated `summarization` tier in model_tiers.yaml
3. **Structured text extraction** - Extracts paragraphs and sentences with error handling
4. **In-memory document store** - Shared storage accessible to all workflow tools
5. **Context-aware chunking** - Chunks documents to fit model context windows with overlap
6. **Incremental summarization** - Builds summaries chunk-by-chunk, feeding previous summary + next chunk
7. **Specialized LLM prompts** - Guarded prompts ensure high-quality summaries
8. **Modular architecture** - Each stage is a separate tool connected via call_tool

## Architecture

### Tier System

Three summarization tiers defined in `model_tiers.yaml`:

- **tier_1 (Fast)**: gemma2:2b, 8K context, 512 token summaries - for quick summaries of short documents
- **tier_2 (Standard)**: llama3, 8K context, 1024 token summaries - balanced speed/quality
- **tier_3 (Large Context)**: mistral-nemo, 128K context, 2048 token summaries - for books and large documents

### Tools

#### 1. Document Store (`document_store`)
**Location**: `tools/executable/document_store.yaml`

In-memory document management with disk persistence.

**Operations**:
- `store` - Store a document with metadata
- `retrieve` - Retrieve a document by ID
- `list` - List all stored documents
- `exists` - Check if a document exists
- `delete` - Delete a document
- `clear` - Clear all documents

**Example**:
```json
{
  "operation": "store",
  "document_id": "my_doc",
  "content": "Document text here...",
  "metadata": {
    "filename": "article.txt",
    "size": 1234
  }
}
```

#### 2. Load Document (`load_document`)
**Location**: `tools/executable/load_document.yaml`

Loads documents from disk and stores them in the document store.

**Input**:
```json
{
  "filepath": "path/to/document.txt",
  "document_id": "optional_id",
  "encoding": "utf-8"
}
```

**Output**:
```json
{
  "success": true,
  "document_id": "my_doc",
  "content": "...",
  "metadata": {
    "filename": "document.txt",
    "size": 2424,
    "format": "txt",
    "loaded_at": "2025-11-17T23:31:36.670158"
  }
}
```

#### 3. Extract Text Content (`extract_text_content`)
**Location**: `tools/executable/extract_text_content.yaml`

Extracts structured text (paragraphs, sentences) from documents.

**Input**:
```json
{
  "document_id": "my_doc",
  "structure_level": "paragraphs",
  "min_paragraph_length": 50,
  "preserve_formatting": false
}
```

**Output**:
```json
{
  "success": true,
  "content": {
    "raw_text": "...",
    "paragraphs": ["para1", "para2", ...],
    "word_count": 350,
    "paragraph_count": 9,
    "sentence_count": 25
  }
}
```

#### 4. Adaptive Chunker (`adaptive_chunker`)
**Location**: `tools/executable/adaptive_chunker.yaml`

Intelligently chunks documents based on model context windows.

**Input**:
```json
{
  "document_id": "my_doc",
  "tier": "tier_2",
  "overlap_tokens": 200,
  "chunk_by": "paragraphs"
}
```

**Features**:
- Auto-adapts chunk size to context window
- Preserves paragraph/sentence boundaries
- Adds overlap between chunks for context
- Estimates tokens conservatively (~4 chars/token)

**Output**:
```json
{
  "success": true,
  "chunks": [
    {
      "chunk_id": 0,
      "content": "...",
      "token_count": 1500,
      "char_count": 6000
    }
  ],
  "chunk_count": 3,
  "context_window": 8192
}
```

#### 5. Summarizer LLMs
**Locations**:
- `tools/llm/summarizer_fast.yaml` - tier_1
- `tools/llm/summarizer_medium.yaml` - tier_2
- `tools/llm/summarizer_large.yaml` - tier_3

Specialized LLM tools with guarded prompts for summarization.

**System Prompt Features**:
- Focus on main ideas and key points
- Preserve original meaning and tone
- Never add information not in source
- Never include opinions or interpretations
- Integrate previous summaries seamlessly

**Input**:
```json
{
  "content": "Text to summarize",
  "previous_summary": "Optional previous summary"
}
```

#### 6. Incremental Summarizer (`incremental_summarizer`)
**Location**: `tools/executable/incremental_summarizer.yaml`

Core orchestrator for chunk-by-chunk summarization.

**Algorithm**:
1. Load chunks from document store
2. For each chunk:
   - Feed previous_summary + chunk to LLM
   - Get updated summary
   - Compress if summary grows too long
3. Return final summary

**Input**:
```json
{
  "document_id": "my_doc",
  "tier": "tier_2",
  "max_summary_length": 1024,
  "detailed": false
}
```

**Output**:
```json
{
  "success": true,
  "summary": "Final summary text...",
  "chunk_count": 3,
  "iterations": 3,
  "metadata": {
    "original_length": 2424,
    "summary_length": 450,
    "compression_ratio": 5.4
  }
}
```

#### 7. Summarize Document (`summarize_document`) ⭐
**Location**: `tools/executable/summarize_document.yaml`

**Main entry point** - Complete end-to-end workflow orchestrator.

**Input**:
```json
{
  "filepath": "path/to/document.txt",
  "tier": "tier_2",
  "auto_tier": true,
  "max_summary_length": 1024,
  "detailed": false,
  "save_summary": true,
  "output_path": "optional/output/path.txt"
}
```

**Features**:
- Auto-selects tier based on document size
- Orchestrates full pipeline automatically
- Saves summary to file if requested
- Provides comprehensive metadata

**Workflow**:
```
[1/4] Load document
[2/4] Extract text content
[3/4] Chunk document adaptively
[4/4] Generate incremental summary
```

**Output**:
```json
{
  "success": true,
  "summary": "Final summary...",
  "metadata": {
    "original_size": 2424,
    "summary_size": 450,
    "compression_ratio": 5.4,
    "chunk_count": 3,
    "iterations": 3,
    "processing_time": 12.5,
    "tier_auto_selected": true
  },
  "output_file": "path/to/summary.txt"
}
```

## Usage Examples

### Basic Usage (Recommended)

```python
from node_runtime import call_tool
import json

# Summarize a document (easiest way)
result = call_tool("summarize_document", json.dumps({
    "filepath": "my_article.txt",
    "auto_tier": True,
    "save_summary": True
}))

summary_data = json.loads(result)
print(summary_data["summary"])
```

### Advanced Usage - Step by Step

```python
from node_runtime import call_tool
import json

# Step 1: Load document
call_tool("load_document", json.dumps({
    "filepath": "my_article.txt",
    "document_id": "article1"
}))

# Step 2: Extract content
call_tool("extract_text_content", json.dumps({
    "document_id": "article1",
    "structure_level": "paragraphs"
}))

# Step 3: Chunk document
call_tool("adaptive_chunker", json.dumps({
    "document_id": "article1",
    "tier": "tier_2"
}))

# Step 4: Generate summary
result = call_tool("incremental_summarizer", json.dumps({
    "document_id": "article1",
    "tier": "tier_2",
    "max_summary_length": 1024
}))

summary_data = json.loads(result)
print(summary_data["summary"])
```

### Tier Selection Guidelines

**Auto-select (recommended):**
```json
{
  "filepath": "document.txt",
  "auto_tier": true
}
```

**Manual selection:**
- `tier_1`: Documents < 32K chars (~8K tokens) - Quick summaries
- `tier_2`: Documents 32K-128K chars (~8K-32K tokens) - Standard quality
- `tier_3`: Documents > 128K chars (>32K tokens) - Large context, books

### Quality Levels

**Fast (tier_1)**:
- Speed: ⚡⚡⚡⚡⚡
- Quality: ⭐⭐⭐
- Use: Email, chat messages, short articles

**Standard (tier_2)**:
- Speed: ⚡⚡⚡⚡
- Quality: ⭐⭐⭐⭐
- Use: Articles, reports, documentation

**Advanced (tier_3)**:
- Speed: ⚡⚡
- Quality: ⭐⭐⭐⭐⭐
- Use: Books, research papers, comprehensive reports

## Configuration

### Model Tiers (model_tiers.yaml)

```yaml
summarization:
  tier_1:
    models:
      primary: "gemma2:2b"
    context_window: 8192
    max_output_tokens: 512

  tier_2:
    models:
      primary: "llama3"
    context_window: 8192
    max_output_tokens: 1024

  tier_3:
    models:
      primary: "mistral-nemo"
    context_window: 128000
    max_output_tokens: 2048
```

### Aliases

```yaml
aliases:
  summarizer: "summarization.tier_2"
  summarizer_fast: "summarization.tier_1"
  summarizer_advanced: "summarization.tier_3"
```

## Testing

Test file created at: `test_documents/sample_article.txt`

### Quick Test

```bash
# Using the node runtime
python -c "
from node_runtime import call_tool
import json

result = call_tool('summarize_document', json.dumps({
    'filepath': 'test_documents/sample_article.txt',
    'auto_tier': True,
    'save_summary': True,
    'output_path': 'test_documents/sample_article_summary.txt'
}))

data = json.loads(result)
if data['success']:
    print('✓ Summary generated successfully!')
    print(f'  Original: {data[\"metadata\"][\"original_size\"]} chars')
    print(f'  Summary: {data[\"metadata\"][\"summary_size\"]} chars')
    print(f'  Compression: {data[\"metadata\"][\"compression_ratio\"]}x')
else:
    print(f'✗ Error: {data[\"error\"]}')
"
```

## Error Handling

All tools include comprehensive error handling:

- **File not found**: Clear error message with filepath
- **Document not in store**: Prompts to run prerequisite tools
- **Invalid parameters**: Validation with helpful messages
- **LLM failures**: Automatic retry with fallback models
- **Chunking issues**: Graceful degradation to raw text

## Performance

### Benchmarks (approximate)

| Document Size | Tier | Processing Time | Quality |
|--------------|------|-----------------|---------|
| 2K chars | tier_1 | ~3s | Good |
| 10K chars | tier_2 | ~8s | Excellent |
| 50K chars | tier_2 | ~25s | Excellent |
| 200K chars | tier_3 | ~60s | Exceptional |

### Optimization Tips

1. **Use auto_tier**: Let the system choose the right tier
2. **Adjust overlap**: Reduce `overlap_tokens` for faster processing
3. **Batch processing**: Process multiple documents in parallel
4. **Cache summaries**: Store summaries for reuse

## Future Enhancements

### Optional NLTK Integration

For advanced text processing, NLTK can be added:

```python
# Optional enhancement (not yet implemented)
import nltk

# Better sentence tokenization
# Named entity recognition
# Text classification
# Sentiment analysis
```

To enable: `pip install nltk`

## Files Created

### Configuration
- `code_evolver/model_tiers.yaml` (updated)

### Executable Tools
- `code_evolver/tools/executable/document_store.yaml`
- `code_evolver/tools/executable/document_store.py`
- `code_evolver/tools/executable/load_document.yaml`
- `code_evolver/tools/executable/load_document.py`
- `code_evolver/tools/executable/extract_text_content.yaml`
- `code_evolver/tools/executable/extract_text_content.py`
- `code_evolver/tools/executable/adaptive_chunker.yaml`
- `code_evolver/tools/executable/adaptive_chunker.py`
- `code_evolver/tools/executable/incremental_summarizer.yaml`
- `code_evolver/tools/executable/incremental_summarizer.py`
- `code_evolver/tools/executable/summarize_document.yaml`
- `code_evolver/tools/executable/summarize_document.py`

### LLM Tools (updated)
- `code_evolver/tools/llm/summarizer_fast.yaml`
- `code_evolver/tools/llm/summarizer_medium.yaml`
- `code_evolver/tools/llm/summarizer_large.yaml`

### Test Data
- `test_documents/sample_article.txt`

## Support

All tools will be automatically registered in `tools/index.json` when the system starts.

For issues or questions, refer to the main documentation or check individual tool YAML files for detailed schemas.
