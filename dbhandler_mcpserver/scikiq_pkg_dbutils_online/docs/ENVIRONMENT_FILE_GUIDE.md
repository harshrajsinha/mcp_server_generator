# Environment File Integration Guide

This guide explains how to use environment files with the ScikiQ Database MCP Server, particularly for Claude Desktop integration.

## Overview

The ScikiQ Database MCP Server now supports loading database configurations from environment files, making it easy to manage multiple database connections without hardcoding credentials in configuration files.

## Environment File Format

Environment files use the format `CONNECTION_ID_PARAMETER=value`. Each database connection requires a unique connection ID, and parameters are separated by underscores.

### Basic Connection Parameters

Environment file parameters are automatically converted to DBFactory-compatible format:

```bash
# Required Parameters (converted to DBFactory format)
CONNECTION_ID_DB_TYPE=MYSQL      # → config["dbType"] = "MYSQL"
CONNECTION_ID_HOSTNAME=localhost # → config["hostname"] = "localhost" 
CONNECTION_ID_PORT=3306          # → config["port"] = 3306
CONNECTION_ID_DATABASE=mydb      # → config["dbname"] = "mydb"
CONNECTION_ID_USERNAME=myuser    # → config["dbuser"] = "myuser"
CONNECTION_ID_PASSWORD=mypassword # → config["pwd"] = "mypassword"

# Optional Parameters
CONNECTION_ID_SCHEMA=myschema     # → config["schema"] = "myschema"
```

### Supported Database Types

- `MYSQL` - MySQL/MariaDB
- `POSTGRES` - PostgreSQL
- `ORACLE` - Oracle Database
- `SQLSERVER` - Microsoft SQL Server
- `MONGODB` - MongoDB
- `SNOWFLAKE` - Snowflake
- `BIGQUERY` - Google BigQuery
- `REDSHIFT` - Amazon Redshift
- `SAPHANA` - SAP HANA
- `VERTICA` - Vertica
- `DB2` - IBM DB2
- `TERADATA` - Teradata
- `CHROMADB` - ChromaDB

### SSL Configuration

For databases that support SSL:

```bash
CONNECTION_ID_SSL_MODE=require
CONNECTION_ID_SSL_CERT=/path/to/client-cert.pem
CONNECTION_ID_SSL_KEY=/path/to/client-key.pem
CONNECTION_ID_SSL_CA=/path/to/ca-cert.pem
```

### SSH Tunnel Configuration

For connections through SSH tunnels:

```bash
CONNECTION_ID_SSH_HOST=bastion.example.com
CONNECTION_ID_SSH_USER=sshuser
CONNECTION_ID_SSH_PORT=22
CONNECTION_ID_SSH_KEY=/path/to/ssh-key
```

### Database-Specific Parameters

#### Snowflake
```bash
SNOWFLAKE_PROD_DB_TYPE=SNOWFLAKE
SNOWFLAKE_PROD_HOSTNAME=myaccount.snowflakecomputing.com
SNOWFLAKE_PROD_USERNAME=myuser
SNOWFLAKE_PROD_PASSWORD=mypassword
SNOWFLAKE_PROD_DATABASE=mydb
SNOWFLAKE_PROD_WAREHOUSE=mywarehouse
SNOWFLAKE_PROD_ACCOUNT=myaccount
SNOWFLAKE_PROD_ROLE=myrole
```

#### BigQuery
```bash
BIGQUERY_PROD_DB_TYPE=BIGQUERY
BIGQUERY_PROD_HOSTNAME=bigquery.googleapis.com
BIGQUERY_PROD_DATABASE=myproject
BIGQUERY_PROD_USERNAME=service-account@myproject.iam.gserviceaccount.com
BIGQUERY_PROD_PASSWORD=/path/to/service-account-key.json
```

### Server Configuration

You can also configure server-level settings:

```bash
# Server Settings
MCP_SERVER_LOG_LEVEL=INFO
MCP_SERVER_MAX_CONNECTIONS=50
MCP_SERVER_CONNECTION_TIMEOUT=30
MCP_SERVER_QUERY_TIMEOUT=300
MCP_SERVER_DEBUG=false
```

## Example Environment File

Here's a complete example with multiple database connections:

```bash
# ScikiQ Database MCP Server Configuration
# Production MySQL Database
PROD_MYSQL_DB_TYPE=MYSQL
PROD_MYSQL_HOSTNAME=prod-mysql.example.com
PROD_MYSQL_PORT=3306
PROD_MYSQL_DATABASE=production
PROD_MYSQL_USERNAME=app_user
PROD_MYSQL_PASSWORD=secure_password_123
PROD_MYSQL_SSL_MODE=require

# Development PostgreSQL Database
DEV_POSTGRES_DB_TYPE=POSTGRES
DEV_POSTGRES_HOSTNAME=localhost
DEV_POSTGRES_PORT=5432
DEV_POSTGRES_DATABASE=development
DEV_POSTGRES_USERNAME=dev_user
DEV_POSTGRES_PASSWORD=dev_password
DEV_POSTGRES_SCHEMA=public

# Analytics Snowflake Database
ANALYTICS_SF_DB_TYPE=SNOWFLAKE
ANALYTICS_SF_HOSTNAME=mycompany.snowflakecomputing.com
ANALYTICS_SF_USERNAME=analytics_user
ANALYTICS_SF_PASSWORD=sf_password
ANALYTICS_SF_DATABASE=ANALYTICS_DB
ANALYTICS_SF_WAREHOUSE=COMPUTE_WH
ANALYTICS_SF_ACCOUNT=mycompany
ANALYTICS_SF_ROLE=ANALYST_ROLE

# MongoDB for Document Storage
DOCS_MONGO_DB_TYPE=MONGODB
DOCS_MONGO_HOSTNAME=mongo.example.com
DOCS_MONGO_PORT=27017
DOCS_MONGO_DATABASE=documents
DOCS_MONGO_USERNAME=mongo_user
DOCS_MONGO_PASSWORD=mongo_password

# Server Configuration
MCP_SERVER_LOG_LEVEL=INFO
MCP_SERVER_MAX_CONNECTIONS=25
MCP_SERVER_DEBUG=false
```

## Usage

### Command Line

#### Create Sample Environment File
```bash
python run_mcp_server.py --create-sample-env .env
```

#### Validate Environment File
```bash
python run_mcp_server.py --validate-env --env-file .env
```

#### Start Server with Environment File
```bash
python run_mcp_server.py --env-file .env
```

#### List Connections from Environment
```bash
python run_mcp_server.py --env-file .env --list-connections
```

### Using Startup Scripts

#### Windows
```cmd
start_mcp_server.bat --env-file .env
```

#### Linux/Mac
```bash
./start_mcp_server.sh --env-file .env
```

## Claude Desktop Integration

To use the MCP server with Claude Desktop, add this configuration to your `claude_desktop_config.json`:

### Windows
```json
{
  "mcpServers": {
    "scikiq-db": {
      "command": "python",
      "args": [
        "C:/DAAS/scikiq_v3/pkg_dbutils/run_mcp_server.py",
        "--env-file",
        "C:/DAAS/scikiq_v3/pkg_dbutils/.env"
      ]
    }
  }
}
```

### Linux/Mac
```json
{
  "mcpServers": {
    "scikiq-db": {
      "command": "python3",
      "args": [
        "/path/to/scikiq_v3/pkg_dbutils/run_mcp_server.py",
        "--env-file",
        "/path/to/scikiq_v3/pkg_dbutils/.env"
      ]
    }
  }
}
```

### Alternative with Startup Script
```json
{
  "mcpServers": {
    "scikiq-db": {
      "command": "C:/DAAS/scikiq_v3/pkg_dbutils/start_mcp_server.bat",
      "args": [
        "--env-file",
        "C:/DAAS/scikiq_v3/pkg_dbutils/.env"
      ]
    }
  }
}
```

## Security Best Practices

1. **Environment File Security**
   - Never commit `.env` files to version control
   - Set restrictive file permissions (600 on Unix systems)
   - Use strong, unique passwords for each database

2. **Credential Management**
   - Consider using environment variables instead of files for sensitive environments
   - Use service accounts with minimal required privileges
   - Rotate credentials regularly

3. **Network Security**
   - Use SSL/TLS connections when available
   - Configure SSH tunnels for additional security
   - Restrict database access to specific IP addresses

## Troubleshooting

### Common Issues

1. **Environment File Not Found**
   ```bash
   # Create sample environment file
   python run_mcp_server.py --create-sample-env .env
   ```

2. **Configuration Validation Errors**
   ```bash
   # Validate specific environment file
   python run_mcp_server.py --validate-env --env-file .env
   ```

3. **Connection Failures**
   ```bash
   # Test specific connection
   python run_mcp_server.py --env-file .env --test-connection PROD_MYSQL
   ```

### Debug Mode

Enable debug logging for troubleshooting:

```bash
# In environment file
MCP_SERVER_DEBUG=true
MCP_SERVER_LOG_LEVEL=DEBUG

# Or via command line
python run_mcp_server.py --env-file .env --log-level DEBUG
```

## Migration from Configuration Files

If you're migrating from JSON configuration files, you can convert your existing configurations:

1. **Extract Connection Parameters**
   - Copy database connection details
   - Convert to environment variable format
   - Add connection ID prefixes

2. **Test Migration**
   - Validate new environment file
   - Test connections individually
   - Compare functionality with old configuration

3. **Update Startup Commands**
   - Replace `--config` with `--env-file`
   - Update Claude Desktop configuration
   - Test integration end-to-end

## Advanced Configuration

### Multiple Environment Files

You can use multiple environment files for different environments:

```bash
# Development
python run_mcp_server.py --env-file .env.development

# Staging  
python run_mcp_server.py --env-file .env.staging

# Production
python run_mcp_server.py --env-file .env.production
```

### Environment Variable Override

Environment variables take precedence over environment files:

```bash
# Override specific connection in environment file
export PROD_MYSQL_PASSWORD="new_password"
python run_mcp_server.py --env-file .env
```

### Programmatic Configuration

You can also use the environment parser programmatically:

```python
from scikiq_dbutils.mcp_server.config.env_parser import EnvironmentConfigParser

# Parse environment file
parser = EnvironmentConfigParser('.env')
connections = parser.parse_all_connections()

# Use with MCP server
server = MCPServer(connection_configs=connections)
```