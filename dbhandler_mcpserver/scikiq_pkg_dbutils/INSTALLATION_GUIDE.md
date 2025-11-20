# Installation Guide

This guide provides installation instructions for the ScikiQ Database MCP Server and its dependencies.

## Python Requirements

- **Python 3.8+** (required)
- **Python 3.9+** (recommended for best type hints support)

## Quick Start Installation

### 1. Basic Installation (MCP Server Only)

Install the core MCP server without database drivers:

```bash
pip install -r requirements-minimal.txt
```

### 2. Database-Specific Installation

Choose and install drivers for your specific databases:

#### MySQL/MariaDB
```bash
pip install -r requirements-minimal.txt
pip install -r requirements-mysql.txt
```

#### PostgreSQL
```bash
pip install -r requirements-minimal.txt  
pip install -r requirements-postgresql.txt
```

#### Cloud Databases (Snowflake, BigQuery, Redshift)
```bash
pip install -r requirements-minimal.txt
pip install -r requirements-cloud.txt
```

#### All Databases (Full Installation)
```bash
pip install -r requirements.txt
```

## Individual Database Driver Installation

### MySQL/MariaDB
```bash
# Option 1: C-based driver (recommended, faster)
pip install mysqlclient>=2.1.0

# Option 2: Pure Python driver (easier to install)
pip install PyMySQL>=1.0.2
```

**Note for Windows:** You may need Microsoft Visual C++ 14.0 or greater for `mysqlclient`.

### PostgreSQL
```bash
pip install psycopg2-binary>=2.9.0
```

### Oracle Database
```bash
pip install cx-Oracle>=8.3.0
```

**Note:** Requires Oracle Client libraries to be installed separately.

### Microsoft SQL Server
```bash
# Option 1: pymssql (recommended)
pip install pymssql>=2.2.5

# Option 2: pyodbc (requires ODBC drivers)
pip install pyodbc>=4.0.34
```

### MongoDB
```bash
pip install pymongo>=4.0.0
pip install dnspython>=2.2.1  # For SRV connection strings
```

### Snowflake
```bash
pip install snowflake-connector-python>=3.0.0
```

### Google BigQuery
```bash
pip install google-cloud-bigquery>=3.4.0
pip install google-auth>=2.15.0
```

### SAP HANA
```bash
pip install hdbcli>=2.16.0
```

## Platform-Specific Instructions

### Windows

1. **Install Microsoft Visual C++ 14.0+**
   - Download from Microsoft official site
   - Required for compiling some database drivers

2. **Alternative: Use conda**
   ```bash
   conda install mysqlclient psycopg2 cx_oracle pymssql
   ```

### Linux (Ubuntu/Debian)

1. **Install system dependencies:**
   ```bash
   sudo apt-get update
   sudo apt-get install python3-dev libpq-dev libmysqlclient-dev
   ```

2. **Install Python packages:**
   ```bash
   pip install -r requirements.txt
   ```

### Linux (RHEL/CentOS/Fedora)

1. **Install system dependencies:**
   ```bash
   sudo yum install python3-devel postgresql-devel mysql-devel
   # Or for newer versions:
   sudo dnf install python3-devel postgresql-devel mysql-devel
   ```

2. **Install Python packages:**
   ```bash
   pip install -r requirements.txt
   ```

### macOS

1. **Install Homebrew** (if not already installed):
   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```

2. **Install system dependencies:**
   ```bash
   brew install postgresql mysql
   ```

3. **Install Python packages:**
   ```bash
   pip install -r requirements.txt
   ```

## Virtual Environment Setup (Recommended)

### Using venv
```bash
# Create virtual environment
python -m venv scikiq_mcp_env

# Activate virtual environment
# Windows:
scikiq_mcp_env\Scripts\activate
# Linux/Mac:
source scikiq_mcp_env/bin/activate

# Install requirements
pip install -r requirements-minimal.txt
pip install -r requirements-mysql.txt  # Add other databases as needed
```

### Using conda
```bash
# Create virtual environment
conda create -n scikiq_mcp python=3.9

# Activate environment
conda activate scikiq_mcp

# Install requirements
pip install -r requirements-minimal.txt
conda install mysqlclient psycopg2 cx_oracle  # Install from conda-forge
```

## Verification

Test your installation:

```bash
# Test core MCP server
python run_mcp_server.py --help

# Test database connectivity (after setting up .env file)
python run_mcp_server.py --validate-env --env-file .env

# Create sample environment file
python run_mcp_server.py --create-sample-env .env
```

## Troubleshooting

### Common Issues

1. **"No module named 'MySQLdb'"**
   ```bash
   pip install mysqlclient
   # Or alternative:
   pip install PyMySQL
   ```

2. **"Microsoft Visual C++ 14.0 is required" (Windows)**
   - Install Visual Studio Build Tools
   - Or use conda: `conda install mysqlclient`

3. **"pg_config executable not found"**
   ```bash
   # Ubuntu/Debian:
   sudo apt-get install libpq-dev
   # RHEL/CentOS:
   sudo yum install postgresql-devel
   ```

4. **Oracle Client Libraries Not Found**
   - Install Oracle Instant Client
   - Set environment variables (ORACLE_HOME, LD_LIBRARY_PATH)

### Getting Help

1. Check the [documentation](docs/) directory
2. Verify your Python version: `python --version`
3. Check installed packages: `pip list`
4. Run diagnostic commands:
   ```bash
   python run_mcp_server.py --validate-config
   python run_mcp_server.py --help-tools
   ```

## Development Installation

For development and testing:

```bash
pip install -r requirements.txt
pip install pytest>=7.0.0 pytest-asyncio>=0.20.0
pip install black>=22.0.0 flake8>=5.0.0
pip install mypy>=0.991
```

## Docker Installation (Alternative)

If you prefer Docker:

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
CMD ["python", "run_mcp_server.py"]
```

Build and run:
```bash
docker build -t scikiq-mcp-server .
docker run -p 8080:8080 scikiq-mcp-server
```