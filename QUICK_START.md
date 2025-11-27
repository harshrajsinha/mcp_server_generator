# 🚀 Quick Start Guide - New Features

## For Users

### Using OAuth with Swagger MCP
1. Click **"From Swagger/OpenAPI"**
2. Enter your Swagger URL
3. ✅ Check **"Enable OAuth Server"**
4. Select OAuth provider (GitHub, Google, Custom)
5. Fill in OAuth credentials
6. Click **"Import from Swagger"**
7. Deploy locally or online

### Using OAuth with Codebase MCP
1. Click **"From RestAPI Code"**
2. Choose Local Folder or GitHub Repository
3. ✅ Check **"Enable OAuth Server"**
4. Configure OAuth settings
5. Click **"Scan from Codebase"**
6. Deploy locally or online

### Scanning GitHub Repository
1. Click **"From RestAPI Code"**
2. Select **"GitHub Repository"**
3. Enter repository URL: `https://github.com/owner/repo`
4. Enter branch: `main` or `develop`
5. (Optional) Enter personal access token for private repos
6. Click **"Scan from Codebase"**

### Local Deployment
1. Generate MCP server (any option)
2. Click **"Setup MCP Server"**
3. Click **"Local 💻"** card
4. Wait for success message
5. Restart Claude Desktop
6. MCP server now available!

### Online Deployment
1. Generate MCP server (any option)
2. Click **"Setup MCP Server"**
3. Click **"Online ☁️"** card
4. Choose:
   - **AWS EC2**: Enter AWS credentials
   - **Azure VM**: Enter Azure credentials
   - **Remote SSH**: Enter server details
5. Monitor deployment progress
6. Save connection details

## For Developers

### New Backend Endpoints

#### POST /api/deploy-mcp-local
```javascript
fetch('/api/deploy-mcp-local', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    server_path: "/path/to/mcp_server.py",
    server_name: "my-mcp-server",
    config: {}
  })
})
```

#### POST /api/scan-github-repo
```javascript
fetch('/api/scan-github-repo', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    github_repo_url: "https://github.com/owner/repo",
    github_branch: "main",
    github_token: "ghp_...", // optional
    source_file: "app.py"
  })
})
```

### OAuth Configuration Object
```javascript
{
  enable_oauth: true,
  oauth_config: {
    provider: "github",
    client_id: "your_client_id",
    client_secret: "your_client_secret",
    auth_url: "https://github.com/login/oauth/authorize",
    token_url: "https://github.com/login/oauth/access_token",
    user_info_url: "https://api.github.com/user",
    redirect_uri: "http://localhost:8080/auth/callback"
  }
}
```

### Testing
```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
python test_new_endpoints.py

# Start server
python app.py
```

## Configuration Examples

### GitHub OAuth Provider
```javascript
{
  provider: "github",
  client_id: "Iv1.1234567890abcdef",
  client_secret: "1234567890abcdef1234567890abcdef12345678",
  auth_url: "https://github.com/login/oauth/authorize",
  token_url: "https://github.com/login/oauth/access_token",
  user_info_url: "https://api.github.com/user",
  redirect_uri: "http://localhost:8080/auth/callback"
}
```

### Google OAuth Provider
```javascript
{
  provider: "google",
  client_id: "123456789012-abcdefghijklmnopqrstuvwxyz123456.apps.googleusercontent.com",
  client_secret: "GOCSPX-1234567890abcdefghij",
  auth_url: "https://accounts.google.com/o/oauth2/v2/auth",
  token_url: "https://oauth2.googleapis.com/token",
  user_info_url: "https://www.googleapis.com/oauth2/v2/userinfo",
  redirect_uri: "http://localhost:8080/auth/callback"
}
```

### Custom OAuth Provider
```javascript
{
  provider: "custom",
  client_id: "your_client_id",
  client_secret: "your_client_secret",
  auth_url: "https://your-auth-server.com/oauth/authorize",
  token_url: "https://your-auth-server.com/oauth/token",
  user_info_url: "https://your-auth-server.com/oauth/userinfo",
  redirect_uri: "http://localhost:8080/auth/callback"
}
```

## Troubleshooting

### "GitPython not installed"
```bash
pip install GitPython==3.1.40
```

### "GitHub authentication failed"
1. Generate personal access token
2. Go to GitHub Settings → Developer settings → Personal access tokens
3. Generate new token with `repo` scope
4. Copy token and paste in UI

### "Port 8080 already in use"
- Stop other services using port 8080
- Or modify OAuth server port in generated code

### "Claude Desktop config not found"
- Ensure Claude Desktop is installed
- Check paths:
  - Windows: `%AppData%\Claude\claude_desktop_config.json`
  - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
  - Linux: `~/.config/Claude/claude_desktop_config.json`

## Documentation

- **IMPLEMENTATION_SUMMARY.md** - Complete feature overview
- **VISUAL_GUIDE.md** - UI flows and diagrams
- **BACKEND_API_REQUIREMENTS.md** - API specifications
- **BACKEND_IMPLEMENTATION_STATUS.md** - Implementation details
- **COMPLETE_IMPLEMENTATION_SUMMARY.md** - High-level summary

## Feature Comparison

| Feature | Swagger MCP | Codebase MCP | Database MCP |
|---------|-------------|--------------|--------------|
| OAuth Support | ✅ | ✅ | ✅ |
| Local Deployment | ✅ | ✅ | ✅ |
| AWS Deployment | ✅ | ✅ | ✅ |
| Azure Deployment | ✅ | ✅ | ✅ |
| Remote SSH Deployment | ✅ | ✅ | ✅ |
| GitHub Support | ❌ | ✅ | ❌ |

## Quick Commands

```bash
# Start Flask server
python app.py

# Run tests
python test_new_endpoints.py

# Install dependencies
pip install -r requirements.txt

# Check Claude Desktop config
cat "%AppData%\Claude\claude_desktop_config.json"  # Windows
cat ~/Library/Application\ Support/Claude/claude_desktop_config.json  # macOS
```

---

**Need Help?** Check the full documentation files or the troubleshooting section above.
