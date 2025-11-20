"""
Configuration Schema Validation

Validates configuration files against JSON schema and provides validation utilities.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from jsonschema import validate, ValidationError as JsonSchemaValidationError, RefResolver
import os

from scikiq_dbutils.mcp_server.utils.error_handler import ValidationError


class ConfigValidator:
    """
    Validates configuration files against JSON schema
    """
    
    def __init__(self, schema_path: Optional[str] = None):
        """
        Initialize config validator
        
        Args:
            schema_path: Path to JSON schema file. If None, uses default schema.
        """
        self.logger = logging.getLogger(__name__)
        
        # Load schema
        if schema_path is None:
            schema_path = Path(__file__).parent / "schema.json"
        
        self.schema_path = Path(schema_path)
        self.schema = self._load_schema()
        
        # Create resolver for schema references
        self.resolver = RefResolver(
            base_uri=f"file://{self.schema_path.parent}/",
            referrer=self.schema
        )
    
    def _load_schema(self) -> Dict[str, Any]:
        """Load JSON schema from file"""
        try:
            with open(self.schema_path, 'r', encoding='utf-8') as f:
                schema = json.load(f)
            
            self.logger.debug(f"Loaded configuration schema from {self.schema_path}")
            return schema
            
        except FileNotFoundError:
            self.logger.error(f"Schema file not found: {self.schema_path}")
            raise ValidationError(f"Configuration schema not found: {self.schema_path}")
        
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in schema file: {e}")
            raise ValidationError(f"Invalid JSON schema: {e}")
    
    def validate_config(self, config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate configuration against schema
        
        Args:
            config: Configuration dictionary to validate
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        try:
            validate(instance=config, schema=self.schema, resolver=self.resolver)
            self.logger.debug("Configuration validation passed")
            return True, []
            
        except JsonSchemaValidationError as e:
            error_msg = self._format_validation_error(e)
            errors.append(error_msg)
            self.logger.warning(f"Configuration validation failed: {error_msg}")
            return False, errors
    
    def _format_validation_error(self, error: JsonSchemaValidationError) -> str:
        """
        Format validation error message for better readability
        
        Args:
            error: JSON schema validation error
            
        Returns:
            Formatted error message
        """
        path = " -> ".join(str(p) for p in error.absolute_path)
        
        if path:
            return f"Error at '{path}': {error.message}"
        else:
            return f"Configuration error: {error.message}"
    
    def validate_connection_config(self, connection_config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate a single connection configuration
        
        Args:
            connection_config: Single connection configuration
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        # Get the connection schema from the main schema
        connection_schema = self.schema["properties"]["connections"]["items"]
        
        try:
            validate(instance=connection_config, schema=connection_schema, resolver=self.resolver)
            return True, []
            
        except JsonSchemaValidationError as e:
            error_msg = self._format_validation_error(e)
            return False, [error_msg]
    
    def get_schema_defaults(self) -> Dict[str, Any]:
        """
        Extract default values from schema
        
        Returns:
            Dictionary with default values
        """
        defaults = {}
        
        def extract_defaults(schema_part, path=""):
            if isinstance(schema_part, dict):
                if "default" in schema_part:
                    defaults[path] = schema_part["default"]
                
                if "properties" in schema_part:
                    for prop, prop_schema in schema_part["properties"].items():
                        new_path = f"{path}.{prop}" if path else prop
                        extract_defaults(prop_schema, new_path)
        
        extract_defaults(self.schema)
        return defaults
    
    def apply_defaults(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply default values to configuration
        
        Args:
            config: Configuration to apply defaults to
            
        Returns:
            Configuration with defaults applied
        """
        config_with_defaults = config.copy()
        defaults = self.get_schema_defaults()
        
        for path, default_value in defaults.items():
            keys = path.split('.')
            current = config_with_defaults
            
            # Navigate to the parent of the target key
            for key in keys[:-1]:
                if key not in current:
                    current[key] = {}
                current = current[key]
            
            # Set default if key doesn't exist
            final_key = keys[-1]
            if final_key not in current:
                current[final_key] = default_value
        
        return config_with_defaults


class EnvironmentConfigValidator:
    """
    Validates environment-based configuration
    """
    
    @staticmethod
    def validate_required_env_vars(required_vars: List[str]) -> Tuple[bool, List[str]]:
        """
        Validate that required environment variables are set
        
        Args:
            required_vars: List of required environment variable names
            
        Returns:
            Tuple of (all_present, missing_vars)
        """
        missing_vars = []
        
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        return len(missing_vars) == 0, missing_vars
    
    @staticmethod
    def validate_database_env_config(prefix: str) -> Tuple[bool, List[str]]:
        """
        Validate database configuration from environment variables
        
        Args:
            prefix: Environment variable prefix (e.g., "DB1_")
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        required_vars = [
            f"{prefix}TYPE",
            f"{prefix}HOST", 
            f"{prefix}DATABASE",
            f"{prefix}USER",
            f"{prefix}PASSWORD"
        ]
        
        errors = []
        
        # Check required variables
        for var in required_vars:
            if not os.getenv(var):
                errors.append(f"Missing required environment variable: {var}")
        
        # Validate port if provided
        port_var = f"{prefix}PORT"
        port_value = os.getenv(port_var)
        if port_value:
            try:
                port = int(port_value)
                if port < 1 or port > 65535:
                    errors.append(f"Invalid port in {port_var}: {port}")
            except ValueError:
                errors.append(f"Invalid port format in {port_var}: {port_value}")
        
        # Validate database type
        type_var = f"{prefix}TYPE"
        db_type = os.getenv(type_var)
        if db_type:
            valid_types = [
                "MYSQL", "POSTGRES", "ORACLE", "ORACLE-EBS", "ORACLE-FUSION",
                "SQLSERVER", "MONGODB", "SNOWFLAKE", "BIGQUERY", "REDSHIFT",
                "ATHENA", "SAPHANA", "VERTICA", "DB2", "TERADATA"
            ]
            
            if db_type.upper() not in valid_types:
                errors.append(f"Invalid database type in {type_var}: {db_type}")
        
        return len(errors) == 0, errors


def validate_config_file(config_path: str) -> Tuple[bool, List[str], Optional[Dict[str, Any]]]:
    """
    Validate a configuration file
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        Tuple of (is_valid, errors, parsed_config)
    """
    logger = logging.getLogger(__name__)
    
    try:
        # Load configuration file
        with open(config_path, 'r', encoding='utf-8') as f:
            if config_path.endswith('.json'):
                config = json.load(f)
            elif config_path.endswith(('.yaml', '.yml')):
                import yaml
                config = yaml.safe_load(f)
            else:
                return False, [f"Unsupported configuration file format: {config_path}"], None
        
        # Validate against schema
        validator = ConfigValidator()
        is_valid, errors = validator.validate_config(config)
        
        if is_valid:
            # Apply defaults
            config = validator.apply_defaults(config)
            logger.info(f"Configuration file validation passed: {config_path}")
        else:
            logger.error(f"Configuration file validation failed: {config_path}")
        
        return is_valid, errors, config
        
    except FileNotFoundError:
        return False, [f"Configuration file not found: {config_path}"], None
    
    except json.JSONDecodeError as e:
        return False, [f"Invalid JSON in configuration file: {e}"], None
    
    except Exception as e:
        return False, [f"Error reading configuration file: {e}"], None


def create_sample_config() -> Dict[str, Any]:
    """
    Create a sample configuration with all options
    
    Returns:
        Sample configuration dictionary
    """
    return {
        "connections": [
            {
                "connection_id": "prod_mysql",
                "db_type": "MYSQL",
                "hostname": "mysql.example.com",
                "port": 3306,
                "database": "production",
                "username": "app_user",
                "password": "secure_password_here",
                "password_encrypted": 0,
                "ssl": True,
                "connection_timeout": 30,
                "query_timeout": 300
            },
            {
                "connection_id": "analytics_postgres",
                "db_type": "POSTGRES", 
                "hostname": "postgres.example.com",
                "port": 5432,
                "database": "analytics",
                "username": "analytics_user",
                "password": "secure_password_here",
                "password_encrypted": 0,
                "schema": "public",
                "ssl": True,
                "ssl_mode": "require",
                "connection_timeout": 30,
                "query_timeout": 600
            }
        ],
        "security": {
            "master_password": "change-this-master-password",
            "rate_limit": {
                "max_requests": 100,
                "window_minutes": 60,
                "burst_limit": 25
            },
            "allowed_hosts": [
                "localhost",
                "*.example.com"
            ],
            "allow_private_networks": False,
            "require_ssl_remote": True,
            "sql_injection_protection": True
        },
        "logging": {
            "level": "INFO",
            "structured": False,
            "security_audit": True
        },
        "server": {
            "name": "ScikiQ Database MCP Server",
            "version": "1.0.0",
            "max_concurrent_connections": 50,
            "connection_pool_size": 5,
            "query_result_limit": 10000
        },
        "performance": {
            "enable_metrics": True,
            "slow_query_threshold_ms": 5000,
            "cache_enabled": False,
            "cache_ttl_seconds": 300
        }
    }


def save_sample_config(file_path: str, format: str = "json") -> bool:
    """
    Save a sample configuration file
    
    Args:
        file_path: Path where to save the sample config
        format: Format to save in ("json" or "yaml")
        
    Returns:
        True if successful, False otherwise
    """
    logger = logging.getLogger(__name__)
    
    try:
        sample_config = create_sample_config()
        
        with open(file_path, 'w', encoding='utf-8') as f:
            if format.lower() == "json":
                json.dump(sample_config, f, indent=2)
            elif format.lower() in ["yaml", "yml"]:
                import yaml
                yaml.dump(sample_config, f, default_flow_style=False, indent=2)
            else:
                logger.error(f"Unsupported format: {format}")
                return False
        
        logger.info(f"Sample configuration saved to: {file_path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to save sample configuration: {e}")
        return False