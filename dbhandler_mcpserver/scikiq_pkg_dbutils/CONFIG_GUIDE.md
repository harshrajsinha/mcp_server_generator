# ScikiQ Database MCP Server - Configuration Guide

The ScikiQ Database MCP Server supports two configuration formats:

## 1. Environment File Configuration (.env)

Use the `--env-file` argument to load database configurations from an environment file:

```bash
python -m scikiq_dbutils.mcp_server.main --env-file /path/to/.env
```

## 2. INI Configuration File (.ini)

Use the `--config-file` argument to load database configurations from an INI file:

```bash
python -m scikiq_dbutils.mcp_server.main --config-file /path/to/config.ini
```

### INI Configuration Format

The INI configuration file uses sections to define database connections. Each section should start with `database.` followed by a unique connection name:

```ini
[database.connection_name]
db_type = DATABASE_TYPE
host = hostname
port = port_number
database = database_name
username = username
password = password
password_encrypted = 0
```

### Supported Database Types

- `MYSQL` - MySQL/MariaDB databases
- `POSTGRES` - PostgreSQL databases  
- `ORACLE` - Oracle databases
- `SQLSERVER` - Microsoft SQL Server
- `MONGODB` - MongoDB databases
- `SNOWFLAKE` - Snowflake data warehouse
- `BIGQUERY` - Google BigQuery
- `REDSHIFT` - Amazon Redshift
- `ATHENA` - Amazon Athena
- `SAPHANA` - SAP HANA
- `VERTICA` - HP Vertica
- `DB2` - IBM DB2
- `TERADATA` - Teradata

### Configuration Parameters

| Parameter | Description | Required | Example |
|-----------|-------------|----------|---------|
| `db_type` | Database type (see supported types above) | ✓ | `MYSQL` |
| `host` | Database hostname/IP address | ✓ | `localhost` |
| `port` | Database port number | ✓ | `3306` |
| `database` | Database/schema name | ✓ | `mydb` |
| `username` | Database username | ✓ | `user` |
| `password` | Database password | ✓ | `password123` |
| `password_encrypted` | Password encryption flag (0=plain, 1=base64) | | `0` |
| `schema` | Default schema name | | `public` |
| `service_name` | Oracle service name | | `ORCL` |

### SSL Configuration

For SSL-enabled connections, add SSL parameters:

```ini
[database.secure_postgres]
db_type = POSTGRES
host = secure-db.example.com
port = 5432
database = production_db
username = app_user
password = cGFzc3dvcmQxMjM=
password_encrypted = 1
ssl_mode = require
ssl_cert = /path/to/client-cert.pem
ssl_key = /path/to/client-key.pem
ssl_ca = /path/to/ca-cert.pem
```

### SSH Tunnel Configuration

For connections through SSH tunnels:

```ini
[database.ssh_mysql]
db_type = MYSQL
host = 127.0.0.1
port = 3307
database = remote_db
username = db_user
password = db_pass
password_encrypted = 0
ssh_host = bastion.example.com
ssh_port = 22
ssh_username = ssh_user
ssh_key_file = /path/to/ssh/private/key
```

### Password Encryption

The `password_encrypted` parameter controls how passwords are handled:

- `0` (default): Password is stored in plain text
- `1`: Password is base64 encoded

To encode a password in base64:

```python
import base64
encoded = base64.b64encode("mypassword".encode()).decode()
print(encoded)  # bXlwYXNzd29yZA==
```

### Example Complete Configuration

```ini
# MySQL Local Development
[database.mysql_dev]
db_type = MYSQL
host = localhost
port = 3306
database = development
username = dev_user
password = dev_pass
password_encrypted = 0

# PostgreSQL Production with SSL
[database.postgres_prod]
db_type = POSTGRES
host = prod-db.example.com
port = 5432
database = production
username = prod_user
password = cHJvZF9wYXNz
password_encrypted = 1
ssl_mode = require
ssl_cert = /etc/ssl/certs/client.pem
ssl_key = /etc/ssl/private/client-key.pem
ssl_ca = /etc/ssl/certs/ca.pem

# Oracle with Service Name
[database.oracle_test]
db_type = ORACLE
host = oracle.example.com
port = 1521
database = ORCL
username = test_user
password = dGVzdF9wYXNz
password_encrypted = 1
service_name = ORCL

# MySQL through SSH Tunnel
[database.mysql_ssh]
db_type = MYSQL
host = 127.0.0.1
port = 3307
database = internal_db
username = internal_user
password = internal_pass
password_encrypted = 0
ssh_host = bastion.company.com
ssh_port = 22
ssh_username = ssh_user
ssh_key_file = ~/.ssh/id_rsa
```

### Commands

- **Validate Configuration**: `--validate-env --config-file config.ini`
- **List Connections**: `--list-connections --config-file config.ini`
- **Show Available Tools**: `--help-tools --config-file config.ini`
- **Start MCP Server**: `--config-file config.ini`

### Migration from .env to .ini

The INI format provides better organization and readability compared to environment files. Both formats are supported, and you can gradually migrate your configurations.

## Sample Files

Create sample configuration files:

```bash
# Create a sample INI file
python -m scikiq_dbutils.mcp_server.main --create-sample-env sample.ini

# Create a sample .env file  
python -m scikiq_dbutils.mcp_server.main --create-sample-env sample.env
```