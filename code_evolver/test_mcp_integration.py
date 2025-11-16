#!/usr/bin/env python3
"""
Test script for MCP (Model Context Protocol) integration.

This script demonstrates how to:
1. Load MCP server configurations
2. Connect to MCP servers
3. Discover and list available tools
4. Use MCP tools through the system's tool manager

Usage:
    python test_mcp_integration.py [--config config.mcp.yaml]
"""
import sys
import logging
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.config_manager import ConfigManager
from src.mcp_client_manager import get_mcp_client_manager
from src.mcp_tool_adapter import get_mcp_tool_adapter
from src.tools_manager import ToolsManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main test function."""
    # Parse arguments
    parser = argparse.ArgumentParser(description='Test MCP integration')
    parser.add_argument(
        '--config',
        default='config.mcp.yaml',
        help='Path to config file (default: config.mcp.yaml)'
    )
    args = parser.parse_args()

    logger.info("=" * 80)
    logger.info("MCP Integration Test")
    logger.info("=" * 80)

    # 1. Load configuration
    logger.info(f"\n1. Loading configuration from {args.config}")
    try:
        config_manager = ConfigManager(args.config)
        logger.info("✓ Configuration loaded successfully")
    except Exception as e:
        logger.error(f"✗ Failed to load configuration: {e}")
        return 1

    # 2. Initialize MCP client manager
    logger.info("\n2. Initializing MCP client manager")
    try:
        mcp_manager = get_mcp_client_manager()
        mcp_manager.load_from_config(config_manager.config)
        logger.info(f"✓ Loaded {len(mcp_manager.list_servers())} MCP server configuration(s)")
        logger.info(f"   Servers: {', '.join(mcp_manager.list_servers())}")
    except Exception as e:
        logger.error(f"✗ Failed to initialize MCP manager: {e}")
        return 1

    # 3. Connect to MCP servers
    logger.info("\n3. Connecting to MCP servers")
    try:
        mcp_manager.connect_all_sync()
        connected = mcp_manager.list_connected_servers()
        logger.info(f"✓ Connected to {len(connected)} server(s)")
        if connected:
            logger.info(f"   Connected: {', '.join(connected)}")
        else:
            logger.warning("   No servers connected")
    except Exception as e:
        logger.error(f"✗ Failed to connect to MCP servers: {e}")
        return 1

    # 4. Load tools from MCP servers
    logger.info("\n4. Loading tools from MCP servers")
    try:
        mcp_adapter = get_mcp_tool_adapter()
        tools = mcp_adapter.load_all_tools_sync()
        logger.info(f"✓ Loaded {len(tools)} tool(s) from MCP servers")

        if tools:
            logger.info("\n   Available MCP Tools:")
            for tool in tools:
                logger.info(f"   • {tool.name}")
                logger.info(f"     - Description: {tool.description}")
                logger.info(f"     - Tags: {', '.join(tool.tags)}")
                logger.info(f"     - Server: {tool.metadata.get('mcp_server', 'unknown')}")
                if tool.parameters:
                    param_names = ', '.join(tool.parameters.keys())
                    logger.info(f"     - Parameters: {param_names}")
                logger.info("")
    except Exception as e:
        logger.error(f"✗ Failed to load tools: {e}")
        return 1

    # 5. Test integration with ToolsManager
    logger.info("\n5. Testing integration with ToolsManager")
    try:
        tools_manager = ToolsManager(
            config_manager=config_manager
        )

        # Count MCP tools in the registry
        mcp_tools = [t for t in tools_manager.tools.values() if 'mcp' in t.tags]
        logger.info(f"✓ ToolsManager has {len(mcp_tools)} MCP tool(s) registered")

        if mcp_tools:
            logger.info("\n   MCP Tools in Registry:")
            for tool in mcp_tools[:5]:  # Show first 5
                logger.info(f"   • {tool.name} (ID: {tool.tool_id})")

            if len(mcp_tools) > 5:
                logger.info(f"   ... and {len(mcp_tools) - 5} more")
    except Exception as e:
        logger.error(f"✗ Failed to test ToolsManager integration: {e}")
        logger.exception(e)
        return 1

    # 6. Cleanup
    logger.info("\n6. Cleaning up")
    try:
        mcp_manager.disconnect_all_sync()
        logger.info("✓ Disconnected from all MCP servers")
    except Exception as e:
        logger.warning(f"⚠ Error during cleanup: {e}")

    logger.info("\n" + "=" * 80)
    logger.info("✓ MCP Integration Test Completed Successfully")
    logger.info("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(main())
