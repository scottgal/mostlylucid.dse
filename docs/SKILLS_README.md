# Style Duplication and Markdown Generation Skills

Two new powerful skills for analyzing writing style and generating styled markdown documentation.

## Skills Overview

### 1. `duplicate_style` - Style Analysis Skill

Analyzes writing style from a directory of content using tiered summarization for efficient processing.

**Location:** `code_evolver/tools/executable/duplicate_style.py`

**Features:**
- Recursive directory scanning with smart file filtering
- Tiered LLM selection (gemma2:2b → llama3 → mistral-nemo) based on content size
- Context-aware chunking and progressive summarization
- Incremental style analysis across multiple files
- Optional review and refinement for higher quality

**Input:**
```json
{
  "directory": "/path/to/content",
  "file_patterns": ["*.md", "*.txt"],
  "max_files": 100,
  "quality_requirement": 0.8,
  "review_and_refine": true
}
```

**Output:**
```json
{
  "style_guide": "Comprehensive style analysis...",
  "files_analyzed": 42,
  "total_content_length": 50000,
  "success": true
}
```

**Example Usage:**
```bash
echo '{
  "directory": "docs/",
  "file_patterns": ["*.md"],
  "quality_requirement": 0.8,
  "review_and_refine": true
}' | python code_evolver/tools/executable/duplicate_style.py
```

---

### 2. `write_markdown_doc` - Markdown Documentation Generator

Generates well-formatted markdown documentation with optional style matching.

**Location:** `code_evolver/tools/executable/write_markdown_doc.py`

**Features:**
- Smart LLM tier selection for optimal quality/speed balance
- Optional style guide matching (works with `duplicate_style` output)
- Review and refinement capability
- Proper markdown formatting with validation
- Configurable length (short ~500w, medium ~1500w, long ~3000w)
- **Security guardrails:** enforces output only to `output/` directory

**Input:**
```json
{
  "topic": "What to write about",
  "output_file": "docs/readme.md",
  "style_guide": "Optional style from duplicate_style",
  "outline": "Optional outline",
  "length": "medium",
  "quality_requirement": 0.8,
  "review_and_refine": true
}
```

**Output:**
```json
{
  "file_path": "output/docs/readme.md",
  "content_length": 5000,
  "word_count": 1500,
  "validation": {
    "valid": true,
    "has_headers": true,
    "has_lists": true
  },
  "success": true
}
```

**Example Usage:**
```bash
echo '{
  "topic": "Introduction to Python async/await",
  "output_file": "guides/python_async.md",
  "length": "medium",
  "quality_requirement": 0.8
}' | python code_evolver/tools/executable/write_markdown_doc.py
```

---

## Combined Workflow Example

Extract style from existing documentation and use it to generate new documentation:

```bash
# Step 1: Analyze existing documentation style
STYLE=$(echo '{
  "directory": "existing_docs/",
  "file_patterns": ["*.md"],
  "quality_requirement": 0.8,
  "review_and_refine": true
}' | python code_evolver/tools/executable/duplicate_style.py | jq -r '.style_guide')

# Step 2: Generate new documentation matching that style
echo "{
  \"topic\": \"New Feature Documentation\",
  \"output_file\": \"features/new_feature.md\",
  \"style_guide\": \"$STYLE\",
  \"length\": \"long\",
  \"quality_requirement\": 0.9,
  \"review_and_refine\": true
}" | python code_evolver/tools/executable/write_markdown_doc.py
```

---

## Architecture

### Tiered Summarization System

Both skills use a smart tiered approach to balance speed, quality, and cost:

| Tier | Model | Context Window | Use Case |
|------|-------|---------------|----------|
| Fast | gemma2:2b | 8K tokens | Quick analysis, small content |
| Medium | llama3 | 32K tokens | Balanced quality/speed, most common |
| Large | mistral-nemo | 128K tokens | High quality, large content |

**Automatic Selection:**
- Content size is estimated (4 chars ≈ 1 token)
- Quality requirement influences tier selection
- Progressive summarization for content exceeding context windows

### Security Features

**write_markdown_doc** includes multiple security guardrails:

1. **Path Validation:** All output paths validated to be under `output/` directory
2. **No Traversal:** Blocks `../` path traversal attempts
3. **Sanitized Paths:** Absolute paths are converted to relative under `output/`
4. **Extension Whitelist:** Only `.md` files allowed

```python
# These are BLOCKED:
"../../../etc/passwd.md"  # Path traversal
"/etc/passwd.md"           # Converted to output/etc/passwd.md

# These are ALLOWED:
"docs/readme.md"          # → output/docs/readme.md
"api/reference.md"        # → output/api/reference.md
```

---

## Testing

Run validation tests:

```bash
python test_skills.py
```

Tests validate:
- ✓ Skill structure and files exist
- ✓ JSON input/output schemas
- ✓ File permissions (executable)
- ✓ Security guardrails working
- ✓ Path validation logic

---

## Dependencies

Required Python packages:
- requests
- pyyaml
- numpy
- psutil
- rich
- aiohttp

Install via:
```bash
pip install -r code_evolver/requirements.txt
```

---

## Use Cases

### duplicate_style
- Extract writing style from documentation
- Analyze code comment conventions
- Create style guides from existing content
- Understand voice and tone patterns
- Ensure consistency across documentation

### write_markdown_doc
- Generate documentation matching existing style
- Create technical articles and guides
- Write README files and tutorials
- Generate API documentation
- Produce consistent, styled content at scale

---

## Performance

### duplicate_style
- **Average time:** 30-60 seconds (depends on content size)
- **Scales with:** Number of files × content size
- **Optimization:** Uses incremental summarization to manage context

### write_markdown_doc
- **Average time:** 15-30 seconds (depends on length and quality)
- **Scales with:** Target length × quality requirement
- **Optimization:** Smart tier selection minimizes latency

---

## Future Enhancements

Potential improvements:
- [ ] Support for more file formats (HTML, PDF, DOCX)
- [ ] Custom style templates
- [ ] Style comparison and diff
- [ ] Integration with version control for style tracking
- [ ] Multi-language support
- [ ] Streaming output for large documents
- [ ] Caching of style analyses
