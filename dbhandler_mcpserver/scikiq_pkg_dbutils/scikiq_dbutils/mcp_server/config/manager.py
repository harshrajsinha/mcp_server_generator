"""
Configuration Manager

Manages server configuration and database connection configurations.
"""

import os
import json
import yaml
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
import logging
from datetime import datetime

from .database_config import DatabaseConfig, DatabaseType


class ConfigManager:
    """
    Manages MCP server configuration including database connections
    """
    
    def __init__(self, config_dir: Optional[str] = None):
        self.config_dir = Path(config_dir or os.path.expanduser("~/.scikiq_mcp"))
        self.config_dir.mkdir(exist_ok=True)
        
        self.server_config_file = self.config_dir / "server_config.json"
        self.connections_config_file = self.config_dir / "connections.json"
        
        self.logger = logging.getLogger(__name__)
        
        # Load configurations
        self.server_config = self._load_server_config()
        self.database_configs: Dict[str, DatabaseConfig] = self._load_database_configs()
    
    def _load_server_config(self) -> Dict[str, Any]:
        """Load server configuration"""
        default_config = {
            "server": {
                "name": "ScikiQ Database MCP Server",
                "version": "1.0.0",
                "log_level": "INFO",
                "max_connections": 100
            },
            "security": {
                "enable_auth": False,
                "api_key": None,
                "allowed_ips": []
            },
            "features": {
                "enable_connection_pooling": True,
                "default_query_limit": 10000,
                "max_query_limit": 100000,
                "enable_query_cache": False,
                "cache_ttl_seconds": 300
            }
        }
        
        if self.server_config_file.exists():
            try:
                with open(self.server_config_file, 'r') as f:
                    loaded_config = json.load(f)
                    # Merge with defaults
                    for section, values in loaded_config.items():
                        if section in default_config:
                            default_config[section].update(values)
                        else:
                            default_config[section] = values
            except Exception as e:
                self.logger.warning(f"Error loading server config: {e}, using defaults")
        
        return default_config
    
    def _load_database_configs(self) -> Dict[str, DatabaseConfig]:
        """Load database configurations"""
        configs = {}
        
        if self.connections_config_file.exists():
            try:
                with open(self.connections_config_file, 'r') as f:
                    data = json.load(f)
                    
                for conn_id, config_data in data.get("connections", {}).items():
                    try:
                        configs[conn_id] = DatabaseConfig.from_dict(config_data)
                    except Exception as e:
                        self.logger.error(f"Error loading database config '{conn_id}': {e}")
                        
            except Exception as e:
                self.logger.warning(f"Error loading database configs: {e}")
        
        return configs
    
    def save_server_config(self):
        """Save server configuration to file"""
        try:
            with open(self.server_config_file, 'w') as f:
                json.dump(self.server_config, f, indent=2)
            self.logger.info("Server configuration saved")
        except Exception as e:
            self.logger.error(f"Error saving server config: {e}")
    
    def save_database_configs(self):
        """Save database configurations to file"""
        try:
            data = {
                "connections": {
                    conn_id: config.to_dict()
                    for conn_id, config in self.database_configs.items()
                },
                "metadata": {
                    "last_updated": datetime.now().isoformat(),
                    "total_connections": len(self.database_configs)
                }
            }
            
            with open(self.connections_config_file, 'w') as f:
                json.dump(data, f, indent=2)
            self.logger.info(f"Database configurations saved ({len(self.database_configs)} connections)")
        except Exception as e:
            self.logger.error(f"Error saving database configs: {e}")
    
    def add_database_config(self, connection_id: str, config: Union[DatabaseConfig, Dict[str, Any]]) -> bool:
        """
        Add a new database configuration
        
        Args:
            connection_id: Unique identifier for the connection
            config: DatabaseConfig instance or configuration dictionary
            
        Returns:
            True if added successfully, False otherwise
        """
        try:
            if isinstance(config, dict):
                config = DatabaseConfig.from_dict(config)
            elif not isinstance(config, DatabaseConfig):
                raise ValueError("config must be DatabaseConfig instance or dictionary")
            
            self.database_configs[connection_id] = config
            self.save_database_configs()
            self.logger.info(f"Added database configuration: {connection_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error adding database config '{connection_id}': {e}")
            return False
    
    def remove_database_config(self, connection_id: str) -> bool:
        """
        Remove a database configuration
        
        Args:
            connection_id: Connection identifier to remove
            
        Returns:
            True if removed successfully, False otherwise
        """
        if connection_id in self.database_configs:
            del self.database_configs[connection_id]
            self.save_database_configs()
            self.logger.info(f"Removed database configuration: {connection_id}")
            return True
        return False
    
    def get_database_config(self, connection_id: str) -> Optional[DatabaseConfig]:
        """Get database configuration by ID"""
        return self.database_configs.get(connection_id)
    
    def list_database_configs(self, mask_sensitive: bool = True) -> Dict[str, Dict[str, Any]]:
        """
        List all database configurations
        
        Args:
            mask_sensitive: Whether to mask sensitive data
            
        Returns:
            Dictionary of connection configurations
        """
        if mask_sensitive:
            return {
                conn_id: config.mask_sensitive_data()
                for conn_id, config in self.database_configs.items()
            }
        else:
            return {
                conn_id: config.to_dict()
                for conn_id, config in self.database_configs.items()
            }
    
    def update_database_config(self, connection_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update an existing database configuration
        
        Args:
            connection_id: Connection identifier
            updates: Dictionary of fields to update
            
        Returns:
            True if updated successfully, False otherwise
        """
        if connection_id not in self.database_configs:
            return False
        
        try:
            current_config = self.database_configs[connection_id].to_dict()
            current_config.update(updates)
            
            updated_config = DatabaseConfig.from_dict(current_config)
            self.database_configs[connection_id] = updated_config
            self.save_database_configs()
            
            self.logger.info(f"Updated database configuration: {connection_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating database config '{connection_id}': {e}")
            return False
    
    def get_server_setting(self, section: str, key: str, default: Any = None) -> Any:
        """Get a server configuration setting"""
        return self.server_config.get(section, {}).get(key, default)
    
    def set_server_setting(self, section: str, key: str, value: Any):
        """Set a server configuration setting"""
        if section not in self.server_config:
            self.server_config[section] = {}
        self.server_config[section][key] = value
        self.save_server_config()
    
    def get_database_configs_by_type(self, db_type: DatabaseType) -> Dict[str, DatabaseConfig]:
        """Get all database configurations of a specific type"""
        return {
            conn_id: config
            for conn_id, config in self.database_configs.items()
            if config.dbType == db_type
        }
    
    def validate_all_configs(self) -> Dict[str, List[str]]:
        """
        Validate all database configurations
        
        Returns:
            Dictionary mapping connection IDs to validation error lists
        """
        validation_results = {}
        
        for conn_id, config in self.database_configs.items():
            try:
                config._validate()
                validation_results[conn_id] = []  # No errors
            except ValueError as e:
                validation_results[conn_id] = [str(e)]
            except Exception as e:
                validation_results[conn_id] = [f"Unexpected validation error: {str(e)}"]
        
        return validation_results
    
    def export_config(self, file_path: str, include_sensitive: bool = False):
        """
        Export configuration to file
        
        Args:
            file_path: Path to export file
            include_sensitive: Whether to include sensitive data
        """
        export_data = {
            "server_config": self.server_config,
            "database_configs": self.list_database_configs(mask_sensitive=not include_sensitive),
            "metadata": {
                "exported_at": datetime.now().isoformat(),
                "version": self.get_server_setting("server", "version", "1.0.0"),
                "include_sensitive": include_sensitive
            }
        }
        
        file_path = Path(file_path)
        
        try:
            if file_path.suffix.lower() == '.yaml' or file_path.suffix.lower() == '.yml':
                with open(file_path, 'w') as f:
                    yaml.dump(export_data, f, default_flow_style=False, indent=2)
            else:
                with open(file_path, 'w') as f:
                    json.dump(export_data, f, indent=2)
            
            self.logger.info(f"Configuration exported to: {file_path}")
            
        except Exception as e:
            self.logger.error(f"Error exporting configuration: {e}")
            raise
    
    def import_config(self, file_path: str, overwrite: bool = False) -> bool:
        """
        Import configuration from file
        
        Args:
            file_path: Path to import file
            overwrite: Whether to overwrite existing configurations
            
        Returns:
            True if imported successfully, False otherwise
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            self.logger.error(f"Import file not found: {file_path}")
            return False
        
        try:
            with open(file_path, 'r') as f:
                if file_path.suffix.lower() in ['.yaml', '.yml']:
                    data = yaml.safe_load(f)
                else:
                    data = json.load(f)
            
            # Import server config
            if "server_config" in data and overwrite:
                self.server_config.update(data["server_config"])
                self.save_server_config()
            
            # Import database configs
            if "database_configs" in data:
                imported_count = 0
                for conn_id, config_data in data["database_configs"].items():
                    if conn_id in self.database_configs and not overwrite:
                        self.logger.warning(f"Skipping existing connection: {conn_id}")
                        continue
                    
                    try:
                        config = DatabaseConfig.from_dict(config_data)
                        self.database_configs[conn_id] = config
                        imported_count += 1
                    except Exception as e:
                        self.logger.error(f"Error importing connection '{conn_id}': {e}")
                
                self.save_database_configs()
                self.logger.info(f"Imported {imported_count} database configurations")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error importing configuration: {e}")
            return False
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Get summary of current configuration"""
        db_types_count = {}
        for config in self.database_configs.values():
            db_type = config.dbType.value
            db_types_count[db_type] = db_types_count.get(db_type, 0) + 1
        
        return {
            "server": {
                "name": self.get_server_setting("server", "name"),
                "version": self.get_server_setting("server", "version"),
                "config_dir": str(self.config_dir)
            },
            "database_connections": {
                "total": len(self.database_configs),
                "by_type": db_types_count
            },
            "files": {
                "server_config": str(self.server_config_file),
                "connections_config": str(self.connections_config_file),
                "config_exists": {
                    "server": self.server_config_file.exists(),
                    "connections": self.connections_config_file.exists()
                }
            }
        }