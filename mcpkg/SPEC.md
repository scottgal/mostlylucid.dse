# MCPKG Spec v0.1

> **MCPKG = AI-native package format for tools**
> Each `.mcpkg` contains:
> – a manifest (tool spec)
> – optional OpenAPI / schemas
> – tests
> – examples
> – metadata & signatures

LLMs + hosts can **install**, **validate**, and **use** tools directly from a package.

---

## 1. File Format

* File extension: **`.mcpkg`**
* Physical format: **ZIP archive**
* Must contain at least:
  * `/manifest.json`

All paths inside the ZIP are **POSIX style** (`/` separators).

---

## 2. Package Layout

Recommended structure:

```text
<toolId>-<version>.mcpkg
 ├─ manifest.json          # required – core spec
 ├─ openapi.json           # optional – OpenAPI / schema
 ├─ tests/                 # optional – test cases
 │    ├─ <name>.test.json
 │    └─ ...
 ├─ examples/              # optional – usage examples
 │    ├─ <name>.md
 │    └─ ...
 ├─ meta/                  # optional – publisher/provenance info
 │    ├─ publisher.json
 │    ├─ provenance.json
 │    └─ signature.sig
 └─ README.md              # optional – human docs
```

A minimal valid package is:

```text
foo.mcpkg
 └─ manifest.json
```

---

## 3. Tool Identity

Each package describes **one MCP tool** (you can extend to multiple later).

**Tool ID convention (v0.1)**

* `publisher.domain.capability.name`
* Example:
  * `stripe.payments.create_charge`
  * `mostlylucid.nmt.translate`
  * `acme.crm.search_customers`

The `toolId` must be globally unique in the registry context.

---

## 4. `manifest.json` Schema (v0.1)

Top-level JSON object with these required fields:

```jsonc
{
  "toolId": "stripe.payments.create_charge",
  "name": "Create Stripe Charge",
  "version": "1.0.0",
  "description": "Create a payment charge in Stripe for a given customer and amount.",
  "capabilities": ["payments", "stripe", "charges"],
  "endpoint": {
    "type": "http",
    "method": "POST",
    "url": "https://api.stripe.com/v1/charges",
    "timeoutMs": 10000
  },
  "input_schema": { /* JSON Schema */ },
  "output_schema": { /* JSON Schema */ },

  "auth": {
    "type": "bearer",              // or "oauth2", "api_key", "none"
    "scopes": ["charges:write"],   // optional
    "configHints": {
      "env": ["STRIPE_API_KEY"],   // optional hints for setup
      "docsUrl": "https://docs.stripe.com/..."
    }
  },

  "tests": [
    "tests/basic_charge.test.json",
    "tests/eu_vat_charge.test.json"
  ],

  "examples": [
    "examples/basic_usage.md"
  ],

  "meta": {
    "publisher": {
      "id": "stripe",
      "name": "Stripe",
      "website": "https://stripe.com"
    },
    "license": "proprietary",
    "homepage": "https://stripe.com/mcp",
    "tags": ["production", "payments", "eu-ready"]
  }
}
```

### 4.1 Required Fields

* `toolId` : `string` (unique id as above)
* `name` : `string` (human readable)
* `version` : `string` (SemVer: `MAJOR.MINOR.PATCH`)
* `description` : `string` – short summary
* `capabilities` : `string[]` – tags like `"payments"`, `"crm"`, `"search"`
* `endpoint` : `object`
  * `type` : `"http"` (future: `"grpc"`, `"local"`)
  * `method` : `"GET" | "POST" | "PUT" | "DELETE" | ...`
  * `url` : `string`
  * `timeoutMs` : `number` (optional)
* `input_schema` : **JSON Schema** describing the tool's input object
* `output_schema` : **JSON Schema** describing the output structure

### 4.2 Optional Fields

* `auth` : object describing auth mechanism
  * `type` : `"none" | "bearer" | "api_key" | "oauth2"`
  * `scopes` : `string[]` (optional)
  * `configHints` : freeform hints for humans/hosts
* `tests` : `string[]` – relative paths to test files inside the package
* `examples` : `string[]` – relative paths to markdown/text examples
* `meta` : object
  * `publisher` : object
    * `id` : string (registry ID / slug)
    * `name` : string
    * `website` : string
  * `license` : string (SPDX or freeform)
  * `homepage` : string
  * `tags` : `string[]`

---

## 5. Test Case Format (`tests/*.test.json`)

Each test file defines **one test scenario**.

```jsonc
{
  "name": "basic_eur_charge",
  "description": "Simple EUR 10 charge with valid card.",
  "input": {
    "amount": 1000,
    "currency": "EUR",
    "source": "tok_visa"
  },
  "expected": {
    "status": "succeeded",
    "currency": "eur",
    "amount": 1000
  },
  "assertions": [
    {
      "path": "$.status",
      "equals": "succeeded"
    },
    {
      "path": "$.amount_refunded",
      "equals": 0
    }
  ],
  "timeoutMs": 10000
}
```

### Semantics

* `input` → JSON object to pass to the tool as `arguments`.
* The host:
  * validates `input` against `input_schema`
  * calls the tool
  * gets a JSON `result`
  * evaluates `assertions` against `result`

**Assertion format (v0.1)** – simple but enough for now:

* `path` : JSONPath (e.g. `"$.status"`)
* Either:
  * `equals` : primitive
  * or `notEquals` / `exists` / `notExists` (you can extend as needed)

These tests are:

* **validation** for registry/DiSE
* **examples** for LLMs (how to call the tool)
* **guardrails** against drift/version changes

---

## 6. Examples Format (`examples/*.md`)

Freeform markdown / text used as **humans + LLM context**.

Example `examples/basic_usage.md`:

````markdown
# Basic Usage: Create a Charge

This tool wraps `POST https://api.stripe.com/v1/charges`.

Example call:

```json
{
  "amount": 1000,
  "currency": "EUR",
  "source": "tok_visa",
  "description": "Test payment"
}
```

Expected behavior:

* Creates a charge of 10 EUR
* Status should be `succeeded`
* `amount_refunded` should be 0

````

Hosts can feed this into the LLM as RAG context when deciding how to call the tool.

---

## 7. Meta & Signatures (`meta/`)

Optional but recommended.

### 7.1 `meta/publisher.json`

```json
{
  "id": "stripe",
  "name": "Stripe",
  "website": "https://stripe.com",
  "contact": "support@stripe.com"
}
```

### 7.2 `meta/provenance.json`

```json
{
  "sourceRepo": "https://github.com/stripe/stripe-mcp-tools",
  "commit": "a1b2c3d4e5f6",
  "builtAt": "2025-11-21T10:00:00Z",
  "builtBy": "ci@stripe.com"
}
```

### 7.3 `meta/signature.sig`

* Opaque blob – registry/host can define the signing scheme (e.g. detached signature of `manifest.json` + `tests/`).
* v0.1 spec: "if present, treat as a publisher signature over at least `manifest.json`".

---

## 8. Host Behavior (High-Level)

This is what you want Claude to wire around:

1. **Install**
   * `mcp install <toolId>`
   * Resolve `.mcpkg` from:
     * local file
     * registry HTTP API (future)
   * Unpack to a local `.mcp/tools/<toolId>/` folder

2. **Load tools**
   * Read `manifest.json`
   * Validate:
     * JSON structure
     * `input_schema` / `output_schema` are valid JSON Schema
   * Optionally run tests in `tests/` before enabling.

3. **Expose to LLM**
   * For each loaded tool:
     * create a tool definition with `name`, `description`, `input_schema`
     * pass that to the LLM in the tool list (MCP, OpenAI tools, etc.)
   * Optionally include:
     * examples content as RAG context
     * a summary of successful tests

4. **Run Tests**
   * `mcp test <toolId>`
   * For each test file:
     * Validate `input` against `input_schema`
     * Call endpoint with `input`
     * Assert against `expected` + `assertions`
   * Summarise pass/fail & record metrics (latency, error rates, etc.)

5. **Ranking (DiSE layer)**
   * Not part of v0.1 spec but assumed:
     * Tools can be scored by:
       * test pass rate
       * latency
       * stability
     * DiSE can RAG over `manifest.json` + `tests/` + metrics to:
       * recommend best tool per capability
       * detect regressions

---

## 9. Minimal Example Package

**`echo.mcpkg` contents:**

```text
echo.mcpkg
 ├─ manifest.json
 └─ tests/
      └─ echo.test.json
```

`manifest.json`:

```json
{
  "toolId": "demo.echo",
  "name": "Echo Tool",
  "version": "0.1.0",
  "description": "Echos back whatever input it receives.",
  "capabilities": ["demo", "echo"],
  "endpoint": {
    "type": "http",
    "method": "POST",
    "url": "https://example.com/mcp/echo",
    "timeoutMs": 5000
  },
  "input_schema": {
    "type": "object",
    "properties": {
      "message": { "type": "string" }
    },
    "required": ["message"]
  },
  "output_schema": {
    "type": "object",
    "properties": {
      "message": { "type": "string" }
    },
    "required": ["message"]
  },
  "tests": [
    "tests/echo.test.json"
  ]
}
```

`tests/echo.test.json`:

```json
{
  "name": "simple_echo",
  "description": "Echos back the same message.",
  "input": { "message": "hello" },
  "expected": { "message": "hello" },
  "assertions": [
    { "path": "$.message", "equals": "hello" }
  ]
}
```

---

## 10. Multi-Platform Support with Implementations (v0.2+)

### 10.1 The Problem: Platform-Specific Tool Variants

A single **logical tool** (e.g., `tools.pdf.read_local`) may have multiple **physical implementations** for different:

* Languages (JavaScript, .NET, Python)
* Runtimes (Node.js, browser, .NET 8, Python 3.11)
* Platforms (Linux x64, Windows x64, macOS ARM64)
* Hardware (CPU-only, GPU-accelerated)

The LLM should only see the logical tool, while the host selects the best implementation for the current environment.

### 10.2 Implementations Array

Add an optional `implementations` array to `manifest.json`:

```jsonc
{
  "toolId": "tools.pdf.read_local",
  "name": "Read PDFs Locally",
  "version": "1.0.0",
  "description": "Read and extract text/structure from PDFs on the local machine.",
  "capabilities": ["pdf", "local", "fs"],

  "implementations": [
    {
      "id": "node-pdfjs",
      "language": "javascript",
      "runtime": "node",
      "platforms": ["linux-x64", "win-x64", "darwin-arm64"],
      "endpoint": {
        "type": "local",
        "command": "node ./sdk/javascript/pdf-read.js"
      },
      "requirements": {
        "minNodeVersion": "18.0.0"
      }
    },
    {
      "id": "dotnet-itext",
      "language": "dotnet",
      "runtime": "net8.0",
      "platforms": ["win-x64", "linux-x64"],
      "endpoint": {
        "type": "local",
        "command": "dotnet ./sdk/dotnet/PdfReader.dll"
      }
    },
    {
      "id": "python-pymupdf",
      "language": "python",
      "runtime": "python3.11",
      "platforms": ["linux-x64", "darwin-arm64"],
      "endpoint": {
        "type": "local",
        "command": "python ./sdk/python/pdf_reader.py"
      },
      "requirements": {
        "packages": ["PyMuPDF>=1.23.0"]
      }
    }
  ],

  "input_schema": { /* same for all implementations */ },
  "output_schema": { /* same for all implementations */ }
}
```

### 10.3 Implementation Selection

**Discovery Flow:**

1. **LLM asks**: "I need a tool to read PDFs locally for JavaScript."
2. **Registry RAG** filters by:
   * `capabilities` contains `["pdf", "local"]`
   * `implementations[].language == "javascript"`
3. **Host** installs the package and selects the best implementation:
   * Match `runtime` (Node.js vs browser)
   * Match `platforms` (current OS + architecture)
   * Check `requirements` (versions, dependencies)
4. **Host exposes** the logical tool to the LLM:
   ```json
   {
     "tool": "tools.pdf.read_local",
     "description": "Read PDFs locally",
     "input_schema": { ... }
   }
   ```
5. **LLM calls** the tool (implementation-agnostic):
   ```json
   {
     "tool": "tools.pdf.read_local",
     "arguments": { "path": "/tmp/file.pdf" }
   }
   ```
6. **Host executes** the selected implementation:
   ```bash
   node ./sdk/javascript/pdf-read.js '{"path":"/tmp/file.pdf"}'
   ```

### 10.4 Key Benefits

* **LLM simplicity**: LLM only sees logical tools, not platform details
* **Registry semantics**: "Give me a PDF reader for JavaScript" → precise matches
* **Host flexibility**: Automatically picks the best variant for the environment
* **Graceful fallbacks**: Can rank implementations by performance/compatibility

---

## 11. Composite Tools with Chains (v0.2+)

### 11.1 The Problem: Multi-Step Workflows

Some tools are **pipelines** composed of multiple steps:

* PDF → clean text → embeddings
* Audio → transcribe → translate → summarize
* Image → OCR → extract tables → to CSV

Instead of the LLM orchestrating each step, the **host** can execute a predefined chain.

### 11.2 Chain Definition

Add an optional `chain` array to `manifest.json`:

```jsonc
{
  "toolId": "tools.pdf.pipeline.embed",
  "name": "PDF to Embeddings Pipeline",
  "version": "1.0.0",
  "description": "Extracts text from PDF, cleans it, and generates embeddings.",
  "capabilities": ["pdf", "embeddings", "pipeline"],

  "chain": [
    {
      "step": "read_pdf",
      "tool": "tools.pdf.read_local",
      "inputMapping": {
        "path": "$.input.pdfPath"
      },
      "outputKey": "raw_text"
    },
    {
      "step": "clean_text",
      "tool": "tools.text.clean",
      "inputMapping": {
        "text": "$.raw_text.content"
      },
      "outputKey": "cleaned_text"
    },
    {
      "step": "generate_embeddings",
      "tool": "tools.embeddings.generate",
      "inputMapping": {
        "text": "$.cleaned_text.result",
        "model": "$.input.embeddingModel"
      },
      "outputKey": "embeddings"
    }
  ],

  "input_schema": {
    "type": "object",
    "properties": {
      "pdfPath": { "type": "string" },
      "embeddingModel": { "type": "string", "default": "text-embedding-3-small" }
    },
    "required": ["pdfPath"]
  },

  "output_schema": {
    "type": "object",
    "properties": {
      "embeddings": {
        "type": "array",
        "items": { "type": "number" }
      }
    }
  }
}
```

### 11.3 Chain Execution

**Execution Flow:**

1. **LLM calls** the pipeline tool:
   ```json
   {
     "tool": "tools.pdf.pipeline.embed",
     "arguments": {
       "pdfPath": "/docs/report.pdf",
       "embeddingModel": "text-embedding-3-small"
     }
   }
   ```

2. **Host executes** the chain:
   ```
   Step 1: read_pdf
     Input: { "path": "/docs/report.pdf" }
     Output → raw_text: { "content": "..." }

   Step 2: clean_text
     Input: { "text": raw_text.content }
     Output → cleaned_text: { "result": "..." }

   Step 3: generate_embeddings
     Input: { "text": cleaned_text.result, "model": "text-embedding-3-small" }
     Output → embeddings: { "embeddings": [...] }
   ```

3. **Host returns** final output:
   ```json
   {
     "embeddings": [0.1, 0.2, -0.3, ...]
   }
   ```

### 11.4 JSONPath Input Mapping

Each step's `inputMapping` uses JSONPath to extract values from:

* `$.input.*` - Original tool input
* `$.step_name.*` - Output from a previous step (referenced by `outputKey`)

Example:
```jsonc
"inputMapping": {
  "text": "$.cleaned_text.result",  // From previous step
  "model": "$.input.embeddingModel" // From original input
}
```

### 11.5 Chain Benefits

* **Reduces LLM orchestration complexity**: Single tool call instead of 3+
* **Optimises latency**: Host can execute steps locally without LLM round-trips
* **Enables DiSE evolution**: DiSE can assemble/optimise chains based on metrics
* **Cacheable pipelines**: Registry can store evolved chains as versioned tools

### 11.6 DiSE Integration with Chains

DiSE can:

1. **Generate chains** by analysing workflow patterns:
   * "Users who call PDF read + text clean + embeddings → bundle as pipeline"
2. **Optimise chains** based on metrics:
   * Replace slow step implementations with faster variants
   * Reorder steps for better caching
3. **Version chains** as new tools:
   * `tools.pdf.pipeline.embed:v1` → original chain
   * `tools.pdf.pipeline.embed:v2` → DiSE-optimised chain
4. **Rank chains** for selection:
   * Fastest for CPU-only environments
   * Most accurate for GPU-accelerated setups

---

## 12. DiSE Integration

The mcpkg format is designed to integrate seamlessly with DiSE (Dynamic Intelligence Selection Engine):

* **Generated Nodes**: Each installed tool becomes a DiSE node with the same structure:
  * `manifest.json` provides the tool specification
  * `tests/` provide validation and examples
  * `metadata.json` tracks performance metrics (latency, success rate, etc.)
* **Tool Ranking**: DiSE can score tools based on:
  * Test pass rate
  * Historical performance metrics
  * Capability matching
  * Implementation suitability for the current environment
* **RAG Context**: DiSE can use `examples/`, `tests/`, and `implementations` as context for tool selection decisions
* **Regression Detection**: By continuously running tests, DiSE can detect when a tool's behavior changes
* **Chain Evolution**: DiSE can generate and optimise composite tools by analysing usage patterns and performance metrics

---

## 13. Summary

If you give Claude this spec and say:

> "Build a .NET CLI that can:
> – create `.mcpkg` from a folder
> – install/unpack into `.mcp/tools`
> – validate `manifest.json` and tests
> – run tests
> – emit a tools.json ready to feed into an LLM runtime"

…it should have plenty to work with.

For v0.2+ features (implementations, chains), you can extend the manifest models and add:
* Implementation selector based on runtime/platform detection
* Chain executor that pipes outputs between tools
* Registry RAG filtering by language/platform/capabilities
