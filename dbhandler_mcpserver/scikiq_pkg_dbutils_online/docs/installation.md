# Installation Guide

This guide will help you install and configure the ScikiQ Database Handler MCP Connector for Claude AI.

## System Requirements

### Minimum Requirements
- Python 3.9 or higher
- 2GB RAM
- 1GB free disk space
- Internet connection for package downloads

### Supported Operating Systems
- Windows 10/11
- macOS 10.15+ (Catalina or later)
- Linux (Ubuntu 18.04+, CentOS 7+, or equivalent)

### Supported Claude Versions
- Claude Desktop (latest version)
- Claude API access

## Installation Methods

### Method 1: pip Installation (Recommended)

This is the easiest and most reliable installation method.

```bash
# Install the connector
pip install scikiq-dbhandler-mcp

# Verify installation
scikiq-dbhandler-mcp --version
```

### Method 2: From Source

For development or customization purposes.

```bash
# Clone the repository
git clone https://github.com/scikiq/scikiq-dbhandler-mcp.git
cd scikiq-dbhandler-mcp

# Install in development mode
pip install -e .

# Or install normally
pip install .
```

### Method 3: Docker Installation

For containerized deployments.

```bash
# Pull the Docker image
docker pull scikiq/dbhandler-mcp:latest

# Run the container
docker run -d \
  --name scikiq-dbhandler \
  -e DBHANDLER_MASTER_PASSWORD="your-password" \
  -p 8000:8000 \
  scikiq/dbhandler-mcp:latest
```

## Database Driver Installation

The connector supports many databases. Install the specific drivers you need:

### MySQL/MariaDB
```bash
pip install pymysql
# or
pip install mysqlclient
```

### PostgreSQL
```bash
pip install psycopg2-binary
# or for from-source compilation
pip install psycopg2
```

### Oracle
```bash
pip install cx-Oracle
# Note: Requires Oracle Instant Client
```

### SQL Server
```bash
pip install pyodbc
# Note: Requires ODBC driver
```

### MongoDB
```bash
pip install pymongo
```

### Cloud Databases
```bash
# Snowflake
pip install snowflake-connector-python

# BigQuery
pip install google-cloud-bigquery

# Redshift
pip install redshift-connector
```

### All Drivers (Complete Installation)
```bash
pip install scikiq-dbhandler-mcp[all]
```

## Claude Desktop Configuration

### Step 1: Locate Claude Config File

Find your Claude Desktop configuration file:

**Windows:**
```
%APPDATA%\Claude\claude_desktop_config.json
```

**macOS:**
```
~/Library/Application Support/Claude/claude_desktop_config.json
```

**Linux:**
```
~/.config/Claude/claude_desktop_config.json
```

### Step 2: Add MCP Server Configuration

Edit the configuration file and add the ScikiQ Database Handler:

```json
{
  "mcpServers": {
    "scikiq-dbhandler": {
      "command": "python",
      "args": ["-m", "scikiq_dbutils.mcp_server.main"],
      "env": {
        "DBHANDLER_MASTER_PASSWORD": "your-secure-master-password-here"
      }
    }
  }
}
```

### Step 3: Advanced Configuration (Optional)

For advanced use cases, you can specify additional options:

```json
{
  "mcpServers": {
    "scikiq-dbhandler": {
      "command": "python",
      "args": [
        "-m", "scikiq_dbutils.mcp_server.main",
        "--config-file", "/path/to/your/config.ini",
        "--log-level", "INFO"
      ],
      "env": {
        "DBHANDLER_MASTER_PASSWORD": "your-secure-master-password",
        "LOG_LEVEL": "INFO",
        "RATE_LIMIT_MAX_REQUESTS": "100",
        "RATE_LIMIT_WINDOW_MINUTES": "60"
      },
      "cwd": "/path/to/working/directory"
    }
  }
}
```

### Step 4: Restart Claude Desktop

After editing the configuration file, restart Claude Desktop for the changes to take effect.

## Environment Setup

### Setting Up Master Password

The master password is used to encrypt database credentials securely.

#### Option 1: Environment Variable
```bash
export DBHANDLER_MASTER_PASSWORD="your-secure-password"
```

#### Option 2: Generate Secure Password
```bash
python -c "
from scikiq_dbutils.mcp_server.security import CredentialManager
print('Generated password:', CredentialManager().generate_master_password())
"
```

#### Option 3: .env File
Create a `.env` file in your working directory:

```bash
# .env
DBHANDLER_MASTER_PASSWORD=your-secure-master-password
LOG_LEVEL=INFO
RATE_LIMIT_MAX_REQUESTS=100
RATE_LIMIT_WINDOW_MINUTES=60
```

### Creating Configuration Directory

Create a dedicated configuration directory:

```bash
# Windows
mkdir %USERPROFILE%\.scikiq_mcp

# macOS/Linux
mkdir ~/.scikiq_mcp
```

## Database-Specific Setup

### Oracle Database Setup

1. **Install Oracle Instant Client**
   
   Download from: https://www.oracle.com/database/technologies/instant-client.html

2. **Set Environment Variables**
   ```bash
   export ORACLE_HOME=/path/to/instantclient
   export LD_LIBRARY_PATH=$ORACLE_HOME:$LD_LIBRARY_PATH
   ```

3. **Test Connection**
   ```bash
   python -c "import cx_Oracle; print('Oracle client version:', cx_Oracle.clientversion())"
   ```

### SQL Server Setup

1. **Install ODBC Driver**
   
   **Windows:** Download from Microsoft
   
   **Linux:**
   ```bash
   # Ubuntu/Debian
   curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add -
   curl https://packages.microsoft.com/config/ubuntu/20.04/prod.list > /etc/apt/sources.list.d/mssql-release.list
   apt-get update
   apt-get install msodbcsql17
   
   # CentOS/RHEL
   curl https://packages.microsoft.com/config/rhel/8/prod.repo > /etc/yum.repos.d/mssql-release.repo
   yum install msodbcsql17
   ```

2. **Test Connection**
   ```bash
   python -c "import pyodbc; print('ODBC drivers:', pyodbc.drivers())"
   ```

### MongoDB Setup

1. **Install MongoDB Client Tools (Optional)**
   ```bash
   # For additional utilities
   pip install motor  # Async driver
   ```

2. **Authentication Setup**
   - Ensure MongoDB user has appropriate permissions
   - Configure authentication mechanism if needed

## Verification

### Step 1: Test Installation

```bash
# Check if the package is installed
python -c "import scikiq_dbutils; print('Installation successful')"

# Check version
scikiq-dbhandler-mcp --version
```

### Step 2: Test MCP Server

```bash
# Test server startup
python -m scikiq_dbutils.mcp_server.main --help

# Test with sample configuration
python -m scikiq_dbutils.mcp_server.main --create-sample-env sample.ini
python -m scikiq_dbutils.mcp_server.main --validate-env --config-file sample.ini
```

### Step 3: Test Claude Integration

1. **Start Claude Desktop**
2. **Create a new conversation**
3. **Test basic commands:**

```
List available MCP servers
```

```
Show me the available database tools
```

If you see the ScikiQ Database Handler tools listed, your installation is successful!

## Troubleshooting

### Common Issues

#### Issue: "Command not found: python"
**Solution:**
- Use `python3` instead of `python`
- Or update your configuration to use `python3`

#### Issue: "Module not found: scikiq_dbutils"
**Solutions:**
1. Reinstall the package: `pip install --upgrade scikiq-dbhandler-mcp`
2. Check Python path: `python -c "import sys; print(sys.path)"`
3. Use full path in configuration

#### Issue: "Permission denied" errors
**Solutions:**
1. Install with user flag: `pip install --user scikiq-dbhandler-mcp`
2. Use virtual environment
3. Run with administrator/sudo privileges

#### Issue: Claude doesn't see the connector
**Solutions:**
1. Check configuration file syntax with JSON validator
2. Restart Claude Desktop completely
3. Check Claude logs for error messages
4. Verify file paths are correct

### Database Connection Issues

#### MySQL Connection Problems
```bash
# Test MySQL connectivity
telnet mysql-host 3306

# Common solutions:
# - Check firewall rules
# - Verify MySQL user permissions
# - Enable remote connections in MySQL config
```

#### PostgreSQL SSL Issues
```bash
# Test SSL connection
psql "host=hostname user=username dbname=database sslmode=require"

# Check SSL certificates
openssl verify certificate.pem
```

#### Oracle TNS Issues
```bash
# Test TNS connection
tnsping your-oracle-service

# Check tnsnames.ora configuration
```

### Performance Issues

#### Slow Connections
1. Increase connection timeout in configuration
2. Check network latency
3. Optimize database server performance

#### Memory Usage
1. Reduce connection pool sizes
2. Lower query result limits
3. Enable query result caching

### Getting Help

#### Enable Debug Logging
```json
{
  "mcpServers": {
    "scikiq-dbhandler": {
      "command": "python",
      "args": ["-m", "scikiq_dbutils.mcp_server.main", "--log-level", "DEBUG"],
      "env": {
        "DBHANDLER_MASTER_PASSWORD": "your-password"
      }
    }
  }
}
```

#### Generate Diagnostic Report
```bash
python -m scikiq_dbutils.mcp_server.main --help-tools
python -m scikiq_dbutils.mcp_server.main --list-connections
```

#### Contact Support
- 📧 Email: support@scikiq.com
- 🐛 GitHub Issues: https://github.com/scikiq/scikiq-dbhandler-mcp/issues
- 📖 Documentation: https://docs.scikiq.com/dbhandler-mcp

## Next Steps

After successful installation:

1. **Read the [Configuration Guide](configuration.md)** - Learn how to set up database connections
2. **Check the [API Reference](api_reference.md)** - Understand all available tools
3. **Try the [Examples](examples/)** - See real-world usage patterns
4. **Join our community** - Get help and share experiences

## Security Best Practices

1. **Use strong master passwords** (at least 16 characters)
2. **Store credentials securely** (use encrypted password option)
3. **Limit database user permissions** (read-only for analysis)
4. **Enable SSL/TLS** for remote connections
5. **Configure rate limiting** appropriately for your use case
6. **Regular security audits** of connections and permissions

## Updates and Maintenance

### Updating the Connector
```bash
pip install --upgrade scikiq-dbhandler-mcp
```

### Checking for Updates
```bash
pip list --outdated | grep scikiq-dbhandler-mcp
```

### Backup Configuration
Regularly backup your configuration files:
```bash
cp ~/.scikiq_mcp/config.ini ~/.scikiq_mcp/config.ini.backup.$(date +%Y%m%d)
```

---

**Installation complete!** You're now ready to use Claude AI with your databases. 🎉