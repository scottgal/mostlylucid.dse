#!/usr/bin/env python3
"""
Image Converter - Comprehensive image format conversion tool.

Supports conversion between multiple image formats with options for quality,
resizing, and metadata extraction. Can load from paths, convert formats,
and save to disk for use in workflows.
"""
import json
import sys
import base64
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from io import BytesIO

try:
    from PIL import Image, ImageOps
except ImportError:
    print(json.dumps({
        'status': 'error',
        'message': 'Pillow library not installed. Run: pip install Pillow'
    }))
    sys.exit(1)


class ImageConverter:
    """
    Comprehensive image converter supporting multiple formats and operations.

    Supported formats: PNG, JPEG, JPG, GIF, BMP, TIFF, WEBP, ICO, PPM, and more.
    """

    # Supported image formats
    SUPPORTED_FORMATS = {
        'png', 'jpeg', 'jpg', 'gif', 'bmp', 'tiff', 'tif',
        'webp', 'ico', 'ppm', 'pgm', 'pbm', 'pnm', 'pcx'
    }

    # Format aliases
    FORMAT_ALIASES = {
        'jpg': 'jpeg',
        'tif': 'tiff'
    }

    def __init__(self):
        """Initialize Image Converter."""
        pass

    def normalize_format(self, fmt: str) -> str:
        """
        Normalize image format name.

        Args:
            fmt: Format name (e.g., 'jpg', 'JPEG', 'png')

        Returns:
            Normalized format name
        """
        fmt = fmt.lower().strip()
        if fmt.startswith('.'):
            fmt = fmt[1:]

        # Apply aliases
        fmt = self.FORMAT_ALIASES.get(fmt, fmt)

        return fmt

    def validate_format(self, fmt: str) -> bool:
        """
        Validate if format is supported.

        Args:
            fmt: Format name

        Returns:
            True if supported, False otherwise
        """
        normalized = self.normalize_format(fmt)
        return normalized in self.SUPPORTED_FORMATS

    def load_from_path(self, path: str) -> Dict[str, Any]:
        """
        Load image from file path.

        Args:
            path: Path to image file

        Returns:
            Result dictionary with image data
        """
        try:
            image_path = Path(path)

            if not image_path.exists():
                return {
                    'status': 'error',
                    'message': f'File not found: {path}'
                }

            if not image_path.is_file():
                return {
                    'status': 'error',
                    'message': f'Not a file: {path}'
                }

            # Load image
            image = Image.open(image_path)

            # Get image info
            info = self.get_image_info(image)

            # Convert to base64 for data transfer
            buffered = BytesIO()
            save_format = image.format if image.format else 'PNG'
            image.save(buffered, format=save_format)
            image_data = base64.b64encode(buffered.getvalue()).decode('utf-8')

            return {
                'status': 'success',
                'message': f'Loaded image from {path}',
                'image_data': image_data,
                'format': save_format.lower(),
                'width': info['width'],
                'height': info['height'],
                'mode': info['mode'],
                'size_bytes': len(buffered.getvalue())
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': f'Failed to load image: {str(e)}'
            }

    def load_from_base64(self, data: str) -> Optional[Image.Image]:
        """
        Load image from base64 string.

        Args:
            data: Base64 encoded image data

        Returns:
            PIL Image object or None on failure
        """
        try:
            image_bytes = base64.b64decode(data)
            return Image.open(BytesIO(image_bytes))
        except Exception:
            return None

    def get_image_info(self, image: Image.Image) -> Dict[str, Any]:
        """
        Get image metadata.

        Args:
            image: PIL Image object

        Returns:
            Dictionary with image information
        """
        return {
            'width': image.width,
            'height': image.height,
            'mode': image.mode,
            'format': image.format if image.format else 'Unknown',
            'size': (image.width, image.height)
        }

    def convert_format(
        self,
        image_data: str,
        from_format: str,
        to_format: str,
        quality: int = 95,
        resize: Optional[Tuple[int, int]] = None,
        maintain_aspect: bool = True
    ) -> Dict[str, Any]:
        """
        Convert image from one format to another.

        Args:
            image_data: Base64 encoded image data
            from_format: Source format
            to_format: Target format
            quality: Output quality (1-100, for JPEG/WEBP)
            resize: Optional (width, height) tuple for resizing
            maintain_aspect: Maintain aspect ratio when resizing

        Returns:
            Result dictionary with converted image
        """
        try:
            # Validate formats
            if not self.validate_format(to_format):
                return {
                    'status': 'error',
                    'message': f'Unsupported target format: {to_format}. '
                              f'Supported: {", ".join(sorted(self.SUPPORTED_FORMATS))}'
                }

            # Load image
            image = self.load_from_base64(image_data)
            if image is None:
                return {
                    'status': 'error',
                    'message': 'Failed to decode image data'
                }

            # Get original info
            original_info = self.get_image_info(image)

            # Resize if requested
            if resize:
                if maintain_aspect:
                    image.thumbnail(resize, Image.Resampling.LANCZOS)
                else:
                    image = image.resize(resize, Image.Resampling.LANCZOS)

            # Normalize target format
            to_format = self.normalize_format(to_format).upper()

            # Handle format-specific conversions
            if to_format == 'JPEG' and image.mode in ('RGBA', 'LA', 'P'):
                # JPEG doesn't support transparency, convert to RGB
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image = image.convert('RGBA')
                background.paste(image, mask=image.split()[-1] if image.mode in ('RGBA', 'LA') else None)
                image = background

            # Convert to target format
            buffered = BytesIO()

            # Set save parameters based on format
            save_kwargs = {'format': to_format}

            if to_format in ('JPEG', 'WEBP'):
                save_kwargs['quality'] = quality
                save_kwargs['optimize'] = True
            elif to_format == 'PNG':
                save_kwargs['optimize'] = True

            image.save(buffered, **save_kwargs)

            # Encode to base64
            converted_data = base64.b64encode(buffered.getvalue()).decode('utf-8')

            # Get new info
            new_info = self.get_image_info(image)

            return {
                'status': 'success',
                'message': f'Converted from {from_format} to {to_format}',
                'image_data': converted_data,
                'format': to_format.lower(),
                'original_format': original_info['format'],
                'original_size': original_info['size'],
                'new_size': new_info['size'],
                'width': new_info['width'],
                'height': new_info['height'],
                'mode': new_info['mode'],
                'size_bytes': len(buffered.getvalue())
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': f'Conversion failed: {str(e)}'
            }

    def save_to_path(
        self,
        image_data: str,
        output_path: str,
        format: Optional[str] = None,
        quality: int = 95,
        create_dirs: bool = True
    ) -> Dict[str, Any]:
        """
        Save image to file path.

        Args:
            image_data: Base64 encoded image data
            output_path: Output file path
            format: Image format (inferred from extension if not provided)
            quality: Output quality (1-100, for JPEG/WEBP)
            create_dirs: Create parent directories if needed

        Returns:
            Result dictionary
        """
        try:
            # Load image
            image = self.load_from_base64(image_data)
            if image is None:
                return {
                    'status': 'error',
                    'message': 'Failed to decode image data'
                }

            output_file = Path(output_path)

            # Create parent directories
            if create_dirs:
                output_file.parent.mkdir(parents=True, exist_ok=True)

            # Determine format
            if format:
                save_format = self.normalize_format(format).upper()
            else:
                # Infer from file extension
                ext = output_file.suffix.lower()
                if ext.startswith('.'):
                    ext = ext[1:]
                save_format = self.normalize_format(ext).upper()

            # Validate format
            if not self.validate_format(save_format):
                return {
                    'status': 'error',
                    'message': f'Unsupported format: {save_format}'
                }

            # Handle format-specific conversions
            if save_format == 'JPEG' and image.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image = image.convert('RGBA')
                background.paste(image, mask=image.split()[-1] if image.mode in ('RGBA', 'LA') else None)
                image = background

            # Save image
            save_kwargs = {}
            if save_format in ('JPEG', 'WEBP'):
                save_kwargs['quality'] = quality
                save_kwargs['optimize'] = True
            elif save_format == 'PNG':
                save_kwargs['optimize'] = True

            image.save(str(output_file), format=save_format, **save_kwargs)

            # Get file size
            file_size = output_file.stat().st_size

            return {
                'status': 'success',
                'message': f'Saved image to {output_path}',
                'path': str(output_file.resolve()),
                'format': save_format.lower(),
                'size_bytes': file_size,
                'width': image.width,
                'height': image.height
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': f'Failed to save image: {str(e)}'
            }

    def get_info(self, image_data: str) -> Dict[str, Any]:
        """
        Get image information from base64 data.

        Args:
            image_data: Base64 encoded image data

        Returns:
            Result dictionary with image information
        """
        try:
            image = self.load_from_base64(image_data)
            if image is None:
                return {
                    'status': 'error',
                    'message': 'Failed to decode image data'
                }

            info = self.get_image_info(image)

            return {
                'status': 'success',
                'message': 'Retrieved image information',
                'width': info['width'],
                'height': info['height'],
                'mode': info['mode'],
                'format': info['format'],
                'size': info['size']
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': f'Failed to get image info: {str(e)}'
            }

    def resize_image(
        self,
        image_data: str,
        width: Optional[int] = None,
        height: Optional[int] = None,
        maintain_aspect: bool = True,
        format: Optional[str] = None,
        quality: int = 95
    ) -> Dict[str, Any]:
        """
        Resize image.

        Args:
            image_data: Base64 encoded image data
            width: Target width (None to calculate from height)
            height: Target height (None to calculate from width)
            maintain_aspect: Maintain aspect ratio
            format: Output format (same as input if not specified)
            quality: Output quality

        Returns:
            Result dictionary with resized image
        """
        try:
            image = self.load_from_base64(image_data)
            if image is None:
                return {
                    'status': 'error',
                    'message': 'Failed to decode image data'
                }

            original_size = (image.width, image.height)

            # Calculate dimensions
            if width is None and height is None:
                return {
                    'status': 'error',
                    'message': 'Either width or height must be specified'
                }

            if maintain_aspect:
                if width and height:
                    # Use thumbnail to maintain aspect
                    image.thumbnail((width, height), Image.Resampling.LANCZOS)
                elif width:
                    # Calculate height from width
                    aspect = image.height / image.width
                    height = int(width * aspect)
                    image = image.resize((width, height), Image.Resampling.LANCZOS)
                else:
                    # Calculate width from height
                    aspect = image.width / image.height
                    width = int(height * aspect)
                    image = image.resize((width, height), Image.Resampling.LANCZOS)
            else:
                if not width:
                    width = image.width
                if not height:
                    height = image.height
                image = image.resize((width, height), Image.Resampling.LANCZOS)

            # Save to buffer
            buffered = BytesIO()
            save_format = format.upper() if format else (image.format if image.format else 'PNG')

            save_kwargs = {'format': save_format}
            if save_format in ('JPEG', 'WEBP'):
                save_kwargs['quality'] = quality

            image.save(buffered, **save_kwargs)

            # Encode to base64
            resized_data = base64.b64encode(buffered.getvalue()).decode('utf-8')

            return {
                'status': 'success',
                'message': f'Resized image from {original_size} to ({image.width}, {image.height})',
                'image_data': resized_data,
                'original_size': original_size,
                'new_size': (image.width, image.height),
                'width': image.width,
                'height': image.height,
                'format': save_format.lower(),
                'size_bytes': len(buffered.getvalue())
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': f'Failed to resize image: {str(e)}'
            }


def main():
    """
    Main entry point for image converter tool.

    Reads JSON input from stdin and executes the requested operation.
    """
    try:
        input_data = json.loads(sys.stdin.read())
    except Exception as e:
        print(json.dumps({
            'status': 'error',
            'message': f'Invalid JSON input: {str(e)}'
        }))
        sys.exit(1)

    # Get operation
    operation = input_data.get('operation')

    if not operation:
        print(json.dumps({
            'status': 'error',
            'message': 'Missing required parameter: operation'
        }))
        sys.exit(1)

    # Create converter
    converter = ImageConverter()

    # Execute operation
    result = None

    if operation == 'load':
        path = input_data.get('path')
        if not path:
            result = {
                'status': 'error',
                'message': 'Missing required parameter: path'
            }
        else:
            result = converter.load_from_path(path)

    elif operation == 'convert':
        image_data = input_data.get('image_data')
        from_format = input_data.get('from_format', 'auto')
        to_format = input_data.get('to_format')

        if not image_data:
            result = {
                'status': 'error',
                'message': 'Missing required parameter: image_data'
            }
        elif not to_format:
            result = {
                'status': 'error',
                'message': 'Missing required parameter: to_format'
            }
        else:
            quality = input_data.get('quality', 95)
            resize = input_data.get('resize')
            maintain_aspect = input_data.get('maintain_aspect', True)

            # Parse resize tuple
            if resize and isinstance(resize, list) and len(resize) == 2:
                resize = tuple(resize)
            else:
                resize = None

            result = converter.convert_format(
                image_data, from_format, to_format, quality, resize, maintain_aspect
            )

    elif operation == 'save':
        image_data = input_data.get('image_data')
        output_path = input_data.get('output_path')

        if not image_data:
            result = {
                'status': 'error',
                'message': 'Missing required parameter: image_data'
            }
        elif not output_path:
            result = {
                'status': 'error',
                'message': 'Missing required parameter: output_path'
            }
        else:
            format = input_data.get('format')
            quality = input_data.get('quality', 95)
            create_dirs = input_data.get('create_dirs', True)

            result = converter.save_to_path(
                image_data, output_path, format, quality, create_dirs
            )

    elif operation == 'info':
        image_data = input_data.get('image_data')

        if not image_data:
            result = {
                'status': 'error',
                'message': 'Missing required parameter: image_data'
            }
        else:
            result = converter.get_info(image_data)

    elif operation == 'resize':
        image_data = input_data.get('image_data')

        if not image_data:
            result = {
                'status': 'error',
                'message': 'Missing required parameter: image_data'
            }
        else:
            width = input_data.get('width')
            height = input_data.get('height')
            maintain_aspect = input_data.get('maintain_aspect', True)
            format = input_data.get('format')
            quality = input_data.get('quality', 95)

            result = converter.resize_image(
                image_data, width, height, maintain_aspect, format, quality
            )

    else:
        result = {
            'status': 'error',
            'message': f'Unknown operation: {operation}. '
                      f'Supported: load, convert, save, info, resize'
        }

    # Output result
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
