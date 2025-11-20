"""
Database Configuration Classes

Handles database configuration validation and management.
"""

from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
import os
import json


class DatabaseType(Enum):
    """Supported database types"""
    MYSQL = "MYSQL"
    POSTGRES = "POSTGRES"
    ORACLE = "ORACLE"
    ORACLE_EBS = "ORACLE-EBS"
    ORACLE_FUSION = "ORACLE-FUSION"
    SQLSERVER = "SQLSERVER"
    MONGODB = "MONGODB"
    SNOWFLAKE = "SNOWFLAKE"
    BIGQUERY = "BIGQUERY"
    REDSHIFT = "REDSHIFT"
    ATHENA = "ATHENA"
    SAPHANA = "SAPHANA"
    VERTICA = "VERTICA"
    DB2 = "DB2"
    TERADATA = "TERADATA"
    CHROMADB = "CHROMADB"
    SAGEMAKER = "SAGEMAKER"
    RFC = "RFC"
    S4HANA = "S4HANA"
    BW4HANA = "BW4HANA"
    SAP_ECC = "SAP-ECC"
    AURORADB_MYSQL = "AURORADB-MYSQL"
    AURORADB_POSTGRES = "AURORADB-POSTGRES"
    DUCKDB = "DUCKDB"


class ConnectivityMechanism(Enum):
    """Connectivity mechanisms for database connections"""
    DIRECT = "D"
    SSL = "S"
    SSH = "SSH"


@dataclass
class SSLConfig:
    """SSL configuration for database connections"""
    ssl_cert_path: Optional[str] = None
    ssl_key_path: Optional[str] = None
    ssl_ca_path: Optional[str] = None
    pem_path: Optional[str] = None


@dataclass
class SSHConfig:
    """SSH configuration for database connections"""
    ssh_host: str
    ssh_user: str
    ssh_port: int = 22
    ssh_key_path: Optional[str] = None


@dataclass
class DatabaseConfig:
    """Database connection configuration"""
    
    # Core connection parameters
    dbType: DatabaseType
    hostname: str
    dbname: str
    dbuser: str
    dbpassword: str
    port: Optional[int] = None
    schema: Optional[str] = None
    
    # Password encryption flag (0 = plain text, 1 = base64 encrypted)
    password_encrypted: int = 0  # Default to 0 for MCP server (plain text)
    
    # Connectivity options
    connectivity_mechanism: ConnectivityMechanism = ConnectivityMechanism.DIRECT
    ssl_config: Optional[SSLConfig] = None
    ssh_config: Optional[SSHConfig] = None
    
    # Additional parameters
    connection_type: Optional[str] = None
    resource_key: Optional[str] = None
    app_config: Optional[Dict[str, Any]] = None
    
    # Database-specific parameters
    warehouse: Optional[str] = None  # Snowflake
    account: Optional[str] = None    # Snowflake
    role: Optional[str] = None       # Snowflake
    
    # Validation settings
    validate_on_create: bool = True
    
    def __post_init__(self):
        """Post-initialization validation and setup"""
        if isinstance(self.dbType, str):
            self.dbType = DatabaseType(self.dbType)
        
        if isinstance(self.connectivity_mechanism, str):
            self.connectivity_mechanism = ConnectivityMechanism(self.connectivity_mechanism)
        
        # Set default ports based on database type
        if self.port is None:
            self.port = self._get_default_port()
        
        # Validate configuration if requested
        if self.validate_on_create:
            self._validate()
    
    def _get_default_port(self) -> int:
        """Get default port for database type"""
        default_ports = {
            DatabaseType.MYSQL: 3306,
            DatabaseType.POSTGRES: 5432,
            DatabaseType.ORACLE: 1521,
            DatabaseType.ORACLE_EBS: 1521,
            DatabaseType.ORACLE_FUSION: 1521,
            DatabaseType.SQLSERVER: 1433,
            DatabaseType.MONGODB: 27017,
            DatabaseType.SNOWFLAKE: 443,
            DatabaseType.REDSHIFT: 5439,
            DatabaseType.SAPHANA: 30015,
            DatabaseType.VERTICA: 5433,
            DatabaseType.DB2: 50000,
            DatabaseType.TERADATA: 1025,
            DatabaseType.AURORADB_MYSQL: 3306,
            DatabaseType.AURORADB_POSTGRES: 5432,
            DatabaseType.DUCKDB: None,  # DuckDB doesn't use traditional ports
        }
        return default_ports.get(self.dbType, 5432)
    
    def _validate(self):
        """Validate configuration parameters"""
        errors = []
        
        # Required field validation (DuckDB has different requirements)
        if self.dbType == DatabaseType.DUCKDB:
            # DuckDB can work without traditional database parameters
            # Validation will be done at connection time based on available parameters
            pass
        else:
            # Traditional database validation
            if not self.hostname:
                errors.append("hostname is required")
            if not self.dbname:
                errors.append("dbname is required")
            if not self.dbuser:
                errors.append("dbuser is required")
        
        # Password validation (except for certain types)
        password_optional_types = {DatabaseType.BIGQUERY, DatabaseType.SAGEMAKER}
        if not self.dbpassword and self.dbType not in password_optional_types:
            errors.append("dbpassword is required")
        
        # Port validation
        if self.port is not None and (self.port < 1 or self.port > 65535):
            errors.append("port must be between 1 and 65535")
        
        # SSL configuration validation
        if self.connectivity_mechanism == ConnectivityMechanism.SSL:
            if not self.ssl_config:
                errors.append("SSL configuration is required when using SSL connectivity")
            elif not any([self.ssl_config.pem_path, 
                         all([self.ssl_config.ssl_cert_path, self.ssl_config.ssl_key_path, self.ssl_config.ssl_ca_path])]):
                errors.append("SSL configuration must include either pem_path or all three SSL certificate paths")
        
        # SSH configuration validation
        if self.connectivity_mechanism == ConnectivityMechanism.SSH:
            if not self.ssh_config:
                errors.append("SSH configuration is required when using SSH connectivity")
            else:
                if not self.ssh_config.ssh_host:
                    errors.append("SSH host is required")
                if not self.ssh_config.ssh_user:
                    errors.append("SSH user is required")
                if self.ssh_config.ssh_port < 1 or self.ssh_config.ssh_port > 65535:
                    errors.append("SSH port must be between 1 and 65535")
        
        # Database-specific validation
        if self.dbType == DatabaseType.SNOWFLAKE:
            if not self.warehouse:
                errors.append("warehouse is required for Snowflake connections")
            if not self.account:
                errors.append("account is required for Snowflake connections")
        
        if errors:
            raise ValueError(f"Configuration validation failed: {'; '.join(errors)}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format compatible with existing handlers"""
        import base64
        
        # Handle password encoding based on encryption flag
        if self.password_encrypted == 1:
            # Password is already encrypted, use as-is
            password = self.dbpassword
        else:
            # Password is plain text, encode it for DBFactory
            password = base64.b64encode(bytes(self.dbpassword, "utf-8")).decode('utf-8')
        
        config = {
            "dbType": self.dbType.value,
            "hostname": self.hostname,
            "port": self.port if self.port is not None else "",
            "dbname": self.dbname,
            "dbuser": self.dbuser,
            "dbpassword": password,
            "password_encrypted": 1,  # Always set to 1 since we ensure password is encoded
        }
        
        # Handle DuckDB special case - merge app_config parameters at top level
        if self.dbType == DatabaseType.DUCKDB and self.app_config:
            # For DuckDB, include all app_config parameters at the top level
            for key, value in self.app_config.items():
                if key not in config:  # Don't override existing keys
                    config[key] = value
            # Ensure password encryption is properly set for DuckDB
            config["password_encrypted"] = 0  # DuckDB doesn't need encrypted passwords
        
        # Optional fields
        if self.schema:
            config["schema"] = self.schema
        if self.connection_type:
            config["connection_type"] = self.connection_type
        if self.resource_key:
            config["resource_key"] = self.resource_key
        if self.app_config and self.dbType != DatabaseType.DUCKDB:
            config["app_config"] = self.app_config
        
        # Connectivity mechanism
        config["connectivity_mechanism"] = self.connectivity_mechanism.value
        
        # SSL configuration
        if self.ssl_config:
            if self.ssl_config.pem_path:
                config["pem_path"] = self.ssl_config.pem_path
            else:
                config["ssl_cert_path"] = self.ssl_config.ssl_cert_path
                config["ssl_key_path"] = self.ssl_config.ssl_key_path
                config["ssl_ca_path"] = self.ssl_config.ssl_ca_path
        
        # SSH configuration
        if self.ssh_config:
            config["ssh_host"] = self.ssh_config.ssh_host
            config["ssh_user"] = self.ssh_config.ssh_user
            config["ssh_port"] = self.ssh_config.ssh_port
            if self.ssh_config.ssh_key_path:
                config["ssh_key_path"] = self.ssh_config.ssh_key_path
        
        # Database-specific parameters
        if self.warehouse:
            config["warehouse"] = self.warehouse
        if self.account:
            config["account"] = self.account
        if self.role:
            config["role"] = self.role
        
        return config
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DatabaseConfig':
        """Create DatabaseConfig from dictionary"""
        # Handle password field variations (DBFactory uses 'pwd')
        password = data.get("pwd") or data.get("dbpassword", "")
        
        # Extract SSL configuration
        ssl_config = None
        if data.get("connectivity_mechanism") == "S" or data.get("pem_path"):
            ssl_config = SSLConfig(
                pem_path=data.get("pem_path"),
                ssl_cert_path=data.get("ssl_cert_path"),
                ssl_key_path=data.get("ssl_key_path"),
                ssl_ca_path=data.get("ssl_ca_path")
            )
        
        # Extract SSH configuration
        ssh_config = None
        if data.get("connectivity_mechanism") == "SSH":
            ssh_config = SSHConfig(
                ssh_host=data.get("ssh_host", ""),
                ssh_user=data.get("ssh_user", ""),
                ssh_port=int(data.get("ssh_port", 22)),
                ssh_key_path=data.get("ssh_key_path")
            )
        
        # Handle DuckDB special case - it doesn't require traditional database fields
        db_type = DatabaseType(data["dbType"])
        if db_type == DatabaseType.DUCKDB:
            # Create a complete config dict for DuckDB with all necessary fields
            duckdb_app_config = data.copy()
            # Ensure required fields are present for DBFactory compatibility
            duckdb_app_config.setdefault("dbpassword", "")
            duckdb_app_config.setdefault("pwd", "")
            
            return cls(
                dbType=db_type,
                hostname=data.get("hostname", "duckdb"),  # Use default values for DuckDB
                port=data.get("port") or None,  # Handle None port properly
                dbname=data.get("dbname", "default"),
                dbuser=data.get("dbuser", "default"),
                dbpassword=password or "",
                schema=data.get("schema"),
                connectivity_mechanism=ConnectivityMechanism(data.get("connectivity_mechanism", "D")),
                ssl_config=ssl_config,
                ssh_config=ssh_config,
                connection_type=data.get("connection_type"),
                resource_key=data.get("resource_key"),
                app_config=duckdb_app_config,  # Store all DuckDB-specific parameters in app_config
                warehouse=data.get("warehouse"),
                account=data.get("account"),
                role=data.get("role"),
                validate_on_create=False  # Skip validation for DuckDB
            )
        else:
            return cls(
                dbType=db_type,
                hostname=data["hostname"],
                port=int(data["port"]) if data.get("port") else None,
                dbname=data["dbname"],
                dbuser=data["dbuser"],
                dbpassword=password,
                schema=data.get("schema"),
                connectivity_mechanism=ConnectivityMechanism(data.get("connectivity_mechanism", "D")),
                ssl_config=ssl_config,
                ssh_config=ssh_config,
                connection_type=data.get("connection_type"),
            resource_key=data.get("resource_key"),
            app_config=data.get("app_config"),
            warehouse=data.get("warehouse"),
            account=data.get("account"),
            role=data.get("role"),
            validate_on_create=False  # Skip validation since we're loading existing config
        )
    
    def mask_sensitive_data(self) -> Dict[str, Any]:
        """Get configuration with sensitive data masked"""
        config = self.to_dict()
        
        # Mask sensitive fields
        if config.get("pwd"):
            config["pwd"] = "***masked***"
        if config.get("dbpassword"):
            config["dbpassword"] = "***masked***"
        
        # Mask SSL paths (could contain sensitive info)
        for ssl_field in ["ssl_cert_path", "ssl_key_path", "ssl_ca_path", "pem_path"]:
            if config.get(ssl_field):
                config[ssl_field] = "***masked***"
        
        # Mask SSH key path
        if config.get("ssh_key_path"):
            config["ssh_key_path"] = "***masked***"
        
        return config
    
    def get_connection_string(self) -> str:
        """Generate a connection string representation (without credentials)"""
        if self.dbType in [DatabaseType.MYSQL, DatabaseType.AURORADB_MYSQL]:
            protocol = "mysql"
        elif self.dbType in [DatabaseType.POSTGRES, DatabaseType.AURORADB_POSTGRES]:
            protocol = "postgresql"
        elif self.dbType in [DatabaseType.ORACLE, DatabaseType.ORACLE_EBS, DatabaseType.ORACLE_FUSION]:
            protocol = "oracle"
        elif self.dbType == DatabaseType.SQLSERVER:
            protocol = "mssql"
        else:
            protocol = self.dbType.value.lower()
        
        conn_str = f"{protocol}://{self.dbuser}:***@{self.hostname}:{self.port}/{self.dbname}"
        
        if self.schema:
            conn_str += f"?currentSchema={self.schema}"
        
        return conn_str