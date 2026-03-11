# SciKiq MCP Server - Quick Reference

## 🚀 **Quick Setup Checklist**

### **1. Installation**
```bash
cd scikiq_v3/pkg_dbutils
pip install -r requirements.txt
pip install -e .
```

### **2. Configuration File (config.ini)**
```ini
[your_database_name]
database_type = MYSQL|POSTGRES|ORACLE|DUCKDB|MONGODB|...
host = your-server.com
port = 3306
database = your_database
username = your_user
password = your_password
```

### **3. Claude Desktop Config**
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

## 🛠️ **Essential MCP Tools**

| **Category** | **Tool** | **Purpose** |
|--------------|----------|-------------|
| **Connection** | `db_test_connection` | Test database connectivity |
| **Discovery** | `db_get_all_tables` | List all tables |
| **Schema** | `db_get_table_columns_details` | Get table structure |
| **Query** | `db_execute_query` | Run SELECT queries |
| **Execute** | `db_execute_sql` | Run DDL/DML commands |
| **Analysis** | `db_get_columns_profile` | Data quality analysis |

## 📊 **Supported Databases (25+)**

### **Relational Databases**
- MySQL, PostgreSQL, Oracle, SQL Server, SQLite
- DB2, Teradata, Vertica

### **Cloud Analytics**
- Amazon Redshift, Google BigQuery, Snowflake
- Azure SQL Database, Amazon Athena

### **NoSQL & Modern**
- MongoDB, DuckDB, ClickHouse
- Apache Hive, Apache Drill

### **Enterprise Systems**
- SAP HANA, SAP ERP, IBM Netezza
- Salesforce, Oracle EBS

## 🔧 **DuckDB S3 Special Configuration**
```ini
[duckdb_s3]
database_type = DUCKDB
database_path = :memory:
s3_bucket = your-data-bucket
s3_access_key_id = AKIA...
s3_secret_access_key = xyz...
s3_region = ap-south-1
enable_s3 = true
```

**Features:**
- ✅ Folders become tables automatically
- ✅ Supports Parquet, CSV, JSON
- ❌ ORC files excluded (not supported)
- 🔍 Auto-schema detection

## 💬 **Common Claude Queries**

```
"Show me all my databases"
"What tables are in the production database?"
"Describe the users table structure"
"Run a query to find top 10 customers"
"Analyze data quality in the orders table"
"Connect to my S3 data lake"
"Profile the customer demographics"
```

## 🛡️ **Security Quick Tips**

- 🔐 Use environment variables: `password = ${DB_PASSWORD}`
- 🔒 Enable SSL: `connectivity_mechanism = SSL`
- 🚪 Use SSH tunnels for extra security
- 📝 Enable audit logging: `audit_logging = true`

## 🔍 **Troubleshooting**

| **Issue** | **Solution** |
|-----------|--------------|
| Connection fails | Check credentials, network, firewall |
| Authentication error | Verify username/password, permissions |
| Query timeout | Add LIMIT clause, optimize query |
| ORC files error | Files automatically excluded in DuckDB |
| No tables visible | Check database permissions, schema access |

## 📞 **Need Help?**

1. **Check**: `MCP_SERVER_DOCUMENTATION.md` for full details
2. **Test**: Use `db_test_connection` tool first
3. **Verify**: Configuration syntax in `config.ini`
4. **Debug**: Set `SCIKIQ_DEBUG=true` environment variable

---

*Quick Reference for SciKiq DB Utils MCP Server v3.0*