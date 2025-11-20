"""
INI Configuration Parser for MCP Server

Parses database connections from INI configuration files for the MCP server.
"""

import configparser
import logging
from pathlib import Path
from typing import Dict, Optional, List, Tuple

from scikiq_dbutils.mcp_server.config.database_config import (
    DatabaseConfig, DatabaseType, ConnectivityMechanism, SSLConfig, SSHConfig
)


class IniConfigParser:
    """Parser for INI configuration files containing database connection settings"""
    
    def __init__(self, ini_file_path: str):
        """
        Initialize the INI parser
        
        Args:
            ini_file_path: Path to the INI configuration file
        """
        self.ini_file_path = Path(ini_file_path)
        self.config = configparser.ConfigParser()
        self.logger = logging.getLogger(__name__)
        
        self._load_ini_file()
    
    def _load_ini_file(self):
        """Load and parse the INI file"""
        if not self.ini_file_path.exists():
            raise FileNotFoundError(f"INI file not found: {self.ini_file_path}")
        
        try:
            self.config.read(self.ini_file_path)
            self.logger.info(f"Loaded INI configuration from {self.ini_file_path}")
            self.logger.info(f"Found {len(self.config.sections())} sections in INI file")
        except Exception as e:
            raise ValueError(f"Error reading INI file {self.ini_file_path}: {str(e)}")
    
    def get_connection_sections(self) -> List[str]:
        """
        Get all sections that contain database connection configurations
        
        Returns:
            List of section names that contain database configurations
        """
        connection_sections = []
        for section_name in self.config.sections():
            section = self.config[section_name]
            # Convert section keys to lowercase for case-insensitive matching
            section_keys = [key.lower() for key in section.keys()]
            
            # Check if section has database type
            if 'db_type' in section_keys:
                db_type = section.get('db_type', '').upper()
                
                if db_type == 'DUCKDB':
                    # For DuckDB, check for either S3 config or local database
                    has_s3_config = any(key in section_keys for key in [
                        'aws_access_key_id', 's3_access_key_id', 'bucket_name', 's3_bucket'
                    ])
                    has_local_config = 'database_path' in section_keys
                    
                    if has_s3_config or has_local_config or db_type == 'DUCKDB':
                        connection_sections.append(section_name)
                else:
                    # For other database types, require hostname
                    if 'host' in section_keys or 'hostname' in section_keys:
                        connection_sections.append(section_name)
        
        self.logger.info(f"Found {len(connection_sections)} database connections in INI file")
        return connection_sections
    
    def parse_connection_config(self, section_name: str) -> DatabaseConfig:
        """
        Parse database configuration from a specific INI section
        
        Args:
            section_name: Name of the INI section to parse
            
        Returns:
            DatabaseConfig instance
        """
        if section_name not in self.config:
            raise ValueError(f"Section '{section_name}' not found in INI file")
        
        section = self.config[section_name]
        
        # Extract basic configuration
        config = {}
        
        # Required parameters mapping - supporting both uppercase and lowercase
        param_mapping = {
            # Standard database parameters - Uppercase (ENV style)
            'DB_TYPE': 'dbType',
            'HOSTNAME': 'hostname',
            'PORT': 'port',
            'DATABASE': 'dbname',
            'USERNAME': 'dbuser',
            'PASSWORD': 'dbpassword',
            'SCHEMA': 'schema',
            'SERVICE_NAME': 'service_name',
            # Standard database parameters - Lowercase (INI style)
            'db_type': 'dbType',
            'host': 'hostname',
            'hostname': 'hostname',
            'port': 'port',
            'database': 'dbname',
            'username': 'dbuser',
            'password': 'dbpassword',
            'schema': 'schema',
            'service_name': 'service_name',
            # DuckDB specific parameters
            'aws_access_key_id': 's3_access_key_id',
            'aws_secret_access_key': 's3_secret_access_key',
            'region_name': 's3_region',
            'bucket_name': 's3_bucket',
            's3_access_key_id': 's3_access_key_id',
            's3_secret_access_key': 's3_secret_access_key',
            's3_region': 's3_region',
            's3_bucket': 's3_bucket',
            'database_path': 'database_path',
            's3_prefix': 's3_prefix',
            'default_file_format': 'default_file_format'
        }
        
        # Extract basic configuration
        for ini_key, config_key in param_mapping.items():
            if ini_key in section:
                value = section[ini_key]
                
                # Convert port to integer
                if config_key == 'port' and value:
                    try:
                        value = int(value)
                    except ValueError:
                        raise ValueError(f"Invalid port value in section {section_name}: {value}")
                
                config[config_key] = value
        
        # Check for password encryption flag (support both uppercase and lowercase)
        password_encrypted_value = None
        if 'PASSWORD_ENCRYPTED' in section:
            password_encrypted_value = section['PASSWORD_ENCRYPTED']
        elif 'password_encrypted' in section:
            password_encrypted_value = section['password_encrypted']
        
        if password_encrypted_value is not None:
            try:
                config['password_encrypted'] = int(password_encrypted_value)
            except ValueError:
                config['password_encrypted'] = 0  # Default to unencrypted
        else:
            config['password_encrypted'] = 0  # Default to unencrypted for MCP server
        
        # Validate required fields based on database type
        db_type = config.get('dbType', '').upper()
        
        if db_type == 'DUCKDB':
            # DuckDB has different requirements - check for S3 or local database requirements
            if any(key in section for key in ['aws_access_key_id', 's3_access_key_id', 'bucket_name', 's3_bucket']):
                # S3-based DuckDB - require AWS parameters
                required_s3_fields = ['aws_access_key_id', 'aws_secret_access_key', 'bucket_name']
                missing_s3_fields = []
                
                # Check AWS credentials (support multiple naming patterns)
                if not (section.get('aws_access_key_id') or section.get('s3_access_key_id')):
                    missing_s3_fields.append('aws_access_key_id')
                if not (section.get('aws_secret_access_key') or section.get('s3_secret_access_key')):
                    missing_s3_fields.append('aws_secret_access_key')
                if not (section.get('bucket_name') or section.get('s3_bucket')):
                    missing_s3_fields.append('bucket_name')
                    
                if missing_s3_fields:
                    raise ValueError(f"Missing required S3 configuration in DuckDB section {section_name}: {missing_s3_fields}")
            # For local DuckDB, no additional validation required (can use :memory:)
        else:
            # Traditional database - require standard fields
            required_fields = ['dbType', 'hostname', 'dbname', 'dbuser']
            missing_fields = [field for field in required_fields if field not in config]
            
            if missing_fields:
                raise ValueError(f"Missing required configuration in section {section_name}: {missing_fields}")
        
        # Parse SSL configuration (support both uppercase and lowercase)
        ssl_config = None
        ssl_params_map = {
            'SSL_MODE': 'ssl_mode', 'ssl_mode': 'ssl_mode',
            'SSL_CERT': 'ssl_cert', 'ssl_cert': 'ssl_cert',
            'SSL_KEY': 'ssl_key', 'ssl_key': 'ssl_key', 
            'SSL_CA': 'ssl_ca', 'ssl_ca': 'ssl_ca'
        }
        ssl_values = {}
        
        for ini_param, ssl_key in ssl_params_map.items():
            if ini_param in section:
                ssl_values[ssl_key] = section[ini_param]
        
        if ssl_values:
            ssl_config = SSLConfig(
                ssl_cert_path=ssl_values.get('ssl_cert'),
                ssl_key_path=ssl_values.get('ssl_key'),
                ssl_ca_path=ssl_values.get('ssl_ca')
            )
            config['connectivity_mechanism'] = 'S'
        
        # Parse SSH configuration (support both uppercase and lowercase)
        ssh_config = None
        ssh_params_map = {
            'SSH_HOST': 'ssh_host', 'ssh_host': 'ssh_host',
            'SSH_USER': 'ssh_user', 'ssh_user': 'ssh_user', 'ssh_username': 'ssh_user',
            'SSH_PORT': 'ssh_port', 'ssh_port': 'ssh_port',
            'SSH_KEY': 'ssh_key', 'ssh_key': 'ssh_key', 'ssh_key_file': 'ssh_key',
            'SSH_PASSWORD': 'ssh_password', 'ssh_password': 'ssh_password'
        }
        ssh_values = {}
        
        for ini_param, ssh_key in ssh_params_map.items():
            if ini_param in section:
                ssh_values[ssh_key] = section[ini_param]
        
        if ssh_values.get('ssh_host') and ssh_values.get('ssh_user'):
            ssh_port = 22
            if 'ssh_port' in ssh_values:
                try:
                    ssh_port = int(ssh_values['ssh_port'])
                except ValueError:
                    raise ValueError(f"Invalid SSH port value in section {section_name}: {ssh_values['ssh_port']}")
            
            ssh_config = SSHConfig(
                ssh_host=ssh_values['ssh_host'],
                ssh_user=ssh_values['ssh_user'],
                ssh_port=ssh_port,
                ssh_key_path=ssh_values.get('ssh_key')
            )
            config['connectivity_mechanism'] = 'SSH'
        
        # Set default connectivity mechanism if not set
        if 'connectivity_mechanism' not in config:
            config['connectivity_mechanism'] = 'D'
        
        # Parse database-specific parameters (Snowflake, etc.)
        snowflake_params = ['WAREHOUSE', 'ACCOUNT', 'ROLE']
        for param in snowflake_params:
            if param in section:
                config[param.lower()] = section[param]
        
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
            raise ValueError(f"Error creating database configuration for section {section_name}: {str(e)}")
    
    def parse_all_connections(self) -> Dict[str, DatabaseConfig]:
        """
        Parse all database connections from the INI file
        
        Returns:
            Dictionary mapping connection IDs to DatabaseConfig instances
        """
        connections = {}
        connection_sections = self.get_connection_sections()
        
        for section_name in connection_sections:
            try:
                config = self.parse_connection_config(section_name)
                # Use section name as connection ID, replacing spaces with underscores
                connection_id = section_name.replace(' ', '_').upper()
                connections[connection_id] = config
                self.logger.info(f"Parsed configuration for connection: {connection_id} ({config.dbType.value})")
            except Exception as e:
                self.logger.error(f"Error parsing configuration for section {section_name}: {str(e)}")
        
        return connections
    
    def get_server_config(self) -> Optional[Dict]:
        """
        Get server configuration from INI file if present
        
        Returns:
            Server configuration dictionary or None
        """
        if 'SERVER' in self.config:
            return dict(self.config['SERVER'])
        return None
    
    def validate_connections(self) -> Dict[str, List[str]]:
        """
        Validate all connection configurations
        
        Returns:
            Dictionary mapping connection IDs to lists of validation errors
        """
        validation_results = {}
        connection_sections = self.get_connection_sections()
        
        for section_name in connection_sections:
            connection_id = section_name.replace(' ', '_').upper()
            errors = []
            
            try:
                self.parse_connection_config(section_name)
            except Exception as e:
                errors.append(str(e))
            
            validation_results[connection_id] = errors
        
        return validation_results
    
    def list_connections_summary(self) -> List[Dict]:
        """
        Get a summary of all connections with basic information
        
        Returns:
            List of connection summary dictionaries
        """
        summaries = []
        connection_sections = self.get_connection_sections()
        
        for section_name in connection_sections:
            connection_id = section_name.replace(' ', '_').upper()
            try:
                config = self.parse_connection_config(section_name)
                summaries.append({
                    'connection_id': connection_id,
                    'section_name': section_name,
                    'db_type': config.dbType.value,
                    'hostname': config.hostname,
                    'port': config.port,
                    'database': config.dbname,
                    'has_ssl': config.ssl_config is not None,
                    'has_ssh': config.ssh_config is not None,
                    'status': 'valid'
                })
            except Exception as e:
                summaries.append({
                    'connection_id': connection_id,
                    'section_name': section_name,
                    'db_type': 'Unknown',
                    'hostname': 'Unknown',
                    'port': 0,
                    'database': 'Unknown',
                    'has_ssl': False,
                    'has_ssh': False,
                    'status': 'invalid',
                    'error': str(e)
                })
        
        return summaries
    
    @staticmethod
    def create_sample_ini_file(file_path: str):
        """
        Create a sample INI configuration file
        
        Args:
            file_path: Path where the sample file should be created
        """
        sample_content = """# ScikiQ Database MCP Server Configuration
# This file contains database connection configurations

[Production MySQL]
DB_TYPE=MYSQL
HOSTNAME=localhost
PORT=3306
DATABASE=production
USERNAME=prod_user
PASSWORD=your_password_here
PASSWORD_ENCRYPTED=0
SCHEMA=public

[Development PostgreSQL]
DB_TYPE=POSTGRES
HOSTNAME=localhost
PORT=5432
DATABASE=development
USERNAME=dev_user
PASSWORD=dev_password
PASSWORD_ENCRYPTED=0

[Data Warehouse]
DB_TYPE=SNOWFLAKE
HOSTNAME=mycompany.snowflakecomputing.com
DATABASE=ANALYTICS
USERNAME=analytics_user
PASSWORD=analytics_password
PASSWORD_ENCRYPTED=0
WAREHOUSE=COMPUTE_WH
ACCOUNT=mycompany
ROLE=ANALYST

[Secure Database with SSL]
DB_TYPE=POSTGRES
HOSTNAME=secure-db.example.com
PORT=5432
DATABASE=secure_db
USERNAME=secure_user
PASSWORD=secure_password
PASSWORD_ENCRYPTED=0
SSL_MODE=require
SSL_CERT=/path/to/client-cert.pem
SSL_KEY=/path/to/client-key.pem
SSL_CA=/path/to/ca-cert.pem

[SSH Tunnel Database]
DB_TYPE=MYSQL
HOSTNAME=internal-db.local
PORT=3306
DATABASE=internal_db
USERNAME=internal_user
PASSWORD=internal_password
PASSWORD_ENCRYPTED=0
SSH_HOST=jump-server.example.com
SSH_USER=ssh_user
SSH_PORT=22
SSH_KEY=/path/to/ssh_key

[Server Configuration]
LOG_LEVEL=INFO
MAX_CONNECTIONS=10
TIMEOUT=30
"""
        
        try:
            Path(file_path).write_text(sample_content)
            print(f"Sample INI configuration file created: {file_path}")
        except Exception as e:
            print(f"Error creating sample INI file: {str(e)}")