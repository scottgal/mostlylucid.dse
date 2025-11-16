# NEW Workflow Tools

This directory contains brand new creative workflow tools that expand the capabilities of the code evolver system.

**IMPORTANT**: These are ALL NEW tools - no existing tools were modified. Original tools remain untouched.

## Summary

- **18 New Executable Tools** - Document processing, data manipulation, integrations, storage
- **3 New LLM Tools** - AI-powered image and data analysis
- **100% New** - No modifications to existing tools
- **Production Ready** - Complete with specs, examples, documentation

## New Tools Added

### 📄 Document Processing (4 tools)

#### 1. PDF Text Extractor
Extract text from PDFs with OCR support for scanned documents.
- Multi-page extraction
- OCR for scanned PDFs
- Metadata extraction
- Encrypted PDF support

#### 2. Word Document Processor
Complete Word document read/write with formatting.
- Read .docx files
- Create and modify documents
- Extract tables
- Template support

#### 3. Excel Spreadsheet Processor
Advanced Excel processing with pandas integration.
- Read/write .xlsx and .xls
- SQL-like queries
- Pivot tables
- Multiple sheets

#### 4. Universal Document Parser
Parse 100+ document formats automatically.
- Supports Office, PDF, images, code, archives
- Auto-format detection
- OCR for images
- One tool for all documents

### 🔄 Data Processing (2 tools)

#### 5. JSON Transformer
Transform JSON with JMESPath and JSONPath.
- Query and filter JSON
- Transform data structures
- Schema validation
- Essential for data pipelines

#### 6. CSV Data Processor
Advanced CSV processing with pandas.
- Filter, transform, aggregate
- Large file support
- Data cleaning
- Statistical operations

### 🤖 Automation & Monitoring (2 tools)

#### 7. File System Watcher
Monitor filesystem for changes and trigger workflows.
- Watch for create/modify/delete
- Pattern filtering
- Recursive monitoring
- Real-time triggers

#### 8. Webhook Sender
Send webhooks to Slack, Discord, Teams.
- Rich formatting
- Mentions and attachments
- Multiple services
- Perfect for notifications

### 🌐 Web & Network (2 tools)

#### 9. Web Scraper
Extract content from web pages with CSS selectors.
- JavaScript rendering
- Rate limiting
- robots.txt compliance
- Response caching

#### 10. Database Connector
Connect to SQL and NoSQL databases.
- MySQL, PostgreSQL, MongoDB, etc.
- Execute queries
- Transactions
- Data pipeline integration

### 📧 Communication (1 tool)

#### 11. Email Sender
Send emails with templates and attachments.
- HTML and text emails
- Template support
- Bulk sending
- SMTP integration

### 🎨 Media Processing (1 tool)

#### 12. Image Converter & Processor
Convert, resize, optimize images in 50+ formats.
- Format conversion
- Resize and crop
- Compression
- Watermarking

### 💻 Code Quality (1 tool)

#### 13. Code Formatter
Multi-language code formatting.
- Python, JavaScript, TypeScript, Java, C++, Go, Rust
- Multiple style guides
- Format-on-save

### 🤖 AI-Powered Tools (3 LLM tools)

#### 14. Image Vision Analyzer
AI-powered image analysis and description.
- Object detection
- Text extraction (OCR)
- Scene recognition
- Answer questions about images

#### 15. Data Analyzer
AI-powered data analysis and insights.
- Statistical summaries
- Pattern detection
- Anomaly identification
- Correlation analysis

#### 16. Smart Image Processor
ImageMagick-equivalent with natural language interface.
- Natural language prompts ("take screenshot and resize to half")
- Chains multiple image operations
- Combines webpage_screenshot and image_converter
- AI parses and executes complex workflows

### 🌐 Web Automation (1 tool)

#### 17. Webpage Screenshot
Capture screenshots of web pages with browser automation.
- Full page screenshots
- Element selection
- Mobile device emulation
- JavaScript rendering
- Wait strategies

### ⏰ Task Scheduling (2 tools)

#### 18. Task Scheduler
Schedule recurring tasks with cron syntax.
- Standard cron expressions
- One-time and recurring tasks
- Auto-start background worker
- Pause/resume/trigger tasks

#### 19. Background Task Runner
Global singleton background worker for all tools.
- Shared worker pool (4 threads)
- Auto-start when tasks registered
- All tools use same runner (no duplication)
- Queue management and monitoring

### 💾 Storage & State (2 tools)

#### 20. Tool-Scoped Storage
Per-tool isolated key-value storage.
- Each tool has separate namespace
- File-based persistence (shelve)
- Tool state, config, cache
- Thread-safe with file locking

#### 21. Global-Scoped Storage
System-wide shared key-value storage.
- Shared across all tools
- Cross-tool communication
- Workflow coordination
- Shared configuration

## Directory Structure

```
tools_optimized/
├── executable/      # 18 new executable tools
│   ├── pdf_reader.yaml
│   ├── word_processor.yaml
│   ├── excel_processor.yaml
│   ├── universal_document_parser.yaml
│   ├── json_transformer.yaml
│   ├── csv_processor.yaml
│   ├── file_watcher.yaml
│   ├── webhook_sender.yaml
│   ├── web_scraper.yaml
│   ├── database_connector.yaml
│   ├── email_sender.yaml
│   ├── image_converter.yaml
│   ├── code_formatter.yaml
│   ├── webpage_screenshot.yaml           # NEW: Web automation
│   ├── task_scheduler.yaml               # NEW: Cron scheduling
│   ├── background_task_runner.yaml       # NEW: Global worker
│   ├── tool_scoped_storage.yaml          # NEW: Per-tool storage
│   └── global_scoped_storage.yaml        # NEW: Shared storage
│
├── llm/             # 3 new LLM tools
│   ├── image_vision_analyzer.yaml
│   ├── data_analyzer.yaml
│   └── smart_image_processor.yaml        # NEW: AI image workflow
│
├── lib/             # Shared libraries
│   ├── base_tool.py
│   ├── base_custom_tool.py
│   └── config_resolver.py
│
├── schemas/         # Tool schemas
│   └── tool_schema.json
│
├── validators/      # Validation tools
│   └── tool_validator.py
│
└── README.md       # This file
```

## Quick Start

### Using Tools

All tools follow the same pattern:

```python
# Call tool with operation and parameters
result = call_tool("pdf_reader", {
    "pdf_file": "document.pdf",
    "pages": "all",
    "ocr": false
})

# Result contains extracted text
print(result["text"])
```

## Storage Scope Concept

The system provides two types of persistent storage for tools:

### Tool-Scoped Storage (`tool_scoped_storage`)

**Purpose**: Per-tool isolated key-value storage

**When to use**:
- Tool needs to store its own configuration
- Tool needs to maintain internal state
- Tool needs cache that shouldn't be shared
- Data belongs to one specific tool

**Example**:
```python
# Store tool-specific configuration
call_tool("tool_scoped_storage", {
    "operation": "set",
    "tool_name": "my_analyzer",
    "key": "config",
    "value": {
        "threshold": 0.8,
        "enabled": true,
        "last_run": "2025-11-16T10:30:00"
    }
})

# Retrieve tool-specific configuration
config = call_tool("tool_scoped_storage", {
    "operation": "get",
    "tool_name": "my_analyzer",
    "key": "config",
    "default": {}
})
```

**Isolation**: Tool A cannot access Tool B's storage. Each tool has its own isolated namespace.

**Storage location**: `~/.code_evolver/storage/tool_scoped/{tool_name}.db`

### Global-Scoped Storage (`global_scoped_storage`)

**Purpose**: System-wide shared key-value storage accessible by all tools

**When to use**:
- Multiple tools need to access the same data
- Cross-tool communication required
- Workflow coordination between tools
- Shared system configuration
- Feature flags that affect multiple tools

**Example**:
```python
# Store system-wide configuration (all tools can access)
call_tool("global_scoped_storage", {
    "operation": "set",
    "key": "system.api_endpoint",
    "value": "https://api.example.com"
})

# Any tool can retrieve shared configuration
endpoint = call_tool("global_scoped_storage", {
    "operation": "get",
    "key": "system.api_endpoint",
    "default": "https://default.example.com"
})

# Workflow coordination: Tool A stores results for Tool B
call_tool("global_scoped_storage", {
    "operation": "set",
    "key": "workflow.extraction.results",
    "value": extraction_data
})

# Tool B retrieves results from Tool A
data = call_tool("global_scoped_storage", {
    "operation": "get",
    "key": "workflow.extraction.results"
})
```

**Shared Access**: All tools can read/write the same keys. Use naming conventions to avoid conflicts.

**Storage location**: `~/.code_evolver/storage/global/global.db`

### Storage Operations

Both storage tools support the same operations:

- **get**: Retrieve value (with optional default)
- **set**: Store value (JSON-serializable)
- **delete**: Remove key
- **exists**: Check if key exists
- **list/keys**: List all keys
- **size**: Count number of keys
- **clear**: Remove all data (use with caution!)

### Key Naming Best Practices

**Tool-Scoped Storage**:
```python
# Good: Descriptive keys
"config"
"last_run_timestamp"
"cache:user:123"
"state:processing"

# Bad: Unclear keys
"c"
"lrt"
"d"
```

**Global-Scoped Storage**:
```python
# Good: Namespaced with dots
"system.api_endpoint"
"workflow.step1.results"
"credentials.api_key"
"feature.new_ui_enabled"
"shared.config.timeout"

# Bad: No namespace
"endpoint"
"results"
"key"
```

### Storage Use Cases

**Tool State Persistence**:
```python
# Analyzer remembers last run
call_tool("tool_scoped_storage", {
    "operation": "set",
    "tool_name": "data_analyzer",
    "key": "last_run",
    "value": {
        "timestamp": now(),
        "records_processed": 1000,
        "status": "success"
    }
})
```

**Cross-Tool Workflow**:
```python
# Step 1: Extractor stores results in global scope
call_tool("global_scoped_storage", {
    "operation": "set",
    "key": "workflow.extracted_data",
    "value": extracted_data
})

# Step 2: Processor retrieves from global scope
data = call_tool("global_scoped_storage", {
    "operation": "get",
    "key": "workflow.extracted_data"
})

# Step 3: Clean up after workflow
call_tool("global_scoped_storage", {
    "operation": "delete",
    "key": "workflow.extracted_data"
})
```

**Shared Configuration**:
```python
# Setup tool configures system
call_tool("global_scoped_storage", {
    "operation": "set",
    "key": "config.database",
    "value": {
        "host": "localhost",
        "port": 5432,
        "database": "myapp"
    }
})

# All tools use same configuration
db_config = call_tool("global_scoped_storage", {
    "operation": "get",
    "key": "config.database"
})
```

**Feature Flags**:
```python
# Enable feature globally
call_tool("global_scoped_storage", {
    "operation": "set",
    "key": "feature.beta_mode",
    "value": true
})

# Tools check feature flag
if call_tool("global_scoped_storage", {
    "operation": "get",
    "key": "feature.beta_mode",
    "default": false
})["value"]:
    enable_beta_features()
```

### Technical Details

- **File-based**: Uses Python's `shelve` module (proven, lightweight, built-in)
- **Persistence**: Data survives process restarts
- **Thread-safe**: File locking prevents corruption
- **Performance**: Read < 1ms, Write < 5ms
- **Limits**: Max 256 char keys, 10 MB per value
- **Security**: File permissions 0600 (owner read/write only)

### Example Workflows

#### Document Processing Pipeline
```python
# 1. Watch for new PDFs
file_watcher.start(path="/uploads", pattern="*.pdf")

# 2. Extract text
text = pdf_reader.read(file_path="new_document.pdf")

# 3. Analyze content
insights = data_analyzer.analyze(data=text)

# 4. Send notification
webhook_sender.send(service="slack", message="Document processed!")
```

#### Data Analysis Workflow
```python
# 1. Load Excel data
data = excel_processor.read(file_path="sales.xlsx", sheet_name="Q4")

# 2. Transform to JSON
json_data = json_transformer.transform(data=data, operation="restructure")

# 3. Analyze with AI
insights = data_analyzer.analyze(data=json_data)

# 4. Generate report
report = word_processor.create(template="report_template.docx", vars=insights)
```

#### Web Monitoring System
```python
# 1. Scrape website
data = web_scraper.scrape(url="https://example.com/data")

# 2. Process with CSV
processed = csv_processor.filter(data=data, expression="price < 100")

# 3. Store in database
database_connector.insert(table="products", data=processed)

# 4. Send alert
email_sender.send(to=["admin@example.com"], subject="New data available")
```

## Tool Categories

### By Use Case

**Document Processing**: pdf_reader, word_processor, excel_processor, universal_document_parser

**Data Manipulation**: json_transformer, csv_processor, database_connector

**Automation**: file_watcher, webhook_sender, email_sender, task_scheduler, background_task_runner

**Web Integration**: web_scraper, webhook_sender, webpage_screenshot

**Media**: image_converter, image_vision_analyzer, smart_image_processor

**Code Quality**: code_formatter

**AI Analysis**: image_vision_analyzer, data_analyzer, smart_image_processor

**Storage & State**: tool_scoped_storage, global_scoped_storage

### By Speed

**Very Fast (< 1s)**: json_transformer, file_watcher, csv_processor, webhook_sender, code_formatter, tool_scoped_storage, global_scoped_storage

**Fast (1-5s)**: excel_processor, database_connector, email_sender, image_converter, task_scheduler, background_task_runner

**Medium (5-30s)**: pdf_reader, word_processor, web_scraper, data_analyzer, image_vision_analyzer, webpage_screenshot

**Workflow (Variable)**: smart_image_processor (depends on operations chained), universal_document_parser (depends on format/size)

### By Cost

**Free**: All executable tools (18 tools)

**Low**: smart_image_processor (uses tier_3 coding model)

**Medium**: data_analyzer

**High**: image_vision_analyzer (vision models are expensive)

## Features

All tools include:
- ✅ Complete specifications
- ✅ Structured input/output schemas
- ✅ Comprehensive documentation
- ✅ Multiple examples
- ✅ Error handling
- ✅ Resource constraints
- ✅ Performance metadata

## Installation

Tools specify their dependencies:
```bash
# Each tool includes installation command
pip install python-docx openpyxl pandas requests pillow pytesseract textract
```

## Validation

Validate all tools:
```bash
cd code_evolver/tools_optimized
python validators/tool_validator.py
```

## Best Practices

1. **Read Documentation**: Each tool has comprehensive usage notes
2. **Check Examples**: Multiple examples show common use cases
3. **Handle Errors**: All tools return structured error messages
4. **Resource Limits**: Tools have timeout and memory constraints
5. **Security**: Use environment variables for credentials

## Support

Each tool's YAML file contains:
- Detailed `usage_notes` with examples
- `examples` showing input/output
- `tags` for discovery
- Resource `constraints`

## Future Additions

Planned tools:
- Audio transcription
- Video processing
- Cloud storage connectors (S3, GCS, Azure)
- API client generator
- GraphQL client
- WebSocket client
- ...and more!

## Contributing

When adding new tools:
1. Follow the existing YAML structure
2. Include complete documentation
3. Add multiple examples
4. Specify resource constraints
5. Add appropriate tags
6. Run validation before committing

## License

These tools are part of the code evolver system.
