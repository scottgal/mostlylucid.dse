# Optimized Tools Directory

This directory contains optimized versions of all tools with improved:
- **Code quality**: Better structure, error handling, and maintainability
- **Documentation**: Comprehensive usage notes and examples
- **Consistency**: Standardized schemas, metadata, and patterns
- **Validation**: Input/output validation and type checking

## Key Improvements

### 1. Standardized Schemas
All tools now have consistent, structured input/output schemas using JSON Schema format.

### 2. Complete Metadata
Every tool includes:
- Performance characteristics (cost_tier, speed_tier, quality_tier)
- Resource constraints (timeout, memory limits)
- Dependencies and installation requirements
- Version information

### 3. Base Classes
Common functionality extracted to reusable base classes:
- `BaseTool`: For executable tools
- `BaseCustomTool`: For custom Python tools
- `OpenAPIClient`: For OpenAPI integrations

### 4. Error Handling
Standardized error handling with:
- Consistent error message formats
- Proper exception handling
- Retry logic where appropriate
- Clear failure modes

### 5. Documentation
Enhanced documentation including:
- Detailed usage notes
- Multiple examples
- Integration guides
- Best practices

## Directory Structure

```
tools_optimized/
├── executable/          # Optimized executable tools
├── llm/                 # Optimized LLM tools
├── custom/              # Optimized custom tools
├── openapi/             # Optimized OpenAPI tools
├── lib/                 # Shared base classes and utilities
├── schemas/             # JSON schemas for validation
├── validators/          # Tool validation scripts
└── README.md           # This file
```

## Behavior Preservation

**IMPORTANT**: All optimized tools maintain 100% behavioral compatibility with original tools.
- Same inputs produce same outputs
- All existing tests pass
- API contracts unchanged
- Only internal implementation improved

## Migration Guide

See `OPTIMIZATION_GUIDE.md` for:
- Detailed list of improvements per tool
- Migration instructions
- Testing procedures
- Breaking change analysis (spoiler: none!)

## Validation

Run validation suite:
```bash
cd code_evolver/tools_optimized
python validators/validate_all_tools.py
```

Run compatibility tests:
```bash
pytest tests/test_tool_compatibility.py
```
