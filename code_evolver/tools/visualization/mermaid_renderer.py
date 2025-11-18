#!/usr/bin/env python3
"""
Mermaid Renderer
Renders Mermaid diagram syntax to image files (SVG, PNG, PDF).
"""

import json
import sys
import os
import tempfile
import subprocess
import hashlib
from pathlib import Path
from typing import Optional
from datetime import datetime


class MermaidRenderer:
    """Render Mermaid diagrams to various image formats."""

    def __init__(self, cache_dir: Optional[str] = None):
        self.cache_dir = cache_dir or os.path.join(tempfile.gettempdir(), "mermaid_cache")
        Path(self.cache_dir).mkdir(parents=True, exist_ok=True)

    def _get_cache_key(self, mermaid: str, format: str, theme: str) -> str:
        """Generate a cache key for the diagram."""
        content = f"{mermaid}|{format}|{theme}"
        return hashlib.sha256(content.encode()).hexdigest()

    def _get_cached_path(self, cache_key: str, format: str) -> Optional[str]:
        """Get cached file path if it exists."""
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.{format}")
        if os.path.exists(cache_file):
            return cache_file
        return None

    def _check_dependencies(self) -> dict:
        """Check if required dependencies are available."""
        result = {
            "mermaid_cli": False,
            "node": False,
            "playwright": False,
            "method": None
        }

        # Check for mmdc (mermaid-cli)
        try:
            subprocess.run(
                ["mmdc", "--version"],
                capture_output=True,
                check=True,
                timeout=5
            )
            result["mermaid_cli"] = True
            result["method"] = "mmdc"
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            pass

        # Check for node
        try:
            subprocess.run(
                ["node", "--version"],
                capture_output=True,
                check=True,
                timeout=5
            )
            result["node"] = True
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            pass

        # Check for playwright
        if not result["mermaid_cli"]:
            try:
                import playwright
                result["playwright"] = True
                result["method"] = "playwright"
            except ImportError:
                pass

        return result

    def _render_with_mmdc(
        self,
        mermaid: str,
        output_path: str,
        format: str,
        theme: str,
        background: str,
        width: int,
        height: Optional[int],
        scale: float
    ) -> bool:
        """Render using mermaid-cli (mmdc)."""
        # Create temporary input file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.mmd', delete=False) as f:
            f.write(mermaid)
            input_path = f.name

        try:
            cmd = [
                "mmdc",
                "-i", input_path,
                "-o", output_path,
                "-t", theme,
                "-b", background
            ]

            if width:
                cmd.extend(["-w", str(width)])
            if height:
                cmd.extend(["-H", str(height)])
            if format == "png" and scale != 1:
                cmd.extend(["-s", str(scale)])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                raise RuntimeError(f"mmdc failed: {result.stderr}")

            return True

        finally:
            # Clean up temp file
            try:
                os.unlink(input_path)
            except:
                pass

    def _render_with_playwright(
        self,
        mermaid: str,
        output_path: str,
        format: str,
        theme: str,
        background: str,
        width: int,
        height: Optional[int]
    ) -> bool:
        """Render using Playwright (fallback method)."""
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise ImportError(
                "Playwright is not installed. Install with: pip install playwright && playwright install chromium"
            )

        # Create HTML with Mermaid
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <script type="module">
        import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
        mermaid.initialize({{
            startOnLoad: true,
            theme: '{theme}'
        }});
    </script>
    <style>
        body {{
            margin: 0;
            padding: 20px;
            background: {background};
        }}
        .mermaid {{
            display: flex;
            justify-content: center;
        }}
    </style>
</head>
<body>
    <div class="mermaid">
{mermaid}
    </div>
</body>
</html>
"""

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": width, "height": height or 600})
            page.set_content(html_content)
            page.wait_for_timeout(2000)  # Wait for Mermaid to render

            if format == "svg":
                # Extract SVG
                svg_content = page.locator(".mermaid svg").inner_html()
                with open(output_path, 'w') as f:
                    f.write(f'<svg xmlns="http://www.w3.org/2000/svg">{svg_content}</svg>')
            else:
                # Screenshot
                page.locator(".mermaid").screenshot(
                    path=output_path,
                    type=format if format == "png" else "png"
                )

            browser.close()

        return True

    def _render_fallback_svg(self, mermaid: str, output_path: str) -> bool:
        """Fallback: Create a simple SVG with the mermaid text."""
        svg_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="800" height="600">
    <rect width="100%" height="100%" fill="white"/>
    <text x="10" y="30" font-family="monospace" font-size="14" fill="black">
        <tspan x="10" dy="1.2em">Mermaid diagram (rendering not available)</tspan>
        <tspan x="10" dy="1.2em">Install mermaid-cli: npm install -g @mermaid-js/mermaid-cli</tspan>
        <tspan x="10" dy="2em">Diagram source:</tspan>
    </text>
    <text x="10" y="120" font-family="monospace" font-size="12" fill="#666">
        {self._escape_xml(mermaid[:500])}
    </text>
</svg>"""

        with open(output_path, 'w') as f:
            f.write(svg_content)
        return True

    def _escape_xml(self, text: str) -> str:
        """Escape XML special characters."""
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def render(
        self,
        mermaid: str,
        output_path: Optional[str] = None,
        format: str = "svg",
        theme: str = "default",
        background_color: str = "transparent",
        width: int = 800,
        height: Optional[int] = None,
        scale: float = 1.0,
        use_cache: bool = True
    ) -> dict:
        """Render a Mermaid diagram to an image file."""

        # Check cache
        if use_cache:
            cache_key = self._get_cache_key(mermaid, format, theme)
            cached_path = self._get_cached_path(cache_key, format)
            if cached_path:
                if output_path and output_path != cached_path:
                    # Copy cached file to desired output path
                    import shutil
                    shutil.copy2(cached_path, output_path)
                    final_path = output_path
                else:
                    final_path = cached_path

                return {
                    "success": True,
                    "output_path": final_path,
                    "format": format,
                    "cached": True,
                    "size_bytes": os.path.getsize(final_path)
                }

        # Determine output path
        if not output_path:
            if use_cache:
                output_path = os.path.join(self.cache_dir, f"{cache_key}.{format}")
            else:
                suffix = f".{format}"
                fd, output_path = tempfile.mkstemp(suffix=suffix, dir=self.cache_dir)
                os.close(fd)

        # Check dependencies
        deps = self._check_dependencies()

        # Render based on available method
        try:
            if deps["method"] == "mmdc":
                success = self._render_with_mmdc(
                    mermaid, output_path, format, theme,
                    background_color, width, height, scale
                )
            elif deps["method"] == "playwright":
                success = self._render_with_playwright(
                    mermaid, output_path, format, theme,
                    background_color, width, height
                )
            else:
                # Fallback: create a simple SVG
                if format == "svg":
                    success = self._render_fallback_svg(mermaid, output_path)
                else:
                    raise RuntimeError(
                        "No rendering method available. Install mermaid-cli:\n"
                        "  npm install -g @mermaid-js/mermaid-cli\n"
                        "Or install playwright:\n"
                        "  pip install playwright && playwright install chromium"
                    )

            if success and os.path.exists(output_path):
                return {
                    "success": True,
                    "output_path": output_path,
                    "format": format,
                    "cached": False,
                    "size_bytes": os.path.getsize(output_path),
                    "method": deps["method"] or "fallback",
                    "dependencies": deps
                }
            else:
                raise RuntimeError("Rendering failed: output file not created")

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "dependencies": deps,
                "output_path": output_path if os.path.exists(output_path) else None
            }


def main():
    """Main entry point for the mermaid renderer tool."""
    try:
        # Read input from stdin
        input_data = json.load(sys.stdin)

        # Extract parameters
        mermaid = input_data.get("mermaid")
        if not mermaid:
            raise ValueError("mermaid parameter is required")

        renderer = MermaidRenderer()

        # Render diagram
        result = renderer.render(
            mermaid=mermaid,
            output_path=input_data.get("output_path"),
            format=input_data.get("format", "svg"),
            theme=input_data.get("theme", "default"),
            background_color=input_data.get("background_color", "transparent"),
            width=input_data.get("width", 800),
            height=input_data.get("height"),
            scale=input_data.get("scale", 1.0),
            use_cache=input_data.get("cache", True)
        )

        result["timestamp"] = datetime.now().isoformat()

        print(json.dumps(result, indent=2))
        sys.exit(0 if result.get("success") else 1)

    except Exception as e:
        error_result = {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }
        print(json.dumps(error_result, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
