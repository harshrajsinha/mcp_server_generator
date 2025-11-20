# ScikiQ Database MCP Server

A Model Context Protocol (MCP) server that exposes ScikiQ database utilities as tools for AI assistants like Claude Desktop.

## Overview

The ScikiQ Database MCP Server provides a standardized interface to interact with multiple database systems through the Model Context Protocol. It exposes all the functionality of the ScikiQ database utilities as MCP tools, enabling AI assistants to perform database operations seamlessly.

## Features

- **Multiple Database Support**: MySQL, PostgreSQL, Oracle, SQL Server, MongoDB, Snowflake, BigQuery, Redshift, SAP HANA, Vertica, DB2, Teradata, ChromaDB
- **Environment File Configuration**: Secure credential management through environment files
- **JSON-RPC 2.0 Compliance**: Full MCP protocol implementation
- **Connection Management**: Automatic connection pooling and management
- **SSL/SSH Support**: Secure connections with SSL certificates and SSH tunnels
- **Claude Desktop Integration**: Ready-to-use configuration for Claude Desktop

## Quick Start

### 1. Installation

#### Prerequisites
- Python 3.8+ (Python 3.9+ recommended)
- Pip package manager

#### Core Installation
```bash
# Install core dependencies
pip install -r requirements-minimal.txt

# Or install with specific database drivers
pip install -r requirements-mysql.txt      # For MySQL
pip install -r requirements-postgresql.txt # For PostgreSQL
pip install -r requirements-cloud.txt      # For Snowflake, BigQuery
pip install -r requirements.txt            # Full installation
```

See [Installation Guide](INSTALLATION_GUIDE.md) for detailed instructions.

### 2. Create Environment File

```bash
python run_mcp_server.py --create-sample-env .env
```

Edit the `.env` file with your database credentials:

```bash
# MySQL Production Database
PROD_DB_DB_TYPE=MYSQL
PROD_DB_HOSTNAME=localhost
PROD_DB_PORT=3306
PROD_DB_DATABASE=production
PROD_DB_USERNAME=app_user
PROD_DB_PASSWORD=your_password_here
```

### 3. Start the Server

#### Using Python directly:
```bash
python run_mcp_server.py --env-file .env
```

#### Using startup scripts:
```bash
# Windows
start_mcp_server.bat --env-file .env

# Linux/Mac
./start_mcp_server.sh --env-file .env
```

### 4. Claude Desktop Integration

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "scikiq-db": {
      "command": "python",
      "args": [
        "/path/to/run_mcp_server.py",
        "--env-file",
        "/path/to/.env"
      ]
    }
  }
}
```

## Available Tools

The MCP server exposes 20+ database tools:

### Connection Management
- `db_create_connection` - Create new database connections
- `db_test_connection` - Test database connectivity
- `db_close_connection` - Close active connections
- `db_list_connections` - List available connections

### Query Operations
- `db_execute_query` - Execute SQL queries
- `db_execute_stored_procedure` - Execute stored procedures
- `db_fetch_data` - Fetch data with pagination
- `db_get_query_plan` - Get query execution plans

### Table Operations
- `db_list_tables` - List database tables
- `db_describe_table` - Get table schema
- `db_create_table` - Create new tables
- `db_drop_table` - Drop tables
- `db_get_table_statistics` - Get table statistics

### Column Operations
- `db_list_columns` - List table columns
- `db_get_column_info` - Get column details
- `db_create_index` - Create database indexes
- `db_drop_index` - Drop indexes

### Data Operations
- `db_bulk_insert` - Bulk data insertion
- `db_export_to_csv` - Export data to CSV
- `db_import_from_csv` - Import data from CSV

### System Operations
- `db_get_server_info` - Get database server information
- `db_get_performance_metrics` - Get performance metrics

## Command Line Options

```bash
python run_mcp_server.py [options]

Options:
  --env-file FILE           Environment file path
  --config DIR              Configuration directory
  --log-level LEVEL         Log level (DEBUG, INFO, WARNING, ERROR)
  --name NAME               Server name
  --version VERSION         Server version
  
Utilities:
  --create-sample-env FILE  Create sample environment file
  --validate-env            Validate environment file
  --list-connections        List configured connections
  --test-connection ID      Test specific connection
  --validate-config         Validate all configurations
  --help-tools              Show available tools
  --help-tool TOOL          Show help for specific tool
```

## Environment File Format

See [Environment File Guide](docs/ENVIRONMENT_FILE_GUIDE.md) for detailed information.

Basic format:
```bash
# Connection configuration
CONNECTION_ID_DB_TYPE=MYSQL
CONNECTION_ID_HOSTNAME=localhost
CONNECTION_ID_PORT=3306
CONNECTION_ID_DATABASE=mydb
CONNECTION_ID_USERNAME=user
CONNECTION_ID_PASSWORD=password

# Server configuration
MCP_SERVER_LOG_LEVEL=INFO
MCP_SERVER_MAX_CONNECTIONS=50
```

## Supported Databases

| Database | Type Code | Default Port | SSL Support | SSH Support |
|----------|-----------|--------------|-------------|-------------|
| MySQL | MYSQL | 3306 | ✅ | ✅ |
| PostgreSQL | POSTGRES | 5432 | ✅ | ✅ |
| Oracle | ORACLE | 1521 | ✅ | ✅ |
| SQL Server | SQLSERVER | 1433 | ✅ | ✅ |
| MongoDB | MONGODB | 27017 | ✅ | ✅ |
| Snowflake | SNOWFLAKE | 443 | ✅ | ❌ |
| BigQuery | BIGQUERY | 443 | ✅ | ❌ |
| Redshift | REDSHIFT | 5439 | ✅ | ✅ |
| SAP HANA | SAPHANA | 30015 | ✅ | ✅ |
| Vertica | VERTICA | 5433 | ✅ | ✅ |
| DB2 | DB2 | 50000 | ✅ | ✅ |
| Teradata | TERADATA | 1025 | ✅ | ✅ |
| ChromaDB | CHROMADB | 8000 | ❌ | ❌ |

## Security

### Best Practices
- Use environment files for credential management
- Enable SSL/TLS connections when available
- Use SSH tunnels for additional security
- Set restrictive file permissions on environment files
- Use service accounts with minimal privileges

### Example SSL Configuration
```bash
PROD_DB_SSL_MODE=require
PROD_DB_SSL_CERT=/path/to/client-cert.pem
PROD_DB_SSL_KEY=/path/to/client-key.pem
PROD_DB_SSL_CA=/path/to/ca-cert.pem
```

### Example SSH Configuration
```bash
PROD_DB_SSH_HOST=bastion.example.com
PROD_DB_SSH_USER=sshuser
PROD_DB_SSH_PORT=22
PROD_DB_SSH_KEY=/path/to/ssh-key
```

## Development

### Architecture

The MCP server is built with a modular architecture:

```
scikiq_dbutils/mcp_server/
├── protocol/           # JSON-RPC 2.0 protocol implementation
├── wrappers/          # Database connection management
├── tools/             # MCP tool definitions
├── config/            # Configuration and environment parsing
├── server.py          # Main MCP server
└── main.py           # CLI interface
```

### Adding New Tools

1. Define tool in `tools/registry.py`
2. Implement tool logic in `wrappers/db_wrapper.py`
3. Add tool registration in `tools/registry.py`

### Testing

```bash
# Validate environment configuration
python run_mcp_server.py --validate-env --env-file .env

# Test specific connection
python run_mcp_server.py --test-connection PROD_DB --env-file .env

# List available tools
python run_mcp_server.py --help-tools
```

## Troubleshooting

### Common Issues

1. **Connection Failed**
   ```bash
   python run_mcp_server.py --test-connection CONNECTION_ID --env-file .env
   ```

2. **Invalid Configuration**
   ```bash
   python run_mcp_server.py --validate-env --env-file .env
   ```

3. **Claude Desktop Not Connecting**
   - Check file paths in `claude_desktop_config.json`
   - Verify Python executable path
   - Check environment file permissions

### Debug Mode

Enable debug logging:
```bash
python run_mcp_server.py --env-file .env --log-level DEBUG
```

Or in environment file:
```bash
MCP_SERVER_DEBUG=true
MCP_SERVER_LOG_LEVEL=DEBUG
```

## Documentation

- [Environment File Guide](docs/ENVIRONMENT_FILE_GUIDE.md) - Detailed environment configuration
- [MCP Server Documentation](docs/MCP_SERVER.md) - Server implementation details
- [Database Wrapper Documentation](docs/DATABASE_WRAPPER.md) - Database wrapper API
- [Tool Registry Documentation](docs/TOOL_REGISTRY.md) - Available tools reference

## License

This project is part of the ScikiQ database utilities framework.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review the documentation
3. Create an issue in the repository