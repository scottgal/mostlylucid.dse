# Networking Toolkit

A comprehensive low-level networking toolkit for binary protocols, UDP/TCP communication, and network operations.

## Features

- **Binary Protocol Support**: Encode/decode binary data using struct, msgpack, protobuf, JSON, and custom formats
- **UDP Operations**: Listen for and send UDP datagrams with binary payload support
- **TCP Operations**: Full-featured TCP client and server with connection pooling
- **Resilience**: Built-in retry logic, circuit breaker pattern, and rate limiting
- **DNS Tools**: DNS resolution and reverse lookup
- **Network Utilities**: Port scanning, connection testing, network diagnostics

## Tool-Based Architecture

All networking operations are exposed as callable tools:

```python
# Example: Listen for binary UDP packets and decode them
call_tool("udp_listener", {
    "port": 5000,
    "decoder_tool": "binary_decoder",
    "decoder_config": {"format": "struct", "pattern": "!IHH"}
})

# Example: Send binary UDP packet
call_tool("udp_sender", {
    "host": "192.168.1.100",
    "port": 5000,
    "data": "Hello",
    "encoder_tool": "binary_encoder",
    "encoder_config": {"format": "msgpack"}
})
```

## Components

### Binary Encoding/Decoding
- `binary_encoder` - Encode data to binary formats (struct, msgpack, protobuf, etc.)
- `binary_decoder` - Decode binary data to Python objects
- `string_serializer` - String encoding/decoding (UTF-8, ASCII, Base64, Hex)

### UDP Tools
- `udp_listener` - Listen for UDP packets on a port
- `udp_sender` - Send UDP datagrams
- `udp_server` - Long-running UDP server with callback support

### TCP Tools
- `tcp_server` - TCP server with binary protocol support
- `tcp_client` - TCP client with connection pooling
- `socket_manager` - Low-level socket operations

### Resilience & Rate Limiting
- `resilient_caller` - Wrap any network call with retry/circuit breaker
- `rate_limiter` - Token bucket and sliding window rate limiting
- `connection_pool` - Connection pooling for TCP connections

### Network Utilities
- `dns_resolver` - DNS lookups and reverse DNS
- `port_scanner` - Check if ports are open
- `network_diagnostics` - Ping, traceroute, bandwidth tests

## Binary Format Support

### Struct Format
Python's struct module for C-style binary data:
```python
# Pack/unpack binary data
encoder_config = {
    "format": "struct",
    "pattern": "!IHH",  # Big-endian: uint32, uint16, uint16
    "fields": ["id", "type", "length"]
}
```

### MessagePack
Efficient binary serialization:
```python
encoder_config = {"format": "msgpack"}
```

### Protocol Buffers
Schema-based binary format:
```python
encoder_config = {
    "format": "protobuf",
    "schema": "message.proto",
    "message_type": "MyMessage"
}
```

### Custom Formats
Define your own binary protocol:
```python
encoder_config = {
    "format": "custom",
    "schema": {
        "header": {"type": "uint32", "endian": "big"},
        "payload_length": {"type": "uint16", "endian": "little"},
        "payload": {"type": "bytes", "length_field": "payload_length"}
    }
}
```

## Resilience Features

### Retry Logic
```python
resilient_config = {
    "max_retries": 3,
    "backoff": "exponential",  # exponential, linear, constant
    "initial_delay": 1.0,
    "max_delay": 30.0,
    "jitter": True
}
```

### Circuit Breaker
```python
circuit_breaker_config = {
    "failure_threshold": 5,
    "success_threshold": 2,
    "timeout": 60.0,
    "half_open_max_calls": 3
}
```

### Rate Limiting
```python
rate_limit_config = {
    "algorithm": "token_bucket",  # token_bucket, sliding_window, fixed_window
    "rate": 100,  # requests per window
    "window": 60,  # seconds
    "burst": 20   # burst capacity
}
```

## Usage Examples

### Example 1: Binary UDP Listener

```python
# Listen for binary packets and decode with struct
result = call_tool("udp_listener", {
    "port": 9000,
    "max_packets": 10,
    "timeout": 30,
    "decoder": {
        "format": "struct",
        "pattern": "!IHH",
        "fields": ["timestamp", "sensor_id", "value"]
    }
})

# Result:
# {
#   "success": True,
#   "packets_received": 5,
#   "packets": [
#     {"timestamp": 1234567890, "sensor_id": 1, "value": 42},
#     ...
#   ]
# }
```

### Example 2: TCP Server with Binary Protocol

```python
# Start TCP server that accepts binary data
result = call_tool("tcp_server", {
    "port": 8080,
    "protocol": "binary",
    "decoder": {"format": "msgpack"},
    "handler": "echo",  # or custom handler tool
    "max_connections": 100
})
```

### Example 3: Resilient HTTP-like Request

```python
# Send TCP request with automatic retry
result = call_tool("tcp_client", {
    "host": "api.example.com",
    "port": 443,
    "data": {"action": "get_data", "id": 123},
    "encoder": {"format": "msgpack"},
    "decoder": {"format": "msgpack"},
    "resilience": {
        "max_retries": 3,
        "timeout": 5.0,
        "circuit_breaker": True
    }
})
```

### Example 4: Port Scanning

```python
# Scan ports on a host
result = call_tool("port_scanner", {
    "host": "192.168.1.1",
    "ports": [22, 80, 443, 8080],
    "timeout": 2.0,
    "parallel": True
})

# Result:
# {
#   "success": True,
#   "open_ports": [80, 443],
#   "closed_ports": [22, 8080]
# }
```

## Configuration

Add networking configuration to `config.yaml`:

```yaml
networking:
  udp:
    default_buffer_size: 65536
    default_timeout: 30

  tcp:
    connection_pool_size: 100
    keepalive: true
    nodelay: true
    default_timeout: 30

  resilience:
    default_max_retries: 3
    default_backoff: exponential
    circuit_breaker_enabled: true

  rate_limiting:
    enabled: true
    default_algorithm: token_bucket
    default_rate: 100
    default_window: 60

  security:
    allow_raw_sockets: false
    allowed_ports: [1024-65535]
    blocked_hosts: []
```

## Security Considerations

- Default port range restrictions (>1024)
- Configurable host allow/block lists
- Optional TLS/SSL support for TCP connections
- Rate limiting to prevent abuse
- Buffer overflow protection
- Connection limits

## Dependencies

- `msgpack` - MessagePack serialization
- `protobuf` - Protocol Buffers support (optional)
- Standard library: `socket`, `struct`, `asyncio`, `threading`
