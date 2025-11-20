"""
Environment Configuration Parser

Parses database connections from environment files for the MCP server.
"""

import os
import re
from typing import Dict, Any, List, Optional
from pathlib import Path
import logging

from scikiq_dbutils.mcp_server.config.database_config import DatabaseConfig, DatabaseType, ConnectivityMechanism, SSLConfig, SSHConfig


class EnvironmentConfigParser:
    """
    Parses database configurations from environment files
    """
    
    def __init__(self, env_file_path: Optional[str] = None):
        self.env_file_path = env_file_path
        self.logger = logging.getLogger(__name__)
        self._env_vars = {}
        
        if env_file_path:
            self.load_env_file(env_file_path)
    
    def load_env_file(self, file_path: str):
        """
        Load environment variables from file
        
        Args:
            file_path: Path to the environment file
        """
        env_path = Path(file_path)
        
        if not env_path.exists():
            raise FileNotFoundError(f"Environment file not found: {file_path}")
        
        self._env_vars = {}
        
        try:
            with open(env_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    
                    # Skip empty lines and comments
                    if not line or line.startswith('#'):
                        continue
                    
                    # Parse KEY=VALUE format
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        # Remove quotes if present
                        if (value.startswith('"') and value.endswith('"')) or \
                           (value.startswith("'") and value.endswith("'")):
                            value = value[1:-1]
                        
                        self._env_vars[key] = value
                    else:
                        self.logger.warning(f"Invalid line format at line {line_num}: {line}")
            
            self.logger.info(f"Loaded {len(self._env_vars)} environment variables from {file_path}")
            
        except Exception as e:
            raise ValueError(f"Error reading environment file {file_path}: {str(e)}")
    
    def get_connection_ids(self) -> List[str]:
        """
        Extract unique connection IDs from environment variables
        
        Returns:
            List of connection IDs
        """
        connection_ids = set()
        
        # Pattern to match connection variables: CONNECTIONID_PARAMETER=value
        for key in self._env_vars.keys():
            # Skip server-level configuration
            if key.startswith('MCP_SERVER_'):
                continue
            
            # Extract connection ID (everything before the last underscore)
            parts = key.split('_')
            if len(parts) >= 2:
                # Find the last parameter part
                possible_params = ['DB_TYPE', 'HOSTNAME', 'PORT', 'DATABASE', 'USERNAME', 'PASSWORD', 
                                 'SCHEMA', 'SSL_MODE', 'SSL_CERT', 'SSL_KEY', 'SSL_CA',
                                 'SSH_HOST', 'SSH_USER', 'SSH_PORT', 'SSH_KEY',
                                 'WAREHOUSE', 'ACCOUNT', 'ROLE']
                
                for i in range(len(parts) - 1, 0, -1):
                    param = '_'.join(parts[i:])
                    if param in possible_params:
                        connection_id = '_'.join(parts[:i])
                        connection_ids.add(connection_id)
                        break
        
        return sorted(list(connection_ids))
    
    def parse_connection_config(self, connection_id: str) -> DatabaseConfig:
        """
        Parse database configuration for a specific connection ID
        
        Args:
            connection_id: Connection identifier
            
        Returns:
            DatabaseConfig instance
        """
        config = {}
        ssl_config = None
        ssh_config = None
        
        # Required parameters mapping
        param_mapping = {
            'DB_TYPE': 'dbType',
            'HOSTNAME': 'hostname',
            'PORT': 'port',
            'DATABASE': 'dbname',
            'USERNAME': 'dbuser',
            'PASSWORD': 'dbpassword',  # Use 'dbpassword' for DatabaseConfig consistency
            'SCHEMA': 'schema'
        }
        
        # Extract basic configuration
        for env_key, config_key in param_mapping.items():
            env_var_name = f"{connection_id}_{env_key}"
            if env_var_name in self._env_vars:
                value = self._env_vars[env_var_name]
                
                # Convert port to integer
                if config_key == 'port' and value:
                    try:
                        value = int(value)
                    except ValueError:
                        raise ValueError(f"Invalid port value for {connection_id}: {value}")
                
                config[config_key] = value
        
        # Check for password encryption flag
        password_encrypted_var = f"{connection_id}_PASSWORD_ENCRYPTED"
        if password_encrypted_var in self._env_vars:
            try:
                config['password_encrypted'] = int(self._env_vars[password_encrypted_var])
            except ValueError:
                config['password_encrypted'] = 0  # Default to unencrypted
        else:
            config['password_encrypted'] = 0  # Default to unencrypted for MCP server
        
        # Validate required fields
        required_fields = ['dbType', 'hostname', 'dbname', 'dbuser']
        missing_fields = [field for field in required_fields if field not in config]
        
        if missing_fields:
            raise ValueError(f"Missing required configuration for {connection_id}: {missing_fields}")
        
        # Parse SSL configuration
        ssl_params = ['SSL_MODE', 'SSL_CERT', 'SSL_KEY', 'SSL_CA']
        ssl_values = {}
        
        for param in ssl_params:
            env_var_name = f"{connection_id}_{param}"
            if env_var_name in self._env_vars:
                ssl_values[param] = self._env_vars[env_var_name]
        
        if ssl_values:
            ssl_config = SSLConfig(
                ssl_cert_path=ssl_values.get('SSL_CERT'),
                ssl_key_path=ssl_values.get('SSL_KEY'),
                ssl_ca_path=ssl_values.get('SSL_CA')
            )
            config['connectivity_mechanism'] = 'S'
        
        # Parse SSH configuration
        ssh_params = ['SSH_HOST', 'SSH_USER', 'SSH_PORT', 'SSH_KEY']
        ssh_values = {}
        
        for param in ssh_params:
            env_var_name = f"{connection_id}_{param}"
            if env_var_name in self._env_vars:
                ssh_values[param] = self._env_vars[env_var_name]
        
        if ssh_values.get('SSH_HOST') and ssh_values.get('SSH_USER'):
            ssh_port = 22
            if 'SSH_PORT' in ssh_values:
                try:
                    ssh_port = int(ssh_values['SSH_PORT'])
                except ValueError:
                    raise ValueError(f"Invalid SSH port value for {connection_id}: {ssh_values['SSH_PORT']}")
            
            ssh_config = SSHConfig(
                ssh_host=ssh_values['SSH_HOST'],
                ssh_user=ssh_values['SSH_USER'],
                ssh_port=ssh_port,
                ssh_key_path=ssh_values.get('SSH_KEY')
            )
            config['connectivity_mechanism'] = 'SSH'
        
        # Set default connectivity mechanism if not set
        if 'connectivity_mechanism' not in config:
            config['connectivity_mechanism'] = 'D'
        
        # Parse database-specific parameters (Snowflake, etc.)
        snowflake_params = ['WAREHOUSE', 'ACCOUNT', 'ROLE']
        for param in snowflake_params:
            env_var_name = f"{connection_id}_{param}"
            if env_var_name in self._env_vars:
                config[param.lower()] = self._env_vars[env_var_name]
        
        # Create DatabaseConfig
        try:
            db_config = DatabaseConfig.from_dict(config)
            
            # Set SSL and SSH configurations
            if ssl_config:
                db_config.ssl_config = ssl_config
            if ssh_config:
                db_config.ssh_config = ssh_config
            
            return db_config
            
        except Exception as e:
            raise ValueError(f"Error creating database configuration for {connection_id}: {str(e)}")
    
    def parse_all_connections(self) -> Dict[str, DatabaseConfig]:
        """
        Parse all database configurations from environment variables
        
        Returns:
            Dictionary mapping connection IDs to DatabaseConfig instances
        """
        connections = {}
        connection_ids = self.get_connection_ids()
        
        self.logger.info(f"Found {len(connection_ids)} database connections in environment")
        
        for connection_id in connection_ids:
            try:
                config = self.parse_connection_config(connection_id)
                connections[connection_id] = config
                self.logger.info(f"Parsed configuration for connection: {connection_id} ({config.dbType.value})")
            except Exception as e:
                self.logger.error(f"Error parsing configuration for {connection_id}: {str(e)}")
                # Continue with other connections instead of failing completely
        
        return connections
    
    def get_server_config(self) -> Dict[str, Any]:
        """
        Extract server-level configuration from environment variables
        
        Returns:
            Dictionary of server configuration
        """
        server_config = {}
        
        # Server configuration mapping
        server_param_mapping = {
            'MCP_SERVER_MAX_CONNECTIONS': ('max_connections', int),
            'MCP_SERVER_CONNECTION_TIMEOUT': ('connection_timeout', int),
            'MCP_SERVER_QUERY_TIMEOUT': ('query_timeout', int),
            'MCP_SERVER_LOG_LEVEL': ('log_level', str),
            'MCP_SERVER_DEBUG': ('debug', lambda x: x.lower() in ['true', '1', 'yes', 'on'])
        }
        
        for env_key, (config_key, converter) in server_param_mapping.items():
            if env_key in self._env_vars:
                try:
                    value = converter(self._env_vars[env_key])
                    server_config[config_key] = value
                except (ValueError, TypeError) as e:
                    self.logger.warning(f"Invalid value for {env_key}: {self._env_vars[env_key]}")
        
        return server_config
    
    def validate_environment(self) -> Dict[str, List[str]]:
        """
        Validate all database configurations in the environment
        
        Returns:
            Dictionary mapping connection IDs to validation error lists
        """
        validation_results = {}
        connection_ids = self.get_connection_ids()
        
        for connection_id in connection_ids:
            try:
                config = self.parse_connection_config(connection_id)
                config._validate()  # Run validation
                validation_results[connection_id] = []  # No errors
            except Exception as e:
                validation_results[connection_id] = [str(e)]
        
        return validation_results
    
    def list_connections_summary(self) -> List[Dict[str, Any]]:
        """
        Get a summary of all connections in the environment
        
        Returns:
            List of connection summaries
        """
        summaries = []
        connection_ids = self.get_connection_ids()
        
        for connection_id in connection_ids:
            try:
                config = self.parse_connection_config(connection_id)
                summaries.append({
                    'connection_id': connection_id,
                    'db_type': config.dbType.value,
                    'hostname': config.hostname,
                    'database': config.dbname,
                    'username': config.dbuser,
                    'port': config.port,
                    'has_ssl': config.ssl_config is not None,
                    'has_ssh': config.ssh_config is not None,
                    'status': 'valid'
                })
            except Exception as e:
                summaries.append({
                    'connection_id': connection_id,
                    'status': 'invalid',
                    'error': str(e)
                })
        
        return summaries
    
    @staticmethod
    def create_sample_env_file(file_path: str):
        """
        Create a sample environment file with examples
        
        Args:
            file_path: Path where to create the sample file
        """
        sample_content = """# ScikiQ Database MCP Server Environment Configuration
# 
# Format: CONNECTIONID_PARAMETER=value
# Compatible with DBFactory configuration format
#
# Example connections (update with your actual credentials):

# MySQL Production Database
PROD_DB_DB_TYPE=MYSQL
PROD_DB_HOSTNAME=localhost
PROD_DB_PORT=3306
PROD_DB_DATABASE=production
PROD_DB_USERNAME=app_user
PROD_DB_PASSWORD=your_password_here

# PostgreSQL Development Database
DEV_DB_DB_TYPE=POSTGRES
DEV_DB_HOSTNAME=localhost
DEV_DB_PORT=5432
DEV_DB_DATABASE=development
DEV_DB_USERNAME=dev_user
DEV_DB_PASSWORD=dev_password

# Snowflake Analytics Database (with additional parameters)
ANALYTICS_DB_DB_TYPE=SNOWFLAKE
ANALYTICS_DB_HOSTNAME=mycompany.snowflakecomputing.com
ANALYTICS_DB_DATABASE=ANALYTICS
ANALYTICS_DB_USERNAME=analytics_user
ANALYTICS_DB_PASSWORD=sf_password
ANALYTICS_DB_WAREHOUSE=COMPUTE_WH
ANALYTICS_DB_ACCOUNT=mycompany
ANALYTICS_DB_ROLE=ANALYST

# SSL Example (PostgreSQL with SSL)
SSL_DB_DB_TYPE=POSTGRES
SSL_DB_HOSTNAME=secure-db.example.com
SSL_DB_PORT=5432
SSL_DB_DATABASE=secure_db
SSL_DB_USERNAME=ssl_user
SSL_DB_PASSWORD=ssl_password
SSL_DB_SSL_CERT=/path/to/client-cert.pem
SSL_DB_SSL_KEY=/path/to/client-key.pem
SSL_DB_SSL_CA=/path/to/ca-cert.pem

# SSH Tunnel Example (MySQL via SSH)
SSH_DB_DB_TYPE=MYSQL
SSH_DB_HOSTNAME=internal-db.local
SSH_DB_PORT=3306
SSH_DB_DATABASE=internal_db
SSH_DB_USERNAME=internal_user
SSH_DB_PASSWORD=internal_password
SSH_DB_SSH_HOST=bastion.example.com
SSH_DB_SSH_USER=ssh_user
SSH_DB_SSH_PORT=22
SSH_DB_SSH_KEY=/path/to/ssh-key

# Server Configuration
MCP_SERVER_LOG_LEVEL=INFO
MCP_SERVER_MAX_CONNECTIONS=50
MCP_SERVER_CONNECTION_TIMEOUT=30
MCP_SERVER_QUERY_TIMEOUT=300
MCP_SERVER_DEBUG=false
"""
        
        with open(file_path, 'w') as f:
            f.write(sample_content)
        
        print(f"Sample environment file created: {file_path}")
        print("Please update the file with your actual database credentials.")