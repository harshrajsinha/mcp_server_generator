# AGENTS.md

A guide for AI coding agents working on SCIKIQ MCP Studio - an AI-powered tool to analyze and convert REST APIs to Anthropic MCP (Model Context Protocol) tools.

## Project Overview

SCIKIQ MCP Studio is a Flask-based web application that:
- Scans Python projects and Swagger/OpenAPI specs to detect API endpoints
- Uses Azure OpenAI GPT-4 to analyze API suitability for MCP conversion
- Generates production-ready MCP server code with YAML tool definitions
- Supports deployment to local Claude Desktop, AWS EC2, Azure VM, and remote servers
- Manages database MCP server configurations (MySQL, PostgreSQL, Oracle, etc.)
- Provides a web UI for configuration management and deployment

## Setup Commands

### Initial Setup
```bash
# Create virtual environment (Windows)
python -m venv venv
venv\Scripts\activate

# Create virtual environment (Linux/Mac)
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file from template (if exists)
cp .env.example .env
# Edit .env and add Azure OpenAI credentials
```

### Environment Variables
Create a `.env` file with:
```env
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4
SECRET_KEY=your-secret-key-here
FLASK_ENV=development
```

### Start Development Server
```bash
python app.py
# Server runs on http://localhost:30211
```

## Code Style

- **Python**: Follow PEP 8 style guide
- **Indentation**: 4 spaces (no tabs)
- **Line length**: Maximum 120 characters
- **Imports**: Group standard library, third-party, then local imports
- **Docstrings**: Use triple-quoted strings for all functions and classes
- **Type hints**: Use type hints where appropriate (Python 3.8+)
- **Error handling**: Always use try-except blocks with specific exception types
- **Logging**: Use Python's logging module, not print statements for production code

### File Structure Conventions
- Main application: `app.py`
- Routes and API handlers: `mcp_routes.py`
- Core logic modules: `intelligent_mcp_converter.py`, `swagger_parser.py`
- Deployment logic: `auto_deploy_mcp.py`, `online_deployment.py`
- Frontend: `templates/index.html`, `static/script.js`, `static/styles.css`
- Generated files: `generated_servers/` directory
- Database configs: `saved_mcp_configs.db` (SQLite)

## Testing Instructions

### Running Tests
```bash
# Test database MCP server components
cd dbhandler_mcpserver/scikiq_pkg_dbutils
python test_connection_management.py
python test_duckdb_mcp.py

# Test online MCP server
cd dbhandler_mcpserver/scikiq_pkg_dbutils_online
python test_remote_server.py
python test_mcp_protocol.py
python test_oauth_flow.py
```

### Manual Testing
```bash
# Health check
curl http://localhost:30211/health

# Test API endpoints
curl -X POST http://localhost:30211/api/scan-project \
  -H "Content-Type: application/json" \
  -d '{"project_path": "path/to/project"}'
```

### Before Committing
- Ensure Flask server starts without errors
- Check browser console for JavaScript errors
- Verify SQLite database operations work correctly
- Test deployment flows (if modifying deployment code)

## Key Files and Their Purposes

### Core Application Files
- **`app.py`**: Main Flask application entry point, sets up routes and error handlers
- **`mcp_routes.py`**: All API endpoints, route handlers, deployment logic, SQLite operations
- **`intelligent_mcp_converter.py`**: AI-powered API scanning and MCP conversion logic
- **`swagger_parser.py`**: Swagger/OpenAPI specification parsing
- **`auto_deploy_mcp.py`**: Local Claude Desktop auto-deployment
- **`online_deployment.py`**: AWS/Azure/Remote server deployment logic

### Frontend Files
- **`templates/index.html`**: Main UI template
- **`static/script.js`**: All frontend JavaScript logic (7000+ lines)
- **`static/styles.css`**: Application styles

### Database MCP Server
- **`dbhandler_mcpserver/`**: Database MCP server implementation
  - `scikiq_pkg_dbutils/`: Local MCP server package
  - `scikiq_pkg_dbutils_online/`: HTTP-based MCP server package
  - Both contain: server.py, connection_manager.py, tools/registry.py, config/ini_parser.py

### Configuration Files
- **`requirements.txt`**: Python dependencies
- **`.env`**: Environment variables (not in git)
- **`saved_mcp_configs.db`**: SQLite database for saved configurations
- **`templates/ec2_setup_script.sh`**: EC2 deployment script template

## Development Workflow

### Adding New Features
1. Create feature branch from main
2. Make changes following code style guidelines
3. Test locally with `python app.py`
4. Check browser console for frontend errors
5. Test SQLite operations if modifying saved configs
6. Commit with descriptive messages

### Database Operations
- SQLite database: `saved_mcp_configs.db` (created automatically)
- Tables: `saved_configs`, `deployments`
- Always use `get_db_connection()` helper from `mcp_routes.py`
- Always close connections after use
- Use parameterized queries to prevent SQL injection

### API Endpoints Structure
All endpoints are in `mcp_routes.py`:
- `/api/scan-project` - Scan Python project for APIs
- `/api/scan-swagger` - Parse Swagger/OpenAPI spec
- `/api/analyze-endpoint` - Analyze single endpoint
- `/api/bulk-analyze-apis` - Bulk analysis
- `/api/batch-convert-to-mcp` - Convert APIs to MCP
- `/api/saved-configs` - CRUD operations for saved configs
- `/api/saved-configs/<id>/yaml` - Get/update YAML files
- `/api/deploy/aws` - AWS deployment
- `/api/deploy/azure` - Azure deployment
- `/api/deploy/remote` - Remote SSH deployment

### Frontend JavaScript Structure
- Functions are organized by feature area
- Use async/await for all API calls
- Store global state in `window.*` variables
- Modal management: Create modals dynamically, remove when closed
- Error handling: Always show user-friendly error messages

## Common Tasks

### Adding a New API Endpoint
1. Add route in `mcp_routes.py` with `@app.route()` decorator
2. Add corresponding frontend function in `static/script.js`
3. Update API documentation in README.md if needed
4. Test endpoint with curl or Postman

### Modifying Deployment Logic
- AWS: Check `online_deployment.py` and AWS deployment routes in `mcp_routes.py`
- Azure: Check Azure deployment routes in `mcp_routes.py`
- Remote SSH: Check remote deployment routes
- Always handle errors gracefully and provide user feedback

### Working with YAML Files
- YAML files are stored in `generated_servers/` directory
- Use `yaml.safe_load()` and `yaml.dump()` for parsing/generating
- Always validate YAML structure before saving
- Handle file path normalization for Windows/Linux compatibility

### SQLite Database Operations
- Use `get_db_connection()` helper function
- Always use parameterized queries: `cursor.execute('SELECT * FROM table WHERE id = ?', (id,))`
- Commit transactions: `conn.commit()`
- Close connections: `conn.close()`
- Handle JSON serialization for complex data: `json.dumps()` / `json.loads()`

## Security Considerations

- **Never commit `.env` file** - Contains API keys and secrets
- **Never commit `saved_mcp_configs.db`** - Contains user data
- **Never commit generated files** - `generated_servers/`, `*.yaml`, `*.py` generated files
- **Validate all user inputs** - Especially file paths and API endpoints
- **Use parameterized SQL queries** - Prevent SQL injection
- **Sanitize file paths** - Prevent path traversal attacks
- **Handle credentials securely** - Don't log or expose AWS/Azure credentials

## Deployment Considerations

### Local Deployment
- Updates Claude Desktop config file
- Requires write access to Claude Desktop config directory
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- Mac: `~/Library/Application Support/Claude/claude_desktop_config.json`

### Cloud Deployment
- AWS: Requires Access Key, Secret Key, Region
- Azure: Requires Subscription ID, Tenant ID, Client ID, Client Secret
- Remote SSH: Requires host, username, password/key
- Always validate domain names before deployment
- Never store credentials in code or config files

## Troubleshooting

### Common Issues

1. **Port 30211 already in use**
   - Change port in `app.py` line 120
   - Update all references to port number

2. **YAML file not found**
   - Check `server_path` and `yaml_file` in saved configs
   - Ensure paths are normalized for current OS
   - Check `generated_servers/` directory exists

3. **SQLite database errors**
   - Ensure database file is writable
   - Check `get_db_path()` returns correct absolute path
   - Verify `init_db()` is called on startup

4. **Frontend errors**
   - Check browser console (F12)
   - Verify all API endpoints return expected JSON format
   - Check for CORS issues if accessing from different origin

5. **Deployment failures**
   - Check cloud provider credentials
   - Verify network connectivity
   - Check deployment logs in browser console
   - Review server-side logs for detailed errors

## Code Organization

### Backend Structure
```
mcp_routes.py (5000+ lines)
├── Database initialization (init_db, get_db_connection)
├── Saved configs CRUD (GET, POST, PUT, DELETE)
├── YAML operations (GET, PUT)
├── Deployment endpoints (AWS, Azure, Remote)
├── API scanning endpoints
├── MCP conversion endpoints
└── Utility functions
```

### Frontend Structure
```
static/script.js (7000+ lines)
├── API scanning functions
├── Swagger parsing functions
├── MCP conversion functions
├── Deployment modal functions
├── Saved configurations functions
├── Edit configuration functions
└── Utility functions
```

## Important Notes

- **Port**: Application runs on port `30211` (not 9555 or other ports)
- **Database**: SQLite database is created automatically at `saved_mcp_configs.db`
- **Generated Files**: All generated MCP servers go to `generated_servers/` directory
- **Path Handling**: Always normalize paths for cross-platform compatibility (Windows uses backslashes)
- **Error Handling**: Always provide user-friendly error messages, log detailed errors server-side
- **Async Operations**: Frontend uses async/await extensively, ensure proper error handling
- **Modal Management**: Modals are created dynamically, always remove them when closing

## Testing Checklist

Before submitting changes:
- [ ] Flask server starts without errors
- [ ] All API endpoints return expected responses
- [ ] Frontend JavaScript has no console errors
- [ ] SQLite database operations work correctly
- [ ] File paths work on both Windows and Linux
- [ ] YAML files are generated and parsed correctly
- [ ] Deployment flows work (if modified)
- [ ] Error messages are user-friendly
- [ ] No sensitive data is logged or exposed

## Additional Resources

- Flask Documentation: https://flask.palletsprojects.com/
- MCP Protocol: https://modelcontextprotocol.io/
- Azure OpenAI: https://learn.microsoft.com/azure/ai-services/openai/
- Anthropic MCP SDK: https://github.com/modelcontextprotocol/python-sdk

