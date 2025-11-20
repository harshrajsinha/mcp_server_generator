# Claude Desktop Authorization Debugging

## Your Production Setup
- **Server URL**: https://mcp.scikiq.com
- **Admin Panel**: ✅ Working (screenshot confirms)
- **OAuth Clients**: ✅ 2 clients created

## Common Issues & Solutions

### 1. Port Configuration
**Issue**: Claude might be trying to access port 30210 but your server is running on a different port.

**Check**: 
- What port is your production server actually running on?
- In the screenshot, I see the OAuth Endpoint shows `localhost:30210` - this needs to be updated for production

### 2. Redirect URI Configuration
**Required for Claude Desktop**: `https://claude.ai/api/mcp/auth_callback`

**To Check**:
1. Click "Edit" on the "claude" client
2. Verify the Redirect URI is exactly: `https://claude.ai/api/mcp/auth_callback`

### 3. HTTPS/SSL Configuration
**Issue**: Claude Desktop requires HTTPS for OAuth

**Check**:
- Is your server properly configured with SSL certificates?
- Test: https://mcp.scikiq.com/.well-known/oauth-authorization-server

### 4. Server Configuration
**Claude's Expected URL Format**:
```
https://mcp.scikiq.com/authorize
https://mcp.scikiq.com/token
```

**Not**:
```
https://mcp.scikiq.com:30210/authorize  (with port)
```

## Testing Steps

### Step 1: Test Authorization Endpoint
Try this URL in your browser (replace CLIENT_ID with actual client ID):
```
https://mcp.scikiq.com/authorize?response_type=code&client_id=mcp_client_KhloMk8PxhIXTrrVWgDNmQ&redirect_uri=https://claude.ai/api/mcp/auth_callback&code_challenge=dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk&code_challenge_method=S256
```

### Step 2: Check OAuth Discovery
Visit: https://mcp.scikiq.com/.well-known/oauth-authorization-server

Should return JSON with:
```json
{
  "authorization_endpoint": "https://mcp.scikiq.com/authorize",
  "token_endpoint": "https://mcp.scikiq.com/token",
  "response_types_supported": ["code"],
  "grant_types_supported": ["authorization_code"],
  "code_challenge_methods_supported": ["S256", "plain"]
}
```

### Step 3: Claude Desktop Configuration
In Claude Desktop settings, the server URL should be:
```
https://mcp.scikiq.com
```

**NOT**:
```
https://mcp.scikiq.com:30210
```

## Quick Fixes

### Fix 1: Update Client Redirect URI
1. Go to Admin Panel → OAuth Clients
2. Click "Edit" on the "claude" client  
3. Set Redirect URI to: `https://claude.ai/api/mcp/auth_callback`
4. Save changes

### Fix 2: Check Server Port Configuration
Your production server should be running on port 80 (HTTP) or 443 (HTTPS), not 30210.

If you're using a reverse proxy (nginx/apache), make sure it's configured to forward to your Python server.

### Fix 3: Update OAuth Discovery Endpoint
The OAuth endpoint in your admin panel shows `localhost:30210` - this needs to be updated to your production domain.