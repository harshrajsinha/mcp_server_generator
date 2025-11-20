"""
Database Tool Definitions

Defines all available database tools with their schemas and metadata.
"""

from scikiq_dbutils.mcp_server.protocol.schemas import (
    ToolSchema, ParameterSchema, ParameterType,
    DB_CONNECTION_PARAMS, QUERY_PARAMS, TABLE_PARAMS, COLUMN_PARAMS, FILTER_PARAMS
)


class DatabaseToolDefinitions:
    """Container for all database tool definitions"""
    
    @staticmethod
    def get_all_tools() -> dict:
        """Get all available database tools with their schemas"""
        return {
            # Connection Management Tools
            "db_create_connection": DatabaseToolDefinitions._create_connection_tool(),
            "db_test_connection": DatabaseToolDefinitions._test_connection_tool(),
            "db_close_connection": DatabaseToolDefinitions._close_connection_tool(),
            "db_list_connections": DatabaseToolDefinitions._list_connections_tool(),
            
            # Query Execution Tools
            "db_execute_query": DatabaseToolDefinitions._execute_query_tool(),
            "db_execute_sql": DatabaseToolDefinitions._execute_sql_tool(),
            
            # Table Operations Tools
            "db_get_all_tables": DatabaseToolDefinitions._get_all_tables_tool(),
            "db_get_table_columns": DatabaseToolDefinitions._get_table_columns_tool(),
            "db_get_table_columns_details": DatabaseToolDefinitions._get_table_columns_details_tool(),
            "db_read_table": DatabaseToolDefinitions._read_table_tool(),
            "db_get_table_details": DatabaseToolDefinitions._get_table_details_tool(),
            "db_get_table_relationships": DatabaseToolDefinitions._get_table_relationships_tool(),
            
            # Column Operations Tools
            "db_get_column_lov": DatabaseToolDefinitions._get_column_lov_tool(),
            "db_get_columns_profile": DatabaseToolDefinitions._get_columns_profile_tool(),
            "db_update_column_comment": DatabaseToolDefinitions._update_column_comment_tool(),
            
            # Query Builder Tools
            "db_generate_query": DatabaseToolDefinitions._generate_query_tool(),
            
            # Table Management Tools
            "db_create_table": DatabaseToolDefinitions._create_table_tool(),
            "db_truncate_table": DatabaseToolDefinitions._truncate_table_tool(),
            "db_create_view": DatabaseToolDefinitions._create_view_tool(),
            
            # Data Management Tools
            "db_get_incremental_columns": DatabaseToolDefinitions._get_incremental_columns_tool(),
            "db_fetch_delta_columns": DatabaseToolDefinitions._fetch_delta_columns_tool(),
            "db_get_filtered_row_count": DatabaseToolDefinitions._get_filtered_row_count_tool(),
        }
    
    # Connection Management Tool Definitions
    
    @staticmethod
    def _create_connection_tool() -> ToolSchema:
        tool = ToolSchema(
            name="db_create_connection",
            description="Create a new database connection with the specified configuration"
        )
        tool.add_parameter("connection_id", DB_CONNECTION_PARAMS["connection_id"], required=True)
        tool.add_parameter("config", DB_CONNECTION_PARAMS["config"], required=True)
        return tool
    
    @staticmethod
    def _test_connection_tool() -> ToolSchema:
        tool = ToolSchema(
            name="db_test_connection",
            description="Test database connection without creating a persistent connection"
        )
        tool.add_parameter("config", DB_CONNECTION_PARAMS["config"], required=True)
        return tool
    
    @staticmethod
    def _close_connection_tool() -> ToolSchema:
        tool = ToolSchema(
            name="db_close_connection",
            description="Close and remove an existing database connection"
        )
        tool.add_parameter("connection_id", DB_CONNECTION_PARAMS["connection_id"], required=True)
        return tool
    
    @staticmethod
    def _list_connections_tool() -> ToolSchema:
        return ToolSchema(
            name="db_list_connections",
            description="List all active database connections"
        )
    
    # Query Execution Tool Definitions
    
    @staticmethod
    def _execute_query_tool() -> ToolSchema:
        tool = ToolSchema(
            name="db_execute_query",
            description="Execute a SELECT query and return the results as structured data"
        )
        tool.add_parameter("connection_id", DB_CONNECTION_PARAMS["connection_id"], required=True)
        tool.add_parameter("query", QUERY_PARAMS["query"], required=True)
        tool.add_parameter("limit", QUERY_PARAMS["limit"])
        tool.add_parameter("use_polars", QUERY_PARAMS["use_polars"])
        tool.add_parameter("batch_size", QUERY_PARAMS["batch_size"])
        return tool
    
    @staticmethod
    def _execute_sql_tool() -> ToolSchema:
        tool = ToolSchema(
            name="db_execute_sql",
            description="Execute SQL statements (INSERT, UPDATE, DELETE, DDL, etc.)"
        )
        tool.add_parameter("connection_id", DB_CONNECTION_PARAMS["connection_id"], required=True)
        tool.add_parameter("query", QUERY_PARAMS["query"], required=True)
        return tool
    
    # Table Operations Tool Definitions
    
    @staticmethod
    def _get_all_tables_tool() -> ToolSchema:
        tool = ToolSchema(
            name="db_get_all_tables",
            description="Get a list of all tables in the database"
        )
        tool.add_parameter("connection_id", DB_CONNECTION_PARAMS["connection_id"], required=True)
        tool.add_parameter("search", TABLE_PARAMS["search"])
        tool.add_parameter("table_type", TABLE_PARAMS["table_type"])
        tool.add_parameter("limit", QUERY_PARAMS["limit"])
        return tool
    
    @staticmethod
    def _get_table_columns_tool() -> ToolSchema:
        tool = ToolSchema(
            name="db_get_table_columns",
            description="Get column names and basic information for a specific table"
        )
        tool.add_parameter("connection_id", DB_CONNECTION_PARAMS["connection_id"], required=True)
        tool.add_parameter("table_name", TABLE_PARAMS["table_name"], required=True)
        tool.add_parameter("table_type", ParameterSchema(
            type=ParameterType.STRING,
            description="Table type filter (optional)"
        ))
        return tool
    
    @staticmethod
    def _get_table_columns_details_tool() -> ToolSchema:
        tool = ToolSchema(
            name="db_get_table_columns_details",
            description="Get detailed column information including data types, constraints, etc."
        )
        tool.add_parameter("connection_id", DB_CONNECTION_PARAMS["connection_id"], required=True)
        tool.add_parameter("table_name", TABLE_PARAMS["table_name"], required=True)
        return tool
    
    @staticmethod
    def _read_table_tool() -> ToolSchema:
        tool = ToolSchema(
            name="db_read_table",
            description="Read data from a table and return as structured data"
        )
        tool.add_parameter("connection_id", DB_CONNECTION_PARAMS["connection_id"], required=True)
        tool.add_parameter("table_name", TABLE_PARAMS["table_name"], required=True)
        tool.add_parameter("limit", QUERY_PARAMS["limit"])
        return tool
    
    @staticmethod
    def _get_table_details_tool() -> ToolSchema:
        tool = ToolSchema(
            name="db_get_table_details",
            description="Get comprehensive details about a table including metadata"
        )
        tool.add_parameter("connection_id", DB_CONNECTION_PARAMS["connection_id"], required=True)
        tool.add_parameter("table_name", TABLE_PARAMS["table_name"], required=True)
        tool.add_parameter("detail_type", ParameterSchema(
            type=ParameterType.OBJECT,
            description="Type of details to retrieve (optional)"
        ))
        return tool
    
    @staticmethod
    def _get_table_relationships_tool() -> ToolSchema:
        tool = ToolSchema(
            name="db_get_table_relationships",
            description="Get foreign key relationships for a table"
        )
        tool.add_parameter("connection_id", DB_CONNECTION_PARAMS["connection_id"], required=True)
        tool.add_parameter("table_name", TABLE_PARAMS["table_name"], required=True)
        return tool
    
    # Column Operations Tool Definitions
    
    @staticmethod
    def _get_column_lov_tool() -> ToolSchema:
        tool = ToolSchema(
            name="db_get_column_lov",
            description="Get list of unique values (LOV) for a specific column"
        )
        tool.add_parameter("connection_id", DB_CONNECTION_PARAMS["connection_id"], required=True)
        tool.add_parameter("table_name", TABLE_PARAMS["table_name"], required=True)
        tool.add_parameter("column_name", COLUMN_PARAMS["column_name"], required=True)
        return tool
    
    @staticmethod
    def _get_columns_profile_tool() -> ToolSchema:
        tool = ToolSchema(
            name="db_get_columns_profile",
            description="Get statistical profiling information for table columns"
        )
        tool.add_parameter("connection_id", DB_CONNECTION_PARAMS["connection_id"], required=True)
        tool.add_parameter("table_name", TABLE_PARAMS["table_name"], required=True)
        tool.add_parameter("with_min_max", ParameterSchema(
            type=ParameterType.BOOLEAN,
            description="Include minimum and maximum values in profile",
            default=False
        ))
        tool.add_parameter("filter_condition", ParameterSchema(
            type=ParameterType.STRING,
            description="Optional filter condition for profiling"
        ))
        return tool
    
    @staticmethod
    def _update_column_comment_tool() -> ToolSchema:
        tool = ToolSchema(
            name="db_update_column_comment",
            description="Update the comment/description for a table column"
        )
        tool.add_parameter("connection_id", DB_CONNECTION_PARAMS["connection_id"], required=True)
        tool.add_parameter("table_name", TABLE_PARAMS["table_name"], required=True)
        tool.add_parameter("column_name", COLUMN_PARAMS["column_name"], required=True)
        tool.add_parameter("comment", ParameterSchema(
            type=ParameterType.STRING,
            description="Comment text to add to the column"
        ), required=True)
        return tool
    
    # Query Builder Tool Definitions
    
    @staticmethod
    def _generate_query_tool() -> ToolSchema:
        tool = ToolSchema(
            name="db_generate_query",
            description="Generate SQL query based on specified parameters"
        )
        tool.add_parameter("connection_id", DB_CONNECTION_PARAMS["connection_id"], required=True)
        tool.add_parameter("table_name", TABLE_PARAMS["table_name"], required=True)
        tool.add_parameter("column_names", COLUMN_PARAMS["column_names"])
        tool.add_parameter("limit", QUERY_PARAMS["limit"])
        tool.add_parameter("order_by", FILTER_PARAMS["order_by"])
        tool.add_parameter("filters", FILTER_PARAMS["filters"])
        tool.add_parameter("group_by", FILTER_PARAMS["group_by"])
        tool.add_parameter("distinct", ParameterSchema(
            type=ParameterType.INTEGER,
            description="Use DISTINCT in query (1 for true, 0 for false)",
            default=0,
            minimum=0,
            maximum=1
        ))
        return tool
    
    # Table Management Tool Definitions
    
    @staticmethod
    def _create_table_tool() -> ToolSchema:
        tool = ToolSchema(
            name="db_create_table",
            description="Create a new table in the database"
        )
        tool.add_parameter("connection_id", DB_CONNECTION_PARAMS["connection_id"], required=True)
        tool.add_parameter("table_name", TABLE_PARAMS["table_name"], required=True)
        tool.add_parameter("etl", ParameterSchema(
            type=ParameterType.BOOLEAN,
            description="Create table for ETL operations",
            default=False
        ))
        return tool
    
    @staticmethod
    def _truncate_table_tool() -> ToolSchema:
        tool = ToolSchema(
            name="db_truncate_table",
            description="Remove all data from a table (TRUNCATE)"
        )
        tool.add_parameter("connection_id", DB_CONNECTION_PARAMS["connection_id"], required=True)
        tool.add_parameter("table_name", TABLE_PARAMS["table_name"], required=True)
        return tool
    
    @staticmethod
    def _create_view_tool() -> ToolSchema:
        tool = ToolSchema(
            name="db_create_view",
            description="Create a database view from SQL query"
        )
        tool.add_parameter("connection_id", DB_CONNECTION_PARAMS["connection_id"], required=True)
        tool.add_parameter("view_name", ParameterSchema(
            type=ParameterType.STRING,
            description="Name for the new view"
        ), required=True)
        tool.add_parameter("sql_query", QUERY_PARAMS["query"], required=True)
        return tool
    
    # Data Management Tool Definitions
    
    @staticmethod
    def _get_incremental_columns_tool() -> ToolSchema:
        tool = ToolSchema(
            name="db_get_incremental_columns",
            description="Get columns suitable for incremental data loading (timestamps, IDs, etc.)"
        )
        tool.add_parameter("connection_id", DB_CONNECTION_PARAMS["connection_id"], required=True)
        tool.add_parameter("table_name", TABLE_PARAMS["table_name"], required=True)
        return tool
    
    @staticmethod
    def _fetch_delta_columns_tool() -> ToolSchema:
        tool = ToolSchema(
            name="db_fetch_delta_columns",
            description="Fetch delta columns for change data capture operations"
        )
        tool.add_parameter("connection_id", DB_CONNECTION_PARAMS["connection_id"], required=True)
        tool.add_parameter("table_name", TABLE_PARAMS["table_name"], required=True)
        return tool
    
    @staticmethod
    def _get_filtered_row_count_tool() -> ToolSchema:
        tool = ToolSchema(
            name="db_get_filtered_row_count",
            description="Get count of rows matching a filter condition"
        )
        tool.add_parameter("connection_id", DB_CONNECTION_PARAMS["connection_id"], required=True)
        tool.add_parameter("table_name", TABLE_PARAMS["table_name"], required=True)
        tool.add_parameter("filter_condition", ParameterSchema(
            type=ParameterType.STRING,
            description="SQL WHERE condition (default: '1=1')",
            default="1=1"
        ))
        return tool