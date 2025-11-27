# API/Swagger MCP Server - HTTP with OAuth Support

## Overview

API/Swagger MCP servers now support **both local (stdio) and online (HTTP with OAuth)** transports:

- **Local deployment**: Uses stdio transport for Claude Desktop integration (original behavior)
- **Online deployment**: Uses HTTP transport with OAuth 2.1 authentication for web access

This change enables API/Swagger servers to be deployed online with HTTPS/SSL support, just like Database MCP servers, while maintaining backward compatibility for local use.

---

## Architecture Changes

### Before (stdio only)
```
Local Only:
Claude Desktop → stdio (stdin/stdout) → MCP Server → Loads Tools → Exits
❌ No web access
❌ No HTTPS
❌ No remote access
```

### After (Dual Transport)
```
Local Deployment:
Claude Desktop → stdio (stdin/stdout) → MCP Server → Loads Tools → Exits
✅ Works as before

Online Deployment:
Browser/Client → HTTPS → Nginx → Port 30210 → FastAPI/OAuth → MCP Tools
✅ Web accessible
✅ HTTPS support
✅ OAuth 2.1 authentication
✅ Persistent HTTP service
```

---

## Implementation Details

### 1. New HTTP Loader (`mcp_server_loader_http.py`)

Created a new loader that supports both transports:

**Key Features:**
- Detects transport mode from environment: `MCP_TRANSPORT=stdio` or `MCP_TRANSPORT=http`
- Uses stdio for local (default): Compatible with Claude Desktop
- Uses FastAPI/Starlette for HTTP: Full OAuth 2.1 with PKCE support
- Same tool loading logic for both transports
- Automatic transport selection based on deployment context

**Transport Selection:**
```python
TRANSPORT_MODE = os.getenv("MCP_TRANSPORT", "stdio")  # Default to stdio
```

**HTTP Mode Features:**
- OAuth 2.0 Authorization Server Metadata (RFC 8414)
- Dynamic Client Registration (RFC 7591)
- Authorization Code Flow with PKCE
- Bearer token authentication
- CORS support for web clients
- Health check endpoint
- Persistent service (doesn't exit after loading)

### 2. Updated Deployment Logic (`online_deployment.py`)

**File Preparation:**
```python
if is_online_deployment:
    # Copy HTTP loader with OAuth support
    server_files['mcp_server_loader.py'] = http_loader_content
else:
    # Copy stdio loader (original)
    server_files['mcp_server_loader.py'] = stdio_loader_content
```

**Requirements:**
```python
if is_online_deployment:
    # Include FastAPI/Starlette for HTTP
    requirements = "mcp\nhttpx\npyyaml\nstarlette\nuvicorn\n"
else:
    # Minimal for stdio
    requirements = "mcp\nhttpx\npyyaml\n"
```

**Startup Command:**
```python
# Online: Add --http flag for HTTP mode
startup_command = f"/opt/mcp-server/venv/bin/python /opt/mcp-server/mcp_server_loader.py {yaml_args} --http"
```

### 3. Updated Deployment Template (`ec2_setup_script.sh`)

**Nginx Configuration:**
- Now configured for **all** online deployments (database, api, swagger)
- Previously only database servers had Nginx
- API/Swagger servers now get Nginx reverse proxy on port 80/443 → 30210

**SSL Certificates:**
- Let's Encrypt SSL now configured for API/Swagger servers with domains
- Same security headers and SSL settings as database servers

**Systemd Service:**
```ini
[Service]
Type=simple                    # Persistent service (not oneshot)
Environment="MCP_TRANSPORT=http"
Environment="MCP_PORT=30210"
Environment="MCP_HOST=0.0.0.0"
Environment="SERVER_BASE_URL=https://domain.com"
Restart=always                 # Auto-restart on failure
```

**Import Tests:**
```bash
# API/Swagger servers now test HTTP dependencies
python3 -c "import mcp,httpx,yaml,starlette,uvicorn"
```

**Status Messages:**
```
✓ MCP api Server started successfully!
Server is available at:
  - https://domain.com (HTTPS)
  - http://domain.com (HTTP - redirects to HTTPS)
  - http://1.2.3.4:30210 (Direct access)

OAuth Metadata: https://domain.com/.well-known/oauth-authorization-server
Health Check: https://domain.com/health
```

---

## OAuth 2.1 Endpoints

### Authorization Server Metadata
```
GET /.well-known/oauth-authorization-server
```
Returns OAuth server configuration (RFC 8414)

### Dynamic Client Registration
```
POST /oauth/register
Content-Type: application/json

{
  "client_name": "My MCP Client"
}

Response:
{
  "client_id": "mcp_client_xyz...",
  "client_name": "My MCP Client",
  "grant_types": ["authorization_code", "refresh_token"],
  "token_endpoint_auth_method": "none"
}
```

### Authorization Endpoint
```
GET /oauth/authorize?client_id=...&redirect_uri=...&response_type=code&code_challenge=...&code_challenge_method=S256&state=...
```
Returns authorization code

### Token Endpoint
```
POST /oauth/token
Content-Type: application/x-www-form-urlencoded

grant_type=authorization_code&code=...&redirect_uri=...&client_id=...&code_verifier=...

Response:
{
  "access_token": "mcp_access_...",
  "refresh_token": "mcp_refresh_...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

### MCP Tool Endpoints
```
GET /mcp/tools
Authorization: Bearer <access_token>

POST /mcp/call
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "name": "tool_name",
  "arguments": {...}
}
```

### Health Check
```
GET /health

Response:
{
  "status": "healthy",
  "server": "scikiq-mcp-autoAPI",
  "version": "2.0.0",
  "transport": "http",
  "tools_loaded": 10
}
```

---

## Usage Examples

### Local Deployment (stdio)

**1. Deploy locally:**
```bash
python mcp_server_loader.py tools_myapi_20251125.yaml
```

**2. Configure in Claude Desktop:**
```json
{
  "mcpServers": {
    "my-api": {
      "command": "python",
      "args": [
        "/path/to/mcp_server_loader.py",
        "/path/to/tools_myapi.yaml"
      ]
    }
  }
}
```

**Behavior:**
- Uses stdio transport
- Loads tools and stays running
- No HTTP server
- No OAuth
- Local access only

### Online Deployment (HTTP with OAuth)

**1. Deploy to AWS:**
```python
deployer.deploy_to_aws_ec2(
    server_type='swagger',
    server_path='/path/to/generated_servers',
    yaml_file='tools_myapi_20251125.yaml',
    domain='api.example.com',
    # ... other parameters
)
```

**2. Access via HTTPS:**
```bash
# Check OAuth configuration
curl https://api.example.com/.well-known/oauth-authorization-server

# Check health
curl https://api.example.com/health

# Register OAuth client
curl -X POST https://api.example.com/oauth/register \
  -H "Content-Type: application/json" \
  -d '{"client_name": "My Client"}'

# Use OAuth flow to get access token
# ... (authorization code flow with PKCE)

# Call MCP tools
curl https://api.example.com/mcp/tools \
  -H "Authorization: Bearer <access_token>"

curl -X POST https://api.example.com/mcp/call \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "get_quote", "arguments": {"symbol": "AAPL"}}'
```

**Behavior:**
- Uses HTTP transport with OAuth
- Runs as persistent HTTP service
- Nginx reverse proxy
- SSL/TLS encryption
- OAuth 2.1 authentication
- Web accessible
- Auto-restarts on failure

---

## Environment Variables

### HTTP Mode Configuration
```bash
MCP_TRANSPORT=http          # Enable HTTP transport (default: stdio)
MCP_HOST=0.0.0.0           # Listen address (default: 0.0.0.0)
MCP_PORT=30210             # Listen port (default: 30210)
SERVER_BASE_URL=https://domain.com  # Base URL for OAuth redirects
```

### Automatic Detection
The loader automatically uses HTTP mode when `--http` flag is present:
```bash
python mcp_server_loader.py tools.yaml --http
```

---

## Security Features

### OAuth 2.1 with PKCE
- Public client support (no client secret required)
- PKCE (Proof Key for Code Exchange) prevents authorization code interception
- SHA-256 code challenge method

### Token Management
- Access tokens expire after 1 hour
- Refresh tokens for obtaining new access tokens
- In-memory token store (production should use database)

### HTTPS/SSL
- Automatic SSL certificate via Let's Encrypt
- HTTP to HTTPS redirect
- Security headers (HSTS, X-Frame-Options, etc.)
- Modern SSL protocols and ciphers

### CORS
- Configurable CORS origins
- Supports web-based MCP clients
- Credentials support for OAuth

---

## Comparison: Database vs API/Swagger Servers

### Database MCP Server
- **Purpose**: Database operations (query, execute, manage connections)
- **Transport**: Always HTTP (no stdio option)
- **Admin UI**: Full OAuth admin interface at `/admin/login`
- **User Management**: Multi-user support with admin/user roles
- **Authentication**: OAuth with admin-created users
- **Database**: SQLite for user/client storage

### API/Swagger MCP Server
- **Purpose**: Expose REST APIs as MCP tools
- **Transport**: Dual (stdio for local, HTTP for online)
- **Admin UI**: None (OAuth only)
- **User Management**: None (auto-approve authorization)
- **Authentication**: OAuth with automatic client registration
- **Database**: In-memory token store (no persistence)

### Key Differences
| Feature | Database Server | API/Swagger Server |
|---------|----------------|-------------------|
| Local Use | ❌ No | ✅ Yes (stdio) |
| Online Use | ✅ Yes (HTTP) | ✅ Yes (HTTP) |
| Admin Interface | ✅ Full UI | ❌ OAuth only |
| User Management | ✅ Admin creates users | ❌ Auto-registration |
| Persistent Storage | ✅ SQLite | ❌ In-memory |
| Tool Source | Database operations | YAML tool definitions |
| Configuration | config.ini | YAML files |

---

## Backward Compatibility

### Existing Local Deployments
- ✅ Continue to work unchanged
- ✅ No breaking changes to stdio transport
- ✅ Claude Desktop configuration remains the same
- ✅ Original `mcp_server_loader.py` still works

### Migration Path
1. **No action needed** for local deployments
2. **Redeploy** existing online API servers to enable HTTP/OAuth
3. **Update configuration** to use HTTPS URLs instead of explaining "no web access"

---

## Testing

### Test HTTP Transport Locally
```bash
# Start server in HTTP mode
MCP_TRANSPORT=http MCP_PORT=30210 python mcp_server_loader.py tools.yaml --http

# In another terminal
curl http://localhost:30210/health
curl http://localhost:30210/.well-known/oauth-authorization-server
```

### Test stdio Transport
```bash
# Start server in stdio mode (default)
python mcp_server_loader.py tools.yaml

# Server will read from stdin and write to stdout
# Use with Claude Desktop or MCP client
```

---

## Deployment Checklist

### Online API/Swagger Deployment
- ✅ EC2 instance created
- ✅ Security group allows ports 80, 443, 22
- ✅ Domain DNS pointing to instance IP
- ✅ Nginx installed and configured
- ✅ SSL certificate obtained (Let's Encrypt)
- ✅ MCP server installed with HTTP loader
- ✅ systemd service running (Type=simple, persistent)
- ✅ Environment variables set (MCP_TRANSPORT=http, etc.)
- ✅ OAuth endpoints accessible
- ✅ Health check returns 200 OK
- ✅ Can register OAuth client
- ✅ Can complete OAuth flow
- ✅ Can call MCP tools with access token

---

## Troubleshooting

### Server won't start
```bash
# Check systemd service
sudo systemctl status mcp-server

# Check logs
sudo journalctl -u mcp-server -n 50

# Check if port is listening
sudo ss -tlnp | grep 30210
```

### OAuth not working
```bash
# Verify OAuth metadata
curl http://localhost:30210/.well-known/oauth-authorization-server

# Check environment variables
sudo cat /etc/systemd/system/mcp-server.service | grep Environment
```

### Nginx errors
```bash
# Test Nginx config
sudo nginx -t

# Check Nginx logs
sudo tail -f /var/log/nginx/error.log

# Verify proxy pass
curl -v http://localhost/health
```

### SSL certificate issues
```bash
# Check certificate
sudo certbot certificates

# Renew certificate
sudo certbot renew

# Check Nginx SSL config
sudo cat /etc/nginx/sites-enabled/mcp-server
```

---

## Future Enhancements

### Possible Improvements
1. **Persistent Token Storage**: Use database instead of in-memory
2. **Admin Interface**: Add web UI for OAuth client management
3. **User Management**: Optional user authentication layer
4. **Rate Limiting**: Protect against abuse
5. **Metrics/Monitoring**: Prometheus/Grafana integration
6. **Multi-Tenancy**: Support multiple isolated tool sets
7. **Webhook Support**: Push notifications for tool events
8. **GraphQL Support**: Alternative to REST APIs

---

## Summary

This implementation provides the best of both worlds:

✅ **Local Development**: Fast, simple stdio transport for Claude Desktop
✅ **Online Production**: Secure HTTP/OAuth transport with HTTPS
✅ **Unified Codebase**: Same loader supports both transports
✅ **No Breaking Changes**: Existing local deployments continue to work
✅ **Production Ready**: Full OAuth 2.1, SSL, systemd service
✅ **Easy Migration**: Single flag enables HTTP mode

The API/Swagger MCP servers now have feature parity with Database MCP servers for online deployments, while maintaining their simpler local deployment model.
