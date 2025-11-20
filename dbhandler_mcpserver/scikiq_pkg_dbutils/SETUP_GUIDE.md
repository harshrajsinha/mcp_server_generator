# 🚀 SciKiq MCP Server Setup Guide

## **Turn Claude Desktop into a Database Expert!**

This guide will help you connect Claude Desktop to your databases in just a few simple steps.

---

## 📋 **What You'll Need**

- ✅ Claude Desktop installed
- ✅ Python 3.8 or newer
- ✅ Access to your database systems
- ✅ 15 minutes to set up

---

## 🎯 **Step-by-Step Setup**

### **Step 1: Install the MCP Server**

Open a terminal/command prompt and run:

```bash
# Navigate to the SciKiq directory
cd /path/to/scikiq_v3/pkg_dbutils

# Install dependencies
pip install -r requirements.txt

# Install the package
pip install -e .
```

### **Step 2: Create Your Database Configuration**

Create a file called `config.ini` in the `pkg_dbutils` folder:

```ini
# Example: MySQL Database
[my_mysql_db]
database_type = MYSQL
host = mysql.mycompany.com
port = 3306
database = sales_data
username = analyst_user
password = my_secure_password

# Example: PostgreSQL Database  
[analytics_postgres]
database_type = POSTGRES
host = analytics.mycompany.com
port = 5432
database = analytics
username = data_analyst
password = another_password

# Example: DuckDB with S3 Data Lake
[s3_data_lake]
database_type = DUCKDB
database_path = :memory:
s3_bucket = company-data-lake
s3_access_key_id = AKIA1234567890
s3_secret_access_key = abcdef1234567890
s3_region = us-east-1
enable_s3 = true
```

**💡 Pro Tip**: You can add as many database connections as you need!

### **Step 3: Configure Claude Desktop**

Find your Claude Desktop configuration file:
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Mac**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

Add this configuration:

```json
{
  "mcpServers": {
    "scikiq-db-utils": {
      "command": "python",
      "args": [
        "-m",
        "scikiq_dbutils.mcp_server.server"
      ],
      "cwd": "/full/path/to/scikiq_v3/pkg_dbutils",
      "env": {
        "CONFIG_PATH": "config.ini"
      }
    }
  }
}
```

**⚠️ Important**: Replace `/full/path/to/scikiq_v3/pkg_dbutils` with your actual folder path!

### **Step 4: Restart Claude Desktop**

Close and restart Claude Desktop completely.

### **Step 5: Test Your Setup**

In Claude Desktop, try asking:

```
"What databases do I have access to?"
```

If everything is working, Claude will show you your configured databases!

---

## 🎉 **What You Can Do Now**

### **Explore Your Data**
```
"Show me all tables in my_mysql_db"
"What columns are in the customers table?"
"Describe the structure of the orders table"
```

### **Run Analysis**
```
"Show me the top 10 customers by revenue"
"Analyze the data quality in the users table"
"Find any missing data in the orders table"
```

### **Generate Reports**
```
"Create a monthly sales report"
"Show me customer demographics"
"Analyze sales trends over time"
```

---

## 🔧 **Common Database Configurations**

### **MySQL**
```ini
[mysql_production]
database_type = MYSQL
host = mysql.company.com
port = 3306
database = production
username = readonly_user
password = secure_password
connectivity_mechanism = SSL  # Optional: for encrypted connections
```

### **PostgreSQL**
```ini
[postgres_warehouse]
database_type = POSTGRES
host = postgres.company.com
port = 5432
database = data_warehouse
username = analyst
password = postgres_password
```

### **SQL Server**
```ini
[sqlserver_erp]
database_type = SQLSERVER
host = sqlserver.company.com
port = 1433
database = ERP_Database
username = domain\user
password = windows_password
```

### **MongoDB**
```ini
[mongodb_logs]
database_type = MONGODB
host = mongo.company.com
port = 27017
database = application_logs
username = log_reader
password = mongo_password
```

### **Oracle**
```ini
[oracle_finance]
database_type = ORACLE
host = oracle.company.com
port = 1521
database = FINANCE
username = finance_user
password = oracle_password
```

### **Amazon S3 Data Lake (via DuckDB)**
```ini
[s3_data_lake]
database_type = DUCKDB
database_path = :memory:
s3_bucket = my-company-data-lake
s3_access_key_id = AKIA...
s3_secret_access_key = secret...
s3_region = us-east-1
enable_s3 = true
s3_prefix = analytics/tables/  # Optional: folder prefix
```

---

## 🛡️ **Security Best Practices**

### **1. Use Environment Variables for Passwords**
Instead of putting passwords directly in the config file:

```ini
[secure_database]
database_type = MYSQL
host = mysql.company.com
port = 3306
database = production
username = user
password = ${MYSQL_PASSWORD}  # Reads from environment variable
```

Then set the environment variable:
```bash
# Windows
set MYSQL_PASSWORD=your_actual_password

# Mac/Linux
export MYSQL_PASSWORD=your_actual_password
```

### **2. Use Read-Only Database Users**
Create dedicated read-only users for Claude Desktop:
```sql
-- MySQL example
CREATE USER 'claude_readonly'@'%' IDENTIFIED BY 'secure_password';
GRANT SELECT ON production.* TO 'claude_readonly'@'%';
```

### **3. Enable SSL Connections**
```ini
[secure_connection]
database_type = POSTGRES
host = secure-db.company.com
port = 5432
database = sensitive_data
username = secure_user
password = secure_password
connectivity_mechanism = SSL
ssl_cert_path = /path/to/client-cert.pem
ssl_key_path = /path/to/client-key.pem
ssl_ca_path = /path/to/ca-cert.pem
```

---

## 🔍 **Troubleshooting**

### **"MCP server not found" Error**
1. Check the `cwd` path in your Claude Desktop config
2. Make sure you installed the package with `pip install -e .`
3. Restart Claude Desktop completely

### **"Connection failed" Error**
1. Test your database connection outside of Claude first
2. Check if your database server is running
3. Verify your credentials are correct
4. Check firewall and network settings

### **"No tables visible" Error**
1. Make sure your database user has SELECT permissions
2. Check if you're connecting to the right database/schema
3. Some databases require specific schema permissions

### **DuckDB S3 Issues**
1. Verify your AWS credentials have S3 read access
2. Check that your S3 bucket exists and has data
3. Supported file formats: Parquet, CSV, JSON (ORC files are automatically excluded)

---

## 💡 **Pro Tips**

### **Multiple Environments**
Set up different configurations for different environments:
```ini
[mysql_dev]
database_type = MYSQL
host = dev-mysql.company.com
# ... dev settings

[mysql_prod]
database_type = MYSQL
host = prod-mysql.company.com
# ... production settings
```

### **Connection Naming**
Use descriptive connection names that indicate purpose:
- `sales_analytics_postgres`
- `customer_data_mysql`
- `logs_mongodb`
- `warehouse_redshift`

### **Testing Connections**
Before asking complex questions, test with simple ones:
```
"Test connection to mysql_prod"
"Show me tables in sales_analytics_postgres"
```

---

## 🎯 **Next Steps**

Once you have everything set up:

1. **Explore**: Ask Claude to show you what data you have
2. **Analyze**: Start with simple queries and build up complexity
3. **Automate**: Use Claude to generate reports and insights
4. **Secure**: Review and improve your security settings
5. **Expand**: Add more database connections as needed

---

## 📞 **Getting Help**

If you run into issues:

1. **Check the logs**: Look for error messages in Claude Desktop's console
2. **Test manually**: Try connecting to your database with a regular database client
3. **Review config**: Double-check your `config.ini` syntax
4. **Consult docs**: See `MCP_SERVER_DOCUMENTATION.md` for detailed information

---

**🎉 Congratulations!** You now have Claude Desktop connected to your databases. Start exploring your data with the power of AI!

---

*Setup Guide for SciKiq DB Utils MCP Server v3.0*