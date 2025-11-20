# SciKiq MCP Server - Admin User Management Setup Guide

## 🎯 Overview

This enhanced MCP server provides **admin user management** with the ability to create and manage multiple OAuth clients. Perfect for enterprise deployments where you need controlled access to database tools.

## 🏗️ Architecture

```
Admin User (you) 
    ↓ Creates & manages
OAuth Clients (Claude Desktop, Apps, etc.)
    ↓ Authenticate via OAuth 2.1
Protected Database Tools & APIs
```

## 🚀 Quick Setup

### Step 1: Create Admin User
```bash
# Create the first admin user
python remote_mcp_server_admin.py --create-admin admin:your_secure_password:admin@yourcompany.com

# Output:
# ✅ Admin user created: admin
# 🔗 Login at: http://localhost:3000/admin/login
```

### Step 2: Start the Server
```bash
# Start the server with admin management
python remote_mcp_server_admin.py --debug

# Output:
# 🚀 SciKiq MCP Server with Admin Management starting on http://localhost:3000
# 👤 Admin Panel: http://localhost:3000/admin/login
# 📡 OAuth: http://localhost:3000/.well-known/oauth-authorization-server
```

### Step 3: Access Admin Panel
1. Open: `http://localhost:3000/admin/login`
2. Login with your admin credentials
3. You'll see the **Admin Dashboard** with client management

## 🔧 Admin Dashboard Features

### Client Management
- **Create OAuth Clients**: For Claude Desktop, custom apps, etc.
- **View All Clients**: See client IDs, names, creation dates
- **Client Status**: Active/inactive clients
- **Redirect URIs**: Configure allowed callback URLs

### User Management (Future)
- **Add Users**: Create additional admin users
- **Role Management**: Admin, readonly, etc.
- **Access Logs**: Monitor authentication events

## 👥 Creating OAuth Clients

### Via Admin Dashboard (Recommended)
1. Login to admin panel: `http://localhost:3000/admin/login`
2. Click **"Create New Client"**
3. Fill in details:
   ```
   Client Name: Claude Desktop
   Redirect URIs: 
   http://localhost:8080/callback
   https://claude.ai/oauth/callback
   ```
4. Save and get your **Client ID**

### Via API (Programmatic)
```bash
curl -X POST http://localhost:3000/register \
  -H "Content-Type: application/json" \
  -d '{
    "client_name": "My App",
    "redirect_uris": ["http://localhost:3000/callback"]
  }'

# Response:
{
  "client_id": "mcp_client_abc123...",
  "client_name": "My App",
  "grant_types": ["authorization_code", "refresh_token"],
  "response_types": ["code"],
  "token_endpoint_auth_method": "none"
}
```

## 🔗 Claude Desktop Integration

### Step 1: Create Client for Claude
1. In admin dashboard, create new client:
   - **Name**: "Claude Desktop"
   - **Redirect URIs**: Use Claude's callback URL

### Step 2: Configure Claude Desktop
1. Open Claude Desktop Settings
2. Go to **Connectors**
3. Add new connector:
   ```
   Name: SciKiq DB Utils
   URL: http://localhost:3000
   Client ID: mcp_client_abc123...
   ```

### Step 3: OAuth Flow
1. Claude Desktop will redirect to authorization endpoint
2. User approves access (auto-approved in demo)
3. Claude gets access token
4. All API calls include `Authorization: Bearer <token>`

## 🗃️ Database Schema

The system uses SQLite with these tables:

### Users Table
```sql
- id (Primary Key)
- username (Unique)
- password_hash (PBKDF2 + Salt)
- role (admin, user)
- email
- created_at, last_login, is_active
```

### OAuth Clients Table  
```sql
- id (Primary Key)
- client_id (Unique)
- client_name
- redirect_uris (JSON)
- grant_types (JSON)
- created_by_user_id (Foreign Key)
- created_at, is_active
```

### Access Tokens Table
```sql
- id (Primary Key)  
- token (Unique)
- client_id
- user_id
- scope, expires_at
- created_at
```

## 🔐 Security Features

### Password Security
- **PBKDF2 hashing** with salt (100,000 iterations)
- **Secure session management** (8-hour admin sessions)
- **HttpOnly cookies** for admin sessions

### OAuth Security
- **PKCE required** for all authorization flows
- **Token expiration** (1 hour access, 30 day refresh)
- **Secure token storage** in database
- **Client validation** for all requests

### Network Security
- **CORS protection** with configurable origins
- **HTTPS support** (via reverse proxy)
- **Rate limiting** (can be added)

## 🛠️ Configuration Options

### Server Options
```bash
# Basic setup
python remote_mcp_server_admin.py --create-admin admin:pass123

# Custom configuration
python remote_mcp_server_admin.py \
  --host 0.0.0.0 \
  --port 8080 \
  --db-path /secure/mcp_auth.db \
  --config-path /etc/mcp/config.ini \
  --debug

# Production deployment
python remote_mcp_server_admin.py \
  --host 0.0.0.0 \
  --port 8080
```

### Environment Variables
```bash
# Database configuration
export CONFIG_PATH=/path/to/database/config.ini

# Database credentials
export MYSQL_PASSWORD=secure_password
export POSTGRES_PASSWORD=secure_password
```

## 📊 Monitoring & Management

### Admin Dashboard Metrics
- **Active Clients**: Number of registered OAuth clients
- **Token Usage**: Active access tokens
- **Database Tools**: Available database operations
- **Connection Status**: Database connectivity health

### Logs & Debugging
```bash
# Enable detailed logging
python remote_mcp_server_admin.py --debug

# Key log events:
# - Admin login attempts
# - OAuth client creation
# - Token generation/validation
# - Database tool execution
# - Connection errors
```

## 🚨 Troubleshooting

### Admin Login Issues
```bash
# Check if admin user exists
sqlite3 mcp_auth.db "SELECT * FROM users WHERE role='admin';"

# Reset admin password
python -c "
from remote_mcp_server_admin import DatabaseManager
db = DatabaseManager('mcp_auth.db')
# Manually update password in database
"
```

### Client Registration Issues
```bash
# Check client in database
sqlite3 mcp_auth.db "SELECT * FROM oauth_clients;"

# Verify redirect URIs format
# Ensure URIs are properly formatted JSON array
```

### OAuth Flow Issues
```bash
# Check token validation
sqlite3 mcp_auth.db "SELECT * FROM access_tokens WHERE expires_at > datetime('now');"

# Verify PKCE challenge/verifier
# Enable debug mode to see OAuth flow details
```

## 📈 Production Deployment

### Database Setup
```bash
# Use external database for production
# PostgreSQL recommended for high concurrency
export DATABASE_URL=postgresql://user:pass@host:5432/mcp_auth
```

### Security Hardening
```bash
# Use HTTPS (nginx + SSL)
# Restrict CORS origins  
# Enable rate limiting
# Use secure session storage
# Monitor access logs
```

### High Availability
```bash
# Load balancer + multiple instances
# Shared database for session/token storage
# Health checks on /health endpoint
# Graceful shutdown handling
```

## 🎉 Success!

You now have a **fully managed MCP server** with:

✅ **Admin user management** - Control who can create clients  
✅ **OAuth client management** - Easy client creation via web UI  
✅ **Secure authentication** - Industry-standard OAuth 2.1 + PKCE  
✅ **Database integration** - All your existing database tools  
✅ **Claude Desktop ready** - Perfect for enterprise AI integration  

**Ready for enterprise deployment with centralized access control!** 🚀

## 📞 Next Steps

1. **Create your admin user**: `--create-admin username:password:email`
2. **Start the server**: Access admin panel at `/admin/login` 
3. **Create OAuth clients**: For Claude Desktop and other apps
4. **Connect Claude**: Configure with your client ID
5. **Monitor usage**: Use admin dashboard for oversight

Your database tools are now securely accessible through a managed OAuth 2.1 system!