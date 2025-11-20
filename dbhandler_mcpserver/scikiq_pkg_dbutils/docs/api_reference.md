# API Reference

This document provides a comprehensive reference for all tools and functions available in the ScikiQ Database Handler MCP Connector.

## Table of Contents
- [Overview](#overview)
- [Database Connection Tools](#database-connection-tools)
- [Query Execution Tools](#query-execution-tools)
- [Database Management Tools](#database-management-tools)
- [Utility Tools](#utility-tools)
- [SAP Integration Tools](#sap-integration-tools)
- [Error Handling](#error-handling)
- [Response Formats](#response-formats)

## Overview

The ScikiQ Database Handler MCP Connector provides 25+ tools for comprehensive database operations. All tools follow a consistent interface pattern and return structured responses.

### Tool Categories

| Category | Tools | Purpose |
|----------|--------|---------|
| Connection | 3 | Manage database connections |
| Query | 6 | Execute SQL queries and operations |
| Management | 8 | Database administration tasks |
| Utility | 5 | Helper and analysis functions |
| SAP | 3 | SAP system integration |

### Common Parameters

Most tools accept these common parameters:

- `connection_name` (string): Named connection from configuration
- `timeout` (number, optional): Operation timeout in seconds
- `format` (string, optional): Response format (`json`, `csv`, `table`)

## Database Connection Tools

### 1. create_database_connection

Create a new database connection configuration.

**Parameters:**
```typescript
{
  "connection_name": string,      // Unique name for the connection
  "database_type": string,        // Database type (mysql, postgresql, etc.)
  "host": string,                // Database host
  "port": number,                // Database port
  "database": string,            // Database name
  "username": string,            // Username
  "password": string,            // Password (will be encrypted)
  "ssl_config": object,          // SSL configuration (optional)
  "connection_params": object    // Additional connection parameters (optional)
}
```

**Supported Database Types:**
- `mysql` - MySQL/MariaDB
- `postgresql` - PostgreSQL
- `oracle` - Oracle Database
- `sqlserver` - Microsoft SQL Server
- `mongodb` - MongoDB
- `snowflake` - Snowflake Data Warehouse
- `bigquery` - Google BigQuery
- `redshift` - Amazon Redshift
- `db2` - IBM DB2
- `teradata` - Teradata
- `vertica` - Vertica
- `hive` - Apache Hive
- `athena` - AWS Athena
- `saphana` - SAP HANA
- `netezza` - IBM Netezza
- `chromadb` - ChromaDB Vector Database
- `duckdb` - DuckDB with S3 Support

**Example:**
```json
{
  "connection_name": "prod_analytics",
  "database_type": "postgresql",
  "host": "analytics.company.com",
  "port": 5432,
  "database": "analytics",
  "username": "readonly_user",
  "password": "secure_password",
  "ssl_config": {
    "ssl_mode": "require",
    "ssl_ca": "/path/to/ca.pem"
  }
}
```

**Response:**
```json
{
  "success": true,
  "message": "Connection 'prod_analytics' created successfully",
  "connection_id": "prod_analytics",
  "encrypted": true
}
```

### 2. test_database_connection

Test connectivity to a database connection.

**Parameters:**
```typescript
{
  "connection_name": string      // Connection name to test
}
```

**Response:**
```json
{
  "success": true,
  "connection_name": "prod_analytics",
  "database_type": "postgresql",
  "host": "analytics.company.com",
  "database": "analytics",
  "connection_time_ms": 45,
  "server_version": "PostgreSQL 13.7",
  "status": "Connected"
}
```

### 3. list_database_connections

List all configured database connections.

**Parameters:**
```typescript
{
  "include_details": boolean     // Include connection details (optional, default: false)
}
```

**Response:**
```json
{
  "success": true,
  "connections": [
    {
      "name": "prod_analytics",
      "type": "postgresql",
      "host": "analytics.company.com",
      "database": "analytics",
      "status": "active"
    }
  ],
  "total_count": 1
}
```

## Query Execution Tools

### 4. execute_sql_query

Execute a SQL query on a database connection.

**Parameters:**
```typescript
{
  "connection_name": string,     // Connection to use
  "query": string,              // SQL query to execute
  "parameters": array,          // Query parameters (optional)
  "limit": number,              // Maximum rows to return (optional)
  "timeout": number,            // Query timeout in seconds (optional)
  "format": string              // Response format (optional)
}
```

**Example:**
```json
{
  "connection_name": "prod_analytics",
  "query": "SELECT product_name, SUM(sales) as total_sales FROM sales WHERE date >= ? GROUP BY product_name ORDER BY total_sales DESC",
  "parameters": ["2024-01-01"],
  "limit": 100,
  "format": "table"
}
```

**Response:**
```json
{
  "success": true,
  "query": "SELECT product_name, SUM(sales)...",
  "execution_time_ms": 234,
  "row_count": 15,
  "columns": ["product_name", "total_sales"],
  "data": [
    ["Product A", 15000],
    ["Product B", 12500]
  ],
  "format": "table"
}
```

### 5. execute_sql_batch

Execute multiple SQL queries in a batch.

**Parameters:**
```typescript
{
  "connection_name": string,     // Connection to use
  "queries": array,             // Array of SQL queries
  "transaction": boolean,       // Execute in transaction (optional)
  "continue_on_error": boolean, // Continue if one query fails (optional)
  "timeout": number             // Overall timeout (optional)
}
```

**Example:**
```json
{
  "connection_name": "prod_analytics",
  "queries": [
    "CREATE TEMPORARY TABLE temp_sales AS SELECT * FROM sales WHERE date = CURRENT_DATE",
    "UPDATE temp_sales SET processed = true WHERE amount > 1000",
    "SELECT COUNT(*) FROM temp_sales WHERE processed = true"
  ],
  "transaction": true
}
```

**Response:**
```json
{
  "success": true,
  "total_queries": 3,
  "successful_queries": 3,
  "failed_queries": 0,
  "results": [
    {
      "query_index": 0,
      "success": true,
      "message": "Table created",
      "affected_rows": 1500
    },
    {
      "query_index": 1,
      "success": true,
      "affected_rows": 234
    },
    {
      "query_index": 2,
      "success": true,
      "data": [[234]]
    }
  ],
  "total_execution_time_ms": 456
}
```

### 6. get_query_explain_plan

Get the execution plan for a SQL query.

**Parameters:**
```typescript
{
  "connection_name": string,     // Connection to use
  "query": string,              // SQL query to analyze
  "format": string              // Plan format (optional)
}
```

**Response:**
```json
{
  "success": true,
  "query": "SELECT * FROM sales WHERE date >= '2024-01-01'",
  "execution_plan": [
    {
      "operation": "Seq Scan",
      "table": "sales",
      "filter": "(date >= '2024-01-01'::date)",
      "cost": "0.00..15000.00",
      "rows": 5000,
      "width": 124
    }
  ],
  "estimated_cost": 15000,
  "estimated_rows": 5000
}
```

### 7. execute_prepared_statement

Execute a prepared statement with parameters.

**Parameters:**
```typescript
{
  "connection_name": string,     // Connection to use
  "statement_name": string,     // Prepared statement name
  "statement": string,          // SQL statement (if creating)
  "parameters": array,          // Statement parameters
  "action": string              // create, execute, or drop (optional)
}
```

### 8. get_query_history

Get query execution history for a connection.

**Parameters:**
```typescript
{
  "connection_name": string,     // Connection name
  "limit": number,              // Number of queries to return (optional)
  "start_date": string,         // Start date filter (optional)
  "end_date": string            // End date filter (optional)
}
```

### 9. cancel_query

Cancel a running query.

**Parameters:**
```typescript
{
  "connection_name": string,     // Connection name
  "query_id": string            // Query ID to cancel
}
```

## Database Management Tools

### 10. get_database_schema

Get the schema information for a database.

**Parameters:**
```typescript
{
  "connection_name": string,     // Connection to use
  "schema_name": string,        // Schema name (optional)
  "include_tables": boolean,    // Include table information (optional)
  "include_views": boolean,     // Include view information (optional)
  "include_procedures": boolean // Include stored procedures (optional)
}
```

**Response:**
```json
{
  "success": true,
  "connection_name": "prod_analytics",
  "database": "analytics",
  "schemas": [
    {
      "name": "public",
      "tables": [
        {
          "name": "sales",
          "type": "table",
          "columns": [
            {
              "name": "id",
              "type": "integer",
              "nullable": false,
              "primary_key": true
            },
            {
              "name": "product_name",
              "type": "varchar(255)",
              "nullable": true
            }
          ],
          "indexes": [
            {
              "name": "idx_sales_date",
              "columns": ["date"],
              "unique": false
            }
          ]
        }
      ]
    }
  ]
}
```

### 11. get_table_info

Get detailed information about a specific table.

**Parameters:**
```typescript
{
  "connection_name": string,     // Connection to use
  "table_name": string,         // Table name
  "schema_name": string,        // Schema name (optional)
  "include_statistics": boolean, // Include table statistics (optional)
  "include_constraints": boolean // Include constraints (optional)
}
```

**Response:**
```json
{
  "success": true,
  "table_name": "sales",
  "schema_name": "public",
  "table_type": "table",
  "columns": [
    {
      "name": "id",
      "data_type": "integer",
      "is_nullable": false,
      "column_default": "nextval('sales_id_seq'::regclass)",
      "primary_key": true,
      "foreign_key": null
    }
  ],
  "indexes": [],
  "constraints": [],
  "statistics": {
    "row_count": 150000,
    "table_size_bytes": 12456789,
    "index_size_bytes": 2345678,
    "last_analyzed": "2024-01-15T10:30:00Z"
  }
}
```

### 12. get_table_sample_data

Get a sample of data from a table.

**Parameters:**
```typescript
{
  "connection_name": string,     // Connection to use
  "table_name": string,         // Table name
  "schema_name": string,        // Schema name (optional)
  "sample_size": number,        // Number of rows to sample (optional)
  "sampling_method": string,    // random, first, last (optional)
  "columns": array              // Specific columns to include (optional)
}
```

### 13. analyze_table_profile

Perform data profiling analysis on a table.

**Parameters:**
```typescript
{
  "connection_name": string,     // Connection to use
  "table_name": string,         // Table name
  "schema_name": string,        // Schema name (optional)
  "columns": array,             // Specific columns to analyze (optional)
  "sample_percentage": number   // Percentage of data to sample (optional)
}
```

**Response:**
```json
{
  "success": true,
  "table_name": "sales",
  "analysis_date": "2024-01-15T10:30:00Z",
  "row_count": 150000,
  "column_profiles": [
    {
      "column_name": "amount",
      "data_type": "numeric",
      "null_count": 150,
      "null_percentage": 0.1,
      "unique_count": 45678,
      "min_value": 0.01,
      "max_value": 999999.99,
      "mean": 1234.56,
      "median": 567.89,
      "std_dev": 2345.67,
      "data_quality_score": 0.95
    }
  ]
}
```

### 14. optimize_table_performance

Analyze and suggest performance optimizations for a table.

**Parameters:**
```typescript
{
  "connection_name": string,     // Connection to use
  "table_name": string,         // Table name
  "schema_name": string,        // Schema name (optional)
  "include_index_analysis": boolean, // Analyze indexes (optional)
  "include_query_analysis": boolean  // Analyze query patterns (optional)
}
```

### 15. create_database_backup

Create a backup of database objects.

**Parameters:**
```typescript
{
  "connection_name": string,     // Connection to use
  "backup_type": string,        // full, schema, data
  "objects": array,             // Specific objects to backup (optional)
  "backup_location": string,    // Backup file path
  "compression": boolean        // Compress backup (optional)
}
```

### 16. get_database_size_info

Get size information for database objects.

**Parameters:**
```typescript
{
  "connection_name": string,     // Connection to use
  "object_type": string,        // tables, indexes, database (optional)
  "schema_name": string         // Schema filter (optional)
}
```

### 17. monitor_database_performance

Monitor database performance metrics.

**Parameters:**
```typescript
{
  "connection_name": string,     // Connection to use
  "metrics": array,             // Specific metrics to collect (optional)
  "duration_minutes": number    // Monitoring duration (optional)
}
```

## Utility Tools

### 18. convert_data_types

Convert data between different formats and types.

**Parameters:**
```typescript
{
  "data": any,                  // Data to convert
  "source_format": string,     // Source format (json, csv, xml)
  "target_format": string,     // Target format (json, csv, xml)
  "conversion_options": object  // Additional options (optional)
}
```

### 19. validate_sql_syntax

Validate SQL syntax without executing the query.

**Parameters:**
```typescript
{
  "connection_name": string,     // Connection for dialect validation
  "query": string,              // SQL query to validate
  "strict_mode": boolean        // Enable strict validation (optional)
}
```

**Response:**
```json
{
  "success": true,
  "query": "SELECT * FROM sales WHERE date >= '2024-01-01'",
  "valid": true,
  "syntax_errors": [],
  "warnings": [
    {
      "type": "performance",
      "message": "Query may benefit from an index on date column",
      "line": 1,
      "column": 30
    }
  ],
  "estimated_complexity": "medium"
}
```

### 20. format_sql_query

Format and beautify SQL queries.

**Parameters:**
```typescript
{
  "query": string,              // SQL query to format
  "style": string,              // Formatting style (optional)
  "indent_size": number,        // Indentation size (optional)
  "keyword_case": string        // upper, lower, title (optional)
}
```

### 21. generate_sample_data

Generate sample data for testing purposes.

**Parameters:**
```typescript
{
  "connection_name": string,     // Connection to use
  "table_name": string,         // Target table
  "row_count": number,          // Number of rows to generate
  "data_types": object,         // Column data type specifications
  "constraints": object         // Data constraints (optional)
}
```

### 22. export_query_results

Export query results to various formats.

**Parameters:**
```typescript
{
  "connection_name": string,     // Connection to use
  "query": string,              // Query to execute and export
  "export_format": string,      // csv, json, xlsx, parquet
  "file_path": string,          // Export file path
  "export_options": object      // Format-specific options (optional)
}
```

## SAP Integration Tools

### 23. connect_sap_system

Connect to SAP system using RFC.

**Parameters:**
```typescript
{
  "connection_name": string,     // SAP connection name
  "sap_host": string,           // SAP application server host
  "sap_sysnr": string,          // SAP system number
  "sap_client": string,         // SAP client
  "sap_user": string,           // SAP username
  "sap_password": string,       // SAP password
  "sap_language": string        // SAP language (optional)
}
```

### 24. execute_sap_rfc

Execute SAP RFC function calls.

**Parameters:**
```typescript
{
  "connection_name": string,     // SAP connection name
  "function_name": string,      // RFC function name
  "import_parameters": object,  // Import parameters (optional)
  "table_parameters": object,   // Table parameters (optional)
  "export_format": string       // Response format (optional)
}
```

### 25. get_sap_table_data

Extract data from SAP tables.

**Parameters:**
```typescript
{
  "connection_name": string,     // SAP connection name
  "table_name": string,         // SAP table name
  "fields": array,              // Fields to extract (optional)
  "where_condition": string,    // WHERE condition (optional)
  "max_rows": number            // Maximum rows (optional)
}
```

## Error Handling

All tools return standardized error responses when operations fail:

```json
{
  "success": false,
  "error": {
    "code": "CONNECTION_FAILED",
    "message": "Failed to connect to database",
    "details": {
      "connection_name": "prod_analytics",
      "host": "analytics.company.com",
      "error_type": "ConnectionError",
      "timestamp": "2024-01-15T10:30:00Z"
    },
    "suggestions": [
      "Check if the database server is running",
      "Verify network connectivity",
      "Check username and password"
    ]
  }
}
```

### Error Codes

| Code | Description | Common Causes |
|------|-------------|---------------|
| `CONNECTION_FAILED` | Database connection failed | Network, credentials, server down |
| `QUERY_EXECUTION_ERROR` | SQL query execution failed | Syntax error, permissions, timeout |
| `INVALID_PARAMETERS` | Invalid tool parameters | Missing required fields, wrong types |
| `TIMEOUT_ERROR` | Operation timed out | Long-running query, network latency |
| `PERMISSION_DENIED` | Insufficient permissions | Database user permissions |
| `RATE_LIMIT_EXCEEDED` | Too many requests | Rate limiting active |
| `CONFIGURATION_ERROR` | Configuration problem | Invalid config file, missing settings |
| `ENCRYPTION_ERROR` | Credential encryption/decryption failed | Wrong master password, corrupted data |

## Response Formats

### Standard Success Response

```json
{
  "success": true,
  "message": "Operation completed successfully",
  "data": {},
  "metadata": {
    "execution_time_ms": 123,
    "timestamp": "2024-01-15T10:30:00Z",
    "connection_name": "prod_analytics"
  }
}
```

### Query Result Formats

#### Table Format
```json
{
  "format": "table",
  "columns": ["id", "name", "amount"],
  "data": [
    [1, "Product A", 100.50],
    [2, "Product B", 200.75]
  ],
  "row_count": 2
}
```

#### JSON Format
```json
{
  "format": "json",
  "data": [
    {"id": 1, "name": "Product A", "amount": 100.50},
    {"id": 2, "name": "Product B", "amount": 200.75}
  ],
  "row_count": 2
}
```

#### CSV Format
```json
{
  "format": "csv",
  "data": "id,name,amount\n1,Product A,100.50\n2,Product B,200.75",
  "row_count": 2
}
```

## Performance Considerations

### Query Optimization

- Use `limit` parameter to avoid large result sets
- Set appropriate `timeout` values for long-running queries
- Use prepared statements for repeated queries
- Enable query result caching for frequently accessed data

### Connection Management

- Use connection pooling for high-frequency operations
- Test connections before use with `test_database_connection`
- Monitor connection health with performance monitoring tools
- Configure appropriate connection timeouts

### Security Best Practices

- Always use parameterized queries to prevent SQL injection
- Encrypt sensitive credentials using the built-in encryption
- Use SSL/TLS for remote database connections
- Configure rate limiting to prevent abuse
- Regularly audit database user permissions

## Tool Usage Examples

### Basic Query Example
```json
{
  "tool": "execute_sql_query",
  "parameters": {
    "connection_name": "analytics_db",
    "query": "SELECT product_category, COUNT(*) as product_count FROM products WHERE active = true GROUP BY product_category",
    "format": "json"
  }
}
```

### Table Analysis Example
```json
{
  "tool": "analyze_table_profile",
  "parameters": {
    "connection_name": "sales_db",
    "table_name": "customer_orders",
    "columns": ["order_amount", "customer_age", "order_date"],
    "sample_percentage": 10
  }
}
```

### Batch Operations Example
```json
{
  "tool": "execute_sql_batch",
  "parameters": {
    "connection_name": "etl_db",
    "queries": [
      "TRUNCATE TABLE staging_data",
      "INSERT INTO staging_data SELECT * FROM raw_data WHERE processed_date = CURRENT_DATE",
      "UPDATE staging_data SET status = 'processed' WHERE validation_check = true"
    ],
    "transaction": true
  }
}
```

---

This completes the API reference documentation. For more examples and advanced usage patterns, see the [Examples](examples/) directory.