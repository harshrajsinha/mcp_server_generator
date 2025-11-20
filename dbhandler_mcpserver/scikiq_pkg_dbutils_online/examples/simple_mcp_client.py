"""
Example: Basic MCP Client for ScikiQ Database Server

This example shows how to create a simple MCP client that communicates
with the ScikiQ Database MCP Server.
"""

import json
import subprocess
import sys
import asyncio
from typing import Dict, Any, Optional


class SimpleMCPClient:
    """
    Simple MCP client that communicates with the database server via stdin/stdout
    """
    
    def __init__(self, server_command: list):
        self.server_command = server_command
        self.process = None
        self.request_id = 0
    
    async def start_server(self):
        """Start the MCP server process"""
        self.process = await asyncio.create_subprocess_exec(
            *self.server_command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        print("MCP Server started")
    
    async def stop_server(self):
        """Stop the MCP server process"""
        if self.process:
            self.process.terminate()
            await self.process.wait()
            print("MCP Server stopped")
    
    def _get_next_request_id(self) -> str:
        """Get next request ID"""
        self.request_id += 1
        return str(self.request_id)
    
    async def send_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Send a JSON-RPC request to the server"""
        if not self.process:
            raise RuntimeError("Server not started")
        
        request = {
            "jsonrpc": "2.0",
            "id": self._get_next_request_id(),
            "method": method
        }
        
        if params:
            request["params"] = params
        
        # Send request
        request_json = json.dumps(request) + "\\n"
        self.process.stdin.write(request_json.encode())
        await self.process.stdin.drain()
        
        # Read response
        response_line = await self.process.stdout.readline()
        if not response_line:
            raise RuntimeError("No response from server")
        
        response = json.loads(response_line.decode().strip())
        return response
    
    async def initialize(self) -> Dict[str, Any]:
        """Initialize the MCP session"""
        return await self.send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "clientInfo": {
                "name": "SimpleMCPClient",
                "version": "1.0.0"
            }
        })
    
    async def list_tools(self) -> Dict[str, Any]:
        """Get list of available tools"""
        return await self.send_request("tools/list")
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a specific tool"""
        return await self.send_request("tools/call", {
            "name": tool_name,
            "arguments": arguments
        })
    
    async def get_server_info(self) -> Dict[str, Any]:
        """Get server information"""
        return await self.send_request("server/info")


async def main():
    """Example usage of the MCP client"""
    
    # Configuration for database connection
    db_config = {
        "dbType": "MYSQL",
        "hostname": "localhost",
        "port": 3306,
        "dbname": "testdb", 
        "dbuser": "testuser",
        "dbpassword": "testpass"
    }
    
    # Create client
    server_command = [sys.executable, "run_mcp_server.py"]
    client = SimpleMCPClient(server_command)
    
    try:
        # Start server
        await client.start_server()
        
        # Initialize session
        print("Initializing MCP session...")
        init_response = await client.initialize()
        print(f"Server initialized: {init_response.get('result', {}).get('serverInfo', {})}")
        
        # Get server info
        print("\\nGetting server info...")
        info_response = await client.get_server_info()
        if info_response.get("result"):
            server_info = info_response["result"]
            print(f"Server: {server_info.get('name')} v{server_info.get('version')}")
            print(f"Total tools: {server_info.get('statistics', {}).get('total_tools', 0)}")
        
        # List available tools
        print("\\nListing available tools...")
        tools_response = await client.list_tools()
        if tools_response.get("result"):
            tools = tools_response["result"]["tools"]
            print(f"Found {len(tools)} tools:")
            for tool in tools[:5]:  # Show first 5 tools
                print(f"  - {tool['name']}: {tool['description']}")
            if len(tools) > 5:
                print(f"  ... and {len(tools) - 5} more tools")
        
        # Create a database connection
        print("\\nCreating database connection...")
        conn_response = await client.call_tool("db_create_connection", {
            "connection_id": "example_db",
            "config": db_config
        })
        
        print("Connection result:", conn_response.get("result", {}).get("content", [{}])[0].get("text", "No result"))
        
        # List connections
        print("\\nListing connections...")
        list_conn_response = await client.call_tool("db_list_connections", {})
        print("Connections:", list_conn_response.get("result", {}).get("content", [{}])[0].get("text", "No connections"))
        
        # Example: Get all tables (this will fail if the connection above failed)
        print("\\nGetting all tables...")
        tables_response = await client.call_tool("db_get_all_tables", {
            "connection_id": "example_db"
        })
        
        tables_content = tables_response.get("result", {}).get("content", [{}])[0].get("text", "{}")
        try:
            tables_data = json.loads(tables_content)
            if tables_data.get("tables"):
                print(f"Found {len(tables_data['tables'])} tables")
            else:
                print("No tables found or connection failed")
        except:
            print("Error parsing tables response:", tables_content)
        
        # Close connection
        print("\\nClosing connection...")
        close_response = await client.call_tool("db_close_connection", {
            "connection_id": "example_db"
        })
        print("Close result:", close_response.get("result", {}).get("content", [{}])[0].get("text", "No result"))
        
    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        # Stop server
        await client.stop_server()


if __name__ == "__main__":
    asyncio.run(main())