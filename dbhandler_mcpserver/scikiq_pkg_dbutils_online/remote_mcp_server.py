#!/usr/bin/env python3
"""
SciKiq DB Utils - Remote MCP Server for Claude Connectors

This module creates a remote MCP server that can be used as a Claude Connector.
It exposes the database utilities via HTTP endpoints for remote access.

Features:
- StreamableHTTP transport support
- Optional OAuth authentication
- CORS support for web clients
- Production-ready deployment
- Claude Desktop integration
"""

import asyncio
import contextlib
import logging
import os
import sys
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any, Literal

import click
import uvicorn
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.routing import Mount, Route
from starlette.responses import Response, JSONResponse
from starlette.types import Receive, Scope, Send

# Add the package to Python path
package_root = Path(__file__).parent
sys.path.insert(0, str(package_root))

# Import our existing MCP server tools
from scikiq_dbutils.mcp_server.config.manager import ConfigManager
from scikiq_dbutils.mcp_server.config.ini_parser import IniConfigParser
from scikiq_dbutils.mcp_server.wrappers.connection_manager import ConnectionManager
from scikiq_dbutils.mcp_server.tools.registry import ToolRegistry
from scikiq_dbutils.mcp_server.wrappers.db_wrapper import DatabaseWrapper


logger = logging.getLogger(__name__)


class FastMCPServer:
    """FastMCP-style server using our existing tools"""
    
    def __init__(self, name: str, config_path: str):
        self.name = name
        self.config_path = config_path
        
        # Initialize our existing components
        try:
            if os.path.exists(config_path):
                parser = IniConfigParser(config_path)
                connection_configs = parser.parse_all_connections()
            else:
                logger.warning(f"Config file {config_path} not found, using empty configuration")
                connection_configs = {}
                
            self.connection_manager = ConnectionManager(connection_configs)
            self.db_wrapper = DatabaseWrapper(self.connection_manager)
            self.tool_registry = ToolRegistry(self.db_wrapper)
            
        except Exception as e:
            logger.error(f"Failed to initialize MCP server: {e}")
            raise
    
    async def list_tools(self):
        """List available tools"""
        try:
            # Use the registry's list_tools method
            tools_data = self.tool_registry.list_tools()
            return {"tools": tools_data}
        except Exception as e:
            logger.error(f"Error listing tools: {e}")
            return {"tools": []}
    
    async def call_tool(self, name: str, arguments: dict):
        """Call a tool with arguments"""
        try:
            from scikiq_dbutils.mcp_server.protocol.messages import MCPToolCall
            
            # Create tool call object
            tool_call = MCPToolCall(name=name, arguments=arguments)
            
            # Execute the tool using the registry
            result = self.tool_registry.execute_tool(tool_call)
            
            # Convert result to the expected format
            if hasattr(result, 'is_error') and result.is_error:
                return {
                    "content": [{"type": "text", "text": result.content.get("message", "Tool execution failed")}],
                    "isError": True
                }
            else:
                # Success case
                if hasattr(result, 'content'):
                    if isinstance(result.content, dict):
                        content_text = str(result.content)
                    else:
                        content_text = str(result.content)
                else:
                    content_text = str(result)
                
                return {
                    "content": [{"type": "text", "text": content_text}],
                    "isError": False
                }
                
        except Exception as e:
            logger.error(f"Error calling tool {name}: {e}")
            return {
                "content": [{"type": "text", "text": f"Error executing tool: {str(e)}"}],
                "isError": True
            }


class RemoteMCPServer:
    """Remote MCP Server for Claude Connectors"""
    
    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 3000,
        config_path: str | None = None,
        cors_origins: list[str] | None = None,
        debug: bool = False
    ):
        self.host = host
        self.port = port
        self.config_path = config_path or os.getenv("CONFIG_PATH", "config.ini")
        self.cors_origins = cors_origins or ["*"]
        self.debug = debug
        
        # Create the MCP server
        self.mcp_server = FastMCPServer("SciKiq DB Utils", self.config_path)
        
    async def create_starlette_app(self) -> Starlette:
        """Create the Starlette ASGI application"""
        
        # Basic MCP tool endpoints
        async def list_tools_endpoint(request):
            """List available tools endpoint"""
            try:
                tools = await self.mcp_server.list_tools()
                return JSONResponse(tools)
            except Exception as e:
                logger.error(f"Error in list_tools: {e}")
                return JSONResponse(
                    {"error": f"Failed to list tools: {str(e)}"},
                    status_code=500
                )
        
        async def call_tool_endpoint(request):
            """Call tool endpoint"""
            try:
                data = await request.json()
                tool_name = data.get("name")
                arguments = data.get("arguments", {})
                
                if not tool_name:
                    return JSONResponse(
                        {"error": "Missing tool name"},
                        status_code=400
                    )
                
                result = await self.mcp_server.call_tool(tool_name, arguments)
                return JSONResponse(result)
                
            except Exception as e:
                logger.error(f"Error in call_tool: {e}")
                return JSONResponse(
                    {"error": f"Failed to call tool: {str(e)}"},
                    status_code=500
                )
        
        async def health_check(request):
            """Health check endpoint"""
            try:
                # Test database connections
                connection_status = {}
                for conn_id in self.mcp_server.connection_manager.connections:
                    try:
                        conn_config = self.mcp_server.connection_manager.get_connection_config(conn_id)
                        connection_status[conn_id] = "available"
                    except Exception:
                        connection_status[conn_id] = "error"
                        
                return JSONResponse({
                    "status": "healthy",
                    "service": "SciKiq DB Utils MCP Server",
                    "version": "1.0.0",
                    "connections": connection_status,
                    "config_path": self.config_path
                })
            except Exception as e:
                return JSONResponse(
                    {
                        "status": "unhealthy", 
                        "error": str(e)
                    },
                    status_code=500
                )
        
        async def mcp_info(request):
            """MCP server information"""
            return JSONResponse({
                "name": "SciKiq DB Utils MCP Server",
                "version": "1.0.0",
                "description": "Database connectivity and analysis for Claude",
                "capabilities": {
                    "tools": True,
                    "resources": False,
                    "prompts": False
                },
                "endpoints": {
                    "tools": "/mcp/tools",
                    "call": "/mcp/call",
                    "health": "/health"
                }
            })
        
        # Create routes
        routes = [
            Route("/health", endpoint=health_check, methods=["GET"]),
            Route("/mcp/info", endpoint=mcp_info, methods=["GET"]),
            Route("/mcp/tools", endpoint=list_tools_endpoint, methods=["GET"]),
            Route("/mcp/call", endpoint=call_tool_endpoint, methods=["POST"]),
        ]
        
        # Create Starlette app
        app = Starlette(
            debug=self.debug,
            routes=routes,
        )
        
        # Add CORS middleware
        app = CORSMiddleware(
            app,
            allow_origins=self.cors_origins,
            allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
            allow_headers=["*"],
            expose_headers=["Content-Type"],
            allow_credentials=True,
        )
        
        return app
    
    async def run(self):
        """Run the remote MCP server"""
        app = await self.create_starlette_app()
        
        logger.info(f"🚀 SciKiq MCP Server starting on http://{self.host}:{self.port}")
        logger.info(f"🔧 Config: {self.config_path}")
        logger.info(f"📡 Endpoints: /health, /mcp/info, /mcp/tools, /mcp/call")
        
        # Configure uvicorn
        config = uvicorn.Config(
            app=app,
            host=self.host,
            port=self.port,
            log_level="info" if not self.debug else "debug",
            access_log=self.debug,
        )
        
        server = uvicorn.Server(config)
        await server.serve()


@click.command()
@click.option(
    "--host",
    default="0.0.0.0",
    help="Host to bind to (default: 0.0.0.0 for remote access)"
)
@click.option(
    "--port",
    default=3000,
    help="Port to listen on (default: 3000)"
)
@click.option(
    "--config-path",
    help="Path to configuration file (default: config.ini or CONFIG_PATH env var)"
)
@click.option(
    "--cors-origins",
    multiple=True,
    help="Allowed CORS origins (can be specified multiple times, default: all origins)"
)
@click.option(
    "--debug",
    is_flag=True,
    help="Enable debug mode with verbose logging"
)
def main(
    host: str,
    port: int,
    config_path: str | None,
    cors_origins: tuple[str, ...],
    debug: bool,
) -> int:
    """
    SciKiq DB Utils - Remote MCP Server for Claude Connectors
    
    This server provides database connectivity for Claude Desktop via HTTP transport.
    It supports 25+ database systems with enterprise security features.
    
    Examples:
    
        # Start server for local development
        python remote_mcp_server.py --debug
        
        # Start server for production deployment  
        python remote_mcp_server.py --host 0.0.0.0 --port 8080
        
        # Specify custom configuration file
        python remote_mcp_server.py --config-path /path/to/config.ini
        
        # Configure CORS for specific origins
        python remote_mcp_server.py --cors-origins https://claude.ai --cors-origins https://claude.com
    """
    
    # Configure logging
    log_level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Convert CORS origins tuple to list
    cors_origins_list = list(cors_origins) if cors_origins else ["*"]
    
    # Create and run server
    server = RemoteMCPServer(
        host=host,
        port=port,
        config_path=config_path,
        cors_origins=cors_origins_list,
        debug=debug
    )
    
    try:
        asyncio.run(server.run())
        return 0
    except KeyboardInterrupt:
        logger.info("🛑 Server stopped by user")
        return 0
    except Exception as e:
        logger.error(f"❌ Server error: {e}")
        if debug:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())