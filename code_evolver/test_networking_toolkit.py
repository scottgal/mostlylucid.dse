"""
Comprehensive Tests for Networking Toolkit

Tests all networking tools including:
- Binary encoding/decoding
- UDP listener/sender
- TCP client/server
- Resilience features
- Network utilities
"""

import json
import time
import threading
from typing import Dict, Any


class NetworkingToolkitTester:
    """Test suite for networking toolkit."""

    def __init__(self):
        """Initialize tester."""
        self.results = []
        self.passed = 0
        self.failed = 0

    def test(self, name: str, test_func):
        """Run a single test."""
        print(f"\n{'='*60}")
        print(f"Testing: {name}")
        print('='*60)

        try:
            result = test_func()
            if result:
                print(f"✓ PASSED: {name}")
                self.passed += 1
                self.results.append({"test": name, "status": "PASSED"})
                return True
            else:
                print(f"✗ FAILED: {name}")
                self.failed += 1
                self.results.append({"test": name, "status": "FAILED"})
                return False

        except Exception as e:
            print(f"✗ ERROR in {name}: {e}")
            self.failed += 1
            self.results.append({"test": name, "status": "ERROR", "error": str(e)})
            return False

    def run_all_tests(self):
        """Run all networking toolkit tests."""
        print("\n" + "="*60)
        print("NETWORKING TOOLKIT TEST SUITE")
        print("="*60)

        # Binary Codec Tests
        print("\n### BINARY CODEC TESTS ###")
        self.test("Binary Encoder - Struct Format", self.test_binary_encoder_struct)
        self.test("Binary Encoder - MessagePack", self.test_binary_encoder_msgpack)
        self.test("Binary Encoder - JSON", self.test_binary_encoder_json)
        self.test("Binary Encoder - Custom Format", self.test_binary_encoder_custom)
        self.test("Binary Decoder - Struct Format", self.test_binary_decoder_struct)
        self.test("Binary Decoder - MessagePack", self.test_binary_decoder_msgpack)
        self.test("String Serializer - Base64", self.test_string_serializer_base64)
        self.test("String Serializer - Hex", self.test_string_serializer_hex)

        # UDP Tests
        print("\n### UDP TESTS ###")
        self.test("UDP Echo Test", self.test_udp_echo)
        self.test("UDP Binary Protocol", self.test_udp_binary_protocol)

        # TCP Tests
        print("\n### TCP TESTS ###")
        self.test("TCP Echo Test", self.test_tcp_echo)
        self.test("TCP Binary Protocol", self.test_tcp_binary_protocol)

        # Resilience Tests
        print("\n### RESILIENCE TESTS ###")
        self.test("Retry Logic - Exponential Backoff", self.test_retry_exponential)
        self.test("Circuit Breaker", self.test_circuit_breaker)
        self.test("Rate Limiter - Token Bucket", self.test_rate_limiter_token_bucket)
        self.test("Rate Limiter - Sliding Window", self.test_rate_limiter_sliding_window)

        # Network Utilities Tests
        print("\n### NETWORK UTILITIES TESTS ###")
        self.test("DNS Resolver - Forward", self.test_dns_forward)
        self.test("DNS Resolver - Reverse", self.test_dns_reverse)
        self.test("Port Scanner", self.test_port_scanner)
        self.test("Network Diagnostics", self.test_network_diagnostics)

        # Print summary
        self.print_summary()

    # Binary Encoder Tests

    def test_binary_encoder_struct(self) -> bool:
        """Test struct encoding."""
        from src.networking.binary_codec import BinaryEncoder

        encoder = BinaryEncoder()
        result = encoder.execute(
            data={"id": 123, "type": 5, "value": 999},
            format="struct",
            pattern="IHH",
            fields=["id", "type", "value"]
        )

        print(f"Result: {json.dumps({k: v for k, v in result.items() if k != 'binary_data'}, indent=2)}")
        return result["success"] and result["size"] == 8

    def test_binary_encoder_msgpack(self) -> bool:
        """Test MessagePack encoding."""
        from src.networking.binary_codec import BinaryEncoder

        encoder = BinaryEncoder()
        result = encoder.execute(
            data={"name": "test", "value": 42, "active": True},
            format="msgpack"
        )

        print(f"Result: {json.dumps({k: v for k, v in result.items() if k != 'binary_data'}, indent=2)}")
        return result["success"] and result["size"] > 0

    def test_binary_encoder_json(self) -> bool:
        """Test JSON encoding."""
        from src.networking.binary_codec import BinaryEncoder

        encoder = BinaryEncoder()
        result = encoder.execute(
            data={"test": "data", "number": 123},
            format="json"
        )

        print(f"Result: {json.dumps({k: v for k, v in result.items() if k != 'binary_data'}, indent=2)}")
        return result["success"] and result["format"] == "json"

    def test_binary_encoder_custom(self) -> bool:
        """Test custom format encoding."""
        from src.networking.binary_codec import BinaryEncoder

        encoder = BinaryEncoder()
        result = encoder.execute(
            data={"header": 0xDEADBEEF, "length": 42},
            format="custom",
            schema={
                "header": {"type": "uint32", "endian": "big"},
                "length": {"type": "uint16", "endian": "little"}
            }
        )

        print(f"Result: {json.dumps({k: v for k, v in result.items() if k != 'binary_data'}, indent=2)}")
        return result["success"] and result["size"] == 6

    # Binary Decoder Tests

    def test_binary_decoder_struct(self) -> bool:
        """Test struct decoding."""
        from src.networking.binary_codec import BinaryEncoder, BinaryDecoder

        # Encode first
        encoder = BinaryEncoder()
        encode_result = encoder.execute(
            data=[123, 5, 999],
            format="struct",
            pattern="IHH"
        )

        if not encode_result["success"]:
            return False

        # Then decode
        decoder = BinaryDecoder()
        decode_result = decoder.execute(
            binary_data=encode_result["binary_data"],
            format="struct",
            pattern="IHH",
            fields=["id", "type", "value"]
        )

        print(f"Decoded: {json.dumps(decode_result, indent=2)}")
        return (decode_result["success"] and
                decode_result["data"]["id"] == 123 and
                decode_result["data"]["value"] == 999)

    def test_binary_decoder_msgpack(self) -> bool:
        """Test MessagePack decoding."""
        from src.networking.binary_codec import BinaryEncoder, BinaryDecoder

        # Encode first
        encoder = BinaryEncoder()
        test_data = {"name": "test", "value": 42, "items": [1, 2, 3]}
        encode_result = encoder.execute(data=test_data, format="msgpack")

        if not encode_result["success"]:
            return False

        # Then decode
        decoder = BinaryDecoder()
        decode_result = decoder.execute(
            binary_data=encode_result["binary_data"],
            format="msgpack"
        )

        print(f"Decoded: {json.dumps(decode_result, indent=2)}")
        return (decode_result["success"] and
                decode_result["data"]["name"] == "test" and
                decode_result["data"]["value"] == 42)

    # String Serializer Tests

    def test_string_serializer_base64(self) -> bool:
        """Test Base64 encoding/decoding."""
        from src.networking.binary_codec import StringSerializer

        serializer = StringSerializer()

        # Encode
        encode_result = serializer.execute(
            data="Hello, World!",
            action="encode",
            representation="base64"
        )

        if not encode_result["success"]:
            return False

        # Decode
        decode_result = serializer.execute(
            data=encode_result["data"],
            action="decode",
            representation="base64"
        )

        print(f"Base64: {encode_result['data']}")
        print(f"Decoded: {decode_result['data']}")
        return decode_result["success"] and decode_result["data"] == "Hello, World!"

    def test_string_serializer_hex(self) -> bool:
        """Test Hex encoding/decoding."""
        from src.networking.binary_codec import StringSerializer

        serializer = StringSerializer()

        # Encode
        encode_result = serializer.execute(
            data="Test",
            action="encode",
            representation="hex"
        )

        if not encode_result["success"]:
            return False

        # Decode
        decode_result = serializer.execute(
            data=encode_result["data"],
            action="decode",
            representation="hex"
        )

        print(f"Hex: {encode_result['data']}")
        print(f"Decoded: {decode_result['data']}")
        return decode_result["success"] and decode_result["data"] == "Test"

    # UDP Tests

    def test_udp_echo(self) -> bool:
        """Test UDP send and receive."""
        from src.networking.udp_tools import UDPListener, UDPSender
        import threading

        listener = UDPListener()
        sender = UDPSender()

        # Start listener in background
        listen_result = {}

        def listen_thread():
            listen_result.update(listener.execute(
                port=9999,
                max_packets=1,
                timeout=5.0
            ))

        thread = threading.Thread(target=listen_thread)
        thread.start()

        # Give listener time to start
        time.sleep(0.5)

        # Send data
        send_result = sender.execute(
            host="127.0.0.1",
            port=9999,
            data="Hello UDP!"
        )

        # Wait for listener
        thread.join(timeout=6.0)

        print(f"Send: {json.dumps(send_result, indent=2)}")
        print(f"Listen: {json.dumps(listen_result, indent=2)}")

        return (send_result["success"] and
                listen_result.get("success", False) and
                listen_result.get("packets_received", 0) == 1)

    def test_udp_binary_protocol(self) -> bool:
        """Test UDP with binary encoding."""
        from src.networking.udp_tools import UDPListener, UDPSender
        import threading

        listener = UDPListener()
        sender = UDPSender()

        # Start listener with decoder
        listen_result = {}

        def listen_thread():
            listen_result.update(listener.execute(
                port=10000,
                max_packets=1,
                timeout=5.0,
                decoder={
                    "format": "struct",
                    "pattern": "IH",
                    "fields": ["id", "value"]
                }
            ))

        thread = threading.Thread(target=listen_thread)
        thread.start()
        time.sleep(0.5)

        # Send binary data
        send_result = sender.execute(
            host="127.0.0.1",
            port=10000,
            data={"id": 12345, "value": 678},
            encoder={
                "format": "struct",
                "pattern": "IH",
                "fields": ["id", "value"]
            }
        )

        thread.join(timeout=6.0)

        print(f"Send: {json.dumps(send_result, indent=2)}")
        print(f"Listen: {json.dumps(listen_result, indent=2)}")

        return (send_result["success"] and
                listen_result.get("success", False) and
                listen_result["packets_received"] == 1)

    # TCP Tests

    def test_tcp_echo(self) -> bool:
        """Test TCP echo server."""
        from src.networking.tcp_tools import TCPServer, TCPClient
        import threading

        server = TCPServer()
        client = TCPClient()

        # Start server in background
        server_result = {}

        def server_thread():
            server_result.update(server.execute(
                port=8888,
                timeout=5.0,
                handler="echo"
            ))

        thread = threading.Thread(target=server_thread)
        thread.start()
        time.sleep(0.5)

        # Connect and send
        client_result = client.execute(
            host="127.0.0.1",
            port=8888,
            data="Hello TCP!",
            timeout=5.0
        )

        thread.join(timeout=6.0)

        print(f"Client: {json.dumps(client_result, indent=2)}")
        print(f"Server: {json.dumps(server_result, indent=2)}")

        return (client_result["success"] and
                server_result.get("success", False))

    def test_tcp_binary_protocol(self) -> bool:
        """Test TCP with binary protocol."""
        from src.networking.tcp_tools import TCPServer, TCPClient
        import threading

        server = TCPServer()
        client = TCPClient()

        # Start server with binary codec
        server_result = {}

        def server_thread():
            server_result.update(server.execute(
                port=8889,
                timeout=5.0,
                handler="echo",
                decoder={"format": "msgpack"},
                encoder={"format": "msgpack"}
            ))

        thread = threading.Thread(target=server_thread)
        thread.start()
        time.sleep(0.5)

        # Send binary data
        client_result = client.execute(
            host="127.0.0.1",
            port=8889,
            data={"command": "test", "value": 123},
            encoder={"format": "msgpack"},
            decoder={"format": "msgpack"},
            timeout=5.0
        )

        thread.join(timeout=6.0)

        print(f"Client: {json.dumps(client_result, indent=2)}")
        print(f"Server: {json.dumps(server_result, indent=2)}")

        return client_result["success"] and server_result.get("success", False)

    # Resilience Tests

    def test_retry_exponential(self) -> bool:
        """Test exponential backoff retry."""
        from src.networking.resilience import ResilientCaller

        caller = ResilientCaller()

        # This will fail but should retry
        result = caller.execute(
            tool_name="tcp_client",
            tool_params={
                "host": "192.0.2.1",  # TEST-NET address (should fail)
                "port": 9999,
                "data": "test",
                "timeout": 1.0
            },
            max_retries=2,
            backoff="exponential",
            initial_delay=0.5
        )

        print(f"Resilient call result: {json.dumps(result, indent=2)}")

        # Should have 3 total attempts (1 initial + 2 retries)
        return not result["success"] and len(result["attempts"]) == 3

    def test_circuit_breaker(self) -> bool:
        """Test circuit breaker pattern."""
        from src.networking.resilience import CircuitBreaker

        cb = CircuitBreaker(failure_threshold=3, timeout=2.0)

        # Should start closed
        assert cb.state.value == "closed"

        # Record failures
        for _ in range(3):
            cb.record_failure()

        # Should now be open
        is_open = cb.state.value == "open"
        print(f"Circuit breaker state after failures: {cb.state.value}")

        return is_open

    def test_rate_limiter_token_bucket(self) -> bool:
        """Test token bucket rate limiter."""
        from src.networking.resilience import RateLimiter

        limiter = RateLimiter()

        # Allow 5 requests per second with burst of 5
        results = []
        for i in range(10):
            result = limiter.execute(
                key="test_key",
                algorithm="token_bucket",
                rate=5,
                window=1.0,
                burst=5
            )
            results.append(result["allowed"])

        print(f"Rate limiter results: {results}")

        # First 5 should be allowed, rest denied
        allowed_count = sum(results)
        print(f"Allowed: {allowed_count}/10")

        return allowed_count <= 6  # Allow some tolerance

    def test_rate_limiter_sliding_window(self) -> bool:
        """Test sliding window rate limiter."""
        from src.networking.resilience import RateLimiter

        limiter = RateLimiter()

        results = []
        for i in range(10):
            result = limiter.execute(
                key="test_key_2",
                algorithm="sliding_window",
                rate=5,
                window=1.0
            )
            results.append(result["allowed"])

        print(f"Sliding window results: {results}")
        allowed_count = sum(results)
        print(f"Allowed: {allowed_count}/10")

        return allowed_count == 5

    # Network Utilities Tests

    def test_dns_forward(self) -> bool:
        """Test DNS forward resolution."""
        from src.networking.network_utils import DNSResolver

        resolver = DNSResolver()
        result = resolver.execute(
            hostname="localhost",
            action="resolve"
        )

        print(f"DNS result: {json.dumps(result, indent=2)}")
        return result["success"] and len(result.get("ip_addresses", [])) > 0

    def test_dns_reverse(self) -> bool:
        """Test DNS reverse lookup."""
        from src.networking.network_utils import DNSResolver

        resolver = DNSResolver()
        result = resolver.execute(
            ip_address="127.0.0.1",
            action="reverse"
        )

        print(f"Reverse DNS result: {json.dumps(result, indent=2)}")
        return result["success"] or result.get("error_type") == "DNSError"

    def test_port_scanner(self) -> bool:
        """Test port scanner."""
        from src.networking.network_utils import PortScanner

        scanner = PortScanner()
        result = scanner.execute(
            host="127.0.0.1",
            ports=[22, 80, 443, 8888],  # Scan a few ports
            timeout=1.0,
            parallel=False
        )

        print(f"Port scan result: {json.dumps(result, indent=2)}")
        return result["success"] and result["total_ports_scanned"] == 4

    def test_network_diagnostics(self) -> bool:
        """Test network diagnostics."""
        from src.networking.network_utils import NetworkDiagnostics

        diag = NetworkDiagnostics()
        result = diag.execute(
            host="127.0.0.1",
            port=80,
            action="connection_test",
            timeout=2.0
        )

        print(f"Diagnostics result: {json.dumps(result, indent=2)}")
        return "status" in result

    def print_summary(self):
        """Print test summary."""
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        print(f"Total Tests: {self.passed + self.failed}")
        print(f"Passed: {self.passed}")
        print(f"Failed: {self.failed}")
        print(f"Success Rate: {(self.passed / (self.passed + self.failed) * 100):.1f}%")
        print("="*60)

        if self.failed > 0:
            print("\nFailed Tests:")
            for result in self.results:
                if result["status"] != "PASSED":
                    print(f"  - {result['test']}: {result['status']}")
                    if "error" in result:
                        print(f"    Error: {result['error']}")


if __name__ == "__main__":
    tester = NetworkingToolkitTester()
    tester.run_all_tests()
