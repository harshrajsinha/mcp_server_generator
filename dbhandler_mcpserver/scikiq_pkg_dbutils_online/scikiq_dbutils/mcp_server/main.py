#!/usr/bin/env python3
"""
ScikiQ Database MCP Server Startup Script

Starts the Model Context Protocol server for database operations.
"""

import asyncio
import argparse
import logging
import sys
import signal
from pathlib import Path

# Add the parent directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from scikiq_dbutils.mcp_server.server import MCPServer
from scikiq_dbutils.mcp_server.config.manager import ConfigManager
from scikiq_dbutils.mcp_server.config.env_parser import EnvironmentConfigParser
from scikiq_dbutils.mcp_server.config.ini_parser import IniConfigParser


def setup_signal_handlers(server: MCPServer):
    """Setup signal handlers for graceful shutdown"""
    def signal_handler(signum, frame):
        logging.info(f"Received signal {signum}, shutting down...")
        server.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="ScikiQ Database MCP Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Start server with default settings
  %(prog)s --config /path/to/config          # Use custom config directory
  %(prog)s --env-file /path/to/.env          # Load database configs from environment file
  %(prog)s --config-file /path/to/config.ini # Load database configs from INI file
  %(prog)s --create-sample-env sample.env    # Create a sample environment file
  %(prog)s --create-sample-env sample.ini    # Create a sample INI configuration file
  %(prog)s --validate-env --env-file .env    # Validate environment file configurations
  %(prog)s --validate-env --config-file config.ini # Validate INI file configurations
  %(prog)s --help-tools                      # Show available database tools
  %(prog)s --help-tool db_execute_query      # Show help for specific tool
        """
    )
    
    parser.add_argument(
        "--config", "-c",
        type=str,
        help="Configuration directory path (default: ~/.scikiq_mcp)"
    )
    
    parser.add_argument(
        "--env-file", "-e",
        type=str,
        help="Environment file path containing database credentials (e.g., .env)"
    )
    
    parser.add_argument(
        "--config-file", "-f",
        type=str,
        help="INI configuration file path containing database credentials (e.g., config.ini)"
    )
    
    parser.add_argument(
        "--log-level", "-l",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Set logging level (default: INFO)"
    )
    
    parser.add_argument(
        "--name", "-n",
        type=str,
        default="ScikiQ Database MCP Server",
        help="Server name (default: ScikiQ Database MCP Server)"
    )
    
    parser.add_argument(
        "--version", "-v",
        type=str,
        default="1.0.0",
        help="Server version (default: 1.0.0)"
    )
    
    parser.add_argument(
        "--help-tools",
        action="store_true",
        help="Show available database tools and exit"
    )
    
    parser.add_argument(
        "--help-tool",
        type=str,
        metavar="TOOL_NAME",
        help="Show help for a specific tool and exit"
    )
    
    parser.add_argument(
        "--list-connections",
        action="store_true",
        help="List configured database connections and exit"
    )
    
    parser.add_argument(
        "--test-connection",
        type=str,
        metavar="CONNECTION_ID",
        help="Test a specific database connection and exit"
    )
    
    parser.add_argument(
        "--validate-config",
        action="store_true",
        help="Validate configuration and exit"
    )
    
    parser.add_argument(
        "--validate-env",
        action="store_true",
        help="Validate environment file configuration and exit"
    )
    
    parser.add_argument(
        "--create-sample-env",
        type=str,
        metavar="FILE_PATH",
        help="Create a sample environment file and exit"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    
    try:
        # Handle sample environment file creation
        if args.create_sample_env:
            try:
                if args.create_sample_env.endswith('.ini'):
                    IniConfigParser.create_sample_ini_file(args.create_sample_env)
                else:
                    EnvironmentConfigParser.create_sample_env_file(args.create_sample_env)
                return 0
            except Exception as e:
                logger.error(f"Failed to create sample configuration file: {str(e)}")
                return 1
        
        # Initialize configuration manager
        config_manager = ConfigManager(args.config)
        
        # Load configuration file if provided
        config_parser = None
        
        # Check if both env-file and config-file are provided
        if args.env_file and args.config_file:
            logger.error("Cannot specify both --env-file and --config-file. Please use only one.")
            return 1
        
        if args.env_file:
            try:
                logger.info(f"Loading environment file: {args.env_file}")
                config_parser = EnvironmentConfigParser(args.env_file)
                
                # Load database configurations from environment file
                connections = config_parser.parse_all_connections()
                logger.info(f"Loaded {len(connections)} database connections from environment file")
                
                # Add connections to config manager
                for conn_id, db_config in connections.items():
                    config_manager.add_database_config(conn_id, db_config)
                    logger.info(f"Added connection: {conn_id} ({db_config.dbType.value})")
                
                # Apply server configuration
                server_config = config_parser.get_server_config()
                if server_config:
                    logger.info(f"Applied server configuration from environment: {server_config}")
                
            except Exception as e:
                logger.error(f"Failed to load environment file: {str(e)}")
                return 1
        
        elif args.config_file:
            try:
                logger.info(f"Loading INI configuration file: {args.config_file}")
                config_parser = IniConfigParser(args.config_file)
                
                # Load database configurations from INI file
                connections = config_parser.parse_all_connections()
                logger.info(f"Loaded {len(connections)} database connections from INI file")
                
                # Add connections to config manager
                for conn_id, db_config in connections.items():
                    config_manager.add_database_config(conn_id, db_config)
                    logger.info(f"Added connection: {conn_id} ({db_config.dbType.value})")
                
                # Apply server configuration
                server_config = config_parser.get_server_config()
                enabled_tools = config_parser.get_enabled_tools()
                if server_config:
                    logger.info(f"Applied server configuration from INI file: {server_config}")
                if enabled_tools:
                    logger.info(f"Enabled tools filter: {len(enabled_tools)} tools enabled")
                
            except Exception as e:
                logger.error(f"Failed to load INI configuration file: {str(e)}")
                return 1
        
        # Handle utility commands
        if args.help_tools or args.help_tool:
            # Get enabled tools from config if available
            enabled_tools = None
            if config_parser and hasattr(config_parser, 'get_enabled_tools'):
                enabled_tools = config_parser.get_enabled_tools()
            server = MCPServer(name=args.name, version=args.version, enabled_tools=enabled_tools)
            
            if args.help_tools:
                print(server.get_tool_help())
            elif args.help_tool:
                print(server.get_tool_help(args.help_tool))
            
            return 0
        
        if args.list_connections:
            configs = config_manager.list_database_configs(mask_sensitive=True)
            if configs:
                print("Configured Database Connections:")
                print("=" * 40)
                for conn_id, config in configs.items():
                    db_type = config.get("dbType", "Unknown")
                    hostname = config.get("hostname", "Unknown")
                    dbname = config.get("dbname", "Unknown")
                    print(f"  {conn_id}: {db_type} @ {hostname}/{dbname}")
            else:
                print("No database connections configured.")
            return 0
        
        if args.test_connection:
            config = config_manager.get_database_config(args.test_connection)
            if not config:
                print(f"Error: Connection '{args.test_connection}' not found.")
                return 1
            
            print(f"Testing connection '{args.test_connection}'...")
            try:
                test_result = config_manager.test_connection(config.to_dict())
                if test_result.get("error", 0) == 0:
                    print("✓ Connection test successful!")
                else:
                    print(f"✗ Connection test failed: {test_result.get('msg', 'Unknown error')}")
                    return 1
            except Exception as e:
                print(f"✗ Connection test failed: {str(e)}")
                return 1
            
            return 0
        
        if args.validate_config:
            print("Validating configuration...")
            validation_results = config_manager.validate_all_configs()
            
            has_errors = False
            for conn_id, errors in validation_results.items():
                if errors:
                    has_errors = True
                    print(f"✗ {conn_id}: {'; '.join(errors)}")
                else:
                    print(f"✓ {conn_id}: Valid")
            
            if not validation_results:
                print("No database configurations found.")
            elif not has_errors:
                print("All configurations are valid.")
            
            return 1 if has_errors else 0
        
        if args.validate_env:
            config_file = args.env_file or args.config_file
            if not config_file:
                print("Error: --env-file or --config-file is required when using --validate-env")
                return 1
            
            try:
                print(f"Validating configuration file: {config_file}")
                
                if config_file.endswith('.ini'):
                    parser = IniConfigParser(config_file)
                    validation_results = parser.validate_connections()
                else:
                    parser = EnvironmentConfigParser(config_file)
                    validation_results = parser.validate_environment()
                
                has_errors = False
                for conn_id, errors in validation_results.items():
                    if errors:
                        has_errors = True
                        print(f"✗ {conn_id}: {'; '.join(errors)}")
                    else:
                        print(f"✓ {conn_id}: Valid")
                
                if not validation_results:
                    print("No database connections found in configuration file.")
                elif not has_errors:
                    print("All configurations are valid.")
                
                # Show connection summary
                print("\nConnection Summary:")
                summaries = parser.list_connections_summary()
                for summary in summaries:
                    if summary['status'] == 'valid':
                        ssl_info = " (SSL)" if summary['has_ssl'] else ""
                        ssh_info = " (SSH)" if summary['has_ssh'] else ""
                        print(f"  {summary['connection_id']}: {summary['db_type']} @ {summary['hostname']}:{summary['port']}/{summary['database']}{ssl_info}{ssh_info}")
                    else:
                        print(f"  {summary['connection_id']}: ERROR - {summary['error']}")
                
                return 1 if has_errors else 0
                
            except Exception as e:
                print(f"Error validating configuration file: {str(e)}")
                return 1
        
        # Start the MCP server
        logger.info(f"Starting {args.name} v{args.version}")
        
        # Prepare connection configurations
        connection_configs = None
        enabled_tools = None
        if config_parser:
            connection_configs = config_parser.parse_all_connections()
            # Get enabled tools from config if available
            if hasattr(config_parser, 'get_enabled_tools'):
                enabled_tools = config_parser.get_enabled_tools()
        
        # Create and configure server
        server = MCPServer(name=args.name, version=args.version, 
                          connection_configs=connection_configs,
                          enabled_tools=enabled_tools)
        
        # Setup signal handlers for graceful shutdown
        setup_signal_handlers(server)
        
        # Run the server
        logger.info("Server starting in stdio mode...")
        asyncio.run(server.run_stdio())
        
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
        return 0
    except Exception as e:
        logger.error(f"Server error: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())