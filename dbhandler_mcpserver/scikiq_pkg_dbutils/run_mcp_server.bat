@echo off
REM ScikiQ Database MCP Server Startup Script for Windows

REM Get the directory where this script is located
set SCRIPT_DIR=%~dp0

REM Run the MCP server
python "%SCRIPT_DIR%run_mcp_server.py" %*

REM Pause if there was an error (optional)
if errorlevel 1 pause