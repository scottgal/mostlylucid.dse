# Development APIs - Free Tools Collection

This directory contains a comprehensive collection of free development APIs that require no authentication. These tools are perfect for testing, prototyping, development, and learning.

## Table of Contents

- [Data Enrichment & Demographics](#data-enrichment--demographics)
- [Testing & Mocking](#testing--mocking)
- [Networking & Utilities](#networking--utilities)
- [Content Generation](#content-generation)
- [Visual Assets](#visual-assets)

---

## Data Enrichment & Demographics

### Agify.io
**File:** `agify.yaml`
**Purpose:** Estimate age from a first name using statistical data
**Key Features:**
- No authentication required
- Supports country-specific predictions
- Batch predictions (up to 10 names)
- Returns confidence score (sample size)

**Use Cases:**
- Data enrichment
- Demographic analysis
- Marketing segmentation
- Form validation

**Example:**
```python
from agify import predict_age
result = predict_age("michael")
# Returns: {"name": "michael", "age": 66, "count": 233514}
```

---

### Genderize.io
**File:** `genderize.yaml`
**Purpose:** Estimate gender from a first name using statistical data
**Key Features:**
- No authentication required
- Country-specific predictions
- Probability scores
- Batch processing

**Use Cases:**
- Data normalization
- Personalization
- Analytics
- CRM enrichment

**Example:**
```python
from genderize import predict_gender
result = predict_gender("alex")
# Returns: {"name": "alex", "gender": "male", "probability": 0.89, "count": 12345}
```

---

### Nationalize.io
**File:** `nationalize.yaml`
**Purpose:** Estimate nationality from a first name
**Key Features:**
- Returns multiple countries with probabilities
- Batch processing
- No authentication required

**Use Cases:**
- Demographic analysis
- Localization
- Market research
- Customer segmentation

**Example:**
```python
from nationalize import predict_nationality
result = predict_nationality("hans")
# Returns list of countries with probabilities
```

---

## Testing & Mocking

### Httpbin
**File:** `httpbin.yaml`
**Purpose:** Simple HTTP Request & Response Service for testing
**Key Features:**
- Test all HTTP methods (GET, POST, PUT, DELETE, etc.)
- Test headers, cookies, authentication
- Simulate delays and status codes
- Request inspection

**Use Cases:**
- API development
- HTTP client testing
- Debugging
- Learning HTTP protocols

**Example:**
```python
from httpbin import test_post
result = test_post(json_data={"key": "value"})
# Returns full request details including posted data
```

---

### ReqRes
**File:** `reqres.yaml`
**Purpose:** Hosted REST API with realistic user data
**Key Features:**
- CRUD operations on users
- Pagination support
- Realistic data structure
- Simulated authentication

**Use Cases:**
- Frontend development
- API integration testing
- Prototyping
- Learning REST APIs

**Example:**
```python
from reqres import list_users
users = list_users(page=1)
# Returns paginated user data
```

---

### JSONPlaceholder
**File:** `jsonplaceholder.yaml`
**Purpose:** Fake REST API for testing and prototyping
**Key Features:**
- 100 posts, 500 comments, 100 photos, 200 todos
- Full CRUD support
- Multiple resources (posts, users, comments, albums, todos)
- Realistic data structure

**Use Cases:**
- Learning REST APIs
- Testing AJAX calls
- Prototyping applications
- Teaching API concepts

**Example:**
```python
from jsonplaceholder import get_posts
posts = get_posts(limit=10)
# Returns list of blog posts
```

---

## Networking & Utilities

### IPify
**File:** `ipify.yaml`
**Purpose:** Get public IP address
**Key Features:**
- IPv4 and IPv6 support
- JSON or plain text format
- Very fast response
- No rate limits

**Use Cases:**
- Network diagnostics
- IP detection
- Location services
- Security applications

**Example:**
```python
from ipify import get_ip_json
result = get_ip_json()
# Returns: {"ip": "123.45.67.89"}
```

---

### CountAPI
**File:** `countapi.yaml`
**Purpose:** Simple counting service
**Key Features:**
- Create custom counters
- Increment/decrement operations
- Get/set values
- Statistics tracking

**Use Cases:**
- Visitor tracking
- Analytics
- Rate limiting
- Simple metrics

**Example:**
```python
from countapi import increment_counter
result = increment_counter("my-app", "visitors")
# Returns: {"value": 42}
```

---

### UUID Generator
**File:** `uuid_generator.yaml`
**Purpose:** Generate UUIDs via API
**Key Features:**
- UUID v1 (timestamp-based)
- UUID v4 (random)
- Batch generation (up to 100)
- No authentication required

**Use Cases:**
- Testing database operations
- Generating unique identifiers
- Distributed systems
- API development

**Example:**
```python
from uuid_generator import generate_uuid_v4
uuid = generate_uuid_v4()
# Returns: "f47ac10b-58cc-4372-a567-0e02b2c3d479"
```

---

## Content Generation

### Random User API
**File:** `randomuser.yaml`
**Purpose:** Generate random user data
**Key Features:**
- Complete user profiles (name, email, photo, address)
- Gender and nationality filtering
- Reproducible results with seeds
- Field selection

**Use Cases:**
- Mockups and prototypes
- Testing user interfaces
- Populating databases
- Demo applications

**Example:**
```python
from randomuser import generate_user
user = generate_user(gender='female', nationality='us')
# Returns complete user profile with photo
```

---

### Lorem Ipsum Generator
**File:** `ipsum_generator.yaml`
**Purpose:** Generate Lorem Ipsum placeholder text
**Key Features:**
- Customizable paragraph count
- Variable length (short/medium/long)
- HTML or plain text
- Rich formatting options (lists, code, headers)

**Use Cases:**
- Layout testing
- Typography design
- Content mockups
- UI development

**Example:**
```python
from ipsum_generator import generate_plaintext
text = generate_plaintext(5)
# Returns 5 paragraphs of Lorem Ipsum text
```

---

### Bored API
**File:** `bored_api.yaml`
**Purpose:** Generate random activity suggestions
**Key Features:**
- Activity types (education, recreational, social, etc.)
- Filter by participants
- Price range filtering
- Accessibility information

**Use Cases:**
- Testing randomization
- Content generation
- Application ideas
- User engagement

**Example:**
```python
from bored_api import get_random_activity
activity = get_random_activity()
# Returns: {"activity": "Learn Express.js", "type": "education", ...}
```

---

## Visual Assets

### Kroki
**File:** `kroki.yaml`
**Purpose:** Create diagrams from textual descriptions
**Key Features:**
- Multiple diagram types (PlantUML, Mermaid, GraphViz)
- Multiple output formats (SVG, PNG, PDF)
- No authentication required
- Extensive diagram syntax support

**Supported Diagram Types:**
- PlantUML: UML diagrams
- Mermaid: Flowcharts, sequence diagrams
- GraphViz: Graph visualizations
- BlockDiag, SeqDiag, ActDiag, NwDiag

**Use Cases:**
- Documentation
- Architecture diagrams
- Workflow visualization
- System design

**Example:**
```python
from kroki import generate_mermaid
diagram = generate_mermaid("""
graph TD
    A[Start] --> B{Decision}
    B -->|Yes| C[Action]
    B -->|No| D[End]
""")
# Returns SVG diagram
```

---

### QR Code Generator
**File:** `qrcode_generator.yaml`
**Purpose:** Generate QR codes
**Key Features:**
- Custom sizes (up to 1000px)
- Custom colors
- Multiple formats (PNG, SVG, JPEG)
- Custom margins

**Use Cases:**
- Testing QR functionality
- Prototyping
- Link sharing
- Mobile development

**Example:**
```python
from qrcode_generator import generate_qrcode
qr = generate_qrcode("https://example.com", size=300)
# Returns QR code image
```

---

### Placeholder Images
**File:** `placeholder_images.yaml`
**Purpose:** Generate placeholder images for mockups
**Key Features:**
- Custom dimensions
- Custom colors (background and text)
- Custom text overlay
- Multiple formats (PNG, JPG, WebP)

**Use Cases:**
- UI/UX prototyping
- Layout testing
- Image lazy loading
- Content placeholders

**Example:**
```python
from placeholder_images import generate_placeholder
img = generate_colored_placeholder(
    width=800,
    height=600,
    bgcolor='0066cc',
    text='Banner'
)
# Returns placeholder image
```

---

## Quick Reference Table

| API | Category | Main Purpose | Auth Required | Rate Limit |
|-----|----------|--------------|---------------|------------|
| Agify.io | Demographics | Age estimation | No | Yes (free tier) |
| Genderize.io | Demographics | Gender estimation | No | Yes (free tier) |
| Nationalize.io | Demographics | Nationality estimation | No | Yes (free tier) |
| Httpbin | Testing | HTTP testing | No | No |
| ReqRes | Testing | Mock REST API | No | No |
| JSONPlaceholder | Testing | Fake data API | No | No |
| IPify | Networking | IP detection | No | No |
| CountAPI | Utilities | Counting service | No | No |
| UUID Generator | Utilities | UUID generation | No | No |
| Random User | Content | User data generation | No | No |
| Lorem Ipsum | Content | Text generation | No | No |
| Bored API | Content | Activity suggestions | No | No |
| Kroki | Visual | Diagram generation | No | No |
| QR Code | Visual | QR code creation | No | No |
| Placeholder Images | Visual | Image placeholders | No | No |

---

## Usage Tips

### 1. Rate Limiting
While most of these APIs are free, some have rate limits on the free tier:
- **Agify/Genderize/Nationalize**: 1,000 requests/day (free tier)
- Consider caching results for frequently used queries

### 2. Error Handling
Always implement proper error handling:
```python
try:
    result = api_call()
except requests.exceptions.HTTPError as e:
    print(f"API error: {e}")
except requests.exceptions.ConnectionError:
    print("Network error")
```

### 3. Performance
- Use batch operations when available
- Cache results when appropriate
- Consider API proximity for latency-sensitive applications

### 4. Testing Best Practices
- Use these APIs for development and testing only
- Don't rely on them for production critical paths
- Have fallbacks for when APIs are unavailable

---

## Integration Examples

### Full Stack Testing Setup
```python
# Generate test users
from randomuser import generate_users
users = generate_users(count=10)

# Create counters for each user
from countapi import create_counter
for user in users['results']:
    create_counter('test-app', user['login']['username'])

# Generate placeholder content
from ipsum_generator import generate_paragraphs
from placeholder_images import generate_square_placeholder

content = generate_paragraphs(5)
avatar = generate_square_placeholder(200)
```

### API Testing Workflow
```python
# Test HTTP methods
from httpbin import test_get, test_post, test_headers

# Verify GET works
get_result = test_get({'param': 'value'})
assert 'args' in get_result

# Verify POST works
post_result = test_post(json_data={'key': 'value'})
assert post_result['json']['key'] == 'value'

# Verify headers
headers_result = test_headers({'X-Custom': 'test'})
assert 'X-Custom' in headers_result['headers']
```

---

## Contributing

To add a new API tool:

1. Create a YAML file following the existing format
2. Include comprehensive `code_template` with examples
3. Add appropriate tags for discoverability
4. Update this README with the new tool
5. Test the integration thoroughly

---

## Resources

- [Public APIs Repository](https://github.com/public-apis/public-apis)
- Tool Organization Guide: `../TOOL_ORGANIZATION.md`
- OpenAPI Specification: Each tool includes spec_url

---

## License

These tools are wrappers around free public APIs. Please review each API's terms of service before use in production.

**Last Updated:** 2025-11-18
