# Swagger MCP Server Deployment Fix

## Problem
When deploying Swagger/API MCP servers to AWS EC2, the server code was not being copied to the instance. The EC2 instance was created successfully, but the `/home/ubuntu/` directory remained empty, and the MCP server files were missing.

## Root Cause
The frontend's `startDeployment()` function (for the generic Publish Online modal) was **not sending** the `server_type` and `server_path` parameters to the backend when deploying API/Swagger servers.

### Comparison:
- **Database Deployment** (working): Sends `server_type: 'database'`, `config_path`, and `server_path`
- **API/Swagger Deployment** (broken): Only sent AWS credentials, region, instance type, domain, and server_name

Without these parameters, the backend couldn't identify what type of server to prepare or where to find the server files.

## Solution

### Frontend Changes (index.html)
Updated three deployment flows to include missing parameters:

#### 1. AWS Deployment (lines ~6370-6398)
```javascript
// Extract directory path from YAML file path
let serverPath = null;
if (window.lastGeneratedYamlPath) {
    const normalizedPath = window.lastGeneratedYamlPath.replace(/\\/g, '/');
    serverPath = normalizedPath.substring(0, normalizedPath.lastIndexOf('/'));
} else {
    serverPath = 'generated_servers';
}

payload = {
    access_key: ...,
    secret_key: ...,
    region: ...,
    instance_type: ...,
    domain: ...,
    server_name: ...,
    server_type: projectSourceType || 'api',  // NEW: Identify server type
    server_path: serverPath                   // NEW: Directory containing MCP files
};
```

#### 2. Azure Deployment (lines ~6400-6420)
Added the same `server_type` and `server_path` logic.

#### 3. Remote SSH Deployment (lines ~6422-6445)
Added the same `server_type` and `server_path` logic.

## How It Works Now

### Complete Flow:
1. **User converts APIs to MCP tools** → Backend generates:
   - `mcp_server_loader.py` in `generated_servers/`
   - `tools_<name>_<timestamp>.yaml` in `generated_servers/`
   - Stores path in `window.lastGeneratedYamlPath`

2. **User clicks "Deploy Online"** → Opens deployment modal with AWS/Azure/Remote tabs

3. **User fills credentials and clicks "Deploy Now"** → Frontend sends:
   ```json
   {
     "access_key": "...",
     "secret_key": "...",
     "server_type": "swagger",
     "server_path": "C:/DAAS/MCP POC/gaurav/generated_servers"
   }
   ```

4. **Backend receives deployment request** → Calls `_prepare_server_files()`:
   ```python
   elif server_type in ['api', 'codebase', 'swagger']:
       # Read mcp_server_loader.py
       loader_path = base_path / 'mcp_server_loader.py'
       
       # Read all YAML tool files
       yaml_files = list(base_path.glob('tools_*.yaml'))
       
       # Read requirements.txt (or use default)
   ```

5. **Files embedded in setup script** → Base64-encoded and included in EC2 user data

6. **EC2 instance extracts files** → Setup script creates:
   - `/opt/mcp-server/mcp_server_loader.py`
   - `/opt/mcp-server/tools_scikiq_20251102_163628.yaml`
   - `/opt/mcp-server/requirements.txt`

7. **Server starts** → Command:
   ```bash
   /opt/mcp-server/venv/bin/python /opt/mcp-server/mcp_server_loader.py /opt/mcp-server/tools_*.yaml
   ```

## File Locations

### Modified Files:
- `templates/index.html` (lines 6365-6445)
  - Added `server_type` and `server_path` to AWS deployment payload
  - Added `server_type` and `server_path` to Azure deployment payload  
  - Added `server_type` and `server_path` to Remote SSH deployment payload

### Backend Files (already working, no changes needed):
- `online_deployment.py` (lines 368-398)
  - `_prepare_server_files()` already handles 'api', 'swagger', 'codebase' types
  - Reads `mcp_server_loader.py` and `tools_*.yaml` files
  
- `online_deployment.py` (lines 589-596)
  - `generate_setup_script()` already creates correct startup command for API servers

- `templates/ec2_setup_script.sh` (lines 54-115)
  - Already extracts base64-encoded files and handles tarballs

## Testing Steps

1. **Import Swagger file** → Analyze APIs → Convert high-confidence APIs to MCP
2. **Click "Deploy Online"** → Select AWS EC2
3. **Fill credentials** → Access Key, Secret Key, Region, Instance Type
4. **Click "Deploy Now"** → Watch deployment logs
5. **Verify on EC2**:
   ```bash
   ssh -i key.pem ubuntu@<public-ip>
   ls -la /opt/mcp-server/
   # Should see: mcp_server_loader.py, tools_*.yaml, requirements.txt, venv/
   ```
6. **Check server status**:
   ```bash
   sudo systemctl status mcp-server
   # Should be active (running)
   ```
7. **Test API endpoint**:
   ```bash
   curl http://<public-ip>:30210/health
   # Should return: {"status": "healthy"}
   ```

## Key Variables Used

- `window.lastGeneratedYamlPath` - Full path to generated YAML file (e.g., `C:\...\tools_scikiq_20251102_163628.yaml`)
- `projectSourceType` - Type of project source ('swagger', 'api', 'codebase')
- `server_path` - Directory containing MCP server files (extracted from YAML path)
- `server_type` - Type of MCP server for backend to prepare files correctly

## Benefits

1. ✅ Swagger MCP servers now deploy with all necessary code files
2. ✅ Consistent deployment flow for Database and API/Swagger servers
3. ✅ Works across AWS, Azure, and Remote SSH deployments
4. ✅ Fallback to 'generated_servers' if YAML path not found
5. ✅ Proper path normalization (handles Windows backslashes)

## Related Files

- Database MCP deployment: Uses `dbhandler_mcpserver/scikiq_pkg_dbutils_online/`
- API/Swagger MCP deployment: Uses `generated_servers/` with loader + YAML files
- Setup template: `templates/ec2_setup_script.sh`
- Deployment logic: `online_deployment.py`
- Frontend UI: `templates/index.html`

---

**Status**: ✅ Fixed and ready for testing
**Date**: 2024
**Issue**: Swagger MCP server code not copied to EC2
**Solution**: Added server_type and server_path parameters to deployment payloads
