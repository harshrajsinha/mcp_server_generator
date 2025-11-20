# Publishing DBHANDLER as a Claude Connector - Complete Guide

## Table of Contents
1. [Overview](#overview)
2. [Architecture Understanding](#architecture-understanding)
3. [Preparing Your DBHANDLER](#preparing-your-dbhandler)
4. [Setting Up MCP Server](#setting-up-mcp-server)
5. [Security & Authentication](#security--authentication)
6. [Creating the Connector Package](#creating-the-connector-package)
7. [Testing](#testing)
8. [Publishing Process](#publishing-process)
9. [User Installation Guide](#user-installation-guide)
10. [Deployment Options](#deployment-options)
11. [Maintenance & Updates](#maintenance--updates)
12. [Code Examples](#code-examples)
13. [Resources](#resources)

---

## Overview

Claude connectors allow you to integrate external tools and services directly into Claude's interface, making them available for AI-assisted workflows. Your DBHANDLER would become a reusable tool that any Claude user can connect to their databases.

### What You'll Build
- A Model Context Protocol (MCP) server
- 25+ database operation tools
- Secure credential management
- Multi-database support (MySQL, PostgreSQL, Oracle, SQL Server, MongoDB, etc.)
- User-friendly configuration interface

---

## Architecture Understanding

### What is a Claude Connector?

A connector is a server that implements the Model Context Protocol (MCP), exposing tools/functions that Claude can call.

### Key Components

1. **MCP Server**: Your DBHANDLER backend that handles database operations
2. **Tool Definitions**: JSON schemas describing available functions
3. **Authentication**: Mechanism to secure database credentials
4. **Configuration UI**: User interface for setup

### Your Current Tools

Your DBHANDLER already has these tools ready:
- `db_create_connection` - Create new database connections
- `db_test_connection` - Test connection validity
- `db_close_connection` - Close connections
- `db_list_connections` - List all active connections
- `db_execute_query` - Execute SELECT queries
- `db_execute_sql` - Execute INSERT/UPDATE/DELETE/DDL
- `db_get_all_tables` - List all tables
- `db_get_table_columns` - Get column information
- `db_get_table_columns_details` - Detailed column metadata
- `db_read_table` - Read table data
- `db_get_table_details` - Comprehensive table information
- `db_get_table_relationships` - Foreign key relationships
- `db_get_column_lov` - List of values for columns
- `db_get_columns_profile` - Statistical profiling
- `db_update_column_comment` - Update column comments
- `db_generate_query` - Generate SQL queries
- `db_create_table` - Create new tables
- `db_truncate_table` - Remove all table data
- `db_create_view` - Create database views
- `db_get_incremental_columns` - Get columns for incremental loading
- `db_fetch_delta_columns` - Fetch delta columns for CDC
- `db_get_filtered_row_count` - Count rows with filters

---

## Preparing Your DBHANDLER

### Step 1: Review Current Implementation

✅ Your tools already follow MCP standards with proper JSON schemas:

```json
{
  "name": "db_create_connection",
  "description": "Create a new database connection with the specified configuration",
  "parameters": {
    "type": "object",
    "properties": {
      "connection_id": {
        "type": "string",
        "description": "Database connection identifier"
      },
      "config": {
        "type": "object",
        "properties": {
          "dbType": {"type": "string", "enum": ["MYSQL", "POSTGRES", "ORACLE", ...]},
          "hostname": {"type": "string"},
          "port": {"type": "integer"},
          "dbname": {"type": "string"},
          "dbuser": {"type": "string"},
          "dbpassword": {"type": "string"}
        }
      }
    },
    "required": ["connection_id", "config"]
  }
}
```

### Step 2: Ensure Error Handling

Make sure all tools return consistent error formats:

```python
def handle_error(error: Exception) -> dict:
    return {
        "content": f"Error: {str(error)}",
        "isError": True,
        "error_type": type(error).__name__,
        "timestamp": datetime.now().isoformat()
    }

def handle_success(data: any) -> dict:
    return {
        "content": data,
        "isError": False,
        "timestamp": datetime.now().isoformat()
    }
```

### Step 3: Add Input Validation

```python
def validate_connection_config(config: dict) -> bool:
    required_fields = ["dbType", "hostname", "dbname", "dbuser", "dbpassword"]
    
    for field in required_fields:
        if field not in config:
            raise ValueError(f"Missing required field: {field}")
    
    valid_db_types = ["MYSQL", "POSTGRES", "ORACLE", "SQLSERVER", 
                      "MONGODB", "SNOWFLAKE", "BIGQUERY", "REDSHIFT"]
    
    if config["dbType"] not in valid_db_types:
        raise ValueError(f"Invalid database type: {config['dbType']}")
    
    return True
```

---

## Setting Up MCP Server

### Option A: Python MCP Server (Recommended)

#### 1. Install Dependencies

```bash
pip install mcp>=0.1.0
pip install sqlalchemy>=2.0.0
pip install pymysql>=1.0.0
pip install psycopg2-binary>=2.9.0
pip install cx-Oracle>=8.3.0
pip install pyodbc>=4.0.0
pip install cryptography>=41.0.0
```

#### 2. Create Server Structure

```python
# server.py
import asyncio
from mcp.server import Server
from mcp.types import Tool, TextContent, Resource
from typing import Any, Sequence
import json

class DBHandlerMCP:
    def __init__(self):
        self.server = Server("dbhandler")
        self.connections = {}
        self.setup_handlers()
    
    def setup_handlers(self):
        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            return [
                Tool(
                    name="db_create_connection",
                    description="Create a new database connection with the specified configuration",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "connection_id": {
                                "type": "string",
                                "description": "Database connection identifier"
                            },
                            "config": {
                                "type": "object",
                                "properties": {
                                    "dbType": {
                                        "type": "string",
                                        "enum": ["MYSQL", "POSTGRES", "ORACLE", "SQLSERVER"],
                                        "description": "Database type"
                                    },
                                    "hostname": {
                                        "type": "string",
                                        "description": "Database hostname or IP"
                                    },
                                    "port": {
                                        "type": "integer",
                                        "description": "Database port number"
                                    },
                                    "dbname": {
                                        "type": "string",
                                        "description": "Database name"
                                    },
                                    "dbuser": {
                                        "type": "string",
                                        "description": "Database username"
                                    },
                                    "dbpassword": {
                                        "type": "string",
                                        "description": "Database password"
                                    }
                                },
                                "required": ["dbType", "hostname", "dbname", "dbuser", "dbpassword"]
                            }
                        },
                        "required": ["connection_id", "config"]
                    }
                ),
                Tool(
                    name="db_execute_query",
                    description="Execute a SELECT query and return results",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "connection_id": {
                                "type": "string",
                                "description": "Database connection identifier"
                            },
                            "query": {
                                "type": "string",
                                "description": "SQL query to execute"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum rows to return",
                                "minimum": 1
                            }
                        },
                        "required": ["connection_id", "query"]
                    }
                ),
                Tool(
                    name="db_get_all_tables",
                    description="Get a list of all tables in the database",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "connection_id": {
                                "type": "string",
                                "description": "Database connection identifier"
                            },
                            "search": {
                                "type": "string",
                                "description": "Search pattern for filtering tables"
                            }
                        },
                        "required": ["connection_id"]
                    }
                ),
                # Add all other 22+ tools here...
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict) -> Sequence[TextContent]:
            try:
                if name == "db_create_connection":
                    result = await self.create_connection(
                        arguments["connection_id"],
                        arguments["config"]
                    )
                elif name == "db_execute_query":
                    result = await self.execute_query(
                        arguments["connection_id"],
                        arguments["query"],
                        arguments.get("limit")
                    )
                elif name == "db_get_all_tables":
                    result = await self.get_all_tables(
                        arguments["connection_id"],
                        arguments.get("search")
                    )
                # Add handlers for all other tools...
                else:
                    raise ValueError(f"Unknown tool: {name}")
                
                return [TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )]
            except Exception as e:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "error": str(e),
                        "isError": True
                    }, indent=2)
                )]
    
    async def create_connection(self, connection_id: str, config: dict) -> dict:
        """Create a new database connection"""
        # Your existing implementation
        pass
    
    async def execute_query(self, connection_id: str, query: str, limit: int = None) -> dict:
        """Execute a SELECT query"""
        # Your existing implementation
        pass
    
    async def get_all_tables(self, connection_id: str, search: str = None) -> dict:
        """Get all tables in the database"""
        # Your existing implementation
        pass
    
    async def run(self):
        """Run the MCP server"""
        from mcp.server.stdio import stdio_server
        
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )

# Entry point
async def main():
    server = DBHandlerMCP()
    await server.run()

if __name__ == "__main__":
    asyncio.run(main())
```

### Option B: Node.js MCP Server

```javascript
// server.js
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";

class DBHandlerMCP {
  constructor() {
    this.server = new Server(
      {
        name: "dbhandler",
        version: "1.0.0",
      },
      {
        capabilities: {
          tools: {},
        },
      }
    );
    
    this.connections = new Map();
    this.setupHandlers();
  }

  setupHandlers() {
    this.server.setRequestHandler(ListToolsRequestSchema, async () => ({
      tools: [
        {
          name: "db_create_connection",
          description: "Create a new database connection",
          inputSchema: {
            type: "object",
            properties: {
              connection_id: { type: "string" },
              config: {
                type: "object",
                properties: {
                  dbType: { type: "string", enum: ["MYSQL", "POSTGRES", "ORACLE", "SQLSERVER"] },
                  hostname: { type: "string" },
                  port: { type: "number" },
                  dbname: { type: "string" },
                  dbuser: { type: "string" },
                  dbpassword: { type: "string" }
                }
              }
            }
          }
        },
        // Add all other tools...
      ]
    }));

    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      try {
        const { name, arguments: args } = request.params;
        
        switch (name) {
          case "db_create_connection":
            return await this.createConnection(args.connection_id, args.config);
          case "db_execute_query":
            return await this.executeQuery(args.connection_id, args.query, args.limit);
          // Handle all other tools...
          default:
            throw new Error(`Unknown tool: ${name}`);
        }
      } catch (error) {
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify({ error: error.message, isError: true })
            }
          ]
        };
      }
    });
  }

  async createConnection(connectionId, config) {
    // Implementation
  }

  async executeQuery(connectionId, query, limit) {
    // Implementation
  }

  async run() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
  }
}

// Entry point
const server = new DBHandlerMCP();
server.run().catch(console.error);
```

---

## Security & Authentication

### 1. Credential Encryption

```python
# encryption.py
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
import base64
import os

class CredentialManager:
    def __init__(self, master_password: str = None):
        self.master_password = master_password or os.getenv("MASTER_PASSWORD", "change-me")
        self.key = self._derive_key(self.master_password)
        self.cipher = Fernet(self.key)
    
    def _derive_key(self, password: str) -> bytes:
        """Derive encryption key from password"""
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'dbhandler_salt_2024',  # Use proper salt in production
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(password.encode()))
    
    def encrypt_password(self, password: str) -> str:
        """Encrypt a database password"""
        return self.cipher.encrypt(password.encode()).decode()
    
    def decrypt_password(self, encrypted_password: str) -> str:
        """Decrypt a database password"""
        return self.cipher.decrypt(encrypted_password.encode()).decode()
    
    def encrypt_config(self, config: dict) -> dict:
        """Encrypt sensitive fields in config"""
        encrypted_config = config.copy()
        if "dbpassword" in encrypted_config:
            encrypted_config["dbpassword"] = self.encrypt_password(
                encrypted_config["dbpassword"]
            )
        return encrypted_config
    
    def decrypt_config(self, config: dict) -> dict:
        """Decrypt sensitive fields in config"""
        decrypted_config = config.copy()
        if "dbpassword" in decrypted_config:
            decrypted_config["dbpassword"] = self.decrypt_password(
                decrypted_config["dbpassword"]
            )
        return decrypted_config
```

### 2. SQL Injection Prevention

```python
# security.py
import re
from typing import List

class SQLValidator:
    # Dangerous SQL patterns
    DANGEROUS_PATTERNS = [
        r";\s*DROP\s+",
        r";\s*DELETE\s+FROM\s+",
        r";\s*UPDATE\s+.*SET\s+",
        r";\s*INSERT\s+INTO\s+",
        r";\s*CREATE\s+",
        r";\s*ALTER\s+",
        r";\s*TRUNCATE\s+",
        r"EXEC\s*\(",
        r"EXECUTE\s*\(",
        r"xp_cmdshell",
        r"sp_executesql",
    ]
    
    @staticmethod
    def is_safe_query(query: str) -> tuple[bool, str]:
        """
        Check if a query is safe to execute
        Returns: (is_safe, reason)
        """
        query_upper = query.upper()
        
        # Check for multiple statements
        if query.count(';') > 0 and not query.strip().endswith(';'):
            return False, "Multiple SQL statements detected"
        
        # Check for dangerous patterns
        for pattern in SQLValidator.DANGEROUS_PATTERNS:
            if re.search(pattern, query, re.IGNORECASE):
                return False, f"Dangerous pattern detected: {pattern}"
        
        # Check for comments that might hide malicious code
        if '--' in query or '/*' in query:
            return False, "SQL comments not allowed"
        
        return True, "Query appears safe"
    
    @staticmethod
    def sanitize_identifier(identifier: str) -> str:
        """Sanitize table/column names"""
        # Only allow alphanumeric, underscore, and dot
        if not re.match(r'^[a-zA-Z0-9_\.]+$', identifier):
            raise ValueError(f"Invalid identifier: {identifier}")
        return identifier

# Usage in your tools
def execute_query(connection_id: str, query: str) -> dict:
    is_safe, reason = SQLValidator.is_safe_query(query)
    if not is_safe:
        return {
            "content": f"Query rejected: {reason}",
            "isError": True
        }
    
    # Proceed with execution
    # ...
```

### 3. Rate Limiting

```python
# rate_limiter.py
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict

class RateLimiter:
    def __init__(self, max_requests: int = 100, window_minutes: int = 60):
        self.max_requests = max_requests
        self.window = timedelta(minutes=window_minutes)
        self.requests: Dict[str, list] = defaultdict(list)
    
    def check_rate_limit(self, connection_id: str) -> tuple[bool, str]:
        """
        Check if request is within rate limit
        Returns: (is_allowed, message)
        """
        now = datetime.now()
        cutoff = now - self.window
        
        # Remove old requests
        self.requests[connection_id] = [
            req_time for req_time in self.requests[connection_id]
            if req_time > cutoff
        ]
        
        # Check limit
        if len(self.requests[connection_id]) >= self.max_requests:
            return False, f"Rate limit exceeded: {self.max_requests} requests per {self.window.seconds//60} minutes"
        
        # Add current request
        self.requests[connection_id].append(now)
        
        remaining = self.max_requests - len(self.requests[connection_id])
        return True, f"Rate limit OK. {remaining} requests remaining"

# Usage
rate_limiter = RateLimiter(max_requests=100, window_minutes=60)

def execute_query(connection_id: str, query: str) -> dict:
    is_allowed, message = rate_limiter.check_rate_limit(connection_id)
    if not is_allowed:
        return {
            "content": message,
            "isError": True
        }
    
    # Proceed with execution
    # ...
```

### 4. Connection Security

```python
# connection_security.py
from typing import Dict

class ConnectionSecurityManager:
    # Allowed hosts (whitelist)
    ALLOWED_HOSTS = [
        "localhost",
        "127.0.0.1",
        "*.yourdomain.com",
        # Add your allowed hosts
    ]
    
    # Blocked hosts (blacklist)
    BLOCKED_HOSTS = [
        "0.0.0.0",
        "169.254.169.254",  # AWS metadata
        "metadata.google.internal",  # GCP metadata
    ]
    
    @staticmethod
    def is_host_allowed(hostname: str) -> tuple[bool, str]:
        """Check if a hostname is allowed"""
        
        # Check blacklist first
        if hostname in ConnectionSecurityManager.BLOCKED_HOSTS:
            return False, f"Host {hostname} is blocked"
        
        # Check if it matches cloud metadata endpoints
        if "metadata" in hostname.lower():
            return False, "Metadata endpoints are not allowed"
        
        # In production, implement proper whitelist checking
        # For development, allow all non-blocked hosts
        return True, "Host is allowed"
    
    @staticmethod
    def validate_connection_config(config: Dict) -> tuple[bool, str]:
        """Validate connection configuration"""
        
        # Check hostname
        is_allowed, message = ConnectionSecurityManager.is_host_allowed(
            config.get("hostname", "")
        )
        if not is_allowed:
            return False, message
        
        # Validate port range
        port = config.get("port", 0)
        if not (1 <= port <= 65535):
            return False, f"Invalid port: {port}"
        
        # Check for SSL/TLS requirement for production
        if not config.get("ssl", False) and not config.get("hostname") in ["localhost", "127.0.0.1"]:
            return False, "SSL/TLS is required for remote connections"
        
        return True, "Configuration is valid"
```

---

## Creating the Connector Package

### Project Structure

```
dbhandler-mcp/
├── README.md
├── LICENSE
├── setup.py (or package.json)
├── requirements.txt
├── .env.example
├── .gitignore
├── src/
│   ├── __init__.py
│   ├── server.py
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── connection_handler.py
│   │   ├── query_handler.py
│   │   ├── table_handler.py
│   │   └── metadata_handler.py
│   ├── security/
│   │   ├── __init__.py
│   │   ├── encryption.py
│   │   ├── sql_validator.py
│   │   └── rate_limiter.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── database_factory.py
│   │   └── error_handler.py
│   └── config/
│       ├── __init__.py
│       └── settings.py
├── config/
│   ├── schema.json
│   └── claude_mcp_config.json
├── tests/
│   ├── __init__.py
│   ├── test_server.py
│   ├── test_handlers.py
│   └── test_security.py
├── docs/
│   ├── installation.md
│   ├── configuration.md
│   ├── api_reference.md
│   └── examples.md
└── examples/
    ├── basic_connection.py
    ├── query_examples.py
    └── advanced_usage.py
```

### setup.py (Python Package)

```python
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="dbhandler-mcp",
    version="1.0.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="Database Handler MCP Connector for Claude AI",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/dbhandler-mcp",
    project_urls={
        "Bug Tracker": "https://github.com/yourusername/dbhandler-mcp/issues",
        "Documentation": "https://github.com/yourusername/dbhandler-mcp/docs",
        "Source Code": "https://github.com/yourusername/dbhandler-mcp",
    },
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Database",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.9",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "dbhandler-mcp=src.server:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["config/*.json", "config/*.yaml"],
    },
    keywords="claude mcp database sql connector ai assistant",
    license="MIT",
)
```

### requirements.txt

```
# MCP Core
mcp>=0.1.0

# Database Drivers
sqlalchemy>=2.0.0
pymysql>=1.0.0
psycopg2-binary>=2.9.0
cx-Oracle>=8.3.0
pyodbc>=4.0.0
pymongo>=4.0.0

# Cloud Databases
snowflake-connector-python>=3.0.0
google-cloud-bigquery>=3.0.0
redshift-connector>=2.0.0

# Security
cryptography>=41.0.0
python-dotenv>=1.0.0

# Utilities
pandas>=2.0.0
polars>=0.19.0
python-dateutil>=2.8.0
pydantic>=2.0.0

# Development (optional)
pytest>=7.4.0
pytest-asyncio>=0.21.0
black>=23.0.0
flake8>=6.0.0
mypy>=1.5.0
```

### Configuration Schema (config/schema.json)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "DBHANDLER MCP Configuration",
  "description": "Configuration schema for DBHANDLER Claude connector",
  "type": "object",
  "properties": {
    "connections": {
      "type": "array",
      "description": "List of database connections",
      "items": {
        "type": "object",
        "properties": {
          "connection_id": {
            "type": "string",
            "description": "Unique identifier for this connection",
            "pattern": "^[a-zA-Z0-9_-]+$",
            "minLength": 1,
            "maxLength": 50
          },
          "db_type": {
            "type": "string",
            "description": "Database type",
            "enum": [
              "MYSQL",
              "POSTGRES",
              "ORACLE",
              "SQLSERVER",
              "MONGODB",
              "SNOWFLAKE",
              "BIGQUERY",
              "REDSHIFT",
              "ATHENA",
              "SAPHANA",
              "VERTICA",
              "DB2",
              "TERADATA"
            ]
          },
          "hostname": {
            "type": "string",
            "description": "Database hostname or IP address",
            "minLength": 1
          },
          "port": {
            "type": "integer",
            "description": "Database port number",
            "minimum": 1,
            "maximum": 65535
          },
          "database": {
            "type": "string",
            "description": "Database name",
            "minLength": 1
          },
          "username": {
            "type": "string",
            "description": "Database username",
            "minLength": 1
          },
          "password": {
            "type": "string",
            "description": "Database password (will be encrypted)",
            "format": "password",
            "minLength": 1
          },
          "schema": {
            "type": "string",
            "description": "Database schema (optional)"
          },
          "ssl": {
            "type": "boolean",
            "description": "Use SSL/TLS connection",
            "default": true
          },
          "connection_timeout": {
            "type": "integer",
            "description": "Connection timeout in seconds",
            "default": 30,
            "minimum": 5,
            "maximum": 300
          },
          "query_timeout": {
            "type": "integer",
            "description": "Query timeout in seconds",
            "default": 300,
            "minimum": 10,
            "maximum": 3600
          }
        },
        "required": ["connection_id", "db_type", "hostname", "database", "username", "password"]
      }
    },
    "security": {
      "type": "object",
      "description": "Security settings",
      "properties": {
        "master_password": {
          "type": "string",
          "description": "Master password for encryption",
          "format": "password"
        },
        "rate_limit": {
          "type": "object",
          "properties": {
            "max_requests": {
              "type": "integer",
              "default": 100,
              "minimum": 1
            },
            "window_minutes": {
              "type": "integer",
              "default": 60,
              "minimum": 1
            }
          }
        },
        "allowed_hosts": {
          "type": "array",
          "description": "Whitelist of allowed database hosts",
          "items": {
            "type": "string"
          }
        }
      }
    },
    "logging": {
      "type": "object",
      "properties": {
        "level": {
          "type": "string",
          "enum": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
          "default": "INFO"
        },
        "file": {
          "type": "string",
          "description": "Log file path"
        }
      }
    }
  },
  "required": ["connections"]
}
```

### Claude MCP Config (config/claude_mcp_config.json)

```json
{
  "mcpServers": {
    "dbhandler": {
      "command": "python",
      "args": ["-m", "dbhandler_mcp.server"],
      "env": {
        "MASTER_PASSWORD": "${DBHANDLER_MASTER_PASSWORD}"
      }
    }
  }
}
```

### .env.example

```bash
# DBHANDLER MCP Environment Variables

# Master password for credential encryption
DBHANDLER_MASTER_PASSWORD=your-secure-master-password-here

# Database Connections (Optional - can also configure via Claude UI)
# DB1_TYPE=MYSQL
# DB1_HOST=localhost
# DB1_PORT=3306
# DB1_DATABASE=mydb
# DB1_USER=dbuser
# DB1_PASSWORD=dbpassword

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/dbhandler-mcp.log

# Rate Limiting
RATE_LIMIT_MAX_REQUESTS=100
RATE_LIMIT_WINDOW_MINUTES=60

# Security
ALLOWED_HOSTS=localhost,127.0.0.1,*.mycompany.com
```

### README.md Template

```markdown
# DBHANDLER MCP - Database Connector for Claude AI

Connect Claude AI to your databases with secure, enterprise-grade database operations.

## Features

- 🗄️ **Multi-Database Support**: MySQL, PostgreSQL, Oracle, SQL Server, MongoDB, Snowflake, BigQuery, and more
- 🔒 **Enterprise Security**: Encrypted credentials, SQL injection prevention, rate limiting
- 🚀 **25+ Database Operations**: Query, analyze, profile, and manage your databases
- 📊 **Data Analysis**: Statistical profiling, relationship mapping, metadata extraction
- 🔄 **Connection Management**: Create, test, and manage multiple database connections
- ⚡ **High Performance**: Optimized queries with connection pooling and caching

## Supported Databases

- MySQL
- PostgreSQL
- Oracle
- Microsoft SQL Server
- MongoDB
- Snowflake
- Google BigQuery
- Amazon Redshift
- AWS Athena
- SAP HANA
- Vertica
- IBM DB2
- Teradata

## Installation

### Prerequisites

- Python 3.9 or higher
- Claude Desktop or Claude API access

### Via pip

```bash
pip install dbhandler-mcp
```

### From source

```bash
git clone https://github.com/yourusername/dbhandler-mcp.git
cd dbhandler-mcp
pip install -e .
```

## Quick Start

### 1. Configure Claude

Add to your Claude Desktop config file (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "dbhandler": {
      "command": "python",
      "args": ["-m", "dbhandler_mcp.server"],
      "env": {
        "MASTER_PASSWORD": "your-secure-password"
      }
    }
  }
}
```

### 2. Create Database Connection

In Claude, simply ask:

```
Connect to my MySQL database:
- Host: localhost
- Port: 3306
- Database: mydb
- Username: root
- Password: ****
```

### 3. Start Querying

```
Show me all tables in my database
```

```
Query the users table and show me the first 10 rows
```

```
Get the schema for the orders table
```

## Available Tools

### Connection Management
- `db_create_connection` - Create new database connection
- `db_test_connection` - Test connection validity
- `db_close_connection` - Close active connection
- `db_list_connections` - List all connections

### Query Operations
- `db_execute_query` - Execute SELECT queries
- `db_execute_sql` - Execute INSERT/UPDATE/DELETE/DDL
- `db_generate_query` - Generate SQL from parameters

### Table Operations
- `db_get_all_tables` - List all tables
- `db_get_table_columns` - Get column information
- `db_get_table_columns_details` - Detailed column metadata
- `db_read_table` - Read table data
- `db_get_table_details` - Comprehensive table info
- `db_get_table_relationships` - Foreign key relationships
- `db_create_table` - Create new tables
- `db_truncate_table` - Remove all table data
- `db_create_view` - Create database views

### Data Analysis
- `db_get_column_lov` - List of values for columns
- `db_get_columns_profile` - Statistical profiling
- `db_get_filtered_row_count` - Count with filters
- `db_get_incremental_columns` - Incremental load columns
- `db_fetch_delta_columns` - Delta columns for CDC

### Metadata
- `db_update_column_comment` - Update column comments

## Configuration

### Environment Variables

Create a `.env` file:

```bash
DBHANDLER_MASTER_PASSWORD=your-secure-password
LOG_LEVEL=INFO
RATE_LIMIT_MAX_REQUESTS=100
RATE_LIMIT_WINDOW_MINUTES=60
```

### Connection Config File

Create `~/.dbhandler/connections.json`:

```json
{
  "connections": [
    {
      "connection_id": "prod_mysql",
      "db_type": "MYSQL",
      "hostname": "prod-db.company.com",
      "port": 3306,
      "database": "production",
      "username": "readonly_user",
      "password": "encrypted_password",
      "ssl": true
    }
  ]
}
```

## Security

### Credential Encryption

All passwords are encrypted using Fernet (symmetric encryption):

```python
from dbhandler_mcp.security import CredentialManager

manager = CredentialManager(master_password="your-password")
encrypted = manager.encrypt_password("db-password")
```

### SQL Injection Prevention

All queries are validated before execution:

```python
from dbhandler_mcp.security import SQLValidator

is_safe, reason = SQLValidator.is_safe_query(query)
```

### Rate Limiting

Automatic rate limiting prevents abuse:
- Default: 100 requests per hour per connection
- Configurable via environment variables

## Examples

### Example 1: Data Analysis

```
Claude, connect to my analytics database and:
1. Show me all tables
2. Profile the customers table
3. Find relationships between customers and orders
4. Show me top 10 customers by order count
```

### Example 2: Schema Exploration

```
What's the structure of my database? Show me:
- All tables and their row counts
- Foreign key relationships
- Column data types and constraints
```

### Example 3: Data Quality Check

```
Analyze the data quality of the users table:
- Show me null counts for each column
- Find duplicate emails
- Check for invalid date formats
```

## Troubleshooting

### Connection Issues

**Problem**: Connection timeout

**Solution**: 
- Check firewall rules
- Verify database is accessible
- Increase `connection_timeout` in config

### Permission Errors

**Problem**: Access denied

**Solution**:
- Verify database credentials
- Check user permissions
- Ensure SSL certificates are valid

### Rate Limiting

**Problem**: Too many requests

**Solution**:
- Increase rate limit in config
- Optimize query patterns
- Use connection pooling

## Development

### Running Tests

```bash
pytest tests/
```

### Code Formatting

```bash
black src/
flake8 src/
```

### Type Checking

```bash
mypy src/
```

## Contributing

Contributions are welcome! Please read our [Contributing Guide](CONTRIBUTING.md).

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## License

MIT License - see [LICENSE](LICENSE) file for details

## Support

- 📧 Email: support@yourcompany.com
- 💬 Discord: [Join our community](https://discord.gg/yourserver)
- 🐛 Issues: [GitHub Issues](https://github.com/yourusername/dbhandler-mcp/issues)
- 📖 Documentation: [Full Docs](https://docs.yourcompany.com/dbhandler-mcp)

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.

## Roadmap

- [ ] Add support for more databases (Cassandra, DynamoDB)
- [ ] Query optimization suggestions
- [ ] Visual query builder
- [ ] Data lineage tracking
- [ ] Automated backup management
- [ ] Multi-tenant support

## Acknowledgments

- Built with [Model Context Protocol](https://modelcontextprotocol.io/)
- Powered by [Anthropic Claude](https://www.anthropic.com/)

---

Made with ❤️ by [Your Team]
```

---

## Testing

### Test Structure

```python
# tests/test_server.py
import pytest
import asyncio
from src.server import DBHandlerMCP

@pytest.fixture
async def server():
    """Create test server instance"""
    server = DBHandlerMCP()
    yield server
    # Cleanup connections
    for conn_id in list(server.connections.keys()):
        await server.close_connection(conn_id)

@pytest.mark.asyncio
async def test_create_connection(server):
    """Test database connection creation"""
    config = {
        "dbType": "MYSQL",
        "hostname": "localhost",
        "port": 3306,
        "dbname": "test_db",
        "dbuser": "test_user",
        "dbpassword": "test_password"
    }
    
    result = await server.create_connection("test_conn", config)
    
    assert result["isError"] == False
    assert "test_conn" in server.connections

@pytest.mark.asyncio
async def test_execute_query(server):
    """Test query execution"""
    # Setup connection first
    config = {
        "dbType": "MYSQL",
        "hostname": "localhost",
        "port": 3306,
        "dbname": "test_db",
        "dbuser": "test_user",
        "dbpassword": "test_password"
    }
    await server.create_connection("test_conn", config)
    
    # Execute test query
    result = await server.execute_query(
        "test_conn",
        "SELECT * FROM test_table LIMIT 10"
    )
    
    assert result["isError"] == False
    assert "data" in result["content"]

@pytest.mark.asyncio
async def test_sql_injection_prevention(server):
    """Test SQL injection prevention"""
    from src.security.sql_validator import SQLValidator
    
    malicious_queries = [
        "SELECT * FROM users; DROP TABLE users;--",
        "SELECT * FROM users WHERE id = 1 OR 1=1",
        "'; DELETE FROM users; --",
    ]
    
    for query in malicious_queries:
        is_safe, reason = SQLValidator.is_safe_query(query)
        assert is_safe == False

@pytest.mark.asyncio
async def test_rate_limiting(server):
    """Test rate limiting functionality"""
    from src.security.rate_limiter import RateLimiter
    
    limiter = RateLimiter(max_requests=5, window_minutes=1)
    
    # Should allow first 5 requests
    for i in range(5):
        is_allowed, msg = limiter.check_rate_limit("test_conn")
        assert is_allowed == True
    
    # Should block 6th request
    is_allowed, msg = limiter.check_rate_limit("test_conn")
    assert is_allowed == False

@pytest.mark.asyncio
async def test_credential_encryption():
    """Test credential encryption/decryption"""
    from src.security.encryption import CredentialManager
    
    manager = CredentialManager("test-master-password")
    
    original_password = "my-secret-password"
    encrypted = manager.encrypt_password(original_password)
    decrypted = manager.decrypt_password(encrypted)
    
    assert encrypted != original_password
    assert decrypted == original_password

@pytest.mark.asyncio
async def test_get_all_tables(server):
    """Test table listing"""
    config = {
        "dbType": "MYSQL",
        "hostname": "localhost",
        "port": 3306,
        "dbname": "test_db",
        "dbuser": "test_user",
        "dbpassword": "test_password"
    }
    await server.create_connection("test_conn", config)
    
    result = await server.get_all_tables("test_conn")
    
    assert result["isError"] == False
    assert "tables" in result["content"]
    assert isinstance(result["content"]["tables"], list)

# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

### Integration Tests

```python
# tests/test_integration.py
import pytest
import asyncio
from src.server import DBHandlerMCP

@pytest.fixture(scope="module")
async def live_server():
    """Create server with live database connection"""
    server = DBHandlerMCP()
    
    # Setup test database
    config = {
        "dbType": "MYSQL",
        "hostname": "localhost",
        "port": 3306,
        "dbname": "integration_test",
        "dbuser": "root",
        "dbpassword": "password"
    }
    
    await server.create_connection("integration_test", config)
    
    # Create test table
    await server.execute_sql(
        "integration_test",
        """
        CREATE TABLE IF NOT EXISTS test_users (
            id INT PRIMARY KEY AUTO_INCREMENT,
            name VARCHAR(100),
            email VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    
    # Insert test data
    await server.execute_sql(
        "integration_test",
        """
        INSERT INTO test_users (name, email) VALUES
        ('John Doe', 'john@example.com'),
        ('Jane Smith', 'jane@example.com'),
        ('Bob Johnson', 'bob@example.com')
        """
    )
    
    yield server
    
    # Cleanup
    await server.execute_sql("integration_test", "DROP TABLE IF EXISTS test_users")
    await server.close_connection("integration_test")

@pytest.mark.asyncio
async def test_full_workflow(live_server):
    """Test complete workflow from connection to query"""
    
    # List tables
    tables_result = await live_server.get_all_tables("integration_test")
    assert "test_users" in str(tables_result)
    
    # Get table columns
    columns_result = await live_server.get_table_columns("integration_test", "test_users")
    assert "id" in str(columns_result)
    assert "name" in str(columns_result)
    
    # Query data
    query_result = await live_server.execute_query(
        "integration_test",
        "SELECT * FROM test_users"
    )
    assert len(query_result["content"]["data"]) == 3
    
    # Profile columns
    profile_result = await live_server.get_columns_profile(
        "integration_test",
        "test_users"
    )
    assert profile_result["isError"] == False
```

---

## Publishing Process

### 1. Prepare for Publishing

```bash
# Update version in setup.py
# Create distribution files
python setup.py sdist bdist_wheel

# Check package
twine check dist/*
```

### 2. Publish to PyPI

```bash
# Test PyPI first
twine upload --repository testpypi dist/*

# Production PyPI
twine upload dist/*
```

### 3. Publish to NPM (if Node.js version)

```bash
npm login
npm publish
```

### 4. Create GitHub Release

```bash
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin v1.0.0
```

### 5. Submit to MCP Registry

Create a Pull Request to the MCP servers repository:

```bash
git clone https://github.com/modelcontextprotocol/servers
cd servers

# Create your connector directory
mkdir -p src/dbhandler
cp -r /path/to/your/connector/* src/dbhandler/

# Add to registry
# Edit README.md to add your connector

git add .
git commit -m "Add DBHANDLER connector for database operations"
git push origin add-dbhandler

# Create PR on GitHub
```

### 6. Documentation for Anthropic

Create `SUBMISSION.md`:

```markdown
# DBHANDLER MCP Connector Submission

## Overview
Enterprise-grade database connector for Claude AI with support for 13+ databases.

## Key Features
- Multi-database support (MySQL, PostgreSQL, Oracle, SQL Server, etc.)
- 25+ database operations
- Enterprise security (encryption, SQL injection prevention, rate limiting)
- High performance with connection pooling

## Installation
```bash
pip install dbhandler-mcp
```

## Configuration
```json
{
  "mcpServers": {
    "dbhandler": {
      "command": "python",
      "args": ["-m", "dbhandler_mcp.server"]
    }
  }
}
```

## Use Cases
- Database exploration and analysis
- Schema documentation
- Data quality assessment
- Query generation and optimization
- Database administration

## Repository
https://github.com/yourusername/dbhandler-mcp

## Documentation
https://docs.yourcompany.com/dbhandler-mcp

## Support
support@yourcompany.com

## License
MIT
```

---

## User Installation Guide

### For End Users

```markdown
# Installing DBHANDLER Connector in Claude

## Step 1: Install the Package

Open your terminal and run:

```bash
pip install dbhandler-mcp
```

## Step 2: Find Claude's Config File

The config file location depends on your OS:

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

## Step 3: Edit Config File

Add the DBHANDLER connector:

```json
{
  "mcpServers": {
    "dbhandler": {
      "command": "python",
      "args": ["-m", "dbhandler_mcp.server"],
      "env": {
        "MASTER_PASSWORD": "your-secure-master-password"
      }
    }
  }
}
```

## Step 4: Restart Claude

Close and reopen Claude Desktop.

## Step 5: Verify Installation

In Claude, type:

```
List available MCP servers
```

You should see "dbhandler" in the list.

## Step 6: Create Your First Connection

```
Connect to my MySQL database:
- Connection ID: my_database
- Host: localhost
- Port: 3306
- Database: mydb
- Username: myuser
- Password: mypassword
```

## Step 7: Start Using

```
Show me all tables in my_database
```

```
Describe the users table
```

```
Query the orders table and show me the last 10 orders
```

## Troubleshooting

### Issue: "Command not found: python"

**Solution**: Use `python3` instead:

```json
{
  "command": "python3",
  "args": ["-m", "dbhandler_mcp.server"]
}
```

### Issue: "Connection failed"

**Solutions**:
1. Check database is running
2. Verify credentials
3. Check firewall settings
4. Ensure database allows remote connections

### Issue: "Rate limit exceeded"

**Solution**: Wait a few minutes or increase rate limit in config.

## Getting Help

- Documentation: https://docs.yourcompany.com/dbhandler-mcp
- Issues: https://github.com/yourusername/dbhandler-mcp/issues
- Email: support@yourcompany.com
```

---

## Deployment Options

### Option 1: Serverless (AWS Lambda)

```python
# lambda_function.py
import json
import asyncio
from src.server import DBHandlerMCP

# Global server instance (reused across invocations)
server = DBHandlerMCP()

def lambda_handler(event, context):
    """AWS Lambda handler"""
    
    try:
        # Parse request
        tool_name = event.get('tool_name')
        arguments = event.get('arguments', {})
        
        # Execute tool
        result = asyncio.run(
            server.call_tool(tool_name, arguments)
        )
        
        return {
            'statusCode': 200,
            'body': json.dumps(result),
            'headers': {
                'Content-Type': 'application/json'
            }
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'isError': True
            }),
            'headers': {
                'Content-Type': 'application/json'
            }
        }
```

**Deployment**:

```bash
# Package for Lambda
pip install -t ./package -r requirements.txt
cd package
zip -r ../deployment-package.zip .
cd ..
zip -g deployment-package.zip lambda_function.py src/*

# Deploy using AWS CLI
aws lambda create-function \
  --function-name dbhandler-mcp \
  --runtime python3.11 \
  --role arn:aws:iam::ACCOUNT:role/lambda-role \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://deployment-package.zip \
  --timeout 300 \
  --memory-size 512
```

### Option 2: Docker Container

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY src/ ./src/
COPY config/ ./config/

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV MASTER_PASSWORD=""

# Expose port (if running as HTTP server)
EXPOSE 8000

# Run server
CMD ["python", "-m", "src.server"]
```

**Build and Run**:

```bash
# Build image
docker build -t dbhandler-mcp:latest .

# Run container
docker run -d \
  --name dbhandler-mcp \
  -e MASTER_PASSWORD="your-password" \
  -p 8000:8000 \
  dbhandler-mcp:latest

# Using Docker Compose
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  dbhandler:
    build: .
    image: dbhandler-mcp:latest
    container_name: dbhandler-mcp
    ports:
      - "8000:8000"
    environment:
      - MASTER_PASSWORD=${MASTER_PASSWORD}
      - LOG_LEVEL=INFO
    volumes:
      - ./config:/app/config
      - ./logs:/app/logs
    restart: unless-stopped
    networks:
      - dbhandler-network

networks:
  dbhandler-network:
    driver: bridge
```

### Option 3: Kubernetes

```yaml
# kubernetes/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dbhandler-mcp
  labels:
    app: dbhandler-mcp
spec:
  replicas: 3
  selector:
    matchLabels:
      app: dbhandler-mcp
  template:
    metadata:
      labels:
        app: dbhandler-mcp
    spec:
      containers:
      - name: dbhandler-mcp
        image: yourusername/dbhandler-mcp:latest
        ports:
        - containerPort: 8000
        env:
        - name: MASTER_PASSWORD
          valueFrom:
            secretKeyRef:
              name: dbhandler-secrets
              key: master-password
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: dbhandler-mcp-service
spec:
  selector:
    app: dbhandler-mcp
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
```

---

## Maintenance & Updates

### Version Management

```python
# src/__version__.py
__version__ = "1.0.0"
__version_info__ = (1, 0, 0)
```

### CHANGELOG.md

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Support for AWS Athena
- Query result caching

## [1.0.0] - 2024-11-04

### Added
- Initial release
- Support for MySQL, PostgreSQL, Oracle, SQL Server
- 25+ database operations
- Enterprise security features
- Rate limiting
- Credential encryption

### Security
- SQL injection prevention
- Rate limiting implementation
- Credential encryption with Fernet

## [0.9.0] - 2024-10-15

### Added
- Beta release
- Core functionality

### Fixed
- Connection timeout issues
- Memory leaks in connection pooling
```

### Monitoring and Logging

```python
# src/utils/monitoring.py
import logging
import time
from functools import wraps
from typing import Callable

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('dbhandler-mcp.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('dbhandler-mcp')

def log_tool_execution(func: Callable):
    """Decorator to log tool execution"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        tool_name = func.__name__
        
        try:
            logger.info(f"Executing tool: {tool_name}")
            result = await func(*args, **kwargs)
            
            duration = (time.time() - start_time) * 1000
            logger.info(f"Tool {tool_name} completed in {duration:.2f}ms")
            
            return result
            
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            logger.error(f"Tool {tool_name} failed after {duration:.2f}ms: {str(e)}")
            raise
    
    return wrapper

# Usage
@log_tool_execution
async def execute_query(connection_id: str, query: str):
    # Implementation
    pass
```

---

## Code Examples

### Example 1: Complete MCP Server Implementation

See the Python MCP Server section above for the complete implementation.

### Example 2: Custom Database Driver

```python
# src/drivers/custom_database.py
from sqlalchemy import create_engine
from typing import Dict, Any

class CustomDatabaseDriver:
    """Driver for a custom database"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.engine = None
        self.connection = None
    
    def connect(self) -> bool:
        """Establish database connection"""
        try:
            connection_string = self._build_connection_string()
            self.engine = create_engine(connection_string)
            self.connection = self.engine.connect()
            return True
        except Exception as e:
            raise ConnectionError(f"Failed to connect: {str(e)}")
    
    def _build_connection_string(self) -> str:
        """Build database connection string"""
        return (
            f"custom://{self.config['username']}:{self.config['password']}"
            f"@{self.config['hostname']}:{self.config['port']}"
            f"/{self.config['database']}"
        )
    
    def execute_query(self, query: str) -> Dict[str, Any]:
        """Execute SELECT query"""
        result = self.connection.execute(query)
        rows = result.fetchall()
        columns = result.keys()
        
        return {
            "columns": list(columns),
            "data": [dict(zip(columns, row)) for row in rows],
            "row_count": len(rows)
        }
    
    def close(self):
        """Close connection"""
        if self.connection:
            self.connection.close()
        if self.engine:
            self.engine.dispose()
```

### Example 3: Query Builder

```python
# src/utils/query_builder.py
from typing import List, Dict, Any

class QueryBuilder:
    """SQL query builder"""
    
    def __init__(self, table_name: str):
        self.table_name = table_name
        self.select_columns = []
        self.where_conditions = []
        self.order_by_columns = []
        self.limit_value = None
    
    def select(self, *columns: str) -> 'QueryBuilder':
        """Add SELECT columns"""
        self.select_columns.extend(columns)
        return self
    
    def where(self, condition: str) -> 'QueryBuilder':
        """Add WHERE condition"""
        self.where_conditions.append(condition)
        return self
    
    def order_by(self, column: str, direction: str = "ASC") -> 'QueryBuilder':
        """Add ORDER BY"""
        self.order_by_columns.append(f"{column} {direction}")
        return self
    
    def limit(self, value: int) -> 'QueryBuilder':
        """Add LIMIT"""
        self.limit_value = value
        return self
    
    def build(self) -> str:
        """Build final SQL query"""
        # SELECT clause
        if self.select_columns:
            select_clause = f"SELECT {', '.join(self.select_columns)}"
        else:
            select_clause = "SELECT *"
        
        # FROM clause
        from_clause = f"FROM {self.table_name}"
        
        # WHERE clause
        where_clause = ""
        if self.where_conditions:
            where_clause = f"WHERE {' AND '.join(self.where_conditions)}"
        
        # ORDER BY clause
        order_by_clause = ""
        if self.order_by_columns:
            order_by_clause = f"ORDER BY {', '.join(self.order_by_columns)}"
        
        # LIMIT clause
        limit_clause = ""
        if self.limit_value:
            limit_clause = f"LIMIT {self.limit_value}"
        
        # Combine all parts
        query_parts = [
            select_clause,
            from_clause,
            where_clause,
            order_by_clause,
            limit_clause
        ]
        
        return ' '.join(part for part in query_parts if part)

# Usage
query = (QueryBuilder("users")
    .select("id", "name", "email")
    .where("status = 'active'")
    .where("created_at > '2024-01-01'")
    .order_by("created_at", "DESC")
    .limit(10)
    .build())

print(query)
# SELECT id, name, email FROM users WHERE status = 'active' AND created_at > '2024-01-01' ORDER BY created_at DESC LIMIT 10
```

---

## Resources

### Official Documentation

- **MCP Documentation**: https://modelcontextprotocol.io/
- **MCP GitHub**: https://github.com/modelcontextprotocol
- **Claude Documentation**: https://docs.anthropic.com/
- **SQLAlchemy**: https://www.sqlalchemy.org/

### Example Connectors

- **MCP Servers Repository**: https://github.com/modelcontextprotocol/servers
- **File System Server**: Example of MCP implementation
- **PostgreSQL Server**: Database connector example

### Tools & Libraries

- **Python MCP SDK**: `pip install mcp`
- **Node.js MCP SDK**: `npm install @modelcontextprotocol/sdk`
- **MCP Inspector**: `npx @modelcontextprotocol/inspector`

### Testing Resources

- **pytest**: https://pytest.org/
- **pytest-asyncio**: https://github.com/pytest-dev/pytest-asyncio
- **SQLAlchemy Testing**: https://docs.sqlalchemy.org/en/20/orm/session_transaction.html

### Security Resources

- **OWASP SQL Injection**: https://owasp.org/www-community/attacks/SQL_Injection
- **Cryptography Library**: https://cryptography.io/
- **Security Best Practices**: https://cheatsheetseries.owasp.org/

### Deployment Resources

- **Docker Documentation**: https://docs.docker.com/
- **AWS Lambda**: https://docs.aws.amazon.com/lambda/
- **Kubernetes**: https://kubernetes.io/docs/

---

## Next Steps

1. ✅ Review this guide thoroughly
2. ✅ Set up development environment
3. ✅ Implement MCP server with your DBHANDLER logic
4. ✅ Write comprehensive tests
5. ✅ Add security features (encryption, validation, rate limiting)
6. ✅ Create documentation (README, API reference, examples)
7. ✅ Test locally using MCP Inspector
8. ✅ Package your connector
9. ✅ Publish to PyPI/NPM
10. ✅ Submit to Anthropic's MCP registry
11. ✅ Support users and iterate

---

## Support & Contact

For questions or assistance:

- **GitHub Issues**: [Create an issue](https://github.com/yourusername/dbhandler-mcp/issues)
- **Email**: support@yourcompany.com
- **Documentation**: https://docs.yourcompany.com/dbhandler-mcp
- **Discord**: [Join our community](https://discord.gg/yourserver)

---

**Good luck with your DBHANDLER MCP Connector! 🚀**
