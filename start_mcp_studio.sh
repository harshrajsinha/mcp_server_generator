#!/bin/bash
# Start MCP Studio Server on port 30211

cd /home/superadmin/hr/mcp_server_code/mcp_server_generator

# Check if already running
if curl -s http://localhost:30211/health > /dev/null 2>&1; then
    echo "MCP Studio already running on port 30211"
    exit 0
fi

# Start in background
nohup python3 app.py > /tmp/mcp_studio.log 2>&1 &
echo "MCP Studio started with PID: $!"
sleep 2

# Verify
if curl -s http://localhost:30211/health > /dev/null 2>&1; then
    echo "✅ MCP Studio running on http://localhost:30211"
else
    echo "❌ Failed to start. Check /tmp/mcp_studio.log"
fi
