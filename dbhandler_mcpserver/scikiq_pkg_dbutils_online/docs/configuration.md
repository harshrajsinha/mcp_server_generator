# Configuration Guide

This comprehensive guide covers all aspects of configuring the ScikiQ Database Handler MCP Connector.

## Table of Contents
- [Configuration Files](#configuration-files)
- [Database Connections](#database-connections)
- [Security Settings](#security-settings)
- [Performance Tuning](#performance-tuning)
- [Logging Configuration](#logging-configuration)
- [Advanced Configuration](#advanced-configuration)

## Configuration Files

The connector supports multiple configuration formats to suit different deployment scenarios.

### Configuration File Locations

The connector searches for configuration files in the following order:

1. File specified by `--config-file` argument
2. `./config.ini` (current directory)
3. `~/.scikiq_mcp/config.ini` (user home directory)
4. `/etc/scikiq_mcp/config.ini` (system-wide, Linux/macOS)

### INI Format Configuration

The default configuration format uses INI files for easy editing:

```ini
# config.ini - Sample configuration file

[general]
# Master password for credential encryption
master_password_env = DBHANDLER_MASTER_PASSWORD
# Default timeout for database operations (seconds)
default_timeout = 30
# Maximum number of concurrent connections
max_connections = 10
# Enable performance monitoring
enable_monitoring = true

[logging]
# Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
level = INFO
# Log file path (optional, logs to console if not specified)
file = ~/.scikiq_mcp/logs/dbhandler.log
# Maximum log file size (MB)
max_file_size = 10
# Number of backup files to keep
backup_count = 5
# Enable structured logging (JSON format)
structured = true

[rate_limiting]
# Enable rate limiting
enabled = true
# Maximum requests per window
max_requests = 100
# Time window in minutes
window_minutes = 60

[security]
# Enable SQL injection protection
sql_injection_protection = true
# Allowed hosts for connections (comma-separated)
allowed_hosts = localhost,127.0.0.1,*.mycompany.com
# Require SSL/TLS for remote connections
require_ssl = true
# Connection timeout (seconds)
connection_timeout = 10

[cache]
# Enable query result caching
enabled = true
# Cache TTL in seconds
ttl = 300
# Maximum cache size (MB)
max_size = 100

# Database connection examples
[database:mysql_prod]
type = mysql
host = prod-mysql.company.com
port = 3306
database = analytics
username = readonly_user
# Encrypted password (use encrypt_password tool to generate)
password_encrypted = gAAAAABhZ...
# Or use environment variable
password_env = MYSQL_PROD_PASSWORD
ssl_mode = required
ssl_ca = /path/to/ca-cert.pem
connection_params = {"charset": "utf8mb4", "autocommit": true}

[database:postgres_staging]
type = postgresql
host = staging-postgres.company.com
port = 5432
database = testdb
username = test_user
password_env = POSTGRES_STAGING_PASSWORD
ssl_mode = prefer
pool_size = 5
pool_timeout = 30

[database:snowflake_warehouse]
type = snowflake
account = mycompany.snowflakecomputing.com
warehouse = ANALYTICS_WH
database = PRODUCTION
schema = PUBLIC
username = analytics_user
password_env = SNOWFLAKE_PASSWORD
role = ANALYST_ROLE
```

### JSON Format Configuration

For programmatic configuration management:

```json
{
  "general": {
    "master_password_env": "DBHANDLER_MASTER_PASSWORD",
    "default_timeout": 30,
    "max_connections": 10,
    "enable_monitoring": true
  },
  "logging": {
    "level": "INFO",
    "file": "~/.scikiq_mcp/logs/dbhandler.log",
    "max_file_size": 10,
    "backup_count": 5,
    "structured": true
  },
  "rate_limiting": {
    "enabled": true,
    "max_requests": 100,
    "window_minutes": 60
  },
  "security": {
    "sql_injection_protection": true,
    "allowed_hosts": ["localhost", "127.0.0.1", "*.mycompany.com"],
    "require_ssl": true,
    "connection_timeout": 10
  },
  "databases": {
    "mysql_prod": {
      "type": "mysql",
      "host": "prod-mysql.company.com",
      "port": 3306,
      "database": "analytics",
      "username": "readonly_user",
      "password_encrypted": "gAAAAABhZ...",
      "ssl_mode": "required",
      "ssl_ca": "/path/to/ca-cert.pem"
    }
  }
}
```

## Database Connections

### Supported Database Types

The connector supports the following database types:

| Database | Type Key | Driver |
|----------|----------|---------|
| MySQL/MariaDB | `mysql` | pymysql |
| PostgreSQL | `postgresql` | psycopg2 |
| Oracle | `oracle` | cx_Oracle |
| SQL Server | `sqlserver` | pyodbc |
| MongoDB | `mongodb` | pymongo |
| Snowflake | `snowflake` | snowflake-connector-python |
| BigQuery | `bigquery` | google-cloud-bigquery |
| Redshift | `redshift` | redshift-connector |
| DB2 | `db2` | ibm_db |
| Teradata | `teradata` | teradataml |
| Vertica | `vertica` | vertica-python |
| Hive | `hive` | pyhive |
| Athena | `athena` | PyAthena |
| SAPHana | `saphana` | hdbcli |
| NetezzaHandler | `netezza` | nzpy |
| ChromaDB | `chromadb` | chromadb |
| DuckDB | `duckdb` | duckdb |

### Connection Parameters

#### MySQL/MariaDB Configuration
```ini
[database:mysql_example]
type = mysql
host = mysql-server.company.com
port = 3306
database = mydb
username = myuser
password_env = MYSQL_PASSWORD
# MySQL-specific options
ssl_mode = required  # disabled, preferred, required, verify_ca, verify_identity
ssl_ca = /path/to/ca.pem
ssl_cert = /path/to/client-cert.pem
ssl_key = /path/to/client-key.pem
charset = utf8mb4
autocommit = true
connection_params = {"connect_timeout": 10, "read_timeout": 30}
```

#### PostgreSQL Configuration
```ini
[database:postgres_example]
type = postgresql
host = postgres-server.company.com
port = 5432
database = mydb
username = myuser
password_env = POSTGRES_PASSWORD
# PostgreSQL-specific options
ssl_mode = require  # disable, allow, prefer, require, verify-ca, verify-full
ssl_ca = /path/to/ca.pem
ssl_cert = /path/to/client-cert.pem
ssl_key = /path/to/client-key.pem
application_name = scikiq_mcp_connector
# Connection pooling
pool_size = 5
pool_timeout = 30
pool_recycle = 3600
```

#### Oracle Database Configuration
```ini
[database:oracle_example]
type = oracle
host = oracle-server.company.com
port = 1521
service_name = ORCL
# Or use SID instead of service_name
# sid = ORCL
username = myuser
password_env = ORACLE_PASSWORD
# Oracle-specific options
encoding = UTF-8
nencoding = UTF-8
# For Oracle Wallet
wallet_location = /path/to/wallet
wallet_password_env = WALLET_PASSWORD
# Connection pooling
pool_min = 2
pool_max = 10
pool_increment = 1
```

#### SQL Server Configuration
```ini
[database:sqlserver_example]
type = sqlserver
host = sqlserver.company.com
port = 1433
database = MyDatabase
username = myuser
password_env = SQLSERVER_PASSWORD
# SQL Server-specific options
driver = ODBC Driver 17 for SQL Server
trusted_connection = false
encrypt = true
trust_server_certificate = false
connection_timeout = 30
command_timeout = 30
```

#### MongoDB Configuration
```ini
[database:mongo_example]
type = mongodb
host = mongo-cluster.company.com
port = 27017
database = mydb
username = myuser
password_env = MONGO_PASSWORD
# MongoDB-specific options
auth_source = admin
replica_set = rs0
read_preference = secondaryPreferred
ssl = true
ssl_ca_certs = /path/to/ca.pem
ssl_certfile = /path/to/client.pem
```

#### DuckDB Configuration
```ini
# Local DuckDB (file-based or in-memory)
[database:duckdb_local]
type = duckdb
database_path = /path/to/database.duckdb  # or ":memory:" for in-memory
enable_s3 = false

# DuckDB with S3 storage support
[database:duckdb_s3]
type = duckdb
database_path = :memory:
enable_s3 = true
s3_bucket = my-data-warehouse
s3_prefix = tables/
s3_region = us-east-1
s3_access_key_id_env = AWS_ACCESS_KEY_ID
s3_secret_access_key_env = AWS_SECRET_ACCESS_KEY
default_file_format = parquet
# DuckDB-specific options
# Folders in S3 bucket are treated as tables
# Supports parquet, csv, json file formats
# Automatic schema detection and parallel processing
```

#### Cloud Database Configurations

##### Snowflake
```ini
[database:snowflake_example]
type = snowflake
account = mycompany.snowflakecomputing.com
warehouse = COMPUTE_WH
database = ANALYTICS
schema = PUBLIC
username = analyst
password_env = SNOWFLAKE_PASSWORD
role = ANALYST_ROLE
# Snowflake-specific options
authenticator = snowflake  # or externalbrowser, oauth, jwt
private_key_file = /path/to/rsa_key.p8
private_key_passphrase_env = SNOWFLAKE_KEY_PASSPHRASE
client_session_keep_alive = true
```

##### BigQuery
```ini
[database:bigquery_example]
type = bigquery
project_id = my-gcp-project
# Authentication methods:
# 1. Service account key file
credentials_file = /path/to/service-account.json
# 2. Application default credentials (preferred for GCP)
use_default_credentials = true
# 3. Service account key (base64 encoded)
credentials_base64_env = BIGQUERY_CREDENTIALS_B64
# BigQuery-specific options
location = US
maximum_bytes_billed = 1000000000
```

##### Redshift
```ini
[database:redshift_example]
type = redshift
host = redshift-cluster.region.redshift.amazonaws.com
port = 5439
database = analytics
username = analyst
password_env = REDSHIFT_PASSWORD
# Redshift-specific options
ssl = true
cluster_identifier = my-cluster
region = us-west-2
# IAM authentication
use_iam = true
cluster_db_user = iam_user
```

## Security Settings

### Password Management

#### Environment Variables (Recommended)
```ini
[database:secure_db]
type = postgresql
host = secure-db.company.com
username = myuser
password_env = SECURE_DB_PASSWORD
```

Set the environment variable:
```bash
export SECURE_DB_PASSWORD="your-secure-password"
```

#### Encrypted Passwords
Use the built-in encryption tool to encrypt passwords:

```bash
# Generate encrypted password
python -c "
from scikiq_dbutils.mcp_server.security import CredentialManager
cm = CredentialManager()
encrypted = cm.encrypt_credential('your-password')
print('Encrypted password:', encrypted.decode())
"
```

Then use in configuration:
```ini
[database:encrypted_db]
type = mysql
host = mysql.company.com
username = myuser
password_encrypted = gAAAAABhZ1Z2X3YmZGVmZ...
```

### SSL/TLS Configuration

#### Certificate-Based Authentication
```ini
[database:ssl_db]
type = postgresql
host = secure-postgres.company.com
ssl_mode = require
ssl_ca = /path/to/ca-certificate.pem
ssl_cert = /path/to/client-certificate.pem
ssl_key = /path/to/client-key.pem
ssl_key_password_env = SSL_KEY_PASSWORD
```

#### Host Validation
Configure allowed hosts to prevent unauthorized connections:

```ini
[security]
allowed_hosts = localhost,127.0.0.1,*.company.com,10.0.0.0/8
blocked_hosts = suspicious-host.com,192.168.1.100
```

### Rate Limiting

Configure rate limiting to prevent abuse:

```ini
[rate_limiting]
enabled = true
max_requests = 100
window_minutes = 60
# Per-user limits (if authentication is enabled)
per_user_max_requests = 20
# Burst allowance
burst_allowance = 10
```

## Performance Tuning

### Connection Pooling

Configure connection pools for better performance:

```ini
[database:pooled_db]
type = postgresql
host = postgres.company.com
# Connection pool settings
pool_size = 5          # Number of persistent connections
pool_timeout = 30      # Timeout to get connection from pool
pool_recycle = 3600    # Recycle connections after 1 hour
pool_pre_ping = true   # Validate connections before use
```

### Query Optimization

Configure query limits and timeouts:

```ini
[general]
# Default query timeout
default_timeout = 30
# Maximum rows returned per query
max_result_rows = 10000
# Query execution timeout
query_timeout = 300
# Enable query result compression
enable_compression = true
```

### Caching Configuration

Enable caching for better performance:

```ini
[cache]
enabled = true
# Cache backend: memory, redis, filesystem
backend = memory
# Cache TTL in seconds
ttl = 300
# Maximum cache size (MB)
max_size = 100
# Cache key prefix
key_prefix = scikiq_mcp
# Redis configuration (if using Redis backend)
redis_host = localhost
redis_port = 6379
redis_db = 0
redis_password_env = REDIS_PASSWORD
```

## Logging Configuration

### Basic Logging Setup

```ini
[logging]
level = INFO
file = ~/.scikiq_mcp/logs/dbhandler.log
max_file_size = 10
backup_count = 5
```

### Advanced Logging Configuration

```ini
[logging]
level = INFO
# Multiple log handlers
handlers = file,console,syslog
# File handler configuration
file_handler_file = ~/.scikiq_mcp/logs/dbhandler.log
file_handler_level = INFO
file_handler_max_bytes = 10485760  # 10MB
file_handler_backup_count = 5
file_handler_format = %(asctime)s - %(name)s - %(levelname)s - %(message)s
# Console handler configuration
console_handler_level = WARNING
console_handler_format = %(levelname)s: %(message)s
# Syslog handler configuration (Linux/macOS)
syslog_handler_address = /dev/log
syslog_handler_facility = LOG_LOCAL0
# Structured logging (JSON format)
structured = true
structured_format = {"timestamp": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s", "module": "%(name)s"}
```

### Log Levels

| Level | Description | Use Case |
|-------|-------------|----------|
| DEBUG | Detailed diagnostic information | Development, troubleshooting |
| INFO | General operational messages | Normal operation monitoring |
| WARNING | Warning messages for unusual conditions | Monitoring potential issues |
| ERROR | Error messages for serious problems | Error tracking and alerting |
| CRITICAL | Critical errors that may stop operation | Emergency alerts |

## Advanced Configuration

### Environment-Specific Configurations

Use different configurations for different environments:

```ini
# config.ini
[general]
environment = ${ENVIRONMENT:development}
include_configs = ${environment}_config.ini

# development_config.ini
[logging]
level = DEBUG
[cache]
enabled = false

# production_config.ini
[logging]
level = WARNING
[cache]
enabled = true
ttl = 600
```

### Dynamic Configuration

Enable dynamic configuration reloading:

```ini
[general]
# Enable configuration file monitoring
config_auto_reload = true
# Check interval in seconds
config_reload_interval = 60
```

### Custom Connection Factories

For complex connection scenarios:

```ini
[database:custom_db]
type = custom
factory_class = mycompany.db.CustomConnectionFactory
factory_params = {"param1": "value1", "param2": "value2"}
```

### Monitoring Integration

Configure monitoring and metrics:

```ini
[monitoring]
enabled = true
# Metrics backend: prometheus, statsd, influxdb
backend = prometheus
# Prometheus configuration
prometheus_port = 8090
prometheus_path = /metrics
# StatsD configuration
statsd_host = localhost
statsd_port = 8125
statsd_prefix = scikiq.mcp
# Custom metrics
custom_metrics = query_duration,connection_count,error_rate
```

## Configuration Validation

### Validate Configuration File

```bash
# Validate configuration syntax
python -m scikiq_dbutils.mcp_server.main --validate-config config.ini

# Test database connections
python -m scikiq_dbutils.mcp_server.main --test-connections config.ini

# Generate configuration documentation
python -m scikiq_dbutils.mcp_server.main --config-docs > config_reference.md
```

### Configuration Schema

The connector uses JSON Schema for configuration validation. View the schema:

```bash
python -c "
from scikiq_dbutils.mcp_server.config import ConfigValidator
validator = ConfigValidator()
print(validator.get_schema_documentation())
"
```

## Troubleshooting

### Common Configuration Issues

#### Issue: "Configuration file not found"
```bash
# Check file exists and permissions
ls -la config.ini
# Use absolute path
python -m scikiq_dbutils.mcp_server.main --config-file /full/path/to/config.ini
```

#### Issue: "Invalid configuration format"
```bash
# Validate INI syntax
python -c "
import configparser
config = configparser.ConfigParser()
config.read('config.ini')
print('Configuration is valid')
"
```

#### Issue: "Database connection failed"
```bash
# Test individual connection
python -c "
from scikiq_dbutils.mcp_server.config import DatabaseConfig
config = DatabaseConfig.from_file('config.ini')
conn = config.get_connection('mysql_prod')
print('Connection successful:', conn.test_connection())
"
```

### Debug Configuration

Enable debug mode for detailed configuration logging:

```ini
[logging]
level = DEBUG
[general]
debug_config = true
```

## Security Best Practices

1. **Never store plaintext passwords** in configuration files
2. **Use environment variables** for sensitive data
3. **Enable SSL/TLS** for all remote connections
4. **Limit database user permissions** to minimum required
5. **Regularly rotate credentials** and update encrypted passwords
6. **Use connection pooling** to limit concurrent connections
7. **Configure rate limiting** to prevent abuse
8. **Monitor connection attempts** and failed authentications
9. **Keep configuration files secure** with appropriate file permissions
10. **Use configuration validation** to catch errors early

## Configuration Management

### Version Control

Store configuration templates in version control:

```bash
# config.template.ini
[database:prod_db]
type = postgresql
host = ${DB_HOST}
port = ${DB_PORT:5432}
database = ${DB_NAME}
username = ${DB_USER}
password_env = DB_PASSWORD
```

### Configuration Deployment

Use configuration management tools:

```bash
# Ansible example
- name: Deploy MCP configuration
  template:
    src: config.template.ini
    dest: /etc/scikiq_mcp/config.ini
    mode: '0600'
  vars:
    db_host: "{{ production_db_host }}"
    db_name: "{{ production_db_name }}"
```

### Environment Variables Reference

| Variable | Description | Default |
|----------|-------------|---------|
| `DBHANDLER_MASTER_PASSWORD` | Master password for encryption | Required |
| `LOG_LEVEL` | Logging level | INFO |
| `RATE_LIMIT_MAX_REQUESTS` | Rate limit max requests | 100 |
| `RATE_LIMIT_WINDOW_MINUTES` | Rate limit window | 60 |
| `CONFIG_FILE` | Configuration file path | config.ini |
| `ENABLE_MONITORING` | Enable monitoring | false |
| `CACHE_ENABLED` | Enable caching | true |
| `SSL_VERIFY` | Verify SSL certificates | true |

---

This completes the configuration guide. For additional help, see the [Troubleshooting Guide](troubleshooting.md) or contact support.