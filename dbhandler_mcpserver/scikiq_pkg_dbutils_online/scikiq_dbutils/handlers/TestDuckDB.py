"""
Test script for DuckDB Handler with S3 support.

This script demonstrates how to use the DuckDB handler with AWS S3 storage,
treating folders in S3 buckets as tables.
"""

import os
import sys
import json
import pandas as pd
from datetime import datetime

# Add the package path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scikiq_dbutils.handlers.DuckDBHandler import clsDuckDB


def test_duckdb_local():
    """Test DuckDB with local in-memory database."""
    print("=== Testing DuckDB Local Mode ===")
    
    # Configuration for local DuckDB
    local_config = {
        "database_path": ":memory:",
        "enable_s3": False,
        "resource_key": "test_duckdb_local"
    }
    
    try:
        # Initialize handler
        duckdb_handler = clsDuckDB(local_config)
        
        # Test connection
        result = duckdb_handler.testConnection()
        print(f"Connection test: {result}")
        
        # Create sample data
        sample_data = pd.DataFrame({
            'id': [1, 2, 3, 4, 5],
            'name': ['Alice', 'Bob', 'Charlie', 'David', 'Eve'],
            'age': [25, 30, 35, 28, 32],
            'salary': [50000, 60000, 75000, 55000, 68000],
            'created_date': pd.date_range('2024-01-01', periods=5)
        })
        
        # Connect and create table from DataFrame
        duckdb_handler.connect()
        duckdb_handler.connection.register('employees', sample_data)
        
        # Test query execution
        query_result = duckdb_handler.executeQuery("SELECT * FROM employees WHERE age > 30")
        print(f"Query result shape: {query_result.shape}")
        print(f"Query result:\n{query_result}")
        
        # Test table listing
        tables = duckdb_handler.get_all_tables()
        print(f"Available tables: {tables}")
        
        # Test column information
        columns = duckdb_handler.getTableColumns('employees')
        print(f"Table columns: {columns}")
        
        # Test column details
        column_details = duckdb_handler.getTableColumnsDetails('employees')
        print(f"Column details: {column_details}")
        
        # Clean up
        duckdb_handler.close()
        
        print("✅ Local DuckDB test completed successfully!")
        
    except Exception as e:
        print(f"❌ Local DuckDB test failed: {str(e)}")
        import traceback
        traceback.print_exc()


def test_duckdb_s3():
    """Test DuckDB with S3 storage (requires AWS credentials)."""
    print("\n=== Testing DuckDB S3 Mode ===")
    
    # Note: This requires valid AWS credentials and S3 bucket
    # Replace with your actual AWS credentials and bucket
    s3_config = {
        "database_path": ":memory:",
        "enable_s3": True,
        "s3_bucket": "your-test-bucket",  # Replace with actual bucket
        "s3_prefix": "duckdb_tables/",
        "s3_region": "us-east-1",
        "s3_access_key_id": "YOUR_ACCESS_KEY",  # Replace with actual key
        "s3_secret_access_key": "YOUR_SECRET_KEY",  # Replace with actual key
        "default_file_format": "parquet",
        "resource_key": "test_duckdb_s3"
    }
    
    # Skip S3 test if credentials are not provided
    if (s3_config["s3_access_key_id"] == "YOUR_ACCESS_KEY" or 
        s3_config["s3_bucket"] == "your-test-bucket"):
        print("⚠️  Skipping S3 test - please provide valid AWS credentials and bucket")
        return
    
    try:
        # Initialize handler
        duckdb_handler = clsDuckDB(s3_config)
        
        # Test connection
        result = duckdb_handler.testConnection()
        print(f"S3 connection test: {result}")
        
        if result['error'] == 0:
            # List S3 tables (folders)
            tables = duckdb_handler.get_all_tables()
            print(f"S3 tables (folders): {tables}")
            
            # If tables exist, test querying one
            if tables:
                first_table = tables[0]['table_name']
                print(f"Testing table: {first_table}")
                
                # Get table schema
                columns = duckdb_handler.getTableColumns(first_table)
                print(f"Table columns: {columns}")
                
                # Query sample data
                sample_query = f"SELECT * FROM {first_table} LIMIT 5"
                result_data = duckdb_handler.executeQuery(sample_query)
                print(f"Sample data shape: {result_data.shape}")
                print(f"Sample data:\n{result_data}")
                
            else:
                print("No S3 tables found in the specified bucket/prefix")
            
            # Test creating a new "table" (S3 folder)
            create_result = duckdb_handler.createTable("test_table")
            print(f"Create table result: {create_result}")
        
        print("✅ S3 DuckDB test completed!")
        
    except Exception as e:
        print(f"❌ S3 DuckDB test failed: {str(e)}")
        import traceback
        traceback.print_exc()


def demo_s3_table_operations():
    """Demonstrate S3 table operations with sample data."""
    print("\n=== Demo: S3 Table Operations ===")
    
    # This is a conceptual demo showing how S3 operations would work
    print("""
    DuckDB S3 Handler Capabilities:
    
    1. Folder-as-Table Abstraction:
       - S3 folders are treated as database tables
       - Files within folders are treated as table data
       - Supports Parquet, CSV, and JSON formats
    
    2. Query Examples:
       # Query a Parquet table in S3
       SELECT * FROM sales_data WHERE date >= '2024-01-01'
       
       # Aggregate across multiple files
       SELECT region, SUM(amount) 
       FROM transactions 
       GROUP BY region
       
       # Join multiple S3 tables
       SELECT c.name, SUM(o.total)
       FROM customers c
       JOIN orders o ON c.id = o.customer_id
       GROUP BY c.name
    
    3. Performance Benefits:
       - Columnar storage with Parquet
       - Pushdown predicates to S3
       - Parallel processing of files
       - Memory-efficient streaming
    
    4. S3 Structure Example:
       my-bucket/
       ├── data/tables/
       │   ├── customers/
       │   │   ├── part-001.parquet
       │   │   ├── part-002.parquet
       │   │   └── part-003.parquet
       │   ├── orders/
       │   │   ├── 2024-01.parquet
       │   │   ├── 2024-02.parquet
       │   │   └── 2024-03.parquet
       │   └── products/
       │       └── products.csv
    
    5. Configuration Tips:
       - Use IAM roles for better security
       - Consider S3 Transfer Acceleration for large datasets
       - Partition data by date/region for better performance
       - Use columnar formats (Parquet) for analytics workloads
    """)


def create_sample_config():
    """Create sample configuration files."""
    print("\n=== Creating Sample Configuration ===")
    
    # Local DuckDB configuration
    local_config = {
        "dbType": "DUCKDB",
        "database_path": "/path/to/local/database.duckdb",
        "enable_s3": False,
        "resource_key": "local_duckdb_connection"
    }
    
    # S3 DuckDB configuration
    s3_config = {
        "dbType": "DUCKDB", 
        "database_path": ":memory:",
        "enable_s3": True,
        "s3_bucket": "my-data-warehouse",
        "s3_prefix": "tables/",
        "s3_region": "us-east-1",
        "s3_access_key_id": "${AWS_ACCESS_KEY_ID}",
        "s3_secret_access_key": "${AWS_SECRET_ACCESS_KEY}",
        "default_file_format": "parquet",
        "resource_key": "s3_duckdb_connection"
    }
    
    # Save configurations
    with open('duckdb_local_config.json', 'w') as f:
        json.dump(local_config, f, indent=2)
    
    with open('duckdb_s3_config.json', 'w') as f:
        json.dump(s3_config, f, indent=2)
    
    print("✅ Sample configuration files created:")
    print("   - duckdb_local_config.json (Local DuckDB)")
    print("   - duckdb_s3_config.json (S3 DuckDB)")
    
    # Create sample MCP configuration
    mcp_config = {
        "mcpServers": {
            "scikiq-dbhandler": {
                "command": "python",
                "args": ["-m", "scikiq_dbutils.mcp_server.main"],
                "env": {
                    "DBHANDLER_MASTER_PASSWORD": "your-secure-master-password"
                }
            }
        }
    }
    
    with open('claude_desktop_config_duckdb.json', 'w') as f:
        json.dump(mcp_config, f, indent=2)
    
    print("   - claude_desktop_config_duckdb.json (Claude MCP config)")


if __name__ == "__main__":
    print("DuckDB Handler Test Suite")
    print("=" * 50)
    
    # Test local DuckDB
    test_duckdb_local()
    
    # Test S3 DuckDB (if credentials available)
    test_duckdb_s3()
    
    # Show demo information
    demo_s3_table_operations()
    
    # Create sample configurations
    create_sample_config()
    
    print("\n" + "=" * 50)
    print("Test suite completed!")
    print("""
    Next steps:
    1. Install dependencies: pip install duckdb boto3 s3fs
    2. Configure AWS credentials 
    3. Update S3 bucket and credentials in config
    4. Add DuckDB connection to your MCP configuration
    5. Test with Claude Desktop
    """)