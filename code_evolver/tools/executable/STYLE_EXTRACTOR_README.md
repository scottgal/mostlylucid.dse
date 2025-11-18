# Style Extractor Tool

A comprehensive style analysis tool that extracts detailed style information from any source (web pages, files, text) and outputs structured JSON profiles. Similar to Google's [langextract](https://github.com/google/langextract) but focused on style analysis rather than language detection.

## Features

- **Multi-source extraction**: Analyze content from URLs, files, or direct text
- **Tiered analysis**: Choose between quick, detailed, or comprehensive analysis
- **12 style aspects**: Tone, formality, vocabulary, sentence structure, paragraph structure, formatting, punctuation, rhetorical devices, voice, pacing, imagery, and technical level
- **Configurable guardrails**: Write operations restricted to tool-scoped directory
- **RAG integration**: Optionally store extracted styles for similarity search
- **File format support**: Output as JSON or YAML

## Installation

Required dependencies:
```bash
pip install requests beautifulsoup4 pyyaml
```

## Usage

### Basic Usage

Extract style from text:
```json
{
  "source_type": "text",
  "source": "Your text content here...",
  "extraction_tier": "detailed"
}
```

Extract from a file:
```json
{
  "source_type": "file",
  "source": "/path/to/document.txt",
  "extraction_tier": "comprehensive",
  "save_to_file": true,
  "filename": "document_style.json"
}
```

Extract from a URL:
```json
{
  "source_type": "url",
  "source": "https://example.com/article",
  "extraction_tier": "detailed"
}
```

### Extraction Tiers

| Tier | Speed | Cost | Quality | Method | LLM Required |
|------|-------|------|---------|--------|--------------|
| **quick** | Very Fast | Free | Good (70%) | Rule-based | No |
| **detailed** | Fast | Low | Excellent (85%) | LLM-assisted | Yes |
| **comprehensive** | Medium | Medium | Exceptional (95%) | Multi-pass LLM | Yes |

### Style Aspects

You can analyze specific aspects or all aspects (default):

- **tone**: Sentiment, emotional intensity, confidence
- **formality**: Formal vs informal indicators
- **vocabulary**: Word diversity, complexity, common terms
- **sentence_structure**: Length, variety, complexity
- **paragraph_structure**: Organization, consistency
- **formatting**: Headings, lists, emphasis
- **punctuation**: Usage patterns
- **rhetorical_devices**: Questions, metaphors, repetition
- **voice**: Active/passive, person (1st, 2nd, 3rd)
- **pacing**: Rhythm, variation
- **imagery**: Sensory language, descriptive richness
- **technical_level**: Jargon, complexity

Example with specific aspects:
```json
{
  "source_type": "text",
  "source": "Sample text...",
  "extraction_tier": "quick",
  "style_aspects": ["tone", "formality", "vocabulary"]
}
```

## Output Format

```json
{
  "success": true,
  "source_type": "text",
  "source": "[381 chars]",
  "extraction_tier": "detailed",
  "style_profile": {
    "tone": {
      "sentiment": "positive|neutral|negative",
      "emotional_intensity": "low|medium|high",
      "confidence": 0.85,
      "indicators": { ... }
    },
    "formality": {
      "level": "very informal|informal|neutral|formal|very formal",
      "score": 0.67,
      "indicators": { ... }
    },
    "vocabulary": {
      "word_count": 49,
      "unique_words": 44,
      "lexical_diversity": 0.898,
      "complexity_level": "low|medium|high",
      "top_words": [ ... ]
    },
    // ... other aspects
  },
  "metadata": {
    "content_length": 381,
    "word_count": 49,
    "sentence_count": 5,
    "paragraph_count": 1,
    "extraction_time_ms": 0.47,
    "timestamp": "2025-11-18T12:04:50.593522Z",
    "tier_used": "detailed"
  }
}
```

## Configuration

Configuration is managed in `config.yaml`:

```yaml
style_extractor:
  enabled: true
  # Write guardrails - files only written to tool-scoped directory
  write_guardrails:
    fixed_directory: "./data/filesystem/style_extractor/"
    allowed_extensions: [".json", ".yaml", ".yml", ".txt"]
    max_file_size_mb: 10
    max_files: 1000

  # Default settings
  defaults:
    extraction_tier: "detailed"
    max_content_length: 50000
    save_to_rag: true

  # File reading settings
  file:
    max_file_size_mb: 50
    allowed_extensions: [".txt", ".md", ".html", ".xml", ...]
```

## Security & Guardrails

### Read Guardrails
- File size limits (default: 50MB)
- Extension whitelist for reading
- Encoding handling (UTF-8 with error tolerance)

### Write Guardrails
- **Fixed directory**: All output files written to `./data/filesystem/style_extractor/`
- **Extension whitelist**: Only `.json`, `.yaml`, `.yml`, `.txt` allowed
- **Size limits**: Max 10MB per file, 1000 files total
- **Path traversal protection**: Cannot escape tool-scoped directory

## Use Cases

### 1. Content Analysis
Extract and compare writing styles across different authors or documents:
```bash
echo '{"source_type": "file", "source": "author1.txt", "save_to_file": true}' | \
  python style_extractor.py
```

### 2. Style Transfer Preparation
Analyze target style before applying style transfer:
```bash
echo '{"source_type": "url", "source": "https://blog.example.com",
       "extraction_tier": "comprehensive", "save_to_file": true}' | \
  python style_extractor.py
```

### 3. Writing Assessment
Evaluate formality and tone of writing:
```bash
echo '{"source_type": "text", "source": "Your essay...",
       "style_aspects": ["formality", "tone", "technical_level"]}' | \
  python style_extractor.py
```

### 4. Corpus Analysis
Build a dataset of style profiles for machine learning:
```bash
for file in corpus/*.txt; do
  echo "{\"source_type\": \"file\", \"source\": \"$file\",
        \"save_to_file\": true, \"filename\": \"$(basename $file .txt)_style.json\"}" | \
    python style_extractor.py
done
```

## Evaluation

The `style_extraction_evaluator` tool can assess the quality of extractions:

```json
{
  "extraction_result": { /* style extraction output */ },
  "tier": "detailed"
}
```

Evaluation scores:
- **completeness**: Coverage of requested aspects
- **accuracy**: Correctness of conclusions
- **depth**: Quality of insights
- **consistency**: Internal coherence
- **usefulness**: Actionability

## Limitations

1. **Rule-based tiers**: Quick and detailed tiers use heuristics that may not capture nuanced style
2. **English focus**: Primarily tuned for English text analysis
3. **Context window**: Very long documents are truncated (configurable)
4. **Web content**: HTML extraction quality depends on page structure

## Performance

Typical extraction times (Core i7, 16GB RAM):

| Tier | 1KB text | 10KB text | 100KB text |
|------|----------|-----------|------------|
| quick | 0.5ms | 2ms | 15ms |
| detailed | 50ms | 200ms | 1s |
| comprehensive | 200ms | 800ms | 5s |

## API Reference

### Command-line Interface

```bash
python style_extractor.py < input.json > output.json
```

### Input Schema

```typescript
{
  source_type: "url" | "file" | "text"
  source: string
  extraction_tier?: "quick" | "detailed" | "comprehensive"
  style_aspects?: string[]
  output_format?: "json" | "yaml"
  save_to_file?: boolean
  filename?: string
  include_metadata?: boolean
  max_content_length?: number
}
```

### Output Schema

```typescript
{
  success: boolean
  source_type: string
  source: string
  extraction_tier: string
  style_profile: {
    [aspect: string]: {
      // Aspect-specific metrics and analysis
    }
  }
  metadata: {
    content_length: number
    word_count: number
    sentence_count: number
    paragraph_count: number
    extraction_time_ms: number
    timestamp: string
    tier_used: string
  }
  saved_file?: string
  message: string
  error?: string
}
```

## Integration with Other Tools

### RAG Memory
Extracted styles can be stored in RAG for similarity search:
```python
from rag_memory import RAGMemory

rag = RAGMemory()
rag.add_artifact(
    content=json.dumps(style_profile),
    metadata={"source": "document.txt", "tier": "detailed"}
)
```

### Filesystem Manager
Files are automatically scoped to `style_extractor/`:
```python
from filesystem_manager import FilesystemManager

fm = FilesystemManager()
result = fm.read(scope="style_extractor", path="extracted_style.json")
```

## Troubleshooting

### Error: "File not found"
Ensure the file path is correct and accessible. Use absolute paths if needed.

### Error: "Failed to fetch URL"
Check internet connection, URL validity, and firewall settings.

### Error: "Extension not allowed"
When saving, use only allowed extensions: `.json`, `.yaml`, `.yml`, `.txt`

### Warning: "Content truncated"
Increase `max_content_length` or use comprehensive tier with chunking.

## Contributing

Style analysis patterns can be improved by:
1. Adding more sophisticated linguistic patterns
2. Tuning thresholds based on empirical data
3. Expanding language support
4. Improving web content extraction

## License

Part of the mostlylucid DiSE project.
