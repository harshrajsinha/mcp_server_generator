"""
Example Database Configurations

This file contains example configurations for various database types
supported by the ScikiQ Database MCP Server.
"""

# MySQL Configuration
MYSQL_CONFIG = {
    "dbType": "MYSQL",
    "hostname": "localhost",
    "port": 3306,
    "dbname": "myapp",
    "dbuser": "appuser",
    "dbpassword": "securepassword",
    "schema": "public"
}

# MySQL with SSL
MYSQL_SSL_CONFIG = {
    "dbType": "MYSQL", 
    "hostname": "mysql.example.com",
    "port": 3306,
    "dbname": "production",
    "dbuser": "prod_user",
    "dbpassword": "prod_password",
    "connectivity_mechanism": "S",
    "pem_path": "/path/to/mysql-ca-cert.pem"
}

# PostgreSQL Configuration
POSTGRES_CONFIG = {
    "dbType": "POSTGRES",
    "hostname": "localhost", 
    "port": 5432,
    "dbname": "analytics",
    "dbuser": "analyst",
    "dbpassword": "analyst_password",
    "schema": "analytics"
}

# Oracle Configuration
ORACLE_CONFIG = {
    "dbType": "ORACLE",
    "hostname": "oracle.company.com",
    "port": 1521,
    "dbname": "ORCL",  # Service name or SID
    "dbuser": "hr_user",
    "dbpassword": "hr_password",
    "schema": "HR"
}

# SQL Server Configuration
SQLSERVER_CONFIG = {
    "dbType": "SQLSERVER",
    "hostname": "sqlserver.company.com",
    "port": 1433,
    "dbname": "CompanyDB",
    "dbuser": "sa",
    "dbpassword": "SqlPassword123",
    "schema": "dbo"
}

# Snowflake Configuration
SNOWFLAKE_CONFIG = {
    "dbType": "SNOWFLAKE",
    "hostname": "account.snowflakecomputing.com",
    "port": 443,
    "dbname": "ANALYTICS_DB",
    "dbuser": "data_analyst",
    "dbpassword": "snowflake_password", 
    "warehouse": "ANALYTICS_WH",
    "account": "your_account_name",
    "role": "ANALYST_ROLE",
    "schema": "PUBLIC"
}

# BigQuery Configuration (uses service account)
BIGQUERY_CONFIG = {
    "dbType": "BIGQUERY",
    "hostname": "bigquery.googleapis.com",
    "dbname": "your-project-id",
    "dbuser": "service-account@project.iam.gserviceaccount.com",
    "dbpassword": "/path/to/service-account-key.json",  # Path to service account JSON
    "schema": "dataset_name"
}

# Redshift Configuration
REDSHIFT_CONFIG = {
    "dbType": "REDSHIFT", 
    "hostname": "redshift-cluster.amazonaws.com",
    "port": 5439,
    "dbname": "datawarehouse",
    "dbuser": "dwh_user",
    "dbpassword": "redshift_password",
    "schema": "public"
}

# MongoDB Configuration
MONGODB_CONFIG = {
    "dbType": "MONGODB",
    "hostname": "mongodb.company.com",
    "port": 27017,
    "dbname": "application_db",
    "dbuser": "app_user", 
    "dbpassword": "mongo_password"
}

# SAP HANA Configuration
SAPHANA_CONFIG = {
    "dbType": "SAPHANA",
    "hostname": "hana.company.com", 
    "port": 30015,
    "dbname": "HXE",
    "dbuser": "SYSTEM",
    "dbpassword": "hana_password",
    "schema": "SYSTEM"
}

# Vertica Configuration
VERTICA_CONFIG = {
    "dbType": "VERTICA",
    "hostname": "vertica.company.com",
    "port": 5433,
    "dbname": "analytics_db",
    "dbuser": "dbadmin", 
    "dbpassword": "vertica_password",
    "schema": "public"
}

# SSH Tunnel Example (MySQL through SSH)
MYSQL_SSH_CONFIG = {
    "dbType": "MYSQL",
    "hostname": "internal-mysql.company.com",  # Internal hostname
    "port": 3306,
    "dbname": "internal_db",
    "dbuser": "internal_user",
    "dbpassword": "internal_password",
    "connectivity_mechanism": "SSH",
    "ssh_host": "bastion.company.com",  # SSH jump host
    "ssh_user": "ssh_user",
    "ssh_port": 22,
    "ssh_key_path": "/path/to/ssh/private/key"
}

# Complete configuration file example
EXAMPLE_CONNECTIONS_CONFIG = {
    "connections": {
        "dev_mysql": MYSQL_CONFIG,
        "prod_mysql": MYSQL_SSL_CONFIG,
        "analytics_postgres": POSTGRES_CONFIG,
        "hr_oracle": ORACLE_CONFIG,
        "company_sqlserver": SQLSERVER_CONFIG,
        "dwh_snowflake": SNOWFLAKE_CONFIG,
        "analytics_bigquery": BIGQUERY_CONFIG,
        "dwh_redshift": REDSHIFT_CONFIG,
        "app_mongodb": MONGODB_CONFIG,
        "erp_saphana": SAPHANA_CONFIG,
        "analytics_vertica": VERTICA_CONFIG,
        "secure_mysql": MYSQL_SSH_CONFIG
    },
    "metadata": {
        "created_at": "2024-01-01T00:00:00Z",
        "description": "Example database connections for ScikiQ MCP Server",
        "version": "1.0"
    }
}

# Environment-specific configurations
DEVELOPMENT_CONFIG = {
    "connections": {
        "local_mysql": {
            "dbType": "MYSQL",
            "hostname": "localhost",
            "port": 3306,
            "dbname": "dev_app",
            "dbuser": "dev_user",
            "dbpassword": "dev_password"
        },
        "local_postgres": {
            "dbType": "POSTGRES", 
            "hostname": "localhost",
            "port": 5432,
            "dbname": "dev_analytics",
            "dbuser": "postgres",
            "dbpassword": "postgres"
        }
    }
}

PRODUCTION_CONFIG = {
    "connections": {
        "prod_primary": {
            "dbType": "POSTGRES",
            "hostname": "prod-primary.company.com", 
            "port": 5432,
            "dbname": "production", 
            "dbuser": "app_prod",
            "dbpassword": "secure_prod_password",
            "connectivity_mechanism": "S",
            "ssl_ca_path": "/etc/ssl/certs/ca-cert.pem",
            "ssl_cert_path": "/etc/ssl/certs/client-cert.pem",
            "ssl_key_path": "/etc/ssl/private/client-key.pem"
        },
        "prod_dwh": {
            "dbType": "SNOWFLAKE",
            "hostname": "company.snowflakecomputing.com",
            "port": 443, 
            "dbname": "PROD_DWH",
            "dbuser": "dwh_service",
            "dbpassword": "dwh_service_password",
            "warehouse": "PROD_WH",
            "account": "company_prod",
            "role": "DWH_SERVICE_ROLE"
        }
    }
}

# Helper function to create configuration files
def create_config_file(config_dict: dict, filename: str):
    """Create a configuration file from a configuration dictionary"""
    import json
    import os
    
    config_dir = os.path.expanduser("~/.scikiq_mcp")
    os.makedirs(config_dir, exist_ok=True)
    
    config_path = os.path.join(config_dir, filename)
    
    with open(config_path, 'w') as f:
        json.dump(config_dict, f, indent=2)
    
    print(f"Configuration saved to: {config_path}")

# Example usage:
if __name__ == "__main__":
    # Create example configuration files
    create_config_file(DEVELOPMENT_CONFIG, "dev_connections.json")
    create_config_file(PRODUCTION_CONFIG, "prod_connections.json")
    create_config_file(EXAMPLE_CONNECTIONS_CONFIG, "example_connections.json")
    
    print("Example configuration files created!")
    print("\\nTo use a specific configuration:")
    print("1. Copy the desired config to ~/.scikiq_mcp/connections.json")
    print("2. Update the connection details for your environment")
    print("3. Start the MCP server")