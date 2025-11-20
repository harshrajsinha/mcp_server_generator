"""
Main MCP Server Implementation

Handles JSON-RPC 2.0 communication for Model Context Protocol.
"""

import json
import asyncio
import logging
import sys
import traceback
from typing import Dict, Any, Optional, List
from datetime import datetime
from io import StringIO

from scikiq_dbutils.mcp_server.protocol.messages import (
    JsonRpcRequest, JsonRpcResponse, JsonRpcError, MCPToolCall,
    create_parse_error, create_invalid_request_error, create_method_not_found_error,
    create_invalid_params_error, create_internal_error
)
from scikiq_dbutils.mcp_server.wrappers.connection_manager import ConnectionManager
from scikiq_dbutils.mcp_server.wrappers.db_wrapper import DatabaseWrapper
from scikiq_dbutils.mcp_server.tools.registry import ToolRegistry


class MCPServer:
    """
    Model Context Protocol Server for Database Operations
    
    Implements JSON-RPC 2.0 server that exposes database functionality as MCP tools.
    """
    
    def __init__(self, name: str = "ScikiQ Database MCP Server", version: str = "1.0.0", 
                 connection_configs: Optional[Dict[str, Any]] = None):
        self.name = name
        self.version = version
        self.connection_manager = ConnectionManager(connection_configs)
        self.db_wrapper = DatabaseWrapper(self.connection_manager)
        self.tool_registry = ToolRegistry(self.db_wrapper)
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        self._setup_logging()
        
        # Server state
        self.is_running = False
        self._capabilities = self._build_capabilities()
        
        self.logger.info(f"Initialized {self.name} v{self.version}")
    
    def _setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('mcp_server.log')
            ]
        )
    
    def _build_capabilities(self) -> Dict[str, Any]:
        """Build server capabilities object"""
        return {
            "tools": {
                "listChanged": True
            },
            "prompts": {},
            "resources": {},
            "experimental": {}
        }
    
    async def handle_request(self, request_data: str) -> str:
        """
        Handle incoming JSON-RPC request
        
        Args:
            request_data: JSON string containing the request
            
        Returns:
            JSON string containing the response
        """
        try:
            # Parse JSON-RPC request
            try:
                request_dict = json.loads(request_data)
            except json.JSONDecodeError as e:
                error_response = JsonRpcResponse.error(
                    id=None,
                    error=create_parse_error(str(e))
                )
                return error_response.to_json()
            
            # Validate basic JSON-RPC structure
            if not isinstance(request_dict, dict):
                error_response = JsonRpcResponse.error(
                    id=None,
                    error=create_invalid_request_error("Request must be a JSON object")
                )
                return error_response.to_json()
            
            # Extract request ID for response
            request_id = request_dict.get("id")
            
            try:
                request = JsonRpcRequest.from_dict(request_dict)
            except (KeyError, ValueError) as e:
                error_response = JsonRpcResponse.error(
                    id=request_id,
                    error=create_invalid_request_error(str(e))
                )
                return error_response.to_json()
            
            # Route to method handler
            response = await self._route_request(request)
            return response.to_json()
            
        except Exception as e:
            self.logger.error(f"Unexpected error handling request: {str(e)}")
            self.logger.error(traceback.format_exc())
            
            error_response = JsonRpcResponse.error(
                id=None,
                error=create_internal_error(str(e))
            )
            return error_response.to_json()
    
    async def _route_request(self, request: JsonRpcRequest) -> JsonRpcResponse:
        """
        Route request to appropriate handler method
        
        Args:
            request: Parsed JSON-RPC request
            
        Returns:
            JSON-RPC response
        """
        method_handlers = {
            "initialize": self._handle_initialize,
            "tools/list": self._handle_tools_list,
            "tools/call": self._handle_tools_call,
            "server/info": self._handle_server_info,
            "server/status": self._handle_server_status,
            "ping": self._handle_ping,
        }
        
        if request.method not in method_handlers:
            return JsonRpcResponse.error(
                id=request.id,
                error=create_method_not_found_error(request.method)
            )
        
        try:
            handler = method_handlers[request.method]
            result = await handler(request.params or {})
            return JsonRpcResponse.success(id=request.id, result=result)
            
        except Exception as e:
            self.logger.error(f"Error in method '{request.method}': {str(e)}")
            self.logger.error(traceback.format_exc())
            
            return JsonRpcResponse.error(
                id=request.id,
                error=create_internal_error(f"Error in {request.method}: {str(e)}")
            )
    
    async def _handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP initialize request"""
        self.logger.info(f"Initialize request from client: {params.get('clientInfo', {})}")
        
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": self._capabilities,
            "serverInfo": {
                "name": self.name,
                "version": self.version
            }
        }
    
    async def _handle_tools_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/list request"""
        self.logger.info("Tools list requested")
        
        tools = self.tool_registry.list_tools()
        return {"tools": tools}
    
    async def _handle_tools_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/call request"""
        try:
            # Validate required parameters
            if "name" not in params:
                raise ValueError("Missing required parameter: name")
            if "arguments" not in params:
                raise ValueError("Missing required parameter: arguments")
            
            # Create tool call
            tool_call = MCPToolCall(
                name=params["name"],
                arguments=params["arguments"]
            )
            
            self.logger.info(f"Executing tool: {tool_call.name}")
            
            # Execute tool
            result = self.tool_registry.execute_tool(tool_call)
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result.to_dict(), indent=2) if result.content else "No result"
                    }
                ],
                "isError": result.is_error
            }
            
        except ValueError as e:
            raise ValueError(f"Invalid tool call parameters: {str(e)}")
        except Exception as e:
            self.logger.error(f"Error executing tool: {str(e)}")
            return {
                "content": [
                    {
                        "type": "text", 
                        "text": f"Tool execution error: {str(e)}"
                    }
                ],
                "isError": True
            }
    
    async def _handle_server_info(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle server info request"""
        tools_by_category = self.tool_registry.get_tools_by_category()
        connections = self.connection_manager.list_connections()
        
        return {
            "name": self.name,
            "version": self.version,
            "description": "MCP Server for database operations using ScikiQ DB Utils",
            "capabilities": self._capabilities,
            "statistics": {
                "total_tools": len(self.tool_registry.get_tools_list()),
                "active_connections": len(connections),
                "tools_by_category": {cat: len(tools) for cat, tools in tools_by_category.items()}
            },
            "supported_databases": [
                "MySQL", "PostgreSQL", "Oracle", "SQL Server", "MongoDB",
                "Snowflake", "BigQuery", "Redshift", "Athena", "SAP HANA",
                "Vertica", "DB2", "Teradata", "ChromaDB", "SageMaker"
            ]
        }
    
    async def _handle_server_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle server status request"""
        connections = self.connection_manager.list_connections()
        
        return {
            "status": "running" if self.is_running else "stopped",
            "uptime": datetime.now().isoformat(),
            "connections": connections,
            "memory_usage": self._get_memory_usage()
        }
    
    async def _handle_ping(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle ping request"""
        return {
            "pong": True,
            "timestamp": datetime.now().isoformat(),
            "server": self.name
        }
    
    def _get_memory_usage(self) -> Dict[str, Any]:
        """Get memory usage information"""
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            return {
                "rss": memory_info.rss,
                "vms": memory_info.vms,
                "percent": process.memory_percent()
            }
        except ImportError:
            return {"error": "psutil not available"}
        except Exception as e:
            return {"error": str(e)}
    
    def start(self):
        """Start the MCP server"""
        self.is_running = True
        self.logger.info(f"Started {self.name} v{self.version}")
    
    def stop(self):
        """Stop the MCP server"""
        self.is_running = False
        self.connection_manager.close_all()
        self.logger.info(f"Stopped {self.name}")
    
    async def run_stdio(self):
        """
        Run server using stdin/stdout for communication
        
        This is the standard way MCP servers communicate with clients
        """
        self.start()
        
        try:
            while self.is_running:
                try:
                    # Read from stdin
                    line = await asyncio.get_event_loop().run_in_executor(
                        None, sys.stdin.readline
                    )
                    
                    if not line:  # EOF
                        break
                    
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Process request
                    response = await self.handle_request(line)
                    
                    # Write to stdout
                    print(response, flush=True)
                    
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    self.logger.error(f"Error in stdio loop: {str(e)}")
                    
        finally:
            self.stop()
    
    def get_tool_help(self, tool_name: Optional[str] = None) -> str:
        """
        Get help information for tools
        
        Args:
            tool_name: Specific tool name, or None for all tools
            
        Returns:
            Formatted help text
        """
        if tool_name:
            tool_info = self.tool_registry.get_tool_info(tool_name)
            if "error" in tool_info:
                return f"Error: {tool_info['message']}"
            
            schema = tool_info["schema"]
            help_text = f"Tool: {schema['name']}\\n"
            help_text += f"Description: {schema['description']}\\n\\n"
            
            if "properties" in schema.get("inputSchema", {}):
                help_text += "Parameters:\\n"
                properties = schema["inputSchema"]["properties"]
                required = schema["inputSchema"].get("required", [])
                
                for param_name, param_schema in properties.items():
                    required_marker = " (required)" if param_name in required else ""
                    param_type = param_schema.get("type", "unknown")
                    description = param_schema.get("description", "")
                    help_text += f"  - {param_name} ({param_type}){required_marker}: {description}\\n"
            
            return help_text
        else:
            # List all tools by category
            tools_by_category = self.tool_registry.get_tools_by_category()
            help_text = f"{self.name} - Available Tools\\n"
            help_text += "=" * 50 + "\\n\\n"
            
            for category, tool_names in tools_by_category.items():
                help_text += f"{category.title()} Tools:\\n"
                for tool_name in sorted(tool_names):
                    tool_schema = self.tool_registry.get_tool_schema(tool_name)
                    if tool_schema:
                        help_text += f"  - {tool_name}: {tool_schema.description}\\n"
                help_text += "\\n"
            
            return help_text