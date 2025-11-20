# ScikiQ Database Handler MCP - Database Connector for Claude AI

[![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io/)

Connect Claude AI to your databases with secure, enterprise-grade database operations. The ScikiQ Database Handler provides seamless integration between Claude and your data infrastructure.

## 🚀 Features

- 🗄️ **Multi-Database Support**: MySQL, PostgreSQL, Oracle, SQL Server, MongoDB, Snowflake, BigQuery, DuckDB, and 16+ more
- 🔒 **Enterprise Security**: Encrypted credentials, SQL injection prevention, rate limiting, connection validation
- ⚡ **25+ Database Operations**: Query, analyze, profile, and manage your databases with AI assistance  
- 📊 **Data Analysis**: Statistical profiling, relationship mapping, metadata extraction
- 🔄 **Connection Management**: Create, test, and manage multiple database connections
- 🏗️ **High Performance**: Optimized queries with connection pooling and caching
- 🛡️ **Production Ready**: Comprehensive logging, monitoring, and error handling

## 🎯 Supported Databases

| Database | Type | Status |
|----------|------|--------|
| MySQL/MariaDB | Relational | ✅ Full Support |
| PostgreSQL | Relational | ✅ Full Support |
| Oracle | Relational | ✅ Full Support |
| Microsoft SQL Server | Relational | ✅ Full Support |
| MongoDB | NoSQL | ✅ Full Support |
| Snowflake | Cloud DW | ✅ Full Support |
| Google BigQuery | Cloud DW | ✅ Full Support |
| Amazon Redshift | Cloud DW | ✅ Full Support |
| AWS Athena | Analytics | ✅ Full Support |
| SAP HANA | In-Memory | ✅ Full Support |
| Vertica | Analytics | ✅ Full Support |
| IBM DB2 | Relational | ✅ Full Support |
| Teradata | DW | ✅ Full Support |
| Netezza | DW | ✅ Full Support |
| Apache Hive | Big Data | ✅ Full Support |
| ChromaDB | Vector | ✅ Full Support |
| DuckDB | Analytics/S3 | ✅ Full Support |

## 📦 Installation

### Prerequisites

- Python 3.9 or higher
- Claude Desktop or Claude API access

### Via pip (Recommended)

```bash
pip install scikiq-dbhandler-mcp
```

### From Source

```bash
git clone https://github.com/scikiq/scikiq-dbhandler-mcp.git
cd scikiq-dbhandler-mcp
pip install -e .
```

## ⚙️ Configuration

### 1. Configure Claude Desktop

Add to your Claude Desktop config file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`  
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`  
**Linux**: `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "scikiq-dbhandler": {
      "command": "python",
      "args": ["-m", "scikiq_dbutils.mcp_server.main"],
      "env": {
        "DBHANDLER_MASTER_PASSWORD": "your-secure-master-password"
      }
    }
  }
}
```

### 2. Environment Variables

Create a `.env` file or set environment variables:

```bash
# Required
DBHANDLER_MASTER_PASSWORD=your-secure-master-password

# Optional
LOG_LEVEL=INFO
RATE_LIMIT_MAX_REQUESTS=100
RATE_LIMIT_WINDOW_MINUTES=60
```

### 3. Configuration Files

#### INI Configuration (Recommended)

Create `~/.scikiq_mcp/connections.ini`:

```ini
[database.prod_mysql]
db_type = MYSQL
host = mysql.prod.company.com
port = 3306
database = production
username = app_user
password = base64encodedpassword
password_encrypted = 1
ssl = true

[database.analytics_postgres]
db_type = POSTGRES
host = postgres.analytics.company.com
port = 5432
database = analytics
username = analytics_user
password = plainpassword
password_encrypted = 0
schema = public
ssl_mode = require
```

## 🎯 Quick Start

### 1. Restart Claude Desktop

After configuration, restart Claude Desktop to load the connector.

### 2. Verify Installation

In Claude, ask:

```
List my available database connections
```

### 3. Create Your First Connection

```
Connect to my MySQL database:
- Connection ID: my_db
- Host: localhost  
- Port: 3306
- Database: testdb
- Username: user
- Password: password
```

### 4. Start Querying

```
Show me all tables in my_db
```

```
Describe the structure of the users table
```

```
Query the orders table and show me the top 10 recent orders
```

## 🛠️ Available Tools

### Connection Management
- `db_create_connection` - Create new database connection
- `db_test_connection` - Test connection validity  
- `db_close_connection` - Close active connection
- `db_list_connections` - List all connections

### Query Operations
- `db_execute_query` - Execute SELECT queries
- `db_execute_sql` - Execute INSERT/UPDATE/DELETE/DDL
- `db_generate_query` - Generate SQL from natural language

### Table Operations  
- `db_get_all_tables` - List all tables
- `db_get_table_columns` - Get column information
- `db_get_table_columns_details` - Detailed column metadata
- `db_read_table` - Read table data with filters
- `db_get_table_details` - Comprehensive table information
- `db_get_table_relationships` - Foreign key relationships
- `db_create_table` - Create new tables
- `db_truncate_table` - Remove all table data
- `db_create_view` - Create database views

### Data Analysis
- `db_get_column_lov` - List of values for columns
- `db_get_columns_profile` - Statistical profiling  
- `db_get_filtered_row_count` - Count with filters
- `db_get_incremental_columns` - Incremental load columns
- `db_fetch_delta_columns` - Delta columns for CDC

### Metadata Management
- `db_update_column_comment` - Update column descriptions

## 🔒 Security Features

### Credential Encryption
All database passwords are encrypted using Fernet symmetric encryption.

### SQL Injection Prevention
- Automatic query validation
- Dangerous pattern detection
- Parameter sanitization
- Query complexity limits

### Rate Limiting
- Per-connection request limits
- Sliding window algorithm
- Burst protection
- Configurable thresholds

### Connection Security  
- Host whitelist/blacklist
- SSL/TLS enforcement
- Private network controls
- Credential validation

## 📊 Usage Examples

### Example 1: Data Exploration

```
Claude, help me explore my customer database:
1. Show me all tables
2. Analyze the customers table structure  
3. Find the top 10 customers by revenue
4. Check for data quality issues
```

### Example 2: Schema Analysis

```
What's the relationship between my orders and customers tables?
Show me:
- Foreign key relationships  
- Column data types
- Index information
- Row counts
```

## 🆘 Support

- 📧 **Email**: support@scikiq.com
- 🐛 **Issues**: [GitHub Issues](https://github.com/scikiq/scikiq-dbhandler-mcp/issues)
- 📖 **Documentation**: [Full Documentation](https://docs.scikiq.com/dbhandler-mcp)

## 📄 License

This project is licensed under the MIT License.

---

**Made with ❤️ by the ScikiQ Team**