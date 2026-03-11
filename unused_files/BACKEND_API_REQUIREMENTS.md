# Backend API Requirements for MCP Server Enhancements

## Overview
This document outlines the backend API endpoints that need to be implemented or updated to support the new frontend features for Swagger and Codebase-based MCP servers.

---

## 1. Local Deployment Endpoint

### `POST /api/deploy-mcp-local`

**Purpose**: Deploy MCP server to local Claude Desktop configuration

**Request Body**:
```json
{
  "server_path": "/path/to/mcp_server_high_confidence.py",
  "server_name": "scikiq-mcp-autoAPI",
  "config": {
    // Either SwaggerConfig or ProjectConfig
    "swagger_url": "https://api.example.com/swagger.json",
    "api_base_url": "https://api.example.com",
    "enable_oauth": true,
    "oauth_client_name": "claude-desktop",
    "oauth_redirect_uris": "http://localhost:3000/callback",
    // OR for codebase
    "source_type": "github",
    "github_repo_url": "https://github.com/owner/repo",
    "project_path": "/local/path",
    "api_base_url": "http://localhost:9321"
  }
}
```

**Response**:
```json
{
  "success": true,
  "message": "MCP Server deployed locally",
  "config_path": "/Users/user/Library/Application Support/Claude/claude_desktop_config.json",
  "backup_path": "/Users/user/Library/Application Support/Claude/claude_desktop_config.backup.20251125_120000.json"
}
```

**Implementation Notes**:
- Reuse logic from `deploy_database_mcp_to_claude()` in mcp_routes.py
- Detect Python executable
- Update Claude Desktop config file
- Create backup before modifying
- Handle Windows/Mac/Linux paths correctly

---

## 2. GitHub Repository Scanning Endpoint

### `POST /api/scan-github-repo`

**Purpose**: Clone and scan a GitHub repository for API endpoints

**Request Body**:
```json
{
  "github_repo_url": "https://github.com/owner/repo",
  "github_branch": "main",
  "github_token": "ghp_xxxxxxxxxxxx",  // Optional, for private repos
  "source_file": "app.py",             // Optional
  "api_base_url": "http://localhost:9321"
}
```

**Response**:
```json
{
  "success": true,
  "api_definitions": [
    {
      "route": "/api/users",
      "methods": ["GET", "POST"],
      "function_name": "get_users",
      "file": "/tmp/repo-clone/app.py",
      "file_name": "app.py",
      "line_number": 45,
      "docstring": "Get all users",
      "parameters": [...],
      "confidence": 0.95,
      "business_domain": "user_management"
    }
  ],
  "file_tree": {...},
  "intelligence": {
    "project_type": "Flask API",
    "frameworks": ["Flask"],
    "total_endpoints": 15
  }
}
```

**Implementation Steps**:
1. Clone GitHub repo to temporary directory using `git clone`
2. If `github_token` provided, use it for authentication
3. Checkout specified branch
4. Run existing code scanning logic on cloned repo
5. Clean up temporary directory after scan
6. Return same structure as `/api/scan-project`

**Implementation Example**:
```python
import git
import tempfile
import shutil

@app.route('/api/scan-github-repo', methods=['POST'])
def scan_github_repo():
    data = request.get_json()
    repo_url = data.get('github_repo_url')
    branch = data.get('github_branch', 'main')
    token = data.get('github_token')
    
    # Create temporary directory
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Prepare clone URL with token if provided
        if token:
            # Format: https://token@github.com/owner/repo.git
            clone_url = repo_url.replace('https://', f'https://{token}@')
        else:
            clone_url = repo_url
            
        # Clone repository
        repo = git.Repo.clone_from(clone_url, temp_dir, branch=branch)
        
        # Scan the cloned repository using existing scan logic
        result = scan_project_directory(temp_dir, data.get('source_file'))
        
        return jsonify({
            'success': True,
            'api_definitions': result['api_definitions'],
            'file_tree': result['file_tree'],
            'intelligence': result['intelligence']
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
        
    finally:
        # Clean up temporary directory
        shutil.rmtree(temp_dir, ignore_errors=True)
```

**Dependencies Needed**:
```bash
pip install GitPython
```

---

## 3. Update Online Deployment Endpoints

### Existing Endpoints to Update:
- `POST /api/deploy-aws`
- `POST /api/deploy-azure`
- `POST /api/deploy-remote`

**Changes Needed**:
1. Accept Swagger/Codebase configs in addition to database configs
2. Generate appropriate MCP server files based on source type
3. Include OAuth server setup if enabled

**Updated Request Body** (for all three):
```json
{
  "deployment_type": "swagger" | "codebase" | "database",
  "server_name": "my-mcp-server",
  "server_port": 30210,
  "domain": "api.example.com",  // Optional
  
  // For swagger/codebase
  "server_file_path": "/path/to/mcp_server_high_confidence.py",
  "enable_oauth": true,
  "oauth_client_name": "claude-desktop",
  "oauth_redirect_uris": "http://localhost:3000/callback",
  
  // For AWS
  "aws_region": "ap-south-1",
  "aws_access_key": "...",
  "aws_secret_key": "...",
  "instance_type": "t2.micro",
  
  // For Azure
  "azure_subscription_id": "...",
  "azure_tenant_id": "...",
  "azure_client_id": "...",
  "azure_client_secret": "...",
  
  // For Remote
  "ssh_host": "192.168.1.100",
  "ssh_user": "ubuntu",
  "ssh_password": "...",
  "ssh_key_path": "..."
}
```

**Implementation Logic**:
```python
@app.route('/api/deploy-aws', methods=['POST'])
def deploy_aws():
    data = request.get_json()
    deployment_type = data.get('deployment_type', 'database')
    
    if deployment_type == 'database':
        # Existing database deployment logic
        pass
    elif deployment_type in ['swagger', 'codebase']:
        # New logic for API-based MCP servers
        server_file_path = data.get('server_file_path')
        enable_oauth = data.get('enable_oauth', False)
        
        # Package server files
        files_to_deploy = [server_file_path]
        
        if enable_oauth:
            # Include OAuth server files
            files_to_deploy.extend([
                'oauth_server.py',
                'oauth_database.db',
                'requirements_oauth.txt'
            ])
        
        # Deploy to AWS EC2
        deployer = OnlineDeployer()
        result = deployer.deploy_to_aws(
            files=files_to_deploy,
            region=data.get('aws_region'),
            credentials={...},
            config=data
        )
        
        return jsonify(result)
```

---

## 4. MCP Server Generation Updates

### Update `generate_mcp_server_code()` Function

**Location**: `mcp_routes.py`

**Changes**:
1. Accept OAuth configuration parameters
2. Generate OAuth server code if enabled
3. Include OAuth dependencies in requirements.txt

**Example**:
```python
def generate_mcp_server_code(mcp_tools, base_url, enable_oauth=False, oauth_config=None):
    """Generate MCP server Python code from tool definitions"""
    
    code = """
    # Auto-generated MCP Server
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    import httpx
    """
    
    if enable_oauth:
        code += """
    # OAuth 2.1 Server Support
    from oauth_server import OAuthServer
    from starlette.applications import Starlette
    from starlette.routing import Route
    
    # Initialize OAuth server
    oauth_server = OAuthServer(
        client_name='{oauth_client_name}',
        redirect_uris={oauth_redirect_uris}
    )
        """.format(
            oauth_client_name=oauth_config.get('oauth_client_name'),
            oauth_redirect_uris=oauth_config.get('oauth_redirect_uris')
        )
    
    # ... rest of MCP server code generation
    
    return code
```

---

## 5. OAuth Server Files to Package

When OAuth is enabled, include these files with the MCP server:

### 5.1. `oauth_server.py`
- Reuse from `dbhandler_mcpserver/scikiq_pkg_dbutils_online/remote_mcp_server_auth.py`
- OAuth 2.1 implementation with PKCE
- Client registration
- Token management

### 5.2. `oauth_database.db`
- SQLite database for OAuth clients and tokens
- Auto-created on first run
- Schema for clients, tokens, codes

### 5.3. Updated `requirements.txt`
```txt
mcp>=1.0.0
httpx
requests
starlette
uvicorn
authlib>=1.2.0
cryptography
pyjwt
```

---

## 6. File Packaging Function

### `package_mcp_server_for_deployment()`

**Purpose**: Bundle all necessary files for deployment

**Parameters**:
```python
def package_mcp_server_for_deployment(
    server_file_path: str,
    enable_oauth: bool = False,
    oauth_config: dict = None
) -> dict:
    """
    Package MCP server files for deployment
    
    Returns:
    {
        'files': {
            'mcp_server.py': '<content>',
            'requirements.txt': '<content>',
            'oauth_server.py': '<content>',  # if OAuth enabled
            'config.ini': '<content>'        # if needed
        },
        'startup_command': 'python mcp_server.py',
        'port': 30210
    }
    """
```

---

## 7. Testing Endpoints

Create endpoints for testing the new functionality:

### `POST /api/test-github-clone`
Test GitHub repository cloning without scanning

### `POST /api/test-oauth-config`
Validate OAuth configuration

### `GET /api/deployment-status/<deployment_id>`
Check status of ongoing deployments

---

## 📋 Implementation Checklist

### Phase 1: Core Functionality
- [ ] Implement `/api/deploy-mcp-local`
- [ ] Implement `/api/scan-github-repo`
- [ ] Add GitPython dependency
- [ ] Test local deployment flow
- [ ] Test GitHub repo scanning

### Phase 2: OAuth Integration
- [ ] Update `generate_mcp_server_code()` for OAuth
- [ ] Create OAuth file packaging function
- [ ] Test OAuth server generation
- [ ] Verify OAuth server works with Claude

### Phase 3: Online Deployment
- [ ] Update `/api/deploy-aws` for swagger/codebase
- [ ] Update `/api/deploy-azure` for swagger/codebase
- [ ] Update `/api/deploy-remote` for swagger/codebase
- [ ] Test deployments with OAuth enabled
- [ ] Test deployments without OAuth

### Phase 4: Testing & Validation
- [ ] Create test cases for GitHub cloning
- [ ] Create test cases for OAuth config
- [ ] Test end-to-end: Swagger → Deploy → Use in Claude
- [ ] Test end-to-end: GitHub → Deploy → Use in Claude
- [ ] Verify no breaking changes to database MCP

---

## 🚨 Important Notes

1. **Security**: GitHub tokens should be handled securely and not logged
2. **Cleanup**: Always clean up temporary directories after GitHub clones
3. **Error Handling**: Provide clear error messages for GitHub auth failures
4. **OAuth**: OAuth database should be created automatically on first run
5. **Paths**: Handle Windows/Linux path differences correctly
6. **Rate Limits**: Consider GitHub API rate limits for public repos

---

## 📚 Reference Files

**Existing implementations to reference**:
- `mcp_routes.py` - Database MCP deployment (lines 1423-1650)
- `online_deployment.py` - AWS/Azure/Remote deployment
- `dbhandler_mcpserver/scikiq_pkg_dbutils_online/remote_mcp_server_auth.py` - OAuth implementation
- `auto_deploy_mcp.py` - Auto-deployment logic

---

**Created**: November 25, 2025
**Priority**: High
**Estimated Effort**: 8-12 hours
