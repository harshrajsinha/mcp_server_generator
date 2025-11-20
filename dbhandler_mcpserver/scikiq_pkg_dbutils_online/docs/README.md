# ScikiQ Database MCP Server

A Model Context Protocol (MCP) server that exposes database functionality as tools for performing various database operations. Built on top of the ScikiQ Database Utils library, it supports multiple database types and provides a JSON-RPC 2.0 compliant interface.

## Features

- **Multi-Database Support**: MySQL, PostgreSQL, Oracle, SQL Server, MongoDB, Snowflake, BigQuery, Redshift, Athena, SAP HANA, Vertica, DB2, Teradata, ChromaDB, and SageMaker
- **JSON-RPC 2.0 Compliant**: Full compliance with JSON-RPC 2.0 specification
- **MCP Protocol**: Implements Model Context Protocol for tool-based interactions
- **Connection Management**: Secure connection pooling and management
- **Rich Tool Set**: 20+ database operation tools including querying, table management, and data analysis
- **Configuration Management**: Flexible configuration system with validation
- **Security Features**: SSL/SSH connectivity, credential management
- **Performance Optimization**: Polars integration for faster data processing

## Supported Database Operations

### Connection Management
- Create and test database connections
- List active connections
- Close connections

### Query Operations
- Execute SELECT queries with result formatting
- Execute SQL statements (INSERT, UPDATE, DELETE, DDL)
- Query builder with filters, sorting, and grouping

### Table Operations
- List all tables and views
- Get table structure and metadata
- Read table data with pagination
- Get table relationships and foreign keys

### Column Operations
- Get column details and data types
- Column profiling and statistics
- List of values (LOV) for columns
- Update column comments

### Data Management
- Incremental data loading support
- Change data capture (CDC) operations
- Row count with filters
- Table creation and management

## Quick Start

### 1. Installation

The MCP server is included with the ScikiQ Database Utils package:

```bash
pip install scikiq-dbutils
```

### 2. Start the Server

```bash
# Using Python
python run_mcp_server.py

# On Windows
run_mcp_server.bat

# With custom configuration
python run_mcp_server.py --config /path/to/config

# Show available tools
python run_mcp_server.py --help-tools
```

### 3. Configuration

The server uses configuration files stored in `~/.scikiq_mcp/` by default:

- `server_config.json`: Server settings
- `connections.json`: Database connection configurations

Example database configuration:

```json
{
  "connections": {
    "my_mysql": {
      "dbType": "MYSQL",
      "hostname": "localhost",
      "port": 3306,
      "dbname": "testdb",
      "dbuser": "user",
      "dbpassword": "password",
      "schema": "public"
    }
  }
}
```

### 4. Using with MCP Clients

The server communicates via stdin/stdout using JSON-RPC 2.0. Example interaction:

```json
// Request
{
  "jsonrpc": "2.0",
  "id": "1",
  "method": "tools/call",
  "params": {
    "name": "db_create_connection",
    "arguments": {
      "connection_id": "test_db",
      "config": {
        "dbType": "MYSQL",
        "hostname": "localhost",
        "port": 3306,
        "dbname": "testdb",
        "dbuser": "user",
        "dbpassword": "password"
      }
    }
  }
}

// Response
{
  "jsonrpc": "2.0",
  "id": "1",
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\\"connection_id\\": \\"test_db\\", \\"status\\": \\"connected\\"}"
      }
    ],
    "isError": false
  }
}
```

## Available Tools

### Connection Management Tools

| Tool | Description |
|------|-------------|
| `db_create_connection` | Create a new database connection |
| `db_test_connection` | Test database connection without persistence |
| `db_close_connection` | Close and remove a connection |
| `db_list_connections` | List all active connections |

### Query Execution Tools

| Tool | Description |
|------|-------------|
| `db_execute_query` | Execute SELECT queries with structured results |
| `db_execute_sql` | Execute SQL statements (DML/DDL) |

### Table Operations Tools

| Tool | Description |
|------|-------------|
| `db_get_all_tables` | List all tables and views |
| `db_get_table_columns` | Get table column information |
| `db_get_table_columns_details` | Get detailed column metadata |
| `db_read_table` | Read table data with pagination |
| `db_get_table_details` | Get comprehensive table information |
| `db_get_table_relationships` | Get foreign key relationships |

### Column Operations Tools

| Tool | Description |
|------|-------------|
| `db_get_column_lov` | Get unique values for a column |
| `db_get_columns_profile` | Get statistical column profiling |
| `db_update_column_comment` | Update column comments |

### Query Builder Tools

| Tool | Description |
|------|-------------|
| `db_generate_query` | Generate SQL queries from parameters |

### Table Management Tools

| Tool | Description |
|------|-------------|
| `db_create_table` | Create new tables |
| `db_truncate_table` | Remove all table data |
| `db_create_view` | Create database views |

### Data Management Tools

| Tool | Description |
|------|-------------|
| `db_get_incremental_columns` | Find columns for incremental loading |
| `db_fetch_delta_columns` | Get change data capture columns |
| `db_get_filtered_row_count` | Count rows with conditions |

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   MCP Client    │◄──►│   MCP Server    │◄──►│  Database       │
│                 │    │                 │    │  Handlers       │
├─────────────────┤    ├─────────────────┤    ├─────────────────┤
│ • Claude        │    │ • JSON-RPC 2.0  │    │ • MySQL         │
│ • VS Code       │    │ • Tool Registry │    │ • PostgreSQL    │
│ • Custom Apps   │    │ • Connection    │    │ • Oracle        │
│                 │    │   Management    │    │ • SQL Server    │
│                 │    │ • Config Mgmt   │    │ • MongoDB       │
│                 │    │                 │    │ • Snowflake     │
│                 │    │                 │    │ • And more...   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Key Components

1. **MCP Server (`server.py`)**: Main server handling JSON-RPC 2.0 communication
2. **Tool Registry (`tools/registry.py`)**: Manages available tools and validation
3. **Database Wrapper (`wrappers/db_wrapper.py`)**: Wraps database operations as tools
4. **Connection Manager (`wrappers/connection_manager.py`)**: Handles database connections
5. **Configuration Manager (`config/manager.py`)**: Manages server and database configurations
6. **Protocol Classes (`protocol/`)**: JSON-RPC 2.0 message handling

## Configuration

### Server Configuration

```json
{
  "server": {
    "name": "ScikiQ Database MCP Server",
    "version": "1.0.0",
    "log_level": "INFO",
    "max_connections": 100
  },
  "security": {
    "enable_auth": false,
    "api_key": null,
    "allowed_ips": []
  },
  "features": {
    "enable_connection_pooling": true,
    "default_query_limit": 10000,
    "max_query_limit": 100000,
    "enable_query_cache": false,
    "cache_ttl_seconds": 300
  }
}
```

### Database Configuration

```json
{
  "connections": {
    "production_mysql": {
      "dbType": "MYSQL",
      "hostname": "prod-mysql.example.com",
      "port": 3306,
      "dbname": "production",
      "dbuser": "app_user",
      "dbpassword": "encrypted_password",
      "schema": "app_schema",
      "connectivity_mechanism": "S",
      "ssl_ca_path": "/path/to/ca.pem"
    },
    "analytics_snowflake": {
      "dbType": "SNOWFLAKE",
      "hostname": "account.snowflakecomputing.com",
      "dbname": "ANALYTICS",
      "dbuser": "analyst",
      "dbpassword": "password",
      "warehouse": "ANALYTICS_WH",
      "account": "your_account",
      "role": "ANALYST_ROLE"
    }
  }
}
```

## Security Features

- **SSL/TLS Support**: Secure database connections with certificate validation
- **SSH Tunneling**: Connect through SSH tunnels for enhanced security  
- **Credential Management**: Secure storage and handling of database credentials
- **Connection Validation**: Comprehensive connection testing and validation
- **Error Handling**: Secure error messages without credential exposure

## Performance Features

- **Polars Integration**: Optional Polars backend for faster data processing
- **Batch Processing**: Configurable batch sizes for large datasets
- **Connection Pooling**: Efficient connection management and reuse
- **Query Optimization**: Built-in query limiting and optimization
- **Memory Management**: Efficient memory usage for large result sets

## Error Handling

The server provides detailed error information while maintaining security:

```json
{
  "jsonrpc": "2.0",
  "id": "1", 
  "error": {
    "code": -32002,
    "message": "Database connection error (MYSQL): Connection refused",
    "data": {
      "db_type": "MYSQL",
      "error": "Connection refused"
    }
  }
}
```

## Logging

Comprehensive logging for monitoring and debugging:

```
2024-01-01 10:00:00 - scikiq_dbutils.mcp_server.server - INFO - Starting ScikiQ Database MCP Server v1.0.0
2024-01-01 10:00:01 - scikiq_dbutils.mcp_server.server - INFO - Executing tool: db_execute_query
2024-01-01 10:00:02 - scikiq_dbutils.mcp_server.wrappers.connection_manager - INFO - Added database configuration: prod_mysql
```

## Command Line Interface

```bash
# Start server
python run_mcp_server.py

# Show help
python run_mcp_server.py --help

# Show available tools
python run_mcp_server.py --help-tools

# Get help for specific tool
python run_mcp_server.py --help-tool db_execute_query

# List configured connections
python run_mcp_server.py --list-connections

# Test a connection
python run_mcp_server.py --test-connection my_db

# Validate configuration
python run_mcp_server.py --validate-config

# Custom configuration directory
python run_mcp_server.py --config /custom/path

# Set log level
python run_mcp_server.py --log-level DEBUG
```

## Troubleshooting

### Common Issues

1. **Connection Refused**: Check database host, port, and network connectivity
2. **Authentication Failed**: Verify username and password
3. **SSL Errors**: Ensure SSL certificates are properly configured
4. **Tool Not Found**: Check tool name spelling and availability
5. **Parameter Errors**: Validate tool parameters against schema

### Debug Mode

Enable debug logging for detailed troubleshooting:

```bash
python run_mcp_server.py --log-level DEBUG
```

### Configuration Validation

Validate your configuration before starting:

```bash
python run_mcp_server.py --validate-config
```

## Integration Examples

See the `examples/` directory for:
- MCP client implementations
- Database configuration examples
- Tool usage examples
- Integration patterns

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure existing tests pass
5. Submit a pull request

## License

This project is licensed under the same terms as the ScikiQ Database Utils package.

## Support

For support and questions:
- Create an issue in the repository
- Check the examples and documentation
- Review the troubleshooting section