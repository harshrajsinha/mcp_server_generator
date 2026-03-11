# SciKiq DB Utils MCP Server

## Complete Database Connectivity Solution for Claude Desktop

---

## 🎯 **Purpose & Overview**

The **SciKiq DB Utils MCP Server** is a comprehensive Model Context Protocol (MCP) server that provides Claude Desktop with seamless access to 25+ database systems. It transforms Claude into a powerful database analyst, data engineer, and SQL expert by enabling direct database connectivity, query execution, and data analysis capabilities.

### **What This MCP Server Does**
- 🔗 **Universal Database Connectivity**: Connect to MySQL, PostgreSQL, Oracle, SQL Server, MongoDB, DuckDB, and 20+ other database systems
- 📊 **Intelligent Data Analysis**: Automatically discover tables, analyze schemas, and provide data insights
- 🔍 **Advanced Query Capabilities**: Execute SQL queries, generate reports, and perform complex data operations
- ☁️ **Cloud Storage Integration**: Direct access to AWS S3, Google Cloud Storage, and other cloud data sources
- 🛡️ **Enterprise Security**: Encrypted credentials, SQL injection prevention, and secure connection management
- 🚀 **AI-Powered Analytics**: Let Claude analyze your data patterns, suggest optimizations, and generate insights

---

## 🌟 **Key Features**

### **Database Support (25+ Systems)**
| Category | Supported Databases |
|----------|-------------------|
| **Relational** | MySQL, PostgreSQL, Oracle, SQL Server, SQLite, DB2, Teradata |
| **Cloud** | Amazon Redshift, Google BigQuery, Snowflake, Azure SQL |
| **NoSQL** | MongoDB, CouchDB, Cassandra |
| **Analytics** | DuckDB, ClickHouse, Presto, Apache Drill |
| **Enterprise** | SAP HANA, SAP ERP, IBM Netezza, Vertica |
| **Streaming** | Apache Kafka, Redis |
| **Storage** | AWS S3, Google Cloud Storage, Azure Blob |

### **Advanced Analytics Features**
- 📈 **Data Profiling**: Automatic column statistics, data quality assessment
- 🔄 **ETL Operations**: Data extraction, transformation, and loading
- 📊 **Query Optimization**: Performance analysis and query suggestions
- 🎯 **Schema Discovery**: Automatic table and relationship mapping
- 📝 **Documentation Generation**: Auto-generate data dictionaries and reports

### **Enterprise Security**
- 🔐 **Credential Encryption**: AES-256 encryption for database credentials
- 🛡️ **SQL Injection Prevention**: Built-in query sanitization and validation
- 🚦 **Rate Limiting**: Configurable connection and query throttling
- 📝 **Audit Logging**: Comprehensive activity tracking and monitoring
- 🔒 **Role-Based Access**: Fine-grained permission control

---

## 🏗️ **Architecture**

```
┌─────────────────────────────────────────────────────────────┐
│                    Claude Desktop                            │
└─────────────────────┬───────────────────────────────────────┘
                      │ MCP Protocol
┌─────────────────────▼───────────────────────────────────────┐
│                SciKiq MCP Server                            │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐ │
│  │ Config      │ │ Security    │ │ Connection Manager      │ │
│  │ Manager     │ │ Layer       │ │                         │ │
│  └─────────────┘ └─────────────┘ └─────────────────────────┘ │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │              Database Handlers                          │ │
│  │ MySQL │ PostgreSQL │ Oracle │ MongoDB │ DuckDB │ ...    │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────┬───────────────────────────────────────┘
                      │ Native Database Protocols
┌─────────────────────▼───────────────────────────────────────┐
│              Your Databases & Data Sources                  │
│  🏢 On-Premise  │  ☁️ Cloud  │  📊 Data Lakes  │  🗄️ Archives │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 **Quick Start Guide**

### **Prerequisites**
- 🖥️ **Claude Desktop** installed and configured
- 🐍 **Python 3.8+** with pip
- 🔑 **Database credentials** for systems you want to connect to

### **1. Installation**

```bash
# Clone or download the SciKiq DB Utils package
cd scikiq_v3/pkg_dbutils

# Install required dependencies
pip install -r requirements.txt

# Install the package
pip install -e .
```

### **2. Configuration**

Create a `config.ini` file with your database connections:

```ini
# Example: MySQL Connection
[mysql_prod]
database_type = MYSQL
host = your-mysql-server.com
port = 3306
database = production_db
username = your_username
password = your_password
connectivity_mechanism = DIRECT

# Example: PostgreSQL Connection  
[postgres_analytics]
database_type = POSTGRES
host = analytics-db.company.com
port = 5432
database = analytics
username = analyst_user
password = secure_password

# Example: DuckDB with S3 Storage
[duckdb_s3]
database_type = DUCKDB
database_path = :memory:
s3_bucket = your-data-bucket
s3_access_key_id = AKIA...
s3_secret_access_key = xyz123...
s3_region = ap-south-1
enable_s3 = true

# Example: MongoDB Connection
[mongodb_logs]
database_type = MONGODB
host = mongo-cluster.company.com
port = 27017
database = application_logs
username = log_reader
password = mongo_password
```

### **3. Claude Desktop Integration**

Add to your Claude Desktop `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "scikiq-db-utils": {
      "command": "python",
      "args": [
        "-m",
        "scikiq_dbutils.mcp_server.server"
      ],
      "cwd": "/path/to/scikiq_v3/pkg_dbutils",
      "env": {
        "CONFIG_PATH": "config.ini"
      }
    }
  }
}
```

### **4. Start Using**

Restart Claude Desktop and start asking database questions:

```
"Show me all tables in the mysql_prod database"
"What are the column details for the users table?"
"Run a query to find the top 10 customers by revenue"
"Analyze the data quality in the orders table"
```

---

## 📋 **Available MCP Tools**

### **Connection Management**
| Tool | Description | Example |
|------|-------------|---------|
| `db_test_connection` | Test database connectivity | Test connection to mysql_prod |
| `db_list_connections` | List all configured connections | Show available databases |
| `db_get_connection_info` | Get connection details | Get info for postgres_analytics |

### **Schema Discovery**
| Tool | Description | Example |
|------|-------------|---------|
| `db_get_all_tables` | List all tables in database | Show tables in production_db |
| `db_get_table_columns` | Get column names for table | Get columns for users table |
| `db_get_table_columns_details` | Get detailed column info | Get full schema for orders table |
| `db_get_table_relationships` | Find table relationships | Show foreign keys for users |

### **Query Execution**
| Tool | Description | Example |
|------|-------------|---------|
| `db_execute_query` | Run SELECT queries | Execute custom SQL queries |
| `db_execute_sql` | Run DDL/DML statements | Create tables, insert data |
| `db_read_table` | Read table data with limits | Read first 100 rows from orders |

### **Data Analysis**
| Tool | Description | Example |
|------|-------------|---------|
| `db_get_column_lov` | Get list of values for column | Get unique values in status column |
| `db_get_columns_profile` | Analyze column statistics | Profile data quality metrics |
| `db_generate_query` | AI-powered query generation | Generate reports automatically |

### **Advanced Operations**
| Tool | Description | Example |
|------|-------------|---------|
| `db_create_table` | Create new tables | Set up staging tables |
| `db_truncate_table` | Clear table data | Reset test environments |
| `db_create_view` | Create database views | Create analytical views |

---

## 🔧 **Configuration Guide**

### **Database Types Supported**
```ini
# Use these exact values for database_type:
MYSQL, POSTGRES, ORACLE, SQLSERVER, SQLITE, DB2, TERADATA,
REDSHIFT, BIGQUERY, SNOWFLAKE, MONGODB, DUCKDB, HIVE,
SAPHANA, NETEZZA, VERTICA, CLICKHOUSE, ATHENA
```

### **Connection Security Options**
```ini
# Connectivity mechanisms:
connectivity_mechanism = DIRECT        # Direct connection
connectivity_mechanism = SSH_TUNNEL    # SSH tunnel connection
connectivity_mechanism = SSL           # SSL/TLS encryption

# SSL Configuration (when using SSL)
ssl_cert_path = /path/to/client-cert.pem
ssl_key_path = /path/to/client-key.pem
ssl_ca_path = /path/to/ca-cert.pem

# SSH Tunnel Configuration
ssh_host = bastion.company.com
ssh_port = 22
ssh_username = tunnel_user
ssh_private_key_path = /path/to/ssh-key
```

### **Advanced DuckDB S3 Configuration**
```ini
[duckdb_s3_advanced]
database_type = DUCKDB
database_path = /path/to/persistent.duckdb  # Or :memory: for in-memory
s3_bucket = your-data-lake
s3_prefix = data/tables/                    # Optional: folder prefix
s3_access_key_id = AKIA...
s3_secret_access_key = xyz123...
s3_region = ap-south-1
default_file_format = parquet               # parquet, csv, json
enable_s3 = true
```

---

## 💡 **Usage Examples**

### **Example 1: Data Discovery**
```
User: "What databases do I have access to?"
Claude: Uses db_list_connections to show all configured databases

User: "Show me the tables in my production MySQL database"
Claude: Uses db_get_all_tables with mysql_prod connection

User: "What columns are in the customers table?"
Claude: Uses db_get_table_columns_details to show full schema
```

### **Example 2: Data Analysis**
```
User: "Analyze the sales data for last quarter"
Claude: 
1. Uses db_get_all_tables to find sales tables
2. Uses db_get_table_columns_details to understand schema
3. Uses db_execute_query to run analytical queries
4. Provides insights and visualizations
```

### **Example 3: ETL Operations**
```
User: "Copy data from MySQL to our data lake"
Claude:
1. Uses db_execute_query to extract data from MySQL
2. Processes and transforms the data
3. Uses DuckDB S3 handler to load data to S3 bucket
4. Confirms successful data transfer
```

### **Example 4: Data Quality Assessment**
```
User: "Check the data quality of our customer database"
Claude:
1. Uses db_get_columns_profile for statistical analysis
2. Uses db_get_column_lov to check value distributions  
3. Uses db_execute_query for custom data quality checks
4. Provides comprehensive data quality report
```

---

## 🛡️ **Security Best Practices**

### **Credential Management**
- 🔐 Store sensitive credentials in environment variables
- 🗝️ Use database-specific service accounts with minimal permissions
- 🔄 Rotate passwords regularly
- 📝 Enable audit logging for all database operations

### **Configuration Security**
```ini
# Use environment variables for sensitive data
password = ${DB_PASSWORD}
s3_secret_access_key = ${AWS_SECRET_KEY}

# Enable audit logging
audit_logging = true
audit_log_path = /secure/logs/db_audit.log

# Rate limiting
max_connections_per_minute = 60
query_timeout_seconds = 300
```

### **Network Security**
- 🌐 Use VPN or private networks when possible
- 🔒 Enable SSL/TLS for all database connections
- 🚪 Configure firewall rules to restrict database access
- 🔧 Use SSH tunnels for additional security layer

---

## 🔍 **Troubleshooting**

### **Common Issues**

#### **Connection Errors**
```
❌ "Failed to connect to database"
✅ Solution:
- Check network connectivity
- Verify credentials in config.ini
- Test connection using db_test_connection tool
- Check firewall and security group settings
```

#### **Authentication Failures**
```
❌ "Authentication failed"
✅ Solution:
- Verify username and password
- Check if account is locked or expired
- Ensure database user has necessary permissions
- For cloud databases, check IAM roles
```

#### **Query Timeouts**
```
❌ "Query execution timeout"
✅ Solution:
- Optimize query performance
- Increase query_timeout_seconds in config
- Use LIMIT clauses for large datasets
- Consider pagination for big results
```

#### **DuckDB S3 Issues**
```
❌ "No files found in S3 folder"
✅ Solution:
- Check S3 bucket permissions
- Verify AWS credentials
- Ensure file formats are supported (Parquet, CSV, JSON)
- ORC files are automatically excluded
```

### **Debug Mode**
Enable detailed logging by setting environment variable:
```bash
export SCIKIQ_DEBUG=true
```

---

## 🎯 **Specific Database Features**

### **DuckDB with S3 Storage**
- **Folder-as-Table**: S3 folders automatically become queryable tables
- **Format Support**: Parquet, CSV, JSON files (ORC excluded for compatibility)
- **Auto-Discovery**: Automatic detection of data schemas
- **Performance**: Optimized columnar processing for analytics

### **MongoDB Integration**
- **Document Queries**: Native MongoDB query syntax support
- **Aggregation Pipelines**: Complex data processing operations
- **Schema Inference**: Automatic schema detection for collections

### **SAP Connectivity**
- **SAP HANA**: Direct SQL access to SAP HANA databases
- **SAP ERP**: RFC and BAPI function calls
- **Real-time Data**: Live connection to SAP systems

### **Cloud Analytics**
- **BigQuery**: Google Cloud analytics platform
- **Snowflake**: Cloud data warehouse operations  
- **Redshift**: Amazon data warehouse connectivity

---

## 📚 **API Reference**

### **MCP Tool Specifications**

#### **db_execute_query**
```json
{
  "name": "db_execute_query",
  "description": "Execute SQL SELECT queries and return results",
  "inputSchema": {
    "type": "object",
    "properties": {
      "connection_id": {
        "type": "string",
        "description": "Database connection ID from config.ini"
      },
      "query": {
        "type": "string", 
        "description": "SQL SELECT query to execute"
      },
      "limit": {
        "type": "integer",
        "description": "Maximum number of rows to return",
        "default": 1000
      }
    },
    "required": ["connection_id", "query"]
  }
}
```

#### **db_get_table_columns_details**
```json
{
  "name": "db_get_table_columns_details",
  "description": "Get detailed column information for a table",
  "inputSchema": {
    "type": "object",
    "properties": {
      "connection_id": {
        "type": "string",
        "description": "Database connection ID"
      },
      "table_name": {
        "type": "string",
        "description": "Name of the table to analyze"
      }
    },
    "required": ["connection_id", "table_name"]
  }
}
```

---

## 🔄 **Version History & Roadmap**

### **Current Version: 3.0**
- ✅ 25+ database system support
- ✅ Enterprise security features
- ✅ DuckDB S3 integration with ORC exclusion
- ✅ Advanced analytics capabilities
- ✅ Claude Desktop MCP integration

### **Upcoming Features**
- 🔮 **AI Query Optimization**: Machine learning-powered query suggestions
- 🔮 **Visual Query Builder**: Drag-and-drop query construction
- 🔮 **Real-time Streaming**: Live data processing capabilities
- 🔮 **Advanced Encryption**: Zero-knowledge encryption for credentials
- 🔮 **Multi-Cloud Support**: Enhanced cloud provider integrations

---

## 📞 **Support & Community**

### **Getting Help**
- 📖 **Documentation**: This comprehensive guide
- 🐛 **Issue Tracking**: Report bugs and request features
- 💬 **Community Forum**: Connect with other users
- 📧 **Enterprise Support**: For business-critical deployments

### **Contributing**
We welcome contributions! Areas where you can help:
- 🔌 **New Database Connectors**: Add support for additional databases
- 🛡️ **Security Enhancements**: Improve authentication and encryption
- 📊 **Analytics Features**: Add new data analysis capabilities
- 📝 **Documentation**: Improve guides and examples

---

## 📄 **License & Legal**

This MCP server is designed for legitimate database connectivity and analysis purposes. Users are responsible for:
- 🔒 Securing their database credentials
- 📋 Compliance with data protection regulations
- 🏢 Following organizational data access policies
- ⚖️ Respecting database licensing terms

---

## 🎉 **Conclusion**

The **SciKiq DB Utils MCP Server** transforms Claude Desktop into a powerful database analyst and data engineer. With support for 25+ database systems, enterprise security features, and advanced analytics capabilities, it provides a comprehensive solution for data connectivity and analysis.

**Ready to get started?** Follow the Quick Start Guide above and unlock the full potential of AI-powered database analytics with Claude Desktop!

---

*📅 Last Updated: November 6, 2025*  
*🔖 Version: 3.0*  
*🏢 SciKiq Database Utilities - MCP Server Edition*