"""
UDP Networking Tools

Provides UDP listener and sender tools for binary protocols.
Supports automatic packet decoding and encoding using the binary codec.
"""

import socket
import logging
import threading
import time
import queue
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime

from .binary_codec import BinaryDecoder, BinaryEncoder

logger = logging.getLogger(__name__)


class UDPListener:
    """
    Listen for UDP packets on a specified port.

    Features:
    - Binary packet reception
    - Automatic decoding using binary codec
    - Configurable timeout and packet limits
    - Non-blocking and blocking modes
    - Packet filtering and validation
    """

    def __init__(self, config_manager=None):
        """
        Initialize UDP listener.

        Args:
            config_manager: Optional configuration manager
        """
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)
        self.decoder = BinaryDecoder(config_manager)
        self.active_sockets = {}

    def execute(
        self,
        port: int,
        host: str = "0.0.0.0",
        max_packets: Optional[int] = None,
        timeout: Optional[float] = 30.0,
        buffer_size: int = 65536,
        decoder: Optional[Dict[str, Any]] = None,
        filter_func: Optional[str] = None,
        return_raw: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Listen for UDP packets.

        Args:
            port: Port number to listen on (1-65535)
            host: Host address to bind to (default: 0.0.0.0 for all interfaces)
            max_packets: Maximum number of packets to receive (None = unlimited)
            timeout: Timeout in seconds (None = no timeout)
            buffer_size: UDP receive buffer size (default: 65536)
            decoder: Decoder configuration dict (format, pattern, fields, etc.)
            filter_func: Optional filter function name to validate packets
            return_raw: Return raw bytes instead of decoding

        Returns:
            Dict with success status and received packets
        """
        try:
            # Validate port
            if not (1 <= port <= 65535):
                return {
                    "success": False,
                    "error": f"Invalid port: {port}. Must be 1-65535"
                }

            # Create UDP socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            # Set timeout if specified
            if timeout:
                sock.settimeout(timeout)

            # Bind to address
            sock.bind((host, port))
            self.logger.info(f"UDP listener bound to {host}:{port}")

            packets = []
            start_time = time.time()
            packet_count = 0

            while True:
                # Check if we've reached max packets
                if max_packets and packet_count >= max_packets:
                    break

                # Check if we've exceeded timeout
                if timeout and (time.time() - start_time) > timeout:
                    break

                try:
                    # Receive packet
                    data, addr = sock.recvfrom(buffer_size)
                    packet_count += 1

                    packet_info = {
                        "packet_number": packet_count,
                        "timestamp": datetime.utcnow().isoformat(),
                        "source_address": addr[0],
                        "source_port": addr[1],
                        "size": len(data)
                    }

                    # Decode or return raw
                    if return_raw:
                        packet_info["raw_data"] = data
                        packet_info["hex"] = data.hex()
                    elif decoder:
                        decode_result = self.decoder.execute(
                            binary_data=data,
                            **decoder
                        )
                        if decode_result["success"]:
                            packet_info["decoded_data"] = decode_result["data"]
                            packet_info["format"] = decode_result.get("format")
                        else:
                            packet_info["decode_error"] = decode_result["error"]
                            packet_info["raw_data"] = data
                    else:
                        # Try to decode as UTF-8 string
                        try:
                            packet_info["text"] = data.decode('utf-8')
                        except:
                            packet_info["raw_data"] = data
                            packet_info["hex"] = data.hex()

                    packets.append(packet_info)
                    self.logger.debug(f"Received packet {packet_count} from {addr}")

                except socket.timeout:
                    self.logger.info("Socket timeout reached")
                    break
                except Exception as e:
                    self.logger.error(f"Error receiving packet: {e}")
                    break

            sock.close()

            return {
                "success": True,
                "packets_received": packet_count,
                "packets": packets,
                "listen_duration": time.time() - start_time,
                "host": host,
                "port": port
            }

        except PermissionError:
            return {
                "success": False,
                "error": f"Permission denied to bind to port {port}. Try a port > 1024 or run with elevated privileges."
            }
        except OSError as e:
            return {
                "success": False,
                "error": f"Socket error: {e}",
                "error_type": "OSError"
            }
        except Exception as e:
            self.logger.error(f"UDP listener error: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }

    def start_async_listener(
        self,
        port: int,
        host: str = "0.0.0.0",
        callback: Optional[Callable] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Start an async UDP listener in a background thread.

        Args:
            port: Port to listen on
            host: Host to bind to
            callback: Callback function to handle packets
            **kwargs: Additional arguments for execute()

        Returns:
            Dict with listener_id for managing the listener
        """
        listener_id = f"udp_{host}_{port}_{int(time.time())}"
        packet_queue = queue.Queue()

        def listener_thread():
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((host, port))

            timeout = kwargs.get('timeout', 1.0)
            sock.settimeout(timeout)

            while listener_id in self.active_sockets:
                try:
                    data, addr = sock.recvfrom(kwargs.get('buffer_size', 65536))
                    packet_info = {
                        "data": data,
                        "address": addr,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    packet_queue.put(packet_info)

                    if callback:
                        callback(packet_info)

                except socket.timeout:
                    continue
                except Exception as e:
                    self.logger.error(f"Listener error: {e}")
                    break

            sock.close()

        thread = threading.Thread(target=listener_thread, daemon=True)
        thread.start()

        self.active_sockets[listener_id] = {
            "thread": thread,
            "queue": packet_queue,
            "host": host,
            "port": port
        }

        return {
            "success": True,
            "listener_id": listener_id,
            "host": host,
            "port": port,
            "status": "running"
        }

    def stop_async_listener(self, listener_id: str) -> Dict[str, Any]:
        """Stop an async listener."""
        if listener_id in self.active_sockets:
            del self.active_sockets[listener_id]
            return {
                "success": True,
                "listener_id": listener_id,
                "status": "stopped"
            }
        else:
            return {
                "success": False,
                "error": f"Listener not found: {listener_id}"
            }


class UDPSender:
    """
    Send UDP datagrams to a remote host.

    Features:
    - Binary packet transmission
    - Automatic encoding using binary codec
    - Broadcast support
    - Multicast support
    - Rate limiting
    """

    def __init__(self, config_manager=None):
        """
        Initialize UDP sender.

        Args:
            config_manager: Optional configuration manager
        """
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)
        self.encoder = BinaryEncoder(config_manager)

    def execute(
        self,
        host: str,
        port: int,
        data: Any,
        encoder: Optional[Dict[str, Any]] = None,
        source_port: Optional[int] = None,
        broadcast: bool = False,
        multicast: bool = False,
        ttl: int = 64,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Send UDP datagram.

        Args:
            host: Destination host (IP address or hostname)
            port: Destination port (1-65535)
            data: Data to send (will be encoded if encoder is specified)
            encoder: Encoder configuration dict (format, pattern, etc.)
            source_port: Source port to bind to (optional)
            broadcast: Enable broadcast mode
            multicast: Enable multicast mode
            ttl: Time-to-live for multicast packets

        Returns:
            Dict with success status and bytes sent
        """
        try:
            # Validate port
            if not (1 <= port <= 65535):
                return {
                    "success": False,
                    "error": f"Invalid port: {port}. Must be 1-65535"
                }

            # Encode data if encoder is specified
            if encoder:
                encode_result = self.encoder.execute(data=data, **encoder)
                if not encode_result["success"]:
                    return {
                        "success": False,
                        "error": f"Encoding failed: {encode_result['error']}"
                    }
                binary_data = encode_result["binary_data"]
            elif isinstance(data, bytes):
                binary_data = data
            elif isinstance(data, str):
                binary_data = data.encode('utf-8')
            else:
                # Try JSON encoding as fallback
                import json
                binary_data = json.dumps(data).encode('utf-8')

            # Create UDP socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

            # Set socket options
            if broadcast:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

            if multicast:
                sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)

            # Bind to source port if specified
            if source_port:
                sock.bind(('', source_port))

            # Send data
            bytes_sent = sock.sendto(binary_data, (host, port))
            sock.close()

            return {
                "success": True,
                "bytes_sent": bytes_sent,
                "destination": f"{host}:{port}",
                "data_size": len(binary_data),
                "broadcast": broadcast,
                "multicast": multicast
            }

        except socket.gaierror as e:
            return {
                "success": False,
                "error": f"DNS resolution failed for {host}: {e}",
                "error_type": "DNSError"
            }
        except OSError as e:
            return {
                "success": False,
                "error": f"Socket error: {e}",
                "error_type": "OSError"
            }
        except Exception as e:
            self.logger.error(f"UDP sender error: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }

    def send_batch(
        self,
        host: str,
        port: int,
        packets: List[Any],
        encoder: Optional[Dict[str, Any]] = None,
        delay: float = 0.0,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Send multiple UDP packets.

        Args:
            host: Destination host
            port: Destination port
            packets: List of data packets to send
            encoder: Encoder configuration
            delay: Delay between packets in seconds

        Returns:
            Dict with batch send results
        """
        results = []
        total_bytes = 0
        successful = 0
        failed = 0

        for i, packet_data in enumerate(packets):
            result = self.execute(
                host=host,
                port=port,
                data=packet_data,
                encoder=encoder,
                **kwargs
            )

            results.append({
                "packet_number": i + 1,
                "success": result["success"],
                "bytes_sent": result.get("bytes_sent", 0),
                "error": result.get("error")
            })

            if result["success"]:
                successful += 1
                total_bytes += result["bytes_sent"]
            else:
                failed += 1

            if delay > 0 and i < len(packets) - 1:
                time.sleep(delay)

        return {
            "success": failed == 0,
            "total_packets": len(packets),
            "successful": successful,
            "failed": failed,
            "total_bytes": total_bytes,
            "results": results
        }
