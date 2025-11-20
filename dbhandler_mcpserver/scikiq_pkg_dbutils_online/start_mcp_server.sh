#!/bin/bash
# ScikiQ Database MCP Server Startup Script for Linux/Mac
# 
# This script starts the MCP server with environment file support.
# Ideal for use with Claude Desktop configuration.

# Default settings
ENV_FILE=".env"
LOG_LEVEL="INFO"
SERVER_NAME="ScikiQ Database MCP Server"

# Function to show help
show_help() {
    echo "Usage: $0 [options]"
    echo
    echo "Options:"
    echo "  --env-file FILE     Environment file path (default: .env)"
    echo "  --log-level LEVEL   Log level (default: INFO)"
    echo "  --name NAME         Server name"
    echo "  --help              Show this help"
    echo
    echo "Environment file format:"
    echo "  CONNECTION_ID_DB_TYPE=MYSQL"
    echo "  CONNECTION_ID_HOSTNAME=localhost"
    echo "  CONNECTION_ID_PORT=3306"
    echo "  CONNECTION_ID_DATABASE=mydb"
    echo "  CONNECTION_ID_USERNAME=user"
    echo "  CONNECTION_ID_PASSWORD=password"
    echo
    echo "Claude Desktop Configuration:"
    echo "  Add to claude_desktop_config.json:"
    echo '  "mcpServers": {'
    echo '    "scikiq-db": {'
    echo '      "command": "python3",'
    echo '      "args": ['
    echo '        "/path/to/run_mcp_server.py",'
    echo '        "--env-file", "/path/to/.env"'
    echo '      ]'
    echo '    }'
    echo '  }'
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --env-file)
            ENV_FILE="$2"
            shift 2
            ;;
        --log-level)
            LOG_LEVEL="$2"
            shift 2
            ;;
        --name)
            SERVER_NAME="$2"
            shift 2
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

echo "Starting ScikiQ Database MCP Server..."

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if environment file exists
if [[ ! -f "$ENV_FILE" ]]; then
    echo "Warning: Environment file '$ENV_FILE' not found."
    echo "Creating sample environment file..."
    
    if python3 "$SCRIPT_DIR/run_mcp_server.py" --create-sample-env "$ENV_FILE"; then
        echo
        echo "Sample environment file created: $ENV_FILE"
        echo "Please edit this file with your actual database credentials."
        echo "Then run this script again."
        exit 0
    else
        echo "Failed to create sample environment file."
        exit 1
    fi
fi

# Validate environment file before starting
echo "Validating environment file: $ENV_FILE"
if ! python3 "$SCRIPT_DIR/run_mcp_server.py" --validate-env --env-file "$ENV_FILE"; then
    echo "Environment file validation failed."
    echo "Please check your configuration and try again."
    exit 1
fi

echo "Starting server with environment file: $ENV_FILE"
echo "Log level: $LOG_LEVEL"
echo "Server name: $SERVER_NAME"
echo

# Start the MCP server
python3 "$SCRIPT_DIR/run_mcp_server.py" --env-file "$ENV_FILE" --log-level "$LOG_LEVEL" --name "$SERVER_NAME"

echo "MCP Server stopped."