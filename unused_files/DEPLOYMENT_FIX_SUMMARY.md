# Deployment Fix Summary - API/Swagger vs Database MCP Servers

## Problem Identified

API/Swagger MCP servers were being deployed with the same configuration as Database MCP servers, causing:
1. **502 Bad Gateway errors** - Nginx proxying to port 30210, but stdio servers don't listen on HTTP ports
2. **Infinite restart loops** - systemd Type=simple with Restart=always, causing restart counter to reach 90+
3. **Architecture mismatch** - stdio transport servers don't need web/HTTP access

## Root Cause

MCP servers have two distinct architectures:

### Database MCP Servers
- **Transport**: HTTP (FastAPI/Uvicorn)
- **Port**: 30210
- **Interface**: OAuth-based web admin
- **Access**: Via browser through Nginx reverse proxy
- **Lifecycle**: Persistent daemon (always running)
- **SSL**: Required for production (Let's Encrypt)

### API/Swagger MCP Servers
- **Transport**: stdio (stdin/stdout)
- **Port**: None (no network listening)
- **Interface**: Claude Desktop only
- **Access**: Not web-accessible
- **Lifecycle**: Loads tools and exits (oneshot)
- **SSL**: Not applicable

## Changes Made to `ec2_setup_script.sh`

### 1. Conditional Nginx Configuration (Lines 164-255)

**Before**: Nginx always configured for all server types

**After**: Nginx only configured for database servers
```bash
if [ "{{SERVER_TYPE}}" = "database" ]; then
    echo "Configuring Nginx for database MCP server..."
    # ... nginx configuration ...
else
    echo "Skipping Nginx configuration (API/Swagger servers use stdio transport)"
fi
```

### 2. Conditional SSL Setup (Lines 270-580)

**Before**: SSL certificate always attempted via Let's Encrypt

**After**: SSL only for database servers with domains
```bash
if [ "{{SERVER_TYPE}}" = "database" ]; then
    # ... nginx and SSL configuration ...
    if [ -n "$DOMAIN" ]; then
        # ... Let's Encrypt certbot ...
    fi
else
    echo "Skipping Nginx and SSL setup for {{SERVER_TYPE}} server (uses stdio transport)"
fi
```

### 3. Different systemd Service Configurations (Lines 604-650)

**Before**: All servers used `Type=simple` with `Restart=always`

**After**: Different configurations based on server type

#### Database Servers (Type=simple)
```ini
[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/mcp-server
Environment="PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/opt/mcp-server/venv/bin"
Environment="SERVER_BASE_URL=$SERVER_BASE_URL"
ExecStart={{STARTUP_COMMAND}}
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
```

#### API/Swagger Servers (Type=oneshot)
```ini
[Service]
Type=oneshot
User=ubuntu
WorkingDirectory=/opt/mcp-server
Environment="PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/opt/mcp-server/venv/bin"
ExecStart={{STARTUP_COMMAND}}
RemainAfterExit=yes
StandardOutput=journal
StandardError=journal
```

**Key Differences**:
- `Type=oneshot` - Service expected to exit after completing its task
- `RemainAfterExit=yes` - Service considered active after exit
- No `Restart` directive - Service doesn't restart automatically

### 4. Different Status Messages (Lines 720-755)

**Before**: All servers showed HTTP/Nginx URLs

**After**: Different messages for different server types

#### Database Servers
```
✓ MCP Database Server started successfully!
Server is available at:
  - https://domain.com (HTTPS)
  - http://domain.com (HTTP - redirects to HTTPS)
  - http://1.2.3.4:30210 (Direct access)
```

#### API/Swagger Servers
```
✓ MCP Server initialized successfully!

This server uses stdio transport for Claude Desktop.
The service loaded the tools and exited (this is expected behavior).

To verify initialization, check the logs:
  sudo journalctl -u mcp-server -n 50 --no-pager

You should see: 'Successfully loaded X/X tools from ...'
```

## Expected Behavior After Fix

### Database MCP Server Deployment
1. ✅ Nginx installed and configured
2. ✅ SSL certificate obtained via Let's Encrypt
3. ✅ systemd service runs continuously (Type=simple)
4. ✅ Admin interface accessible at https://domain.com/admin/login
5. ✅ OAuth flow works through web interface

### API/Swagger MCP Server Deployment
1. ✅ Nginx installation skipped
2. ✅ SSL certificate not attempted
3. ✅ systemd service loads tools and exits (Type=oneshot)
4. ✅ No HTTP interface (not accessible via browser)
5. ✅ Logs show "Successfully loaded X/X tools"
6. ✅ No infinite restart loops
7. ✅ Service status shows as "active (exited)" - this is correct

## Testing Verification

To verify the fix works correctly:

### For API/Swagger Server
```bash
# Check service status (should show "active (exited)")
sudo systemctl status mcp-server

# Check logs (should show successful tool loading)
sudo journalctl -u mcp-server -n 50 --no-pager

# Verify no Nginx config exists
ls -l /etc/nginx/sites-enabled/mcp-server  # Should not exist

# Verify no ports listening
sudo ss -tlnp | grep 30210  # Should return empty
```

### For Database Server
```bash
# Check service status (should show "active (running)")
sudo systemctl status mcp-server

# Check Nginx (should be running)
sudo systemctl status nginx

# Check ports (should see 80, 443, 30210)
sudo ss -tlnp | grep -E '(80|443|30210)'

# Access admin interface
curl -k https://domain.com/admin/login
```

## Files Modified

1. **templates/ec2_setup_script.sh**
   - Added conditional Nginx configuration
   - Added conditional SSL setup
   - Created separate systemd service configurations
   - Updated status check messages

## Related Changes

Previous fixes that support this change:
1. ✅ Unique server naming based on API domain
2. ✅ YAML file specific deployment
3. ✅ Conditional import testing
4. ✅ Enhanced logging for diagnostics

## Next Steps

1. Test deployment of new API/Swagger server
2. Verify no 502 errors occur
3. Confirm service exits cleanly after loading tools
4. Check logs show proper initialization messages
5. Optional: Test with Claude Desktop to confirm stdio transport works

## Technical Notes

- **stdio transport**: MCP protocol over standard input/output, used for local/IDE integration
- **HTTP transport**: MCP protocol over HTTP, used for remote/web access
- **Type=oneshot**: systemd service type for tasks that run once and exit
- **RemainAfterExit**: Keeps service marked as "active" even after exit
- This fix aligns with Anthropic's MCP specification for stdio-based servers
