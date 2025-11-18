# Code Evolver - OpenTelemetry Observability Stack

Complete observability solution replacing `optimized_perf_tracker` with industry-standard OpenTelemetry + Loki + Drift Detection.

## 🎯 Architecture Overview

```
┌─────────────────────┐
│  Code Evolver App   │
│  (Tool Execution)   │
└──────────┬──────────┘
           │ OpenTelemetry SDK
           │ (Traces, Metrics, Logs)
           ▼
┌─────────────────────────────────────────┐
│   OpenTelemetry Collector (OTLP)        │
│   - Receives telemetry                  │
│   - Processes & enriches                │
│   - Routes to backends                  │
└──┬──────────┬──────────┬───────────────┘
   │          │          │
   ▼          ▼          ▼
┌──────┐  ┌──────┐  ┌──────────┐
│ Loki │  │Prome-│  │ Jaeger   │
│(Logs)│  │theus │  │ (Traces) │
└──────┘  │(Metr │  └──────────┘
          │ics)  │
          └──────┘
               │
               ▼
        ┌──────────────┐
        │   Grafana    │
        │ (Dashboards) │
        └──────────────┘
               │
               ▼
        ┌──────────────┐
        │ Drift        │
        │ Detector     │
        └──────────────┘
```

## 📦 Components

### 1. **TelemetryTracker** (`telemetry_tracker.py`)
Replaces `optimized_perf_tracker.py` with OpenTelemetry:

- **Traces**: Distributed tracing with parent-child relationships
- **Metrics**: Counters, histograms, gauges
- **Logs**: Structured logging to Loki
- **Drift Detection**: Built-in performance monitoring

### 2. **DriftDetector** (`drift_detector.py`)
Performance drift and anomaly detection:

- Statistical analysis (z-scores, percentiles)
- Pattern clustering integration
- Baseline tracking
- Alert generation

### 3. **Docker Compose Stack** (`docker-compose.observability.yaml`)
All required services:

- **PostgreSQL**: Primary database
- **Qdrant**: Vector database for embeddings
- **Loki**: Log aggregation
- **Prometheus**: Metrics storage
- **OpenTelemetry Collector**: Telemetry pipeline
- **Grafana**: Visualization
- **Jaeger**: Distributed tracing (optional)

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements-telemetry.txt
```

### 2. Configure Environment

```bash
# Copy example environment file
cp .env.observability.example .env.observability

# Edit with your settings
nano .env.observability
```

### 3. Start Observability Stack

```bash
# Start all services
docker-compose -f docker-compose.observability.yaml up -d

# Check status
docker-compose -f docker-compose.observability.yaml ps

# View logs
docker-compose -f docker-compose.observability.yaml logs -f
```

### 4. Configure Application

Update `code_evolver/config/telemetry.yaml`:

```yaml
telemetry:
  enabled: true
  service_name: "code-evolver"

  # Use local OTLP collector
  traces_endpoint: "http://localhost:4318/v1/traces"
  metrics_endpoint: "http://localhost:4318/v1/metrics"

  # Loki for logs
  loki_url: "http://localhost:3100/loki/api/v1/push"

  # Enable drift detection
  drift_detection_enabled: true
  drift_threshold: 0.15  # 15%
```

### 5. Instrument Your Code

Replace old perfcatcher calls:

**Before** (old perfcatcher):
```python
from src.optimized_perf_tracker import track_tool_call, end_tool_call

record_id = track_tool_call("my_tool", {"param": "value"})
try:
    # Do work
    result = do_something()
finally:
    end_tool_call(record_id)
```

**After** (OpenTelemetry):
```python
from src.telemetry_tracker import track_tool_call

with track_tool_call("my_tool", {"param": "value"}) as span:
    # Do work
    result = do_something()

    # Add custom attributes
    span.set_attribute("result.count", len(result))
```

## 🎛️ Configuration

### Telemetry Configuration (`telemetry.yaml`)

```yaml
telemetry:
  enabled: true
  service_name: "code-evolver"
  environment: "production"

  # Traces
  traces_enabled: true
  traces_exporter: "otlp"
  traces_endpoint: "http://localhost:4318/v1/traces"
  traces_protocol: "http"  # or "grpc"
  traces_sample_rate: 1.0  # 0.0 to 1.0

  # Metrics
  metrics_enabled: true
  metrics_exporter: "otlp"
  metrics_endpoint: "http://localhost:4318/v1/metrics"
  metrics_export_interval_ms: 30000

  # Logs
  loki_enabled: true
  loki_url: "http://localhost:3100/loki/api/v1/push"
  log_level: "INFO"

  # Drift Detection
  drift_detection_enabled: true
  drift_threshold: 0.15
  drift_window_size: 100
```

### Using External Services

#### Grafana Cloud

```yaml
telemetry:
  traces_endpoint: "https://otlp-gateway-prod-us-east-0.grafana.net/otlp/v1/traces"
  metrics_endpoint: "https://otlp-gateway-prod-us-east-0.grafana.net/otlp/v1/metrics"
  loki_url: "https://logs-prod-us-central1.grafana.net/loki/api/v1/push"
```

#### Honeycomb

```yaml
telemetry:
  traces_endpoint: "https://api.honeycomb.io/v1/traces"
  # Add API key via environment
```

#### New Relic

```yaml
telemetry:
  traces_endpoint: "https://otlp.nr-data.net/v1/traces"
  metrics_endpoint: "https://otlp.nr-data.net/v1/metrics"
```

#### Datadog

```yaml
telemetry:
  traces_endpoint: "http://localhost:4318/v1/traces"  # Datadog Agent
  metrics_endpoint: "http://localhost:4318/v1/metrics"
```

## 📊 Drift Detection

### How It Works

1. **Baseline Establishment**
   - Collects performance samples for each tool
   - Calculates mean, std dev, percentiles

2. **Anomaly Detection**
   - Uses z-score analysis
   - Flags outliers (default: 3 std devs)

3. **Drift Calculation**
   - Compares recent window vs baseline
   - Alerts on threshold breach (default: 15%)

4. **Pattern Analysis**
   - Integrates with `pattern_clusterer.py`
   - Identifies usage pattern changes

### Usage

```python
from src.drift_detector import get_detector
from src.telemetry_tracker import get_tracker

# Get instances
tracker = get_tracker()
detector = get_detector(tracker, rag_memory)

# Record measurements (automatic via telemetry_tracker)
with tracker.track_tool_call("my_tool", params) as span:
    # Work happens
    pass

# Check drift
drift_events = detector.get_drift_report(tool_name="my_tool")

# Analyze patterns
clusters = detector.analyze_patterns(target_tool="my_tool")

# Get baseline stats
stats = detector.get_baseline_stats()
```

### Drift Alerts

Drift events include:

- `timestamp`: When detected
- `tool_name`: Affected tool
- `drift_type`: performance, pattern, anomaly
- `severity`: low, medium, high, critical
- `baseline_value`: Historical average
- `current_value`: Recent measurement
- `deviation_percent`: How much drift
- `description`: Human-readable explanation

## 📈 Accessing Dashboards

### Grafana (Visualization)

- **URL**: http://localhost:3000
- **Default Login**: admin / admin
- **Dashboards**: Auto-provisioned
- **Data Sources**: Loki, Prometheus, Jaeger

### Prometheus (Metrics)

- **URL**: http://localhost:9090
- **Query Language**: PromQL
- **Retention**: 30 days

### Jaeger (Traces)

- **URL**: http://localhost:16686
- **Search**: By service, operation, tags
- **Dependency Graph**: Service relationships

### Loki (Logs)

- **URL**: http://localhost:3100
- **Query Language**: LogQL
- **Accessed via**: Grafana

## 🔍 Querying Data

### LogQL (Loki Logs)

```logql
# All logs from code-evolver
{application="code-evolver"}

# Errors only
{application="code-evolver"} |= "ERROR"

# Specific tool
{application="code-evolver", tool_name="llm_generate"}

# With duration filter
{application="code-evolver"} | json | duration_ms > 5000
```

### PromQL (Prometheus Metrics)

```promql
# Total tool calls
sum(tool_calls_total)

# Tool call rate
rate(tool_calls_total[5m])

# P95 latency
histogram_quantile(0.95, tool_duration_bucket)

# Error rate
rate(tool_errors_total[5m]) / rate(tool_calls_total[5m])
```

## 🛠️ Development

### Running Tests

```bash
pytest tests/test_telemetry_tracker.py
pytest tests/test_drift_detector.py
```

### Local Development (without Docker)

1. **Install dependencies**:
   ```bash
   pip install -r requirements-telemetry.txt
   ```

2. **Use console exporters** (telemetry.yaml):
   ```yaml
   telemetry:
     traces_exporter: "console"
     metrics_exporter: "console"
     loki_enabled: false
   ```

3. **Run your code**:
   ```bash
   python your_script.py
   ```

## 🔄 Migration from Old Perfcatcher

### Step 1: Update Imports

```python
# Old
from src.optimized_perf_tracker import track_tool_call, end_tool_call

# New
from src.telemetry_tracker import track_tool_call
```

### Step 2: Update Usage Pattern

```python
# Old
record_id = track_tool_call("tool", params)
try:
    result = do_work()
finally:
    end_tool_call(record_id)

# New
with track_tool_call("tool", params) as span:
    result = do_work()
    span.set_attribute("result.size", len(result))
```

### Step 3: Update Configuration

- Rename `tool_perf_limits.yaml` → `telemetry.yaml`
- Use new YAML structure (see examples above)

### Step 4: Deploy New Stack

```bash
docker-compose -f docker-compose.observability.yaml up -d
```

## 📊 Performance Impact

### Overhead Comparison

| Component | CPU | Memory | Latency |
|-----------|-----|--------|---------|
| Old perfcatcher | ~1% | ~50MB | ~0.1ms |
| OpenTelemetry SDK | ~2% | ~100MB | ~0.2ms |
| OTLP Collector | ~3% | ~200MB | N/A |

**Total overhead**: ~5% CPU, ~350MB RAM

### Optimization Tips

1. **Sampling**: Reduce `traces_sample_rate`
2. **Batching**: Increase batch sizes
3. **Filtering**: Use tail-based sampling
4. **Local only**: Disable remote exporters in dev

## 🐛 Troubleshooting

### Issue: No traces appearing

**Check**:
1. Is OTLP collector running?
   ```bash
   curl http://localhost:13133
   ```

2. Are traces being sent?
   ```bash
   docker logs code-evolver-otel-collector
   ```

3. Check telemetry config:
   ```yaml
   traces_enabled: true
   traces_endpoint: "http://localhost:4318/v1/traces"
   ```

### Issue: Loki not receiving logs

**Check**:
1. Loki health:
   ```bash
   curl http://localhost:3100/ready
   ```

2. Python logging level:
   ```yaml
   log_level: "INFO"  # Not "ERROR"
   ```

3. Loki handler installed:
   ```bash
   pip show python-logging-loki
   ```

### Issue: High memory usage

**Solution**:
1. Reduce batch sizes in `otel-collector-config.yaml`
2. Enable sampling: `traces_sample_rate: 0.1`
3. Increase export intervals: `metrics_export_interval_ms: 60000`

## 🔒 Security

### Production Recommendations

1. **Change default passwords** (`.env.observability`)
2. **Enable TLS** for all endpoints
3. **Use authentication** for Grafana/Prometheus
4. **Network isolation** (separate Docker network)
5. **Secret management** (use vault/secrets manager)

### Example: TLS Configuration

```yaml
# telemetry.yaml
telemetry:
  traces_endpoint: "https://secure-collector:4318/v1/traces"
  tls:
    cert_file: "/path/to/cert.pem"
    key_file: "/path/to/key.pem"
    ca_file: "/path/to/ca.pem"
```

## 📚 Additional Resources

- [OpenTelemetry Docs](https://opentelemetry.io/docs/)
- [Loki Documentation](https://grafana.com/docs/loki/)
- [Prometheus Docs](https://prometheus.io/docs/)
- [Grafana Dashboards](https://grafana.com/docs/)
- [Jaeger Tracing](https://www.jaegertracing.io/docs/)

## 🤝 Support

For issues or questions:
1. Check logs: `docker-compose logs`
2. Verify config: `config/telemetry.yaml`
3. Test connectivity: `curl` health endpoints

---

**Built with ❤️ using OpenTelemetry, Loki, and modern observability practices**
