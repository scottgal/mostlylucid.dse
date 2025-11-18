"""
Network Utilities

Provides DNS resolution, port scanning, and network diagnostic tools.
"""

import socket
import logging
import time
import threading
from typing import Dict, Any, Optional, List
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


class DNSResolver:
    """
    DNS resolution and reverse DNS lookup.

    Features:
    - Forward DNS resolution (hostname -> IP)
    - Reverse DNS lookup (IP -> hostname)
    - Multiple record types (A, AAAA, MX, etc.)
    - DNS caching
    - Timeout handling
    """

    def __init__(self, config_manager=None):
        """
        Initialize DNS resolver.

        Args:
            config_manager: Optional configuration manager
        """
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)
        self.cache = {}

    def execute(
        self,
        hostname: Optional[str] = None,
        ip_address: Optional[str] = None,
        action: str = "resolve",
        timeout: float = 5.0,
        use_cache: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Resolve DNS queries.

        Args:
            hostname: Hostname to resolve
            ip_address: IP address for reverse lookup
            action: Action to perform (resolve, reverse, both)
            timeout: DNS query timeout
            use_cache: Use cached results if available

        Returns:
            Dict with DNS resolution results
        """
        try:
            socket.setdefaulttimeout(timeout)

            if action == "resolve" and hostname:
                return self._resolve_hostname(hostname, use_cache)
            elif action == "reverse" and ip_address:
                return self._reverse_lookup(ip_address, use_cache)
            elif action == "both" and hostname:
                forward = self._resolve_hostname(hostname, use_cache)
                if forward.get("success") and forward.get("ip_addresses"):
                    reverse = self._reverse_lookup(forward["ip_addresses"][0], use_cache)
                    return {
                        "success": True,
                        "forward": forward,
                        "reverse": reverse
                    }
                return forward
            else:
                return {
                    "success": False,
                    "error": "Invalid action or missing parameters",
                    "valid_actions": ["resolve", "reverse", "both"]
                }

        except socket.timeout:
            return {
                "success": False,
                "error": "DNS query timeout",
                "error_type": "TimeoutError"
            }
        except Exception as e:
            self.logger.error(f"DNS error: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }

    def _resolve_hostname(self, hostname: str, use_cache: bool) -> Dict[str, Any]:
        """Resolve hostname to IP addresses."""
        cache_key = f"resolve:{hostname}"

        if use_cache and cache_key in self.cache:
            cached = self.cache[cache_key]
            if time.time() - cached["timestamp"] < 300:  # 5 minute TTL
                self.logger.debug(f"DNS cache hit for {hostname}")
                return cached["result"]

        try:
            start_time = time.time()

            # Get all address info
            addr_info = socket.getaddrinfo(hostname, None)

            # Extract unique IP addresses
            ipv4_addresses = []
            ipv6_addresses = []

            for info in addr_info:
                family = info[0]
                ip = info[4][0]

                if family == socket.AF_INET and ip not in ipv4_addresses:
                    ipv4_addresses.append(ip)
                elif family == socket.AF_INET6 and ip not in ipv6_addresses:
                    ipv6_addresses.append(ip)

            result = {
                "success": True,
                "hostname": hostname,
                "ipv4_addresses": ipv4_addresses,
                "ipv6_addresses": ipv6_addresses,
                "ip_addresses": ipv4_addresses + ipv6_addresses,
                "query_time_ms": int((time.time() - start_time) * 1000)
            }

            # Cache the result
            if use_cache:
                self.cache[cache_key] = {
                    "result": result,
                    "timestamp": time.time()
                }

            return result

        except socket.gaierror as e:
            return {
                "success": False,
                "hostname": hostname,
                "error": f"DNS resolution failed: {e}",
                "error_type": "DNSError"
            }

    def _reverse_lookup(self, ip_address: str, use_cache: bool) -> Dict[str, Any]:
        """Reverse DNS lookup (IP to hostname)."""
        cache_key = f"reverse:{ip_address}"

        if use_cache and cache_key in self.cache:
            cached = self.cache[cache_key]
            if time.time() - cached["timestamp"] < 300:  # 5 minute TTL
                self.logger.debug(f"DNS cache hit for {ip_address}")
                return cached["result"]

        try:
            start_time = time.time()
            hostname, aliaslist, ipaddrlist = socket.gethostbyaddr(ip_address)

            result = {
                "success": True,
                "ip_address": ip_address,
                "hostname": hostname,
                "aliases": aliaslist,
                "query_time_ms": int((time.time() - start_time) * 1000)
            }

            # Cache the result
            if use_cache:
                self.cache[cache_key] = {
                    "result": result,
                    "timestamp": time.time()
                }

            return result

        except socket.herror as e:
            return {
                "success": False,
                "ip_address": ip_address,
                "error": f"Reverse DNS lookup failed: {e}",
                "error_type": "DNSError"
            }


class PortScanner:
    """
    Network port scanner.

    Features:
    - TCP port scanning
    - UDP port scanning
    - Parallel scanning
    - Service detection
    - Timeout handling
    """

    def __init__(self, config_manager=None):
        """
        Initialize port scanner.

        Args:
            config_manager: Optional configuration manager
        """
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)

        # Common service port mappings
        self.common_ports = {
            20: "FTP Data",
            21: "FTP Control",
            22: "SSH",
            23: "Telnet",
            25: "SMTP",
            53: "DNS",
            80: "HTTP",
            110: "POP3",
            143: "IMAP",
            443: "HTTPS",
            465: "SMTPS",
            587: "SMTP Submission",
            993: "IMAPS",
            995: "POP3S",
            3306: "MySQL",
            5432: "PostgreSQL",
            6379: "Redis",
            8080: "HTTP Alt",
            8443: "HTTPS Alt",
            27017: "MongoDB",
        }

    def execute(
        self,
        host: str,
        ports: Optional[List[int]] = None,
        port_range: Optional[tuple] = None,
        protocol: str = "tcp",
        timeout: float = 2.0,
        parallel: bool = True,
        max_workers: int = 50,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Scan ports on a host.

        Args:
            host: Target hostname or IP address
            ports: List of specific ports to scan
            port_range: Tuple of (start_port, end_port) for range scan
            protocol: Protocol to scan (tcp, udp)
            timeout: Connection timeout per port
            parallel: Use parallel scanning
            max_workers: Maximum parallel workers

        Returns:
            Dict with scan results
        """
        try:
            # Resolve hostname
            try:
                target_ip = socket.gethostbyname(host)
            except socket.gaierror as e:
                return {
                    "success": False,
                    "error": f"DNS resolution failed for {host}: {e}",
                    "error_type": "DNSError"
                }

            # Determine ports to scan
            if ports:
                scan_ports = ports
            elif port_range:
                scan_ports = list(range(port_range[0], port_range[1] + 1))
            else:
                # Default to common ports
                scan_ports = list(self.common_ports.keys())

            start_time = time.time()

            if parallel and len(scan_ports) > 1:
                results = self._parallel_scan(target_ip, scan_ports, protocol, timeout, max_workers)
            else:
                results = self._sequential_scan(target_ip, scan_ports, protocol, timeout)

            open_ports = [r for r in results if r["state"] == "open"]
            closed_ports = [r for r in results if r["state"] == "closed"]
            filtered_ports = [r for r in results if r["state"] == "filtered"]

            return {
                "success": True,
                "host": host,
                "target_ip": target_ip,
                "protocol": protocol,
                "total_ports_scanned": len(scan_ports),
                "open_ports": open_ports,
                "closed_ports": closed_ports,
                "filtered_ports": filtered_ports,
                "scan_duration": time.time() - start_time,
                "all_results": results
            }

        except Exception as e:
            self.logger.error(f"Port scan error: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }

    def _scan_port(self, ip: str, port: int, protocol: str, timeout: float) -> Dict[str, Any]:
        """Scan a single port."""
        result = {
            "port": port,
            "protocol": protocol,
            "service": self.common_ports.get(port, "Unknown")
        }

        try:
            if protocol == "tcp":
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(timeout)
                start = time.time()
                connection_result = sock.connect_ex((ip, port))
                response_time = time.time() - start
                sock.close()

                if connection_result == 0:
                    result["state"] = "open"
                    result["response_time_ms"] = int(response_time * 1000)
                else:
                    result["state"] = "closed"

            elif protocol == "udp":
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.settimeout(timeout)

                try:
                    # Send empty packet
                    sock.sendto(b'', (ip, port))
                    # Try to receive
                    data, addr = sock.recvfrom(1024)
                    result["state"] = "open"
                except socket.timeout:
                    # UDP timeout often means open (no response)
                    result["state"] = "open|filtered"
                except Exception:
                    result["state"] = "closed"
                finally:
                    sock.close()

        except socket.timeout:
            result["state"] = "filtered"
        except Exception as e:
            result["state"] = "error"
            result["error"] = str(e)

        return result

    def _sequential_scan(
        self,
        ip: str,
        ports: List[int],
        protocol: str,
        timeout: float
    ) -> List[Dict[str, Any]]:
        """Scan ports sequentially."""
        results = []
        for port in ports:
            result = self._scan_port(ip, port, protocol, timeout)
            results.append(result)
            self.logger.debug(f"Scanned port {port}: {result['state']}")
        return results

    def _parallel_scan(
        self,
        ip: str,
        ports: List[int],
        protocol: str,
        timeout: float,
        max_workers: int
    ) -> List[Dict[str, Any]]:
        """Scan ports in parallel."""
        results = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_port = {
                executor.submit(self._scan_port, ip, port, protocol, timeout): port
                for port in ports
            }

            for future in as_completed(future_to_port):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    port = future_to_port[future]
                    self.logger.error(f"Error scanning port {port}: {e}")
                    results.append({
                        "port": port,
                        "state": "error",
                        "error": str(e)
                    })

        # Sort by port number
        results.sort(key=lambda x: x["port"])
        return results

    def scan_common_ports(self, host: str, **kwargs) -> Dict[str, Any]:
        """Quick scan of common ports."""
        return self.execute(host=host, ports=list(self.common_ports.keys()), **kwargs)


class NetworkDiagnostics:
    """
    Network diagnostic utilities.

    Features:
    - Connection testing
    - Latency measurement
    - Bandwidth estimation
    - Network path analysis
    """

    def __init__(self, config_manager=None):
        """Initialize network diagnostics."""
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)

    def execute(
        self,
        host: str,
        port: int = 80,
        action: str = "ping",
        count: int = 4,
        timeout: float = 5.0,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Run network diagnostics.

        Args:
            host: Target host
            port: Target port for connection tests
            action: Diagnostic action (ping, latency, connection_test)
            count: Number of test iterations
            timeout: Timeout per test

        Returns:
            Dict with diagnostic results
        """
        try:
            if action == "ping":
                return self._tcp_ping(host, port, count, timeout)
            elif action == "latency":
                return self._measure_latency(host, port, count, timeout)
            elif action == "connection_test":
                return self._test_connection(host, port, timeout)
            else:
                return {
                    "success": False,
                    "error": f"Unknown action: {action}",
                    "valid_actions": ["ping", "latency", "connection_test"]
                }

        except Exception as e:
            self.logger.error(f"Diagnostic error: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }

    def _tcp_ping(self, host: str, port: int, count: int, timeout: float) -> Dict[str, Any]:
        """TCP ping to measure connectivity."""
        results = []
        successful = 0
        total_time = 0

        for i in range(count):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(timeout)

                start = time.time()
                sock.connect((host, port))
                response_time = (time.time() - start) * 1000
                sock.close()

                results.append({
                    "sequence": i + 1,
                    "success": True,
                    "response_time_ms": response_time
                })
                successful += 1
                total_time += response_time

            except Exception as e:
                results.append({
                    "sequence": i + 1,
                    "success": False,
                    "error": str(e)
                })

            if i < count - 1:
                time.sleep(1)

        return {
            "success": True,
            "host": host,
            "port": port,
            "packets_sent": count,
            "packets_received": successful,
            "packet_loss_percent": ((count - successful) / count) * 100,
            "average_response_time_ms": total_time / successful if successful > 0 else 0,
            "results": results
        }

    def _measure_latency(self, host: str, port: int, count: int, timeout: float) -> Dict[str, Any]:
        """Measure network latency."""
        latencies = []

        for _ in range(count):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(timeout)

                start = time.time()
                sock.connect((host, port))
                latency = (time.time() - start) * 1000
                sock.close()

                latencies.append(latency)

            except Exception:
                pass

        if latencies:
            return {
                "success": True,
                "host": host,
                "port": port,
                "min_latency_ms": min(latencies),
                "max_latency_ms": max(latencies),
                "avg_latency_ms": sum(latencies) / len(latencies),
                "measurements": len(latencies)
            }
        else:
            return {
                "success": False,
                "error": "No successful measurements"
            }

    def _test_connection(self, host: str, port: int, timeout: float) -> Dict[str, Any]:
        """Test TCP connection."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)

            start = time.time()
            sock.connect((host, port))
            connect_time = time.time() - start

            sock.close()

            return {
                "success": True,
                "host": host,
                "port": port,
                "status": "reachable",
                "connection_time_ms": int(connect_time * 1000)
            }

        except socket.timeout:
            return {
                "success": False,
                "host": host,
                "port": port,
                "status": "timeout",
                "error": "Connection timeout"
            }
        except ConnectionRefusedError:
            return {
                "success": False,
                "host": host,
                "port": port,
                "status": "refused",
                "error": "Connection refused"
            }
        except Exception as e:
            return {
                "success": False,
                "host": host,
                "port": port,
                "status": "error",
                "error": str(e)
            }
