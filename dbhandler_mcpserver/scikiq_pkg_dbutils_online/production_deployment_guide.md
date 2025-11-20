# Production Deployment Guide

## Quick Fix for Your Current Issue

For your production server at `mcp.scikiq.com`, you need to set the environment variable:

### Option 1: Set environment variable before starting the server

```bash
# Linux/macOS
export SERVER_BASE_URL=https://mcp.scikiq.com
python remote_mcp_server_admin.py --host 0.0.0.0 --port 80

# Windows
set SERVER_BASE_URL=https://mcp.scikiq.com
python remote_mcp_server_admin.py --host 0.0.0.0 --port 80

# PowerShell
$env:SERVER_BASE_URL="https://mcp.scikiq.com"
python remote_mcp_server_admin.py --host 0.0.0.0 --port 80
```

### Option 2: Create a production startup script

Create `start_production.sh` (Linux/macOS) or `start_production.bat` (Windows):

**Linux/macOS:**
```bash
#!/bin/bash
export SERVER_BASE_URL=https://mcp.scikiq.com
export CONFIG_PATH=config.ini
python remote_mcp_server_admin.py --host 0.0.0.0 --port 80 --db-path mcp_auth.db
```

**Windows:**
```batch
@echo off
set SERVER_BASE_URL=https://mcp.scikiq.com
set CONFIG_PATH=config.ini
python remote_mcp_server_admin.py --host 0.0.0.0 --port 80 --db-path mcp_auth.db
```

### Option 3: Docker deployment with environment variables

```dockerfile
# Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
ENV SERVER_BASE_URL=https://mcp.scikiq.com
EXPOSE 80
CMD ["python", "remote_mcp_server_admin.py", "--host", "0.0.0.0", "--port", "80"]
```

## What This Fixes

After setting `SERVER_BASE_URL=https://mcp.scikiq.com`, your admin dashboard will show:

**Before:**
```
OAuth Endpoint: http://localhost:30210/.well-known/oauth-authorization-server
```

**After:**
```
OAuth Endpoint: https://mcp.scikiq.com/.well-known/oauth-authorization-server
```

## Testing the Fix

1. **Deploy the updated code** to your production server
2. **Set the environment variable**: `SERVER_BASE_URL=https://mcp.scikiq.com`
3. **Restart your server**
4. **Check the admin dashboard** - OAuth Endpoint should now show the correct URL
5. **Test the authorization URL**:
   ```
   https://mcp.scikiq.com/authorize?response_type=code&client_id=mcp_client_KhloMk8PxhIXTrrVWgDNmQ&redirect_uri=https://claude.ai/api/mcp/auth_callback&code_challenge=test&code_challenge_method=S256
   ```

## Claude Desktop Configuration

Once this is fixed, configure Claude Desktop with:
- **Server URL**: `https://mcp.scikiq.com`
- **Client ID**: `mcp_client_KhloMk8PxhIXTrrVWgDNmQ` (from your dashboard)

## Still Need to Check

1. **Redirect URI**: Make sure your "claude" client has redirect URI set to `https://claude.ai/api/mcp/auth_callback`
2. **SSL Certificate**: Ensure your server has proper HTTPS/SSL configured
3. **Firewall**: Make sure ports 80/443 are accessible