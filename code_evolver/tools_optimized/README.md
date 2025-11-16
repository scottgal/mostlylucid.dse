# NEW Workflow Tools

This directory contains brand new creative workflow tools that expand the capabilities of the code evolver system.

**IMPORTANT**: These are ALL NEW tools - no existing tools were modified. Original tools remain untouched.

## Summary

- **15 New Executable Tools** - Document processing, data manipulation, integrations
- **2 New LLM Tools** - AI-powered image and data analysis
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

### 🤖 AI-Powered Tools (2 LLM tools)

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

## Directory Structure

```
tools_optimized/
├── executable/      # 13 new executable tools
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
│   └── code_formatter.yaml
│
├── llm/             # 2 new LLM tools
│   ├── image_vision_analyzer.yaml
│   └── data_analyzer.yaml
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

**Automation**: file_watcher, webhook_sender, email_sender

**Web Integration**: web_scraper, webhook_sender

**Media**: image_converter, image_vision_analyzer

**Code Quality**: code_formatter

**AI Analysis**: image_vision_analyzer, data_analyzer

### By Speed

**Very Fast (< 1s)**: json_transformer, file_watcher, csv_processor, webhook_sender, code_formatter

**Fast (1-5s)**: excel_processor, database_connector, email_sender, image_converter

**Medium (5-30s)**: pdf_reader, word_processor, web_scraper, data_analyzer, image_vision_analyzer

**Variable**: universal_document_parser (depends on format/size)

### By Cost

**Free**: All executable tools

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
