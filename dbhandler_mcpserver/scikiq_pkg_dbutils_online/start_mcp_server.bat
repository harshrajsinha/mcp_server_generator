@echo off
REM ScikiQ Database MCP Server Startup Script for Windows
REM 
REM This script starts the MCP server with environment file support.
REM Ideal for use with Claude Desktop configuration.

echo Starting ScikiQ Database MCP Server...

REM Set default environment file path
set ENV_FILE=.env
set LOG_LEVEL=INFO
set SERVER_NAME=ScikiQ Database MCP Server

REM Parse command line arguments
:parse_args
if "%1"=="" goto :start_server
if "%1"=="--env-file" (
    set ENV_FILE=%2
    shift
    shift
    goto :parse_args
)
if "%1"=="--log-level" (
    set LOG_LEVEL=%2
    shift
    shift
    goto :parse_args
)
if "%1"=="--name" (
    set SERVER_NAME=%2
    shift
    shift
    goto :parse_args
)
if "%1"=="--help" (
    echo Usage: %0 [options]
    echo.
    echo Options:
    echo   --env-file FILE     Environment file path ^(default: .env^)
    echo   --log-level LEVEL   Log level ^(default: INFO^)
    echo   --name NAME         Server name
    echo   --help              Show this help
    echo.
    echo Environment file format:
    echo   CONNECTION_ID_DB_TYPE=MYSQL
    echo   CONNECTION_ID_HOSTNAME=localhost
    echo   CONNECTION_ID_PORT=3306
    echo   CONNECTION_ID_DATABASE=mydb
    echo   CONNECTION_ID_USERNAME=user
    echo   CONNECTION_ID_PASSWORD=password
    echo.
    echo Claude Desktop Configuration:
    echo   Add to claude_desktop_config.json:
    echo   "mcpServers": {
    echo     "scikiq-db": {
    echo       "command": "python",
    echo       "args": [
    echo         "C:/path/to/run_mcp_server.py",
    echo         "--env-file", "C:/path/to/.env"
    echo       ]
    echo     }
    echo   }
    goto :end
)
shift
goto :parse_args

:start_server
REM Check if environment file exists
if not exist "%ENV_FILE%" (
    echo Warning: Environment file '%ENV_FILE%' not found.
    echo Creating sample environment file...
    python "%~dp0run_mcp_server.py" --create-sample-env "%ENV_FILE%"
    if errorlevel 1 (
        echo Failed to create sample environment file.
        exit /b 1
    )
    echo.
    echo Sample environment file created: %ENV_FILE%
    echo Please edit this file with your actual database credentials.
    echo Then run this script again.
    goto :end
)

REM Validate environment file before starting
echo Validating environment file: %ENV_FILE%
python "%~dp0run_mcp_server.py" --validate-env --env-file "%ENV_FILE%"
if errorlevel 1 (
    echo Environment file validation failed.
    echo Please check your configuration and try again.
    exit /b 1
)

echo Starting server with environment file: %ENV_FILE%
echo Log level: %LOG_LEVEL%
echo Server name: %SERVER_NAME%
echo.

REM Start the MCP server
python "%~dp0run_mcp_server.py" --env-file "%ENV_FILE%" --log-level "%LOG_LEVEL%" --name "%SERVER_NAME%"

:end
echo MCP Server stopped.