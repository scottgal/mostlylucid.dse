"""
Networking Toolkit

Comprehensive low-level networking capabilities including:
- Binary protocol encoding/decoding
- UDP/TCP client and server tools
- Resilience (retry, circuit breaker, rate limiting)
- Network utilities (DNS, port scanning, etc.)
"""

__version__ = "1.0.0"

from .binary_codec import BinaryEncoder, BinaryDecoder, StringSerializer
from .udp_tools import UDPListener, UDPSender
from .tcp_tools import TCPServer, TCPClient
from .resilience import ResilientCaller, RateLimiter, CircuitBreaker
from .network_utils import DNSResolver, PortScanner, NetworkDiagnostics

__all__ = [
    "BinaryEncoder",
    "BinaryDecoder",
    "StringSerializer",
    "UDPListener",
    "UDPSender",
    "TCPServer",
    "TCPClient",
    "ResilientCaller",
    "RateLimiter",
    "CircuitBreaker",
    "DNSResolver",
    "PortScanner",
    "NetworkDiagnostics",
]
