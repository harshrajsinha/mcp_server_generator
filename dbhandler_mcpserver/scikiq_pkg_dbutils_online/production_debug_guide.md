# Production Debug Guide

## Step 1: Check Your Client Configuration

1. Go to: https://mcp.scikiq.com/admin/dashboard
2. Click **"Edit"** on the **"claude"** client
3. Check the **Redirect URI** field
4. It MUST be exactly: `https://claude.ai/api/mcp/auth_callback`

## Step 2: Test Authorization Endpoint Directly

Try this URL in your browser (replace CLIENT_ID with your actual client ID):

```
https://mcp.scikiq.com/authorize?response_type=code&client_id=mcp_client_KhloMk8PxhIXTrrVWgDNmQ&redirect_uri=https://claude.ai/api/mcp/auth_callback&code_challenge=dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk&code_challenge_method=S256
```

**Expected Results:**
- ✅ **Success**: Should redirect to `https://claude.ai/api/mcp/auth_callback?code=mcp_code_XXXXX`
- ❌ **Invalid Client**: `{"error":"invalid_client","error_description":"Invalid client_id"}`
- ❌ **Invalid Redirect**: `{"error":"invalid_request","error_description":"Invalid redirect_uri"}`

## Step 3: Common Issues & Fixes

### Issue 1: Wrong Redirect URI
**Problem**: Client redirect URI is not set to Claude's callback URL
**Solution**: 
1. Edit the client
2. Set Redirect URI to: `https://claude.ai/api/mcp/auth_callback`
3. Save

### Issue 2: Client Not Found
**Problem**: The client ID in the URL doesn't match your database
**Solution**: Use the correct client ID from your admin dashboard

### Issue 3: Server Not Running
**Problem**: Your production server stopped or crashed
**Solution**: Check server logs and restart

## Step 4: Update Production Server (if needed)

If you need to update your production server with the improved error logging, deploy the updated `remote_mcp_server_admin.py` file.

## Step 5: Configure Claude Desktop

Once authorization works, configure Claude Desktop with:

**Server URL**: `https://mcp.scikiq.com`
**Client ID**: `mcp_client_KhloMk8PxhIXTrrVWgDNmQ` (or your actual client ID)

## Quick Test Command

You can also test with curl:

```bash
curl -v "https://mcp.scikiq.com/authorize?response_type=code&client_id=mcp_client_KhloMk8PxhIXTrrVWgDNmQ&redirect_uri=https://claude.ai/api/mcp/auth_callback&code_challenge=test&code_challenge_method=S256"
```

This should return either a redirect (302) or an error message that tells us what's wrong.