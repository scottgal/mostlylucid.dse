# Smart Faker - Usage Examples

The Smart Faker tool is an intelligent data generator that accepts plain English, code snippets, JSON schemas, or any LLM-interpretable input and generates realistic fake data.

## Table of Contents
- [Basic Usage](#basic-usage)
- [Input Types](#input-types)
- [Output Formats](#output-formats)
- [Advanced Features](#advanced-features)
- [Use Cases](#use-cases)

---

## Basic Usage

### Example 1: Plain English Description

```python
from node_runtime import NodeRuntime
import json

runtime = NodeRuntime()

result = runtime.call_tool(
    "smart_faker",
    prompt="I need user data with name, email, age, and subscription status",
    count=3
)

print(result)
```

**Output:**
```json
{
  "success": true,
  "data": [
    {
      "name": "Sarah Johnson",
      "email": "sarah.johnson@example.com",
      "age": 28,
      "subscription_status": "active"
    },
    {
      "name": "Michael Chen",
      "email": "michael.chen@example.com",
      "age": 35,
      "subscription_status": "premium"
    },
    {
      "name": "Emma Davis",
      "email": "emma.davis@example.com",
      "age": 42,
      "subscription_status": "inactive"
    }
  ],
  "format": "json",
  "count": 3
}
```

---

## Input Types

### 1. Plain English

Simple, natural language descriptions:

```python
# Customer data
result = runtime.call_tool(
    "smart_faker",
    prompt="Generate customer records with customer_id, full name, email, phone number, and total purchases",
    count=5
)

# IoT sensor data
result = runtime.call_tool(
    "smart_faker",
    prompt="IoT temperature sensor readings with timestamp, sensor_id, temperature in celsius, and humidity percentage",
    count=100
)

# E-commerce orders
result = runtime.call_tool(
    "smart_faker",
    prompt="Order data with order_id, customer_name, items array, total_amount, and order_status",
    count=10
)
```

### 2. JSON Schema

Full JSON Schema specification:

```python
schema = {
    "type": "object",
    "properties": {
        "transaction_id": {
            "type": "string",
            "description": "Unique transaction identifier"
        },
        "amount": {
            "type": "number",
            "minimum": 0.01,
            "maximum": 10000.00
        },
        "currency": {
            "type": "string",
            "enum": ["USD", "EUR", "GBP"]
        },
        "status": {
            "type": "string",
            "enum": ["pending", "completed", "failed", "refunded"]
        },
        "timestamp": {
            "type": "string",
            "format": "date-time"
        }
    },
    "required": ["transaction_id", "amount", "currency", "status"]
}

result = runtime.call_tool(
    "smart_faker",
    prompt=json.dumps(schema),
    count=20
)
```

### 3. Code Snippets

#### Python Class

```python
code = '''
class Product:
    def __init__(self, sku, name, price, stock, category):
        self.sku = sku
        self.name = name
        self.price = price
        self.stock = stock
        self.category = category
'''

result = runtime.call_tool(
    "smart_faker",
    prompt=code,
    count=10,
    additional_context="For an electronics store inventory"
)
```

#### TypeScript Interface

```python
code = '''
interface User {
    id: number;
    username: string;
    email: string;
    isActive: boolean;
    roles: string[];
    createdAt: Date;
}
'''

result = runtime.call_tool(
    "smart_faker",
    prompt=code,
    count=15
)
```

#### C# Class

```python
code = '''
public class Employee
{
    public int EmployeeId { get; set; }
    public string FirstName { get; set; }
    public string LastName { get; set; }
    public string Department { get; set; }
    public decimal Salary { get; set; }
    public DateTime HireDate { get; set; }
    public bool IsFullTime { get; set; }
}
'''

result = runtime.call_tool(
    "smart_faker",
    prompt=code,
    count=25
)
```

### 4. Example JSON

Paste an example and get similar data:

```python
example = {
    "order_id": "ORD-2024-001",
    "customer": {
        "name": "John Doe",
        "email": "john@example.com"
    },
    "items": [
        {"product": "Laptop", "price": 999.99, "qty": 1},
        {"product": "Mouse", "price": 24.99, "qty": 2}
    ],
    "total": 1049.97,
    "status": "shipped"
}

result = runtime.call_tool(
    "smart_faker",
    prompt=f"Generate data like this example:\n{json.dumps(example, indent=2)}",
    count=5,
    additional_context="For an e-commerce platform"
)
```

---

## Output Formats

### 1. JSON (Default)

```python
result = runtime.call_tool(
    "smart_faker",
    prompt="User with name, email, age",
    count=3,
    output_format="json"
)

# Returns nicely formatted JSON array
```

### 2. CSV

Perfect for importing into spreadsheets or databases:

```python
result = runtime.call_tool(
    "smart_faker",
    prompt="Employee with employee_id, name, department, salary, hire_date",
    count=100,
    output_format="csv"
)

# Save to file
with open('employees.csv', 'w') as f:
    f.write(result['data'])
```

**Output:**
```csv
department,employee_id,hire_date,name,salary
Engineering,1001,2020-03-15,Alice Johnson,95000.00
Marketing,1002,2019-07-22,Bob Smith,72000.00
Sales,1003,2021-01-10,Carol White,68000.00
...
```

### 3. JSON Lines (JSONL)

One JSON object per line - great for streaming and log files:

```python
result = runtime.call_tool(
    "smart_faker",
    prompt="Log entry with timestamp, level, message, user_id",
    count=1000,
    output_format="jsonl"
)

# Each line is a valid JSON object
```

**Output:**
```jsonl
{"timestamp": "2024-01-15T10:30:00Z", "level": "INFO", "message": "User logged in", "user_id": 1234}
{"timestamp": "2024-01-15T10:30:05Z", "level": "WARN", "message": "API rate limit approaching", "user_id": 5678}
{"timestamp": "2024-01-15T10:30:12Z", "level": "ERROR", "message": "Database connection timeout", "user_id": 9012}
```

### 4. Array (Python List)

```python
result = runtime.call_tool(
    "smart_faker",
    prompt="Product names",
    count=10,
    output_format="array"
)

# Returns Python list representation
```

---

## Advanced Features

### 1. Streaming Large Datasets

For memory efficiency with very large datasets:

```python
result = runtime.call_tool(
    "smart_faker",
    prompt="IoT sensor readings with device_id, timestamp, temperature, humidity, pressure",
    count=100000,
    output_format="jsonl",
    stream=True
)

# Data is output one line at a time as it's generated
# Perfect for processing large datasets without loading everything into memory
```

### 2. Reproducible Data with Seeds

Generate the same data every time:

```python
result = runtime.call_tool(
    "smart_faker",
    prompt="Test user with name, email, phone",
    count=10,
    seed=42  # Same seed = same data
)

# Run again with seed=42, get identical data
# Perfect for testing and demos
```

### 3. Additional Context

Guide the LLM to generate domain-specific data:

```python
result = runtime.call_tool(
    "smart_faker",
    prompt="Patient records with patient_id, name, diagnosis, medications",
    count=50,
    additional_context="For a pediatric clinic. Patients are children ages 0-17. Common diagnoses include asthma, allergies, and routine checkups."
)
```

### 4. Custom LLM Model

Use different models for interpretation:

```python
result = runtime.call_tool(
    "smart_faker",
    prompt="Complex medical data...",
    llm_model="llama3:8b",  # Use larger model for better interpretation
    count=100
)
```

---

## Use Cases

### Use Case 1: API Testing

Generate mock API responses:

```python
# Mock user API response
users = runtime.call_tool(
    "smart_faker",
    prompt='''
    API response with:
    - users (array of objects)
    - each user has: id, username, email, avatar_url, created_at
    - pagination info: page, per_page, total_pages, total_count
    ''',
    count=1
)
```

### Use Case 2: Database Seeding

Populate development database:

```python
# Generate 1000 products
products = runtime.call_tool(
    "smart_faker",
    prompt="Product with sku, name, description, price, stock, category, supplier",
    count=1000,
    output_format="csv",
    seed=12345  # Reproducible for team
)

# Import into database
# psql -d mydb -c "\COPY products FROM 'products.csv' CSV HEADER"
```

### Use Case 3: Load Testing

Generate realistic test data for performance testing:

```python
# Generate 100K events for load testing
events = runtime.call_tool(
    "smart_faker",
    prompt="Event log with event_id, user_id, event_type, timestamp, payload",
    count=100000,
    output_format="jsonl",
    stream=True
)
```

### Use Case 4: Prototyping

Quick sample data for UI mockups:

```python
# Generate sample data for dashboard
dashboard_data = runtime.call_tool(
    "smart_faker",
    prompt='''
    Dashboard metrics with:
    - revenue: number
    - new_users: integer
    - active_sessions: integer
    - conversion_rate: percentage (0-100)
    - top_products: array of product names
    - date: date
    ''',
    count=30,  # 30 days of data
    additional_context="For a SaaS analytics dashboard"
)
```

### Use Case 5: Data Science

Create training/test datasets:

```python
# Generate labeled dataset for ML training
dataset = runtime.call_tool(
    "smart_faker",
    prompt='''
    Customer churn data with:
    - customer_id
    - tenure_months: integer (1-72)
    - monthly_charges: number (20-150)
    - total_charges: number
    - contract_type: month-to-month, one year, two year
    - payment_method: credit card, bank transfer, electronic check
    - churn: boolean (true if customer churned)
    ''',
    count=10000,
    output_format="csv",
    seed=2024
)
```

### Use Case 6: Documentation

Generate example data for API documentation:

```python
# Create example requests/responses for docs
api_example = runtime.call_tool(
    "smart_faker",
    prompt='''
    POST /api/orders request body:
    {
        "items": [{"product_id": string, "quantity": integer}],
        "shipping_address": {
            "street": string,
            "city": string,
            "state": string,
            "zip": string
        },
        "payment_method": string
    }
    ''',
    count=3,
    additional_context="For REST API documentation examples"
)
```

---

## Tips and Best Practices

1. **Be Specific**: The more detail in your prompt, the better the results
   ```python
   # Good
   "Employee records with employee_id (5 digits), first_name, last_name, department (Engineering/Sales/Marketing), annual_salary (50k-150k), hire_date (2020-2024)"

   # Less ideal
   "Employee data"
   ```

2. **Use Additional Context**: Provide domain information for better data
   ```python
   additional_context="For a healthcare provider. Include realistic medical terminology and HIPAA-compliant anonymized data."
   ```

3. **Choose Right Format**:
   - JSON: APIs, nested structures
   - CSV: Database imports, spreadsheets
   - JSONL: Log files, streaming, large datasets
   - Array: Python scripts, quick lists

4. **Use Seeds for Tests**: Always use seeds in test fixtures
   ```python
   seed=42  # Deterministic data for tests
   ```

5. **Stream Large Datasets**: For 10K+ records, use streaming
   ```python
   count=100000,
   output_format="jsonl",
   stream=True
   ```

---

## Comparison: Smart Faker vs Other Tools

| Feature | Smart Faker | fake_data_generator | llm_fake_data_generator |
|---------|-------------|---------------------|-------------------------|
| Plain English Input | ✅ Yes | ❌ No (schema only) | ✅ Yes (limited) |
| Code Snippet Input | ✅ Yes | ❌ No | ❌ No |
| JSON Schema | ✅ Yes | ✅ Yes | ✅ Yes |
| CSV Output | ✅ Yes | ❌ No | ❌ No |
| Streaming | ✅ Yes | ❌ No | ❌ No |
| LLM Interpretation | ✅ Yes | ❌ No | ✅ Yes |
| Fast Generation | ✅ Yes (Faker) | ✅ Yes (Faker) | ❌ No (LLM each) |
| Context Awareness | ✅ Yes | ❌ Limited | ✅ Yes |
| Reproducible (Seed) | ✅ Yes | ❌ No | ❌ No |

**Use Smart Faker when you need:**
- Flexible input formats
- Multiple output formats
- Large datasets with streaming
- Quick prototyping from descriptions
- Reproducible test data

---

## Troubleshooting

### LLM Not Available

The tool automatically falls back to pattern matching if LLM is unavailable:
```python
# Will still work with basic pattern matching
result = runtime.call_tool(
    "smart_faker",
    prompt="user with name, email, age",
    count=5
)
```

### Faker Library Not Installed

Falls back to basic random generation:
```bash
pip install faker  # Recommended for best results
```

### Schema Not Detected Correctly

Provide more explicit schema or use JSON Schema format:
```python
# Instead of vague
prompt="user data"

# Be explicit
prompt='''
{
  "type": "object",
  "properties": {
    "user_id": {"type": "integer"},
    "username": {"type": "string"},
    "email": {"type": "string", "format": "email"}
  }
}
'''
```

---

## Integration Examples

### With Testing Framework

```python
import pytest
from node_runtime import NodeRuntime

@pytest.fixture
def test_users():
    runtime = NodeRuntime()
    result = runtime.call_tool(
        "smart_faker",
        prompt="User with id, username, email, is_active",
        count=10,
        seed=12345  # Reproducible
    )
    return result['data']

def test_user_processing(test_users):
    for user in test_users:
        assert 'email' in user
        assert '@' in user['email']
```

### With Data Pipeline

```python
from node_runtime import NodeRuntime
import pandas as pd

runtime = NodeRuntime()

# Generate large dataset
result = runtime.call_tool(
    "smart_faker",
    prompt="Sales transaction with date, product, quantity, price, customer_id",
    count=10000,
    output_format="csv",
    seed=2024
)

# Load into pandas
df = pd.read_csv(io.StringIO(result['data']))

# Process with pandas
df['total'] = df['quantity'] * df['price']
df['date'] = pd.to_datetime(df['date'])
```

### With API Mocking

```python
from flask import Flask, jsonify
from node_runtime import NodeRuntime

app = Flask(__name__)
runtime = NodeRuntime()

@app.route('/api/users')
def get_users():
    result = runtime.call_tool(
        "smart_faker",
        prompt="User with id, name, email, role",
        count=20,
        seed=42  # Same data each request
    )
    return jsonify(result['data'])
```

---

## Performance

- **Small datasets (< 100 items)**: < 1 second
- **Medium datasets (100-1000 items)**: 1-5 seconds
- **Large datasets (1000-10000 items)**: 5-30 seconds
- **Streaming (10K+ items)**: Constant memory, ~1000 items/second

LLM interpretation happens once at the start, then Faker generates data efficiently.

---

## Contributing

Found a bug or want to add features? Please submit issues or pull requests to the repository.

---

## License

Part of the mostlylucid DiSE project.
