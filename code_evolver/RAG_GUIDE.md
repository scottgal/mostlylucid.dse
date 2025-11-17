# RAG Memory System Guide

**Retrieval-Augmented Generation (RAG) for Code Evolution**

The RAG Memory system provides semantic search and retrieval for plans, functions, sub-workflows, and workflows using embedding-based similarity.

---

## Table of Contents

1. [Overview](#overview)
2. [Artifact Types](#artifact-types)
3. [Architecture](#architecture)
4. [Usage Guide](#usage-guide)
5. [Tagging System](#tagging-system)
6. [Embeddings & Similarity Search](#embeddings--similarity-search)
7. [API Reference](#api-reference)
8. [Examples](#examples)
9. [Best Practices](#best-practices)

---

## Overview

The RAG Memory system stores and retrieves various artifacts using:
- **Semantic Embeddings**: Uses Ollama embeddings for semantic similarity
- **Tag-Based Indexing**: Fast retrieval using tags
- **Quality Scoring**: Tracks artifact quality based on usage
- **Usage Analytics**: Monitors which artifacts are most useful

### Key Features

✅ Store plans, functions, workflows, and sub-workflows
✅ Semantic similarity search using embeddings
✅ Tag-based filtering and categorization
✅ Usage tracking and quality scoring
✅ Persistent storage with JSON + NumPy
✅ Keyword fallback when embeddings unavailable

---

## Artifact Types

The system supports six artifact types:

### 1. PLAN
Strategic approaches and methodologies from the overseer LLM.

**Use cases:**
- Problem-solving strategies
- Algorithm selection rationale
- Optimization approaches

**Example:**
```python
rag.store_artifact(
    artifact_id="plan_text_processing",
    artifact_type=ArtifactType.PLAN,
    name="Large File Processing Strategy",
    description="Strategy for processing large text files efficiently",
    content="""
1. Read file in chunks (configurable chunk size)
2. Process each chunk independently
3. Use streaming to handle results
4. Implement backpressure handling
""",
    tags=["streaming", "performance", "text-processing"]
)
```

### 2. FUNCTION
Reusable code functions with clear interfaces.

**Use cases:**
- Utility functions
- Common algorithms
- Validators and parsers

**Example:**
```python
code = '''
def validate_email(email: str) -> tuple[bool, str]:
    """Validate email address format."""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$'

    if not email:
        return False, "Email cannot be empty"

    if re.match(pattern, email):
        return True, "Valid email"
    else:
        return False, "Invalid email format"
'''

rag.store_artifact(
    artifact_id="func_validate_email",
    artifact_type=ArtifactType.FUNCTION,
    name="Email Validator",
    description="Validates email addresses with detailed error messages",
    content=code,
    tags=["validation", "email", "utility", "regex"]
)
```

### 3. WORKFLOW
Complete sequences of operations.

**Use cases:**
- Code generation pipelines
- Testing workflows
- Deployment sequences

**Example:**
```python
workflow = {
    "name": "Code Generation Workflow",
    "steps": [
        {
            "id": "overseer_planning",
            "action": "consult_llm",
            "model": "overseer",
            "purpose": "Analyze problem and plan approach"
        },
        {
            "id": "code_generation",
            "action": "generate_code",
            "model": "generator",
            "depends_on": ["overseer_planning"]
        },
        {
            "id": "unit_tests",
            "action": "generate_tests",
            "model": "generator",
            "depends_on": ["code_generation"]
        },
        {
            "id": "execution",
            "action": "run_code",
            "sandbox": true,
            "depends_on": ["code_generation", "unit_tests"]
        },
        {
            "id": "evaluation",
            "action": "evaluate",
            "model": "evaluator",
            "depends_on": ["execution"]
        }
    ]
}

rag.store_artifact(
    artifact_id="workflow_code_gen_full",
    artifact_type=ArtifactType.WORKFLOW,
    name="Complete Code Generation Workflow",
    description="End-to-end workflow for generating, testing, and evaluating code",
    content=json.dumps(workflow, indent=2),
    tags=["workflow", "code-generation", "testing", "evaluation"]
)
```

### 4. SUB_WORKFLOW
Reusable parts of larger workflows.

**Use cases:**
- Common workflow patterns
- Reusable workflow components
- Specialized processing steps

**Example:**
```python
sub_workflow = {
    "name": "Test and Fix Loop",
    "description": "Runs tests and escalates failures for fixing",
    "steps": [
        {"action": "run_tests", "framework": "pytest"},
        {
            "action": "check_results",
            "on_failure": "escalate"
        },
        {
            "action": "fix_code",
            "model": "escalation",
            "max_attempts": 3
        }
    ]
}

rag.store_artifact(
    artifact_id="subwf_test_fix_loop",
    artifact_type=ArtifactType.SUB_WORKFLOW,
    name="Test and Fix Loop",
    description="Reusable sub-workflow for testing and auto-fixing",
    content=json.dumps(sub_workflow, indent=2),
    tags=["testing", "escalation", "auto-fix", "sub-workflow"]
)
```

### 5. PROMPT
Reusable prompt templates.

**Use cases:**
- Code review prompts
- Evaluation templates
- Common LLM interactions

**Example:**
```python
prompt = """You are a security auditor. Review the following code for:
1. SQL injection vulnerabilities
2. XSS attack vectors
3. Authentication/authorization issues
4. Data exposure risks
5. Input validation problems

Code to review:
{code}

Provide a structured report with:
- Severity (critical/high/medium/low)
- Description of each issue
- Specific line numbers
- Suggested fixes
"""

rag.store_artifact(
    artifact_id="prompt_security_audit",
    artifact_type=ArtifactType.PROMPT,
    name="Security Audit Prompt",
    description="Comprehensive security audit prompt template",
    content=prompt,
    tags=["security", "audit", "prompt", "code-review"]
)
```

### 6. PATTERN
Design patterns and solution templates.

**Use cases:**
- Common design patterns
- Architecture templates
- Problem-solving approaches

---

## Architecture

### Storage Structure

```
rag_memory/
├── index.json              # Artifact metadata
├── embeddings.npy          # NumPy array of embeddings
├── tags_index.json         # Tag -> artifact_id mapping
└── artifacts/              # Individual artifact files (optional)
    ├── plan_*.json
    ├── func_*.json
    └── workflow_*.json
```

### Data Flow

```
Store Artifact
    ↓
Generate Embedding (Ollama)
    ↓
Save to Index + Embeddings Matrix
    ↓
Update Tags Index

Search/Retrieve
    ↓
Generate Query Embedding
    ↓
Calculate Cosine Similarity
    ↓
Filter by Type/Tags
    ↓
Return Top-K Results
```

---

## Usage Guide

### Initialization

```python
from src import RAGMemory, ArtifactType, OllamaClient, ConfigManager

# Initialize components
config = ConfigManager()
client = OllamaClient(config_manager=config)

# Create RAG memory
rag = RAGMemory(
    memory_path="./rag_memory",
    ollama_client=client,
    embedding_model="llama3"  # Model for embeddings
)
```

### Storing Artifacts

```python
# Store a plan
artifact = rag.store_artifact(
    artifact_id="unique_id",
    artifact_type=ArtifactType.PLAN,
    name="Human-readable name",
    description="Detailed description for search",
    content="Actual content (code, plan, etc.)",
    tags=["tag1", "tag2", "tag3"],
    metadata={"author": "overseer", "complexity": "high"},
    auto_embed=True  # Generate embedding automatically
)
```

### Semantic Search

```python
# Find similar artifacts using embeddings
results = rag.find_similar(
    query="How to process large files efficiently?",
    artifact_type=ArtifactType.PLAN,  # Optional filter
    tags=["performance"],  # Optional filter
    top_k=5,  # Number of results
    min_similarity=0.6  # Minimum similarity threshold
)

for artifact, similarity in results:
    print(f"{artifact.name}: {similarity:.2f}")
    print(artifact.content)
```

### Tag-Based Retrieval

```python
# Find by tags (any match)
artifacts = rag.find_by_tags(
    tags=["validation", "email"],
    artifact_type=ArtifactType.FUNCTION
)

# Find by tags (all must match)
artifacts = rag.find_by_tags(
    tags=["python", "async", "utility"],
    match_all=True
)
```

### Keyword Search (Fallback)

```python
# When embeddings aren't available
results = rag.search_by_keywords(
    query="email validation regex",
    artifact_type=ArtifactType.FUNCTION,
    top_k=3
)
```

### Usage Tracking

```python
# Increment usage when artifact is used
rag.increment_usage("artifact_id")

# Update quality score based on feedback
rag.update_quality_score("artifact_id", 0.85)  # 0.0 to 1.0
```

---

## Tagging System

### Common Tag Categories

**By Purpose:**
- `validation`, `parsing`, `transformation`, `generation`

**By Domain:**
- `text-processing`, `data-analysis`, `web`, `api`, `database`

**By Technology:**
- `python`, `async`, `regex`, `json`, `xml`

**By Quality:**
- `production-ready`, `experimental`, `deprecated`

**By Workflow Stage:**
- `planning`, `generation`, `testing`, `deployment`

**By Performance:**
- `optimized`, `streaming`, `batch`, `real-time`

### Best Practices for Tagging

1. **Be Specific**: `email-validation` better than just `validation`
2. **Use Hierarchies**: `validation/email`, `validation/phone`
3. **Include Technology**: `python`, `async`, `pandas`
4. **Add Context**: `performance`, `security`, `production`
5. **Use Consistent Naming**: `snake_case` or `kebab-case`

---

## Embeddings & Similarity Search

### How It Works

1. **Text Preparation**: Combines name, description, and content sample
2. **Embedding Generation**: Uses Ollama's embeddings API
3. **Storage**: Embeddings stored in NumPy matrix for efficiency
4. **Similarity Calculation**: Cosine similarity between query and artifacts
5. **Ranking**: Results sorted by similarity score

### Embedding Model Selection

```python
# Use llama3 for general purpose (default)
rag = RAGMemory(embedding_model="llama3")

# Use specialized models if available
rag = RAGMemory(embedding_model="nomic-embed-text")
```

### Similarity Thresholds

- **0.9-1.0**: Nearly identical
- **0.7-0.9**: Very similar
- **0.5-0.7**: Moderately similar
- **0.3-0.5**: Somewhat related
- **< 0.3**: Weakly related

---

## API Reference

### RAGMemory Class

#### `store_artifact(...)`
```python
def store_artifact(
    artifact_id: str,
    artifact_type: ArtifactType,
    name: str,
    description: str,
    content: str,
    tags: List[str],
    metadata: Optional[Dict[str, Any]] = None,
    auto_embed: bool = True
) -> Artifact
```

#### `find_similar(...)`
```python
def find_similar(
    query: str,
    artifact_type: Optional[ArtifactType] = None,
    tags: Optional[List[str]] = None,
    top_k: int = 5,
    min_similarity: float = 0.5
) -> List[Tuple[Artifact, float]]
```

#### `find_by_tags(...)`
```python
def find_by_tags(
    tags: List[str],
    artifact_type: Optional[ArtifactType] = None,
    match_all: bool = False
) -> List[Artifact]
```

#### `get_artifact(...)`
```python
def get_artifact(artifact_id: str) -> Optional[Artifact]
```

#### `increment_usage(...)`
```python
def increment_usage(artifact_id: str)
```

#### `update_quality_score(...)`
```python
def update_quality_score(artifact_id: str, score: float)
```

#### `get_statistics()`
```python
def get_statistics() -> Dict[str, Any]
```

---

## Examples

### Example 1: Store and Retrieve Plans

```python
# Store a plan
rag.store_artifact(
    artifact_id="plan_api_design",
    artifact_type=ArtifactType.PLAN,
    name="RESTful API Design Strategy",
    description="Best practices for designing scalable REST APIs",
    content="""
1. Use resource-based URLs
2. HTTP methods for CRUD operations
3. Proper status codes
4. Versioning strategy
5. Authentication/Authorization
6. Rate limiting
7. Documentation (OpenAPI)
""",
    tags=["api", "rest", "design", "backend"]
)

# Find similar plans later
results = rag.find_similar(
    "How to design a good API?",
    artifact_type=ArtifactType.PLAN
)
```

### Example 2: Build a Function Library

```python
# Store multiple utility functions
functions = [
    ("func_parse_json", "JSON Parser", "Safe JSON parsing with error handling", parse_json_code, ["json", "parsing", "utility"]),
    ("func_validate_url", "URL Validator", "Validates URL format", validate_url_code, ["validation", "url", "utility"]),
    ("func_sanitize_html", "HTML Sanitizer", "Removes dangerous HTML tags", sanitize_html_code, ["security", "html", "utility"])
]

for func_id, name, desc, code, tags in functions:
    rag.store_artifact(
        artifact_id=func_id,
        artifact_type=ArtifactType.FUNCTION,
        name=name,
        description=desc,
        content=code,
        tags=tags
    )

# Find all utility functions
utilities = rag.find_by_tags(["utility"], artifact_type=ArtifactType.FUNCTION)
```

### Example 3: Workflow Composition

```python
# Store sub-workflows
rag.store_artifact(
    artifact_id="subwf_input_validation",
    artifact_type=ArtifactType.SUB_WORKFLOW,
    name="Input Validation",
    description="Standard input validation sub-workflow",
    content=input_validation_workflow,
    tags=["validation", "input", "security"]
)

# Find relevant sub-workflows
validation_workflows = rag.find_by_tags(
    ["validation"],
    artifact_type=ArtifactType.SUB_WORKFLOW
)

# Compose into larger workflow
main_workflow = {
    "steps": [
        {"include": "subwf_input_validation"},
        {"action": "process"},
        {"include": "subwf_output_formatting"}
    ]
}
```

---

## Best Practices

### 1. Descriptive Names and Descriptions
Good names and descriptions improve search quality:

❌ Bad:
```python
name="func1"
description="does stuff"
```

✅ Good:
```python
name="Email Address Validator with Domain Verification"
description="Validates email format using regex and optionally verifies domain exists via DNS lookup"
```

### 2. Comprehensive Tagging
Use multiple specific tags:

❌ Bad:
```python
tags=["code"]
```

✅ Good:
```python
tags=["validation", "email", "regex", "dns", "utility", "python", "production-ready"]
```

### 3. Quality Metadata
Include useful metadata:

```python
metadata={
    "author": "overseer",
    "created_for": "user authentication system",
    "complexity": "low",
    "dependencies": [],
    "test_coverage": 0.95,
    "performance": "O(1)",
    "security_reviewed": True
}
```

### 4. Usage Tracking
Update metrics when artifacts are used:

```python
# When you use an artifact
artifact = rag.get_artifact("func_validate_email")
# ... use it ...
rag.increment_usage("func_validate_email")

# After evaluation
if code_works_well:
    rag.update_quality_score("func_validate_email", 0.9)
```

### 5. Regular Maintenance
Periodically review and clean up:

```python
# Get statistics
stats = rag.get_statistics()

# Find unused artifacts
all_artifacts = rag.list_all()
unused = [a for a in all_artifacts if a.usage_count == 0]

# Remove low-quality artifacts
for artifact in all_artifacts:
    if artifact.quality_score < 0.3 and artifact.usage_count < 2:
        rag.delete_artifact(artifact.artifact_id)
```

### 6. Embeddings Strategy
- Use embeddings for semantic search
- Fall back to keywords if Ollama unavailable
- Consider model selection for embeddings
- Monitor embedding quality with similarity scores

---

## Integration with mostlylucid DiSE

The RAG system integrates with other mostlylucid DiSE components:

```python
# In orchestrator
from src import RAGMemory, ArtifactType

def generate_with_rag(description: str):
    # Find similar solutions
    similar_plans = rag.find_similar(
        description,
        artifact_type=ArtifactType.PLAN,
        top_k=3
    )

    # Use best plan as context
    if similar_plans:
        best_plan = similar_plans[0][0]
        context = f"Similar approach that worked:\n{best_plan.content}"
        rag.increment_usage(best_plan.artifact_id)

    # Generate code with context
    # ...
```

---

## Troubleshooting

### No Embeddings Generated
**Problem**: `auto_embed=True` but no embeddings created

**Solutions**:
1. Check Ollama is running: `curl http://localhost:11434/api/tags`
2. Verify embedding model exists: `ollama list`
3. Check logs for embedding errors
4. Try manual embedding: `rag._generate_embedding("test")`

### Low Similarity Scores
**Problem**: Similar items have low scores

**Solutions**:
1. Improve descriptions (more detail = better embeddings)
2. Use consistent terminology in tags
3. Try different embedding models
4. Use tag-based search as fallback

### Slow Search
**Problem**: Search takes too long

**Solutions**:
1. Reduce `top_k` parameter
2. Use tag filters to narrow search
3. Consider pre-filtering by artifact_type
4. Use keyword search for simple queries

---

## Performance Considerations

- **Embedding Generation**: ~1-2 seconds per artifact
- **Storage**: ~1KB per artifact (metadata) + embedding size
- **Search Time**: O(n) where n = number of artifacts
- **Memory Usage**: All embeddings loaded into RAM

For large deployments (>10,000 artifacts), consider:
- Vector databases (Pinecone, Weaviate, Chroma)
- Approximate nearest neighbor search
- Batch embedding generation
- Embedding caching

---

## Future Enhancements

- [ ] Vector database backends
- [ ] Approximate nearest neighbor search (FAISS, Annoy)
- [ ] Hybrid search (embeddings + keywords + tags)
- [ ] Multi-modal embeddings (code + docs + tests)
- [ ] Automatic quality scoring from usage patterns
- [ ] Artifact versioning and lineage tracking
- [ ] Cross-artifact relationship mapping
- [ ] Federated RAG across multiple instances

---

**Questions or Issues?**
See the main README.md or TESTING.md for more information.
