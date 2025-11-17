# Hierarchical RAG Implementation

This document describes the hierarchical RAG memory system for intelligent code reuse.

## Overview

The system now stores nodes at multiple semantic levels, enabling intelligent matching when similar tasks arrive.

## Key Features

### 1. Multi-Level Semantic Storage

Each generated node is stored with:

- **Interface Schema**: Inputs, outputs, and operation type
- **Callable Instruction**: Function signature for semantic matching (e.g., `translate(content, language)`)
- **Workflow Context**: Links to parent workflows and operation types
- **Operation Classification**: generator, transformer, validator, combiner, splitter, filter

### 2. Hierarchical Matching

When a new task arrives, the system searches at multiple levels:

#### Workflow Level
- Finds similar multi-step workflows
- Example: "write a technical post and translate to welsh" matches "write a joke and translate to french" (83% similarity)
- Provides workflow templates for adaptation

#### Node Level
- Finds reusable nodes with similar operation types
- Example: "translate to welsh" finds existing "translate to french" node
- Uses operation_type to narrow semantic search
- Stores workflow context (parent_workflow, step_id, tool_used)

#### Function Level
- Stores callable instructions for fine-grained matching
- Example: `translate(content, target_language)` matches `convert_text(text, language)`
- Enables parameter-level reuse

## Implementation Details

### Interface Detection

Each generated node has its interface automatically detected:

```json
{
  "inputs": ["content", "language"],
  "outputs": ["result"],
  "operation_type": "transformer",
  "description": "Translates content to target language"
}
```

### Callable Instruction Format

Generated from interface schema for semantic matching:

```
translate_to_french(content)
add_numbers(a, b)
generate_story(topic, length)
```

### Workflow Context Metadata

When a node is part of a workflow, it stores:

```json
{
  "workflow_context": {
    "parent_workflow": "write a joke and translate to french",
    "step_id": "step2",
    "step_description": "Translate to French",
    "tool_used": "nmt_translator",
    "operation_type": "transformer"
  }
}
```

### Operation Type Inference

The `_infer_operation_type()` method categorizes nodes based on keywords:

- **Generator**: write, generate, create, compose, produce
- **Transformer**: translate, convert, transform, format, modify
- **Validator**: validate, check, verify, test, review
- **Combiner**: combine, merge, join, aggregate, summarize
- **Splitter**: split, separate, divide, extract, parse
- **Filter**: filter, select, find, search, match

## Benefits

### 1. Granular Reuse

Each node receives only its specific task, not the full user request:
- "write a joke and translate to french" → "write a joke" (step 1) + "translate to french" (step 2)
- Enables reuse in different contexts

### 2. Adaptive Matching

When "write a technical post and translate to welsh" arrives:
- Workflow level: Finds "write a joke and translate to french" pattern
- Node level: Reuses existing "write" generator and "translate" transformer
- Adapts the translate node for welsh instead of french

### 3. Multi-Step Workflow Support

Tasks are automatically decomposed into reusable steps:
- Workflow detection via keywords (and, then, translate, convert)
- Each step becomes a registered, testable node
- Workflows stored in RAG for future adaptation

## Code Locations

### Core Implementation

- `chat_cli.py:566-618` - `_infer_operation_type()` method
- `chat_cli.py:1749-1791` - Node storage with interface and workflow context
- `chat_cli.py:332-564` - Workflow generation and decomposition
- `chat_cli.py:503-547` - Workflow step execution

### Data Structures

- `src/workflow_spec.py` - Workflow specification format
- `src/workflow_builder.py` - Converts overseer output to structured workflows
- `src/rag_memory.py` - RAG storage and retrieval

## Example Usage

### Scenario: Translation Task Evolution

1. **First task**: "write a joke and translate to french"
   - System generates two nodes:
     - `write_a_joke()` - generator
     - `translate_to_french(content)` - transformer
   - Both stored in RAG with full metadata

2. **Second task**: "write a technical post and translate to welsh"
   - Workflow level: Finds similar 2-step pattern (write + translate)
   - Node level: Finds existing `translate_to_french(content)` node
   - Adapts translate node for welsh
   - Reuses write pattern with different content type

3. **Third task**: "translate my document to spanish"
   - Finds existing `translate_to_french(content)` transformer
   - Adapts for spanish
   - No workflow needed (single operation)

## Future Enhancements

- [ ] Function-level code reuse (extract common functions)
- [ ] Test case reuse across similar nodes
- [ ] Automatic node specialization based on usage patterns
- [ ] Quality-weighted semantic search (prefer high-quality nodes)
- [ ] Cross-workflow node composition (combine nodes from different workflows)

## Configuration

Enable workflow mode in `config.yaml`:

```yaml
chat:
  workflow_mode:
    enabled: true
    detect_keywords: ["and", "then", "translate", "convert"]
    min_steps: 2
    max_steps: 10
```

## Directory Structure

Generated content is organized in specific directories:

- `nodes/` - Generated Python code for each node
- `registry/` - Metadata and performance metrics
- `rag_memory/` - Embeddings and semantic indices
- `output/` - User-generated content (stories, articles, etc.)

All generated directories are git-ignored to keep the repository clean.

---

**Status**: Implemented and tested
**Date**: 2025-01-15
**Version**: 1.0.0
