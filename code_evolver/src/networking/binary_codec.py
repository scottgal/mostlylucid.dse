"""
Binary Codec Tools

Provides encoding and decoding of binary data in various formats:
- Python struct (C-style binary data)
- MessagePack
- Protocol Buffers (optional)
- JSON
- Custom binary formats
- String serialization (UTF-8, ASCII, Base64, Hex)
"""

import json
import struct
import base64
import binascii
import logging
from typing import Dict, Any, Optional, List, Union
from io import BytesIO

logger = logging.getLogger(__name__)


class BinaryEncoder:
    """
    Encode Python data structures to binary formats.

    Supports multiple binary serialization formats:
    - struct: Python struct module for C-style data
    - msgpack: MessagePack efficient binary format
    - protobuf: Protocol Buffers (if available)
    - json: JSON encoded to bytes
    - custom: User-defined binary schema
    """

    def __init__(self, config_manager=None):
        """
        Initialize binary encoder.

        Args:
            config_manager: Optional configuration manager
        """
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)

        # Try to import optional dependencies
        try:
            import msgpack
            self.msgpack = msgpack
            self.has_msgpack = True
        except ImportError:
            self.has_msgpack = False
            self.logger.warning("msgpack not available. Install with: pip install msgpack")

        try:
            from google.protobuf import message
            self.has_protobuf = True
        except ImportError:
            self.has_protobuf = False
            self.logger.warning("protobuf not available. Install with: pip install protobuf")

    def execute(
        self,
        data: Any,
        format: str = "msgpack",
        pattern: Optional[str] = None,
        fields: Optional[List[str]] = None,
        schema: Optional[Dict[str, Any]] = None,
        endian: str = "!",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Encode data to binary format.

        Args:
            data: Data to encode (dict, list, or primitive types)
            format: Encoding format (struct, msgpack, protobuf, json, custom)
            pattern: Struct format pattern (e.g., "!IHH" for struct format)
            fields: Field names for struct format (must match pattern)
            schema: Custom schema definition for custom format
            endian: Byte order for struct (! = network/big-endian, < = little, > = big, = = native)

        Returns:
            Dict with success status and encoded binary data
        """
        try:
            if format == "struct":
                return self._encode_struct(data, pattern, fields, endian)
            elif format == "msgpack":
                return self._encode_msgpack(data)
            elif format == "protobuf":
                return self._encode_protobuf(data, schema)
            elif format == "json":
                return self._encode_json(data)
            elif format == "custom":
                return self._encode_custom(data, schema)
            else:
                return {
                    "success": False,
                    "error": f"Unsupported format: {format}",
                    "supported_formats": ["struct", "msgpack", "protobuf", "json", "custom"]
                }

        except Exception as e:
            self.logger.error(f"Encoding error: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }

    def _encode_struct(
        self,
        data: Union[Dict, List, tuple],
        pattern: str,
        fields: Optional[List[str]],
        endian: str
    ) -> Dict[str, Any]:
        """Encode data using Python struct module."""
        if not pattern:
            return {"success": False, "error": "Pattern required for struct format"}

        try:
            # Convert dict to tuple if fields are provided
            if isinstance(data, dict) and fields:
                values = tuple(data.get(f) for f in fields)
            elif isinstance(data, (list, tuple)):
                values = tuple(data)
            else:
                return {"success": False, "error": "Data must be dict (with fields) or list/tuple"}

            # Pack the data
            full_pattern = endian + pattern.lstrip("!<>=@")
            binary_data = struct.pack(full_pattern, *values)

            return {
                "success": True,
                "binary_data": binary_data,
                "hex": binascii.hexlify(binary_data).decode('ascii'),
                "base64": base64.b64encode(binary_data).decode('ascii'),
                "size": len(binary_data),
                "format": "struct",
                "pattern": full_pattern
            }

        except struct.error as e:
            return {"success": False, "error": f"Struct packing error: {e}"}

    def _encode_msgpack(self, data: Any) -> Dict[str, Any]:
        """Encode data using MessagePack."""
        if not self.has_msgpack:
            return {
                "success": False,
                "error": "msgpack not installed",
                "install_command": "pip install msgpack"
            }

        try:
            binary_data = self.msgpack.packb(data, use_bin_type=True)
            return {
                "success": True,
                "binary_data": binary_data,
                "hex": binascii.hexlify(binary_data).decode('ascii'),
                "base64": base64.b64encode(binary_data).decode('ascii'),
                "size": len(binary_data),
                "format": "msgpack"
            }
        except Exception as e:
            return {"success": False, "error": f"MessagePack encoding error: {e}"}

    def _encode_protobuf(self, data: Any, schema: Optional[Dict]) -> Dict[str, Any]:
        """Encode data using Protocol Buffers."""
        if not self.has_protobuf:
            return {
                "success": False,
                "error": "protobuf not installed",
                "install_command": "pip install protobuf"
            }

        return {
            "success": False,
            "error": "Protobuf encoding requires schema definition",
            "note": "Implement protobuf schema loading for your use case"
        }

    def _encode_json(self, data: Any) -> Dict[str, Any]:
        """Encode data as JSON bytes."""
        try:
            json_str = json.dumps(data)
            binary_data = json_str.encode('utf-8')
            return {
                "success": True,
                "binary_data": binary_data,
                "hex": binascii.hexlify(binary_data).decode('ascii'),
                "base64": base64.b64encode(binary_data).decode('ascii'),
                "size": len(binary_data),
                "format": "json"
            }
        except Exception as e:
            return {"success": False, "error": f"JSON encoding error: {e}"}

    def _encode_custom(self, data: Dict, schema: Dict) -> Dict[str, Any]:
        """Encode data using custom binary schema."""
        if not schema:
            return {"success": False, "error": "Schema required for custom format"}

        try:
            buffer = BytesIO()

            for field_name, field_spec in schema.items():
                value = data.get(field_name)
                field_type = field_spec.get("type")
                endian = field_spec.get("endian", "big")

                if field_type == "uint8":
                    buffer.write(struct.pack("B", value))
                elif field_type == "uint16":
                    fmt = ">H" if endian == "big" else "<H"
                    buffer.write(struct.pack(fmt, value))
                elif field_type == "uint32":
                    fmt = ">I" if endian == "big" else "<I"
                    buffer.write(struct.pack(fmt, value))
                elif field_type == "uint64":
                    fmt = ">Q" if endian == "big" else "<Q"
                    buffer.write(struct.pack(fmt, value))
                elif field_type == "int8":
                    buffer.write(struct.pack("b", value))
                elif field_type == "int16":
                    fmt = ">h" if endian == "big" else "<h"
                    buffer.write(struct.pack(fmt, value))
                elif field_type == "int32":
                    fmt = ">i" if endian == "big" else "<i"
                    buffer.write(struct.pack(fmt, value))
                elif field_type == "int64":
                    fmt = ">q" if endian == "big" else "<q"
                    buffer.write(struct.pack(fmt, value))
                elif field_type == "float":
                    fmt = ">f" if endian == "big" else "<f"
                    buffer.write(struct.pack(fmt, value))
                elif field_type == "double":
                    fmt = ">d" if endian == "big" else "<d"
                    buffer.write(struct.pack(fmt, value))
                elif field_type == "bytes":
                    if isinstance(value, str):
                        value = value.encode('utf-8')
                    length_field = field_spec.get("length_field")
                    if length_field:
                        # Length is already encoded in another field
                        buffer.write(value)
                    else:
                        # Fixed length or write all
                        max_len = field_spec.get("length", len(value))
                        buffer.write(value[:max_len])
                elif field_type == "string":
                    encoding = field_spec.get("encoding", "utf-8")
                    str_bytes = value.encode(encoding)
                    length_field = field_spec.get("length_field")
                    if length_field:
                        buffer.write(str_bytes)
                    else:
                        max_len = field_spec.get("length", len(str_bytes))
                        buffer.write(str_bytes[:max_len])

            binary_data = buffer.getvalue()
            return {
                "success": True,
                "binary_data": binary_data,
                "hex": binascii.hexlify(binary_data).decode('ascii'),
                "base64": base64.b64encode(binary_data).decode('ascii'),
                "size": len(binary_data),
                "format": "custom"
            }

        except Exception as e:
            return {"success": False, "error": f"Custom encoding error: {e}"}


class BinaryDecoder:
    """
    Decode binary data to Python data structures.

    Supports the same formats as BinaryEncoder.
    """

    def __init__(self, config_manager=None):
        """
        Initialize binary decoder.

        Args:
            config_manager: Optional configuration manager
        """
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)

        # Try to import optional dependencies
        try:
            import msgpack
            self.msgpack = msgpack
            self.has_msgpack = True
        except ImportError:
            self.has_msgpack = False
            self.logger.warning("msgpack not available")

        try:
            from google.protobuf import message
            self.has_protobuf = True
        except ImportError:
            self.has_protobuf = False
            self.logger.warning("protobuf not available")

    def execute(
        self,
        binary_data: Union[bytes, str],
        format: str = "msgpack",
        pattern: Optional[str] = None,
        fields: Optional[List[str]] = None,
        schema: Optional[Dict[str, Any]] = None,
        endian: str = "!",
        input_encoding: str = "raw",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Decode binary data to Python objects.

        Args:
            binary_data: Binary data to decode (bytes, hex string, or base64 string)
            format: Decoding format (struct, msgpack, protobuf, json, custom)
            pattern: Struct format pattern
            fields: Field names for struct format
            schema: Custom schema definition
            endian: Byte order for struct
            input_encoding: How binary_data is encoded (raw, hex, base64)

        Returns:
            Dict with success status and decoded data
        """
        try:
            # Convert input to bytes if needed
            if input_encoding == "hex":
                binary_data = binascii.unhexlify(binary_data)
            elif input_encoding == "base64":
                binary_data = base64.b64decode(binary_data)
            elif input_encoding == "raw" and isinstance(binary_data, str):
                binary_data = binary_data.encode('latin1')

            if format == "struct":
                return self._decode_struct(binary_data, pattern, fields, endian)
            elif format == "msgpack":
                return self._decode_msgpack(binary_data)
            elif format == "protobuf":
                return self._decode_protobuf(binary_data, schema)
            elif format == "json":
                return self._decode_json(binary_data)
            elif format == "custom":
                return self._decode_custom(binary_data, schema)
            else:
                return {
                    "success": False,
                    "error": f"Unsupported format: {format}",
                    "supported_formats": ["struct", "msgpack", "protobuf", "json", "custom"]
                }

        except Exception as e:
            self.logger.error(f"Decoding error: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }

    def _decode_struct(
        self,
        binary_data: bytes,
        pattern: str,
        fields: Optional[List[str]],
        endian: str
    ) -> Dict[str, Any]:
        """Decode binary data using Python struct module."""
        if not pattern:
            return {"success": False, "error": "Pattern required for struct format"}

        try:
            full_pattern = endian + pattern.lstrip("!<>=@")
            values = struct.unpack(full_pattern, binary_data)

            # Convert to dict if fields provided
            if fields:
                data = dict(zip(fields, values))
            else:
                data = list(values)

            return {
                "success": True,
                "data": data,
                "format": "struct",
                "pattern": full_pattern,
                "size": len(binary_data)
            }

        except struct.error as e:
            return {"success": False, "error": f"Struct unpacking error: {e}"}

    def _decode_msgpack(self, binary_data: bytes) -> Dict[str, Any]:
        """Decode MessagePack binary data."""
        if not self.has_msgpack:
            return {
                "success": False,
                "error": "msgpack not installed",
                "install_command": "pip install msgpack"
            }

        try:
            data = self.msgpack.unpackb(binary_data, raw=False)
            return {
                "success": True,
                "data": data,
                "format": "msgpack",
                "size": len(binary_data)
            }
        except Exception as e:
            return {"success": False, "error": f"MessagePack decoding error: {e}"}

    def _decode_protobuf(self, binary_data: bytes, schema: Optional[Dict]) -> Dict[str, Any]:
        """Decode Protocol Buffers data."""
        if not self.has_protobuf:
            return {
                "success": False,
                "error": "protobuf not installed",
                "install_command": "pip install protobuf"
            }

        return {
            "success": False,
            "error": "Protobuf decoding requires schema definition",
            "note": "Implement protobuf schema loading for your use case"
        }

    def _decode_json(self, binary_data: bytes) -> Dict[str, Any]:
        """Decode JSON from bytes."""
        try:
            json_str = binary_data.decode('utf-8')
            data = json.loads(json_str)
            return {
                "success": True,
                "data": data,
                "format": "json",
                "size": len(binary_data)
            }
        except Exception as e:
            return {"success": False, "error": f"JSON decoding error: {e}"}

    def _decode_custom(self, binary_data: bytes, schema: Dict) -> Dict[str, Any]:
        """Decode data using custom binary schema."""
        if not schema:
            return {"success": False, "error": "Schema required for custom format"}

        try:
            buffer = BytesIO(binary_data)
            data = {}

            for field_name, field_spec in schema.items():
                field_type = field_spec.get("type")
                endian = field_spec.get("endian", "big")

                if field_type == "uint8":
                    data[field_name] = struct.unpack("B", buffer.read(1))[0]
                elif field_type == "uint16":
                    fmt = ">H" if endian == "big" else "<H"
                    data[field_name] = struct.unpack(fmt, buffer.read(2))[0]
                elif field_type == "uint32":
                    fmt = ">I" if endian == "big" else "<I"
                    data[field_name] = struct.unpack(fmt, buffer.read(4))[0]
                elif field_type == "uint64":
                    fmt = ">Q" if endian == "big" else "<Q"
                    data[field_name] = struct.unpack(fmt, buffer.read(8))[0]
                elif field_type == "int8":
                    data[field_name] = struct.unpack("b", buffer.read(1))[0]
                elif field_type == "int16":
                    fmt = ">h" if endian == "big" else "<h"
                    data[field_name] = struct.unpack(fmt, buffer.read(2))[0]
                elif field_type == "int32":
                    fmt = ">i" if endian == "big" else "<i"
                    data[field_name] = struct.unpack(fmt, buffer.read(4))[0]
                elif field_type == "int64":
                    fmt = ">q" if endian == "big" else "<q"
                    data[field_name] = struct.unpack(fmt, buffer.read(8))[0]
                elif field_type == "float":
                    fmt = ">f" if endian == "big" else "<f"
                    data[field_name] = struct.unpack(fmt, buffer.read(4))[0]
                elif field_type == "double":
                    fmt = ">d" if endian == "big" else "<d"
                    data[field_name] = struct.unpack(fmt, buffer.read(8))[0]
                elif field_type == "bytes":
                    length_field = field_spec.get("length_field")
                    if length_field:
                        length = data[length_field]
                    else:
                        length = field_spec.get("length", buffer.getbuffer().nbytes - buffer.tell())
                    data[field_name] = buffer.read(length)
                elif field_type == "string":
                    encoding = field_spec.get("encoding", "utf-8")
                    length_field = field_spec.get("length_field")
                    if length_field:
                        length = data[length_field]
                    else:
                        length = field_spec.get("length", buffer.getbuffer().nbytes - buffer.tell())
                    data[field_name] = buffer.read(length).decode(encoding)

            return {
                "success": True,
                "data": data,
                "format": "custom",
                "size": len(binary_data)
            }

        except Exception as e:
            return {"success": False, "error": f"Custom decoding error: {e}"}


class StringSerializer:
    """
    String encoding and decoding utilities.

    Supports various string encodings and representations:
    - UTF-8, ASCII, Latin-1, etc.
    - Base64 encoding/decoding
    - Hex encoding/decoding
    - URL encoding/decoding
    """

    def __init__(self, config_manager=None):
        """Initialize string serializer."""
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)

    def execute(
        self,
        data: Union[str, bytes],
        action: str = "encode",
        encoding: str = "utf-8",
        representation: str = "raw",
        errors: str = "strict",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Encode or decode strings.

        Args:
            data: String or bytes to process
            action: "encode" or "decode"
            encoding: Character encoding (utf-8, ascii, latin-1, etc.)
            representation: Output format (raw, base64, hex, url)
            errors: Error handling (strict, ignore, replace)

        Returns:
            Dict with success status and processed data
        """
        try:
            if action == "encode":
                return self._encode_string(data, encoding, representation, errors)
            elif action == "decode":
                return self._decode_string(data, encoding, representation, errors)
            else:
                return {
                    "success": False,
                    "error": f"Invalid action: {action}",
                    "valid_actions": ["encode", "decode"]
                }
        except Exception as e:
            self.logger.error(f"String serialization error: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }

    def _encode_string(
        self,
        data: str,
        encoding: str,
        representation: str,
        errors: str
    ) -> Dict[str, Any]:
        """Encode string to bytes."""
        try:
            # First encode to bytes
            if isinstance(data, bytes):
                byte_data = data
            else:
                byte_data = data.encode(encoding, errors=errors)

            # Then apply representation
            if representation == "raw":
                result = byte_data
            elif representation == "base64":
                result = base64.b64encode(byte_data).decode('ascii')
            elif representation == "hex":
                result = binascii.hexlify(byte_data).decode('ascii')
            elif representation == "url":
                from urllib.parse import quote
                result = quote(byte_data.decode(encoding))
            else:
                return {
                    "success": False,
                    "error": f"Invalid representation: {representation}",
                    "valid_representations": ["raw", "base64", "hex", "url"]
                }

            return {
                "success": True,
                "data": result,
                "encoding": encoding,
                "representation": representation,
                "size": len(byte_data)
            }

        except Exception as e:
            return {"success": False, "error": f"Encoding error: {e}"}

    def _decode_string(
        self,
        data: Union[str, bytes],
        encoding: str,
        representation: str,
        errors: str
    ) -> Dict[str, Any]:
        """Decode bytes to string."""
        try:
            # First convert from representation to bytes
            if representation == "raw":
                if isinstance(data, str):
                    byte_data = data.encode('latin1')
                else:
                    byte_data = data
            elif representation == "base64":
                if isinstance(data, bytes):
                    data = data.decode('ascii')
                byte_data = base64.b64decode(data)
            elif representation == "hex":
                if isinstance(data, bytes):
                    data = data.decode('ascii')
                byte_data = binascii.unhexlify(data)
            elif representation == "url":
                from urllib.parse import unquote
                if isinstance(data, bytes):
                    data = data.decode('ascii')
                result = unquote(data)
                return {
                    "success": True,
                    "data": result,
                    "encoding": encoding,
                    "representation": representation,
                    "size": len(result.encode(encoding))
                }
            else:
                return {
                    "success": False,
                    "error": f"Invalid representation: {representation}",
                    "valid_representations": ["raw", "base64", "hex", "url"]
                }

            # Then decode bytes to string
            result = byte_data.decode(encoding, errors=errors)

            return {
                "success": True,
                "data": result,
                "encoding": encoding,
                "representation": representation,
                "size": len(byte_data)
            }

        except Exception as e:
            return {"success": False, "error": f"Decoding error: {e}"}
