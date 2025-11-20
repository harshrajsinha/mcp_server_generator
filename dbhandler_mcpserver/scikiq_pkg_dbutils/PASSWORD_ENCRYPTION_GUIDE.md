# Password Encryption Support in ScikiQ MCP Server

## Overview

The ScikiQ MCP Server now supports both encrypted and unencrypted passwords through a configurable encryption flag. This allows flexibility for different deployment scenarios while maintaining backward compatibility.

## Configuration

### Environment File (.env)

For each database connection, you can specify whether the password is encrypted using the `PASSWORD_ENCRYPTED` flag:

```properties
# Example with unencrypted password (recommended for MCP server)
PROD_MYSQL_DB_TYPE=MYSQL
PROD_MYSQL_HOSTNAME=163.227.93.127
PROD_MYSQL_PORT=3306
PROD_MYSQL_DATABASE=dev_skq_api
PROD_MYSQL_USERNAME=dev_update_usr
PROD_MYSQL_PASSWORD=Human5621
PROD_MYSQL_PASSWORD_ENCRYPTED=0
PROD_MYSQL_SCHEMA=public

# Example with encrypted password (base64 encoded)
PROD_MYSQL_ENCRYPTED_DB_TYPE=MYSQL
PROD_MYSQL_ENCRYPTED_HOSTNAME=163.227.93.127
PROD_MYSQL_ENCRYPTED_PORT=3306
PROD_MYSQL_ENCRYPTED_DATABASE=dev_skq_api
PROD_MYSQL_ENCRYPTED_USERNAME=dev_update_usr
PROD_MYSQL_ENCRYPTED_PASSWORD=SHVtYW41NjIx  # Base64 encoded "Human5621"
PROD_MYSQL_ENCRYPTED_PASSWORD_ENCRYPTED=1
PROD_MYSQL_ENCRYPTED_SCHEMA=public
```

### Configuration Values

- `PASSWORD_ENCRYPTED=0`: Password is stored in plain text (default for MCP server)
- `PASSWORD_ENCRYPTED=1`: Password is base64 encoded

If the `PASSWORD_ENCRYPTED` flag is not specified, it defaults to `0` (unencrypted) for MCP server usage.

## Implementation Details

### 1. DBFactory Changes

The `clsDBHandler.getInstanceByConfig()` method now checks the `password_encrypted` flag:

```python
# Check encryption flag - default to 1 (encrypted) for backward compatibility
encryption_enabled = dbconfig.get('password_encrypted', 1)
if encryption_enabled == 1:
    dbconfig["pwd"] = decodeData(dbconfig['dbpassword'])
else:
    dbconfig["pwd"] = dbconfig['dbpassword']
```

### 2. DatabaseConfig Class

Added `password_encrypted` field with default value of `0`:

```python
# Password encryption flag (0 = plain text, 1 = base64 encrypted)
password_encrypted: int = 0  # Default to 0 for MCP server (plain text)
```

### 3. Environment Parser

The environment parser now reads the `{CONNECTION_ID}_PASSWORD_ENCRYPTED` variable and sets the appropriate flag.

### 4. Automatic Encoding

The `to_dict()` method automatically handles password encoding:
- If `password_encrypted=0`: Encodes the plain text password to base64 for DBFactory
- If `password_encrypted=1`: Uses the already encoded password as-is

## Usage Examples

### For MCP Server (Recommended)

Store passwords in plain text for easier configuration management:

```properties
MYDB_DB_TYPE=MYSQL
MYDB_HOSTNAME=localhost
MYDB_PORT=3306
MYDB_DATABASE=myapp
MYDB_USERNAME=user
MYDB_PASSWORD=mypassword
MYDB_PASSWORD_ENCRYPTED=0
```

### For Production with Pre-encoded Passwords

If you have security requirements to store pre-encoded passwords:

```bash
# Encode password using Python
python -c "import base64; print(base64.b64encode(b'mypassword').decode('utf-8'))"
# Output: bXlwYXNzd29yZA==
```

Then in .env:
```properties
MYDB_DB_TYPE=MYSQL
MYDB_HOSTNAME=localhost
MYDB_PORT=3306
MYDB_DATABASE=myapp
MYDB_USERNAME=user
MYDB_PASSWORD=bXlwYXNzd29yZA==
MYDB_PASSWORD_ENCRYPTED=1
```

## Backward Compatibility

- Existing configurations without the `PASSWORD_ENCRYPTED` flag will default to unencrypted (0) for MCP server
- The DBFactory maintains backward compatibility by defaulting to encrypted (1) when the flag is not present
- All existing database handlers continue to work without modification

## Security Considerations

1. **Plain Text Storage**: While convenient for development, plain text passwords in environment files should be secured appropriately
2. **Base64 Encoding**: Note that base64 is encoding, not encryption - it provides minimal security
3. **File Permissions**: Ensure .env files have restricted permissions (600 on Unix systems)
4. **Environment Variables**: Consider using system environment variables for production deployments

## Testing

You can test password encryption functionality:

```python
from scikiq_dbutils.mcp_server.config.env_parser import EnvironmentConfigParser
from scikiq_dbutils.handlers.DBFactory import clsDBHandler

# Parse environment configuration
parser = EnvironmentConfigParser('.env')
connections = parser.parse_all_connections()
config = connections['YOUR_CONNECTION_ID']

# Check encryption flag
print(f"Password encrypted flag: {config.password_encrypted}")

# Test connection
config_dict = config.to_dict()
db_instance = clsDBHandler.getInstanceByConfig(config_dict)
test_result = db_instance.testConnection()
print(f"Connection test: {test_result}")
```