#!/usr/bin/env python3
"""
ScikiQ Database MCP Server Entry Point

Convenience script to start the MCP server from the package root.
"""

import sys
from pathlib import Path

# Add the package to Python path
package_root = Path(__file__).parent
sys.path.insert(0, str(package_root))

# Import and run the main function
from scikiq_dbutils.mcp_server.main import main

if __name__ == "__main__":
    sys.exit(main())