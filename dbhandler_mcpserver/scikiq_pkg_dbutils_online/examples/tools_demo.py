"""
Example: MCP Tool Usage Demonstrations

This module contains examples showing how to use various MCP tools
provided by the ScikiQ Database MCP Server.
"""

import json
import asyncio
from simple_mcp_client import SimpleMCPClient
import sys


class DatabaseToolsDemo:
    """
    Demonstrates various database tools available in the MCP server
    """
    
    def __init__(self, client: SimpleMCPClient):
        self.client = client
        self.connection_id = "demo_db"
    
    async def setup_connection(self):
        """Setup a demo database connection"""
        print("=== Setting up database connection ===")
        
        # Example configuration - update with your database details
        config = {
            "dbType": "MYSQL",  # Change as needed
            "hostname": "localhost",
            "port": 3306,
            "dbname": "testdb",
            "dbuser": "testuser",
            "dbpassword": "testpass"
        }
        
        # Test connection first
        print("Testing connection...")
        test_response = await self.client.call_tool("db_test_connection", {"config": config})
        print(f"Connection test: {self._parse_result(test_response)}")
        
        # Create connection
        print("Creating connection...")
        create_response = await self.client.call_tool("db_create_connection", {
            "connection_id": self.connection_id,
            "config": config
        })
        print(f"Connection created: {self._parse_result(create_response)}")
        
        return create_response
    
    async def demo_connection_management(self):
        """Demo connection management tools"""
        print("\\n=== Connection Management Tools Demo ===")
        
        # List connections
        print("Listing connections...")
        response = await self.client.call_tool("db_list_connections", {})
        connections = self._parse_result(response)
        print(f"Active connections: {connections}")
    
    async def demo_table_operations(self):
        """Demo table operation tools"""
        print("\\n=== Table Operations Demo ===")
        
        try:
            # Get all tables
            print("Getting all tables...")
            response = await self.client.call_tool("db_get_all_tables", {
                "connection_id": self.connection_id,
                "limit": 10
            })
            tables_data = self._parse_result(response)
            
            if isinstance(tables_data, dict) and 'tables' in tables_data:
                tables = tables_data['tables']
                print(f"Found {len(tables)} tables:")
                for table in tables[:5]:  # Show first 5
                    print(f"  - {table}")
                
                # If we have tables, demonstrate column operations
                if tables:
                    await self.demo_column_operations(tables[0])
            else:
                print("No tables found or error occurred")
                
        except Exception as e:
            print(f"Error in table operations: {e}")
    
    async def demo_column_operations(self, table_name):
        """Demo column operation tools"""
        print(f"\\n=== Column Operations Demo (Table: {table_name}) ===")
        
        try:
            # Get table columns
            print("Getting table columns...")
            response = await self.client.call_tool("db_get_table_columns", {
                "connection_id": self.connection_id,
                "table_name": table_name
            })
            columns_data = self._parse_result(response)
            print(f"Columns: {columns_data}")
            
            # Get detailed column information
            print("Getting detailed column information...")
            response = await self.client.call_tool("db_get_table_columns_details", {
                "connection_id": self.connection_id,
                "table_name": table_name
            })
            details = self._parse_result(response)
            print(f"Column details: {json.dumps(details, indent=2) if isinstance(details, dict) else details}")
            
        except Exception as e:
            print(f"Error in column operations: {e}")
    
    async def demo_query_operations(self):
        """Demo query execution tools"""
        print("\\n=== Query Operations Demo ===")
        
        try:
            # Execute a simple query
            print("Executing simple query...")
            response = await self.client.call_tool("db_execute_query", {
                "connection_id": self.connection_id,
                "query": "SELECT 1 as test_column, 'Hello MCP' as message",
                "limit": 5
            })
            result = self._parse_result(response)
            print(f"Query result: {json.dumps(result, indent=2) if isinstance(result, dict) else result}")
            
            # Execute SQL (this would be for INSERT/UPDATE/DELETE)
            print("\\nNote: db_execute_sql would be used for INSERT/UPDATE/DELETE operations")
            
        except Exception as e:
            print(f"Error in query operations: {e}")
    
    async def demo_query_builder(self):
        """Demo query builder tool"""
        print("\\n=== Query Builder Demo ===")
        
        try:
            # Generate a query
            print("Generating SQL query...")
            response = await self.client.call_tool("db_generate_query", {
                "connection_id": self.connection_id,
                "table_name": "users",  # Example table name
                "column_names": ["id", "name", "email"],
                "limit": 10,
                "filters": [
                    {
                        "field": "status",
                        "operator": "equal",
                        "value": "active"
                    }
                ],
                "order_by": [
                    {
                        "column": "name",
                        "direction": "ASC"
                    }
                ]
            })
            result = self._parse_result(response)
            print(f"Generated query: {result}")
            
        except Exception as e:
            print(f"Error in query builder: {e}")
    
    async def demo_data_management(self):
        """Demo data management tools"""
        print("\\n=== Data Management Demo ===")
        
        try:
            # Get row count with filter
            print("Getting filtered row count...")
            response = await self.client.call_tool("db_get_filtered_row_count", {
                "connection_id": self.connection_id,
                "table_name": "users",  # Example table
                "filter_condition": "status = 'active'"
            })
            result = self._parse_result(response)
            print(f"Row count: {result}")
            
        except Exception as e:
            print(f"Error in data management operations: {e}")
    
    async def cleanup_connection(self):
        """Cleanup demo connection"""
        print("\\n=== Cleanup ===")
        
        try:
            print("Closing connection...")
            response = await self.client.call_tool("db_close_connection", {
                "connection_id": self.connection_id
            })
            result = self._parse_result(response)
            print(f"Connection closed: {result}")
            
        except Exception as e:
            print(f"Error during cleanup: {e}")
    
    def _parse_result(self, response):
        """Parse MCP tool response"""
        if "error" in response:
            return f"Error: {response['error']}"
        
        result = response.get("result", {})
        content = result.get("content", [])
        
        if content and len(content) > 0:
            text = content[0].get("text", "")
            try:
                return json.loads(text)
            except:
                return text
        
        return result


async def main():
    """Run the database tools demonstration"""
    print("ScikiQ Database MCP Server - Tools Demonstration")
    print("=" * 50)
    
    # Create client
    server_command = [sys.executable, "run_mcp_server.py"]
    client = SimpleMCPClient(server_command)
    
    try:
        # Start server and initialize
        await client.start_server()
        await client.initialize()
        
        # Create demo instance
        demo = DatabaseToolsDemo(client)
        
        # Run demonstrations
        connection_result = await demo.setup_connection()
        
        # Only proceed with other demos if connection was successful
        if not connection_result.get("error"):
            await demo.demo_connection_management()
            await demo.demo_table_operations()
            await demo.demo_query_operations() 
            await demo.demo_query_builder()
            await demo.demo_data_management()
        else:
            print("\\nSkipping other demonstrations due to connection failure.")
            print("Please update the database configuration in setup_connection() method.")
        
        # Cleanup
        await demo.cleanup_connection()
        
    except Exception as e:
        print(f"Demo error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Stop server
        await client.stop_server()


if __name__ == "__main__":
    print("Starting MCP Database Tools Demo...")
    print("\\nNote: Make sure to update the database configuration in the setup_connection() method")
    print("with your actual database details before running this demo.\\n")
    
    asyncio.run(main())