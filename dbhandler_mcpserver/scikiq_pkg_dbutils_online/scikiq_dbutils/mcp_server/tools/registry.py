"""
MCP Tool Registry

Manages registration and execution of MCP tools for database operations.
"""

from typing import Dict, Any, Callable, List, Optional
import inspect
import json
from functools import wraps

from scikiq_dbutils.mcp_server.protocol.schemas import ToolSchema
from scikiq_dbutils.mcp_server.protocol.messages import (
    MCPToolCall, MCPToolResult, create_tool_not_found_error, 
    create_tool_execution_error, create_invalid_params_error
)
from scikiq_dbutils.mcp_server.wrappers.db_wrapper import DatabaseWrapper
from .definitions import DatabaseToolDefinitions


class ToolRegistry:
    """
    Registry for MCP tools that handles tool registration, validation, and execution
    """
    
    def __init__(self, db_wrapper: DatabaseWrapper):
        self.db_wrapper = db_wrapper
        self._tools: Dict[str, ToolSchema] = {}
        self._handlers: Dict[str, Callable] = {}
        self._initialize_tools()
    
    def _initialize_tools(self):
        """Initialize all database tools"""
        # Get all tool definitions
        tool_definitions = DatabaseToolDefinitions.get_all_tools()
        
        # Register each tool with its handler
        for tool_name, tool_schema in tool_definitions.items():
            self.register_tool(tool_name, tool_schema, self._get_handler_for_tool(tool_name))
    
    def _get_handler_for_tool(self, tool_name: str) -> Callable:
        """Map tool names to their corresponding handler methods"""
        tool_handlers = {
            # Connection Management
            "db_create_connection": self.db_wrapper.create_connection,
            "db_test_connection": self.db_wrapper.test_connection,
            "db_close_connection": self.db_wrapper.close_connection,
            "db_list_connections": self.db_wrapper.list_connections,
            
            # Query Execution
            "db_execute_query": self.db_wrapper.execute_query,
            "db_execute_sql": self.db_wrapper.execute_sql,
            
            # Table Operations
            "db_get_all_tables": self.db_wrapper.get_all_tables,
            "db_get_table_columns": self.db_wrapper.get_table_columns,
            "db_get_table_columns_details": self.db_wrapper.get_table_columns_details,
            "db_read_table": self.db_wrapper.read_table,
            "db_get_table_details": self.db_wrapper.get_table_details,
            "db_get_table_relationships": self.db_wrapper.get_table_relationships,
            
            # Column Operations
            "db_get_column_lov": self.db_wrapper.get_column_lov,
            "db_get_columns_profile": self.db_wrapper.get_columns_profile,
            "db_update_column_comment": self.db_wrapper.update_column_comment,
            
            # Query Builder
            "db_generate_query": self.db_wrapper.generate_query,
            
            # Table Management
            "db_create_table": self.db_wrapper.create_table,
            "db_truncate_table": self.db_wrapper.truncate_table,
            "db_create_view": self.db_wrapper.create_view,
            
            # Data Management
            "db_get_incremental_columns": self.db_wrapper.get_incremental_columns,
            "db_fetch_delta_columns": self.db_wrapper.fetch_delta_columns,
            "db_get_filtered_row_count": self.db_wrapper.get_filtered_row_count,
        }
        
        if tool_name not in tool_handlers:
            raise ValueError(f"No handler found for tool: {tool_name}")
        
        return tool_handlers[tool_name]
    
    def register_tool(self, name: str, schema: ToolSchema, handler: Callable):
        """
        Register a new tool with its schema and handler
        
        Args:
            name: Tool name (must match schema.name)
            schema: Tool schema definition
            handler: Function to handle tool execution
        """
        if name != schema.name:
            raise ValueError(f"Tool name '{name}' does not match schema name '{schema.name}'")
        
        self._tools[name] = schema
        self._handlers[name] = handler
    
    def get_tool_schema(self, name: str) -> Optional[ToolSchema]:
        """Get schema for a specific tool"""
        return self._tools.get(name)
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """Get list of all registered tools with their schemas"""
        return [tool.to_dict() for tool in self._tools.values()]
    
    def get_tools_list(self) -> Dict[str, ToolSchema]:
        """Get dictionary of all registered tools"""
        return self._tools.copy()
    
    def validate_tool_call(self, tool_call: MCPToolCall) -> Optional[str]:
        """
        Validate a tool call against its schema
        
        Args:
            tool_call: The tool call to validate
            
        Returns:
            None if valid, error message if invalid
        """
        if tool_call.name not in self._tools:
            return f"Tool '{tool_call.name}' not found"
        
        tool_schema = self._tools[tool_call.name]
        return self._validate_parameters(tool_call.arguments, tool_schema.input_schema)
    
    def _validate_parameters(self, arguments: Dict[str, Any], schema: Dict[str, Any]) -> Optional[str]:
        """
        Validate parameters against JSON schema
        
        Args:
            arguments: Tool arguments to validate
            schema: JSON schema for validation
            
        Returns:
            None if valid, error message if invalid
        """
        try:
            # Check required parameters
            required_params = schema.get("required", [])
            for param in required_params:
                if param not in arguments:
                    return f"Missing required parameter: {param}"
            
            # Basic type checking for known parameters
            properties = schema.get("properties", {})
            for param_name, param_value in arguments.items():
                if param_name in properties:
                    param_schema = properties[param_name]
                    error = self._validate_parameter_value(param_name, param_value, param_schema)
                    if error:
                        return error
            
            return None
            
        except Exception as e:
            return f"Parameter validation error: {str(e)}"
    
    def _validate_parameter_value(self, param_name: str, value: Any, param_schema: Dict[str, Any]) -> Optional[str]:
        """
        Validate a single parameter value against its schema
        
        Args:
            param_name: Parameter name
            value: Parameter value
            param_schema: Parameter schema
            
        Returns:
            None if valid, error message if invalid
        """
        param_type = param_schema.get("type")
        
        if param_type == "string" and not isinstance(value, str):
            return f"Parameter '{param_name}' must be a string"
        elif param_type == "integer" and not isinstance(value, int):
            return f"Parameter '{param_name}' must be an integer"
        elif param_type == "number" and not isinstance(value, (int, float)):
            return f"Parameter '{param_name}' must be a number"
        elif param_type == "boolean" and not isinstance(value, bool):
            return f"Parameter '{param_name}' must be a boolean"
        elif param_type == "array" and not isinstance(value, list):
            return f"Parameter '{param_name}' must be an array"
        elif param_type == "object" and not isinstance(value, dict):
            return f"Parameter '{param_name}' must be an object"
        
        # Check enum values
        if "enum" in param_schema and value not in param_schema["enum"]:
            return f"Parameter '{param_name}' must be one of: {param_schema['enum']}"
        
        # Check string constraints
        if param_type == "string":
            if "minLength" in param_schema and len(value) < param_schema["minLength"]:
                return f"Parameter '{param_name}' must be at least {param_schema['minLength']} characters"
            if "maxLength" in param_schema and len(value) > param_schema["maxLength"]:
                return f"Parameter '{param_name}' must be at most {param_schema['maxLength']} characters"
        
        # Check numeric constraints
        if param_type in ["integer", "number"]:
            if "minimum" in param_schema and value < param_schema["minimum"]:
                return f"Parameter '{param_name}' must be at least {param_schema['minimum']}"
            if "maximum" in param_schema and value > param_schema["maximum"]:
                return f"Parameter '{param_name}' must be at most {param_schema['maximum']}"
        
        return None
    
    def execute_tool(self, tool_call: MCPToolCall) -> MCPToolResult:
        """
        Execute a tool call
        
        Args:
            tool_call: The tool call to execute
            
        Returns:
            MCPToolResult with the execution result
        """
        try:
            # Validate tool exists
            if tool_call.name not in self._tools:
                return MCPToolResult.error({
                    "error": "tool_not_found",
                    "message": f"Tool '{tool_call.name}' not found",
                    "available_tools": list(self._tools.keys())
                })
            
            # Validate parameters
            validation_error = self.validate_tool_call(tool_call)
            if validation_error:
                return MCPToolResult.error({
                    "error": "invalid_parameters",
                    "message": validation_error,
                    "tool_schema": self._tools[tool_call.name].to_dict()
                })
            
            # Get handler and execute
            handler = self._handlers[tool_call.name]
            
            # Extract arguments and call handler
            try:
                # Check if handler accepts keyword arguments
                sig = inspect.signature(handler)
                if any(param.kind == param.VAR_KEYWORD for param in sig.parameters.values()):
                    # Handler accepts **kwargs, pass all arguments
                    result = handler(**tool_call.arguments)
                else:
                    # Handler has specific parameters, filter arguments
                    handler_params = set(sig.parameters.keys())
                    filtered_args = {k: v for k, v in tool_call.arguments.items() if k in handler_params}
                    result = handler(**filtered_args)
                
                return result
                
            except TypeError as e:
                if "unexpected keyword argument" in str(e) or "missing" in str(e):
                    return MCPToolResult.error({
                        "error": "parameter_mismatch",
                        "message": f"Parameter mismatch for tool '{tool_call.name}': {str(e)}",
                        "expected_parameters": list(sig.parameters.keys()),
                        "provided_parameters": list(tool_call.arguments.keys())
                    })
                else:
                    raise
            
        except Exception as e:
            return MCPToolResult.error({
                "error": "execution_error",
                "message": f"Error executing tool '{tool_call.name}': {str(e)}",
                "exception_type": type(e).__name__
            })
    
    def get_tool_info(self, tool_name: str) -> Dict[str, Any]:
        """
        Get comprehensive information about a specific tool
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            Dictionary with tool information or error
        """
        if tool_name not in self._tools:
            return {
                "error": "tool_not_found",
                "message": f"Tool '{tool_name}' not found",
                "available_tools": list(self._tools.keys())
            }
        
        tool_schema = self._tools[tool_name]
        handler = self._handlers[tool_name]
        
        return {
            "name": tool_schema.name,
            "description": tool_schema.description,
            "schema": tool_schema.to_dict(),
            "handler": handler.__name__,
            "module": handler.__module__,
        }
    
    def get_tools_by_category(self) -> Dict[str, List[str]]:
        """
        Group tools by category based on their name prefixes
        
        Returns:
            Dictionary mapping categories to tool names
        """
        categories = {}
        
        for tool_name in self._tools.keys():
            if tool_name.startswith("db_"):
                category = tool_name.split("_", 2)[1] if "_" in tool_name else "general"
                if category not in categories:
                    categories[category] = []
                categories[category].append(tool_name)
        
        return categories