# Code Evolver - Complete Tools Reference

**Total Tools: 205**
**Last Updated: 2025-11-18**

This document provides a comprehensive reference of all 205 preconfigured tools available in the Code Evolver system, organized by category.

## Table of Contents

- [CUSTOM](#custom) (6 tools)
- [DEBUG](#debug) (14 tools)
- [EXECUTABLE](#executable) (108 tools)
- [FIXER](#fixer) (4 tools)
- [LLM](#llm) (41 tools)
- [MCP](#mcp) (6 tools)
- [NETWORKING](#networking) (12 tools)
- [OPENAPI](#openapi) (1 tools)
- [OPTIMIZATION](#optimization) (4 tools)
- [PERF](#perf) (9 tools)

---

## CUSTOM

**6 tools** - Custom integrations and external service tools

### Ask User

**File:** `ask_user.yaml`  
**Type:** `custom`  

Interactive user input tool for CLI workflows. Prompts the user for input when running in interactive mode, otherwise asks the overseer LLM to make decisions. Enables workflows to get feedback and confirmation without blocking non-interactive execution. Supports yes/no questions, text input, and multiple choice.

**Tags:** `user-input`, `interactive`, `confirmation`, `prompt`, `cli`, `decision`, `feedback`

---

### Git

**File:** `git.yaml`  
**Type:** `custom`  

Powerful yet safe Git integration tool. Provides access to git operations with authentication from config.yaml. Supports status, log, diff, clone, fetch, pull, push, branch, checkout, and more. Includes safety checks for destructive operations.

**Tags:** `git`, `version-control`, `vcs`, `repository`, `source-control`, `scm`

---

### GitHub

**File:** `github.yaml`  
**Type:** `custom`  

GitHub integration tool for PR management, issue tracking, and repository operations. Works with Git tool for complete GitHub workflow. Supports checking PR status, merge state, comments, reviews, and more. Uses authentication from config.yaml.

**Tags:** `github`, `git`, `pr`, `pull-request`, `issue`, `repository`, `code-review`, `vcs`

---

### Google Fact Check

**File:** `google_factcheck.yaml`  
**Type:** `custom`  

Google Fact Check Tools API integration for verifying claims and checking facts. Responds to natural language questions like 'can you check if this is true' and returns fact-check data from ClaimReview sources. Uses authentication from config.yaml.

**Tags:** `google`, `api`, `fact-check`, `verification`, `claims`, `truth`, `research`

---

### Google Search

**File:** `google_search.yaml`  
**Type:** `custom`  

Google Custom Search API integration for web searches. Responds to natural language queries like 'search for X', 'find out Y', 'top 10 Z results'. Includes RAG caching to store and reuse previous search results. Uses authentication from config.yaml.

**Tags:** `google`, `api`, `search`, `web`, `research`, `rag-cached`, `knowledge`

---

### HTTP Server

**File:** `http_server.yaml`  
**Type:** `custom`  

HTTP server that allows workflows to serve content via HTTP. Supports both HTML and JSON/API responses. Enable workflows to be exposed as web services or REST APIs. Can register endpoints, handle requests, and return formatted responses.

**Tags:** `http`, `server`, `api`, `web`, `rest`, `endpoint`, `service`, `html`, `json`

---

## DEBUG

**14 tools** - Debugging, validation, and code analysis tools

### BugCatcher Exception Monitor

**File:** `bugcatcher.yaml`  
**Type:** `executable`  

Global exception monitoring tool that watches for exceptions and logs them to Loki

---

### Dependency Analyzer

**File:** `dependency_analyzer.yaml`  
**Type:** `executable`  

Analyzes tool dependencies using RAG and metadata for tree shaking. Recursively resolves all required tools, files, and packages to create minimal deployments.

**Tags:** `dependencies`, `tree-shaking`, `optimization`, `analysis`, `packaging`, `deployment`

---

### Internal Test Validator

**File:** `internal_test_validator.yaml`  
**Type:** `executable`  

Internal tool for validating test outputs. Usage tracking disabled since this is internal tooling.

**Tags:** `internal`, `testing`, `validation`, `no-tracking`

---

### Isort Import Checker

**File:** `isort_import_checker.yaml`  
**Type:** `executable`  

Checks if Python imports are sorted correctly

**Tags:** `python`, `imports`, `style`, `organization`

---

### JSON Output Validator

**File:** `json_output_validator.yaml`  
**Type:** `executable`  

Validates that node code outputs valid JSON using json.dumps() and print()

**Tags:** `python`, `json`, `validation`, `output`, `static-analysis`

---

### Main Function Checker

**File:** `main_function_checker.yaml`  
**Type:** `executable`  

Validates that node code has a proper main() function and __main__ block

**Tags:** `python`, `structure`, `validation`, `main`, `static-analysis`

---

### MyPy Type Checker

**File:** `mypy_type_checker.yaml`  
**Type:** `executable`  

Runs mypy type checking on Python code to find type errors before runtime

**Tags:** `python`, `type-checking`, `static-analysis`, `types`

---

### Node Runtime Import Validator

**File:** `node_runtime_import_validator.yaml`  
**Type:** `executable`  

Validates that node_runtime imports come AFTER sys.path.insert() setup to prevent ModuleNotFoundError

**Tags:** `python`, `imports`, `validation`, `node_runtime`, `static-analysis`, `auto-fix`

---

### Output Validator

**File:** `output_validator.yaml`  
**Type:** `executable`  

Validates that every tool produces output (print, return, or file write). For stdin-based tools, ensures JSON output.

**Tags:** `python`, `output`, `validation`, `json`, `static-analysis`

---

### Parse Static Analysis Results

**File:** `parse_static_analysis.yaml`  
**Type:** `executable`  

Parse and aggregate static analysis results for test data generation and tool optimization

**Tags:** `analysis`, `static-analysis`, `parsing`, `quality-metrics`, `test-data`, `optimization`

---

### Python Syntax Validator

**File:** `python_syntax_validator.yaml`  
**Type:** `executable`  

Fast syntax check using Python's AST parser - catches syntax errors before expensive LLM tools

**Tags:** `python`, `syntax`, `validation`, `static-analysis`, `fast`

---

### Static Analysis Runner

**File:** `run_static_analysis.yaml`  
**Type:** `executable`  

Runs all static validators on generated code and reports results. Can run all validators or specific ones. Supports auto-fix and retry-failed modes.

**Tags:** `python`, `validation`, `static-analysis`, `testing`, `quality`, `comprehensive`

---

### Stdin Usage Validator

**File:** `stdin_usage_validator.yaml`  
**Type:** `executable`  

Validates that node code properly reads from stdin using json.load(sys.stdin)

**Tags:** `python`, `validation`, `stdin`, `input`, `static-analysis`

---

### call_tool() Usage Validator

**File:** `call_tool_validator.yaml`  
**Type:** `executable`  

Validates that call_tool() is used correctly with proper arguments (tool_name, prompt)

**Tags:** `python`, `validation`, `call_tool`, `node_runtime`, `static-analysis`

---

## EXECUTABLE

**108 tools** - General-purpose executable tools for code generation and manipulation

### API Wrapper Generator

**File:** `api_wrapper_generator.yaml`  
**Type:** `executable`  

Generates a Flask API wrapper script for any tool or workflow, creating REST endpoints for tool invocation

**Tags:** `api`, `flask`, `rest`, `wrapper`, `code-generation`, `web-service`

---

### Adaptive Document Chunker

**File:** `adaptive_chunker.yaml`  
**Type:** `executable`  

Intelligently chunks documents based on model context windows and summarization tier. Adapts chunk size to fit different model capabilities with overlap for context preservation.

**Tags:** `chunking`, `document-processing`, `summarization`, `context-aware`, `adaptive`

---

### Autoflake Checker

**File:** `autoflake_checker.yaml`  
**Type:** `executable`  

Removes unused imports and unused variables from Python code. Deterministic and fast cleanup tool.

**Tags:** `python`, `cleanup`, `imports`, `static-analysis`, `autoflake`, `deterministic`, `auto-fix`

---

### Bandit Security Scanner

**File:** `bandit_security.yaml`  
**Type:** `executable`  

Runs bandit security scanner to find common security issues in Python code

**Tags:** `python`, `security`, `vulnerability`, `scanning`

---

### Basic Calculator

**File:** `basic_calculator.yaml`  
**Type:** `executable`  

Fast arithmetic operations (add, subtract, multiply, divide, power, modulo). Direct Python execution - no LLM needed. Use for simple math.

**Tags:** `math`, `arithmetic`, `calculator`, `fast`, `deterministic`

---

### Behave BDD Test Generator

**File:** `behave_test_generator.yaml`  
**Type:** `executable`  

Generate Behave BDD tests with step definitions from Gherkin feature files, tool specs, or workflow definitions with plausible test data

**Tags:** `testing`, `bdd`, `behave`, `test-generation`, `gherkin`, `acceptance-testing`, `behavior-driven`, `characterization`

---

### Black Code Formatter

**File:** `black_formatter.yaml`  
**Type:** `executable`  

Runs black formatter to check if Python code follows black style (with --check flag)

**Tags:** `python`, `formatting`, `style`, `black`

---

### Buffer

**File:** `buffer.yaml`  
**Type:** `executable`  

Buffers data to smooth fast traffic. Batches items and flushes based on size, time, or manual trigger. Perfect for smoothing rapid usage tracking updates to Qdrant or rate-limiting API calls.

**Tags:** `buffer`, `batching`, `rate-limiting`, `smoothing`, `traffic-control`

---

### BugCatcher Exception Monitor

**File:** `bugcatcher.yaml`  
**Type:** `executable`  

Global exception monitoring tool that watches for exceptions and logs them to Loki

---

### Bulk Data Store

**File:** `bulk_data_store.yaml`  
**Type:** `executable`  

High-level bulk data storage tool using Postgres for storing detailed logs, bug histories, tool ancestry, performance data, and generated tools. Complements RAG by storing detailed bulk data while RAG handles semantic search.

**Tags:** `database`, `storage`, `bulk-data`, `logs`, `bugs`, `ancestry`, `history`

---

### Check Tool Duplicate

**File:** `check_tool_duplicate.yaml`  
**Type:** `executable`  

Searches for semantically similar tools to avoid creating duplicates. Prevents tool proliferation by finding existing tools that match the functionality.

**Tags:** `deduplication`, `tool-search`, `semantic-similarity`, `meta-programming`

---

### Circular Import Fixer

**File:** `circular_import_fixer.yaml`  
**Type:** `executable`  

Detects and automatically fixes circular import errors in generated Python code.

Common pattern fixed:
- main.py containing "from main import ..." (circular import)
- This happens when the LLM copies test file imports into the main code

Usage:
  echo '{"code": "<python_code>", "filename": "main.py"}' | python circular_import_fixer.py

Returns:
  - fixed: true/false
  - removed_imports: list of removed import lines
  - fixed_code: cleaned code
  - message: summary of what was fixed


**Tags:** `fix`, `error_handler`, `circular_import`, `import_error`, `code_repair`, `auto_fix`, `tdd`, `code_generation`

---

### Config File Generator

**File:** `config_file_generator.yaml`  
**Type:** `executable`  

Generates comprehensive config.yaml files with sensible Ollama defaults (gemma3_1b, llama3), detailed documentation, and instructions for changing settings. Supports both Docker and standalone modes.

**Tags:** `configuration`, `config`, `yaml`, `ollama`, `settings`, `documentation`

---

### Connect SignalR (Natural Language)

**File:** `connect_signalr.yaml`  
**Type:** `executable`  

Simple natural language interface to connect to SignalR hubs. Just say what you want in plain English and it will parse your request, connect to the hub, and automatically create workflows from streaming tasks. Sequential processing - one task at a time.

**Tags:** `signalr`, `natural-language`, `streaming`, `realtime`, `workflow-generation`, `training`, `easy`

---

### Content Splitter

**File:** `content_splitter.yaml`  
**Type:** `executable`  

Splits large content into chunks for progressive summarization.

Strategies:
- paragraph: Split on paragraph boundaries (default)
- sentence: Split on sentence boundaries (more granular)
- fixed: Fixed-size chunks (simple, may break sentences)

Respects max chunk size while maintaining readability.


**Tags:** `content_processing`, `splitting`, `chunking`, `summarization`, `utility`

---

### Contract Validator

**File:** `validate_contract.yaml`  
**Type:** `executable`  

Validates generated code against a specified contract.
Returns compliance report with violations and suggestions.

Use this tool after code generation to ensure the code meets
organizational standards for logging, structure, libraries, etc.


**Tags:** `validation`, `contracts`, `quality`, `compliance`

---

### Create Behave Spec

**File:** `create_behave_spec.yaml`  
**Type:** `executable`  

Create a Behave BDD specification file for RAG storage and future test generation

**Tags:** `testing`, `spec-creation`, `behave`, `bdd`, `rag`

---

### Create Locust Spec

**File:** `create_locust_spec.yaml`  
**Type:** `executable`  

Create a Locust load test specification file for RAG storage and future test generation

**Tags:** `testing`, `spec-creation`, `locust`, `performance`, `rag`

---

### Dependency Analyzer

**File:** `dependency_analyzer.yaml`  
**Type:** `executable`  

Analyzes tool dependencies using RAG and metadata for tree shaking. Recursively resolves all required tools, files, and packages to create minimal deployments.

**Tags:** `dependencies`, `tree-shaking`, `optimization`, `analysis`, `packaging`, `deployment`

---

### Docker Compose Generator

**File:** `docker_compose_generator.yaml`  
**Type:** `executable`  

Generates docker-compose.yml configuration for containerized tool API wrappers

**Tags:** `docker`, `docker-compose`, `orchestration`, `containerization`, `devops`

---

### Docker Helper Scripts Generator

**File:** `docker_helper_scripts_generator.yaml`  
**Type:** `executable`  

Generates helper scripts (build.sh, run.sh, test.sh, stop.sh) for Docker packages

**Tags:** `docker`, `scripts`, `automation`, `devops`, `helpers`

---

### Document Store

**File:** `document_store.yaml`  
**Type:** `executable`  

In-memory document store for summarization workflows. Stores and retrieves documents with metadata.

**Tags:** `storage`, `memory`, `document-management`, `summarization`, `workflow`

---

### Document Workflow

**File:** `document_workflow.yaml`  
**Type:** `executable`  

Generates comprehensive 'How to Use' documentation for a workflow and saves it to README.txt in the workflow directory. Analyzes the code, detects inputs/outputs, identifies tool calls, and creates detailed documentation with examples, flowcharts, and usage instructions.

**Tags:** `documentation`, `workflow`, `readme`, `generator`, `automation`, `metadata`

---

### Environment File Generator

**File:** `env_file_generator.yaml`  
**Type:** `executable`  

Generates .env and .env.example files with complete configuration documentation for Docker containers

**Tags:** `environment`, `configuration`, `docker`, `dotenv`, `settings`

---

### Evolve Tool

**File:** `evolve_tool.yaml`  
**Type:** `executable`  

Evolves a failing tool by regenerating it with fixes and mutations. Creates a promoted version for the current workflow.

**Tags:** `evolution`, `tool-mutation`, `code-generation`, `self-improvement`

---

### Extract Spec From File

**File:** `extract_spec_from_file.yaml`  
**Type:** `executable`  

Extracts specifications from text files for overseer planning. Handles large files by summarizing and sectioning.

**Tags:** `spec`, `file`, `extraction`, `overseer`, `planning`

---

### Extract Text Content

**File:** `extract_text_content.yaml`  
**Type:** `executable`  

Extracts structured text content from documents. Parses into paragraphs, sentences, and sections. Handles various text formats with comprehensive error handling.

**Tags:** `text-extraction`, `parsing`, `nlp`, `summarization`, `document-processing`

---

### Fake Data Generator

**File:** `fake_data_generator.yaml`  
**Type:** `executable`  

Generates realistic fake data using Faker library for API testing and data simulation

**Tags:** `testing`, `data-generation`, `faker`, `api-testing`, `mock-data`

---

### Find Code Fix Pattern

**File:** `find_code_fix_pattern.yaml`  
**Type:** `executable`  

Pattern Recognizer with RAG Data Store - Searches for similar code errors and suggests proven fixes.

Uses a shared RAG-based pattern data store to find code fix patterns that have been successfully
applied in the past. Returns multiple solutions ranked by usage count (proven effectiveness) and
semantic similarity. The data store scope can be configured to search:
- Only patterns from the current tool
- Patterns from the current tool and its sub-tools
- All patterns across the entire tool hierarchy


**Tags:** `learning`, `code-fix`, `pattern-search`, `error-recovery`, `self-improvement`, `rag`, `data-store`, `pattern-recognizer`

---

### HTTP REST Client

**File:** `http_rest_client.yaml`  
**Type:** `executable`  

Standard REST API client with automatic JSON parsing. Supports GET, POST, PUT, PATCH, DELETE methods with JSON request/response handling.

**Tags:** `http`, `rest`, `api`, `json`, `web`, `client`, `request`

---

### HTTP Raw Client

**File:** `http_raw_client.yaml`  
**Type:** `executable`  

Raw HTTP client that returns content as string without parsing. Perfect for HTML, text files, binary data, or any non-JSON content.

**Tags:** `http`, `raw`, `html`, `scraping`, `binary`, `text`, `client`

---

### Incremental Summarizer

**File:** `incremental_summarizer.yaml`  
**Type:** `executable`  

Incrementally summarizes documents chunk-by-chunk. Builds summary by feeding previous summary + next chunk to LLM, adapting to different context windows.

**Tags:** `summarization`, `incremental`, `document-processing`, `workflow`, `orchestration`

---

### Inline Tool

**File:** `inline_tool.yaml`  
**Type:** `executable`  

Bakes tool code directly into workflow scripts with version tracking. Enables enterprise reproducibility by embedding dependencies with RAG references.

**Tags:** `enterprise`, `reproducibility`, `deployment`, `dependency-management`

---

### Install Python Package

**File:** `pip_install.yaml`  
**Type:** `executable`  

Installs Python packages using pip. Use when code requires external dependencies like requests, numpy, pandas, etc. Can install single packages or multiple packages at once. Supports version specifications (e.g., 'requests>=2.28.0'). Essential for code that imports third-party libraries.

**Tags:** `dependencies`, `pip`, `install`, `packages`, `requirements`, `setup`

---

### Internal Test Validator

**File:** `internal_test_validator.yaml`  
**Type:** `executable`  

Internal tool for validating test outputs. Usage tracking disabled since this is internal tooling.

**Tags:** `internal`, `testing`, `validation`, `no-tracking`

---

### Isort Import Checker

**File:** `isort_import_checker.yaml`  
**Type:** `executable`  

Checks if Python imports are sorted correctly

**Tags:** `python`, `imports`, `style`, `organization`

---

### JSON Output Validator

**File:** `json_output_validator.yaml`  
**Type:** `executable`  

Validates that node code outputs valid JSON using json.dumps() and print()

**Tags:** `python`, `json`, `validation`, `output`, `static-analysis`

---

### LLMApi Health Check

**File:** `llmapi_health_check.yaml`  
**Type:** `executable`  

Check if LLMApi test data simulator is running and available

**Tags:** `health-check`, `llmapi`, `testing`, `infrastructure`

---

### Language Detector

**File:** `language_detector.yaml`  
**Type:** `executable`  

Detects the language of text content using multiple methods: NMT API (fast, accurate), heuristic patterns (fast, moderate accuracy), or LLM fallback (slower, high accuracy). Automatically tries NMT first, then falls back to heuristics or LLM.

**Tags:** `language`, `detection`, `nlp`, `i18n`, `localization`, `nmt`, `analysis`

---

### Load Document

**File:** `load_document.yaml`  
**Type:** `executable`  

Loads a text document from disk and stores it in the document store for summarization workflows. Extracts metadata and validates content.

**Tags:** `file-io`, `load`, `document-loading`, `summarization`, `workflow`

---

### Load from Disk

**File:** `load_from_disk.yaml`  
**Type:** `executable`  

Loads content from any file path on disk. Use for reading specifications, code, documentation, or configuration files. Can read from anywhere on the filesystem (not restricted to ./output/). Useful for self-optimization tasks where the system reads its own code.

**Tags:** `file-io`, `load`, `read`, `disk`, `input`

---

### Locust Load Test Generator

**File:** `locust_load_tester.yaml`  
**Type:** `executable`  

Generate and execute Locust performance/load tests from API specs, OpenAPI definitions, or BDD scenarios with plausible test data

**Tags:** `testing`, `load-testing`, `performance`, `locust`, `api-testing`, `stress-testing`, `benchmarking`, `characterization`

---

### Loki Log Aggregation

**File:** `loki.yaml`  
**Type:** `executable`  

Manages Grafana Loki instance for log aggregation and monitoring (tool/global scope)

---

### Main Function Checker

**File:** `main_function_checker.yaml`  
**Type:** `executable`  

Validates that node code has a proper main() function and __main__ block

**Tags:** `python`, `structure`, `validation`, `main`, `static-analysis`

---

### Mark Tool Failure

**File:** `mark_tool_failure.yaml`  
**Type:** `executable`  

Records tool failures for specific scenarios, enabling demotion in search rankings and tag refinement. Helps the system learn which tools work where.

**Tags:** `failure-tracking`, `tool-quality`, `demotion`, `learning`, `internal`

---

### ModuleNotFoundError Fixer

**File:** `module_not_found_fixer.yaml`  
**Type:** `executable`  

Fixes ModuleNotFoundError by adding sys.path setup before imports.

This tool has ENCAPSULATED validation:
- fix() method: Applies the fix to the code
- validate() method: Validates the fix was actually applied

Common patterns handled:
- Adds path setup (sys.path.insert) before imports
- Removes unused imports that cause the error
- Validates all changes are actually in the fixed code


**Tags:** `fix`, `error_handler`, `module_error`, `import_error`, `auto_fix`, `tdd`, `validated`

---

### MyPy Type Checker

**File:** `mypy_type_checker.yaml`  
**Type:** `executable`  

Runs mypy type checking on Python code to find type errors before runtime

**Tags:** `python`, `type-checking`, `static-analysis`, `types`

---

### NMT Translator

**File:** `nmt_translate.yaml`  
**Type:** `executable`  

Fast neural machine translation using the NMT service at localhost:8000. Supports many languages. Use format: 'Translate to <language>: <text>' or 'Translate from <src> to <tgt>: <text>'

**Tags:** `translation`, `nmt`, `neural`, `languages`, `fast`, `api`

---

### Node Runtime Import Validator

**File:** `node_runtime_import_validator.yaml`  
**Type:** `executable`  

Validates that node_runtime imports come AFTER sys.path.insert() setup to prevent ModuleNotFoundError

**Tags:** `python`, `imports`, `validation`, `node_runtime`, `static-analysis`, `auto-fix`

---

### Optimize Cluster

**File:** `optimize_cluster.yaml`  
**Type:** `executable`  

Optimize RAG artifact clusters using iterative self-optimization loop. Can optimize specific workflows, functions, prompts, or entire node types. Supports conversational usage: 'optimize this workflow' or CLI: '/optimize workflow_name'

---

### Package Recovery Tool

**File:** `package_recovery_tool.yaml`  
**Type:** `executable`  

Automatically detects missing packages from error messages and installs them. Supports Python packages (via pip) and system commands (via apt). Enables self-healing workflows.

**Tags:** `recovery`, `dependencies`, `error-handling`, `self-healing`, `package-management`, `resilience`

---

### Parse Static Analysis Results

**File:** `parse_static_analysis.yaml`  
**Type:** `executable`  

Parse and aggregate static analysis results for test data generation and tool optimization

**Tags:** `analysis`, `static-analysis`, `parsing`, `quality-metrics`, `test-data`, `optimization`

---

### Pin Tool Version

**File:** `pin_tool_version.yaml`  
**Type:** `executable`  

Locks a workflow to specific tool versions. Pinned versions are protected from trimming and can be inlined into workflow scripts for enterprise reproducibility.

**Tags:** `enterprise`, `version-control`, `dependency-management`, `workflow`

---

### Platform Information

**File:** `platform_info.yaml`  
**Type:** `executable`  

Gathers comprehensive information about the underlying platform including OS, CPU, GPU, memory, disk, processes, and network. Enables decision-making based on platform characteristics like 'when running with low memory' or 'when running on Windows'. Supports multiple detail levels from basic to full.

**Tags:** `platform`, `system`, `info`, `monitoring`, `cpu`, `gpu`, `memory`, `diagnostic`, `conditional`

---

### Postgres Client

**File:** `postgres_client.yaml`  
**Type:** `executable`  

PostgreSQL database client for executing queries, managing connections, and performing bulk data operations. Provides connection pooling and transaction management.

**Tags:** `database`, `postgres`, `sql`, `storage`, `data`

---

### PyInstrument Profiler

**File:** `pyinstrument_profiler.yaml`  
**Type:** `executable`  

Performance profiling using PyInstrument - provides detailed call stack analysis, line-level timing, and performance bottleneck identification. Generates text, HTML, and JSON reports for optimization analysis.

**Tags:** `python`, `profiling`, `performance`, `optimization`, `pyinstrument`

---

### Pydocstyle Docstring Checker

**File:** `pydocstyle_checker.yaml`  
**Type:** `executable`  

Checks docstring style and completeness according to PEP 257

**Tags:** `python`, `documentation`, `docstrings`, `pep257`

---

### Pynguin Test Generator

**File:** `pynguin_config.yaml`  
**Type:** `executable`  

Automatically generates unit tests using evolutionary algorithms. Windows-compatible configuration.

**Tags:** `testing`, `test-generation`, `pynguin`, `automated`, `windows`, `python`

---

### Pynguin Test Generator

**File:** `pynguin_test_generator.yaml`  
**Type:** `executable`  

Fast automated unit test generation using Pynguin's evolutionary algorithm. Generates high-coverage pytest tests automatically from source code.

**Tags:** `testing`, `test-generation`, `unit-tests`, `pytest`, `coverage`, `fast`, `automated`, `pynguin`, `evolutionary`, `first-line-defense`

---

### Pytest Test Runner

**File:** `pytest_runner.yaml`  
**Type:** `executable`  

Runs pytest unit tests with coverage reporting

**Tags:** `python`, `testing`, `pytest`, `unit-tests`

---

### Pytest with Coverage

**File:** `pytest_coverage.yaml`  
**Type:** `executable`  

Runs pytest with code coverage analysis

**Tags:** `python`, `testing`, `coverage`, `pytest`

---

### Python Syntax Validator

**File:** `python_syntax_validator.yaml`  
**Type:** `executable`  

Fast syntax check using Python's AST parser - catches syntax errors before expensive LLM tools

**Tags:** `python`, `syntax`, `validation`, `static-analysis`, `fast`

---

### Pyupgrade Checker

**File:** `pyupgrade_checker.yaml`  
**Type:** `executable`  

Automatically upgrades Python syntax for newer versions. Modernizes code with f-strings, type hints, and newer Python features.

**Tags:** `python`, `modernization`, `syntax`, `static-analysis`, `pyupgrade`, `deterministic`, `auto-fix`

---

### Radon Complexity Analyzer

**File:** `radon_complexity.yaml`  
**Type:** `executable`  

Analyzes code complexity metrics (cyclomatic complexity, maintainability index)

**Tags:** `python`, `complexity`, `metrics`, `maintainability`

---

### Random Test Data Generator

**File:** `random_data_generator.yaml`  
**Type:** `executable`  

Generates random test data for workflows based on schemas or natural language descriptions. Context-aware for common fields like email, name, age, translation text, etc. Use this when you need test data to validate workflows.

**Tags:** `testing`, `data`, `random`, `generator`, `workflow`, `validation`

---

### Remove Unused node_runtime Import

**File:** `remove_unused_node_runtime_import.yaml`  
**Type:** `executable`  

Detects and removes unused 'from node_runtime import call_tool' imports and related
path setup code when call_tool is not actually used in the code.

This fixes the common error where generated code imports node_runtime but never calls
any tools, causing ModuleNotFoundError in tests.

The tool:
- Checks if call_tool() is actually called in the code
- If NOT used, removes:
  * from node_runtime import call_tool
  * from pathlib import Path (if only for node_runtime)
  * sys.path.insert(...) for node_runtime
  * import logging (if only added by repair system)
  * logging.basicConfig(...)
  * logging.debug(...) calls
  * try/except wrappers added by repair system
- If used, keeps everything intact


**Tags:** `code-cleanup`, `import`, `node_runtime`, `unused`, `static-analysis`, `autofix`

---

### Resilient Tool Call

**File:** `resilient_tool_call.yaml`  
**Type:** `executable`  

Self-recovering tool execution. Automatically tries alternative tools when one fails, marking failures and learning from them. Fulfills the prompt at all costs.

**Tags:** `resilience`, `fallback`, `auto-recovery`, `tool-selection`, `internal`

---

### Ruff Checker

**File:** `ruff_checker.yaml`  
**Type:** `executable`  

Fast Python linter and formatter. Replaces flake8, isort, pyupgrade, and more. Checks code quality and applies safe auto-fixes.

**Tags:** `python`, `linting`, `formatting`, `static-analysis`, `ruff`, `deterministic`, `auto-fix`, `fast`

---

### SSE Stream Producer

**File:** `sse_stream.yaml`  
**Type:** `stream_producer`  

Connects to a Server-Sent Events (SSE) endpoint and streams data continuously. Simpler and more reliable than WebSocket for one-way streaming.

**Tags:** `sse`, `server-sent-events`, `stream`, `real-time`, `producer`, `http`

---

### Save to Disk

**File:** `save_to_disk.yaml`  
**Type:** `executable`  

Saves content to a file in the tool_content/<datetime>/ directory. For safety and organization, ALL content is saved to timestamped directories under tool_content/. This ensures outputs are organized, safe from overwrites, and easy to find.

**Tags:** `file-io`, `save`, `write`, `disk`, `output`, `storage`

---

### Selective File Copier

**File:** `selective_file_copier.yaml`  
**Type:** `executable`  

Copies only required files based on dependency analysis for tree-shaken deployments. Maintains directory structure and creates Python package init files.

**Tags:** `file-operations`, `tree-shaking`, `optimization`, `deployment`, `packaging`

---

### SignalR Hub Connector

**File:** `signalr_hub_connector.yaml`  
**Type:** `executable`  

Connects to a SignalR hub to receive streaming task data. Automatically routes received tasks to the workflow generator for training. Supports real-time task processing and automatic workflow creation from hub messages.

**Tags:** `signalr`, `streaming`, `realtime`, `integration`, `hub`, `websocket`, `training`

---

### SignalR LLMApi Skill

**File:** `signalr_llmapi_skill.yaml`  
**Type:** `executable`  

Complete skill for interacting with LLMApi SignalR simulator. Manages contexts, controls streaming, and executes SSE streams. This orchestrates calls to signalr_llmapi_management (planning) and sse_stream (streaming).

**Tags:** `signalr`, `llmapi`, `stream`, `skill`, `orchestrator`, `executable`

---

### SignalR Tool Trigger

**File:** `signalr_tool_trigger.yaml`  
**Type:** `executable`  

Listens to SignalR endpoint and dynamically triggers tools based on incoming messages. Supports direct tool invocation, workflow generation, and dynamic tool creation from API specs.

**Tags:** `signalr`, `realtime`, `integration`, `dynamic`, `tool-trigger`, `workflow-generation`

---

### SignalR WebSocket Stream

**File:** `signalr_websocket_stream.yaml`  
**Type:** `stream_producer`  

Connects to a SignalR hub via WebSocket and streams data continuously. Subscribes to a specific hub context/method and yields each message received.

**Tags:** `signalr`, `websocket`, `stream`, `real-time`, `producer`

---

### Smart API Parser

**File:** `smart_api_parser.yaml`  
**Type:** `executable`  

Intelligently parses OpenAPI specs, generates realistic test data, and tests all endpoints. Can use Faker or LLM for data generation.

**Tags:** `api-testing`, `openapi`, `swagger`, `testing`, `data-generation`, `integration-testing`

---

### Smart Faker

**File:** `smart_faker.yaml`  
**Type:** `executable`  

Intelligent fake data generator that accepts plain English, code, JSON schemas, or any LLM-interpretable input. Supports multiple output formats including streaming, arrays, and CSV.

**Tags:** `testing`, `data-generation`, `faker`, `llm`, `flexible`, `smart`, `csv`, `streaming`

---

### Standalone Executable Compiler

**File:** `standalone_exe_compiler.yaml`  
**Type:** `executable`  

Compiles tools/workflows into standalone executables (.exe, .app) using PyInstaller. Generates wrapper script, spec file, and build instructions

**Tags:** `compiler`, `executable`, `pyinstaller`, `standalone`, `packaging`, `distribution`

---

### Static Analysis Runner

**File:** `run_static_analysis.yaml`  
**Type:** `executable`  

Runs all static validators on generated code and reports results. Can run all validators or specific ones. Supports auto-fix and retry-failed modes.

**Tags:** `python`, `validation`, `static-analysis`, `testing`, `quality`, `comprehensive`

---

### Stdin Usage Validator

**File:** `stdin_usage_validator.yaml`  
**Type:** `executable`  

Validates that node code properly reads from stdin using json.load(sys.stdin)

**Tags:** `python`, `validation`, `stdin`, `input`, `static-analysis`

---

### Store Code Fix Pattern

**File:** `store_code_fix_pattern.yaml`  
**Type:** `executable`  

Pattern Recognizer with RAG Data Store - Stores code breaks and their fixes as reusable patterns.

Stores code fix patterns in a shared RAG-based data store for future retrieval. Each pattern
includes the error, broken code, fixed code, and context. Patterns are tagged and embedded
for semantic search. The data store scope determines visibility:
- Store patterns at tool level (tool-specific learning)
- Store patterns at tool+subtools level (hierarchical learning)
- Store patterns at hierarchy level (contextual learning)
- Store patterns globally (universal learning)


**Tags:** `learning`, `code-fix`, `pattern-storage`, `error-recovery`, `self-improvement`, `rag`, `data-store`, `pattern-recognizer`

---

### Stream Processor

**File:** `stream_processor.yaml`  
**Type:** `stream_consumer`  

Generic stream processor that connects a stream producer to a consumer tool. Handles filtering, transformation, and routing of stream events.

**Tags:** `stream`, `processor`, `consumer`, `filter`, `transform`, `orchestrator`

---

### Style Extractor

**File:** `style_extractor.yaml`  
**Type:** `executable`  

Extracts comprehensive style information from any source (web pages, files, text) with multi-tier analysis. Analyzes writing style, tone, vocabulary, structure, and formatting patterns to generate detailed JSON profiles. Similar to langextract but for style analysis.

**Tags:** `style`, `analysis`, `extraction`, `nlp`, `content-analysis`, `writing`, `language`, `web-scraping`, `file-processing`

---

### Summarize Document

**File:** `summarize_document.yaml`  
**Type:** `executable`  

Complete document summarization workflow. Loads document, extracts content, chunks adaptively, and generates incremental summary. Auto-adapts to different model context windows.

**Tags:** `summarization`, `workflow`, `document-processing`, `orchestration`, `end-to-end`

---

### Text Formatter

**File:** `text_formatter.yaml`  
**Type:** `executable`  

Fast text formatting operations (uppercase, lowercase, title case, reverse, trim, etc.). Direct Python execution - instant results.

**Tags:** `text`, `formatting`, `string`, `fast`, `deterministic`

---

### Tool Mutator

**File:** `mutate_tool.yaml`  
**Type:** `executable`  

CLI for prompt mutation management. Enables on-demand mutation of LLM tools with overseer consultation. Treats LLM tools like code - enables mutation and specialization for specific use cases.

**Tags:** `mutation`, `prompt-engineering`, `tool-evolution`, `specialization`, `cli`

---

### Tool-Scoped Filesystem

**File:** `filesystem.yaml`  
**Type:** `executable`  

Isolated filesystem operations for tool-scoped data storage with automatic directory management

---

### Trim Tool Versions

**File:** `trim_tool_versions.yaml`  
**Type:** `executable`  

Keeps tools tidy by retaining only recent versions (2-3 back) plus original. Archives or deletes old versions for rollback capability.

**Tags:** `maintenance`, `version-control`, `cleanup`, `storage-optimization`

---

### Undefined Name Checker

**File:** `undefined_name_checker.yaml`  
**Type:** `executable`  

Fast check for undefined variables/imports using flake8 (F821 errors)

**Tags:** `python`, `validation`, `imports`, `static-analysis`, `undefined`

---

### Unit Converter

**File:** `unit_converter.yaml`  
**Type:** `executable`  

Fast unit conversions (length, weight, temperature, time). Direct Python execution. Supports common units like meters/feet, kg/lbs, celsius/fahrenheit, etc.

**Tags:** `conversion`, `units`, `measurement`, `fast`, `deterministic`

---

### Vulture Dead Code Finder

**File:** `vulture_deadcode.yaml`  
**Type:** `executable`  

Finds unused code (dead code) in Python projects

**Tags:** `python`, `dead-code`, `optimization`, `cleanup`

---

### Workflow Datastore

**File:** `workflow_datastore.yaml`  
**Type:** `executable`  

Save and retrieve workflow data persistently. Allows workflows to store project schedules, task lists, and other structured data.

**Tags:** `workflow`, `datastore`, `persistence`, `storage`, `state`

---

### Workflow Diagram Generator

**File:** `workflow_diagram.yaml`  
**Type:** `executable`  

Generates visual workflow diagrams showing tool flow and decisions.

Creates beautiful Mermaid diagrams or ASCII art showing:
- Tool dependencies and flow
- Decision points and conditions
- Tool types (LLM, executable, workflow)
- Complete workflow visualization

Perfect for understanding complex workflows at a glance.


**Tags:** `visualization`, `workflow`, `diagram`, `documentation`, `mermaid`, `ascii`

---

### Workflow Runner

**File:** `workflow_runner.yaml`  
**Type:** `executable`  

Generates a combined Python script from a workflow with all dependencies inlined.
The goal is to reduce the workflow to JUST the required code with all imports properly resolved.
Analyzes workflow steps, extracts tool implementations, and generates a standalone script.


**Tags:** `workflow`, `code-generation`, `dependency-resolution`, `inline`, `standalone`

---

### call_tool() Usage Validator

**File:** `call_tool_validator.yaml`  
**Type:** `executable`  

Validates that call_tool() is used correctly with proper arguments (tool_name, prompt)

**Tags:** `python`, `validation`, `call_tool`, `node_runtime`, `static-analysis`

---

### conversation_manager

**File:** `conversation_manager.yaml`  
**Type:** `executable`  

Manages intelligent conversations with multi-chat context memory, auto-summarization,
and semantic search. Provides context-aware conversations that optimize for response
speed while maintaining accuracy.

Features:
- Multi-chat context memory (remembers previous conversations)
- Auto-summarization based on context window size
- Volatile Qdrant storage for semantic search
- Related context retrieval from past conversations
- Performance tracking (response time, tokens, etc.)
- Intent detection (distinguishes conversation from dialogue generation)

Use this tool for:
- Starting/ending conversational sessions
- Managing conversation context
- Detecting user intent to converse
- Retrieving related conversation history


**Tags:** `conversation`, `context-memory`, `semantic-search`, `summarization`, `intent-detection`, `qdrant`

---

### cron_deconstructor

**File:** `cron_deconstructor.yaml`  
**Type:** `executable`  

Deconstructs cron expressions into rich structured metadata for semantic embedding.

This tool analyzes a cron expression and generates detailed metadata including:
- Human-readable description
- Frequency classification (daily, weekly, monthly, etc.)
- Time of day categorization (morning, afternoon, evening, night)
- Day names (Monday, Tuesday, etc.)
- Next scheduled run times
- Semantic tags for RAG embedding
- Inferred task grouping (reports, backups, monitoring, etc.)

The structured output is designed to be embedded in RAG storage for better
semantic search and grouping of scheduled tasks.


---

### cron_querier

**File:** `cron_querier.yaml`  
**Type:** `executable`  

Converts natural language queries about scheduled tasks into structured search filters.

This tool enables intuitive querying of scheduled tasks using plain English instead
of complex filter syntax. It parses queries to extract:
- Task groups (reports, backups, monitoring, etc.)
- Frequency (daily, weekly, hourly, etc.)
- Time windows ("next 3 hours", "tonight", "tomorrow")
- Time of day (morning, afternoon, evening, night)
- Day names (Monday, Tuesday, etc.)

The structured output can be used directly with the task search system.


---

### duplicate_style

**File:** `duplicate_style.yaml`  
**Type:** `executable`  

Analyzes writing style from a directory of content and creates a comprehensive
style guide. Uses tiered summarization to efficiently process large amounts of content.

Features:
- Recursive directory scanning with smart file filtering
- Tiered LLM selection based on content size (gemma2:2b, llama3, mistral-nemo)
- Context-aware chunking and progressive summarization
- Incremental style analysis that builds understanding across files
- Optional review and refinement for higher quality output

Use cases:
- Extract writing style from documentation to replicate in new docs
- Analyze code comment style for consistency
- Create style guides from existing content
- Understand voice and tone patterns


**Tags:** `style-analysis`, `documentation`, `content-analysis`, `summarization`

---

### fix_attribute_error

**File:** `fix_attribute_error.yaml`  
**Type:** `executable`  

Detects and fixes Python AttributeError.

Handles:
- Missing attributes on objects
- Typos in attribute names
- Wrong object type
- None object attribute access
- Method vs property confusion

Uses RAG to learn from past fixes and suggest corrections.


**Tags:** `fix`, `attribute-error`, `typo`, `none-check`, `fuzzy-match`, `auto-fix`

---

### fix_indentation_error

**File:** `fix_indentation_error.yaml`  
**Type:** `executable`  

Detects and fixes Python indentation errors.

Handles:
- Inconsistent indentation (tabs vs spaces)
- Unexpected indent
- Expected indent
- Unindent does not match
- Mixed indentation styles

Automatically normalizes indentation to 4 spaces (PEP 8).


**Tags:** `fix`, `indentation`, `whitespace`, `pep8`, `auto-fix`

---

### fix_missing_main_call

**File:** `fix_missing_main_call.yaml`  
**Type:** `executable`  

Detects and fixes missing 'if __name__ == "__main__": main()' call.

Handles:
- Code with main() function but no execution
- Missing if __name__ guard
- Code that produces no output due to main() not being called

This is a critical fix for tools that define main() but never execute it,
resulting in "NO OUTPUT WAS PRODUCED" errors.


**Tags:** `fix`, `main-call`, `no-output`, `execution`, `auto-fix`

---

### fix_missing_pip_packages

**File:** `fix_missing_pip_packages.yaml`  
**Type:** `executable`  

Detects and fixes missing pip package errors (ModuleNotFoundError).

Automatically maps module names to pip packages (e.g., bs4 → beautifulsoup4)
and installs missing dependencies.

Features:
- Detects ModuleNotFoundError from test/execution output
- Maps common module → package names (bs4, cv2, PIL, etc.)
- Automatically installs missing packages
- Verifies installation succeeded
- Returns list of installed packages

Use cases:
- Auto-fix "No module named 'bs4'" errors
- Handle missing dependencies in generated code
- Ensure all imports are available before running tests


**Tags:** `fix`, `pip`, `packages`, `dependencies`, `import`, `auto-fix`

---

### fix_name_error

**File:** `fix_name_error.yaml`  
**Type:** `executable`  

Detects and fixes Python NameError (undefined variables/functions).

Handles:
- Undefined variables
- Typos in variable names
- Missing imports
- Scope issues
- Function name typos

Uses fuzzy matching and RAG search to suggest corrections.


**Tags:** `fix`, `name-error`, `undefined`, `typo`, `fuzzy-match`, `auto-fix`

---

### fix_syntax_error

**File:** `fix_syntax_error.yaml`  
**Type:** `executable`  

Detects and fixes Python syntax errors in code.

Uses AST parsing and pattern matching to identify and correct:
- Missing colons after if/for/while/def/class
- Mismatched parentheses, brackets, braces
- Invalid operators or keywords
- Missing commas in lists/dicts/tuples
- Incorrect string quotes

Stores successful fixes in RAG as CODE_FIX artifacts for future reference.


**Tags:** `fix`, `syntax`, `parser`, `ast`, `auto-fix`

---

### fix_type_error

**File:** `fix_type_error.yaml`  
**Type:** `executable`  

Detects and fixes Python type errors.

Handles:
- Type mismatches (string vs int, etc.)
- Unsupported operations between types
- None type errors
- Attribute errors on wrong types
- Iteration over non-iterables

Searches RAG for similar fixes before applying new solutions.


**Tags:** `fix`, `type-error`, `type-checking`, `auto-fix`, `rag-search`

---

### schedule_task

**File:** `schedule_task.yaml`  
**Type:** `executable`  

Schedule a task to run at specific times using cron expressions or natural language descriptions.

This tool is IMMUTABLE - scheduled tasks persist across sessions and run automatically
in the background. Use this for polling events, periodic checks, or recurring operations.

Examples:
- "Check for new emails every 5 minutes"
- "Generate report every Sunday at noon"
- "Backup data daily at 2am"

The scheduler uses low priority execution to avoid interfering with active workflows.


---

### write_markdown_doc

**File:** `write_markdown_doc.yaml`  
**Type:** `executable`  

Generates well-formatted markdown documentation with optional style matching.
Uses tiered LLM selection for optimal quality/speed balance.

Features:
- Smart LLM tier selection (gemma2:2b for quick, llama3 for balanced, mistral-nemo for high-quality)
- Optional style guide matching (works with output from duplicate_style)
- Review and refinement capability for higher quality
- Proper markdown formatting with validation
- Configurable length (short ~500 words, medium ~1500 words, long ~3000 words)
- Security guardrails (enforces output only to 'output/' directory)

Security:
- All output paths are validated to be under output/ directory
- Cannot escape with ../ or absolute paths
- Only .md files allowed

Use cases:
- Generate documentation matching existing style
- Create technical articles and guides
- Write README files and tutorials
- Generate API documentation


**Tags:** `documentation`, `markdown`, `content-generation`, `style-matching`

---

## FIXER

**4 tools** - Automatic code fixing and error correction tools

### Circular Import Fixer

**File:** `circular_import_fixer.yaml`  
**Type:** `executable`  

Detects and automatically fixes circular import errors in generated Python code.

Common pattern fixed:
- main.py containing "from main import ..." (circular import)
- This happens when the LLM copies test file imports into the main code

Usage:
  echo '{"code": "<python_code>", "filename": "main.py"}' | python circular_import_fixer.py

Returns:
  - fixed: true/false
  - removed_imports: list of removed import lines
  - fixed_code: cleaned code
  - message: summary of what was fixed


**Tags:** `fix`, `error_handler`, `circular_import`, `import_error`, `code_repair`, `auto_fix`, `tdd`, `code_generation`

---

### Find Code Fix Pattern

**File:** `find_code_fix_pattern.yaml`  
**Type:** `executable`  

Pattern Recognizer with RAG Data Store - Searches for similar code errors and suggests proven fixes.

Uses a shared RAG-based pattern data store to find code fix patterns that have been successfully
applied in the past. Returns multiple solutions ranked by usage count (proven effectiveness) and
semantic similarity. The data store scope can be configured to search:
- Only patterns from the current tool
- Patterns from the current tool and its sub-tools
- All patterns across the entire tool hierarchy


**Tags:** `learning`, `code-fix`, `pattern-search`, `error-recovery`, `self-improvement`, `rag`, `data-store`, `pattern-recognizer`

---

### ModuleNotFoundError Fixer

**File:** `module_not_found_fixer.yaml`  
**Type:** `executable`  

Fixes ModuleNotFoundError by adding sys.path setup before imports.

This tool has ENCAPSULATED validation:
- fix() method: Applies the fix to the code
- validate() method: Validates the fix was actually applied

Common patterns handled:
- Adds path setup (sys.path.insert) before imports
- Removes unused imports that cause the error
- Validates all changes are actually in the fixed code


**Tags:** `fix`, `error_handler`, `module_error`, `import_error`, `auto_fix`, `tdd`, `validated`

---

### Store Code Fix Pattern

**File:** `store_code_fix_pattern.yaml`  
**Type:** `executable`  

Pattern Recognizer with RAG Data Store - Stores code breaks and their fixes as reusable patterns.

Stores code fix patterns in a shared RAG-based data store for future retrieval. Each pattern
includes the error, broken code, fixed code, and context. Patterns are tagged and embedded
for semantic search. The data store scope determines visibility:
- Store patterns at tool level (tool-specific learning)
- Store patterns at tool+subtools level (hierarchical learning)
- Store patterns at hierarchy level (contextual learning)
- Store patterns globally (universal learning)


**Tags:** `learning`, `code-fix`, `pattern-storage`, `error-recovery`, `self-improvement`, `rag`, `data-store`, `pattern-recognizer`

---

## LLM

**41 tools** - LLM-powered tools for intelligent code generation and analysis

### Article Content Analyzer

**File:** `article_analyzer.yaml`  
**Type:** `llm`  

Analyzes blog posts and articles for clarity, technical accuracy, SEO, and readability. Provides improvement suggestions.

**Tags:** `analysis`, `blog`, `seo`, `readability`, `content`, `review`

---

### Article Outline Generator

**File:** `outline_generator.yaml`  
**Type:** `llm`  

Creates detailed outlines for technical articles based on topics. Structures content logically.

**Tags:** `outline`, `structure`, `planning`, `article`, `organization`

---

### Code Concept Explainer

**File:** `code_explainer.yaml`  
**Type:** `llm`  

Explains complex programming concepts in simple terms for blog articles and tutorials. Creates analogies and examples.

**Tags:** `explanation`, `tutorial`, `teaching`, `concepts`, `examples`

---

### Code Optimizer

**File:** `code_optimizer.yaml`  
**Type:** `llm`  

Comprehensive code optimization tool with profiling, hierarchical optimization (local → cloud → deep), automatic test updating, and version comparison. Handles the complete optimization lifecycle.

**Tags:** `optimization`, `performance`, `refactoring`, `testing`, `profiling`

---

### Code Reviewer

**File:** `code_reviewer.yaml`  
**Type:** `llm`  

Reviews code for quality, best practices, and potential issues. Uses base model for thorough analysis.

**Tags:** `review`, `quality`, `code-analysis`, `best-practices`, `assessment`

---

### Code Translation Validator

**File:** `code_translation_validator.yaml`  
**Type:** `llm`  

Fast validator that ensures translation hasn't corrupted Python code blocks. Checks that code syntax remains valid, only comments are translated, and no code keywords were mistranslated. Use AFTER translating documents containing code.

**Tags:** `code`, `validation`, `translation`, `syntax-check`, `fast`

---

### Content Generator

**File:** `content_generator.yaml`  
**Type:** `llm`  

General purpose content generation for creative writing, articles, stories, and text content. Uses base model for quality output.

**Tags:** `content`, `generation`, `creative`, `writing`, `articles`, `stories`

---

### Content Summarizer

**File:** `content_summarizer.yaml`  
**Type:** `workflow`  

Smart content summarizer that automatically selects best tier and strategy.

Features:
- Automatic tier selection (fast/medium/large)
- Progressive summarization for large content
- Split-summarize-merge for very large docs
- Mantra-aware (respects speed/quality hints)
- Caching of results

This is the HIGH WEIGHT tool that should be used for all summarization.


**Tags:** `summarization`, `smart_routing`, `high_priority`, `workflow`

---

### Content Summarizer

**File:** `summarizer.yaml`  
**Type:** `llm`  

Summarizes content concisely while capturing all key points. Uses base model for quality.

**Tags:** `summarization`, `analysis`, `condensing`, `key-points`

---

### Detect Tool Specialization

**File:** `detect_tool_specialization.yaml`  
**Type:** `llm`  

Detects when an evolved tool has diverged far enough to become a new specialized tool with its own directory. Prevents tools from evolving beyond their original purpose.

**Tags:** `tool-evolution`, `specialization`, `meta-programming`, `organization`

---

### Dockerfile Generator

**File:** `dockerfile_generator.yaml`  
**Type:** `llm`  

Generates optimized Dockerfiles for wrapping tools and workflows with best practices including multi-stage builds, security hardening, and layer caching

**Tags:** `docker`, `dockerfile`, `containerization`, `devops`, `infrastructure`, `api-wrapper`

---

### Documentation Generator

**File:** `doc_generator.yaml`  
**Type:** `llm`  

Generates comprehensive code documentation

**Tags:** `documentation`, `docs`

---

### Explainer

**File:** `explainer.yaml`  
**Type:** `llm`  

Fast AI explainer tool that generates quick, concise descriptions of what's happening in workflows, tools, and system stages. Uses a 1B-class LLM for instant responses. Stage-aware and context-sensitive. Perfect for real-time explanations during tool generation and workflow execution.

**Tags:** `explanation`, `documentation`, `help`, `describe`, `clarify`, `stage-aware`, `workflow`, `real-time`

---

### Fast Code Generator

**File:** `fast_code_generator.yaml`  
**Type:** `llm`  

Fast code generation for simple tasks. Best for basic arithmetic, simple functions, straightforward algorithms. NOT suitable for complex logic or multi-step workflows.

**Tags:** `fast`, `simple`, `basic`, `code-generation`

---

### Fast Summarizer

**File:** `summarizer_fast.yaml`  
**Type:** `llm`  

Quick content summarization with small, fast model.

Use when:
- User says "quickly summarize"
- Speed is priority
- Basic quality is acceptable
- Content < 8k tokens

Model: gemma2:2b (very fast, 8k context)


**Tags:** `summarization`, `fast`, `small_context`, `gemma`

---

### General Code Generator

**File:** `general.yaml`  
**Type:** `llm`  

General purpose code generation for any programming task. Used as fallback when no specialized tool matches. Handles complex logic, multi-step workflows, and sophisticated algorithms.

**Tags:** `general`, `fallback`, `code-generation`, `any-task`, `complex`

---

### LLM Fake Data Generator

**File:** `llm_fake_data_generator.yaml`  
**Type:** `llm`  

Uses LLM to generate contextually appropriate fake data based on field names and descriptions. Better for complex, domain-specific data.

**Tags:** `llm`, `data-generation`, `testing`, `api-testing`, `mock-data`, `contextual`

---

### Large Context Summarizer

**File:** `summarizer_large.yaml`  
**Type:** `llm`  

High-quality summarization with large context window.

Use when:
- User says "carefully summarize" or "thoroughly"
- Quality is critical
- Content 32k-128k tokens
- Complex documents
- Books, research papers

Model: mistral-nemo (large, 128k context)


**Tags:** `summarization`, `high_quality`, `large_context`, `mistral`

---

### Layered Prompt Generator

**File:** `prompt_generator.yaml`  
**Type:** `llm`  

Generates sophisticated layered prompts with weight adjustment and model selection. Supports conversational model queries and dynamic tool creation. Uses tiered architecture with roles (system, role, context, task, constraints, output, examples).

**Tags:** `prompt-engineering`, `prompt-generation`, `layered`, `dynamic`, `tool-creation`, `model-selection`

---

### Long-Form Content Writer

**File:** `long_form_writer.yaml`  
**Type:** `llm`  

Specialized for writing long-form content (novels, books, long articles) using mistral-nemo's massive 128K context window. Best for creative writing, story generation, and content that requires maintaining continuity over many pages. Use with summarizer for ultra-long content.

**Tags:** `creative-writing`, `novel`, `story`, `long-form`, `article`, `book`, `large-context`

---

### Medium Summarizer

**File:** `summarizer_medium.yaml`  
**Type:** `llm`  

Balanced summarization with medium-sized model.

Use when:
- Quality matters
- Reasonable speed needed
- Content 8k-32k tokens
- Need comprehensive summary

Model: llama3 (balanced, 32k context)


**Tags:** `summarization`, `balanced`, `medium_context`, `llama`

---

### Model and Backend Selector

**File:** `model_selector.yaml`  
**Type:** `llm`  

Analyzes natural language requests to select the optimal LLM backend and model combination. Routes requests like 'using the most powerful code llm review this' to the appropriate provider and model (e.g., Anthropic Claude Opus).

**Tags:** `routing`, `model-selection`, `backend-selection`, `llm`, `intelligent-routing`

---

### Performance Optimizer

**File:** `performance_optimizer.yaml`  
**Type:** `llm`  

Suggests performance optimizations

**Tags:** `performance`, `optimization`

---

### Performance Profiler

**File:** `performance_profiler.yaml`  
**Type:** `llm`  

Analyzes code performance using PyInstrument profiling and provides detailed performance metrics, bottleneck identification, and optimization recommendations. Use this when asked to profile code, find performance issues, or analyze execution time.

**Tags:** `performance`, `profiling`, `optimization`, `analysis`, `pyinstrument`

---

### Prompt Genericiser

**File:** `prompt_genericiser.yaml`  
**Type:** `llm`  

Converts specific prompts into generic, reusable tool descriptions. Prevents unnecessary specialization by identifying the underlying generic pattern.

**Tags:** `generalization`, `deduplication`, `pattern-extraction`, `meta-programming`

---

### Prompt Mutator

**File:** `prompt_mutator.yaml`  
**Type:** `llm`  

Mutates LLM tool prompts for specific use cases. Specializes general prompts instead of forcing one prompt to fit all scenarios. Integrates with overseer for intelligent mutation decisions.

**Tags:** `mutation`, `prompt-engineering`, `specialization`, `optimization`, `evolution`

---

### Questions About Me

**File:** `questions_about_me.yaml`  
**Type:** `llm`  

Answers questions about the current system (memory, CPU, GPU, OS, disk, etc.) by gathering platform information and providing natural language responses. Handles questions like 'what memory do you have?', 'is the GPU busy?', 'what OS am I running?', etc.

**Tags:** `system`, `platform`, `info`, `diagnostic`, `conversational`, `qa`, `memory`, `cpu`, `gpu`

---

### Quick Feedback Checker

**File:** `quick_feedback.yaml`  
**Type:** `llm`  

Fast proofreading and quick feedback for text. Uses fast model for speed.

**Tags:** `spellcheck`, `grammar`, `quick-feedback`, `proofreading`, `fast`

---

### Quick Translator

**File:** `quick_translator.yaml`  
**Type:** `llm`  

Direct translation for words and short phrases. Returns immediate results without code generation. For longer translations (paragraphs, documents), use NMT translator or full translation workflow instead.

**Tags:** `translation`, `quick`, `words`, `phrases`, `llm`

---

### RAG Cluster Optimizer

**File:** `rag_cluster_optimizer.yaml`  
**Type:** `llm`  

Iterative self-optimization loop for artifact clusters. Explores variants, generates candidates, validates them through tests and benchmarks, and promotes fitter implementations while preserving lineage. The system learns patterns and converges toward high-fitness implementations over time.

**Tags:** `optimization`, `rag`, `clustering`, `self-improvement`, `evolution`, `fitness`, `variants`

---

### SEO Optimizer

**File:** `seo_optimizer.yaml`  
**Type:** `llm`  

Optimizes technical content for search engines, suggests keywords, meta descriptions, and structure improvements

**Tags:** `seo`, `keywords`, `optimization`, `search`, `metadata`

---

### Security Auditor

**File:** `security_auditor.yaml`  
**Type:** `llm`  

Audits code for security vulnerabilities using the most capable model for thorough analysis

**Tags:** `security`, `audit`, `vulnerability`, `powerful-model`

---

### Semantic Comparator

**File:** `semantic_comparator.yaml`  
**Type:** `llm`  

Decides if two prompts have the EXACT same meaning (100% match) or are similar enough for mutation (>50%). Used to prevent inappropriate workflow reuse for creative tasks.

**Tags:** `comparison`, `semantic`, `routing`, `cache-decision`

---

### SignalR Connection Parser

**File:** `signalr_connection_parser.yaml`  
**Type:** `llm`  

Parses natural language requests to connect to SignalR hubs and converts them into proper connection configuration. Extracts hub URL, context/method name, and workflow generation settings from conversational input.

**Tags:** `signalr`, `parser`, `nlp`, `configuration`, `natural-language`

---

### SignalR LLMApi Skill

**File:** `signalr_llmapi_management.yaml`  
**Type:** `llm`  

Complete skill for interacting with LLMApi SignalR simulator. Supports context management (create, list, delete), stream control (start/stop), and SSE streaming of API data.

**Tags:** `signalr`, `llmapi`, `stream`, `admin`, `skill`, `management`

---

### Style Extraction Evaluator

**File:** `style_extraction_evaluator.yaml`  
**Type:** `llm`  

Evaluates the quality and completeness of extracted style profiles. Assesses accuracy, coverage, and usefulness of style analysis results.

**Tags:** `evaluation`, `quality`, `style`, `analysis`

---

### Task to Workflow Router

**File:** `task_to_workflow_router.yaml`  
**Type:** `llm`  

Analyzes streaming task data from SignalR hub and automatically generates appropriate workflow code. Routes tasks to correct workflow patterns based on task type (summarize, generate, translate). Creates executable Python workflows for training the system.

**Tags:** `workflow`, `generator`, `routing`, `task`, `automation`, `training`, `llm`

---

### Technical Article Writer

**File:** `technical_writer.yaml`  
**Type:** `llm`  

Writes comprehensive technical articles, tutorials, and blog posts on software development topics

**Tags:** `writing`, `technical`, `article`, `blog`, `tutorial`, `documentation`

---

### Technical Proofreader

**File:** `proofreader.yaml`  
**Type:** `llm`  

Proofreads technical content for grammar, style, consistency, and technical accuracy

**Tags:** `proofreading`, `grammar`, `style`, `editing`, `quality`

---

### Translation Quality Validator

**File:** `translation_quality_checker.yaml`  
**Type:** `llm`  

Fast quality check for translation output using gemma3_1b. Detects repeated characters, garbled text, encoding errors, and translation failures. MUST be used after nmt_translator to validate output quality.

**Tags:** `translation`, `validation`, `quality-check`, `error-detection`, `fast`

---

### Workflow Documenter

**File:** `workflow_documenter.yaml`  
**Type:** `llm`  

Generates comprehensive 'How to Use' documentation for workflows by analyzing code, inputs, outputs, and purpose. Creates user-friendly guides for front-end generation and API consumption.

**Tags:** `documentation`, `workflow`, `api`, `guide`, `tutorial`, `how-to`, `frontend`

---

## MCP

**6 tools** - Model Context Protocol integration tools

### Fetch MCP

**File:** `fetch_mcp.yaml`  
**Type:** `mcp`  

Web content fetching and conversion via MCP. Fetches web pages and converts them to markdown for LLM consumption with support for caching and robots.txt compliance.

**Tags:** `mcp`, `mcp-tool`, `web`, `http`, `fetch`, `scraping`, `markdown`, `html`, `internet`, `url`

---

### Filesystem MCP

**File:** `filesystem_mcp.yaml`  
**Type:** `mcp`  

Secure filesystem operations via MCP server. Provides controlled read/write access to specified directories with safety controls.

**Tags:** `mcp`, `mcp-tool`, `filesystem`, `files`, `storage`, `io`, `read`, `write`, `directory`

---

### GitHub MCP

**File:** `github_mcp.yaml`  
**Type:** `mcp`  

GitHub integration via MCP server. Provides repository operations, issue management, PR handling, and code search through the Model Context Protocol.

**Tags:** `mcp`, `mcp-tool`, `github`, `git`, `repository`, `api`, `pr`, `pull-request`, `issue`, `code-hosting`, `version-control`

---

### Memory MCP

**File:** `memory_mcp.yaml`  
**Type:** `mcp`  

Knowledge graph-based persistent memory system via MCP. Stores and retrieves information using entities and relations for contextual knowledge management.

**Tags:** `mcp`, `mcp-tool`, `memory`, `knowledge-graph`, `storage`, `persistence`, `entities`, `relations`, `context`

---

### Time MCP

**File:** `time_mcp.yaml`  
**Type:** `mcp`  

Time and timezone conversion utilities via MCP. Provides current time, date conversion, and timezone operations for time-aware applications.

**Tags:** `mcp`, `mcp-tool`, `time`, `timezone`, `date`, `datetime`, `utilities`, `clock`

---

### Your Tool Name MCP

**File:** `_template.yaml`  
**Type:** `mcp`  

Brief description of what this MCP tool provides

**Tags:** `mcp`, `mcp-tool`

---

## NETWORKING

**12 tools** - Network operations and API tools

### Binary Decoder

**File:** `binary_decoder.yaml`  
**Type:** `custom`  

Decode binary data to Python objects (struct, msgpack, protobuf, json, custom). Supports automatic unpacking of C-style binary data, MessagePack deserialization, and custom binary protocols.

**Tags:** `networking`, `binary`, `decoding`, `deserialization`, `struct`, `msgpack`

---

### Binary Encoder

**File:** `binary_encoder.yaml`  
**Type:** `custom`  

Encode data to binary formats (struct, msgpack, protobuf, json, custom). Supports C-style struct packing, MessagePack serialization, and custom binary schemas.

**Tags:** `networking`, `binary`, `encoding`, `serialization`, `struct`, `msgpack`

---

### DNS Resolver

**File:** `dns_resolver.yaml`  
**Type:** `custom`  

DNS resolution and reverse lookup. Forward DNS (hostname to IP), reverse DNS (IP to hostname), with caching for performance.

**Tags:** `networking`, `dns`, `resolution`, `lookup`, `cache`

---

### Network Diagnostics

**File:** `network_diagnostics.yaml`  
**Type:** `custom`  

Network diagnostic utilities. TCP ping, latency measurement, and connection testing for network troubleshooting and monitoring.

**Tags:** `networking`, `diagnostics`, `ping`, `latency`, `monitoring`, `troubleshooting`

---

### Port Scanner

**File:** `port_scanner.yaml`  
**Type:** `custom`  

Network port scanner. TCP/UDP port scanning with parallel execution, service detection, and common port identification. Security testing and network discovery.

**Tags:** `networking`, `port-scanning`, `security`, `discovery`, `tcp`, `udp`

---

### Rate Limiter

**File:** `rate_limiter.yaml`  
**Type:** `custom`  

Rate limiting for network operations. Supports token bucket, sliding window, and fixed window algorithms to prevent overload and throttle requests.

**Tags:** `networking`, `rate-limiting`, `throttling`, `token-bucket`, `resilience`

---

### Resilient Caller

**File:** `resilient_caller.yaml`  
**Type:** `custom`  

Wrap any network call with retry logic and circuit breaker. Provides exponential backoff, jitter, and automatic failure handling for improved reliability.

**Tags:** `networking`, `resilience`, `retry`, `circuit-breaker`, `reliability`

---

### String Serializer

**File:** `string_serializer.yaml`  
**Type:** `custom`  

String encoding and decoding utilities. Supports UTF-8, ASCII, Base64, Hex, URL encoding/decoding with configurable error handling.

**Tags:** `networking`, `string`, `encoding`, `base64`, `hex`, `serialization`

---

### TCP Client

**File:** `tcp_client.yaml`  
**Type:** `custom`  

TCP client for binary protocols. Connect to server, send/receive binary data with automatic encoding/decoding. Supports connection pooling and keepalive.

**Tags:** `networking`, `tcp`, `client`, `binary`, `connection`

---

### TCP Server

**File:** `tcp_server.yaml`  
**Type:** `custom`  

TCP server for binary protocols. Multi-threaded connection handling with automatic decoding/encoding. Supports echo, uppercase, and custom handlers.

**Tags:** `networking`, `tcp`, `server`, `binary`, `connection`

---

### UDP Listener

**File:** `udp_listener.yaml`  
**Type:** `custom`  

Listen for UDP packets on a specified port. Supports automatic binary decoding, packet filtering, and configurable timeouts. Perfect for receiving sensor data, game packets, or any UDP-based protocol.

**Tags:** `networking`, `udp`, `listener`, `binary`, `packets`, `server`

---

### UDP Sender

**File:** `udp_sender.yaml`  
**Type:** `custom`  

Send UDP datagrams to a remote host. Supports automatic binary encoding, broadcast, and multicast. Great for sending sensor commands, game state updates, or any UDP protocol.

**Tags:** `networking`, `udp`, `sender`, `binary`, `broadcast`, `multicast`

---

## OPENAPI

**1 tools** - OpenAPI/Swagger specification tools

### NMT Translation Service

**File:** `nmt_translator.yaml`  
**Type:** `openapi`  

Neural Machine Translation service for translating text between languages using GET requests. VERY FAST but can be inaccurate - MUST validate output with translation_quality_checker for repeated characters and garbled text. Uses ISO 639 two-letter language codes (e.g., 'en', 'es', 'fr', 'de'). Get supported languages from GET /languages endpoint. API returns 'translations' array. Uses OpenAPI spec from http://localhost:8000/openapi.json.

**Tags:** `translation`, `nmt`, `neural`, `languages`, `openapi`, `api`

---

## OPTIMIZATION

**4 tools** - Code optimization and performance improvement tools

### Code Optimizer

**File:** `code_optimizer.yaml`  
**Type:** `llm`  

Comprehensive code optimization tool with profiling, hierarchical optimization (local → cloud → deep), automatic test updating, and version comparison. Handles the complete optimization lifecycle.

**Tags:** `optimization`, `performance`, `refactoring`, `testing`, `profiling`

---

### Optimize Cluster

**File:** `optimize_cluster.yaml`  
**Type:** `executable`  

Optimize RAG artifact clusters using iterative self-optimization loop. Can optimize specific workflows, functions, prompts, or entire node types. Supports conversational usage: 'optimize this workflow' or CLI: '/optimize workflow_name'

---

### Performance Optimizer

**File:** `performance_optimizer.yaml`  
**Type:** `llm`  

Suggests performance optimizations

**Tags:** `performance`, `optimization`

---

### RAG Cluster Optimizer

**File:** `rag_cluster_optimizer.yaml`  
**Type:** `llm`  

Iterative self-optimization loop for artifact clusters. Explores variants, generates candidates, validates them through tests and benchmarks, and promotes fitter implementations while preserving lineage. The system learns patterns and converges toward high-fitness implementations over time.

**Tags:** `optimization`, `rag`, `clustering`, `self-improvement`, `evolution`, `fitness`, `variants`

---

## PERF

**9 tools** - Performance monitoring and profiling tools

### Behave BDD Test Generator

**File:** `behave_test_generator.yaml`  
**Type:** `executable`  

Generate Behave BDD tests with step definitions from Gherkin feature files, tool specs, or workflow definitions with plausible test data

**Tags:** `testing`, `bdd`, `behave`, `test-generation`, `gherkin`, `acceptance-testing`, `behavior-driven`, `characterization`

---

### Comprehensive Tool Profiler

**File:** `comprehensive_tool_profiler.yaml`  
**Type:** `executable`  

Complete tool profiling orchestrator that combines performance benchmarking,
static analysis, regression evaluation, and RAG metadata updates into a single
workflow. This is the master tool for fully profiling a tool after code generation
or mutation. Tags tools in RAG with performance metrics, static analysis findings
(complexity, security, correctness), regression evaluation scores, source code,
and documentation. Prevents false-positive regressions while ensuring quality.


**Tags:** `profiling`, `orchestration`, `performance`, `static-analysis`, `regression`, `rag`, `workflow`, `comprehensive`

---

### Create Behave Spec

**File:** `create_behave_spec.yaml`  
**Type:** `executable`  

Create a Behave BDD specification file for RAG storage and future test generation

**Tags:** `testing`, `spec-creation`, `behave`, `bdd`, `rag`

---

### Create Locust Spec

**File:** `create_locust_spec.yaml`  
**Type:** `executable`  

Create a Locust load test specification file for RAG storage and future test generation

**Tags:** `testing`, `spec-creation`, `locust`, `performance`, `rag`

---

### Locust Load Test Generator

**File:** `locust_load_tester.yaml`  
**Type:** `executable`  

Generate and execute Locust performance/load tests from API specs, OpenAPI definitions, or BDD scenarios with plausible test data

**Tags:** `testing`, `load-testing`, `performance`, `locust`, `api-testing`, `stress-testing`, `benchmarking`, `characterization`

---

### Performance Profiler

**File:** `performance_profiler.yaml`  
**Type:** `llm`  

Analyzes code performance using PyInstrument profiling and provides detailed performance metrics, bottleneck identification, and optimization recommendations. Use this when asked to profile code, find performance issues, or analyze execution time.

**Tags:** `performance`, `profiling`, `optimization`, `analysis`, `pyinstrument`

---

### Performance Regression Evaluator

**File:** `performance_regression_evaluator.yaml`  
**Type:** `executable`  

Intelligent performance regression assessment using 4B-class LLM evaluation.
Prevents being locked into never accepting performance regressions by evaluating
whether performance changes are reasonable given requirement changes. Combines
static analysis (complexity, security, correctness) with LLM reasoning to score
regression acceptability from 0 (reject) to 100 (accept). Essential for avoiding
false positives in performance regression testing during feature evolution.


**Tags:** `performance`, `regression`, `evaluation`, `llm`, `static-analysis`, `optimization`, `testing`, `quality`

---

### PyInstrument Profiler

**File:** `pyinstrument_profiler.yaml`  
**Type:** `executable`  

Performance profiling using PyInstrument - provides detailed call stack analysis, line-level timing, and performance bottleneck identification. Generates text, HTML, and JSON reports for optimization analysis.

**Tags:** `python`, `profiling`, `performance`, `optimization`, `pyinstrument`

---

### Timeit Performance Optimizer

**File:** `timeit_optimizer.yaml`  
**Type:** `executable`  

Advanced performance testing and optimization tool. Generates self-contained benchmark scripts,
runs performance tests with automatic mocking of tool calls and external services,
collects execution time and memory metrics across 3 runs, and updates RAG metadata
with performance data. Essential for optimization workflows and performance tracking.


**Tags:** `performance`, `optimization`, `benchmarking`, `timeit`, `profiling`, `testing`, `metrics`, `memory`, `mocking`

---

