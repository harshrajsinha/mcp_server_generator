# 🎯 Final Production Deployment Guide - Single Database

## ✅ Database Standardization Complete

All scripts and guides now use **`mcp_auth.db`** as the single database file.

## 🚀 Production Deployment Steps

### Step 1: Prepare Your Production Server

```bash
# Set the environment variable for your domain
export SERVER_BASE_URL=https://mcp.scikiq.com

# If you have an old oauth_server.db, migrate the data:
# (Only if you had data in oauth_server.db that you want to keep)
```

### Step 2: Deploy Files

Upload these files to your production server:
- `remote_mcp_server_admin.py` (updated version)
- `migrate_database.py` (for database migration)
- `config.ini` (your database configuration)

### Step 3: Database Migration (if needed)

```bash
# If you have existing database with missing columns:
python migrate_database.py

# The script will automatically use mcp_auth.db
```

### Step 4: Start Production Server

```bash
# Standard deployment
python remote_mcp_server_admin.py --host 0.0.0.0 --port 80

# Or with custom database path (if needed)
python remote_mcp_server_admin.py --host 0.0.0.0 --port 80 --db-path mcp_auth.db
```

## 🔧 Migration from oauth_server.db (if applicable)

If you have existing data in `oauth_server.db` that you want to migrate to `mcp_auth.db`:

```bash
# 1. Create backup
cp oauth_server.db oauth_server_backup.db

# 2. Copy data to new database
sqlite3 oauth_server.db ".dump" | sqlite3 mcp_auth.db

# 3. Run migration to add missing columns
python migrate_database.py

# 4. Test the new database
python check_clients.py

# 5. Remove old database (after confirming everything works)
rm oauth_server.db
```

## ✅ Verification

After deployment, verify everything works:

1. **Admin Dashboard**: `https://mcp.scikiq.com/admin/dashboard`
   - OAuth Endpoint should show: `https://mcp.scikiq.com/.well-known/oauth-authorization-server`

2. **Test Authorization**: 
   ```
   https://mcp.scikiq.com/authorize?response_type=code&client_id=YOUR_CLIENT_ID&redirect_uri=https://claude.ai/api/mcp/auth_callback&code_challenge=test&code_challenge_method=S256
   ```

3. **Check Database**: 
   ```bash
   python check_clients.py
   ```

## 🎯 Claude Desktop Configuration

Once everything is working:

```json
{
  "mcpServers": {
    "scikiq-db": {
      "command": "npx",
      "args": ["-y", "@anthropic-ai/mcp-client-cli", "oauth"],
      "env": {
        "MCP_OAUTH_SERVER_URL": "https://mcp.scikiq.com",
        "MCP_OAUTH_CLIENT_ID": "YOUR_CLIENT_ID_FROM_DASHBOARD"
      }
    }
  }
}
```

## 📁 File Structure

Your production server should have:
```
/your-deployment-directory/
├── remote_mcp_server_admin.py    # Main server
├── mcp_auth.db                   # Single database file
├── config.ini                    # Database connections
├── migrate_database.py           # Migration script
└── check_clients.py              # Database verification
```

## 🆘 Troubleshooting

**Database Issues:**
```bash
# Check if database exists and has correct structure
python check_clients.py

# Run migration if needed
python migrate_database.py

# Check database file permissions
ls -la mcp_auth.db
```

**Authorization Issues:**
- Verify SERVER_BASE_URL environment variable is set
- Check that client redirect URI is exactly: `https://claude.ai/api/mcp/auth_callback`
- Test OAuth discovery endpoint: `https://mcp.scikiq.com/.well-known/oauth-authorization-server`

## 🎉 Success Indicators

✅ `python check_clients.py` shows your OAuth clients  
✅ Admin dashboard shows correct OAuth endpoint URL  
✅ Authorization URL redirects to Claude without errors  
✅ Claude Desktop can connect to your MCP server  

You're all set with a single, consistent database file!