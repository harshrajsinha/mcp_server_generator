# 🚀 Production Deployment Guide - Fix OAuth Database Error

## Current Issue
Your production server is showing: `"table authorization_codes has no column named state"`

This means your production database needs to be migrated to add the missing columns.

## 🔧 Solution Steps

### Step 1: Backup Your Production Database
```bash
# On your production server
cp mcp_auth.db mcp_auth.db.backup
```

### Step 2: Run Database Migration

**Option A: Upload and run the migration script**
1. Upload `migrate_database.py` to your production server
2. Run: `python migrate_database.py mcp_auth.db`

**Option B: Manual SQL migration (if you prefer)**
```sql
-- Connect to your database and run these commands:
ALTER TABLE authorization_codes ADD COLUMN state TEXT;
ALTER TABLE authorization_codes ADD COLUMN is_used BOOLEAN DEFAULT FALSE;
```

### Step 3: Deploy Updated Server Code
1. Upload the updated `remote_mcp_server_admin.py` file
2. Set the environment variable: `export SERVER_BASE_URL=https://mcp.scikiq.com`
3. Restart your server

### Step 4: Test the Fix

After deployment, test this URL:
```
https://mcp.scikiq.com/authorize?response_type=code&client_id=mcp_client_SXZetzG6fTVUpA-CwNt5PQ&redirect_uri=https://claude.ai/api/mcp/auth_callback&code_challenge=39-Y8jOqxhZMFeKXzLo8qztkIPDVQQWV1CCC_2fBAl&code_challenge_method=S256
```

**Expected result**: Should redirect to:
```
https://claude.ai/api/mcp/auth_callback?code=mcp_code_XXXXXX
```

## 🎯 Complete Deployment Commands

Here's the complete sequence for your production server:

```bash
# 1. Set environment variable (use the correct method for your system)
export SERVER_BASE_URL=https://mcp.scikiq.com

# 2. Backup database
cp mcp_auth.db mcp_auth.db.backup

# 3. Run migration (upload migrate_database.py first)
python migrate_database.py mcp_auth.db

# 4. Start server with updated code
python remote_mcp_server_admin.py --host 0.0.0.0 --port 80 --db-path mcp_auth.db
```

## ✅ Verification Checklist

After deployment, verify:

1. **Admin Dashboard**: OAuth Endpoint shows `https://mcp.scikiq.com/.well-known/oauth-authorization-server`
2. **Authorization URL**: Test the authorization endpoint (no more "Internal server error")
3. **Client Configuration**: Make sure "claude" client has redirect URI: `https://claude.ai/api/mcp/auth_callback`

## 🏆 Claude Desktop Configuration

Once everything works, configure Claude Desktop with:
- **Server URL**: `https://mcp.scikiq.com`
- **Client ID**: `mcp_client_SXZetzG6fTVUpA-CwNt5PQ` (from your dashboard)

## 🆘 Troubleshooting

**If migration fails:**
- Check database file permissions
- Ensure the database file exists and is accessible
- Check that no other process is using the database

**If authorization still fails:**
- Check server logs for specific error messages
- Verify the environment variable is set correctly
- Test the OAuth discovery endpoint: `https://mcp.scikiq.com/.well-known/oauth-authorization-server`