# Tool Usage Tracking System

## Overview

**All tool calls are tracked by default.** Every call_tool() invocation:
1. Increments usage counter in RAG
2. Updates last_used timestamp  
3. Tracks tool_id (with version) for lineage

## Disable Tracking

### Tool Level (YAML):
track_usage: false

### Workflow Level (env var):
export DISABLE_USAGE_TRACKING=true

### Call Level (kwarg):
call_tool("tool", "prompt", disable_tracking=True)

## Priority
Call level > Tool level > Workflow level

Any TRUE = tracking disabled

## Benefits
- Popular tool analytics
- Version adoption tracking
- Lineage effectiveness
- Learning data generation

## Default: ENABLED (recommended for production)
