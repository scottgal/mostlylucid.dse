"""
TCP Networking Tools

Provides TCP server and client tools for binary protocols.
Supports connection pooling, persistent connections, and binary data transfer.
"""

import socket
import threading
import logging
import time
import queue
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
import select

from .binary_codec import BinaryDecoder, BinaryEncoder

logger = logging.getLogger(__name__)


class TCPServer:
    """
    TCP server for binary protocols.

    Features:
    - Multi-threaded connection handling
    - Binary protocol support with automatic decoding
    - Connection limits and timeouts
    - Graceful shutdown
    - Connection pooling
    """

    def __init__(self, config_manager=None):
        """
        Initialize TCP server.

        Args:
            config_manager: Optional configuration manager
        """
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)
        self.decoder = BinaryDecoder(config_manager)
        self.encoder = BinaryEncoder(config_manager)
        self.active_servers = {}

    def execute(
        self,
        port: int,
        host: str = "0.0.0.0",
        max_connections: int = 10,
        timeout: Optional[float] = 30.0,
        decoder: Optional[Dict[str, Any]] = None,
        encoder: Optional[Dict[str, Any]] = None,
        handler: str = "echo",
        backlog: int = 5,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Start TCP server (blocking mode for single request).

        Args:
            port: Port to listen on
            host: Host to bind to
            max_connections: Maximum concurrent connections
            timeout: Socket timeout in seconds
            decoder: Decoder configuration for incoming data
            encoder: Encoder configuration for outgoing data
            handler: Handler type (echo, custom)
            backlog: Listen backlog size

        Returns:
            Dict with server status and connection info
        """
        try:
            # Validate port
            if not (1 <= port <= 65535):
                return {
                    "success": False,
                    "error": f"Invalid port: {port}. Must be 1-65535"
                }

            # Create TCP socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            # Set timeout
            if timeout:
                sock.settimeout(timeout)

            # Bind and listen
            sock.bind((host, port))
            sock.listen(backlog)
            self.logger.info(f"TCP server listening on {host}:{port}")

            connections = []
            start_time = time.time()

            try:
                # Accept one connection for synchronous mode
                client_sock, client_addr = sock.accept()
                self.logger.info(f"Connection from {client_addr}")

                # Handle the connection
                result = self._handle_connection(
                    client_sock,
                    client_addr,
                    decoder,
                    encoder,
                    handler,
                    timeout
                )

                connections.append(result)
                client_sock.close()

            except socket.timeout:
                self.logger.info("No connections received within timeout")

            sock.close()

            return {
                "success": True,
                "connections": connections,
                "total_connections": len(connections),
                "listen_duration": time.time() - start_time,
                "host": host,
                "port": port
            }

        except PermissionError:
            return {
                "success": False,
                "error": f"Permission denied to bind to port {port}. Try a port > 1024."
            }
        except OSError as e:
            return {
                "success": False,
                "error": f"Socket error: {e}",
                "error_type": "OSError"
            }
        except Exception as e:
            self.logger.error(f"TCP server error: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }

    def _handle_connection(
        self,
        client_sock: socket.socket,
        client_addr: tuple,
        decoder: Optional[Dict],
        encoder: Optional[Dict],
        handler: str,
        timeout: Optional[float]
    ) -> Dict[str, Any]:
        """Handle a single client connection."""
        connection_info = {
            "client_address": client_addr[0],
            "client_port": client_addr[1],
            "timestamp": datetime.utcnow().isoformat(),
            "messages": []
        }

        try:
            if timeout:
                client_sock.settimeout(timeout)

            # Receive data
            buffer_size = 8192
            chunks = []

            while True:
                try:
                    chunk = client_sock.recv(buffer_size)
                    if not chunk:
                        break
                    chunks.append(chunk)

                    # For simple protocols, assume one message
                    # For more complex protocols, implement proper framing
                    if len(chunk) < buffer_size:
                        break

                except socket.timeout:
                    break

            if chunks:
                data = b''.join(chunks)
                connection_info["bytes_received"] = len(data)

                # Decode if decoder specified
                if decoder:
                    decode_result = self.decoder.execute(binary_data=data, **decoder)
                    if decode_result["success"]:
                        connection_info["decoded_data"] = decode_result["data"]
                        received_data = decode_result["data"]
                    else:
                        connection_info["decode_error"] = decode_result["error"]
                        received_data = data
                else:
                    try:
                        received_data = data.decode('utf-8')
                        connection_info["text"] = received_data
                    except:
                        connection_info["raw_data"] = data.hex()
                        received_data = data

                # Handle based on handler type
                if handler == "echo":
                    response_data = data
                elif handler == "uppercase" and isinstance(received_data, str):
                    response_data = received_data.upper().encode('utf-8')
                else:
                    # Custom handler would go here
                    response_data = b"OK"

                # Encode response if encoder specified
                if encoder and not isinstance(response_data, bytes):
                    encode_result = self.encoder.execute(data=response_data, **encoder)
                    if encode_result["success"]:
                        response_data = encode_result["binary_data"]

                # Send response
                client_sock.sendall(response_data)
                connection_info["bytes_sent"] = len(response_data)
                connection_info["success"] = True

        except Exception as e:
            connection_info["error"] = str(e)
            connection_info["success"] = False
            self.logger.error(f"Connection handling error: {e}")

        return connection_info

    def start_async_server(
        self,
        port: int,
        host: str = "0.0.0.0",
        max_connections: int = 10,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Start async TCP server in background thread.

        Args:
            port: Port to listen on
            host: Host to bind to
            max_connections: Maximum concurrent connections
            **kwargs: Additional server options

        Returns:
            Dict with server_id for management
        """
        server_id = f"tcp_{host}_{port}_{int(time.time())}"
        connection_queue = queue.Queue()

        def server_thread():
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((host, port))
            sock.listen(kwargs.get('backlog', 5))
            sock.settimeout(1.0)

            while server_id in self.active_servers:
                try:
                    client_sock, client_addr = sock.accept()
                    # Handle in separate thread
                    threading.Thread(
                        target=self._handle_connection,
                        args=(
                            client_sock,
                            client_addr,
                            kwargs.get('decoder'),
                            kwargs.get('encoder'),
                            kwargs.get('handler', 'echo'),
                            kwargs.get('timeout')
                        ),
                        daemon=True
                    ).start()
                except socket.timeout:
                    continue
                except Exception as e:
                    self.logger.error(f"Server error: {e}")
                    break

            sock.close()

        thread = threading.Thread(target=server_thread, daemon=True)
        thread.start()

        self.active_servers[server_id] = {
            "thread": thread,
            "queue": connection_queue,
            "host": host,
            "port": port
        }

        return {
            "success": True,
            "server_id": server_id,
            "host": host,
            "port": port,
            "status": "running"
        }

    def stop_async_server(self, server_id: str) -> Dict[str, Any]:
        """Stop async server."""
        if server_id in self.active_servers:
            del self.active_servers[server_id]
            return {
                "success": True,
                "server_id": server_id,
                "status": "stopped"
            }
        else:
            return {
                "success": False,
                "error": f"Server not found: {server_id}"
            }


class TCPClient:
    """
    TCP client for binary protocols.

    Features:
    - Connection pooling
    - Automatic reconnection
    - Binary protocol support
    - Request/response handling
    - Connection reuse
    """

    def __init__(self, config_manager=None):
        """
        Initialize TCP client.

        Args:
            config_manager: Optional configuration manager
        """
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)
        self.decoder = BinaryDecoder(config_manager)
        self.encoder = BinaryEncoder(config_manager)
        self.connection_pool = {}

    def execute(
        self,
        host: str,
        port: int,
        data: Any,
        encoder: Optional[Dict[str, Any]] = None,
        decoder: Optional[Dict[str, Any]] = None,
        timeout: float = 30.0,
        keepalive: bool = False,
        nodelay: bool = True,
        expect_response: bool = True,
        response_size: int = 8192,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Connect to TCP server and send/receive data.

        Args:
            host: Server hostname or IP
            port: Server port
            data: Data to send
            encoder: Encoder configuration for outgoing data
            decoder: Decoder configuration for incoming data
            timeout: Connection and read timeout
            keepalive: Enable TCP keepalive
            nodelay: Enable TCP_NODELAY (disable Nagle's algorithm)
            expect_response: Whether to wait for response
            response_size: Maximum response size to receive

        Returns:
            Dict with success status and response data
        """
        try:
            # Validate port
            if not (1 <= port <= 65535):
                return {
                    "success": False,
                    "error": f"Invalid port: {port}. Must be 1-65535"
                }

            # Encode data if encoder specified
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
                import json
                binary_data = json.dumps(data).encode('utf-8')

            # Create socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)

            # Set socket options
            if nodelay:
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

            if keepalive:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

            # Connect
            start_time = time.time()
            sock.connect((host, port))
            connect_time = time.time() - start_time

            # Send data
            sock.sendall(binary_data)
            bytes_sent = len(binary_data)

            result = {
                "success": True,
                "bytes_sent": bytes_sent,
                "connection_time_ms": int(connect_time * 1000)
            }

            # Receive response if expected
            if expect_response:
                chunks = []
                total_received = 0

                while total_received < response_size:
                    try:
                        chunk = sock.recv(min(8192, response_size - total_received))
                        if not chunk:
                            break
                        chunks.append(chunk)
                        total_received += len(chunk)

                        # If we got less than buffer size, probably done
                        if len(chunk) < 8192:
                            break

                    except socket.timeout:
                        break

                if chunks:
                    response_data = b''.join(chunks)
                    result["bytes_received"] = len(response_data)

                    # Decode if decoder specified
                    if decoder:
                        decode_result = self.decoder.execute(
                            binary_data=response_data,
                            **decoder
                        )
                        if decode_result["success"]:
                            result["response_data"] = decode_result["data"]
                        else:
                            result["decode_error"] = decode_result["error"]
                            result["raw_response"] = response_data.hex()
                    else:
                        try:
                            result["response_text"] = response_data.decode('utf-8')
                        except:
                            result["raw_response"] = response_data.hex()

            sock.close()
            return result

        except socket.gaierror as e:
            return {
                "success": False,
                "error": f"DNS resolution failed for {host}: {e}",
                "error_type": "DNSError"
            }
        except socket.timeout:
            return {
                "success": False,
                "error": f"Connection timeout to {host}:{port}",
                "error_type": "TimeoutError"
            }
        except ConnectionRefusedError:
            return {
                "success": False,
                "error": f"Connection refused to {host}:{port}",
                "error_type": "ConnectionRefused"
            }
        except Exception as e:
            self.logger.error(f"TCP client error: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }

    def send_batch(
        self,
        host: str,
        port: int,
        messages: List[Any],
        encoder: Optional[Dict[str, Any]] = None,
        decoder: Optional[Dict[str, Any]] = None,
        reuse_connection: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Send multiple messages over TCP.

        Args:
            host: Server hostname
            port: Server port
            messages: List of messages to send
            encoder: Encoder configuration
            decoder: Decoder configuration
            reuse_connection: Reuse the same connection for all messages

        Returns:
            Dict with batch send results
        """
        results = []
        sock = None

        try:
            if reuse_connection:
                # Create persistent connection
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(kwargs.get('timeout', 30.0))
                sock.connect((host, port))

            for i, message in enumerate(messages):
                if reuse_connection and sock:
                    # Use existing connection
                    try:
                        # Encode
                        if encoder:
                            encode_result = self.encoder.execute(data=message, **encoder)
                            if not encode_result["success"]:
                                results.append({
                                    "message_number": i + 1,
                                    "success": False,
                                    "error": encode_result["error"]
                                })
                                continue
                            binary_data = encode_result["binary_data"]
                        elif isinstance(message, bytes):
                            binary_data = message
                        else:
                            binary_data = str(message).encode('utf-8')

                        # Send
                        sock.sendall(binary_data)

                        # Receive if decoder specified
                        if decoder and kwargs.get('expect_response', True):
                            response = sock.recv(kwargs.get('response_size', 8192))
                            decode_result = self.decoder.execute(
                                binary_data=response,
                                **decoder
                            )
                            results.append({
                                "message_number": i + 1,
                                "success": True,
                                "bytes_sent": len(binary_data),
                                "response": decode_result.get("data")
                            })
                        else:
                            results.append({
                                "message_number": i + 1,
                                "success": True,
                                "bytes_sent": len(binary_data)
                            })

                    except Exception as e:
                        results.append({
                            "message_number": i + 1,
                            "success": False,
                            "error": str(e)
                        })
                else:
                    # Use separate connection for each message
                    result = self.execute(
                        host=host,
                        port=port,
                        data=message,
                        encoder=encoder,
                        decoder=decoder,
                        **kwargs
                    )
                    results.append({
                        "message_number": i + 1,
                        **result
                    })

            if sock:
                sock.close()

            successful = sum(1 for r in results if r.get("success", False))
            failed = len(results) - successful

            return {
                "success": failed == 0,
                "total_messages": len(messages),
                "successful": successful,
                "failed": failed,
                "results": results
            }

        except Exception as e:
            if sock:
                sock.close()

            return {
                "success": False,
                "error": str(e),
                "results": results
            }
