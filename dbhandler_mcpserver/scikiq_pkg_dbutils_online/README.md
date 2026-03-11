# SciKiq DB Utils - MCP Server Edition

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io/)
[![Claude Desktop](https://img.shields.io/badge/Claude-Desktop-orange.svg)](https://claude.ai/desktop)

## **Transform Claude Desktop into a Powerful Database Expert** 🚀

The **SciKiq DB Utils MCP Server** is a comprehensive Model Context Protocol (MCP) server that connects Claude Desktop to 25+ database systems, enabling AI-powered data analysis, query execution, and database management.

---

## 🌟 **Key Features**

- 🔗 **Universal Database Connectivity**: MySQL, PostgreSQL, Oracle, SQL Server, MongoDB, DuckDB, and 20+ more
- ☁️ **Cloud Integration**: AWS S3, Google BigQuery, Snowflake, Azure SQL, Amazon Redshift
- 🛡️ **Enterprise Security**: Encrypted credentials, SQL injection prevention, audit logging
- 📊 **AI-Powered Analytics**: Automatic schema discovery, data profiling, query optimization
- 🔍 **Advanced Features**: ETL operations, data quality assessment, relationship mapping

---

## 📚 **Documentation**

| Document | Purpose | Audience |
|----------|---------|----------|
| **[📖 Complete Documentation](MCP_SERVER_DOCUMENTATION.md)** | Comprehensive guide with all features and capabilities | All users, LLMs, developers |
| **[🚀 Setup Guide](SETUP_GUIDE.md)** | Step-by-step installation and configuration | End users, system administrators |
| **[📋 Quick Reference](QUICK_REFERENCE.md)** | Essential commands and troubleshooting | Daily users, quick lookups |

---

## ⚡ **Quick Start**

### **1. Installation**
```bash
cd scikiq_v3/pkg_dbutils
pip install -r requirements.txt
pip install -e .
```

### **2. Configuration**
Create `config.ini`:
```ini
[my_database]
database_type = MYSQL
host = your-server.com
port = 3306
database = your_db
username = your_user
password = your_password
```

### **3. Claude Desktop Integration**
Add to `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "scikiq-db-utils": {
      "command": "python",
      "args": ["-m", "scikiq_dbutils.mcp_server.server"],
      "cwd": "/path/to/pkg_dbutils"
    }
  }
}
```

### **4. Start Using**
```
"Show me all my databases"
"What tables are in the production database?"
"Analyze the customer data quality"
```

---

## 🎯 **Supported Databases**

### **Relational Databases**
MySQL • PostgreSQL • Oracle • SQL Server • SQLite • DB2 • Teradata

### **Cloud Analytics**
Amazon Redshift • Google BigQuery • Snowflake • Azure SQL • Amazon Athena

### **NoSQL & Modern**
MongoDB • DuckDB • ClickHouse • Apache Hive • CouchDB

### **Enterprise Systems**
SAP HANA • SAP ERP • IBM Netezza • Vertica • Salesforce

### **Cloud Storage**
AWS S3 • Google Cloud Storage • Azure Blob Storage

---

## 🛠️ **Available MCP Tools**

| Category | Tools | Purpose |
|----------|-------|---------|
| **Connection** | `db_test_connection`, `db_list_connections` | Database connectivity management |
| **Discovery** | `db_get_all_tables`, `db_get_table_columns` | Schema and structure exploration |
| **Query** | `db_execute_query`, `db_execute_sql` | SQL execution and data retrieval |
| **Analysis** | `db_get_columns_profile`, `db_get_column_lov` | Data quality and profiling |
| **Management** | `db_create_table`, `db_truncate_table` | Database administration |

---

## 🌟 **Special Features**

### **DuckDB S3 Integration**
- **Folder-as-Table**: S3 folders automatically become queryable tables
- **Format Support**: Parquet, CSV, JSON (ORC files automatically excluded)
- **Auto-Discovery**: Automatic schema detection and data profiling
- **Performance**: Optimized columnar processing for analytics

### **Enterprise Security**
- **Credential Encryption**: AES-256 encryption for sensitive data
- **SQL Injection Prevention**: Built-in query sanitization
- **Audit Logging**: Comprehensive activity tracking
- **Role-Based Access**: Fine-grained permission control

### **AI-Powered Analytics**
- **Smart Query Generation**: AI-assisted SQL query creation
- **Data Quality Assessment**: Automatic data profiling and quality metrics
- **Relationship Discovery**: Automatic detection of table relationships
- **Performance Optimization**: Query performance analysis and suggestions

---

## 💡 **Example Use Cases**

### **Data Discovery & Exploration**
```
"What data do I have access to?"
"Show me the structure of the customers table"
"Find all tables related to sales data"
```

### **Data Analysis & Reporting**
```
"Analyze sales trends for the last quarter"
"Create a customer demographics report"
"Find data quality issues in the user database"
```

### **Database Management**
```
"Test all my database connections"
"Show me table sizes and row counts"
"Generate a data dictionary for the schema"
```

### **ETL & Data Integration**
```
"Copy data from MySQL to our S3 data lake"
"Transform and load CSV files from S3"
"Validate data consistency across databases"
```

---

## 🔧 **Configuration Examples**

### **MySQL with SSL**
```ini
[mysql_secure]
database_type = MYSQL
host = secure-mysql.company.com
port = 3306
database = production
username = secure_user
password = ${MYSQL_PASSWORD}
connectivity_mechanism = SSL
ssl_cert_path = /path/to/client-cert.pem
```

### **DuckDB with S3 Data Lake**
```ini
[s3_analytics]
database_type = DUCKDB
database_path = :memory:
s3_bucket = company-data-lake
s3_access_key_id = ${AWS_ACCESS_KEY}
s3_secret_access_key = ${AWS_SECRET_KEY}
s3_region = ap-south-1
enable_s3 = true
```

### **MongoDB Cluster**
```ini
[mongodb_logs]
database_type = MONGODB
host = mongo-cluster.company.com
port = 27017
database = application_logs
username = log_reader
password = ${MONGO_PASSWORD}
```

---

## 🛡️ **Security Features**

- 🔐 **Encrypted Storage**: Sensitive credentials protected with AES-256 encryption
- 🛡️ **Input Validation**: Comprehensive SQL injection prevention
- 📝 **Audit Logging**: Detailed tracking of all database operations
- 🚦 **Rate Limiting**: Configurable connection and query throttling
- 🔒 **Access Control**: Role-based permissions and connection restrictions

---

## 🔍 **Troubleshooting**

### **Common Issues**
- **Connection Errors**: Check network, credentials, and firewall settings
- **Authentication Failures**: Verify user permissions and password policies
- **Query Timeouts**: Optimize queries or adjust timeout settings
- **Schema Access**: Ensure database user has appropriate SELECT permissions

### **Debug Mode**
Enable detailed logging:
```bash
export SCIKIQ_DEBUG=true
```

---

## 📊 **Architecture**

```
Claude Desktop
      ↓ MCP Protocol
SciKiq MCP Server
      ↓ Native Protocols  
Your Databases & Data Sources
```

The MCP server acts as a universal translator between Claude Desktop and your database systems, providing secure, intelligent access to your data infrastructure.

---

## 🚀 **Getting Started**

1. **📖 Read**: Start with the [Setup Guide](SETUP_GUIDE.md) for step-by-step instructions
2. **⚙️ Configure**: Set up your database connections in `config.ini`
3. **🔗 Connect**: Add the MCP server to Claude Desktop
4. **🎯 Explore**: Begin with simple queries to test your setup
5. **📊 Analyze**: Leverage Claude's AI capabilities for data insights

---

## 📞 **Support & Community**

- **📚 Documentation**: Comprehensive guides and API reference
- **🐛 Issues**: Report bugs and request features
- **💬 Community**: Connect with other users and contributors
- **🏢 Enterprise**: Professional support for business deployments

---

## 🎉 **Transform Your Data Workflow**

With the SciKiq DB Utils MCP Server, Claude Desktop becomes your intelligent database companion, capable of:

- 🔍 **Discovering** and exploring your data landscape
- 📊 **Analyzing** complex datasets with AI-powered insights  
- 🛠️ **Managing** database operations and maintenance
- 📈 **Optimizing** query performance and data quality
- 🔄 **Integrating** multiple data sources seamlessly

**Ready to revolutionize your data analysis workflow?** Start with the [Setup Guide](SETUP_GUIDE.md) and unlock the full potential of AI-powered database connectivity!

---

*SciKiq DB Utils MCP Server - Connecting AI to Your Data Universe* 🌟