# Troubleshooting Guide

This guide helps you diagnose and resolve common issues with the ScikiQ Database Handler MCP Connector.

## Table of Contents
- [Installation Issues](#installation-issues)
- [Configuration Problems](#configuration-problems)
- [Connection Failures](#connection-failures)
- [Query Execution Issues](#query-execution-issues)
- [Performance Problems](#performance-problems)
- [Claude Integration Issues](#claude-integration-issues)
- [Security and Authentication](#security-and-authentication)
- [Platform-Specific Issues](#platform-specific-issues)
- [Diagnostic Tools](#diagnostic-tools)

## Installation Issues

### Issue: Package Installation Fails

**Symptoms:**
```bash
pip install scikiq-dbhandler-mcp
ERROR: Could not find a version that satisfies the requirement scikiq-dbhandler-mcp
```

**Solutions:**

1. **Check Python Version**
   ```bash
   python --version
   # Ensure Python 3.9 or higher
   ```

2. **Update pip**
   ```bash
   pip install --upgrade pip
   ```

3. **Use Alternative Installation Methods**
   ```bash
   # Install from source
   git clone https://github.com/scikiq/scikiq-dbhandler-mcp.git
   cd scikiq-dbhandler-mcp
   pip install -e .
   ```

4. **Check Network Connectivity**
   ```bash
   pip install --index-url https://pypi.org/simple/ scikiq-dbhandler-mcp
   ```

### Issue: Database Driver Installation Fails

**Symptoms:**
```bash
pip install cx-Oracle
ERROR: Microsoft Visual C++ 14.0 is required
```

**Solutions:**

1. **Windows: Install Build Tools**
   - Download Microsoft C++ Build Tools
   - Or install Visual Studio Community

2. **Use Binary Packages**
   ```bash
   # Use pre-compiled binaries when available
   pip install psycopg2-binary  # instead of psycopg2
   pip install pymysql          # instead of mysqlclient
   ```

3. **Platform-Specific Solutions**
   ```bash
   # Linux: Install development packages
   sudo apt-get install python3-dev libpq-dev  # PostgreSQL
   sudo yum install python3-devel postgresql-devel  # CentOS/RHEL
   
   # macOS: Install with Homebrew
   brew install postgresql
   ```

### Issue: Import Errors After Installation

**Symptoms:**
```python
ModuleNotFoundError: No module named 'scikiq_dbutils'
```

**Solutions:**

1. **Check Installation Location**
   ```bash
   pip show scikiq-dbhandler-mcp
   python -c "import sys; print(sys.path)"
   ```

2. **Use Virtual Environment**
   ```bash
   python -m venv mcp_env
   source mcp_env/bin/activate  # Linux/macOS
   mcp_env\Scripts\activate     # Windows
   pip install scikiq-dbhandler-mcp
   ```

3. **Check for Multiple Python Versions**
   ```bash
   which python
   which python3
   # Use the same python executable for both installation and execution
   ```

## Configuration Problems

### Issue: Configuration File Not Found

**Symptoms:**
```
ConfigurationError: Configuration file 'config.ini' not found
```

**Solutions:**

1. **Create Configuration File**
   ```bash
   # Create default configuration
   python -m scikiq_dbutils.mcp_server.main --create-sample-config
   ```

2. **Use Absolute Path**
   ```bash
   # Specify full path to configuration file
   python -m scikiq_dbutils.mcp_server.main --config-file /full/path/to/config.ini
   ```

3. **Check File Permissions**
   ```bash
   ls -la config.ini
   chmod 644 config.ini  # Ensure readable
   ```

### Issue: Invalid Configuration Format

**Symptoms:**
```
ConfigParser.ParsingError: Source contains parsing errors
```

**Solutions:**

1. **Validate INI Format**
   ```python
   import configparser
   config = configparser.ConfigParser()
   try:
       config.read('config.ini')
       print("Configuration is valid")
   except Exception as e:
       print(f"Configuration error: {e}")
   ```

2. **Common INI Format Issues**
   ```ini
   # Wrong - Missing section header
   master_password = secret
   
   # Correct - Has section header
   [general]
   master_password = secret
   
   # Wrong - Unescaped special characters
   password = my"password'with quotes
   
   # Correct - Escaped or quoted
   password = "my\"password'with quotes"
   ```

3. **Use Configuration Validator**
   ```bash
   python -m scikiq_dbutils.mcp_server.main --validate-config config.ini
   ```

### Issue: Environment Variables Not Recognized

**Symptoms:**
```
KeyError: 'DBHANDLER_MASTER_PASSWORD'
```

**Solutions:**

1. **Set Environment Variables Correctly**
   ```bash
   # Windows
   set DBHANDLER_MASTER_PASSWORD=your_password
   
   # Linux/macOS
   export DBHANDLER_MASTER_PASSWORD="your_password"
   
   # Persistent (add to .bashrc or .profile)
   echo 'export DBHANDLER_MASTER_PASSWORD="your_password"' >> ~/.bashrc
   ```

2. **Use .env File**
   ```bash
   # Create .env file in working directory
   echo "DBHANDLER_MASTER_PASSWORD=your_password" > .env
   ```

3. **Check Environment Variable Scope**
   ```bash
   # Test if variable is set
   echo $DBHANDLER_MASTER_PASSWORD
   
   # In Python
   python -c "import os; print(os.environ.get('DBHANDLER_MASTER_PASSWORD'))"
   ```

## Connection Failures

### Issue: Database Connection Timeout

**Symptoms:**
```
ConnectionError: Connection timeout after 30 seconds
```

**Solutions:**

1. **Check Network Connectivity**
   ```bash
   # Test basic connectivity
   telnet database-host 5432
   ping database-host
   
   # Test with nmap
   nmap -p 5432 database-host
   ```

2. **Adjust Timeout Settings**
   ```ini
   [database:my_db]
   type = postgresql
   host = db.company.com
   connection_timeout = 60      # Increase timeout
   ```

3. **Check Firewall Rules**
   ```bash
   # Windows
   netsh advfirewall firewall show rule name="PostgreSQL"
   
   # Linux
   iptables -L | grep 5432
   ufw status
   ```

### Issue: Authentication Failed

**Symptoms:**
```
AuthenticationError: password authentication failed for user "username"
```

**Solutions:**

1. **Verify Credentials**
   ```bash
   # Test credentials manually
   psql -h hostname -U username -d database
   mysql -h hostname -u username -p database
   ```

2. **Check Password Encryption**
   ```python
   # Test password decryption
   from scikiq_dbutils.mcp_server.security import CredentialManager
   cm = CredentialManager()
   # Verify password can be decrypted
   decrypted = cm.decrypt_credential(encrypted_password.encode())
   ```

3. **Database User Permissions**
   ```sql
   -- PostgreSQL: Check user permissions
   SELECT * FROM pg_user WHERE usename = 'your_username';
   SELECT * FROM pg_database WHERE datname = 'your_database';
   
   -- MySQL: Check user permissions
   SELECT * FROM mysql.user WHERE User = 'your_username';
   SHOW GRANTS FOR 'your_username'@'%';
   ```

### Issue: SSL/TLS Connection Problems

**Symptoms:**
```
SSLError: certificate verify failed: self signed certificate
```

**Solutions:**

1. **Configure SSL Settings**
   ```ini
   [database:secure_db]
   ssl_mode = require           # or prefer, allow, disable
   ssl_ca = /path/to/ca.pem    # CA certificate
   ssl_cert = /path/to/cert.pem # Client certificate
   ssl_key = /path/to/key.pem   # Client key
   ```

2. **Handle Self-Signed Certificates**
   ```ini
   # Allow self-signed certificates (not recommended for production)
   ssl_mode = require
   ssl_verify = false
   ```

3. **Check Certificate Files**
   ```bash
   # Verify certificate files exist and are readable
   ls -la /path/to/ssl/files/
   openssl x509 -in certificate.pem -text -noout
   ```

### Issue: Connection Pool Exhaustion

**Symptoms:**
```
ConnectionPoolError: Pool limit of 10 connections reached
```

**Solutions:**

1. **Increase Pool Size**
   ```ini
   [database:busy_db]
   pool_size = 20              # Increase pool size
   pool_timeout = 60           # Increase timeout
   pool_recycle = 3600         # Recycle connections hourly
   ```

2. **Monitor Connection Usage**
   ```python
   # Check active connections
   from scikiq_dbutils.mcp_server.handlers import DBFactory
   factory = DBFactory()
   pool_info = factory.get_pool_status('connection_name')
   print(f"Active: {pool_info['active']}, Idle: {pool_info['idle']}")
   ```

3. **Implement Connection Cleanup**
   ```python
   # Ensure connections are properly closed
   try:
       # Database operations
       pass
   finally:
       connection.close()
   ```

## Query Execution Issues

### Issue: SQL Syntax Errors

**Symptoms:**
```
ProgrammingError: syntax error at or near "SELCT"
```

**Solutions:**

1. **Use SQL Validator**
   ```bash
   python -c "
   from scikiq_dbutils.mcp_server.tools import validate_sql_syntax
   result = validate_sql_syntax('connection_name', 'your_query')
   print(result)
   "
   ```

2. **Check Database-Specific Syntax**
   ```sql
   -- PostgreSQL uses LIMIT
   SELECT * FROM table LIMIT 10;
   
   -- SQL Server uses TOP
   SELECT TOP 10 * FROM table;
   
   -- Oracle uses ROWNUM
   SELECT * FROM table WHERE ROWNUM <= 10;
   ```

3. **Use Parameterized Queries**
   ```python
   # Correct parameterized query
   query = "SELECT * FROM users WHERE id = ? AND status = ?"
   parameters = [123, 'active']
   ```

### Issue: Query Timeout

**Symptoms:**
```
TimeoutError: Query execution exceeded 30 seconds
```

**Solutions:**

1. **Increase Query Timeout**
   ```ini
   [general]
   default_timeout = 300       # 5 minutes
   query_timeout = 600         # 10 minutes
   ```

2. **Optimize Query Performance**
   ```sql
   -- Add appropriate indexes
   CREATE INDEX idx_table_column ON table_name (column_name);
   
   -- Use EXPLAIN to analyze query plan
   EXPLAIN ANALYZE SELECT * FROM large_table WHERE condition;
   ```

3. **Limit Result Sets**
   ```python
   # Add LIMIT to prevent large result sets
   query = "SELECT * FROM large_table WHERE condition LIMIT 1000"
   ```

### Issue: Memory Errors with Large Results

**Symptoms:**
```
MemoryError: Unable to allocate array with shape (1000000, 50)
```

**Solutions:**

1. **Use Result Streaming**
   ```python
   # Process results in chunks
   query = "SELECT * FROM large_table"
   for chunk in execute_query_chunked(query, chunk_size=10000):
       process_chunk(chunk)
   ```

2. **Limit Result Size**
   ```ini
   [general]
   max_result_rows = 50000     # Limit number of rows
   enable_compression = true   # Compress results
   ```

3. **Use Server-Side Cursors**
   ```python
   # For PostgreSQL
   cursor = connection.cursor(name='server_cursor')
   cursor.execute("SELECT * FROM large_table")
   while True:
       rows = cursor.fetchmany(1000)
       if not rows:
           break
       process_rows(rows)
   ```

## Performance Problems

### Issue: Slow Query Execution

**Symptoms:**
- Queries taking longer than expected
- High CPU or memory usage

**Solutions:**

1. **Analyze Query Plans**
   ```python
   # Get execution plan
   explain_result = get_query_explain_plan('connection_name', 'your_query')
   print(explain_result)
   ```

2. **Add Database Indexes**
   ```sql
   -- Identify missing indexes
   SELECT * FROM pg_stat_user_tables WHERE schemaname = 'public';
   
   -- Create appropriate indexes
   CREATE INDEX CONCURRENTLY idx_orders_date ON orders (order_date);
   ```

3. **Query Optimization Techniques**
   ```sql
   -- Use appropriate WHERE clauses
   SELECT * FROM orders WHERE order_date >= '2024-01-01' AND status = 'completed';
   
   -- Avoid SELECT *
   SELECT order_id, customer_id, total FROM orders;
   
   -- Use JOINs instead of subqueries when appropriate
   SELECT o.order_id, c.name 
   FROM orders o 
   JOIN customers c ON o.customer_id = c.id;
   ```

### Issue: High Memory Usage

**Symptoms:**
```
MemoryError: Process memory limit exceeded
```

**Solutions:**

1. **Configure Memory Limits**
   ```ini
   [general]
   max_result_rows = 10000     # Limit result size
   enable_streaming = true     # Stream large results
   ```

2. **Use Connection Pooling**
   ```ini
   [database:my_db]
   pool_size = 5               # Limit concurrent connections
   pool_recycle = 1800         # Recycle connections
   ```

3. **Monitor Memory Usage**
   ```python
   import psutil
   process = psutil.Process()
   print(f"Memory usage: {process.memory_info().rss / 1024 / 1024:.1f} MB")
   ```

## Claude Integration Issues

### Issue: Claude Desktop Doesn't See MCP Server

**Symptoms:**
- MCP tools not appearing in Claude Desktop
- "No MCP servers configured" message

**Solutions:**

1. **Check Configuration File Location**
   ```bash
   # Windows
   echo %APPDATA%\Claude\claude_desktop_config.json
   
   # macOS
   echo ~/Library/Application\ Support/Claude/claude_desktop_config.json
   
   # Linux
   echo ~/.config/Claude/claude_desktop_config.json
   ```

2. **Validate JSON Configuration**
   ```bash
   # Check JSON syntax
   python -m json.tool claude_desktop_config.json
   ```

3. **Test MCP Server Directly**
   ```bash
   # Test server startup
   python -m scikiq_dbutils.mcp_server.main --test-mode
   ```

### Issue: MCP Server Startup Errors

**Symptoms:**
```
Error starting MCP server: ModuleNotFoundError
```

**Solutions:**

1. **Use Full Python Path**
   ```json
   {
     "mcpServers": {
       "scikiq-dbhandler": {
         "command": "/full/path/to/python",
         "args": ["-m", "scikiq_dbutils.mcp_server.main"]
       }
     }
   }
   ```

2. **Set Working Directory**
   ```json
   {
     "mcpServers": {
       "scikiq-dbhandler": {
         "command": "python",
         "args": ["-m", "scikiq_dbutils.mcp_server.main"],
         "cwd": "/path/to/project/directory"
       }
     }
   }
   ```

3. **Check Environment Variables**
   ```json
   {
     "mcpServers": {
       "scikiq-dbhandler": {
         "command": "python",
         "args": ["-m", "scikiq_dbutils.mcp_server.main"],
         "env": {
           "PYTHONPATH": "/path/to/modules",
           "DBHANDLER_MASTER_PASSWORD": "your-password"
         }
       }
     }
   }
   ```

### Issue: Tools Not Responding

**Symptoms:**
- Tools appear in Claude but don't execute
- Timeout errors in Claude

**Solutions:**

1. **Enable Debug Logging**
   ```json
   {
     "mcpServers": {
       "scikiq-dbhandler": {
         "command": "python",
         "args": [
           "-m", "scikiq_dbutils.mcp_server.main",
           "--log-level", "DEBUG"
         ]
       }
     }
   }
   ```

2. **Check Log Files**
   ```bash
   # Check application logs
   tail -f ~/.scikiq_mcp/logs/dbhandler.log
   
   # Check Claude Desktop logs (macOS)
   tail -f ~/Library/Logs/Claude/main.log
   ```

3. **Test Individual Tools**
   ```bash
   # Test tool execution directly
   python -c "
   from scikiq_dbutils.mcp_server.tools import list_database_connections
   result = list_database_connections({})
   print(result)
   "
   ```

## Security and Authentication

### Issue: Credential Encryption Errors

**Symptoms:**
```
CryptographyError: Invalid token or master password
```

**Solutions:**

1. **Verify Master Password**
   ```bash
   # Test master password
   python -c "
   import os
   from scikiq_dbutils.mcp_server.security import CredentialManager
   password = os.environ.get('DBHANDLER_MASTER_PASSWORD')
   if password:
       print('Master password is set')
   else:
       print('Master password not found')
   "
   ```

2. **Re-encrypt Credentials**
   ```bash
   # Re-encrypt with new master password
   python -c "
   from scikiq_dbutils.mcp_server.security import CredentialManager
   cm = CredentialManager()
   encrypted = cm.encrypt_credential('your-database-password')
   print('New encrypted password:', encrypted.decode())
   "
   ```

3. **Check Environment Variable Scope**
   ```bash
   # Ensure environment variable is available to the process
   export DBHANDLER_MASTER_PASSWORD="your-master-password"
   python -m scikiq_dbutils.mcp_server.main
   ```

### Issue: Rate Limiting Problems

**Symptoms:**
```
RateLimitError: Too many requests (100/hour limit exceeded)
```

**Solutions:**

1. **Adjust Rate Limits**
   ```ini
   [rate_limiting]
   enabled = true
   max_requests = 200          # Increase limit
   window_minutes = 60
   burst_allowance = 20        # Allow bursts
   ```

2. **Monitor Usage Patterns**
   ```python
   # Check current rate limit status
   from scikiq_dbutils.mcp_server.security import RateLimiter
   limiter = RateLimiter()
   status = limiter.get_status('client_id')
   print(f"Requests: {status['current']}/{status['limit']}")
   ```

3. **Implement Request Batching**
   ```python
   # Batch multiple queries together
   queries = ["SELECT 1", "SELECT 2", "SELECT 3"]
   result = execute_sql_batch('connection_name', queries)
   ```

## Platform-Specific Issues

### Windows Issues

**Issue: Path Separators in Configuration**
```
FileNotFoundError: [Errno 2] No such file or directory: 'C:Userspath o\file'
```

**Solution:**
```ini
# Use forward slashes or escaped backslashes
file_path = C:/Users/path/to/file
# or
file_path = C:\\Users\\path\\to\\file
```

**Issue: PowerShell Execution Policy**
```
Execution of scripts is disabled on this system
```

**Solution:**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### macOS Issues

**Issue: SSL Certificate Problems**
```
SSLError: [SSL: CERTIFICATE_VERIFY_FAILED]
```

**Solution:**
```bash
# Install certificates
/Applications/Python\ 3.x/Install\ Certificates.command

# Or update certificates
brew install ca-certificates
```

### Linux Issues

**Issue: Missing System Dependencies**
```
ImportError: libpq.so.5: cannot open shared object file
```

**Solution:**
```bash
# Ubuntu/Debian
sudo apt-get install libpq-dev python3-dev

# CentOS/RHEL
sudo yum install postgresql-devel python3-devel

# Or use package manager
sudo apt-get install python3-psycopg2
```

## Diagnostic Tools

### Built-in Diagnostic Commands

```bash
# Test configuration
python -m scikiq_dbutils.mcp_server.main --validate-config

# Test database connections
python -m scikiq_dbutils.mcp_server.main --test-connections

# Generate diagnostic report
python -m scikiq_dbutils.mcp_server.main --diagnostic-report

# List available tools
python -m scikiq_dbutils.mcp_server.main --list-tools

# Check system requirements
python -m scikiq_dbutils.mcp_server.main --system-check
```

### Manual Diagnostics

1. **Check Python Environment**
   ```python
   import sys
   print(f"Python version: {sys.version}")
   print(f"Python path: {sys.executable}")
   print(f"Module search paths: {sys.path}")
   ```

2. **Test Database Connectivity**
   ```python
   # PostgreSQL
   import psycopg2
   conn = psycopg2.connect(host='hostname', database='db', user='user', password='pass')
   
   # MySQL
   import pymysql
   conn = pymysql.connect(host='hostname', database='db', user='user', password='pass')
   ```

3. **Check File Permissions**
   ```bash
   # Check configuration file
   ls -la config.ini
   
   # Check log directory
   ls -la ~/.scikiq_mcp/logs/
   
   # Check SSL certificates
   ls -la /path/to/ssl/certificates/
   ```

### Log Analysis

**Enable Verbose Logging:**
```ini
[logging]
level = DEBUG
structured = true
handlers = file,console

[logging.file]
filename = ~/.scikiq_mcp/logs/debug.log
max_bytes = 50000000
backup_count = 10
```

**Common Log Patterns:**
```bash
# Connection issues
grep -i "connection" ~/.scikiq_mcp/logs/dbhandler.log

# Authentication problems
grep -i "auth" ~/.scikiq_mcp/logs/dbhandler.log

# Query execution
grep -i "query" ~/.scikiq_mcp/logs/dbhandler.log

# Performance issues
grep -i "slow\|timeout" ~/.scikiq_mcp/logs/dbhandler.log
```

## Getting Help

### Information to Collect

When seeking support, please collect:

1. **System Information**
   ```bash
   python --version
   pip list | grep -i scikiq
   uname -a  # Linux/macOS
   ```

2. **Configuration (sanitized)**
   ```bash
   # Remove sensitive information before sharing
   cat config.ini | sed 's/password.*/password=REDACTED/'
   ```

3. **Error Logs**
   ```bash
   # Recent error logs
   tail -100 ~/.scikiq_mcp/logs/dbhandler.log
   ```

4. **Claude Desktop Configuration**
   ```bash
   # Sanitized Claude config
   cat claude_desktop_config.json | jq '.mcpServers'
   ```

### Support Channels

- 📧 **Email Support**: support@scikiq.com
- 🐛 **GitHub Issues**: https://github.com/scikiq/scikiq-dbhandler-mcp/issues
- 📖 **Documentation**: https://docs.scikiq.com/dbhandler-mcp
- 💬 **Community Forum**: https://community.scikiq.com

### Creating Effective Bug Reports

1. **Use the Bug Report Template**
2. **Provide Minimal Reproduction Steps**
3. **Include System Information**
4. **Attach Relevant Logs** (sanitized)
5. **Specify Expected vs Actual Behavior**

---

This troubleshooting guide covers the most common issues. If you encounter a problem not covered here, please refer to the specific documentation sections or contact support with detailed information about your issue.