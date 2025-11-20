# Basic Usage Examples

This document provides practical examples of using the ScikiQ Database Handler MCP Connector with Claude AI.

## Getting Started

### Example 1: Setting Up Your First Database Connection

**Claude Conversation:**
```
User: I need to connect to my PostgreSQL analytics database. The host is analytics.company.com, database name is "sales_data", and I have a read-only user account.

Claude: I'll help you set up a connection to your PostgreSQL database. Let me create a secure connection configuration for you.
```

**MCP Tool Call:**
```json
{
  "tool": "create_database_connection",
  "parameters": {
    "connection_name": "analytics_postgres",
    "database_type": "postgresql",
    "host": "analytics.company.com",
    "port": 5432,
    "database": "sales_data",
    "username": "readonly_user",
    "password": "your_secure_password",
    "ssl_config": {
      "ssl_mode": "require"
    }
  }
}
```

**Response:**
```json
{
  "success": true,
  "message": "Connection 'analytics_postgres' created successfully",
  "connection_id": "analytics_postgres",
  "encrypted": true
}
```

### Example 2: Testing the Connection

**Claude Conversation:**
```
User: Can you test if the connection is working properly?

Claude: I'll test the connection to ensure everything is set up correctly.
```

**MCP Tool Call:**
```json
{
  "tool": "test_database_connection",
  "parameters": {
    "connection_name": "analytics_postgres"
  }
}
```

**Response:**
```json
{
  "success": true,
  "connection_name": "analytics_postgres",
  "database_type": "postgresql",
  "host": "analytics.company.com",
  "database": "sales_data",
  "connection_time_ms": 45,
  "server_version": "PostgreSQL 13.7",
  "status": "Connected"
}
```

## Data Analysis Examples

### Example 3: Exploring Database Structure

**Claude Conversation:**
```
User: What tables are available in my database?

Claude: Let me explore the database schema to show you all available tables and their structure.
```

**MCP Tool Call:**
```json
{
  "tool": "get_database_schema",
  "parameters": {
    "connection_name": "analytics_postgres",
    "include_tables": true,
    "include_views": true
  }
}
```

**Response:**
```json
{
  "success": true,
  "schemas": [
    {
      "name": "public",
      "tables": [
        {
          "name": "customers",
          "type": "table",
          "columns": [
            {"name": "customer_id", "type": "integer", "primary_key": true},
            {"name": "customer_name", "type": "varchar(255)"},
            {"name": "email", "type": "varchar(255)"},
            {"name": "registration_date", "type": "date"}
          ]
        },
        {
          "name": "orders",
          "type": "table",
          "columns": [
            {"name": "order_id", "type": "integer", "primary_key": true},
            {"name": "customer_id", "type": "integer"},
            {"name": "order_date", "type": "timestamp"},
            {"name": "total_amount", "type": "decimal(10,2)"}
          ]
        }
      ]
    }
  ]
}
```

### Example 4: Simple Data Query

**Claude Conversation:**
```
User: Show me the top 10 customers by total order value this year.

Claude: I'll query your orders and customers tables to find the top 10 customers by total order value for this year.
```

**MCP Tool Call:**
```json
{
  "tool": "execute_sql_query",
  "parameters": {
    "connection_name": "analytics_postgres",
    "query": "SELECT c.customer_name, c.email, SUM(o.total_amount) as total_spent FROM customers c JOIN orders o ON c.customer_id = o.customer_id WHERE EXTRACT(YEAR FROM o.order_date) = EXTRACT(YEAR FROM CURRENT_DATE) GROUP BY c.customer_id, c.customer_name, c.email ORDER BY total_spent DESC LIMIT 10",
    "format": "json"
  }
}
```

**Response:**
```json
{
  "success": true,
  "execution_time_ms": 156,
  "row_count": 10,
  "data": [
    {"customer_name": "John Smith", "email": "john.smith@email.com", "total_spent": 15420.50},
    {"customer_name": "Sarah Johnson", "email": "sarah.j@email.com", "total_spent": 12650.75},
    {"customer_name": "Michael Brown", "email": "m.brown@email.com", "total_spent": 11890.25}
  ]
}
```

### Example 5: Data Analysis with Parameters

**Claude Conversation:**
```
User: Can you analyze sales trends for a specific product category? I'm interested in "Electronics" category for the last 6 months.

Claude: I'll analyze the sales trends for Electronics over the last 6 months, showing monthly totals and growth rates.
```

**MCP Tool Call:**
```json
{
  "tool": "execute_sql_query",
  "parameters": {
    "connection_name": "analytics_postgres",
    "query": "WITH monthly_sales AS (SELECT DATE_TRUNC('month', o.order_date) as month, SUM(oi.quantity * oi.unit_price) as monthly_total FROM orders o JOIN order_items oi ON o.order_id = oi.order_id JOIN products p ON oi.product_id = p.product_id WHERE p.category = ? AND o.order_date >= CURRENT_DATE - INTERVAL '6 months' GROUP BY DATE_TRUNC('month', o.order_date) ORDER BY month) SELECT month, monthly_total, LAG(monthly_total) OVER (ORDER BY month) as prev_month_total, CASE WHEN LAG(monthly_total) OVER (ORDER BY month) > 0 THEN ROUND(((monthly_total - LAG(monthly_total) OVER (ORDER BY month)) / LAG(monthly_total) OVER (ORDER BY month) * 100), 2) END as growth_rate_percent FROM monthly_sales",
    "parameters": ["Electronics"],
    "format": "json"
  }
}
```

## Advanced Analysis Examples

### Example 6: Table Profiling and Data Quality

**Claude Conversation:**
```
User: I want to understand the data quality of my customers table. Can you analyze it for me?

Claude: I'll perform a comprehensive data profiling analysis on your customers table to assess data quality and provide insights.
```

**MCP Tool Call:**
```json
{
  "tool": "analyze_table_profile",
  "parameters": {
    "connection_name": "analytics_postgres",
    "table_name": "customers",
    "sample_percentage": 100
  }
}
```

**Response:**
```json
{
  "success": true,
  "table_name": "customers",
  "analysis_date": "2024-01-15T10:30:00Z",
  "row_count": 25000,
  "column_profiles": [
    {
      "column_name": "customer_name",
      "data_type": "varchar",
      "null_count": 0,
      "null_percentage": 0.0,
      "unique_count": 24890,
      "duplicate_count": 110,
      "data_quality_score": 0.96,
      "issues": ["Some duplicate names found"]
    },
    {
      "column_name": "email",
      "data_type": "varchar",
      "null_count": 45,
      "null_percentage": 0.18,
      "unique_count": 24955,
      "duplicate_count": 0,
      "data_quality_score": 0.99,
      "pattern_analysis": {
        "valid_email_format": 99.8,
        "invalid_email_format": 0.2
      }
    }
  ]
}
```

### Example 7: Performance Optimization

**Claude Conversation:**
```
User: My queries on the orders table are running slowly. Can you help optimize performance?

Claude: I'll analyze the orders table structure and suggest performance optimizations including potential indexes.
```

**MCP Tool Call:**
```json
{
  "tool": "optimize_table_performance",
  "parameters": {
    "connection_name": "analytics_postgres",
    "table_name": "orders",
    "include_index_analysis": true,
    "include_query_analysis": true
  }
}
```

**Response:**
```json
{
  "success": true,
  "table_name": "orders",
  "current_performance": {
    "table_size_mb": 1250,
    "index_size_mb": 320,
    "avg_query_time_ms": 2340
  },
  "recommendations": [
    {
      "type": "index",
      "priority": "high",
      "description": "Create index on order_date column",
      "sql": "CREATE INDEX idx_orders_order_date ON orders (order_date);",
      "estimated_improvement": "60% faster date range queries"
    },
    {
      "type": "index",
      "priority": "medium", 
      "description": "Create composite index for customer queries",
      "sql": "CREATE INDEX idx_orders_customer_date ON orders (customer_id, order_date);",
      "estimated_improvement": "40% faster customer history queries"
    }
  ]
}
```

## Multi-Database Examples

### Example 8: Working with Multiple Databases

**Claude Conversation:**
```
User: I have data in both PostgreSQL and MySQL databases. Can you help me compare customer counts between them?

Claude: I'll connect to both databases and compare customer counts to help you understand the data distribution.
```

**Setup connections:**
```json
{
  "tool": "create_database_connection",
  "parameters": {
    "connection_name": "mysql_prod",
    "database_type": "mysql",
    "host": "mysql.company.com",
    "port": 3306,
    "database": "production",
    "username": "analyst",
    "password": "secure_password"
  }
}
```

**Query PostgreSQL:**
```json
{
  "tool": "execute_sql_query",
  "parameters": {
    "connection_name": "analytics_postgres",
    "query": "SELECT 'PostgreSQL' as database, COUNT(*) as customer_count FROM customers",
    "format": "json"
  }
}
```

**Query MySQL:**
```json
{
  "tool": "execute_sql_query",
  "parameters": {
    "connection_name": "mysql_prod",
    "query": "SELECT 'MySQL' as database, COUNT(*) as customer_count FROM customers",
    "format": "json"
  }
}
```

### Example 9: Cross-Database Data Analysis

**Claude Conversation:**
```
User: I need to combine sales data from my PostgreSQL warehouse with product information from MySQL. How can I do this?

Claude: I'll extract data from both databases and help you combine them for analysis. Let me get the sales data from PostgreSQL and product data from MySQL.
```

**Get sales data:**
```json
{
  "tool": "execute_sql_query",
  "parameters": {
    "connection_name": "analytics_postgres",
    "query": "SELECT product_id, SUM(quantity) as total_sold, SUM(total_amount) as revenue FROM order_items oi JOIN orders o ON oi.order_id = o.order_id WHERE o.order_date >= CURRENT_DATE - INTERVAL '30 days' GROUP BY product_id",
    "format": "json"
  }
}
```

**Get product information:**
```json
{
  "tool": "execute_sql_query",
  "parameters": {
    "connection_name": "mysql_prod",
    "query": "SELECT product_id, product_name, category, unit_cost FROM products WHERE status = 'active'",
    "format": "json"
  }
}
```

## Cloud Database Examples

### Example 10: Snowflake Data Warehouse

**Claude Conversation:**
```
User: I need to connect to our Snowflake data warehouse and analyze large datasets efficiently.

Claude: I'll help you connect to Snowflake and run efficient queries on your large datasets.
```

**Setup Snowflake connection:**
```json
{
  "tool": "create_database_connection",
  "parameters": {
    "connection_name": "snowflake_warehouse",
    "database_type": "snowflake",
    "account": "company.snowflakecomputing.com",
    "warehouse": "ANALYTICS_WH",
    "database": "PRODUCTION",
    "schema": "SALES",
    "username": "analyst",
    "password": "secure_password",
    "role": "ANALYST_ROLE"
  }
}
```

**Large dataset analysis:**
```json
{
  "tool": "execute_sql_query",
  "parameters": {
    "connection_name": "snowflake_warehouse",
    "query": "SELECT DATE_TRUNC('week', order_date) as week, region, SUM(amount) as weekly_sales FROM fact_sales WHERE order_date >= DATEADD(month, -3, CURRENT_DATE) GROUP BY DATE_TRUNC('week', order_date), region ORDER BY week DESC, weekly_sales DESC",
    "limit": 1000,
    "format": "json"
  }
}
```

### Example 11: Google BigQuery Analytics

**Claude Conversation:**
```
User: I have web analytics data in BigQuery. Can you help me analyze user behavior patterns?

Claude: I'll connect to your BigQuery dataset and analyze user behavior patterns from your web analytics data.
```

**Setup BigQuery connection:**
```json
{
  "tool": "create_database_connection",
  "parameters": {
    "connection_name": "bigquery_analytics",
    "database_type": "bigquery",
    "project_id": "company-analytics-project",
    "credentials_file": "/path/to/service-account.json"
  }
}
```

**User behavior analysis:**
```json
{
  "tool": "execute_sql_query",
  "parameters": {
    "connection_name": "bigquery_analytics",
    "query": "WITH user_sessions AS (SELECT user_id, session_id, COUNT(page_view) as page_views, TIMESTAMP_DIFF(MAX(timestamp), MIN(timestamp), MINUTE) as session_duration_minutes FROM `company-analytics-project.web_analytics.page_views` WHERE DATE(timestamp) >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY) GROUP BY user_id, session_id) SELECT CASE WHEN page_views = 1 THEN 'Single Page' WHEN page_views BETWEEN 2 AND 5 THEN 'Browse' WHEN page_views BETWEEN 6 AND 15 THEN 'Engaged' ELSE 'Power User' END as user_type, COUNT(*) as sessions, AVG(session_duration_minutes) as avg_duration, AVG(page_views) as avg_page_views FROM user_sessions GROUP BY 1 ORDER BY sessions DESC",
    "format": "json"
  }
}
```

## Data Export and Integration

### Example 12: Exporting Query Results

**Claude Conversation:**
```
User: I need to export the sales analysis results to a CSV file for my team to review.

Claude: I'll run the sales analysis query and export the results to a CSV file for you.
```

**Export to CSV:**
```json
{
  "tool": "export_query_results",
  "parameters": {
    "connection_name": "analytics_postgres",
    "query": "SELECT p.product_name, p.category, SUM(oi.quantity) as units_sold, SUM(oi.quantity * oi.unit_price) as revenue FROM products p JOIN order_items oi ON p.product_id = oi.product_id JOIN orders o ON oi.order_id = o.order_id WHERE o.order_date >= CURRENT_DATE - INTERVAL '90 days' GROUP BY p.product_id, p.product_name, p.category ORDER BY revenue DESC",
    "export_format": "csv",
    "file_path": "sales_analysis_q4.csv",
    "export_options": {
      "include_headers": true,
      "delimiter": ",",
      "encoding": "utf-8"
    }
  }
}
```

### Example 13: Batch Data Processing

**Claude Conversation:**
```
User: I need to run a series of data processing steps to clean and aggregate our daily sales data.

Claude: I'll execute a batch of SQL statements to process your daily sales data in the correct order.
```

**Batch processing:**
```json
{
  "tool": "execute_sql_batch",
  "parameters": {
    "connection_name": "analytics_postgres",
    "queries": [
      "-- Step 1: Create temporary staging table",
      "CREATE TEMP TABLE daily_sales_staging AS SELECT * FROM raw_daily_sales WHERE processing_date = CURRENT_DATE",
      
      "-- Step 2: Clean and validate data",
      "DELETE FROM daily_sales_staging WHERE sale_amount <= 0 OR customer_id IS NULL",
      
      "-- Step 3: Calculate aggregated metrics",
      "INSERT INTO daily_sales_summary (sale_date, total_revenue, transaction_count, avg_transaction_value) SELECT DATE(sale_timestamp), SUM(sale_amount), COUNT(*), AVG(sale_amount) FROM daily_sales_staging GROUP BY DATE(sale_timestamp)",
      
      "-- Step 4: Update customer lifetime value",
      "UPDATE customers SET lifetime_value = (SELECT COALESCE(SUM(sale_amount), 0) FROM daily_sales_staging WHERE daily_sales_staging.customer_id = customers.customer_id) + COALESCE(lifetime_value, 0) WHERE customer_id IN (SELECT DISTINCT customer_id FROM daily_sales_staging)"
    ],
    "transaction": true,
    "continue_on_error": false
  }
}
```

## NoSQL Database Examples

### Example 14: MongoDB Document Analysis

**Claude Conversation:**
```
User: I have customer data stored in MongoDB. Can you help me analyze customer segments?

Claude: I'll connect to your MongoDB database and analyze customer segments based on their document data.
```

**Setup MongoDB connection:**
```json
{
  "tool": "create_database_connection",
  "parameters": {
    "connection_name": "mongo_customers",
    "database_type": "mongodb",
    "host": "mongo-cluster.company.com",
    "port": 27017,
    "database": "customer_data",
    "username": "analyst",
    "password": "secure_password",
    "auth_source": "admin"
  }
}
```

**Customer segmentation analysis:**
```json
{
  "tool": "execute_sql_query",
  "parameters": {
    "connection_name": "mongo_customers",
    "query": "db.customers.aggregate([{$group: {_id: '$demographics.age_group', count: {$sum: 1}, avg_order_value: {$avg: '$purchase_history.avg_order_value'}, total_customers: {$sum: 1}}}, {$sort: {count: -1}}])",
    "format": "json"
  }
}
```

### Example 15: DuckDB with S3 Storage

**Claude Conversation:**
```
User: I have data files stored in S3 buckets organized in folders. I want to query them as if they were database tables using DuckDB.

Claude: I'll help you set up DuckDB with S3 support where folders in your S3 bucket are treated as database tables. This is perfect for data lake analytics.
```

**Setup DuckDB S3 connection:**
```json
{
  "tool": "create_database_connection",
  "parameters": {
    "connection_name": "duckdb_s3_data",
    "database_type": "duckdb",
    "database_path": ":memory:",
    "enable_s3": true,
    "s3_bucket": "company-data-lake",
    "s3_prefix": "analytics/tables/",
    "s3_region": "us-east-1",
    "s3_access_key_id": "your_access_key",
    "s3_secret_access_key": "your_secret_key",
    "default_file_format": "parquet"
  }
}
```

**List available tables (S3 folders):**
```json
{
  "tool": "execute_sql_query",
  "parameters": {
    "connection_name": "duckdb_s3_data",
    "query": "SHOW TABLES",
    "format": "json"
  }
}
```

**Query S3 data as tables:**
```json
{
  "tool": "execute_sql_query",
  "parameters": {
    "connection_name": "duckdb_s3_data",
    "query": "SELECT product_category, SUM(sales_amount) as total_sales, COUNT(*) as transaction_count FROM sales_data WHERE sale_date >= '2024-01-01' GROUP BY product_category ORDER BY total_sales DESC",
    "format": "json"
  }
}
```

**Cross-folder analytics:**
```json
{
  "tool": "execute_sql_query", 
  "parameters": {
    "connection_name": "duckdb_s3_data",
    "query": "SELECT c.customer_segment, p.product_category, SUM(s.sales_amount) as revenue FROM sales_data s JOIN customers c ON s.customer_id = c.customer_id JOIN products p ON s.product_id = p.product_id WHERE s.sale_date >= '2024-01-01' GROUP BY c.customer_segment, p.product_category ORDER BY revenue DESC",
    "format": "json"
  }
}
```

**Response with S3 data:**
```json
{
  "success": true,
  "execution_time_ms": 2340,
  "row_count": 25,
  "data": [
    {"customer_segment": "Enterprise", "product_category": "Software", "revenue": 2450000},
    {"customer_segment": "Mid-Market", "product_category": "Hardware", "revenue": 1890000},
    {"customer_segment": "SMB", "product_category": "Services", "revenue": 1250000}
  ],
  "s3_files_processed": 156,
  "data_scanned_mb": 3420
}
```

## Error Handling Examples

### Example 15: Handling Connection Issues

**Claude Conversation:**
```
User: I'm getting connection errors when trying to access my database. Can you help troubleshoot?

Claude: I'll test the connection and help diagnose the issue.
```

**Test connection with error handling:**
```json
{
  "tool": "test_database_connection",
  "parameters": {
    "connection_name": "problematic_db"
  }
}
```

**Response with error:**
```json
{
  "success": false,
  "error": {
    "code": "CONNECTION_FAILED",
    "message": "Failed to connect to database",
    "details": {
      "connection_name": "problematic_db",
      "host": "db.company.com",
      "error_type": "ConnectionTimeout",
      "timestamp": "2024-01-15T10:30:00Z"
    },
    "suggestions": [
      "Check if the database server is running",
      "Verify network connectivity to db.company.com",
      "Check firewall rules on port 5432",
      "Verify username and password are correct"
    ]
  }
}
```

### Example 16: Query Validation

**Claude Conversation:**
```
User: I want to make sure my SQL query is correct before running it on production data.

Claude: I'll validate your SQL query syntax and check for potential issues before execution.
```

**Validate SQL syntax:**
```json
{
  "tool": "validate_sql_syntax",
  "parameters": {
    "connection_name": "analytics_postgres",
    "query": "SELECT customer_name, SUM(order_total) FROM customers c JOIN orders o ON c.id = o.customer_id WHERE order_date >= '2024-01-01' GROUP BY customer_name ORDER BY SUM(order_total) DESC",
    "strict_mode": true
  }
}
```

**Response with validation results:**
```json
{
  "success": true,
  "valid": true,
  "syntax_errors": [],
  "warnings": [
    {
      "type": "performance",
      "message": "Consider adding an index on orders.order_date for better performance",
      "line": 1,
      "column": 95
    },
    {
      "type": "style",
      "message": "Use table aliases consistently (orders table not aliased)",
      "line": 1,
      "column": 85
    }
  ],
  "estimated_complexity": "medium"
}
```

## Best Practices Examples

### Example 17: Secure Query with Parameters

**Claude Conversation:**
```
User: I need to look up specific customer orders, but I want to make sure I'm using secure practices.

Claude: I'll show you how to use parameterized queries to safely look up customer data.
```

**Secure parameterized query:**
```json
{
  "tool": "execute_sql_query",
  "parameters": {
    "connection_name": "analytics_postgres",
    "query": "SELECT o.order_id, o.order_date, o.total_amount, c.customer_name FROM orders o JOIN customers c ON o.customer_id = c.customer_id WHERE c.email = ? AND o.order_date >= ?",
    "parameters": ["customer@email.com", "2024-01-01"],
    "format": "json"
  }
}
```

### Example 18: Monitoring Query Performance

**Claude Conversation:**
```
User: I want to monitor the performance of my queries to ensure they're running efficiently.

Claude: I'll show you how to get execution plans and monitor query performance.
```

**Get query execution plan:**
```json
{
  "tool": "get_query_explain_plan",
  "parameters": {
    "connection_name": "analytics_postgres",
    "query": "SELECT c.customer_name, COUNT(o.order_id) as order_count, SUM(o.total_amount) as total_spent FROM customers c LEFT JOIN orders o ON c.customer_id = o.customer_id WHERE o.order_date >= CURRENT_DATE - INTERVAL '1 year' GROUP BY c.customer_id, c.customer_name HAVING COUNT(o.order_id) > 5 ORDER BY total_spent DESC"
  }
}
```

**Response with execution plan:**
```json
{
  "success": true,
  "execution_plan": [
    {
      "operation": "Sort",
      "cost": "1234.56..1245.67",
      "rows": 500,
      "sort_key": "total_spent DESC"
    },
    {
      "operation": "HashAggregate",
      "cost": "1200.00..1234.56", 
      "rows": 500,
      "group_key": "customer_id, customer_name"
    },
    {
      "operation": "Hash Join",
      "cost": "856.78..1200.00",
      "rows": 15000,
      "join_type": "Left Hash Join"
    }
  ],
  "estimated_cost": 1245.67,
  "estimated_rows": 500,
  "recommendations": [
    "Consider adding composite index on (customer_id, order_date)",
    "Query will benefit from increased work_mem setting"
  ]
}
```

---

These examples demonstrate the practical usage patterns of the ScikiQ Database Handler MCP Connector. For more advanced scenarios and specific use cases, refer to the [Configuration Guide](../configuration.md) and [API Reference](../api_reference.md).