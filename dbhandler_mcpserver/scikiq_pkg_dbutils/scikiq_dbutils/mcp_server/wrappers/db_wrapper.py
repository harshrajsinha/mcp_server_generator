"""
Database Wrapper Class

Wraps clsDBConnection methods as MCP tools without affecting existing functionality.
"""

import json
import pandas as pd
from typing import Any, Dict, List, Optional, Union
from datetime import datetime

from scikiq_dbutils.handlers.DBConnection import clsDBConnection
from scikiq_dbutils.mcp_server.protocol.messages import MCPToolResult, create_tool_execution_error
from .connection_manager import ConnectionManager


class DatabaseWrapper:
    """
    Wrapper class that exposes database operations as MCP tools
    """
    
    def __init__(self, connection_manager: ConnectionManager):
        self.connection_manager = connection_manager
    
    def _serialize_dataframe(self, df) -> Dict[str, Any]:
        """Convert DataFrame to JSON-serializable format"""
        if df is None or df.empty:
            return {
                "columns": [],
                "data": [],
                "shape": [0, 0]
            }
        
        # Handle different DataFrame types (pandas/polars)
        if hasattr(df, 'to_dict'):  # pandas DataFrame
            return {
                "columns": list(df.columns),
                "data": df.to_dict('records'),
                "shape": list(df.shape),
                "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()}
            }
        elif hasattr(df, 'to_pandas'):  # polars DataFrame
            pdf = df.to_pandas()
            return {
                "columns": list(pdf.columns),
                "data": pdf.to_dict('records'),
                "shape": list(pdf.shape),
                "dtypes": {col: str(dtype) for col, dtype in pdf.dtypes.items()}
            }
        else:
            # Fallback for other types
            return {"data": str(df), "type": type(df).__name__}
    
    def _handle_tool_execution(self, connection_id: str, operation_name: str, operation_func) -> MCPToolResult:
        """
        Common handler for tool execution with error handling
        
        Args:
            connection_id: Database connection identifier
            operation_name: Name of the operation for error reporting
            operation_func: Function to execute
            
        Returns:
            MCPToolResult with success or error
        """
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            logger.info(f"_handle_tool_execution called: operation={operation_name}, connection_id={connection_id}")
            
            logger.info(f"Calling ensure_connection for '{connection_id}'...")
            connection = self.connection_manager.ensure_connection(connection_id)
            
            if not connection:
                logger.error(f"Connection '{connection_id}' not found or failed to connect")
                return MCPToolResult.error(f"Connection '{connection_id}' not found or failed to connect")
            
            logger.info(f"Connection obtained, executing operation '{operation_name}'...")
            result = operation_func(connection)
            logger.info(f"Operation '{operation_name}' completed successfully")
            return MCPToolResult.success(result)
            
        except Exception as e:
            logger.error(f"Error in {operation_name}: {str(e)}", exc_info=True)
            error_msg = f"Error in {operation_name}: {str(e)}"
            return MCPToolResult.error(error_msg)
    
    def _normalize_config_for_dbfactory(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize configuration for DBFactory compatibility
        
        Handles password encoding and ensures proper format for both user-provided
        and environment-loaded configurations.
        """
        import base64
        
        config = config.copy()  # Don't modify original
        
        # Check if password_encrypted flag is set
        if 'password_encrypted' not in config:
            # For user-provided configs (like from Claude Desktop), assume unencrypted
            config['password_encrypted'] = 0
        
        # Handle password encoding
        if 'dbpassword' in config and config.get('password_encrypted', 0) == 0:
            # Password is plain text, encode it for DBFactory
            try:
                encoded_password = base64.b64encode(bytes(config['dbpassword'], "utf-8")).decode('utf-8')
                config['dbpassword'] = encoded_password
                config['password_encrypted'] = 1  # Mark as encoded
            except Exception:
                # If encoding fails, keep original password and let DBFactory handle it
                pass
        
        return config
    
    # Connection Management Tools
    
    def create_connection(self, connection_id: str, config: Dict[str, Any]) -> MCPToolResult:
        """Create a new database connection"""
        try:
            # Ensure password encryption flag is set for user-provided configs
            config = self._normalize_config_for_dbfactory(config)
            connection = self.connection_manager.create_connection(connection_id, config)
            return MCPToolResult.success({
                "connection_id": connection_id,
                "db_type": getattr(connection, 'db_type', 'Unknown'),
                "status": "connected"
            })
        except Exception as e:
            return MCPToolResult.error(f"Failed to create connection: {str(e)}")
    
    def test_connection(self, config: Dict[str, Any]) -> MCPToolResult:
        """Test database connection without creating persistent connection"""
        try:
            # Ensure password encryption flag is set for user-provided configs
            config = self._normalize_config_for_dbfactory(config)
            result = self.connection_manager.test_connection(config)
            return MCPToolResult.success(result)
        except Exception as e:
            return MCPToolResult.error(f"Connection test failed: {str(e)}")
    
    def close_connection(self, connection_id: str) -> MCPToolResult:
        """Close and remove a database connection"""
        try:
            removed = self.connection_manager.remove_connection(connection_id)
            if removed:
                return MCPToolResult.success({"connection_id": connection_id, "status": "closed"})
            else:
                return MCPToolResult.error(f"Connection '{connection_id}' not found")
        except Exception as e:
            return MCPToolResult.error(f"Error closing connection: {str(e)}")
    
    def list_connections(self) -> MCPToolResult:
        """List all active database connections"""
        try:
            connections = self.connection_manager.list_connections()
            return MCPToolResult.success(connections)
        except Exception as e:
            return MCPToolResult.error(f"Error listing connections: {str(e)}")
    
    # Query Execution Tools
    
    def execute_query(self, connection_id: str, query: str, limit: Optional[int] = None, 
                     use_polars: bool = False, batch_size: int = 100000) -> MCPToolResult:
        """Execute a SELECT query and return results"""
        def operation(conn: clsDBConnection):
            df = conn.executeQuery(
                query=query,
                limit=limit,
                use_polars=use_polars,
                batch_size=batch_size
            )
            return self._serialize_dataframe(df)
        
        return self._handle_tool_execution(connection_id, "execute_query", operation)
    
    def execute_sql(self, connection_id: str, query: str) -> MCPToolResult:
        """Execute SQL statements (INSERT, UPDATE, DELETE, etc.)"""
        def operation(conn: clsDBConnection):
            result = conn.executeSql(query)
            return {"affected_rows": result if isinstance(result, int) else "Success"}
        
        return self._handle_tool_execution(connection_id, "execute_sql", operation)
    
    # Table Operations Tools
    
    def get_all_tables(self, connection_id: str, search: Optional[str] = None, 
                      table_type: Optional[str] = None, limit: Optional[int] = None) -> MCPToolResult:
        """Get list of all tables in the database"""
        def operation(conn: clsDBConnection):
            tables = conn.get_all_tables(search=search, type=table_type, limit=limit)
            return {"tables": tables}
        
        return self._handle_tool_execution(connection_id, "get_all_tables", operation)
    
    def get_table_columns(self, connection_id: str, table_name: str, table_type: str = '') -> MCPToolResult:
        """Get columns for a specific table"""
        def operation(conn: clsDBConnection):
            columns = conn.getTableColumns(table_name, type=table_type)
            return {"table_name": table_name, "columns": columns}
        
        return self._handle_tool_execution(connection_id, "get_table_columns", operation)
    
    def get_table_columns_details(self, connection_id: str, table_name: str, **others) -> MCPToolResult:
        """Get detailed column information for a table"""
        def operation(conn: clsDBConnection):
            details = conn.getTableColumnsDetails(table_name, **others)
            return {"table_name": table_name, "column_details": details}
        
        return self._handle_tool_execution(connection_id, "get_table_columns_details", operation)
    
    def read_table(self, connection_id: str, table_name: str, limit: Optional[int] = None, **others) -> MCPToolResult:
        """Read data from a table"""
        def operation(conn: clsDBConnection):
            df = conn.readTable(table_name, limit, **others)
            return self._serialize_dataframe(df)
        
        return self._handle_tool_execution(connection_id, "read_table", operation)
    
    def get_table_details(self, connection_id: str, table_name: str, detail_type: Dict = None) -> MCPToolResult:
        """Get detailed information about a table"""
        def operation(conn: clsDBConnection):
            details = conn.getTableDetails(table_name, type=detail_type or {})
            return {"table_name": table_name, "details": details}
        
        return self._handle_tool_execution(connection_id, "get_table_details", operation)
    
    def get_table_relationships(self, connection_id: str, table_name: str) -> MCPToolResult:
        """Get foreign key relationships for a table"""
        def operation(conn: clsDBConnection):
            relationships = conn.getTableRelationships(table_name)
            return {"table_name": table_name, "relationships": relationships}
        
        return self._handle_tool_execution(connection_id, "get_table_relationships", operation)
    
    # Column Operations Tools
    
    def get_column_lov(self, connection_id: str, table_name: str, column_name: str) -> MCPToolResult:
        """Get list of values (LOV) for a column"""
        def operation(conn: clsDBConnection):
            lov = conn.getColumnLOV(table_name, column_name)
            return {
                "table_name": table_name,
                "column_name": column_name,
                "values": lov
            }
        
        return self._handle_tool_execution(connection_id, "get_column_lov", operation)
    
    def get_columns_profile(self, connection_id: str, table_name: str, 
                           with_min_max: bool = False, filter_condition: str = None) -> MCPToolResult:
        """Get column profiling information"""
        def operation(conn: clsDBConnection):
            profile = conn.getColumnsProfile(table_name, with_min_max, filter_condition)
            return {
                "table_name": table_name,
                "profile": profile
            }
        
        return self._handle_tool_execution(connection_id, "get_columns_profile", operation)
    
    def update_column_comment(self, connection_id: str, table_name: str, 
                            column_name: str, comment: str, **others) -> MCPToolResult:
        """Update comment for a table column"""
        def operation(conn: clsDBConnection):
            result = conn.update_column_comment(table_name, column_name, comment, **others)
            return {
                "table_name": table_name,
                "column_name": column_name,
                "comment": comment,
                "success": True
            }
        
        return self._handle_tool_execution(connection_id, "update_column_comment", operation)
    
    # Query Builder Tools
    
    def generate_query(self, connection_id: str, table_name: str, 
                      column_names: Optional[List[str]] = None,
                      limit: Optional[int] = None,
                      order_by: Optional[List[Dict[str, str]]] = None,
                      filters: Optional[List[Dict[str, Any]]] = None,
                      group_by: Optional[List[str]] = None,
                      distinct: int = 0) -> MCPToolResult:
        """Generate SQL query based on parameters"""
        def operation(conn: clsDBConnection):
            query = conn.generateQuery(
                tablename=table_name,
                columnnames=column_names,
                limit=limit,
                orderby=order_by,
                filters=filters,
                groupby=group_by,
                distinct=distinct
            )
            return {
                "table_name": table_name,
                "generated_query": query
            }
        
        return self._handle_tool_execution(connection_id, "generate_query", operation)
    
    # Table Management Tools
    
    def create_table(self, connection_id: str, table_name: str, etl: bool = False) -> MCPToolResult:
        """Create a new table"""
        def operation(conn: clsDBConnection):
            result = conn.createTable(table_name, etl=etl)
            return {
                "table_name": table_name,
                "created": True,
                "result": result
            }
        
        return self._handle_tool_execution(connection_id, "create_table", operation)
    
    def truncate_table(self, connection_id: str, table_name: str) -> MCPToolResult:
        """Truncate a table (remove all data)"""
        def operation(conn: clsDBConnection):
            result = conn.truncateTable(table_name)
            return {
                "table_name": table_name,
                "truncated": True,
                "result": result
            }
        
        return self._handle_tool_execution(connection_id, "truncate_table", operation)
    
    def create_view(self, connection_id: str, view_name: str, sql_query: str) -> MCPToolResult:
        """Create a database view"""
        def operation(conn: clsDBConnection):
            result = conn.createView(view_name, sql_query)
            return {
                "view_name": view_name,
                "created": True,
                "result": result
            }
        
        return self._handle_tool_execution(connection_id, "create_view", operation)
    
    # Data Management Tools
    
    def get_incremental_columns(self, connection_id: str, table_name: str, **others) -> MCPToolResult:
        """Get columns suitable for incremental data loading"""
        def operation(conn: clsDBConnection):
            columns = conn.get_incremental_columns(table_name, **others)
            return {
                "table_name": table_name,
                "incremental_columns": columns
            }
        
        return self._handle_tool_execution(connection_id, "get_incremental_columns", operation)
    
    def fetch_delta_columns(self, connection_id: str, table_name: str, **others) -> MCPToolResult:
        """Fetch delta columns for change data capture"""
        def operation(conn: clsDBConnection):
            columns = conn.fetch_delta_columns(table_name, **others)
            return {
                "table_name": table_name,
                "delta_columns": columns
            }
        
        return self._handle_tool_execution(connection_id, "fetch_delta_columns", operation)
    
    def get_filtered_row_count(self, connection_id: str, table_name: str, 
                              filter_condition: str = "1=1") -> MCPToolResult:
        """Get count of rows matching filter condition"""
        def operation(conn: clsDBConnection):
            count = conn.get_filtered_row_count(table_name, filter_condition)
            return {
                "table_name": table_name,
                "filter_condition": filter_condition,
                "row_count": count
            }
        
        return self._handle_tool_execution(connection_id, "get_filtered_row_count", operation)