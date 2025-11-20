"""
ScikiQ Database Utils MCP Server

A Model Context Protocol (MCP) server that exposes database functionality
as tools for performing various database operations. Supports multiple
database types including MySQL, Oracle, PostgreSQL, SQL Server, and more.
"""

__version__ = "1.0.0"
__author__ = "ScikiQ Team"

# Import classes when needed to avoid circular imports
def get_mcp_server():
    from .server import MCPServer
    return MCPServer

def get_config_manager():
    from .config.manager import ConfigManager
    return ConfigManager

__all__ = ["MCPServer", "ConfigManager"]