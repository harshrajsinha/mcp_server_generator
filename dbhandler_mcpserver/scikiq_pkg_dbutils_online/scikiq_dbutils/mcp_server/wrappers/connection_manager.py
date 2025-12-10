"""
Database Connection Manager

Manages database connections and provides a registry for active connections.
"""

import threading
from typing import Dict, Optional, Any, List
from contextlib import contextmanager
import logging

from scikiq_dbutils.handlers.DBFactory import clsDBHandler
from scikiq_dbutils.handlers.DBConnection import clsDBConnection
from scikiq_dbutils.mcp_server.protocol.messages import create_database_connection_error, create_invalid_database_config_error
from scikiq_dbutils.mcp_server.config.database_config import DatabaseConfig


class ConnectionManager:
    """Manages database connections for the MCP server"""
    
    def __init__(self, auto_connect_configs: Optional[Dict[str, DatabaseConfig]] = None):
        self._connections: Dict[str, clsDBConnection] = {}
        self._connection_configs: Dict[str, DatabaseConfig] = {}
        self._lock = threading.Lock()
        self.logger = logging.getLogger(__name__)
        
        # Auto-connect to provided configurations
        if auto_connect_configs:
            self.load_configurations(auto_connect_configs)
    
    def create_connection(self, connection_id: str, config: Dict[str, Any], lock_held: bool = False) -> clsDBConnection:
        """
        Create a new database connection
        
        Args:
            connection_id: Unique identifier for the connection
            config: Database configuration dictionary
            lock_held: Whether the lock is already held by the caller (prevents deadlock)
            
        Returns:
            Database connection instance
            
        Raises:
            ValueError: If configuration is invalid
            Exception: If connection fails
        """
        self.logger.info(f"create_connection called for: {connection_id}, lock_held={lock_held}")
        
        def _do_create():
            # Validate configuration
            self.logger.info(f"Validating configuration for: {connection_id}")
            validation_errors = self._validate_config(config)
            if validation_errors:
                self.logger.error(f"Configuration validation failed for {connection_id}: {validation_errors}")
                raise ValueError(f"Invalid configuration: {', '.join(validation_errors)}")
            
            self.logger.info(f"Configuration validated, creating DB instance for: {connection_id}")
            try:
                # Create connection using existing factory
                self.logger.info(f"Calling clsDBHandler.getInstanceByConfig for: {connection_id}")
                db_instance = clsDBHandler.getInstanceByConfig(config)
                self.logger.info(f"DB instance created, testing connection for: {connection_id}")
                
                # Test the connection
                test_result = db_instance.testConnection()
                self.logger.info(f"Connection test completed for {connection_id}, result: {test_result}")
                
                if test_result.get('error', 0) != 0:
                    error_msg = test_result.get('msg', 'Unknown error')
                    self.logger.error(f"Connection test failed for {connection_id}: {error_msg}")
                    raise Exception(f"Connection test failed: {error_msg}")
                
                # Store connection
                self.logger.info(f"Storing connection for: {connection_id}")
                self._connections[connection_id] = db_instance
                self.logger.info(f"Connection stored successfully for: {connection_id}")
                return db_instance
                
            except Exception as e:
                self.logger.error(f"Failed to create database connection for {connection_id}: {str(e)}", exc_info=True)
                raise Exception(f"Failed to create database connection: {str(e)}")
        
        if lock_held:
            # Lock already held, just execute
            self.logger.info(f"Lock already held, executing create_connection for: {connection_id}")
            return _do_create()
        else:
            # Need to acquire lock
            self.logger.info(f"Attempting to acquire lock for create_connection: {connection_id}")
            with self._lock:
                self.logger.info(f"Lock acquired for create_connection: {connection_id}")
                return _do_create()
    
    def get_connection(self, connection_id: str) -> Optional[clsDBConnection]:
        """Get an existing connection by ID (case-insensitive)"""
        with self._lock:
            # Try exact match first
            if connection_id in self._connections:
                return self._connections[connection_id]
            # Try case-insensitive match
            actual_key = self._find_connection_key(connection_id, self._connections)
            if actual_key:
                return self._connections[actual_key]
            return None
    
    def remove_connection(self, connection_id: str) -> bool:
        """
        Remove and close a database connection
        
        Args:
            connection_id: Connection identifier
            
        Returns:
            True if connection was found and removed, False otherwise
        """
        with self._lock:
            # Try exact match first
            if connection_id in self._connections:
                try:
                    self._connections[connection_id].close()
                except Exception:
                    pass  # Ignore close errors
                del self._connections[connection_id]
                return True
            # Try case-insensitive match
            actual_key = self._find_connection_key(connection_id, self._connections)
            if actual_key:
                try:
                    self._connections[actual_key].close()
                except Exception:
                    pass  # Ignore close errors
                del self._connections[actual_key]
                return True
            return False
    
    def list_connections(self) -> Dict[str, Dict[str, Any]]:
        """List all connections (both active and configured) with their basic info"""
        with self._lock:
            result = {}
            
            # Add active connections
            for conn_id, conn in self._connections.items():
                result[conn_id] = {
                    "connection_id": conn_id,
                    "db_type": getattr(conn, 'db_type', 'Unknown'),
                    "host": getattr(conn, 'host', 'Unknown'),
                    "database": getattr(conn, 'dbname', 'Unknown'),
                    "status": "active"
                }
            
            # Add configured connections that are not active
            for conn_id, config in self._connection_configs.items():
                if conn_id not in result:  # Only add if not already active
                    result[conn_id] = {
                        "connection_id": conn_id,
                        "db_type": config.dbType.value,
                        "host": config.hostname,
                        "database": config.dbname,
                        "status": "configured"
                    }
                    
            return result
    
    def close_all(self):
        """Close all connections"""
        with self._lock:
            for connection in self._connections.values():
                try:
                    connection.close()
                except Exception:
                    pass  # Ignore close errors
            self._connections.clear()
    
    @contextmanager
    def get_managed_connection(self, connection_id: str):
        """
        Context manager for getting a connection with automatic management
        
        Args:
            connection_id: Connection identifier
            
        Yields:
            Database connection instance
            
        Raises:
            ValueError: If connection not found
        """
        connection = self.get_connection(connection_id)
        if not connection:
            raise ValueError(f"Connection '{connection_id}' not found")
        
        try:
            yield connection
        finally:
            # Could add cleanup logic here if needed
            pass
    
    def _validate_config(self, config: Dict[str, Any]) -> list[str]:
        """
        Validate database configuration
        
        Args:
            config: Database configuration dictionary
            
        Returns:
            List of validation error messages
        """
        errors = []
        
        # Database type validation first
        supported_db_types = {
            "MYSQL", "POSTGRES", "ORACLE", "SQLSERVER", "MONGODB",
            "SNOWFLAKE", "BIGQUERY", "REDSHIFT", "ATHENA", "SAPHANA",
            "VERTICA", "DB2", "TERADATA", "CHROMADB", "SAGEMAKER",
            "ORACLE-EBS", "ORACLE-FUSION", "S4HANA", "BW4HANA", "SAP-ECC",
            "RFC", "AURORADB-MYSQL", "AURORADB-POSTGRES", "DUCKDB"
        }
        
        if "dbType" not in config or not config["dbType"]:
            errors.append("Missing required field: dbType")
        elif config["dbType"] not in supported_db_types:
            errors.append(f"Unsupported database type: {config['dbType']}")
        
        # Required fields vary by database type
        db_type = config.get("dbType", "")
        
        if db_type == "DUCKDB":
            # DuckDB has different requirements - must have either S3 config or local database path
            # Check for S3 configuration using either aws_* or s3_* naming conventions
            has_aws_access_key = any(key in config for key in ['aws_access_key_id', 's3_access_key_id'])
            has_aws_secret_key = any(key in config for key in ['aws_secret_access_key', 's3_secret_access_key'])
            has_bucket = any(key in config for key in ['bucket_name', 's3_bucket'])
            has_s3_config = has_aws_access_key and has_aws_secret_key and has_bucket
            has_local_config = 'database_path' in config
            
            if not (has_s3_config or has_local_config):
                errors.append("DuckDB requires either S3 configuration (aws_access_key_id/s3_access_key_id, aws_secret_access_key/s3_secret_access_key, bucket_name/s3_bucket) or database_path")
        else:
            # Traditional database validation
            required_fields = ["hostname", "dbname", "dbuser"]
            for field in required_fields:
                if field not in config:
                    errors.append(f"Missing required field: {field}")
                elif not config[field]:
                    errors.append(f"Empty value for required field: {field}")
        
        # Validate port if provided
        if "port" in config and config["port"]:
            try:
                port = int(config["port"])
                if port < 1 or port > 65535:
                    errors.append("Port must be between 1 and 65535")
            except (ValueError, TypeError):
                errors.append("Port must be a valid integer")
        
        return errors
    
    def test_connection(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Test a database configuration without creating a persistent connection
        
        Args:
            config: Database configuration dictionary
            
        Returns:
            Test result dictionary with 'error' and 'msg' keys
        """
        validation_errors = self._validate_config(config)
        if validation_errors:
            return {
                'error': 1,
                'msg': f"Configuration validation failed: {', '.join(validation_errors)}"
            }
        
        try:
            # Create temporary connection for testing
            temp_instance = clsDBHandler.getInstanceByConfig(config)
            return temp_instance.testConnection()
        except Exception as e:
            return {
                'error': 1,
                'msg': f"Connection test failed: {str(e)}"
            }
    
    def load_configurations(self, configs: Dict[str, DatabaseConfig]):
        """
        Load multiple database configurations
        
        Args:
            configs: Dictionary mapping connection IDs to DatabaseConfig instances
        """
        with self._lock:
            for connection_id, config in configs.items():
                try:
                    self._connection_configs[connection_id] = config
                    self.logger.info(f"Loaded configuration for connection: {connection_id}")
                except Exception as e:
                    self.logger.error(f"Failed to load configuration for {connection_id}: {str(e)}")
    
    def get_available_connections(self) -> List[str]:
        """
        Get list of available connection IDs (both active and configured)
        
        Returns:
            List of connection IDs
        """
        with self._lock:
            active_connections = set(self._connections.keys())
            configured_connections = set(self._connection_configs.keys())
            return sorted(list(active_connections.union(configured_connections)))
    
    def _find_connection_key(self, connection_id: str, dictionary: Dict[str, Any]) -> Optional[str]:
        """
        Find connection key in dictionary using case-insensitive matching
        
        Args:
            connection_id: Connection identifier to find
            dictionary: Dictionary to search in
            
        Returns:
            Actual key from dictionary if found, None otherwise
        """
        connection_id_upper = connection_id.upper()
        for key in dictionary.keys():
            if key.upper() == connection_id_upper:
                return key
        return None
    
    def auto_connect(self, connection_id: str) -> bool:
        """
        Automatically connect to a configured database
        
        Args:
            connection_id: Connection identifier
            
        Returns:
            True if connection successful, False otherwise
        """
        self.logger.info(f"auto_connect called for: {connection_id}")
        self.logger.info(f"Attempting to acquire lock for: {connection_id}")
        
        with self._lock:
            self.logger.info(f"Lock acquired for: {connection_id}")
            
            # Check if already connected (case-insensitive)
            self.logger.info(f"Checking for existing connection (case-insensitive): {connection_id}")
            actual_conn_key = self._find_connection_key(connection_id, self._connections)
            if actual_conn_key:
                self.logger.info(f"Found existing connection with key: {actual_conn_key}")
                return True  # Already connected
            
            self.logger.info(f"No existing connection found, searching for config: {connection_id}")
            # Find configuration (case-insensitive)
            actual_config_key = self._find_connection_key(connection_id, self._connection_configs)
            if not actual_config_key:
                self.logger.error(f"No configuration found for connection: {connection_id}")
                self.logger.info(f"Available connection configs: {list(self._connection_configs.keys())}")
                return False
            
            self.logger.info(f"Found configuration with key: {actual_config_key}")
            
            try:
                self.logger.info(f"Retrieving config for: {actual_config_key}")
                config = self._connection_configs[actual_config_key]
                self.logger.info(f"Converting config to dict for: {actual_config_key}")
                config_dict = config.to_dict()
                self.logger.info(f"Config dict created, keys: {list(config_dict.keys())}")
                
                # Use the actual key from config for consistency
                # Pass lock_held=True since we already have the lock
                self.logger.info(f"Creating connection for: {actual_config_key} (lock already held)")
                connection = self.create_connection(actual_config_key, config_dict, lock_held=True)
                self.logger.info(f"Auto-connected to database: {actual_config_key}")
                return True
                
            except Exception as e:
                self.logger.error(f"Auto-connect failed for {connection_id}: {str(e)}", exc_info=True)
                return False
    
    def ensure_connection(self, connection_id: str) -> Optional[clsDBConnection]:
        """
        Ensure a connection exists, auto-connecting if necessary
        
        Args:
            connection_id: Connection identifier
            
        Returns:
            Database connection instance or None if failed
        """
        self.logger.info(f"ensure_connection called for: {connection_id}")
        
        # Try to get existing connection
        self.logger.info(f"Checking for existing connection: {connection_id}")
        connection = self.get_connection(connection_id)
        if connection:
            self.logger.info(f"Found existing connection for: {connection_id}")
            return connection
        
        self.logger.info(f"No existing connection found, attempting auto-connect for: {connection_id}")
        # Try auto-connect
        auto_connect_result = self.auto_connect(connection_id)
        self.logger.info(f"auto_connect returned: {auto_connect_result} for: {connection_id}")
        
        if auto_connect_result:
            connection = self.get_connection(connection_id)
            self.logger.info(f"Retrieved connection after auto-connect: {connection is not None} for: {connection_id}")
            return connection
        
        self.logger.error(f"Failed to ensure connection for: {connection_id}")
        return None
    
    def get_connection_info(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a connection
        
        Args:
            connection_id: Connection identifier
            
        Returns:
            Dictionary with connection information or None if not found
        """
        info = {}
        
        with self._lock:
            # Check if actively connected (case-insensitive)
            actual_conn_key = self._find_connection_key(connection_id, self._connections)
            if actual_conn_key:
                info['status'] = 'connected'
                info['active'] = True
                connection_id = actual_conn_key  # Use actual key for consistency
            else:
                # Check if configured (case-insensitive)
                actual_config_key = self._find_connection_key(connection_id, self._connection_configs)
                if actual_config_key:
                    info['status'] = 'configured'
                    info['active'] = False
                    connection_id = actual_config_key  # Use actual key for consistency
                else:
                    return None
            
            # Add configuration info if available
            actual_config_key = self._find_connection_key(connection_id, self._connection_configs)
            if actual_config_key:
                config = self._connection_configs[actual_config_key]
                info.update({
                    'db_type': config.dbType.value,
                    'hostname': config.hostname,
                    'database': config.dbname,
                    'username': config.dbuser,
                    'port': config.port,
                    'has_ssl': config.ssl_config is not None,
                    'has_ssh': config.ssh_config is not None,
                    'connectivity_mechanism': config.connectivity_mechanism.value if hasattr(config, 'connectivity_mechanism') else 'D'
                })
        
        return info