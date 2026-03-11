"""
MCP Studio Routes
Standalone API to MCP conversion tool
"""

from flask import render_template, request, jsonify, send_from_directory, Response, send_file
from flask import stream_with_context
from pathlib import Path
from dotenv import load_dotenv
import os
import json
import yaml
import platform
import subprocess
import time
import sqlite3
from datetime import datetime

# Load environment variables from .env file (override=True ensures .env takes precedence over system env vars)
load_dotenv(override=True)


def generate_yaml_tools_file(mcp_tools, base_url="http://localhost:9321"):
    """
    Generate YAML file containing tool definitions for dynamic loading

    Args:
        mcp_tools: List of tool dictionaries
        base_url: Base URL for the API

    Returns:
        YAML content as string
    """
    tools_config = {
        'base_url': base_url,
        'generated_at': datetime.now().isoformat(),
        'tools': []
    }

    for tool in mcp_tools:
        tool_name = tool['name']
        description = tool['description']
        endpoint = tool['endpoint']
        method = tool['method'].upper()
        params = tool.get('parameters', [])

        # Check if inputSchema is already provided (e.g. by IntelligentMCPConverter)
        input_schema = tool.get('inputSchema')

        if not input_schema:
            # Generate input schema with actual parameters
            properties = {}
            required = []
            for param in params:
                param_name = param.get('name', '')
                param_type = param.get('type', 'string')
                param_desc = param.get('description', '')
                param_required = param.get('required', False)

                if param_name:
                    properties[param_name] = {
                        "type": param_type,
                        "description": param_desc
                    }
                    if param_required:
                        required.append(param_name)

            # Add request body fields
            request_fields = tool.get('request_fields', [])
            for field in request_fields:
                field_name = field.get('name', '')
                field_type = field.get('type', 'string')
                field_desc = field.get('description', '')
                field_required = field.get('required', False)

                if field_name and field_name not in properties:
                    properties[field_name] = {
                        "type": field_type,
                        "description": field_desc
                    }
                    if field_required:
                        required.append(field_name)
            
            input_schema = {
                'type': 'object',
                'properties': properties,
                'required': required
            }

        tool_config = {
            'name': tool_name,
            'description': description,
            'endpoint': endpoint,
            'method': method,
            'input_schema': input_schema
        }

        tools_config['tools'].append(tool_config)

    return yaml.dump(tools_config, default_flow_style=False, sort_keys=False)


def generate_dynamic_mcp_server_loader():
    """
    Generate a dynamic MCP server loader that can load multiple YAML tool files
    Following Anthropic's best practices for Desktop Extensions

    Returns:
        Python code as string for the dynamic loader
    """
    loader_template = '''"""
Dynamic MCP Server Loader - SCIKIQ MCP Studio
Loads tool definitions from YAML files and creates MCP server
Following Anthropic Desktop Extensions best practices
"""

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types
import httpx
import yaml
import sys
import json
import logging
import logging.handlers
import os
from pathlib import Path
from typing import List, Dict, Any

# Configure logging
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

log_file = os.path.join(log_dir, "mcp_server.log")

logger = logging.getLogger("mcp-server")
logger.setLevel(logging.INFO)

# Create handlers
c_handler = logging.StreamHandler(sys.stderr)
f_handler = logging.handlers.TimedRotatingFileHandler(log_file, when='midnight', interval=1, backupCount=30)

c_handler.setLevel(logging.INFO)
f_handler.setLevel(logging.INFO)

# Create formatters and add it to handlers
log_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
c_handler.setFormatter(log_format)
f_handler.setFormatter(log_format)

# Add handlers to the logger
logger.addHandler(c_handler)
logger.addHandler(f_handler)

# Server instance with descriptive name and version
# Following MCP SDK initialization pattern
server = Server("scikiq-mcp-autoAPI")

# Storage for all loaded tools and handlers
all_tools: List[types.Tool] = []
tool_handlers: Dict[str, Dict[str, Any]] = {}

# Track server metadata


def log_message(level: str, message: str) -> None:
    """Log messages to stderr for debugging"""
    if level.lower() == 'error':
        logger.error(message)
    elif level.lower() == 'warning':
        logger.warning(message)
    else:
        logger.info(message)


def validate_tool_config(tool_config: Dict[str, Any], source_file: str) -> bool:
    """
    Validate tool configuration before loading
    Following defensive programming practices
    """
    required_fields = ['name', 'description', 'endpoint', 'method']

    for field in required_fields:
        if field not in tool_config:
            log_message("error", f"Tool in {source_file} missing required field: {field}")
            return False

    # Validate method
    valid_methods = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']
    if tool_config['method'].upper() not in valid_methods:
        log_message("error", f"Invalid HTTP method '{tool_config['method']}' in {source_file}")
        return False

    # Validate name format (no spaces, alphanumeric + hyphens/underscores)
    name = tool_config['name']
    if not name or not all(c.isalnum() or c in '-_' for c in name):
        log_message("error", f"Invalid tool name '{name}' in {source_file}")
        return False

    return True


def load_yaml_tools(yaml_file_path: str) -> int:
    """
    Load tools from a YAML file with validation

    Args:
        yaml_file_path: Path to YAML file containing tool definitions

    Returns:
        Number of tools successfully loaded
    """
    loaded_count = 0

    try:
        # Validate file exists and is readable
        yaml_path = Path(yaml_file_path)
        if not yaml_path.exists():
            log_message("error", f"File not found: {yaml_file_path}")
            return 0

        if not yaml_path.is_file():
            log_message("error", f"Not a file: {yaml_file_path}")
            return 0

        # Load YAML configuration
        with open(yaml_file_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        if not isinstance(config, dict):
            log_message("error", f"Invalid YAML format in {yaml_file_path}")
            return 0

        base_url = config.get('base_url', 'http://localhost:9321')
        tools = config.get('tools', [])

        if not isinstance(tools, list):
            log_message("error", f"'tools' must be a list in {yaml_file_path}")
            return 0

        log_message("info", f"Loading {len(tools)} tools from {yaml_file_path}")

        for idx, tool_config in enumerate(tools):
            try:
                # Validate tool configuration
                if not validate_tool_config(tool_config, yaml_file_path):
                    log_message("warning", f"Skipping invalid tool #{idx + 1}")
                    continue

                tool_name = tool_config['name']

                # Check for duplicate tool names
                if tool_name in tool_handlers:
                    log_message("warning", f"Tool '{tool_name}' already exists, skipping duplicate")
                    continue

                description = tool_config['description']
                endpoint = tool_config['endpoint']
                method = tool_config['method'].upper()
                input_schema = tool_config.get('input_schema', {
                    'type': 'object',
                    'properties': {},
                    'required': []
                })

                # Ensure input_schema has required structure
                if 'type' not in input_schema:
                    input_schema['type'] = 'object'
                if 'properties' not in input_schema:
                    input_schema['properties'] = {}

                # Create MCP tool with clear description
                mcp_tool = types.Tool(
                    name=tool_name,
                    description=description,
                    inputSchema=input_schema
                )
                all_tools.append(mcp_tool)

                # Store handler info
                tool_handlers[tool_name] = {
                    'endpoint': endpoint,
                    'method': method,
                    'base_url': base_url
                }
                loaded_count += 1
                log_message("info", f"Loaded tool: {tool_name} ({method} {endpoint})")

            except Exception as e:
                log_message("error", f"Error processing tool #{idx + 1} in {yaml_file_path}: {str(e)}")
                continue

        log_message("info", f"Successfully loaded {loaded_count}/{len(tools)} tools from {yaml_file_path}")
        return loaded_count

    except yaml.YAMLError as e:
        log_message("error", f"YAML parsing error in {yaml_file_path}: {str(e)}")
        return 0
    except Exception as e:
        log_message("error", f"Failed to load {yaml_file_path}: {str(e)}")
        return 0


# Load all YAML files passed as command-line arguments
total_loaded = 0
if len(sys.argv) > 1:
    log_message("info", f"Starting MCP server with {len(sys.argv) - 1} YAML file(s)")
    for yaml_file in sys.argv[1:]:
        count = load_yaml_tools(yaml_file)
        total_loaded += count
    log_message("info", f"Total tools loaded: {total_loaded}")
else:
    log_message("warning", "No YAML tool files specified. Server will start with no tools.")


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    List all loaded tools

    Returns list of available MCP tools with descriptions
    """
    return all_tools


                    return False, f"Parameter '{arg_name}' must be an object"

        return True, ""

    except Exception as e:
        return False, f"Validation error: {str(e)}"


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    """
    Handle tool calls with comprehensive error handling
    Following MCP SDK patterns for request handling

    Args:
        name: Tool name to invoke
        arguments: Tool parameters

    Returns:
        Tool execution result or error message
    """

    # Validate tool exists
    if name not in tool_handlers:
        available = ', '.join(tool_handlers.keys()) if tool_handlers else 'none'
        error_msg = f"Unknown tool: '{name}'. Available tools: {available}"
        log_message("error", error_msg)
        return [types.TextContent(type="text", text=f"Error: {error_msg}")]

    handler_info = tool_handlers[name]
    base_url = handler_info['base_url']
    endpoint = handler_info['endpoint']
    method = handler_info['method']

    # Get the tool's input schema for validation
    matching_tool = next((t for t in all_tools if t.name == name), None)
    if matching_tool:
        is_valid, validation_error = validate_tool_arguments(
            name,
            arguments,
            matching_tool.inputSchema
        )
        if not is_valid:
            log_message("error", f"Validation failed for tool '{name}': {validation_error}")
            return [types.TextContent(type="text", text=f"Validation Error: {validation_error}")]

    log_message("info", f"Calling tool '{name}' ({method} {base_url}{endpoint})")

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Construct full URL
            url = f"{base_url}{endpoint}"

            # Choose parameter location based on HTTP method
            if method in ['GET', 'DELETE', 'HEAD']:
                # Use query parameters for GET/DELETE/HEAD
                response = await getattr(client, method.lower())(
                    url,
                    params=arguments,
                    timeout=30.0
                )
            else:
                # Use JSON body for POST/PUT/PATCH
                response = await getattr(client, method.lower())(
                    url,
                    json=arguments,
                    timeout=30.0
                )

            # Check for HTTP errors
            response.raise_for_status()

            # Parse response
            try:
                result = response.json()
                result_text = json.dumps(result, indent=2)
            except json.JSONDecodeError:
                result_text = response.text

            log_message("info", f"Tool '{name}' succeeded (status {response.status_code})")
            return [types.TextContent(type="text", text=result_text)]

        except httpx.TimeoutException as e:
            error_msg = f"Request timeout calling {url}: {str(e)}"
            log_message("error", error_msg)
            return [types.TextContent(type="text", text=f"Timeout Error: {error_msg}")]

        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP {e.response.status_code} error from {url}: {e.response.text}"
            log_message("error", error_msg)
            return [types.TextContent(type="text", text=f"HTTP Error: {error_msg}")]

        except httpx.RequestError as e:
            error_msg = f"Request failed to {url}: {str(e)}"
            log_message("error", error_msg)
            return [types.TextContent(type="text", text=f"Connection Error: {error_msg}")]

        except Exception as e:
            error_msg = f"Unexpected error calling tool '{name}': {str(e)}"
            log_message("error", error_msg)
            return [types.TextContent(type="text", text=f"Error: {error_msg}")]


async def main():
    """
    Main entry point for MCP server using stdio transport

    Following MCP best practices:
    - Uses stdio transport (preferred for client compatibility)
    - All logs go to stderr (stdout reserved for MCP protocol messages)
    - Async/await for proper concurrency handling
    - Clean error propagation
    """
    try:
        log_message("info", f"Starting SCIKIQ MCP Server v{SERVER_VERSION}")
        log_message("info", f"Loaded {len(all_tools)} tools from {len(sys.argv) - 1} YAML files")

        # Use stdio transport - stdin for requests, stdout for responses
        # CRITICAL: stdout must contain ONLY valid MCP protocol messages
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())

    except KeyboardInterrupt:
        log_message("info", "Server shutdown requested")
    except Exception as e:
        log_message("error", f"Server error: {str(e)}")
        raise


if __name__ == "__main__":
    import asyncio
    # Run the async server
    asyncio.run(main())
'''
    return loader_template


def generate_mcp_server_code(mcp_tools, base_url="http://localhost:9321", enable_oauth=False, oauth_config=None):
    """Generate MCP server Python code from tool definitions using MCP SDK 1.x"""

    # Build tool list for list_tools
    tools_list = []
    tools_handlers = []

    for tool in mcp_tools:
        tool_name = tool['name']
        description = tool['description'].replace('"', '\\"')  # Escape quotes
        endpoint = tool['endpoint']
        method = tool['method'].upper()
        params = tool.get('parameters', [])

        # Generate input schema with actual parameters
        properties = {}
        required = []
        for param in params:
            param_name = param.get('name', '')
            param_type = param.get('type', 'string')
            param_desc = param.get('description', '').replace('"', '\\"')
            param_required = param.get('required', False)

            if param_name:
                properties[param_name] = {
                    "type": param_type,
                    "description": param_desc
                }
                if param_required:
                    required.append(param_name)

        # Generate tool definition with proper schema
        properties_str = json.dumps(properties) if properties else '{}'
        required_str = json.dumps(required) if required else '[]'

        tools_list.append(f'''        types.Tool(
            name="{tool_name}",
            description="{description}",
            inputSchema={{
                "type": "object",
                "properties": {properties_str},
                "required": {required_str}
            }}
        )''')

        # Generate tool handler with proper error handling and argument passing
        if method in ['GET', 'DELETE']:
            # GET/DELETE use query parameters
            tools_handlers.append(f'''    elif name == "{tool_name}":
        response = await client.{method.lower()}(f"{{BASE_URL}}{endpoint}", params=arguments, timeout=30.0)
        response.raise_for_status()
        return [types.TextContent(type="text", text=str(response.json()))]
''')
        else:
            # POST/PUT use JSON body
            tools_handlers.append(f'''    elif name == "{tool_name}":
        response = await client.{method.lower()}(f"{{BASE_URL}}{endpoint}", json=arguments, timeout=30.0)
        response.raise_for_status()
        return [types.TextContent(type="text", text=str(response.json()))]
''')

    # Join tools with commas
    tools_joined = ',\n'.join(tools_list)

    # Build the first handler without elif
    first_handler = tools_handlers[0].replace('elif name ==', 'if name ==') if tools_handlers else ''
    remaining_handlers = ''.join(tools_handlers[1:]) if len(tools_handlers) > 1 else ''

    # OAuth imports and setup
    oauth_imports = ''
    oauth_server_setup = ''
    oauth_requirements = ''
    
    if enable_oauth and oauth_config:
        oauth_imports = '''
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.responses import HTMLResponse, RedirectResponse, JSONResponse
from authlib.integrations.starlette_client import OAuth, OAuthError
import uvicorn
from pathlib import Path
import sqlite3
import secrets
'''
        
        # Extract OAuth config
        provider = oauth_config.get('provider', 'custom')
        client_id = oauth_config.get('client_id', '')
        client_secret = oauth_config.get('client_secret', '')
        auth_url = oauth_config.get('auth_url', '')
        token_url = oauth_config.get('token_url', '')
        user_info_url = oauth_config.get('user_info_url', '')
        redirect_uri = oauth_config.get('redirect_uri', 'http://localhost:8080/auth/callback')
        
        oauth_server_setup = f'''
# OAuth Configuration
OAUTH_CONFIG = {{
    'provider': '{provider}',
    'client_id': '{client_id}',
    'client_secret': '{client_secret}',
    'auth_url': '{auth_url}',
    'token_url': '{token_url}',
    'user_info_url': '{user_info_url}',
    'redirect_uri': '{redirect_uri}'
}}

# Initialize OAuth
oauth = OAuth()
oauth.register(
    name='provider',
    client_id=OAUTH_CONFIG['client_id'],
    client_secret=OAUTH_CONFIG['client_secret'],
    authorize_url=OAUTH_CONFIG['auth_url'],
    access_token_url=OAUTH_CONFIG['token_url'],
    client_kwargs={{'scope': 'openid profile email'}}
)

# Database for token storage
def init_db():
    conn = sqlite3.connect('oauth_tokens.db')
    c = conn.cursor()
    c.execute(\'\'\'CREATE TABLE IF NOT EXISTS tokens
                 (id TEXT PRIMARY KEY, access_token TEXT, refresh_token TEXT, expires_at REAL)\'\'\')
    conn.commit()
    conn.close()

init_db()

# OAuth routes
async def login(request):
    redirect_uri = OAUTH_CONFIG['redirect_uri']
    return await oauth.provider.authorize_redirect(request, redirect_uri)

async def auth_callback(request):
    try:
        token = await oauth.provider.authorize_access_token(request)
        # Store token in database
        token_id = secrets.token_urlsafe(16)
        conn = sqlite3.connect('oauth_tokens.db')
        c = conn.cursor()
        c.execute('INSERT OR REPLACE INTO tokens VALUES (?, ?, ?, ?)',
                  (token_id, token['access_token'], token.get('refresh_token'), 
                   token.get('expires_at', 0)))
        conn.commit()
        conn.close()
        return HTMLResponse(f'<h1>Authentication successful! Token ID: {{token_id}}</h1>')
    except OAuthError as e:
        return HTMLResponse(f'<h1>Authentication failed: {{e.description}}</h1>')

# Starlette app for OAuth
oauth_app = Starlette(routes=[
    Route('/login', login),
    Route('/auth/callback', auth_callback),
])

def start_oauth_server():
    uvicorn.run(oauth_app, host='0.0.0.0', port=8080)
'''
        
        oauth_requirements = '''authlib==1.3.0
uvicorn[standard]==0.25.0
starlette==0.35.0
cryptography==41.0.7
pyjwt==2.8.0
'''

    server_template = f'''"""
Auto-generated MCP Server
Generated by SCIKIQ MCP Studio
{"With OAuth 2.1 Support" if enable_oauth else ""}
"""

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types
import httpx{oauth_imports}

server = Server("scikiq-mcp-autoAPI")

# Base URL for the API server
BASE_URL = "{base_url}"
{oauth_server_setup}

@server.list_tools()
async def list_tools() -> list[types.Tool]:
    """List available tools"""
    return [
{tools_joined}
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    """Handle tool calls"""

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
{first_handler}{remaining_handlers}
            else:
                raise ValueError(f"Unknown tool: {{name}}")

        except httpx.HTTPError as e:
            return [types.TextContent(type="text", text=f"HTTP Error: {{str(e)}}")]
        except Exception as e:
            return [types.TextContent(type="text", text=f"Error: {{str(e)}}")]


async def main():
    {"# Start OAuth server in background thread" if enable_oauth else ""}
    {"import threading" if enable_oauth else ""}
    {"oauth_thread = threading.Thread(target=start_oauth_server, daemon=True)" if enable_oauth else ""}
    {"oauth_thread.start()" if enable_oauth else ""}
    {"print('OAuth server started on http://localhost:8080')" if enable_oauth else ""}
    
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
'''

    return server_template, oauth_requirements


def setup_mcp_routes(app):
    """Setup all MCP Studio routes"""

    # ==================== MAIN PAGES ====================

    @app.route('/')
    def mcp_home():
        """MCP Studio Home Page"""
        return render_template('index.html')

    # ==================== API ENDPOINTS ====================

    @app.route('/api/config', methods=['GET'])
    def get_config():
        """Get frontend configuration from environment variables"""
        try:
            config = {
                'default_project_path': os.getenv('DEFAULT_PROJECT_PATH', os.path.dirname(os.path.abspath(__file__))),
                'default_source_file': os.getenv('DEFAULT_SOURCE_FILE', 'glic_routes.py')
            }
            return jsonify(config)
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/scan-project', methods=['POST'])
    def mcp_scan_project():
        """Intelligent project scan with API detection reasoning - Returns URLs like Swagger"""
        try:
            from intelligent_mcp_converter import IntelligentMCPConverter
            import os

            data = request.get_json(silent=True) or {}
            project_path = data.get('project_path', os.path.dirname(os.path.abspath(__file__)))
            source_file = data.get('source_file', '')
            api_base_url = data.get('api_base_url', 'http://localhost:5000')

            print(f"[SCAN] Starting codebase scan: {project_path}")
            print(f"[SCAN] Source file filter: {source_file or 'All files'}")
            print(f"[SCAN] API Base URL: {api_base_url}")

            # Check if github_repo_url is provided (from frontend)
            github_repo_url = data.get('github_repo_url')
            if github_repo_url:
                print(f"[SCAN] Found github_repo_url in payload: {github_repo_url}")
                project_path = github_repo_url

            # Ensure project_path is a string and strip whitespace
            if project_path:
                project_path = str(project_path).strip()
            
            print(f"[SCAN] Processed project path: '{project_path}'")

            # Handle GitHub URLs
            if project_path and project_path.startswith(('http://', 'https://', 'git@')):
                print(f"[SCAN] Detected GitHub URL: {project_path}")
                
                # Create cloned_repos directory if it doesn't exist
                cloned_repos_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cloned_repos')
                os.makedirs(cloned_repos_dir, exist_ok=True)
                
                # Extract repo name from URL
                repo_name = project_path.split('/')[-1]
                if repo_name.endswith('.git'):
                    repo_name = repo_name[:-4]
                
                # Handle GitHub Token for private repos
                github_token = data.get('github_token')
                clone_url = project_path
                
                if github_token and 'github.com' in project_path and 'https://' in project_path:
                    # Insert token into URL: https://<token>@github.com/...
                    scheme, rest = project_path.split('://', 1)
                    clone_url = f"{scheme}://{github_token}@{rest}"
                    print("[SCAN] Added GitHub token to clone URL")
                
                target_dir = os.path.join(cloned_repos_dir, repo_name)
                
                # Check if already cloned
                if os.path.exists(target_dir):
                    print(f"[SCAN] Repository already exists at {target_dir}, pulling latest changes...")
                    try:
                        subprocess.run(['git', '-C', target_dir, 'pull'], check=True, capture_output=True)
                        print("[SCAN] Git pull successful")
                    except Exception as e:
                        print(f"[WARN] Git pull failed: {e}")
                        # If pull fails, might be better to re-clone or just proceed
                else:
                    print(f"[SCAN] Cloning repository to {target_dir}...")
                    try:
                        subprocess.run(['git', 'clone', clone_url, target_dir], check=True, capture_output=True)
                        print("[SCAN] Git clone successful")
                    except subprocess.CalledProcessError as e:
                        error_msg = f"Failed to clone repository: {e.stderr.decode() if e.stderr else str(e)}"
                        print(f"[ERROR] {error_msg}")
                        return jsonify({'error': error_msg, 'success': False}), 400
                    except Exception as e:
                        print(f"[ERROR] Clone error: {e}")
                        return jsonify({'error': str(e), 'success': False}), 500
                
                # Update project_path to the local cloned directory
                project_path = target_dir
                print(f"[SCAN] Updated project path to: {project_path}")

            # Use intelligent MCP converter with detection reasoning
            converter = IntelligentMCPConverter(project_path, api_base_url)
            endpoints = converter.analyze_codebase(source_file)
            mcp_tools = converter.convert_to_mcp_tools()

            print(f"[SCAN] Found {len(endpoints)} API endpoints")

            # Detect framework(s) used
            detected_frameworks = set()
            for endpoint in endpoints:
                if hasattr(endpoint, 'is_api_reasoning') and endpoint.is_api_reasoning:
                    framework = endpoint.is_api_reasoning.get('framework', 'unknown')
                    if framework != 'unknown':
                        detected_frameworks.add(framework)
            
            # Fallback framework detection
            if not detected_frameworks:
                detected_frameworks = {'flask'}  # Default assumption
            
            framework_name = ', '.join(detected_frameworks).title()
            print(f"[SCAN] Detected frameworks: {framework_name}")

            # Build API definitions with detection reasoning (Swagger-compatible format)
            api_definitions = []
            for endpoint in endpoints:
                api_def = {
                    'route': endpoint.path,
                    'methods': endpoint.methods,
                    'function_name': endpoint.function_name,
                    'docstring': endpoint.purpose,
                    'summary': endpoint.purpose,  # Swagger-compatible field
                    'description': endpoint.purpose,  # Swagger-compatible field
                    'parameters': endpoint.parameters,
                    'request_fields': endpoint.request_body_fields,
                    'file': endpoint.file_location,
                    'file_name': os.path.basename(endpoint.file_location),
                    'line_number': endpoint.line_number,
                    'business_domain': endpoint.business_domain,
                    'security_level': endpoint.security_level,
                    'confidence': endpoint.confidence_score,
                    'is_async': endpoint.is_async,
                    'function_code': endpoint.function_code,
                    # Detection reasoning
                    'detection': {
                        'decision': endpoint.is_api_reasoning.get('decision', 'API'),
                        'score': endpoint.is_api_reasoning.get('score', 0),
                        'threshold': endpoint.is_api_reasoning.get('threshold', 2),
                        'signals': endpoint.is_api_reasoning.get('signals', [])
                    }
                }
                api_definitions.append(api_def)

            # Calculate statistics by domain
            domains = {}
            for ep in endpoints:
                domains[ep.business_domain] = domains.get(ep.business_domain, 0) + 1

            # Group URLs by business domain (for tree display like Swagger tags)
            domain_groups = {}
            for api_def in api_definitions:
                domain = api_def['business_domain']
                if domain not in domain_groups:
                    domain_groups[domain] = []
                domain_groups[domain].append(api_def)

            print(f"[SCAN] Grouped into {len(domain_groups)} business domains: {list(domain_groups.keys())}")

            # Return Swagger-like response structure
            combined_results = {
                'success': True,
                'api_definitions': api_definitions,  # Flat list for compatibility
                'domain_groups': domain_groups,  # Grouped by domain for tree view
                'total_apis': len(endpoints),
                'api_base_url': api_base_url,
                'message': f'Successfully scanned {len(endpoints)} API endpoints from codebase',
                'intelligence': {
                    'project_type': f'{framework_name} REST API',
                    'conversion_method': 'intelligent_semantic_analysis',
                    'frameworks': list(detected_frameworks),
                    'business_domains': list(domains.keys()),
                    'domain_distribution': domains,
                    'avg_confidence': sum(e.confidence_score for e in endpoints) / len(endpoints) if endpoints else 0,
                    'detection_summary': {
                        'api_endpoints_found': len(endpoints),
                        'avg_detection_score': sum(e.is_api_reasoning.get('score', 0) for e in endpoints) / len(endpoints) if endpoints else 0
                    }
                }
            }

            return jsonify(combined_results)

        except BrokenPipeError:
            # Client disconnected - this is not a real error
            return jsonify({
                'success': False,
                'error': 'Client disconnected'
            }), 499
        except Exception as e:
            import traceback
            try:
                traceback.print_exc()
            except BrokenPipeError:
                pass  # Ignore broken pipe when printing traceback
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/read-file', methods=['POST'])
    def mcp_read_file():
        """Read file content for code viewer"""
        try:
            data = request.get_json()
            file_path = data.get('file_path')

            if not file_path or not os.path.exists(file_path):
                return jsonify({
                    'success': False,
                    'error': 'File not found'
                }), 404

            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            return jsonify({
                'success': True,
                'content': content,
                'file_path': file_path
            })

        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/generate-yaml-documentation', methods=['POST'])
    def generate_yaml_documentation():
        """Generate comprehensive documentation from YAML MCP tools file"""
        try:
            import yaml

            data = request.get_json()
            yaml_content = data.get('yaml_content')
            yaml_path = data.get('yaml_path')

            # Get YAML content from path if not provided directly
            if not yaml_content and yaml_path:
                if os.path.exists(yaml_path):
                    with open(yaml_path, 'r', encoding='utf-8') as f:
                        yaml_content = f.read()
                else:
                    return jsonify({
                        'success': False,
                        'error': 'YAML file not found'
                    }), 404

            if not yaml_content:
                return jsonify({
                    'success': False,
                    'error': 'No YAML content provided'
                }), 400

            # Parse YAML
            try:
                yaml_data = yaml.safe_load(yaml_content)
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': f'Invalid YAML: {str(e)}'
                }), 400

            tools = yaml_data.get('tools', [])
            server_info = yaml_data.get('server', {})

            # Generate documentation in Markdown format
            doc_lines = []

            # Header
            doc_lines.append("# MCP Server API Documentation")
            doc_lines.append("")
            doc_lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            doc_lines.append(f"**Total Tools:** {len(tools)}")
            doc_lines.append("")

            # Server info if available
            if server_info:
                doc_lines.append("## Server Configuration")
                doc_lines.append("")
                if server_info.get('name'):
                    doc_lines.append(f"- **Name:** {server_info.get('name')}")
                if server_info.get('version'):
                    doc_lines.append(f"- **Version:** {server_info.get('version')}")
                if server_info.get('base_url'):
                    doc_lines.append(f"- **Base URL:** `{server_info.get('base_url')}`")
                doc_lines.append("")

            # Table of Contents
            doc_lines.append("## Table of Contents")
            doc_lines.append("")
            for i, tool in enumerate(tools, 1):
                tool_name = tool.get('name', f'tool_{i}')
                doc_lines.append(f"{i}. [{tool_name}](#{tool_name.lower().replace('_', '-')})")
            doc_lines.append("")

            # Tools Documentation
            doc_lines.append("---")
            doc_lines.append("")
            doc_lines.append("## API Tools Reference")
            doc_lines.append("")

            for tool in tools:
                tool_name = tool.get('name', 'Unknown')
                description = tool.get('description', 'No description available')
                method = tool.get('method', 'GET').upper()
                endpoint = tool.get('endpoint', '/')
                input_schema = tool.get('inputSchema', {})
                properties = input_schema.get('properties', {})
                required = input_schema.get('required', [])

                # Tool Header
                doc_lines.append(f"### {tool_name}")
                doc_lines.append("")
                doc_lines.append(f"**Description:** {description}")
                doc_lines.append("")
                doc_lines.append(f"**Endpoint:** `{method} {endpoint}`")
                doc_lines.append("")

                # Parameters
                if properties:
                    doc_lines.append("#### Parameters")
                    doc_lines.append("")
                    doc_lines.append("| Parameter | Type | Required | Description |")
                    doc_lines.append("|-----------|------|----------|-------------|")

                    for param_name, param_info in properties.items():
                        param_type = param_info.get('type', 'string')
                        param_desc = param_info.get('description', '-')
                        is_required = '✓' if param_name in required else '✗'
                        doc_lines.append(f"| `{param_name}` | {param_type} | {is_required} | {param_desc} |")

                    doc_lines.append("")
                else:
                    doc_lines.append("#### Parameters")
                    doc_lines.append("")
                    doc_lines.append("*No parameters required*")
                    doc_lines.append("")

                # Example Usage
                doc_lines.append("#### Example Usage")
                doc_lines.append("")
                doc_lines.append("```json")
                doc_lines.append("{")
                doc_lines.append(f'  "tool": "{tool_name}",')
                doc_lines.append('  "arguments": {')

                example_args = []
                for param_name, param_info in properties.items():
                    param_type = param_info.get('type', 'string')
                    if param_type == 'string':
                        example_args.append(f'    "{param_name}": "example_value"')
                    elif param_type == 'integer' or param_type == 'number':
                        example_args.append(f'    "{param_name}": 0')
                    elif param_type == 'boolean':
                        example_args.append(f'    "{param_name}": true')
                    elif param_type == 'array':
                        example_args.append(f'    "{param_name}": []')
                    elif param_type == 'object':
                        example_args.append(f'    "{param_name}": {{}}')
                    else:
                        example_args.append(f'    "{param_name}": null')

                doc_lines.append(',\n'.join(example_args))
                doc_lines.append('  }')
                doc_lines.append("}")
                doc_lines.append("```")
                doc_lines.append("")
                doc_lines.append("---")
                doc_lines.append("")

            # Footer
            doc_lines.append("## Notes")
            doc_lines.append("")
            doc_lines.append("- All endpoints require proper authentication if configured")
            doc_lines.append("- Response format is JSON")
            doc_lines.append("- Error responses include `error` field with description")
            doc_lines.append("")
            doc_lines.append("---")
            doc_lines.append("")
            doc_lines.append("*Documentation auto-generated by SCIKIQ MCP Studio*")

            documentation = '\n'.join(doc_lines)

            return jsonify({
                'success': True,
                'documentation': documentation,
                'tool_count': len(tools),
                'format': 'markdown'
            })

        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/analyze-endpoint', methods=['POST'])
    def mcp_analyze_endpoint():
        """Analyze endpoint with AI to generate plain English explanation and MCP suitability score"""
        try:
            from openai import AzureOpenAI

            data = request.get_json()
            route = data.get('route', '')
            method = data.get('method', 'GET')
            function_name = data.get('function_name', '')
            function_code = data.get('function_code', '')
            docstring = data.get('docstring', '')
            business_domain = data.get('business_domain', 'general')

            # Azure OpenAI configuration from .env file
            api_key = os.getenv('AZURE_OPENAI_API_KEY')
            azure_endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')
            api_version = os.getenv('AZURE_OPENAI_API_VERSION')
            deployment_name = os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME')

            if not api_key:
                return jsonify({
                    'success': False,
                    'error': 'Azure OpenAI API key not configured. Please set AZURE_OPENAI_API_KEY environment variable.'
                }), 400

            # Create httpx client with proxy disabled to avoid 'proxies' argument error
            import httpx
            http_client = httpx.Client(proxy=None, trust_env=False)

            # Use Azure OpenAI to analyze the endpoint
            client = AzureOpenAI(
                api_key=api_key,
                api_version=api_version,
                azure_endpoint=azure_endpoint,
                http_client=http_client
            )

            analysis_prompt = f"""You are a CRITICAL API analyst. Analyze this endpoint's MCP tool suitability with realistic, varied scoring.

Route: {method} {route}
Function Name: {function_name}
Business Domain: {business_domain}
Current Documentation: {docstring}

Function Code:
{function_code}

SCORING GUIDELINES (be strict and realistic):
- 90-100%: Perfect MCP tool - pure data API, well-documented, clear parameters, stateless, returns JSON
- 75-89%: Good candidate - returns data but has minor issues (missing docs, some complexity)
- 60-74%: Acceptable - usable but has limitations (partial docs, moderate complexity)
- 40-59%: Marginal - significant issues (poor docs, complex state, mixed concerns)
- 20-39%: Poor - mostly unsuitable (HTML rendering, complex UI logic, heavy dependencies)
- 0-19%: Not suitable - definitely not an MCP tool (static pages, redirects, file downloads)

RED FLAGS (lower score):
- Renders HTML templates (render_template, .html) → Score 10-20%
- Missing or vague documentation (when parameters exist) → Reduce 15-25%
- Complex business logic without clear parameters → Reduce 20-30%
- Database queries without clear data model (for complex queries) → Reduce 10-15%
- Side effects (email sending, file operations) without documentation → Reduce 10-15%

GREEN FLAGS (higher score):
- Returns JSON/dict (jsonify, return dict) → +15-20%
- Well-documented with parameter descriptions → +10-15%
- Clear, focused purpose → +10-15%
- No side effects or well-documented ones → +5-10%
- RESTful design with proper HTTP methods → +5-10%

Provide response in JSON format:
{{
  "plain_english": "2-3 sentence business explanation in simple terms",
  "mcp_score": 0-100,
  "key_strengths": ["strength 1", "strength 2"],
  "key_weaknesses": ["weakness 1", "weakness 2"],
  "recommended_parameters": [
    {{"name": "param1", "type": "string", "description": "what it does", "required": true}}
  ],
  "example_tool_call": "mcp_tool_name(param1='value', param2=123)",
  "improvement_suggestions": ["suggestion 1", "suggestion 2"]
}}"""

            response = client.chat.completions.create(
                model=deployment_name,
                messages=[
                    {"role": "system", "content": "You are a fair, critical API analyst who provides realistic MCP suitability scores. Be strict but fair."},
                    {"role": "user", "content": analysis_prompt}
                ],
                temperature=0.5,
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)

            return jsonify({
                'success': True,
                'analysis': result
            })

        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/bulk-analyze-apis', methods=['POST'])
    def mcp_bulk_analyze_apis():
        """Analyze all APIs and return summary with confidence filtering"""
        try:
            from openai import AzureOpenAI
            import json

            data = request.get_json()
            endpoints = data.get('endpoints', [])
            min_confidence = data.get('min_confidence', 80)
            max_apis = data.get('max_apis', 10)  # Default to 10, but can be overridden by frontend

            # Limit number of APIs to analyze based on frontend selection
            if len(endpoints) > max_apis:
                print(f"[INFO] Limiting analysis from {len(endpoints)} to {max_apis} APIs as requested")
                endpoints = endpoints[:max_apis]

            if len(endpoints) == 0:
                return jsonify({
                    'success': False,
                    'error': 'No endpoints to analyze'
                }), 400

            # Azure OpenAI configuration
            api_key = os.getenv('AZURE_OPENAI_API_KEY')
            azure_endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')
            api_version = os.getenv('AZURE_OPENAI_API_VERSION')
            deployment_name = os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME')

            if not api_key:
                return jsonify({
                    'success': False,
                    'error': 'Azure OpenAI API key not configured'
                }), 400

            # Create httpx client with proxy disabled to avoid 'proxies' argument error
            import httpx
            http_client = httpx.Client(proxy=None, trust_env=False)

            client = AzureOpenAI(
                api_key=api_key,
                api_version=api_version,
                azure_endpoint=azure_endpoint,
                http_client=http_client
            )

            analyzed_endpoints = []
            high_confidence_apis = []

            print(f"[INFO] Starting bulk analysis of {len(endpoints)} APIs...")
            import sys

            for idx, endpoint_data in enumerate(endpoints):
                print(f"[INFO] Analyzing {idx+1}/{len(endpoints)}: {endpoint_data.get('route')}")
                sys.stdout.flush()
                try:
                    route = endpoint_data.get('route')
                    method = endpoint_data.get('methods', ['GET'])[0]
                    function_code = endpoint_data.get('function_code', '')
                    docstring = endpoint_data.get('docstring', '')
                    business_domain = endpoint_data.get('business_domain', 'general')

                    analysis_prompt = f"""Analyze this API endpoint for MCP tool suitability:

Route: {method} {route}
Business Domain: {business_domain}
Documentation: {docstring}

Function Code:
{function_code}

Score it 0-100% and provide:
1. Plain English explanation (2-3 sentences)
2. MCP suitability score (be realistic)
3. Key strengths (bullet points)
4. Key weaknesses (bullet points)

Respond in JSON:
{{
  "plain_english": "Business explanation",
  "mcp_score": 85,
  "strengths": ["strength 1", "strength 2"],
  "weaknesses": ["weakness 1", "weakness 2"],
  "recommended_action": "convert|enhance|skip"
}}"""

                    response = client.chat.completions.create(
                        model=deployment_name,
                        messages=[
                            {"role": "system", "content": "You are a fair API analyst. Be balanced in scoring."},
                            {"role": "user", "content": analysis_prompt}
                        ],
                        temperature=0.5,
                        response_format={"type": "json_object"}
                    )

                    result = json.loads(response.choices[0].message.content)

                    analyzed_endpoint = {
                        **endpoint_data,
                        'analysis': {
                            'plain_english': result.get('plain_english', ''),
                            'mcp_score': result.get('mcp_score', 50),
                            'strengths': result.get('strengths', []),
                            'weaknesses': result.get('weaknesses', []),
                            'recommended_action': result.get('recommended_action', 'review')
                        }
                    }

                    analyzed_endpoints.append(analyzed_endpoint)

                    # Filter by confidence
                    if result.get('mcp_score', 0) >= min_confidence:
                        high_confidence_apis.append(analyzed_endpoint)

                except Exception as e:
                    print(f"Error analyzing {route}: {str(e)}")
                    continue

            # Calculate statistics
            total_apis = len(analyzed_endpoints)
            avg_score = sum(ep['analysis']['mcp_score'] for ep in analyzed_endpoints) / total_apis if total_apis > 0 else 0

            print(f"[SUCCESS] Bulk analysis complete: {total_apis} APIs analyzed, {len(high_confidence_apis)} high confidence")
            sys.stdout.flush()

            return jsonify({
                'success': True,
                'summary': {
                    'total_analyzed': total_apis,
                    'high_confidence_count': len(high_confidence_apis),
                    'average_score': round(avg_score, 1),
                    'min_confidence_threshold': min_confidence,
                    'limited': len(data.get('endpoints', [])) > max_apis
                },
                'high_confidence_apis': high_confidence_apis,
                'all_analyzed_apis': analyzed_endpoints
            })

        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/batch-convert-to-mcp', methods=['POST'])
    def mcp_batch_convert_to_mcp():
        """Convert multiple APIs to MCP tools in batch using YAML-based approach"""
        try:
            data = request.get_json()
            endpoints = data.get('endpoints', [])
            output_file = data.get('output_file', 'mcp_server_generated.py')
            # Get base_url, with proper fallback to default if not provided or empty
            base_url = data.get('base_url') or data.get('api_base_url') or 'http://localhost:9321'
            # If base_url is empty string, use default
            if not base_url or base_url.strip() == '':
                base_url = 'http://localhost:9321'
            
            server_name = data.get('server_name', 'scikiq-mcp-autoAPI')
            # Authentication and other API connection options to persist in YAML
            auth_config = {
                'auth_type': data.get('auth_type', 'none'),
                'auth_token': data.get('auth_token'),
                'auth_user': data.get('auth_user'),
                'auth_pass': data.get('auth_pass'),
                'verify_ssl': data.get('verify_ssl', True),
                'timeout': data.get('timeout', 30)
            }

            # Ensure output goes to generated_servers folder
            os.makedirs('generated_servers', exist_ok=True)

            # Generate MCP server code for all endpoints
            mcp_tools = []

            for endpoint_data in endpoints:
                route = endpoint_data.get('route')
                methods = endpoint_data.get('methods', ['GET'])
                function_name = endpoint_data.get('function_name', '')
                # Prefer human-friendly description from analysis if present
                analysis = endpoint_data.get('analysis', {}) or {}
                plain_desc = analysis.get('plain_english') if isinstance(analysis, dict) else None
                docstring = endpoint_data.get('docstring', '')
                description = plain_desc or docstring or f'Access {route}'
                parameters = endpoint_data.get('parameters', [])
                request_fields = endpoint_data.get('request_fields', [])

                tool_definition = {
                    'name': function_name.replace('glic_', '').replace('_', '-'),
                    'description': description,
                    'endpoint': route,
                    'method': methods[0],
                    'parameters': parameters,
                    'request_fields': request_fields
                }

                mcp_tools.append(tool_definition)

            # Generate unique timestamp for this tool set
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

            # Create a YAML filename that includes the server name for easy linking
            safe_server = ''.join(c for c in server_name if (c.isalnum() or c in '-_')).lower() or 'scikiq'
            yaml_filename = f'tools_{safe_server}_{timestamp}.yaml'
            yaml_path = os.path.join('generated_servers', yaml_filename)

            # Build YAML content including auth and generated metadata
            yaml_content = generate_yaml_tools_file(mcp_tools, base_url)
            # If generate_yaml_tools_file returns a string, try to prepend top-level metadata
            try:
                # Try to parse as text and prepend metadata block
                meta = f"base_url: {base_url}\ngenerated_at: '{datetime.now().isoformat()}'\nserver: {server_name}\n"
                # include auth only if provided
                if auth_config.get('auth_type') and auth_config.get('auth_type') != 'none':
                    meta += 'auth:\n'
                    for k, v in auth_config.items():
                        if v is not None:
                            meta += f"  {k}: {v}\n"

                # If yaml_content already has a top-level base_url, avoid duplicating
                if isinstance(yaml_content, str) and 'base_url:' not in yaml_content.split('\n', 1)[0]:
                    yaml_full = meta + yaml_content
                else:
                    yaml_full = yaml_content
            except Exception:
                yaml_full = yaml_content

            with open(yaml_path, 'w', encoding='utf-8') as f:
                f.write(yaml_full)

            # Generate/update the dynamic loader script (ensure loader exists)
            loader_filename = 'mcp_server_loader.py'
            loader_path = os.path.join('generated_servers', loader_filename)

            if not os.path.exists(loader_path):
                loader_code = generate_dynamic_mcp_server_loader()
                with open(loader_path, 'w', encoding='utf-8') as f:
                    f.write(loader_code)

            return jsonify({
                'success': True,
                'converted_count': len(mcp_tools),
                'output_file': loader_filename,
                'output_path': os.path.abspath(loader_path),
                'yaml_file': yaml_filename,
                'yaml_path': os.path.abspath(yaml_path),
                'tools': mcp_tools,
                'message': f'Successfully converted {len(mcp_tools)} APIs to MCP tools',
                'note': 'Tools saved to YAML file. Use loader script with YAML file(s) as arguments.',
                'linked_server': server_name
            })

        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/generated/<path:filename>')
    def serve_generated_file(filename):
        """Serve generated MCP server files"""
        return send_from_directory('generated_servers', filename, mimetype='text/plain; charset=utf-8')
    
    @app.route('/mcp_server_loader.py')
    def serve_mcp_server_loader():
        """Serve mcp_server_loader.py from generated_servers directory"""
        try:
            loader_path = os.path.join('generated_servers', 'mcp_server_loader.py')
            if os.path.exists(loader_path):
                return send_file(
                    loader_path,
                    mimetype='text/x-python; charset=utf-8',
                    as_attachment=False
                )
            else:
                # Try to find it in any subdirectory
                generated_dir = Path('generated_servers')
                if generated_dir.exists():
                    for loader_file in generated_dir.rglob('mcp_server_loader.py'):
                        return send_file(
                            str(loader_file),
                            mimetype='text/x-python; charset=utf-8',
                            as_attachment=False
                        )
                return jsonify({'error': 'mcp_server_loader.py not found'}), 404
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/glic/mcp-deployment')
    def mcp_deployment_page():
        """MCP Deployment status and instructions page"""
        return jsonify({
            'status': 'ready',
            'message': 'MCP Deployment Service',
            'endpoints': {
                'deploy': {
                    'url': '/api/auto-deploy-mcp',
                    'method': 'POST',
                    'description': 'Automatically deploy MCP server to Claude Desktop',
                    'example': {
                        'server_path': os.path.join(os.getenv('DEFAULT_PROJECT_PATH', os.path.dirname(os.path.abspath(__file__))), 'generated_servers', 'mcp_server_high_confidence.py'),
                        'server_name': 'scikiq-mcp-autoAPI',
                        'auto_restart': True
                    }
                }
            },
            'instructions': {
                'step_1': 'Generate your MCP server using the main interface',
                'step_2': 'Call POST /api/auto-deploy-mcp with server path',
                'step_3': 'Claude Desktop will restart automatically',
                'step_4': 'Start chatting with your MCP tools!'
            }
        })

    @app.route('/api/auto-deploy-mcp', methods=['POST'])
    def auto_deploy_mcp():
        """Automatically deploy MCP server to Claude Desktop with YAML tools"""
        try:
            from auto_deploy_mcp import MCPAutoDeployer

            data = request.get_json()
            mcp_server_path = data.get('server_path')
            yaml_tools_path = data.get('yaml_path')  # Optional YAML tools file
            server_name = data.get('server_name', 'scikiq-mcp-autoAPI')
            auto_restart = data.get('auto_restart', True)

            print(f"[DEBUG] Received server_path from frontend: {repr(mcp_server_path)}")
            print(f"[DEBUG] Server name: {server_name}")

            if not mcp_server_path:
                return jsonify({
                    'success': False,
                    'error': 'No server_path provided'
                }), 400

            deployer = MCPAutoDeployer()
            result = deployer.deploy_mcp_server(
                mcp_server_path=mcp_server_path,
                yaml_tools_path=yaml_tools_path,
                server_name=server_name,
                auto_restart=auto_restart
            )

            if result['success']:
                return jsonify(result)
            else:
                return jsonify(result), 500

        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/parse-swagger', methods=['POST'])
    def mcp_parse_swagger():
        """Parse Swagger/OpenAPI specification and extract endpoints"""
        try:
            from swagger_parser import SwaggerParser

            data = request.get_json()
            swagger_url = data.get('swagger_url', '')
            api_base_url = data.get('api_base_url', '')

            if not swagger_url:
                return jsonify({
                    'success': False,
                    'error': 'Swagger URL is required'
                }), 400

            # Default API base URL to the swagger URL's base if not provided
            if not api_base_url:
                from urllib.parse import urlparse
                parsed = urlparse(swagger_url)
                api_base_url = f"{parsed.scheme}://{parsed.netloc}"

            # Extract authentication and SSL/TLS configuration
            config = {
                'auth_type': data.get('auth_type', 'none'),
                'auth_token': data.get('auth_token'),
                'auth_user': data.get('auth_user'),
                'auth_pass': data.get('auth_pass'),
                'verify_ssl': data.get('verify_ssl', True),
                'timeout': data.get('timeout', 30)
            }

            # Parse Swagger spec with configuration
            parser = SwaggerParser(swagger_url, api_base_url, **config)
            parser.fetch_swagger_spec()
            endpoints = parser.extract_endpoints()

            return jsonify({
                'success': True,
                'api_definitions': endpoints,
                'total_apis': len(endpoints),
                'api_base_url': api_base_url,
                'message': f'Successfully parsed {len(endpoints)} endpoints from Swagger spec'
            })

        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/rescan-apis', methods=['POST'])
    def rescan_apis():
        """Rescan APIs from saved source information (Swagger URL or project path)"""
        try:
            data = request.get_json()
            source_info = data.get('source_info', {})
            
            if not source_info:
                return jsonify({
                    'success': False,
                    'error': 'Source information is required'
                }), 400
            
            # Check if it's Swagger or codebase
            if 'swagger_url' in source_info:
                # Rescan from Swagger
                from swagger_parser import SwaggerParser
                swagger_url = source_info['swagger_url']
                api_base_url = source_info.get('api_base_url', '')
                
                if not api_base_url:
                    from urllib.parse import urlparse
                    parsed = urlparse(swagger_url)
                    api_base_url = f"{parsed.scheme}://{parsed.netloc}"
                
                parser = SwaggerParser(swagger_url, api_base_url)
                parser.fetch_swagger_spec()
                endpoints = parser.extract_endpoints()
                
                # Normalize Swagger endpoints to match expected format
                normalized_endpoints = []
                for endpoint in endpoints:
                    # SwaggerParser returns 'route' and 'methods' array, normalize to 'path' and 'method'
                    route = endpoint.get('route', endpoint.get('path', ''))
                    methods = endpoint.get('methods', [])
                    method = methods[0] if methods else endpoint.get('method', 'GET')
                    
                    normalized_endpoint = {
                        'path': route,
                        'method': method.upper(),
                        'summary': endpoint.get('summary', endpoint.get('docstring', '')),
                        'description': endpoint.get('description', endpoint.get('docstring', '')),
                        'parameters': endpoint.get('parameters', []),
                        'id': f"{method.upper()}_{route}".replace('/', '_').replace('{', '').replace('}', '')
                    }
                    normalized_endpoints.append(normalized_endpoint)
                
                return jsonify({
                    'success': True,
                    'api_definitions': normalized_endpoints,
                    'total_apis': len(normalized_endpoints),
                    'api_base_url': api_base_url,
                    'source_type': 'swagger'
                })
            elif 'project_path' in source_info:
                # Rescan from codebase
                from intelligent_mcp_converter import IntelligentMCPConverter
                project_path = source_info['project_path']
                source_file = source_info.get('source_file', '')
                api_base_url = source_info.get('api_base_url', 'http://localhost:5000')
                
                converter = IntelligentMCPConverter(project_path, api_base_url)
                endpoints = converter.analyze_codebase(source_file)
                
                # Convert endpoints to API definitions format
                api_definitions = []
                for endpoint in endpoints:
                    api_def = {
                        'path': endpoint.path,
                        'method': endpoint.method,
                        'summary': getattr(endpoint, 'summary', ''),
                        'description': getattr(endpoint, 'description', ''),
                        'parameters': getattr(endpoint, 'parameters', []),
                        'domain': getattr(endpoint, 'domain', 'default'),
                        'id': f"{endpoint.method}_{endpoint.path}".replace('/', '_').replace('{', '').replace('}', '')
                    }
                    api_definitions.append(api_def)
                
                return jsonify({
                    'success': True,
                    'api_definitions': api_definitions,
                    'total_apis': len(api_definitions),
                    'api_base_url': api_base_url,
                    'source_type': 'codebase'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Invalid source information. Must contain swagger_url or project_path'
                }), 400
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/swagger/tester')
    def mcp_swagger_tester():
        """Swagger API Tester with MCP Integration"""
        return render_template('swagger_tester.html')

    @app.route('/api/swagger/execute', methods=['POST'])
    def mcp_api_swagger_execute():
        """Execute API call via MCP proxy"""
        import requests
        import time

        try:
            data = request.get_json()

            base_url = data.get('base_url', 'https://petstore.swagger.io/v2')
            endpoint = data.get('endpoint', '')
            method = data.get('method', 'GET').upper()
            query_params = data.get('query_params', {})
            headers = data.get('headers', {})
            body = data.get('body')

            # Build full URL
            full_url = base_url + endpoint
            if query_params:
                params_str = '&'.join([f"{k}={v}" for k, v in query_params.items()])
                full_url += f"?{params_str}"

            print(f"[MCP SWAGGER] Executing {method} request to: {full_url}")

            # Track execution time
            start_time = time.time()

            # Execute request based on method
            if method == 'GET':
                response = requests.get(full_url, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(full_url, headers=headers, json=body, timeout=10)
            elif method == 'PUT':
                response = requests.put(full_url, headers=headers, json=body, timeout=10)
            elif method == 'DELETE':
                response = requests.delete(full_url, headers=headers, timeout=10)
            else:
                return jsonify({
                    'success': False,
                    'error': f'Unsupported HTTP method: {method}'
                }), 400

            execution_time = round((time.time() - start_time) * 1000, 2)  # ms

            # Parse response
            try:
                response_data = response.json()
            except:
                response_data = response.text

            print(f"[MCP SWAGGER] Response Status: {response.status_code}, Time: {execution_time}ms")

            return jsonify({
                'success': True,
                'status_code': response.status_code,
                'execution_time': f'{execution_time}ms',
                'data': response_data,
                'headers': dict(response.headers)
            })

        except requests.exceptions.Timeout:
            return jsonify({
                'success': False,
                'error': 'Request timeout - API took too long to respond'
            }), 408
        except requests.exceptions.ConnectionError:
            return jsonify({
                'success': False,
                'error': 'Connection error - Unable to reach API server'
            }), 503
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    
    # ==================== MCP SERVER MANAGEMENT ====================

    @app.route('/api/mcp-servers', methods=['GET'])
    def list_mcp_servers():
        """List all registered MCP servers"""
        try:
            from mcp_cleanup import MCPCleanup

            cleanup = MCPCleanup()
            result = cleanup.list_servers()

            if result['success']:
                return jsonify({
                    'success': True,
                    'servers': result['servers'],
                    'count': result.get('count', len(result['servers'])),
                    'message': result.get('message', f"Found {len(result['servers'])} MCP server(s)")
                })
            else:
                return jsonify({
                    'success': False,
                    'error': result.get('error', 'Failed to list servers')
                }), 500

        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/mcp-servers/<server_name>', methods=['DELETE'])
    def delete_mcp_server(server_name):
        """Delete a specific MCP server"""
        try:
            from mcp_cleanup import MCPCleanup

            data = request.get_json(silent=True) or {}
            delete_files = data.get('delete_files', True)
            restart_claude = data.get('restart_claude', True)

            cleanup = MCPCleanup()
            result = cleanup.delete_server(
                server_name=server_name,
                delete_files=delete_files,
                restart_claude=restart_claude
            )

            if result['success']:
                return jsonify({
                    'success': True,
                    'message': f"Successfully deleted MCP server '{server_name}'",
                    'results': result.get('results', {})
                })
            else:
                return jsonify({
                    'success': False,
                    'error': result.get('error', 'Failed to delete server')
                }), 500

        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/mcp-servers/all', methods=['DELETE'])
    def delete_all_mcp_servers():
        """Delete all MCP servers"""
        try:
            from mcp_cleanup import MCPCleanup

            data = request.get_json(silent=True) or {}
            delete_files = data.get('delete_files', True)
            restart_claude = data.get('restart_claude', True)

            cleanup = MCPCleanup()
            result = cleanup.delete_all_servers(
                delete_files=delete_files,
                restart_claude=restart_claude
            )

            if result['success']:
                return jsonify({
                    'success': True,
                    'message': f"Successfully deleted {result.get('deleted_count', 0)} MCP server(s)",
                    'deleted_count': result.get('deleted_count', 0),
                    'results': result.get('results', [])
                })
            else:
                return jsonify({
                    'success': False,
                    'error': result.get('error', 'Failed to delete servers')
                }), 500

        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/generate-database-mcp', methods=['POST'])
    def mcp_generate_database_mcp():
        """Generate database MCP server configuration and config.ini file"""
        try:
            data = request.get_json()
            server_name = data.get('server_name', 'database-mcp-server')
            server_path = data.get('server_path', '')
            connections = data.get('connections', [])
            
            # Auto-detect server path if not provided
            # Database MCP server is always at dbhandler_mcpserver/scikiq_pkg_dbutils relative to project root
            if not server_path:
                project_root = os.path.dirname(os.path.abspath(__file__))
                server_path = os.path.join(project_root, 'dbhandler_mcpserver', 'scikiq_pkg_dbutils')
            
            if not connections:
                return jsonify({
                    'success': False,
                    'error': 'At least one database connection is required'
                }), 400
            
            # Get selected tools from request
            selected_tools = data.get('selected_tools', [])
            
            # Generate config.ini content
            config_content = generate_database_config_ini(connections, selected_tools)
            
            # Save config.ini file
            config_dir = Path(server_path)
            config_path = config_dir / 'config.ini'
            
            # Ensure directory exists
            config_dir.mkdir(parents=True, exist_ok=True)
            
            # Write config file
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(config_content)
            
            # Detect Python path
            python_path = detect_python_executable()
            
            return jsonify({
                'success': True,
                'message': 'Database MCP server configuration generated successfully',
                'config_path': str(config_path),
                'server_path': str(server_path),
                'server_name': server_name,
                'python_path': python_path,
                'connections_count': len(connections)
            })
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/get-database-tools', methods=['GET'])
    def mcp_get_database_tools():
        """Get list of available database MCP tools"""
        try:
            # Define all available database tools with their categories
            tools = {
                'Connection Management': [
                    {'id': 'db_create_connection', 'name': 'Create Connection', 'description': 'Create a new database connection with the specified configuration'},
                    {'id': 'db_test_connection', 'name': 'Test Connection', 'description': 'Test database connection without creating a persistent connection'},
                    {'id': 'db_close_connection', 'name': 'Close Connection', 'description': 'Close and remove an existing database connection'},
                    {'id': 'db_list_connections', 'name': 'List Connections', 'description': 'List all active database connections'}
                ],
                'Query Operations': [
                    {'id': 'db_execute_query', 'name': 'Execute Query', 'description': 'Execute a SELECT query and return the results as structured data'},
                    {'id': 'db_execute_sql', 'name': 'Execute SQL', 'description': 'Execute SQL statements (INSERT, UPDATE, DELETE, DDL, etc.)'},
                    {'id': 'db_generate_query', 'name': 'Generate Query', 'description': 'Generate SQL query based on specified parameters'}
                ],
                'Table Operations': [
                    {'id': 'db_get_all_tables', 'name': 'Get All Tables', 'description': 'Get a list of all tables in the database'},
                    {'id': 'db_get_table_columns', 'name': 'Get Table Columns', 'description': 'Get column names and basic information for a specific table'},
                    {'id': 'db_get_table_columns_details', 'name': 'Get Table Columns Details', 'description': 'Get detailed column information including data types, constraints, etc.'},
                    {'id': 'db_read_table', 'name': 'Read Table', 'description': 'Read data from a table and return as structured data'},
                    {'id': 'db_get_table_details', 'name': 'Get Table Details', 'description': 'Get comprehensive details about a table including metadata'},
                    {'id': 'db_get_table_relationships', 'name': 'Get Table Relationships', 'description': 'Get foreign key relationships for a table'}
                ],
                'Column Operations': [
                    {'id': 'db_get_column_lov', 'name': 'Get Column LOV', 'description': 'Get list of unique values (LOV) for a specific column'},
                    {'id': 'db_get_columns_profile', 'name': 'Get Columns Profile', 'description': 'Get statistical profiling information for table columns'},
                    {'id': 'db_update_column_comment', 'name': 'Update Column Comment', 'description': 'Update the comment/description for a table column'}
                ],
                'Table Management': [
                    {'id': 'db_create_table', 'name': 'Create Table', 'description': 'Create a new table in the database'},
                    {'id': 'db_truncate_table', 'name': 'Truncate Table', 'description': 'Remove all data from a table (TRUNCATE)'},
                    {'id': 'db_create_view', 'name': 'Create View', 'description': 'Create a database view from SQL query'}
                ],
                'Data Management': [
                    {'id': 'db_get_incremental_columns', 'name': 'Get Incremental Columns', 'description': 'Get columns suitable for incremental data loading (timestamps, IDs, etc.)'},
                    {'id': 'db_fetch_delta_columns', 'name': 'Fetch Delta Columns', 'description': 'Fetch delta columns for change data capture operations'},
                    {'id': 'db_get_filtered_row_count', 'name': 'Get Filtered Row Count', 'description': 'Get count of rows matching a filter condition'}
                ]
            }
            
            return jsonify({
                'success': True,
                'tools': tools
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/update-database-config-tools', methods=['POST'])
    def update_database_config_tools():
        """Update config.ini file with selected tools"""
        try:
            data = request.get_json()
            config_path = data.get('config_path')
            selected_tools = data.get('selected_tools', [])
            
            if not config_path:
                return jsonify({
                    'success': False,
                    'error': 'Config path is required'
                }), 400
            
            # Resolve config path - handle both relative and absolute paths
            project_root = Path(__file__).parent
            project_root_str = str(project_root)
            
            # Fix malformed paths - check if path has concatenated project root (like "DAASMCP POCgaurav")
            config_path_str = str(config_path).strip()
            
            # Check for malformed path pattern: "DAASMCP POCgaurav" or similar concatenation
            if 'DAASMCP POCgaurav' in config_path_str or (project_root_str.replace(' ', '') in config_path_str.replace(' ', '') and 'dbhandler_mcpserver' in config_path_str):
                # Extract the relative part - look for "dbhandler_mcpserver" or "scikiq_pkg_dbutils"
                if 'dbhandler_mcpserver' in config_path_str:
                    idx = config_path_str.find('dbhandler_mcpserver')
                    rel_part = config_path_str[idx:]
                    config_path_str = str(project_root / rel_part.replace('\\', '/').replace('//', '/'))
                elif 'scikiq_pkg_dbutils' in config_path_str:
                    idx = config_path_str.find('scikiq_pkg_dbutils')
                    # Need to add dbhandler_mcpserver before it
                    rel_part = config_path_str[idx:]
                    config_path_str = str(project_root / 'dbhandler_mcpserver' / rel_part.replace('\\', '/').replace('//', '/'))
            
            # Normalize the path
            config_path_normalized = config_path_str.replace('\\', '/').replace('//', '/')
            
            # If path contains project root duplicated, fix it
            project_root_normalized = project_root_str.replace('\\', '/')
            if project_root_normalized in config_path_normalized and config_path_normalized.count(project_root_normalized) > 1:
                # Remove duplicate project root
                parts = config_path_normalized.split(project_root_normalized)
                config_path_normalized = project_root_normalized + ''.join(parts[1:])
            
            config_file = Path(config_path_normalized.replace('/', os.sep))
            
            # If not absolute, try relative to project root
            if not config_file.is_absolute():
                project_root = Path(__file__).parent
                config_file = (project_root / config_path_normalized).resolve()
            else:
                config_file = config_file.resolve()
            
            if not config_file.exists():
                # Try alternative paths - most common location first
                project_root = Path(__file__).parent
                standard_config_path = project_root / 'dbhandler_mcpserver' / 'scikiq_pkg_dbutils' / 'config.ini'
                
                if standard_config_path.exists():
                    config_file = standard_config_path
                    print(f"[DEBUG] Using standard config path: {config_file}")
                else:
                    # Try other alternatives
                    alt_paths = [
                        Path(config_path_normalized).resolve() if Path(config_path_normalized).is_absolute() else None,
                        project_root / config_path_normalized if not Path(config_path_normalized).is_absolute() else None,
                    ]
                    
                    # Filter out None values
                    alt_paths = [p for p in alt_paths if p is not None]
                    
                    found = False
                    for alt_path in alt_paths:
                        try:
                            alt_path_resolved = alt_path.resolve()
                            if alt_path_resolved.exists():
                                config_file = alt_path_resolved
                                found = True
                                break
                        except:
                            continue
                    
                    if not found:
                        return jsonify({
                            'success': False,
                            'error': f'Config file not found. Original: {config_path}. Tried standard location: {standard_config_path}. Please ensure config.ini exists.'
                        }), 404
            
            # Read existing config file to preserve format
            with open(config_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse config for validation
            import configparser
            config = configparser.ConfigParser()
            config.optionxform = str  # Preserve case sensitivity
            config.read_string(content)
            
            # Ensure SERVER section exists
            if 'SERVER' not in config:
                config.add_section('SERVER')
            
            # Update ENABLED_TOOLS value
            enabled_tools_value = ','.join(selected_tools) if selected_tools and len(selected_tools) > 0 else None
            
            # Update content by finding/replacing or adding SERVER section
            lines = content.split('\n')
            new_lines = []
            in_server_section = False
            enabled_tools_found = False
            i = 0
            
            while i < len(lines):
                line = lines[i]
                stripped = line.strip()
                
                # Check if we're entering SERVER section
                if stripped.upper() == '[SERVER]':
                    in_server_section = True
                    new_lines.append('[SERVER]')
                    i += 1
                    # Process SERVER section content
                    while i < len(lines) and (not lines[i].strip() or not lines[i].strip().startswith('[')):
                        if i >= len(lines):
                            break
                        current_line = lines[i]
                        current_stripped = current_line.strip().upper()
                        
                        # Skip existing ENABLED_TOOLS line
                        if current_stripped.startswith('ENABLED_TOOLS'):
                            enabled_tools_found = True
                            if enabled_tools_value:
                                new_lines.append(f"ENABLED_TOOLS={enabled_tools_value}")
                            i += 1
                            continue
                        
                        # Skip empty lines at end of section
                        if not current_stripped and i < len(lines) - 1:
                            next_stripped = lines[i + 1].strip() if i + 1 < len(lines) else ''
                            if next_stripped and next_stripped.startswith('['):
                                i += 1
                                continue
                        
                        new_lines.append(current_line)
                        i += 1
                    
                    # Add ENABLED_TOOLS if not found and we have tools
                    if not enabled_tools_found and enabled_tools_value:
                        new_lines.append(f"ENABLED_TOOLS={enabled_tools_value}")
                    
                    in_server_section = False
                    continue
                
                new_lines.append(line)
                i += 1
            
            # If SERVER section wasn't found, add it at the end
            if not in_server_section and enabled_tools_value:
                # Remove trailing empty lines
                while new_lines and not new_lines[-1].strip():
                    new_lines.pop()
                # Add SERVER section
                if new_lines and new_lines[-1].strip():
                    new_lines.append('')
                new_lines.append('[SERVER]')
                new_lines.append(f"ENABLED_TOOLS={enabled_tools_value}")
            
            # Write updated content
            with open(config_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(new_lines))
            
            return jsonify({
                'success': True,
                'message': f'Updated config.ini with {len(selected_tools)} enabled tools',
                'config_path': str(config_file)
            })
            
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"[ERROR] Failed to update config: {str(e)}")
            print(f"[ERROR] Traceback: {error_trace}")
            return jsonify({
                'success': False,
                'error': str(e),
                'traceback': error_trace
            }), 500

    @app.route('/api/get-database-config', methods=['GET'])
    def mcp_get_database_config():
        """Get the content of a database config.ini file"""
        try:
            import base64
            from urllib.parse import unquote
            
            config_path = request.args.get('path')
            is_encoded = request.args.get('encoded', 'false').lower() == 'true'
            
            if not config_path:
                return jsonify({
                    'success': False,
                    'error': 'Path parameter is required'
                }), 400
            
            # Decode base64 if encoded, otherwise use URL decode
            if is_encoded:
                try:
                    config_path = base64.b64decode(config_path).decode('utf-8')
                except Exception as e:
                    return jsonify({
                        'success': False,
                        'error': f'Invalid encoded path: {str(e)}'
                    }), 400
            else:
                # Properly decode the URL-encoded path
                config_path = unquote(config_path)
            
            # Normalize path separators for Windows
            if os.name == 'nt':  # Windows
                config_path = config_path.replace('/', '\\')
            
            config_path = Path(config_path)
            
            if not config_path.exists():
                return jsonify({
                    'success': False,
                    'error': f'Config file not found: {config_path}'
                }), 404
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config_content = f.read()
            
            return jsonify({
                'success': True,
                'config_content': config_content
            })
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    # ==================== SAVED CONFIGURATIONS API (SQLite3) ====================
    
    def get_db_path():
        """Get the path to the SQLite database file"""
        import os
        # Use absolute path to ensure database is created in the correct location
        db_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(db_dir, 'saved_mcp_configs.db')
        return db_path
    
    def init_db():
        """Initialize the SQLite database and create tables if they don't exist"""
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create table for saved configurations
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS saved_configs (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                name TEXT NOT NULL,
                config_data TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        ''')
        
        # Create table for deployment history
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS deployments (
                id TEXT PRIMARY KEY,
                config_id TEXT NOT NULL,
                platform TEXT NOT NULL,
                deployment_data TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'unknown',
                deployed_at TEXT NOT NULL,
                FOREIGN KEY (config_id) REFERENCES saved_configs(id) ON DELETE CASCADE
            )
        ''')
        
        # Add status column if it doesn't exist (for existing databases)
        try:
            cursor.execute('ALTER TABLE deployments ADD COLUMN status TEXT DEFAULT "unknown"')
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        # Create indexes for faster queries
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_config_type ON saved_configs(type)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_deployment_config_id ON deployments(config_id)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_deployment_platform ON deployments(platform)
        ''')
        
        conn.commit()
        conn.close()
    
    def get_db_connection():
        """Get a database connection"""
        init_db()  # Ensure database is initialized
        return sqlite3.connect(get_db_path())
    
    # Initialize database when routes are set up
    try:
        init_db()
        print("[INFO] Database initialized successfully")
    except Exception as e:
        print(f"[ERROR] Failed to initialize database: {e}")
        import traceback
        traceback.print_exc()
    
    @app.route('/api/saved-configs', methods=['GET'])
    def get_saved_configs():
        """Get all saved MCP server configurations"""
        try:
            print(f"[DEBUG] get_saved_configs called, db path: {get_db_path()}")
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, type, name, config_data, created_at, updated_at
                FROM saved_configs
                ORDER BY updated_at DESC
            ''')
            
            rows = cursor.fetchall()
            conn.close()
            
            configs = []
            for row in rows:
                config_id, config_type, name, config_data_json, created_at, updated_at = row
                try:
                    config_data = json.loads(config_data_json) if config_data_json else {}
                except (json.JSONDecodeError, TypeError) as e:
                    print(f"[WARNING] Failed to parse config_data for config {config_id}: {e}")
                    config_data = {}
                
                configs.append({
                    'id': config_id,
                    'type': config_type,
                    'name': name,
                    'config': config_data,
                    'created_at': created_at,
                    'updated_at': updated_at
                })
            
            print(f"[DEBUG] Returning {len(configs)} configurations")
            return jsonify({
                'success': True,
                'configs': configs
            })
        except Exception as e:
            import traceback
            print(f"[ERROR] Exception in get_saved_configs: {e}")
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/saved-configs', methods=['POST'])
    def save_mcp_config():
        """Save an MCP server configuration"""
        try:
            data = request.get_json()
            config_type = data.get('type')  # 'swagger', 'codebase', or 'database'
            config_name = data.get('name', 'Untitled Configuration')
            config_data = data.get('config', {})
            
            if not config_type:
                return jsonify({
                    'success': False,
                    'error': 'Configuration type is required'
                }), 400
            
            # Generate unique ID
            config_id = str(int(time.time() * 1000))
            created_at = datetime.now().isoformat()
            updated_at = created_at
            
            # Convert config_data to JSON string
            config_data_json = json.dumps(config_data, ensure_ascii=False)
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO saved_configs (id, type, name, config_data, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (config_id, config_type, config_name, config_data_json, created_at, updated_at))
            
            conn.commit()
            conn.close()
            
            new_config = {
                'id': config_id,
                'type': config_type,
                'name': config_name,
                'config': config_data,
                'created_at': created_at,
                'updated_at': updated_at
            }
            
            return jsonify({
                'success': True,
                'config': new_config,
                'message': 'Configuration saved successfully'
            })
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/saved-configs/<config_id>', methods=['PUT'])
    def update_saved_config(config_id):
        """Update a saved MCP server configuration"""
        try:
            data = request.get_json()
            config_name = data.get('name')
            config_data = data.get('config')
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Check if config exists
            cursor.execute('SELECT id FROM saved_configs WHERE id = ?', (config_id,))
            if not cursor.fetchone():
                conn.close()
                return jsonify({
                    'success': False,
                    'error': 'Configuration not found'
                }), 404
            
            # Build update query dynamically
            updates = []
            params = []
            
            if config_name:
                updates.append('name = ?')
                params.append(config_name)
            
            if config_data:
                updates.append('config_data = ?')
                params.append(json.dumps(config_data, ensure_ascii=False))
            
            if not updates:
                conn.close()
                return jsonify({
                    'success': False,
                    'error': 'No fields to update'
                }), 400
            
            updates.append('updated_at = ?')
            params.append(datetime.now().isoformat())
            params.append(config_id)  # For WHERE clause
            
            query = f'UPDATE saved_configs SET {", ".join(updates)} WHERE id = ?'
            cursor.execute(query, params)
            conn.commit()
            conn.close()
            
            return jsonify({
                'success': True,
                'message': 'Configuration updated successfully'
            })
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/saved-configs/<config_id>/yaml', methods=['GET'])
    def get_config_yaml(config_id):
        """Get YAML file content for a saved configuration"""
        try:
            print(f"[DEBUG] get_config_yaml called for config_id: {config_id}")
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Get config
            cursor.execute('SELECT config_data, type FROM saved_configs WHERE id = ?', (config_id,))
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                print(f"[DEBUG] Configuration {config_id} not found in database")
                return jsonify({
                    'success': False,
                    'error': 'Configuration not found'
                }), 404
            
            config_data_json, config_type = row
            print(f"[DEBUG] Config type: {config_type}, Config data: {config_data_json[:200] if config_data_json else 'None'}...")
            
            try:
                config_data = json.loads(config_data_json) if config_data_json else {}
            except json.JSONDecodeError as e:
                print(f"[DEBUG] Failed to parse config_data JSON: {e}")
                return jsonify({
                    'success': False,
                    'error': f'Invalid configuration data format: {str(e)}'
                }), 500
            
            print(f"[DEBUG] Parsed config_data keys: {list(config_data.keys())}")
            
            # Get YAML file path
            yaml_file = config_data.get('yaml_file')
            server_path = config_data.get('server_path', '')
            
            # If no YAML file, try to construct YAML data from config_data
            if not yaml_file:
                print(f"[DEBUG] No yaml_file found in config_data. Available keys: {list(config_data.keys())}")
                
                # For database configurations or configurations without YAML files,
                # try to construct a basic YAML structure from config_data
                if config_type == 'database':
                    return jsonify({
                        'success': False,
                        'error': 'Database configurations cannot be edited through YAML. Please use the database configuration editor.'
                    }), 400
                
                # For swagger/codebase configs without YAML, create empty structure
                yaml_data = {
                    'base_url': config_data.get('base_url', 'http://localhost:9321'),
                    'tools': config_data.get('tools', []),
                    'generated_at': config_data.get('generated_at', datetime.now().isoformat())
                }
                
                return jsonify({
                    'success': True,
                    'yaml_content': yaml.dump(yaml_data, default_flow_style=False),
                    'yaml_data': yaml_data,
                    'yaml_path': None,
                    'note': 'YAML file not found, using configuration data'
                })
            
            print(f"[DEBUG] YAML file from config: {yaml_file}")
            print(f"[DEBUG] Server path from config: {server_path}")
            
            # Construct full path if yaml_file is just a filename
            if not os.path.isabs(yaml_file):
                # yaml_file is just a filename, need to combine with server_path
                if server_path:
                    yaml_file = os.path.join(server_path, yaml_file)
                    print(f"[DEBUG] Constructed full YAML path: {yaml_file}")
                else:
                    # Try to find in generated_servers directory
                    generated_servers_dir = os.path.join(os.getcwd(), 'generated_servers')
                    if os.path.exists(generated_servers_dir):
                        yaml_file = os.path.join(generated_servers_dir, yaml_file)
                        print(f"[DEBUG] Using generated_servers directory: {yaml_file}")
                    else:
                        print(f"[DEBUG] WARNING: Cannot construct full path, server_path is missing")
            
            # Normalize path (handle Windows backslashes)
            yaml_file = os.path.normpath(yaml_file)
            print(f"[DEBUG] Final normalized YAML file path: {yaml_file}")
            
            # Check if file exists
            if not os.path.exists(yaml_file):
                print(f"[DEBUG] YAML file does not exist at: {yaml_file}")
                # Try alternative locations
                alt_paths = [
                    os.path.join(os.getcwd(), 'generated_servers', os.path.basename(yaml_file)),
                    os.path.join(os.getcwd(), os.path.basename(yaml_file)),
                ]
                
                found_path = None
                for alt_path in alt_paths:
                    if os.path.exists(alt_path):
                        found_path = alt_path
                        print(f"[DEBUG] Found YAML file at alternative path: {found_path}")
                        break
                
                if found_path:
                    yaml_file = found_path
                else:
                    print(f"[DEBUG] YAML file not found in any location, using config_data fallback")
                    # Try to construct from config_data as fallback
                    yaml_data = {
                        'base_url': config_data.get('base_url', 'http://localhost:9321'),
                        'tools': config_data.get('tools', []),
                        'generated_at': config_data.get('generated_at', datetime.now().isoformat())
                    }
                    
                    return jsonify({
                        'success': True,
                        'yaml_content': yaml.dump(yaml_data, default_flow_style=False),
                        'yaml_data': yaml_data,
                        'yaml_path': yaml_file,
                        'note': 'YAML file not found at path, using configuration data'
                    })
            
            # Read YAML content
            try:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    yaml_content = f.read()
            except Exception as e:
                print(f"[DEBUG] Failed to read YAML file: {e}")
                return jsonify({
                    'success': False,
                    'error': f'Failed to read YAML file: {str(e)}'
                }), 500
            
            # Parse YAML to get structure
            try:
                yaml_data = yaml.safe_load(yaml_content)
                if not yaml_data:
                    yaml_data = {}
                
                print(f"[DEBUG] Parsed YAML data keys: {list(yaml_data.keys())}")
                print(f"[DEBUG] YAML data type: {type(yaml_data)}")
                
                # Ensure tools is a list
                if 'tools' in yaml_data:
                    tools = yaml_data['tools']
                    print(f"[DEBUG] Tools found in YAML: {len(tools) if isinstance(tools, list) else 'not a list'}")
                    print(f"[DEBUG] Tools type: {type(tools)}")
                    if isinstance(tools, list):
                        print(f"[DEBUG] Number of tools: {len(tools)}")
                        if tools:
                            print(f"[DEBUG] First tool keys: {list(tools[0].keys()) if isinstance(tools[0], dict) else 'not a dict'}")
                            print(f"[DEBUG] First tool sample: {str(tools[0])[:200] if tools else 'empty list'}")
                        # Ensure tools list is valid
                        if len(tools) == 0:
                            print(f"[DEBUG] Tools list is empty")
                    else:
                        print(f"[DEBUG] Tools is not a list, type is: {type(tools)}, value: {tools}")
                        # Try to convert to list if it's a dict or other structure
                        if isinstance(tools, dict):
                            print(f"[DEBUG] Tools is a dict, converting values to list")
                            yaml_data['tools'] = list(tools.values()) if tools else []
                        elif tools is None:
                            print(f"[DEBUG] Tools is None, setting to empty list")
                            yaml_data['tools'] = []
                        else:
                            print(f"[DEBUG] Tools is unexpected type, setting to empty list")
                            yaml_data['tools'] = []
                else:
                    print(f"[DEBUG] No 'tools' key found in YAML data. Available keys: {list(yaml_data.keys())}")
                    # Check if tools might be under a different key
                    if 'tool' in yaml_data:
                        print(f"[DEBUG] Found 'tool' key (singular), converting to 'tools' list")
                        yaml_data['tools'] = [yaml_data['tool']] if yaml_data['tool'] else []
                    else:
                        print(f"[DEBUG] Creating empty tools list")
                        yaml_data['tools'] = []
                
                # Final validation - ensure tools is always a list
                if not isinstance(yaml_data.get('tools'), list):
                    print(f"[DEBUG] WARNING: tools is not a list after processing, fixing...")
                    yaml_data['tools'] = []
                    
            except Exception as e:
                print(f"[DEBUG] Failed to parse YAML: {e}")
                import traceback
                traceback.print_exc()
                return jsonify({
                    'success': False,
                    'error': f'Failed to parse YAML file: {str(e)}'
                }), 500
            
            print(f"[DEBUG] Final YAML data tools count: {len(yaml_data.get('tools', []))}")
            
            return jsonify({
                'success': True,
                'yaml_content': yaml_content,
                'yaml_data': yaml_data,
                'yaml_path': yaml_file
            })
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/saved-configs/<config_id>/yaml', methods=['PUT'])
    def update_config_yaml(config_id):
        """Update YAML file and save as new version"""
        try:
            data = request.get_json()
            yaml_data = data.get('yaml_data')
            version_note = data.get('version_note', 'Updated configuration')
            selected_api_ids = data.get('selected_api_ids', [])
            
            if not yaml_data:
                return jsonify({
                    'success': False,
                    'error': 'YAML data is required'
                }), 400
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Get original config
            cursor.execute('SELECT config_data, type, name FROM saved_configs WHERE id = ?', (config_id,))
            row = cursor.fetchone()
            
            if not row:
                conn.close()
                return jsonify({
                    'success': False,
                    'error': 'Configuration not found'
                }), 404
            
            config_data_json, config_type, config_name = row
            config_data = json.loads(config_data_json) if config_data_json else {}
            
            # Get original YAML path
            original_yaml_file = config_data.get('yaml_file')
            if not original_yaml_file:
                conn.close()
                return jsonify({
                    'success': False,
                    'error': 'Original YAML file path not found'
                }), 400
            
            # Generate new YAML file path with version timestamp
            original_path = Path(original_yaml_file)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            new_yaml_filename = f"{original_path.stem}_v{timestamp}{original_path.suffix}"
            new_yaml_path = original_path.parent / new_yaml_filename
            
            # Write new YAML file
            with open(new_yaml_path, 'w', encoding='utf-8') as f:
                yaml.dump(yaml_data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
            
            # Create new version of config
            new_config_id = str(int(time.time() * 1000))
            created_at = datetime.now().isoformat()
            
            # Update config_data with new YAML path and selected API IDs
            config_data['yaml_file'] = str(new_yaml_path)
            config_data['version_note'] = version_note
            config_data['original_config_id'] = config_id
            config_data['tool_count'] = len(yaml_data.get('tools', []))
            if selected_api_ids:
                config_data['selected_api_ids'] = selected_api_ids
            
            config_data_json = json.dumps(config_data, ensure_ascii=False)
            
            cursor.execute('''
                INSERT INTO saved_configs (id, type, name, config_data, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (new_config_id, config_type, f"{config_name} (v{timestamp})", config_data_json, created_at, created_at))
            
            conn.commit()
            conn.close()
            
            return jsonify({
                'success': True,
                'new_config_id': new_config_id,
                'yaml_path': str(new_yaml_path),
                'message': 'Configuration updated and saved as new version'
            })
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/saved-configs/<config_id>/refresh-deployment', methods=['POST'])
    def refresh_deployment_yaml(config_id):
        """Refresh deployed instance with updated YAML"""
        import logging
        logger = logging.getLogger(__name__)
        
        print(f"[REFRESH-DEPLOYMENT] ========== START ==========")
        print(f"[REFRESH-DEPLOYMENT] Route called: POST /api/saved-configs/<config_id>/refresh-deployment")
        print(f"[REFRESH-DEPLOYMENT] Config ID: {config_id}")
        print(f"[REFRESH-DEPLOYMENT] Request method: {request.method}")
        print(f"[REFRESH-DEPLOYMENT] Request URL: {request.url}")
        print(f"[REFRESH-DEPLOYMENT] Request headers: {dict(request.headers)}")
        
        try:
            data = request.get_json()
            print(f"[REFRESH-DEPLOYMENT] Request JSON data: {data}")
            
            deployment_id = data.get('deployment_id') if data else None
            print(f"[REFRESH-DEPLOYMENT] Extracted deployment_id: {deployment_id}")
            
            if not deployment_id:
                print(f"[REFRESH-DEPLOYMENT] ERROR: Deployment ID is missing")
                return jsonify({
                    'success': False,
                    'error': 'Deployment ID is required'
                }), 400
            
            print(f"[REFRESH-DEPLOYMENT] Step 1: Connecting to database...")
            conn = get_db_connection()
            cursor = conn.cursor()
            print(f"[REFRESH-DEPLOYMENT] Database connection established")
            
            # First, check if this config is a versioned config and get original config_id
            print(f"[REFRESH-DEPLOYMENT] Step 2: Checking if config {config_id} exists and is versioned...")
            cursor.execute('SELECT config_data FROM saved_configs WHERE id = ?', (config_id,))
            config_row = cursor.fetchone()
            original_config_id = config_id
            
            if config_row:
                print(f"[REFRESH-DEPLOYMENT] Config found in database")
                config_data_json = config_row[0]
                if config_data_json:
                    try:
                        config_data = json.loads(config_data_json)
                        original_config_id = config_data.get('original_config_id', config_id)
                        print(f"[REFRESH-DEPLOYMENT] Original config_id: {original_config_id}, Current config_id: {config_id}")
                        if original_config_id != config_id:
                            print(f"[REFRESH-DEPLOYMENT] This is a versioned config (v{config_id} of original {original_config_id})")
                    except Exception as e:
                        print(f"[REFRESH-DEPLOYMENT] WARNING: Failed to parse config_data JSON: {e}")
            else:
                print(f"[REFRESH-DEPLOYMENT] WARNING: Config {config_id} not found in saved_configs table")
            
            # Get deployment details - check both current config_id and original_config_id
            # This handles cases where config was saved as a new version
            print(f"[REFRESH-DEPLOYMENT] Step 3: Searching for deployment...")
            print(f"[REFRESH-DEPLOYMENT] Query parameters: deployment_id={deployment_id}, config_id={config_id}, original_config_id={original_config_id}")
            
            cursor.execute('''
                SELECT platform, deployment_data, status, config_id
                FROM deployments
                WHERE id = ? AND (config_id = ? OR config_id = ?)
            ''', (deployment_id, config_id, original_config_id))
            
            deployment_row = cursor.fetchone()
            
            # Also check what deployments exist for debugging
            cursor.execute('SELECT id, config_id, platform, status FROM deployments WHERE id = ?', (deployment_id,))
            all_matching_deployments = cursor.fetchall()
            print(f"[REFRESH-DEPLOYMENT] All deployments with id={deployment_id}: {all_matching_deployments}")
            
            if not deployment_row:
                conn.close()
                print(f"[REFRESH-DEPLOYMENT] ERROR: Deployment not found!")
                print(f"[REFRESH-DEPLOYMENT] Searched for: deployment_id={deployment_id}, config_id={config_id}, original_config_id={original_config_id}")
                print(f"[REFRESH-DEPLOYMENT] Found {len(all_matching_deployments)} deployment(s) with matching deployment_id but different config_id")
                return jsonify({
                    'success': False,
                    'error': f'Deployment not found for deployment_id: {deployment_id}, config_id: {config_id}',
                    'debug_info': {
                        'deployment_id': deployment_id,
                        'config_id': config_id,
                        'original_config_id': original_config_id,
                        'matching_deployments': [{'id': d[0], 'config_id': d[1], 'platform': d[2], 'status': d[3]} for d in all_matching_deployments]
                    }
                }), 404
            
            platform_name, deployment_data_json, status, deployment_config_id = deployment_row
            print(f"[REFRESH-DEPLOYMENT] Deployment found successfully!")
            print(f"[REFRESH-DEPLOYMENT] Platform: {platform_name}")
            print(f"[REFRESH-DEPLOYMENT] Status: {status}")
            print(f"[REFRESH-DEPLOYMENT] Deployment config_id: {deployment_config_id}")
            print(f"[REFRESH-DEPLOYMENT] Deployment data (first 200 chars): {str(deployment_data_json)[:200] if deployment_data_json else 'None'}...")
            
            print(f"[REFRESH-DEPLOYMENT] Step 4: Parsing deployment data...")
            try:
                deployment_data = json.loads(deployment_data_json) if deployment_data_json else {}
                print(f"[REFRESH-DEPLOYMENT] Deployment data parsed successfully")
                print(f"[REFRESH-DEPLOYMENT] Deployment data keys: {list(deployment_data.keys())}")
                print(f"[REFRESH-DEPLOYMENT] Public IP: {deployment_data.get('public_ip', 'Not found')}")
                print(f"[REFRESH-DEPLOYMENT] Instance ID: {deployment_data.get('instance_id', 'Not found')}")
                print(f"[REFRESH-DEPLOYMENT] Domain: {deployment_data.get('domain', 'Not found')}")
            except Exception as e:
                print(f"[REFRESH-DEPLOYMENT] ERROR: Failed to parse deployment_data JSON: {e}")
                conn.close()
                return jsonify({
                    'success': False,
                    'error': f'Failed to parse deployment data: {str(e)}'
                }), 500
            
            # Get config to find latest YAML path
            # Get the current config
            print(f"[REFRESH-DEPLOYMENT] Step 5: Fetching config data for YAML path...")
            cursor.execute('''
                SELECT config_data, name FROM saved_configs 
                WHERE id = ?
            ''', (config_id,))
            
            config_row = cursor.fetchone()
            
            if not config_row:
                conn.close()
                print(f"[REFRESH-DEPLOYMENT] ERROR: Configuration {config_id} not found in saved_configs")
                return jsonify({
                    'success': False,
                    'error': 'Configuration not found'
                }), 404
            
            config_data_json, config_name = config_row
            print(f"[REFRESH-DEPLOYMENT] Config found: {config_name}")
            
            try:
                config_data = json.loads(config_data_json) if config_data_json else {}
                print(f"[REFRESH-DEPLOYMENT] Config data parsed successfully")
                print(f"[REFRESH-DEPLOYMENT] Config data keys: {list(config_data.keys())}")
            except Exception as e:
                print(f"[REFRESH-DEPLOYMENT] ERROR: Failed to parse config_data JSON: {e}")
                conn.close()
                return jsonify({
                    'success': False,
                    'error': f'Failed to parse configuration data: {str(e)}'
                }), 500
            
            # Check if this is a versioned config and find the latest version
            # original_config_id is stored in config_data JSON, not as a column
            print(f"[REFRESH-DEPLOYMENT] Step 6: Checking for versioned config...")
            original_config_id_from_data = config_data.get('original_config_id')
            print(f"[REFRESH-DEPLOYMENT] original_config_id from config_data: {original_config_id_from_data}")
            
            if original_config_id_from_data:
                print(f"[REFRESH-DEPLOYMENT] This is a versioned config, searching for latest version...")
                # This is a versioned config, find the latest version
                # Search for configs with this original_config_id in their JSON data
                cursor.execute('''
                    SELECT config_data, name, created_at FROM saved_configs 
                    WHERE id = ? OR config_data LIKE ?
                    ORDER BY created_at DESC
                    LIMIT 1
                ''', (original_config_id_from_data, f'%"original_config_id":"{original_config_id_from_data}"%'))
                
                latest_row = cursor.fetchone()
                if latest_row:
                    config_data_json, config_name, created_at = latest_row
                    print(f"[REFRESH-DEPLOYMENT] Latest version found: {config_name}, created_at: {created_at}")
                    try:
                        config_data = json.loads(config_data_json) if config_data_json else {}
                        print(f"[REFRESH-DEPLOYMENT] Latest version config_data parsed successfully")
                    except Exception as e:
                        print(f"[REFRESH-DEPLOYMENT] ERROR: Failed to parse latest version config_data: {e}")
                else:
                    print(f"[REFRESH-DEPLOYMENT] No newer version found, using current config")
            else:
                print(f"[REFRESH-DEPLOYMENT] Not a versioned config, using current config")
            
            conn.close()
            print(f"[REFRESH-DEPLOYMENT] Database connection closed")
            
            print(f"[REFRESH-DEPLOYMENT] Step 7: Extracting YAML file path...")
            yaml_file = config_data.get('yaml_file')
            print(f"[REFRESH-DEPLOYMENT] YAML file from config_data: {yaml_file}")
            
            # If YAML file doesn't exist, try to find it in generated_servers directory
            if yaml_file:
                print(f"[REFRESH-DEPLOYMENT] Checking if YAML file exists: {yaml_file}")
                if os.path.exists(yaml_file):
                    print(f"[REFRESH-DEPLOYMENT] YAML file found at: {yaml_file}")
                else:
                    print(f"[REFRESH-DEPLOYMENT] YAML file not found at original path, searching alternatives...")
                    # Try to find in generated_servers directory
                    yaml_filename = os.path.basename(yaml_file)
                    potential_paths = [
                        os.path.join('generated_servers', yaml_filename),
                        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'generated_servers', yaml_filename)
                    ]
                    print(f"[REFRESH-DEPLOYMENT] Searching in potential paths: {potential_paths}")
                    for path in potential_paths:
                        print(f"[REFRESH-DEPLOYMENT] Checking: {path}")
                        if os.path.exists(path):
                            yaml_file = path
                            print(f"[REFRESH-DEPLOYMENT] YAML file found at: {yaml_file}")
                            break
                    else:
                        print(f"[REFRESH-DEPLOYMENT] YAML file not found in any potential paths")
            
            if not yaml_file or not os.path.exists(yaml_file):
                print(f"[REFRESH-DEPLOYMENT] ERROR: YAML file not found!")
                print(f"[REFRESH-DEPLOYMENT] Final yaml_file value: {yaml_file}")
                print(f"[REFRESH-DEPLOYMENT] File exists check: {os.path.exists(yaml_file) if yaml_file else 'N/A'}")
                return jsonify({
                    'success': False,
                    'error': f'YAML file not found: {yaml_file}',
                    'debug_info': {
                        'yaml_file_from_config': config_data.get('yaml_file'),
                        'yaml_file_final': yaml_file,
                        'file_exists': os.path.exists(yaml_file) if yaml_file else False,
                        'current_directory': os.getcwd()
                    }
                }), 404
            
            # Get deployment details
            print(f"[REFRESH-DEPLOYMENT] Step 8: Extracting deployment details...")
            public_ip = deployment_data.get('public_ip')
            instance_id = deployment_data.get('instance_id')
            domain = deployment_data.get('domain')
            
            print(f"[REFRESH-DEPLOYMENT] Public IP: {public_ip}")
            print(f"[REFRESH-DEPLOYMENT] Instance ID: {instance_id}")
            print(f"[REFRESH-DEPLOYMENT] Domain: {domain}")
            
            if not public_ip:
                print(f"[REFRESH-DEPLOYMENT] ERROR: Public IP not found in deployment data")
                print(f"[REFRESH-DEPLOYMENT] Available deployment_data keys: {list(deployment_data.keys())}")
                return jsonify({
                    'success': False,
                    'error': 'Deployment IP not found',
                    'debug_info': {
                        'deployment_data_keys': list(deployment_data.keys()),
                        'deployment_data': deployment_data
                    }
                }), 400
            
            print(f"[REFRESH-DEPLOYMENT] Step 9: Preparing YAML refresh...")
            print(f"[REFRESH-DEPLOYMENT] Platform: {platform_name}")
            print(f"[REFRESH-DEPLOYMENT] Target IP: {public_ip}")
            print(f"[REFRESH-DEPLOYMENT] YAML file to deploy: {yaml_file}")
            
            # Implement actual YAML refresh on deployed instance
            print(f"[REFRESH-DEPLOYMENT] Step 10: Connecting to instance via SSH...")
            
            # Get SSH credentials from deployment data and original config
            ssh_username = None
            ssh_password = None
            ssh_key_path = None
            
            print(f"[REFRESH-DEPLOYMENT] Step 10a: Extracting SSH credentials...")
            print(f"[REFRESH-DEPLOYMENT] Checking deployment_data for credentials...")
            
            # Check for admin credentials (AWS/Azure deployments)
            admin_credentials = deployment_data.get('admin_credentials', {})
            print(f"[REFRESH-DEPLOYMENT] admin_credentials: {admin_credentials}")
            if admin_credentials:
                ssh_username = admin_credentials.get('username') or admin_credentials.get('user')
                ssh_password = admin_credentials.get('password')
                print(f"[REFRESH-DEPLOYMENT] Using admin credentials: username={ssh_username}")
            
            # Check for SSH credentials (remote deployments)
            if not ssh_username:
                ssh_username = deployment_data.get('ssh_username') or deployment_data.get('username')
                ssh_password = deployment_data.get('ssh_password') or deployment_data.get('password')
                ssh_key_path = deployment_data.get('ssh_key_path') or deployment_data.get('key_path')
                print(f"[REFRESH-DEPLOYMENT] Using SSH credentials from deployment_data: username={ssh_username}, has_password={bool(ssh_password)}, has_key={bool(ssh_key_path)}")
            
            # For AWS/Azure, check original config_data for SSH key or credentials
            if platform_name.upper() in ['AWS', 'AZURE']:
                print(f"[REFRESH-DEPLOYMENT] Checking original config_data for AWS/Azure credentials...")
                print(f"[REFRESH-DEPLOYMENT] config_data keys: {list(config_data.keys())}")
                
                # Check for SSH key path in config_data
                if not ssh_key_path:
                    ssh_key_path = config_data.get('ssh_key_path') or config_data.get('key_path') or config_data.get('key_file')
                    if ssh_key_path:
                        print(f"[REFRESH-DEPLOYMENT] Found SSH key path in config_data: {ssh_key_path}")
                
                # Check for AWS access keys (we might need to use AWS Systems Manager Session Manager)
                aws_access_key = config_data.get('access_key') or config_data.get('aws_access_key')
                aws_secret_key = config_data.get('secret_key') or config_data.get('aws_secret_key')
                aws_region = config_data.get('region') or deployment_data.get('region')
                
                if aws_access_key and aws_secret_key and aws_region:
                    print(f"[REFRESH-DEPLOYMENT] Found AWS credentials in config_data")
                    print(f"[REFRESH-DEPLOYMENT] AWS Region: {aws_region}")
                    # We can use AWS Systems Manager Session Manager as fallback if SSH key is not available
                    # But for now, we'll try to find the key first
                
                # Check serverConfig for nested credentials
                server_config = config_data.get('serverConfig', {})
                if server_config and isinstance(server_config, dict):
                    print(f"[REFRESH-DEPLOYMENT] Checking serverConfig for credentials...")
                    if not ssh_key_path:
                        ssh_key_path = server_config.get('ssh_key_path') or server_config.get('key_path')
                    if not ssh_username:
                        ssh_username = server_config.get('ssh_username') or server_config.get('username')
                    if not ssh_password:
                        ssh_password = server_config.get('ssh_password') or server_config.get('password')
            
            # Default username for AWS EC2 (Ubuntu AMI)
            if not ssh_username and platform_name.upper() == 'AWS':
                ssh_username = 'ubuntu'
                print(f"[REFRESH-DEPLOYMENT] Using default AWS username: ubuntu")
            
            # Default username for Azure VM (Ubuntu)
            if not ssh_username and platform_name.upper() == 'AZURE':
                ssh_username = 'azureuser'
                print(f"[REFRESH-DEPLOYMENT] Using default Azure username: azureuser")
            
            if not ssh_username:
                print(f"[REFRESH-DEPLOYMENT] ERROR: No SSH username found")
                return jsonify({
                    'success': False,
                    'error': 'SSH username not found in deployment data or config',
                    'debug_info': {
                        'deployment_data_keys': list(deployment_data.keys()),
                        'config_data_keys': list(config_data.keys()),
                        'admin_credentials': admin_credentials,
                        'platform': platform_name
                    }
                }), 400
            
            # For AWS, check deployment_data for key_name first, then try to get from EC2
            if not ssh_password and not ssh_key_path and platform_name.upper() == 'AWS':
                # First check if key_name is stored in deployment_data
                key_name_from_deployment = deployment_data.get('key_name')
                print(f"[REFRESH-DEPLOYMENT] Key name from deployment_data: {key_name_from_deployment}")
                
                if key_name_from_deployment:
                    # Try common locations for PEM files using the stored key name
                    common_key_paths = [
                        os.path.expanduser(f'~/.ssh/{key_name_from_deployment}.pem'),
                        os.path.expanduser(f'~/.ssh/{key_name_from_deployment}'),
                        os.path.join(os.path.expanduser('~'), 'Downloads', f'{key_name_from_deployment}.pem'),
                        os.path.join(os.path.expanduser('~'), 'Downloads', f'{key_name_from_deployment}'),
                        f'{key_name_from_deployment}.pem',
                        key_name_from_deployment
                    ]
                    
                    print(f"[REFRESH-DEPLOYMENT] Searching for SSH key using stored key_name: {key_name_from_deployment}")
                    print(f"[REFRESH-DEPLOYMENT] Searching paths: {common_key_paths}")
                    
                    for potential_path in common_key_paths:
                        if os.path.exists(potential_path):
                            ssh_key_path = potential_path
                            print(f"[REFRESH-DEPLOYMENT] Found SSH key at: {ssh_key_path}")
                            break
                    
                    if not ssh_key_path:
                        print(f"[REFRESH-DEPLOYMENT] SSH key file not found in common locations for key_name: {key_name_from_deployment}")
                
                # If still not found, try to get key pair name from EC2 instance
                if not ssh_key_path:
                    aws_access_key = config_data.get('access_key') or config_data.get('aws_access_key')
                    aws_secret_key = config_data.get('secret_key') or config_data.get('aws_secret_key')
                    aws_region = config_data.get('region') or deployment_data.get('region')
                    
                    if aws_access_key and aws_secret_key and aws_region and instance_id:
                        print(f"[REFRESH-DEPLOYMENT] No SSH key found, attempting to retrieve key_name from EC2 instance...")
                        try:
                            import boto3
                            from botocore.exceptions import ClientError
                            
                            ec2_client = boto3.client(
                                'ec2',
                                aws_access_key_id=aws_access_key,
                                aws_secret_access_key=aws_secret_key,
                                region_name=aws_region
                            )
                            
                            # Get instance details to find key pair name
                            response = ec2_client.describe_instances(InstanceIds=[instance_id])
                            if response['Reservations']:
                                instance = response['Reservations'][0]['Instances'][0]
                                key_name = instance.get('KeyName')
                                print(f"[REFRESH-DEPLOYMENT] EC2 instance key pair name: {key_name}")
                                
                                if key_name:
                                    # Try common locations for PEM files
                                    common_key_paths = [
                                        os.path.expanduser(f'~/.ssh/{key_name}.pem'),
                                        os.path.expanduser(f'~/.ssh/{key_name}'),
                                        os.path.join(os.path.expanduser('~'), 'Downloads', f'{key_name}.pem'),
                                        os.path.join(os.path.expanduser('~'), 'Downloads', f'{key_name}'),
                                        f'{key_name}.pem',
                                        key_name
                                    ]
                                    
                                    for potential_path in common_key_paths:
                                        if os.path.exists(potential_path):
                                            ssh_key_path = potential_path
                                            print(f"[REFRESH-DEPLOYMENT] Found SSH key at: {ssh_key_path}")
                                            break
                                    
                                    if not ssh_key_path:
                                        print(f"[REFRESH-DEPLOYMENT] SSH key file not found in common locations")
                                        print(f"[REFRESH-DEPLOYMENT] Searched paths: {common_key_paths}")
                        except Exception as e:
                            print(f"[REFRESH-DEPLOYMENT] WARNING: Failed to retrieve EC2 key pair info: {e}")
                
                # If still no key found, provide helpful error
                if not ssh_password and not ssh_key_path:
                    print(f"[REFRESH-DEPLOYMENT] ERROR: No SSH key found after all attempts")
                    return jsonify({
                        'success': False,
                        'error': 'SSH key not found. For AWS EC2, the SSH key (.pem file) is required to connect.',
                        'suggestion': f'Please ensure the SSH key file is available. You can manually upload the YAML file using:\nscp "{yaml_file}" ubuntu@{public_ip}:/opt/mcp-server/\nssh ubuntu@{public_ip} "sudo systemctl restart mcp-server"',
                        'debug_info': {
                            'has_password': bool(ssh_password),
                            'has_key': bool(ssh_key_path),
                            'has_aws_credentials': bool(aws_access_key and aws_secret_key),
                            'platform': platform_name,
                            'instance_id': instance_id,
                            'public_ip': public_ip,
                            'key_name': key_name if 'key_name' in locals() else None
                        }
                    }), 400
            
            if not ssh_password and not ssh_key_path:
                print(f"[REFRESH-DEPLOYMENT] ERROR: No SSH password or key found")
                return jsonify({
                    'success': False,
                    'error': 'SSH password or key not found in deployment data or config',
                    'debug_info': {
                        'has_password': bool(ssh_password),
                        'has_key': bool(ssh_key_path),
                        'platform': platform_name,
                        'deployment_data_keys': list(deployment_data.keys()),
                        'config_data_keys': list(config_data.keys())
                    }
                }), 400
            
            # Read YAML file content
            print(f"[REFRESH-DEPLOYMENT] Step 11: Reading YAML file content...")
            try:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    yaml_content = f.read()
                print(f"[REFRESH-DEPLOYMENT] YAML file read successfully ({len(yaml_content)} bytes)")
            except Exception as e:
                print(f"[REFRESH-DEPLOYMENT] ERROR: Failed to read YAML file: {e}")
                return jsonify({
                    'success': False,
                    'error': f'Failed to read YAML file: {str(e)}'
                }), 500
            
            # Connect via SSH and upload YAML file
            print(f"[REFRESH-DEPLOYMENT] Step 12: Establishing SSH connection...")
            try:
                import paramiko
                
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                
                # Connect to the instance
                print(f"[REFRESH-DEPLOYMENT] Connecting to {public_ip} as {ssh_username}...")
                if ssh_key_path and os.path.exists(ssh_key_path):
                    print(f"[REFRESH-DEPLOYMENT] Using SSH key: {ssh_key_path}")
                    ssh.connect(
                        hostname=public_ip,
                        username=ssh_username,
                        key_filename=ssh_key_path,
                        timeout=30
                    )
                elif ssh_password:
                    print(f"[REFRESH-DEPLOYMENT] Using SSH password authentication")
                    ssh.connect(
                        hostname=public_ip,
                        username=ssh_username,
                        password=ssh_password,
                        timeout=30
                    )
                else:
                    raise Exception("No SSH credentials available")
                
                print(f"[REFRESH-DEPLOYMENT] SSH connection established successfully")
                
                # Upload YAML file via SFTP
                print(f"[REFRESH-DEPLOYMENT] Step 13: Uploading YAML file via SFTP...")
                yaml_filename = os.path.basename(yaml_file)
                remote_yaml_path = f'/opt/mcp-server/{yaml_filename}'
                
                sftp = ssh.open_sftp()
                try:
                    # Create remote directory if it doesn't exist
                    try:
                        sftp.stat('/opt/mcp-server')
                    except IOError:
                        print(f"[REFRESH-DEPLOYMENT] Creating /opt/mcp-server directory...")
                        stdin, stdout, stderr = ssh.exec_command('sudo mkdir -p /opt/mcp-server && sudo chown ubuntu:ubuntu /opt/mcp-server')
                        stdout.channel.recv_exit_status()
                    
                    # Upload YAML file
                    print(f"[REFRESH-DEPLOYMENT] Uploading {yaml_filename} to {remote_yaml_path}...")
                    with sftp.file(remote_yaml_path, 'w') as remote_file:
                        remote_file.write(yaml_content)
                    
                    # Set proper permissions
                    sftp.chmod(remote_yaml_path, 0o644)
                    print(f"[REFRESH-DEPLOYMENT] YAML file uploaded successfully")
                    
                finally:
                    sftp.close()
                
                # Restart MCP server service
                print(f"[REFRESH-DEPLOYMENT] Step 14: Restarting MCP server service...")
                restart_commands = [
                    'sudo systemctl restart mcp-server',
                    'sleep 2',
                    'sudo systemctl status mcp-server --no-pager -l'
                ]
                
                for cmd in restart_commands:
                    print(f"[REFRESH-DEPLOYMENT] Executing: {cmd}")
                    stdin, stdout, stderr = ssh.exec_command(cmd)
                    exit_status = stdout.channel.recv_exit_status()
                    output = stdout.read().decode('utf-8', errors='ignore')
                    error_output = stderr.read().decode('utf-8', errors='ignore')
                    
                    if exit_status != 0 and 'status' not in cmd:  # status command may have non-zero exit
                        print(f"[REFRESH-DEPLOYMENT] WARNING: Command '{cmd}' exited with status {exit_status}")
                        if error_output:
                            print(f"[REFRESH-DEPLOYMENT] Error output: {error_output}")
                    else:
                        print(f"[REFRESH-DEPLOYMENT] Command output: {output[:500]}")  # First 500 chars
                
                # Verify service is running
                print(f"[REFRESH-DEPLOYMENT] Step 15: Verifying service status...")
                stdin, stdout, stderr = ssh.exec_command('sudo systemctl is-active mcp-server')
                service_status = stdout.read().decode('utf-8').strip()
                print(f"[REFRESH-DEPLOYMENT] Service status: {service_status}")
                
                if service_status == 'active':
                    print(f"[REFRESH-DEPLOYMENT] ✓ MCP server service is running")
                else:
                    print(f"[REFRESH-DEPLOYMENT] WARNING: MCP server service status: {service_status}")
                
                ssh.close()
                print(f"[REFRESH-DEPLOYMENT] SSH connection closed")
                
            except paramiko.AuthenticationException as e:
                print(f"[REFRESH-DEPLOYMENT] ERROR: SSH authentication failed: {e}")
                return jsonify({
                    'success': False,
                    'error': f'SSH authentication failed: {str(e)}',
                    'debug_info': {
                        'host': public_ip,
                        'username': ssh_username,
                        'has_password': bool(ssh_password),
                        'has_key': bool(ssh_key_path)
                    }
                }), 401
            except paramiko.SSHException as e:
                print(f"[REFRESH-DEPLOYMENT] ERROR: SSH connection error: {e}")
                return jsonify({
                    'success': False,
                    'error': f'SSH connection error: {str(e)}',
                    'debug_info': {
                        'host': public_ip,
                        'username': ssh_username
                    }
                }), 500
            except Exception as e:
                print(f"[REFRESH-DEPLOYMENT] ERROR: Failed to refresh YAML: {e}")
                import traceback
                error_traceback = traceback.format_exc()
                print(f"[REFRESH-DEPLOYMENT] Traceback: {error_traceback}")
                return jsonify({
                    'success': False,
                    'error': f'Failed to refresh YAML: {str(e)}',
                    'error_type': type(e).__name__
                }), 500
            
            print(f"[REFRESH-DEPLOYMENT] ========== SUCCESS ==========")
            print(f"[REFRESH-DEPLOYMENT] YAML refresh completed successfully")
            print(f"[REFRESH-DEPLOYMENT] Deployment ID: {deployment_id}")
            print(f"[REFRESH-DEPLOYMENT] Config ID: {config_id}")
            print(f"[REFRESH-DEPLOYMENT] Platform: {platform_name}")
            print(f"[REFRESH-DEPLOYMENT] YAML file: {yaml_filename}")
            print(f"[REFRESH-DEPLOYMENT] Remote path: {remote_yaml_path}")
            
            return jsonify({
                'success': True,
                'message': f'YAML refresh completed successfully for deployment {deployment_id}',
                'details': {
                    'yaml_file': yaml_filename,
                    'remote_path': remote_yaml_path,
                    'service_status': service_status,
                    'platform': platform_name
                },
                'debug_info': {
                    'deployment_id': deployment_id,
                    'config_id': config_id,
                    'platform': platform_name,
                    'public_ip': public_ip,
                    'instance_id': instance_id,
                    'yaml_file_local': yaml_file,
                    'yaml_file_remote': remote_yaml_path
                }
            })
            
        except Exception as e:
            import traceback
            error_traceback = traceback.format_exc()
            print(f"[REFRESH-DEPLOYMENT] ========== ERROR ==========")
            print(f"[REFRESH-DEPLOYMENT] Exception occurred: {type(e).__name__}: {str(e)}")
            print(f"[REFRESH-DEPLOYMENT] Traceback:")
            print(error_traceback)
            print(f"[REFRESH-DEPLOYMENT] ===========================")
            return jsonify({
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__,
                'traceback': error_traceback
            }), 500
    
    @app.route('/api/saved-configs/<config_id>', methods=['DELETE'])
    def delete_saved_config(config_id):
        """Delete a saved MCP server configuration"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Check if config exists
            cursor.execute('SELECT id FROM saved_configs WHERE id = ?', (config_id,))
            if not cursor.fetchone():
                conn.close()
                return jsonify({
                    'success': False,
                    'error': 'Configuration not found'
                }), 404
            
            # Delete config
            cursor.execute('DELETE FROM saved_configs WHERE id = ?', (config_id,))
            conn.commit()
            conn.close()
            
            return jsonify({
                'success': True,
                'message': 'Configuration deleted successfully'
            })
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/saved-configs/<config_id>/deployments', methods=['POST'])
    def save_deployment(config_id):
        """Save deployment details for a configuration"""
        try:
            data = request.get_json()
            deployment_data = data.get('deployment_data', {})
            platform = data.get('platform', 'unknown')
            status = data.get('status', 'unknown')  # success, failed, unknown
            
            if not deployment_data:
                return jsonify({
                    'success': False,
                    'error': 'Deployment data is required'
                }), 400
            
            # Check if config exists
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT id FROM saved_configs WHERE id = ?', (config_id,))
            if not cursor.fetchone():
                conn.close()
                return jsonify({
                    'success': False,
                    'error': 'Configuration not found'
                }), 404
            
            # Check for duplicate deployments (same instance_id or public_ip within last 5 minutes)
            # This prevents duplicate saves from multiple frontend calls
            instance_id = deployment_data.get('instance_id')
            public_ip = deployment_data.get('public_ip')
            
            if instance_id or public_ip:
                # Check for recent duplicate deployments (within last 5 minutes)
                five_minutes_ago = (datetime.now().timestamp() - 300) * 1000  # Convert to milliseconds
                cursor.execute('''
                    SELECT id, deployment_data FROM deployments
                    WHERE config_id = ? AND platform = ?
                    ORDER BY deployed_at DESC
                    LIMIT 10
                ''', (config_id, platform))
                
                existing_deployments = cursor.fetchall()
                for existing_id, existing_data_json in existing_deployments:
                    try:
                        existing_data = json.loads(existing_data_json)
                        
                        # Check if instance_id or public_ip matches
                        if (instance_id and existing_data.get('instance_id') == instance_id) or \
                           (public_ip and existing_data.get('public_ip') == public_ip):
                            # Check if deployment is recent (within 5 minutes)
                            cursor.execute('SELECT deployed_at FROM deployments WHERE id = ?', (existing_id,))
                            deployed_at_str = cursor.fetchone()[0]
                            deployed_at = datetime.fromisoformat(deployed_at_str.replace('Z', '+00:00'))
                            time_diff = (datetime.now() - deployed_at.replace(tzinfo=None)).total_seconds()
                            
                            if time_diff < 300:  # Within 5 minutes
                                conn.close()
                                return jsonify({
                                    'success': True,
                                    'deployment_id': existing_id,
                                    'message': 'Deployment already exists (duplicate prevented)',
                                    'duplicate': True
                                })
                    except (json.JSONDecodeError, ValueError):
                        continue  # Skip invalid JSON or date parsing errors
            
            # Generate deployment ID
            deployment_id = str(int(time.time() * 1000))
            deployed_at = datetime.now().isoformat()
            
            # Convert deployment_data to JSON string
            deployment_data_json = json.dumps(deployment_data, ensure_ascii=False)
            
            # Insert deployment
            cursor.execute('''
                INSERT INTO deployments (id, config_id, platform, deployment_data, status, deployed_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (deployment_id, config_id, platform, deployment_data_json, status, deployed_at))
            
            conn.commit()
            conn.close()
            
            return jsonify({
                'success': True,
                'deployment_id': deployment_id,
                'message': 'Deployment details saved successfully'
            })
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/saved-configs/<config_id>/deployments', methods=['GET'])
    def get_deployments(config_id):
        """Get all deployments for a configuration"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, platform, deployment_data, status, deployed_at
                FROM deployments
                WHERE config_id = ?
                ORDER BY deployed_at DESC
            ''', (config_id,))
            
            rows = cursor.fetchall()
            conn.close()
            
            deployments = []
            for row in rows:
                dep_id, platform, deployment_data_json, status, deployed_at = row
                deployments.append({
                    'id': dep_id,
                    'platform': platform,
                    'deployment_data': json.loads(deployment_data_json),
                    'status': status,
                    'deployed_at': deployed_at
                })
            
            return jsonify({
                'success': True,
                'deployments': deployments
            })
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/saved-configs/<config_id>/deployments/<deployment_id>/status', methods=['PUT'])
    def update_deployment_status(config_id, deployment_id):
        """Update deployment status"""
        try:
            data = request.get_json()
            new_status = data.get('status', 'unknown')
            deployment_data = data.get('deployment_data', None)
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Check if deployment exists
            cursor.execute('SELECT id FROM deployments WHERE id = ? AND config_id = ?', (deployment_id, config_id))
            if not cursor.fetchone():
                conn.close()
                return jsonify({
                    'success': False,
                    'error': 'Deployment not found'
                }), 404
            
            # Update status
            if deployment_data:
                # Update both status and deployment_data
                deployment_data_json = json.dumps(deployment_data, ensure_ascii=False)
                cursor.execute('''
                    UPDATE deployments 
                    SET status = ?, deployment_data = ?
                    WHERE id = ? AND config_id = ?
                ''', (new_status, deployment_data_json, deployment_id, config_id))
            else:
                # Update only status
                cursor.execute('''
                    UPDATE deployments 
                    SET status = ?
                    WHERE id = ? AND config_id = ?
                ''', (new_status, deployment_id, config_id))
            
            conn.commit()
            conn.close()
            
            return jsonify({
                'success': True,
                'message': 'Deployment status updated successfully'
            })
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/saved-configs/<config_id>/deployments/<deployment_id>/refresh', methods=['POST'])
    def refresh_deployment_status(config_id, deployment_id):
        """Refresh deployment status by checking with cloud provider"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Get deployment details
            cursor.execute('''
                SELECT platform, deployment_data, status
                FROM deployments
                WHERE id = ? AND config_id = ?
            ''', (deployment_id, config_id))
            
            row = cursor.fetchone()
            if not row:
                conn.close()
                return jsonify({
                    'success': False,
                    'error': 'Deployment not found'
                }), 404
            
            platform, deployment_data_json, current_status = row
            deployment_data = json.loads(deployment_data_json)
            
            # Get configuration to access credentials
            cursor.execute('SELECT config_data FROM saved_configs WHERE id = ?', (config_id,))
            config_row = cursor.fetchone()
            if not config_row:
                conn.close()
                return jsonify({
                    'success': False,
                    'error': 'Configuration not found'
                }), 404
            
            config_data = json.loads(config_row[0])
            
            # Check status based on platform
            new_status = 'unknown'
            updated_deployment_data = deployment_data.copy()
            
            if platform == 'aws':
                # Check AWS instance status
                try:
                    import boto3
                    instance_id = deployment_data.get('instance_id')
                    if instance_id and config_data.get('access_key') and config_data.get('secret_key'):
                        ec2 = boto3.client(
                            'ec2',
                            aws_access_key_id=config_data.get('access_key'),
                            aws_secret_access_key=config_data.get('secret_key'),
                            region_name=deployment_data.get('region', 'ap-south-1')
                        )
                        
                        response = ec2.describe_instances(InstanceIds=[instance_id])
                        if response['Reservations']:
                            instance = response['Reservations'][0]['Instances'][0]
                            state = instance['State']['Name']
                            
                            if state == 'running':
                                new_status = 'success'
                                # Update public IP if changed
                                if 'PublicIpAddress' in instance:
                                    updated_deployment_data['public_ip'] = instance['PublicIpAddress']
                            elif state in ['pending', 'stopping', 'stopped']:
                                new_status = 'unknown'
                            else:
                                new_status = 'failed'
                except Exception as e:
                    print(f"Error checking AWS status: {e}")
                    new_status = 'unknown'
            
            elif platform == 'azure':
                # Check Azure VM status
                try:
                    from azure.identity import ClientSecretCredential
                    from azure.mgmt.compute import ComputeManagementClient
                    
                    subscription_id = deployment_data.get('subscription_id') or config_data.get('subscription_id')
                    resource_group = deployment_data.get('resource_group') or config_data.get('resource_group')
                    vm_name = deployment_data.get('vm_name')
                    
                    if subscription_id and resource_group and vm_name:
                        credential = ClientSecretCredential(
                            tenant_id=config_data.get('tenant_id'),
                            client_id=config_data.get('client_id'),
                            client_secret=config_data.get('client_secret')
                        )
                        compute_client = ComputeManagementClient(credential, subscription_id)
                        
                        vm = compute_client.virtual_machines.get(resource_group, vm_name, expand='instanceView')
                        if vm.instance_view:
                            power_state = next((s.code for s in vm.instance_view.statuses if 'PowerState' in s.code), None)
                            if power_state == 'PowerState/running':
                                new_status = 'success'
                            elif power_state in ['PowerState/starting', 'PowerState/stopping']:
                                new_status = 'unknown'
                            else:
                                new_status = 'failed'
                except Exception as e:
                    print(f"Error checking Azure status: {e}")
                    new_status = 'unknown'
            
            # Update deployment status
            updated_deployment_data_json = json.dumps(updated_deployment_data, ensure_ascii=False)
            cursor.execute('''
                UPDATE deployments 
                SET status = ?, deployment_data = ?
                WHERE id = ? AND config_id = ?
            ''', (new_status, updated_deployment_data_json, deployment_id, config_id))
            
            conn.commit()
            conn.close()
            
            return jsonify({
                'success': True,
                'status': new_status,
                'deployment_data': updated_deployment_data,
                'message': 'Deployment status refreshed successfully'
            })
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/download-database-config', methods=['GET'])
    def mcp_download_database_config():
        """Download a database config.ini file"""
        try:
            import base64
            from urllib.parse import unquote
            
            config_path = request.args.get('path')
            is_encoded = request.args.get('encoded', 'false').lower() == 'true'
            
            if not config_path:
                return jsonify({
                    'success': False,
                    'error': 'Path parameter is required'
                }), 400
            
            # Decode base64 if encoded, otherwise use URL decode
            if is_encoded:
                try:
                    config_path = base64.b64decode(config_path).decode('utf-8')
                except Exception as e:
                    return jsonify({
                        'success': False,
                        'error': f'Invalid encoded path: {str(e)}'
                    }), 400
            else:
                # Properly decode the URL-encoded path
                config_path = unquote(config_path)
            
            # Normalize path separators for Windows
            if os.name == 'nt':  # Windows
                config_path = config_path.replace('/', '\\')
            
            config_path = Path(config_path)
            
            if not config_path.exists():
                return jsonify({
                    'success': False,
                    'error': f'Config file not found: {config_path}'
                }), 404
            
            # Extract filename
            filename = config_path.name
            
            return send_file(
                str(config_path),
                mimetype='text/plain',
                as_attachment=True,
                download_name=filename
            )
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/auto-deploy-database-mcp', methods=['POST'])
    def mcp_auto_deploy_database_mcp():
        """Auto-deploy database MCP server to Claude Desktop"""
        try:
            data = request.get_json()
            config_path = data.get('config_path')
            server_path = data.get('server_path')
            server_name = data.get('server_name')
            
            # Auto-detect server path if not provided
            if not server_path:
                project_root = os.path.dirname(os.path.abspath(__file__))
                server_path = os.path.join(project_root, 'dbhandler_mcpserver', 'scikiq_pkg_dbutils')
            
            if not all([config_path, server_name]):
                return jsonify({
                    'success': False,
                    'error': 'Missing required parameters: config_path and server_name are required'
                }), 400
            
            # Detect Python path
            python_path = detect_python_executable()
            
            # Deploy to Claude Desktop using manual config update
            result = deploy_database_mcp_to_claude(server_name, server_path, config_path, python_path)
            
            if result['success']:
                return jsonify({
                    'success': True,
                    'message': 'Database MCP server deployed successfully to Claude Desktop',
                    'config_path': result.get('config_path'),
                    'backup_path': result.get('backup_path')
                })
            else:
                return jsonify({
                    'success': False,
                    'error': result.get('error', 'Deployment failed')
                }), 500
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    def deploy_database_mcp_to_claude(server_name, server_path, config_ini_path, python_path):
        """Deploy database MCP server to Claude Desktop configuration"""
        try:
            # Get Claude Desktop config path
            config_path = get_claude_desktop_config_path()
            
            # Create backup
            backup_path = None
            if config_path.exists():
                backup_path = config_path.with_suffix(f'.backup.{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
                import shutil
                shutil.copy2(config_path, backup_path)
            
            # Load or create config
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            else:
                config = {}
            
            # Ensure mcpServers section exists
            if "mcpServers" not in config:
                config["mcpServers"] = {}
            
            # Add database MCP server
            # Ensure paths are properly escaped for Windows
            run_server_path = str(Path(server_path) / "run_mcp_server.py").replace('/', '\\') if platform.system() == "Windows" else str(Path(server_path) / "run_mcp_server.py")
            config_ini_path_fixed = str(Path(config_ini_path)).replace('/', '\\') if platform.system() == "Windows" else str(Path(config_ini_path))
            
            print(f"[DEBUG] Original paths:")
            print(f"  server_path: {server_path}")
            print(f"  config_ini_path: {config_ini_path}")
            print(f"[DEBUG] Fixed paths:")
            print(f"  run_server_path: {run_server_path}")
            print(f"  config_ini_path_fixed: {config_ini_path_fixed}")
            
            config["mcpServers"][server_name] = {
                "command": python_path,
                "args": [
                    run_server_path,
                    "--config-file",
                    config_ini_path_fixed
                ]
            }
            
            # Ensure config directory exists
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write updated config
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            return {
                'success': True,
                'config_path': str(config_path),
                'backup_path': str(backup_path) if backup_path else None
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def get_claude_desktop_config_path():
        """Get Claude Desktop config path based on OS"""
        system = platform.system()
        if system == "Windows":
            return Path(os.getenv('APPDATA')) / "Claude" / "claude_desktop_config.json"
        elif system == "Darwin":  # macOS
            return Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
        elif system == "Linux":
            return Path.home() / ".config" / "Claude" / "claude_desktop_config.json"
        else:
            raise Exception(f"Unsupported operating system: {system}")


    def generate_database_config_ini(connections, selected_tools=None):
        """Generate config.ini content from database connections"""
        config_lines = []
        config_lines.append("# Database MCP Server Configuration")
        config_lines.append("# Generated by MCP Studio")
        config_lines.append(f"# Created: {datetime.now().isoformat()}")
        config_lines.append("")
        
        # Add SERVER section with enabled tools if provided
        if selected_tools and len(selected_tools) > 0:
            config_lines.append("[SERVER]")
            config_lines.append("# Enabled MCP tools (comma-separated list)")
            config_lines.append(f"ENABLED_TOOLS={','.join(selected_tools)}")
            config_lines.append("")
        
        for conn in connections:
            connection_name = conn.get('connection_name', 'database')
            db_type = conn.get('db_type', 'MYSQL').upper()
            
            config_lines.append(f"[{connection_name}]")
            config_lines.append(f"DB_TYPE={db_type}")
            
            # Add connection parameters based on database type
            if db_type == 'DUCKDB':
                # DuckDB specific configuration
                connection_type = conn.get('duckdb_connection_type', 'local')
                
                if connection_type == 's3':
                    # S3 configuration for DuckDB
                    aws_access_key_id = conn.get('aws_access_key_id', '')
                    aws_secret_access_key = conn.get('aws_secret_access_key', '')
                    region_name = conn.get('region_name', 'ap-south-1')
                    bucket_name = conn.get('bucket_name', '')
                    
                    if aws_access_key_id:
                        config_lines.append(f"aws_access_key_id={aws_access_key_id}")
                    if aws_secret_access_key:
                        config_lines.append(f"aws_secret_access_key={aws_secret_access_key}")
                    if region_name:
                        config_lines.append(f"region_name={region_name}")
                    if bucket_name:
                        config_lines.append(f"bucket_name={bucket_name}")
                else:
                    # Local file configuration
                    database_path = conn.get('database_path', '')
                    if database_path:
                        config_lines.append(f"DATABASE_PATH={database_path}")
            else:
                # Standard database configuration
                # Check for hostname in multiple possible keys (hostname, host, HOSTNAME, HOST)
                host = (conn.get('hostname') or conn.get('host') or 
                       conn.get('HOSTNAME') or conn.get('HOST') or 'localhost')
                port = conn.get('port', get_default_port_for_db(db_type))
                database = conn.get('database', '')
                username = conn.get('username', '')
                password = conn.get('password', '')
                
                config_lines.append(f"HOSTNAME={host}")
                config_lines.append(f"PORT={port}")
                config_lines.append(f"DATABASE={database}")
                config_lines.append(f"USERNAME={username}")
                config_lines.append(f"PASSWORD={password}")
                config_lines.append("PASSWORD_ENCRYPTED=0")
                
                # Add database-specific parameters
                if db_type == 'ORACLE':
                    service_name = conn.get('service_name', '')
                    if service_name:
                        config_lines.append(f"SERVICE_NAME={service_name}")
                elif db_type == 'MONGODB':
                    auth_db = conn.get('auth_database', 'admin')
                    config_lines.append(f"AUTH_DATABASE={auth_db}")
                elif db_type in ['POSTGRES', 'SQLSERVER', 'VERTICA']:
                    # Add schema from user input or use default
                    schema = conn.get('schema', '')
                    if not schema:
                        # Use default schema based on database type
                        if db_type == 'POSTGRES':
                            schema = 'public'
                        elif db_type == 'SQLSERVER':
                            schema = 'dbo'
                        elif db_type == 'VERTICA':
                            schema = 'public'
                    config_lines.append(f"SCHEMA={schema}")

                # Add SSL configuration if provided
                ssl_mode = conn.get('ssl_mode', '')
                if ssl_mode:
                    config_lines.append(f"SSL_MODE={ssl_mode}")
            
            config_lines.append("")  # Empty line between connections
        
        return "\n".join(config_lines)

    def get_default_port_for_db(db_type):
        """Get default port for database type"""
        ports = {
            'MYSQL': 3306,
            'POSTGRES': 5432,
            'SQLSERVER': 1433,
            'ORACLE': 1521,
            'MONGODB': 27017,
            'SNOWFLAKE': 443,
            'REDSHIFT': 5439,
            'BIGQUERY': 443,
            'VERTICA': 5433
        }
        return ports.get(db_type, 3306)

    def detect_python_executable():
        """Detect the appropriate Python executable"""
        import sys
        import shutil
        
        # Try to find python in common locations
        python_candidates = [
            sys.executable,
            shutil.which('python'),
            shutil.which('python3'),
            shutil.which('py')
        ]
        
        for candidate in python_candidates:
            if candidate and Path(candidate).exists():
                return candidate
        
        # Fallback to system python
        return 'python'


    # ==================== MCP DEPLOYMENT ENDPOINTS (SWAGGER & CODEBASE) ====================

    @app.route('/api/deploy-mcp-local', methods=['POST'])
    def deploy_mcp_local():
        """Deploy MCP server to local Claude Desktop"""
        try:
            data = request.get_json()
            server_path = data.get('server_path')
            server_name = data.get('server_name', 'scikiq-mcp-autoAPI')
            config = data.get('config', {})
            
            if not server_path:
                return jsonify({
                    'success': False,
                    'error': 'Server path is required'
                }), 400
            
            # Detect Python path
            python_path = detect_python_executable()
            
            # Get Claude Desktop config path
            config_path = get_claude_desktop_config_path()
            
            # Create backup
            backup_path = None
            if config_path.exists():
                backup_path = config_path.with_suffix(f'.backup.{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
                import shutil
                shutil.copy2(config_path, backup_path)
            
            # Load or create config
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    claude_config = json.load(f)
            else:
                claude_config = {}
            
            # Ensure mcpServers section exists
            if "mcpServers" not in claude_config:
                claude_config["mcpServers"] = {}
            
            # Add MCP server
            server_path_fixed = str(Path(server_path)).replace('/', '\\') if platform.system() == "Windows" else str(Path(server_path))
            
            claude_config["mcpServers"][server_name] = {
                "command": python_path,
                "args": [server_path_fixed]
            }
            
            # Ensure config directory exists
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write updated config
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(claude_config, f, indent=2, ensure_ascii=False)
            
            return jsonify({
                'success': True,
                'message': 'MCP Server deployed successfully to Claude Desktop',
                'config_path': str(config_path),
                'backup_path': str(backup_path) if backup_path else None
            })
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/scan-github-repo', methods=['POST'])
    def scan_github_repo():
        """Clone and scan a GitHub repository for API endpoints"""
        try:
            import git
            import tempfile
            import shutil
            
            data = request.get_json()
            repo_url = data.get('github_repo_url')
            branch = data.get('github_branch', 'main')
            token = data.get('github_token')
            source_file = data.get('source_file')
            
            if not repo_url:
                return jsonify({
                    'success': False,
                    'error': 'GitHub repository URL is required'
                }), 400
            
            # Create temporary directory
            temp_dir = tempfile.mkdtemp()
            
            try:
                # Prepare clone URL with token if provided
                if token:
                    # Format: https://token@github.com/owner/repo.git
                    if 'github.com' in repo_url:
                        clone_url = repo_url.replace('https://', f'https://{token}@')
                    else:
                        clone_url = repo_url
                else:
                    clone_url = repo_url
                
                print(f"[GITHUB-SCAN] Cloning repository: {repo_url}")
                print(f"[GITHUB-SCAN] Branch: {branch}")
                print(f"[GITHUB-SCAN] Temp directory: {temp_dir}")
                
                # Clone repository
                git.Repo.clone_from(clone_url, temp_dir, branch=branch, depth=1)
                
                print(f"[GITHUB-SCAN] Repository cloned successfully")
                
                # Import the scan logic (this should already exist)
                from swagger_parser import scan_codebase_for_apis
                
                # Scan the cloned repository
                result = scan_codebase_for_apis(temp_dir, source_file)
                
                return jsonify({
                    'success': True,
                    'api_definitions': result.get('api_definitions', []),
                    'file_tree': result.get('file_tree', {}),
                    'intelligence': result.get('intelligence', {}),
                    'total_apis': len(result.get('api_definitions', []))
                })
                
            except git.exc.GitCommandError as e:
                error_msg = str(e)
                if 'Authentication failed' in error_msg or 'could not read Username' in error_msg:
                    return jsonify({
                        'success': False,
                        'error': 'GitHub authentication failed. Please provide a valid personal access token for private repositories.'
                    }), 401
                elif 'Repository not found' in error_msg:
                    return jsonify({
                        'success': False,
                        'error': 'Repository not found. Please check the URL and try again.'
                    }), 404
                else:
                    return jsonify({
                        'success': False,
                        'error': f'Git error: {error_msg}'
                    }), 500
                    
            except Exception as e:
                import traceback
                traceback.print_exc()
                return jsonify({
                    'success': False,
                    'error': f'Scan error: {str(e)}'
                }), 500
                
            finally:
                # Clean up temporary directory
                try:
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    print(f"[GITHUB-SCAN] Cleaned up temp directory")
                except:
                    pass
                    
        except ImportError as e:
            return jsonify({
                'success': False,
                'error': 'GitPython is not installed. Please install it with: pip install GitPython'
            }), 500
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    # ==================== CLIENT INSTALLATION ENDPOINTS ====================

    @app.route('/api/generate-installer', methods=['POST'])
    def generate_client_installer():
        """Generate a client installer script for local MCP server installation"""
        try:
            data = request.get_json()
            installation_path = data.get('installation_path', '')
            server_name = data.get('server_name', 'mcp_server')
            server_type = data.get('server_type', 'swagger')  # swagger, codebase, database
            server_config = data.get('server_config', {})
            
            # Generate the installer script
            installer_script = generate_client_installer_script(
                installation_path, server_name, server_type, server_config
            )
            
            # Save installer script
            installer_filename = f"{server_name}_installer.py"
            installer_path = os.path.join('generated_servers', installer_filename)
            
            # Ensure directory exists
            os.makedirs('generated_servers', exist_ok=True)
            
            with open(installer_path, 'w', encoding='utf-8') as f:
                f.write(installer_script)
            
            return jsonify({
                'success': True,
                'installer_filename': installer_filename,
                'installer_path': installer_path,
                'download_url': f'/download-installer/{installer_filename}',
                'instructions': get_installer_instructions()
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/download-installer/<filename>')
    def download_installer(filename):
        """Download the installer script"""
        try:
            return send_from_directory(
                'generated_servers', 
                filename,
                as_attachment=True,
                mimetype='text/x-python'
            )
        except Exception as e:
            return jsonify({'error': str(e)}), 404

    @app.route('/api/get-server-package', methods=['POST'])
    def get_server_package():
        """Generate and package MCP server files for download"""
        try:
            data = request.get_json()
            server_name = data.get('server_name', 'mcp_server')
            server_type = data.get('server_type', 'swagger')
            server_config = data.get('server_config', {})
            
            # Generate server files based on type
            package_info = generate_server_package(server_name, server_type, server_config)
            
            return jsonify({
                'success': True,
                'package_info': package_info
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    # ==================== ONLINE DEPLOYMENT ROUTES ====================
    
    @app.route('/api/deploy/aws', methods=['POST'])
    def deploy_aws():
        """Deploy MCP server to AWS EC2"""
        print("[DEPLOY-AWS] Endpoint called!")
        try:
            print("[DEPLOY-AWS] Importing OnlineDeployer...")
            from online_deployment import OnlineDeployer
            print("[DEPLOY-AWS] OnlineDeployer imported successfully")
            
            data = request.get_json()
            print(f"[DEPLOY-AWS] Request data: {data.keys() if data else 'No data'}")
            
            deployer = OnlineDeployer()
            print("[DEPLOY-AWS] OnlineDeployer instance created")
            
            def generate():
                try:
                    yield "[LOG] Starting AWS Deployment...\n"
                    print("[DEPLOY-AWS] Generator started")
                    
                    # Get server type and paths
                    server_type = data.get('server_type')  # 'api', 'database', 'codebase', 'swagger'
                    server_path = data.get('server_path')
                    config_path = data.get('config_path')
                    domain = data.get('domain') or data.get('awsDomain')
                    yaml_file = data.get('yaml_file')  # Specific YAML filename for this deployment
                    
                    # Auto-detect server path for database servers if not provided
                    if not server_path and server_type == 'database':
                        project_root = os.path.dirname(os.path.abspath(__file__))
                        server_path = os.path.join(project_root, 'dbhandler_mcpserver', 'scikiq_pkg_dbutils')
                        yield f"[LOG] Auto-detected database server path: {server_path}\n"
                    
                    # Prepare server files based on type
                    if server_type and server_path:
                        yield f"[LOG] Preparing {server_type} MCP server files from {server_path}\n"
                        if yaml_file:
                            yield f"[LOG] Using specific YAML file: {yaml_file}\n"
                        server_files = {}  # Will be prepared in deploy_to_aws
                    else:
                        # Legacy: simple server files
                        server_files = {
                            'app.py': 'print("Hello MCP")',
                            'requirements.txt': 'flask\nmcp'
                        }
                        yield "[LOG] Prepared server files\n"
                    
                    # If config_path is not provided for database server, try to find it in the server path
                    if not config_path and server_type == 'database' and server_path:
                        potential_config = Path(server_path) / 'scikiq_pkg_dbutils' / 'config.ini'
                        if potential_config.exists():
                            config_path = str(potential_config.resolve())
                            yield f"[LOG] Auto-detected config file: {config_path}\n"
                        else:
                             # Try directly in server_path
                            potential_config_direct = Path(server_path) / 'config.ini'
                            if potential_config_direct.exists():
                                config_path = str(potential_config_direct.resolve())
                                yield f"[LOG] Auto-detected config file: {config_path}\n"
                    
                    # Ensure config_path is absolute for database deployments
                    if server_type == 'database' and config_path:
                        project_root = Path(__file__).parent
                        project_root_str = str(project_root)
                        config_path_str = str(config_path).strip()
                        
                        # Fix malformed paths - check if path has concatenated project root
                        # Pattern: "DAASMCP POCgaurav" or duplicated project root segments
                        project_root_no_spaces = project_root_str.replace(' ', '').replace('\\', '/')
                        config_path_no_spaces = config_path_str.replace(' ', '').replace('\\', '/')
                        
                        if 'DAASMCP POCgaurav' in config_path_str or (project_root_no_spaces in config_path_no_spaces and config_path_no_spaces.count(project_root_no_spaces) > 1):
                            # Extract the relative part - look for "dbhandler_mcpserver" or "config.ini"
                            if 'dbhandler_mcpserver' in config_path_str:
                                idx = config_path_str.find('dbhandler_mcpserver')
                                rel_part = config_path_str[idx:]
                                # Ensure proper path separators
                                rel_part = rel_part.replace('\\', '/').replace('//', '/')
                                config_path_str = str((project_root / rel_part).resolve())
                            elif 'scikiq_pkg_dbutils' in config_path_str:
                                idx = config_path_str.find('scikiq_pkg_dbutils')
                                rel_part = config_path_str[idx:]
                                rel_part = rel_part.replace('\\', '/').replace('//', '/')
                                config_path_str = str((project_root / 'dbhandler_mcpserver' / rel_part).resolve())
                            elif 'config.ini' in config_path_str:
                                # If we can find config.ini, try to extract path from it
                                idx = config_path_str.find('config.ini')
                                # Look backwards for dbhandler_mcpserver
                                before_config = config_path_str[:idx]
                                if 'dbhandler_mcpserver' in before_config:
                                    db_idx = before_config.find('dbhandler_mcpserver')
                                    rel_part = config_path_str[db_idx:]
                                    rel_part = rel_part.replace('\\', '/').replace('//', '/')
                                    config_path_str = str((project_root / rel_part).resolve())
                                else:
                                    # Fallback to standard location
                                    config_path_str = str((project_root / 'dbhandler_mcpserver' / 'scikiq_pkg_dbutils' / 'config.ini').resolve())
                        
                        # Normalize the path
                        config_path_normalized = config_path_str.replace('\\', '/').replace('//', '/')
                        
                        # If path contains project root duplicated, fix it
                        project_root_normalized = project_root_str.replace('\\', '/')
                        if project_root_normalized in config_path_normalized and config_path_normalized.count(project_root_normalized) > 1:
                            # Remove duplicate project root
                            parts = config_path_normalized.split(project_root_normalized)
                            config_path_normalized = project_root_normalized + ''.join(parts[1:])
                        
                        # Use Path's native path handling - Path handles platform-specific separators automatically
                        config_path_abs = Path(config_path_normalized)
                        
                        # If still not absolute or doesn't exist, try standard location
                        if not config_path_abs.is_absolute() or not config_path_abs.exists():
                            standard_config_path = project_root / 'dbhandler_mcpserver' / 'scikiq_pkg_dbutils' / 'config.ini'
                            if standard_config_path.exists():
                                config_path = str(standard_config_path.resolve())
                                yield f"[LOG] Fixed malformed path, using standard location: {config_path}\n"
                            else:
                                # Try relative resolution
                                if not config_path_abs.is_absolute():
                                    config_path = str((project_root / config_path_normalized).resolve())
                                else:
                                    config_path = str(config_path_abs.resolve())
                        else:
                            config_path = str(config_path_abs.resolve())
                        
                        yield f"[LOG] Using config file: {config_path}\n"
                        
                        # Final check: if file doesn't exist, try standard location
                        import os as os_module  # Import locally to avoid scoping issues
                        if not os_module.path.exists(config_path):
                            standard_config_path = project_root / 'dbhandler_mcpserver' / 'scikiq_pkg_dbutils' / 'config.ini'
                            if standard_config_path.exists():
                                config_path = str(standard_config_path.resolve())
                                yield f"[LOG] Config file not found at specified path, using standard location: {config_path}\n"
                            else:
                                yield f"[LOG] WARNING: Config file not found at {config_path} and standard location also not found\n"
                    
                    # For database servers, read connections and selected_tools from config
                    connections = None
                    selected_tools = None
                    if server_type == 'database' and config_path:
                        try:
                            import configparser
                            import os
                            yield f"[LOG] Reading connections from config file: {config_path}\n"
                            yield f"[LOG] Config file exists: {os.path.exists(config_path)}\n"
                            
                            config = configparser.ConfigParser()
                            config.read(config_path, encoding='utf-8')
                            
                            yield f"[LOG] Config sections found: {config.sections()}\n"
                            
                            # Extract connections from config
                            connections = []
                            for section in config.sections():
                                if section.upper() != 'SERVER':
                                    conn = {}
                                    conn['connection_name'] = section
                                    for key, value in config[section].items():
                                        conn[key.lower()] = value
                                    connections.append(conn)
                            
                            yield f"[LOG] Extracted {len(connections)} connections from config\n"
                            
                            # Validate that connections exist (mandatory for database servers)
                            if len(connections) == 0:
                                yield f"[LOG] ERROR: No database connections found in config file. Connections are mandatory for database MCP server.\n"
                                raise ValueError("No database connections found in config file. Please configure at least one database connection before deploying.")
                            
                            # Extract selected tools from SERVER section
                            if 'SERVER' in config and 'ENABLED_TOOLS' in config['SERVER']:
                                selected_tools = [t.strip() for t in config['SERVER']['ENABLED_TOOLS'].split(',') if t.strip()]
                                yield f"[LOG] Extracted {len(selected_tools)} selected tools: {selected_tools}\n"
                            else:
                                yield f"[LOG] No ENABLED_TOOLS found in SERVER section\n"
                        except ValueError as ve:
                            # Re-raise ValueError (validation errors)
                            yield f"[LOG] ERROR: {str(ve)}\n"
                            raise
                        except Exception as e:
                            yield f"[LOG] Warning: Could not read connections from config: {e}\n"
                            import traceback
                            yield f"[LOG] Traceback: {traceback.format_exc()}\n"
                            # If config file exists but couldn't be read, still raise error
                            if os.path.exists(config_path):
                                raise ValueError(f"Failed to read database connections from config file: {e}")
                    
                    result = deployer.deploy_to_aws(
                        aws_access_key=data.get('access_key'),
                        aws_secret_key=data.get('secret_key'),
                        region=data.get('region', 'ap-south-1'),
                        instance_type=data.get('instance_type', 't2.micro'),
                        server_files=server_files,
                        server_type=server_type,
                        server_path=server_path,
                        config_path=config_path,
                        domain=domain,
                        server_name=data.get('server_name'),
                        yaml_file=yaml_file,
                        connections=connections,
                        selected_tools=selected_tools
                    )
                    
                    yield "[LOG] Deployment method called\n"
                    
                    # Read all logs from the queue
                    # Route 53 setup happens synchronously in deploy_to_aws, so logs should be in queue
                    max_iterations = 1000  # Increased to ensure we capture all logs including wait messages
                    iteration = 0
                    empty_iterations = 0
                    max_empty_iterations = 30  # Increased to allow more time for threaded progress logs (30 * 0.5s = 15s)
                    result_received = False
                    
                    # First, read logs while deployment is running
                    while iteration < max_iterations:
                        try:
                            log = deployer.logs.get(timeout=0.5)  # Increased timeout to better catch threaded logs
                            yield f"{log}\n"
                            empty_iterations = 0  # Reset empty counter
                            iteration += 1
                        except:
                            empty_iterations += 1
                            iteration += 1
                            # If no logs for a while but still waiting, continue
                            if empty_iterations < max_empty_iterations:
                                time.sleep(0.5)  # Increased delay to better align with threaded log intervals
                            
                            # If we got a result, continue reading for a bit more to catch Route 53 logs
                            if result is not None:
                                if not result_received:
                                    result_received = True
                                    # Give more time for Route 53 logs to be queued
                                    time.sleep(1.0)
                                    empty_iterations = 0  # Reset to continue reading
                                    continue
                                
                                # After result, wait longer for any remaining logs from threads
                                if empty_iterations < max_empty_iterations:
                                    time.sleep(0.5)  # Longer delay to catch delayed logs
                                    continue
                            
                            # If we've had several empty reads, check if we should continue
                            if empty_iterations >= max_empty_iterations:
                                if result is not None:
                                    # Got result and no more logs, we're done
                                    break
                                elif iteration < max_iterations - 50:
                                    # No result yet, continue waiting
                                    empty_iterations = 0  # Reset to keep waiting
                                    time.sleep(1.0)  # Wait a bit longer
                                    continue
                                else:
                                    # Timeout waiting for result
                                    break
                            continue
                    
                    # After reading initial logs, if we have a result, read any remaining logs
                    if result:
                        # Read any remaining logs (Route 53 setup logs should be here)
                        additional_logs_timeout = 2  # Wait up to 2 seconds for additional logs
                        start_time = time.time()
                        logs_read = 0
                        while time.time() - start_time < additional_logs_timeout and logs_read < 20:
                            try:
                                log = deployer.logs.get(timeout=0.1)
                                yield f"{log}\n"
                                logs_read += 1
                                start_time = time.time()  # Reset timeout on successful read
                            except:
                                if logs_read > 0:
                                    # Got some logs, wait a bit more
                                    time.sleep(0.1)
                                    continue
                                break
                        
                        yield f"[SUCCESS] Deployment Complete! Public IP: {result.get('public_ip')}\n"
                        if result.get('domain'):
                            yield f"[INFO] Domain configured: {result.get('domain')}\n"
                            yield f"[INFO] DNS propagation may take 5-10 minutes. Server will be available at https://{result.get('domain')}\n"
                        else:
                            yield f"[INFO] Server accessible at http://{result.get('public_ip')} after initialization (5-10 minutes)\n"
                        
                        # Generate deployment details summary
                        if result.get('deployment_summary'):
                            summary = result.get('deployment_summary')
                            yield "\n"
                            yield "=" * 60 + "\n"
                            yield "DEPLOYMENT DETAILS SUMMARY\n"
                            yield "=" * 60 + "\n"
                            yield f"Instance ID: {summary.get('instance_id')}\n"
                            yield f"Region: {summary.get('region')}\n"
                            yield f"Public IP: {summary.get('public_ip')}\n"
                            if summary.get('domain'):
                                yield f"Domain: {summary.get('domain')}\n"
                            yield f"Instance Type: {summary.get('instance_type')}\n"
                            yield "\n"
                            yield "Access URLs:\n"
                            for url_type, url in summary.get('access_urls', {}).items():
                                yield f"  {url_type}: {url}\n"
                            if summary.get('admin_credentials'):
                                yield "\n"
                                yield "Admin Credentials:\n"
                                yield f"  Username: {summary.get('admin_credentials', {}).get('username')}\n"
                                yield f"  Password: {summary.get('admin_credentials', {}).get('password')}\n"
                                yield f"  Email: {summary.get('admin_credentials', {}).get('email')}\n"
                            yield "\n"
                            yield "=" * 60 + "\n"
                            yield "Copy the above details for your records.\n"
                            yield "=" * 60 + "\n"

                        # Auto-download logs if requested
                        auto_download_logs = data.get('auto_download_logs', False)
                        if auto_download_logs and result.get('deployment_summary'):
                            instance_id = result.get('deployment_summary', {}).get('instance_id')
                            region = data.get('region', 'ap-south-1')

                            if instance_id:
                                yield "\n"
                                yield "=" * 60 + "\n"
                                yield "FETCHING DEPLOYMENT LOGS...\n"
                                yield "=" * 60 + "\n"
                                yield f"[INFO] Waiting for setup to complete on {instance_id}...\n"
                                yield "[INFO] This may take 5-10 minutes. Logs will be fetched automatically.\n"

                                # Wait a bit for cloud-init to start logging
                                time.sleep(30)

                                log_result = deployer.get_deployment_logs(
                                    instance_id=instance_id,
                                    aws_access_key=data.get('access_key'),
                                    aws_secret_key=data.get('secret_key'),
                                    region=region,
                                    wait_for_completion=True,
                                    max_wait_seconds=600  # Wait up to 10 minutes
                                )

                                # Stream any logs from the log fetcher
                                while True:
                                    try:
                                        log = deployer.logs.get(timeout=0.1)
                                        yield f"{log}\n"
                                    except:
                                        break

                                if log_result.get('success'):
                                    yield "\n"
                                    yield "=" * 60 + "\n"
                                    yield "EC2 CONSOLE OUTPUT / SETUP LOGS\n"
                                    yield "=" * 60 + "\n"
                                    yield log_result.get('logs', 'No logs available yet')
                                    yield "\n"
                                    yield "=" * 60 + "\n"
                                    if log_result.get('completed'):
                                        yield "[SUCCESS] Setup completed on EC2 instance.\n"
                                    else:
                                        yield "[INFO] Setup may still be in progress. Check instance console for full logs.\n"
                                else:
                                    yield f"[WARNING] Could not fetch logs: {log_result.get('error', 'Unknown error')}\n"
                                    yield "[INFO] You can manually fetch logs later using the /api/deploy/aws/logs endpoint.\n"
                    else:
                        # Read any remaining error logs
                        try:
                            for _ in range(10):
                                log = deployer.logs.get(timeout=0.1)
                                yield f"{log}\n"
                        except:
                            pass
                        yield "[ERROR] Deployment Failed.\n"
                except Exception as gen_error:
                    print(f"[DEPLOY-AWS] Generator error: {gen_error}")
                    yield f"[ERROR] Generator error: {str(gen_error)}\n"

            print("[DEPLOY-AWS] Returning streaming response")
            return Response(stream_with_context(generate()), mimetype='text/plain')

        except ImportError as ie:
            import traceback
            error_msg = f"Import error: {str(ie)}. Make sure online_deployment.py exists and dependencies are installed."
            print(f"[DEPLOY-AWS] {error_msg}")
            print(f"[DEPLOY-AWS] Traceback: {traceback.format_exc()}")
            return jsonify({'error': error_msg}), 500
        except Exception as e:
            import traceback
            error_msg = f"Deployment error: {str(e)}"
            print(f"[DEPLOY-AWS] {error_msg}")
            print(f"[DEPLOY-AWS] Traceback: {traceback.format_exc()}")
            return jsonify({'error': error_msg}), 500
            error_msg = f"Deployment error: {str(e)}"
            print(f"[DEPLOY-AWS] {error_msg}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': error_msg}), 500

    @app.route('/api/deploy/aws/logs', methods=['POST'])
    def get_aws_deployment_logs():
        """Get deployment logs from AWS EC2 instance"""
        print("[DEPLOY-AWS-LOGS] Endpoint called!")
        try:
            from online_deployment import OnlineDeployer
            data = request.get_json()

            instance_id = data.get('instance_id')
            access_key = data.get('access_key')
            secret_key = data.get('secret_key')
            region = data.get('region', 'ap-south-1')
            wait_for_completion = data.get('wait_for_completion', False)
            max_wait_seconds = data.get('max_wait_seconds', 300)

            if not instance_id:
                return jsonify({'error': 'instance_id is required'}), 400
            if not access_key or not secret_key:
                return jsonify({'error': 'AWS credentials (access_key, secret_key) are required'}), 400

            deployer = OnlineDeployer()

            def generate():
                yield f"[LOG] Fetching logs for instance {instance_id} in {region}...\n"

                result = deployer.get_deployment_logs(
                    instance_id=instance_id,
                    aws_access_key=access_key,
                    aws_secret_key=secret_key,
                    region=region,
                    wait_for_completion=wait_for_completion,
                    max_wait_seconds=max_wait_seconds
                )

                # Stream deployer logs
                while True:
                    try:
                        log = deployer.logs.get(timeout=0.1)
                        yield f"{log}\n"
                    except:
                        break

                if result.get('success'):
                    yield "\n" + "=" * 60 + "\n"
                    yield "DEPLOYMENT LOGS\n"
                    yield "=" * 60 + "\n"
                    yield result.get('logs', 'No logs available')
                    yield "\n" + "=" * 60 + "\n"
                    if result.get('completed'):
                        yield "[SUCCESS] Setup completed.\n"
                    else:
                        yield "[INFO] Setup still in progress or status unknown.\n"
                else:
                    yield f"[ERROR] Failed to fetch logs: {result.get('error', 'Unknown error')}\n"

            return Response(stream_with_context(generate()), mimetype='text/plain')

        except Exception as e:
            error_msg = f"Error fetching logs: {str(e)}"
            print(f"[DEPLOY-AWS-LOGS] {error_msg}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': error_msg}), 500

    @app.route('/api/deploy/aws/logs/download', methods=['POST'])
    def download_aws_deployment_logs():
        """Download deployment logs as a file"""
        print("[DEPLOY-AWS-LOGS-DOWNLOAD] Endpoint called!")
        try:
            from online_deployment import OnlineDeployer
            data = request.get_json()

            instance_id = data.get('instance_id')
            access_key = data.get('access_key')
            secret_key = data.get('secret_key')
            region = data.get('region', 'ap-south-1')

            if not instance_id:
                return jsonify({'error': 'instance_id is required'}), 400
            if not access_key or not secret_key:
                return jsonify({'error': 'AWS credentials are required'}), 400

            deployer = OnlineDeployer()
            result = deployer.get_deployment_logs(
                instance_id=instance_id,
                aws_access_key=access_key,
                aws_secret_key=secret_key,
                region=region,
                wait_for_completion=False
            )

            if result.get('success'):
                logs_content = result.get('logs', 'No logs available')
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"deployment_logs_{instance_id}_{timestamp}.txt"

                response = Response(logs_content, mimetype='text/plain')
                response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
                return response
            else:
                return jsonify({'error': result.get('error', 'Failed to fetch logs')}), 500

        except Exception as e:
            error_msg = f"Error downloading logs: {str(e)}"
            print(f"[DEPLOY-AWS-LOGS-DOWNLOAD] {error_msg}")
            return jsonify({'error': error_msg}), 500

    @app.route('/api/deploy/azure', methods=['POST'])
    def deploy_azure():
        """Deploy MCP server to Azure VM"""
        print("[DEPLOY-AZURE] Endpoint called!")
        try:
            from online_deployment import OnlineDeployer
            data = request.get_json()
            
            deployer = OnlineDeployer()
            
            def generate():
                yield "Starting Azure Deployment...\n"
                
                # Get server type and paths
                server_type = data.get('server_type')
                server_path = data.get('server_path')
                config_path = data.get('config_path')
                yaml_file = data.get('yaml_file')
                
                # Auto-detect server path for database servers if not provided
                if not server_path and server_type == 'database':
                    project_root = os.path.dirname(os.path.abspath(__file__))
                    server_path = os.path.join(project_root, 'dbhandler_mcpserver', 'scikiq_pkg_dbutils')
                    yield f"[LOG] Auto-detected database server path: {server_path}\n"
                
                if server_type and server_path:
                    yield f"[LOG] Preparing {server_type} MCP server files from {server_path}\n"
                    if yaml_file:
                        yield f"[LOG] Using specific YAML file: {yaml_file}\n"
                    
                    # For database servers, read connections and selected_tools from config
                    connections = None
                    selected_tools = None
                    if server_type == 'database' and config_path:
                        try:
                            import configparser
                            import os
                            yield f"[LOG] Reading connections from config file: {config_path}\n"
                            yield f"[LOG] Config file exists: {os.path.exists(config_path)}\n"
                            
                            config = configparser.ConfigParser()
                            config.read(config_path, encoding='utf-8')
                            
                            yield f"[LOG] Config sections found: {config.sections()}\n"
                            
                            # Extract connections from config
                            connections = []
                            for section in config.sections():
                                if section.upper() != 'SERVER':
                                    conn = {}
                                    conn['connection_name'] = section
                                    for key, value in config[section].items():
                                        conn[key.lower()] = value
                                    connections.append(conn)
                            
                            yield f"[LOG] Extracted {len(connections)} connections from config\n"
                            
                            # Validate that connections exist (mandatory for database servers)
                            if len(connections) == 0:
                                yield f"[LOG] ERROR: No database connections found in config file. Connections are mandatory for database MCP server.\n"
                                raise ValueError("No database connections found in config file. Please configure at least one database connection before deploying.")
                            
                            # Extract selected tools from SERVER section
                            if 'SERVER' in config and 'ENABLED_TOOLS' in config['SERVER']:
                                selected_tools = [t.strip() for t in config['SERVER']['ENABLED_TOOLS'].split(',') if t.strip()]
                                yield f"[LOG] Extracted {len(selected_tools)} selected tools: {selected_tools}\n"
                            else:
                                yield f"[LOG] No ENABLED_TOOLS found in SERVER section\n"
                        except ValueError as ve:
                            # Re-raise ValueError (validation errors)
                            yield f"[LOG] ERROR: {str(ve)}\n"
                            raise
                        except Exception as e:
                            yield f"[LOG] Warning: Could not read connections from config: {e}\n"
                            import traceback
                            yield f"[LOG] Traceback: {traceback.format_exc()}\n"
                            # If config file exists but couldn't be read, still raise error
                            if os.path.exists(config_path):
                                raise ValueError(f"Failed to read database connections from config file: {e}")
                    
                    # Prepare server files based on type
                    from online_deployment import OnlineDeployer
                    temp_deployer = OnlineDeployer()
                    server_files = temp_deployer._prepare_server_files(
                        server_type=server_type,
                        server_path=server_path,
                        config_path=config_path,
                        yaml_file=yaml_file
                    )
                    yield f"[LOG] Prepared {len(server_files)} server files\n"
                else:
                    server_files = {
                        'app.py': 'print("Hello MCP")',
                        'requirements.txt': 'flask\nmcp'
                    }
                
                result = deployer.deploy_to_azure(
                    subscription_id=data.get('subscription_id'),
                    client_id=data.get('client_id'),
                    client_secret=data.get('client_secret'),
                    tenant_id=data.get('tenant_id'),
                    resource_group=data.get('resource_group', 'mcp-server-rg'),
                    location=data.get('location', 'eastus'),
                    server_files=server_files,
                    server_type=server_type,
                    connections=connections,
                    selected_tools=selected_tools
                )
                
                max_iterations = 1000
                iteration = 0
                empty_iterations = 0
                max_empty_iterations = 30
                while iteration < max_iterations:
                    try:
                        log = deployer.logs.get(timeout=0.5)
                        yield f"{log}\n"
                        empty_iterations = 0
                        iteration += 1
                    except:
                        empty_iterations += 1
                        iteration += 1
                        if empty_iterations < max_empty_iterations:
                            time.sleep(0.5)
                            continue
                        if result is not None:
                            break
                        if iteration < max_iterations - 50:
                            empty_iterations = 0
                            time.sleep(1.0)
                            continue
                        break

            return Response(stream_with_context(generate()), mimetype='text/plain')

        except Exception as e:
            print(f"[DEPLOY-AZURE] Error: {str(e)}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/deploy/remote', methods=['POST'])
    def deploy_remote():
        """Deploy MCP server to remote machine via SSH"""
        print("[DEPLOY-REMOTE] Endpoint called!")
        try:
            from online_deployment import OnlineDeployer
            data = request.get_json()
            
            deployer = OnlineDeployer()
            
            def generate():
                yield "Starting Remote SSH Deployment...\n"
                
                # Get server type and paths
                server_type = data.get('server_type')
                server_path = data.get('server_path')
                config_path = data.get('config_path')
                yaml_file = data.get('yaml_file')
                
                # Auto-detect server path for database servers if not provided
                if not server_path and server_type == 'database':
                    project_root = os.path.dirname(os.path.abspath(__file__))
                    server_path = os.path.join(project_root, 'dbhandler_mcpserver', 'scikiq_pkg_dbutils')
                    yield f"[LOG] Auto-detected database server path: {server_path}\n"
                
                if server_type and server_path:
                    yield f"[LOG] Preparing {server_type} MCP server files from {server_path}\n"
                    if yaml_file:
                        yield f"[LOG] Using specific YAML file: {yaml_file}\n"
                    
                    # For database servers, read connections and selected_tools from config
                    connections = None
                    selected_tools = None
                    if server_type == 'database' and config_path:
                        try:
                            import configparser
                            import os
                            yield f"[LOG] Reading connections from config file: {config_path}\n"
                            yield f"[LOG] Config file exists: {os.path.exists(config_path)}\n"
                            
                            config = configparser.ConfigParser()
                            config.read(config_path, encoding='utf-8')
                            
                            yield f"[LOG] Config sections found: {config.sections()}\n"
                            
                            # Extract connections from config
                            connections = []
                            for section in config.sections():
                                if section.upper() != 'SERVER':
                                    conn = {}
                                    conn['connection_name'] = section
                                    for key, value in config[section].items():
                                        conn[key.lower()] = value
                                    connections.append(conn)
                            
                            yield f"[LOG] Extracted {len(connections)} connections from config\n"
                            
                            # Validate that connections exist (mandatory for database servers)
                            if len(connections) == 0:
                                yield f"[LOG] ERROR: No database connections found in config file. Connections are mandatory for database MCP server.\n"
                                raise ValueError("No database connections found in config file. Please configure at least one database connection before deploying.")
                            
                            # Extract selected tools from SERVER section
                            if 'SERVER' in config and 'ENABLED_TOOLS' in config['SERVER']:
                                selected_tools = [t.strip() for t in config['SERVER']['ENABLED_TOOLS'].split(',') if t.strip()]
                                yield f"[LOG] Extracted {len(selected_tools)} selected tools: {selected_tools}\n"
                            else:
                                yield f"[LOG] No ENABLED_TOOLS found in SERVER section\n"
                        except ValueError as ve:
                            # Re-raise ValueError (validation errors)
                            yield f"[LOG] ERROR: {str(ve)}\n"
                            raise
                        except Exception as e:
                            yield f"[LOG] Warning: Could not read connections from config: {e}\n"
                            import traceback
                            yield f"[LOG] Traceback: {traceback.format_exc()}\n"
                            # If config file exists but couldn't be read, still raise error
                            if os.path.exists(config_path):
                                raise ValueError(f"Failed to read database connections from config file: {e}")
                    
                    # Prepare server files based on type
                    from online_deployment import OnlineDeployer
                    temp_deployer = OnlineDeployer()
                    server_files = temp_deployer._prepare_server_files(
                        server_type=server_type,
                        server_path=server_path,
                        config_path=config_path,
                        yaml_file=yaml_file
                    )
                    yield f"[LOG] Prepared {len(server_files)} server files\n"
                else:
                    server_files = {
                        'app.py': 'print("Hello MCP")',
                        'requirements.txt': 'flask\nmcp'
                    }
                
                result = deployer.deploy_to_remote(
                    host=data.get('host'),
                    username=data.get('username'),
                    password=data.get('password', ''),
                    ssh_key_path=data.get('ssh_key_path'),
                    server_files=server_files,
                    server_type=server_type,
                    connections=connections,
                    selected_tools=selected_tools
                )
                
                max_iterations = 1000
                iteration = 0
                empty_iterations = 0
                max_empty_iterations = 30
                while iteration < max_iterations:
                    try:
                        log = deployer.logs.get(timeout=0.5)
                        yield f"{log}\n"
                        empty_iterations = 0
                        iteration += 1
                    except:
                        empty_iterations += 1
                        iteration += 1
                        if empty_iterations < max_empty_iterations:
                            time.sleep(0.5)
                            continue
                        if result is not None:
                            break
                        if iteration < max_iterations - 50:
                            empty_iterations = 0
                            time.sleep(1.0)
                            continue
                        break

            return Response(stream_with_context(generate()), mimetype='text/plain')

        except Exception as e:
            print(f"[DEPLOY-REMOTE] Error: {str(e)}")
            return jsonify({'error': str(e)}), 500

    # ==================== HELPER FUNCTIONS ====================

    def generate_client_installer_script(installation_path, server_name, server_type, server_config):
        """Generate a cross-platform Python installer script"""
        
        installer_template = f'''#!/usr/bin/env python3
"""
MCP Server Client Installer
Generated by SCIKIQ MCP Studio - Hosted Service
Auto-installs MCP server with virtual environment on client machine
"""

import os
import sys
import subprocess
import platform
import json
import urllib.request
import urllib.error
import zipfile
import shutil
from pathlib import Path

# Configuration
INSTALLATION_PATH = r"{installation_path}"
SERVER_NAME = "{server_name}"
SERVER_TYPE = "{server_type}"
HOSTED_SERVICE_URL = "http://localhost:30211"  # Replace with actual hosted URL
PYTHON_REQUIREMENTS = [
    "mcp>=1.0.0",
    "httpx>=0.24.0",
    "pydantic>=2.0.0"
]

class MCPInstaller:
    def __init__(self):
        self.system = platform.system()
        self.installation_path = Path(INSTALLATION_PATH)
        self.venv_path = self.installation_path / "mcp_venv"
        self.server_path = self.installation_path / SERVER_NAME
        
    def log(self, message, level="INFO"):
        """Log installation progress"""
        print(f"[{{level}}] {{message}}")
        
    def check_python(self):
        """Check if Python 3.8+ is available"""
        try:
            version = sys.version_info
            if version.major < 3 or (version.major == 3 and version.minor < 8):
                raise ValueError(f"Python 3.8+ required, found {{version.major}}.{{version.minor}}")
            self.log(f"Python {{version.major}}.{{version.minor}}.{{version.micro}} detected")
            return True
        except Exception as e:
            self.log(f"Python check failed: {{e}}", "ERROR")
            return False
            
    def create_installation_directory(self):
        """Create installation directory structure"""
        try:
            self.log(f"Creating installation directory: {{self.installation_path}}")
            self.installation_path.mkdir(parents=True, exist_ok=True)
            self.server_path.mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            self.log(f"Failed to create directories: {{e}}", "ERROR")
            return False
            
    def create_virtual_environment(self):
        """Create Python virtual environment"""
        try:
            self.log("Creating virtual environment...")
            
            # Remove existing venv if it exists
            if self.venv_path.exists():
                self.log("Removing existing virtual environment")
                shutil.rmtree(self.venv_path)
            
            # Create new virtual environment
            subprocess.run([
                sys.executable, "-m", "venv", str(self.venv_path)
            ], check=True)
            
            self.log("Virtual environment created successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            self.log(f"Failed to create virtual environment: {{e}}", "ERROR")
            return False
        except Exception as e:
            self.log(f"Unexpected error creating venv: {{e}}", "ERROR")
            return False
            
    def get_venv_python(self):
        """Get path to Python executable in virtual environment"""
        if self.system == "Windows":
            return self.venv_path / "Scripts" / "python.exe"
        else:
            return self.venv_path / "bin" / "python"
            
    def get_venv_pip(self):
        """Get path to pip executable in virtual environment"""
        if self.system == "Windows":
            return self.venv_path / "Scripts" / "pip.exe"
        else:
            return self.venv_path / "bin" / "pip"
            
    def install_requirements(self):
        """Install Python requirements in virtual environment"""
        try:
            pip_executable = self.get_venv_pip()
            
            self.log("Upgrading pip...")
            subprocess.run([
                str(pip_executable), "install", "--upgrade", "pip"
            ], check=True)
            
            self.log("Installing MCP requirements...")
            for package in PYTHON_REQUIREMENTS:
                self.log(f"Installing {{package}}")
                subprocess.run([
                    str(pip_executable), "install", package
                ], check=True)
                
            # Install additional requirements based on server type
            if SERVER_TYPE == "database":
                db_packages = [
                    "psycopg2-binary",  # PostgreSQL
                    "pymysql",          # MySQL
                    "pymongo",          # MongoDB
                    "duckdb",           # DuckDB
                    "sqlalchemy"        # General SQL toolkit
                ]
                for package in db_packages:
                    try:
                        self.log(f"Installing database package: {{package}}")
                        subprocess.run([
                            str(pip_executable), "install", package
                        ], check=True)
                    except subprocess.CalledProcessError:
                        self.log(f"Optional package {{package}} installation failed", "WARNING")
                        
            self.log("All requirements installed successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            self.log(f"Failed to install requirements: {{e}}", "ERROR")
            return False
        except Exception as e:
            self.log(f"Unexpected error installing requirements: {{e}}", "ERROR")
            return False
            
    def download_server_files(self):
        """Download MCP server files from hosted service"""
        try:
            self.log("Downloading MCP server files...")
            
            # Request server package from hosted service
            server_config = {server_config}
            
            request_data = {{
                "server_name": SERVER_NAME,
                "server_type": SERVER_TYPE,
                "server_config": server_config
            }}
            
            # Convert request data to JSON
            json_data = json.dumps(request_data).encode('utf-8')
            
            # Create request
            req = urllib.request.Request(
                f"{{HOSTED_SERVICE_URL}}/api/get-server-package",
                data=json_data,
                headers={{'Content-Type': 'application/json'}}
            )
            
            # Download server package info
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode('utf-8'))
                
            if not result.get('success'):
                raise Exception(f"Server package generation failed: {{result.get('error')}}")
                
            package_info = result['package_info']
            
            # Download each file
            for file_info in package_info['files']:
                file_url = f"{{HOSTED_SERVICE_URL}}{{file_info['download_url']}}"
                file_path = self.server_path / file_info['filename']
                
                self.log(f"Downloading {{file_info['filename']}}...")
                urllib.request.urlretrieve(file_url, file_path)
                
            self.log("Server files downloaded successfully")
            return True
            
        except urllib.error.URLError as e:
            self.log(f"Network error downloading files: {{e}}", "ERROR")
            return False
        except Exception as e:
            self.log(f"Failed to download server files: {{e}}", "ERROR")
            return False
            
    def configure_claude_desktop(self):
        """Configure Claude Desktop to use the installed MCP server"""
        try:
            self.log("Configuring Claude Desktop...")
            
            # Get Claude Desktop config path
            config_path = self.get_claude_desktop_config_path()
            
            if not config_path:
                self.log("Claude Desktop config path not found", "WARNING")
                return False
                
            # Load existing config or create new
            config = {{}}
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    
            # Ensure mcpServers section exists
            if "mcpServers" not in config:
                config["mcpServers"] = {{}}
                
            # Add MCP server configuration
            python_executable = str(self.get_venv_python())
            server_script = str(self.server_path / "mcp_server.py")
            
            config["mcpServers"][SERVER_NAME] = {{
                "command": python_executable,
                "args": [server_script],
                "env": {{}}
            }}
            
            # Add config file for database servers
            if SERVER_TYPE == "database":
                config_ini_path = str(self.server_path / "config.ini")
                config["mcpServers"][SERVER_NAME]["args"].extend(["--config-file", config_ini_path])
                
            # Save configuration
            config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
                
            self.log("Claude Desktop configured successfully")
            return True
            
        except Exception as e:
            self.log(f"Failed to configure Claude Desktop: {{e}}", "ERROR")
            return False
            
    def get_claude_desktop_config_path(self):
        """Get Claude Desktop configuration path"""
        if self.system == "Windows":
            return Path.home() / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json"
        elif self.system == "Darwin":
            return Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
        elif self.system == "Linux":
            return Path.home() / ".config" / "Claude" / "claude_desktop_config.json"
        else:
            return None
            
    def create_run_script(self):
        """Create convenience script to run MCP server"""
        try:
            python_executable = self.get_venv_python()
            server_script = self.server_path / "mcp_server.py"
            
            if self.system == "Windows":
                # Create .bat file for Windows
                script_path = self.installation_path / f"run_{{SERVER_NAME}}.bat"
                bat_content = "@echo off\\n"
                bat_content += "echo Starting {{SERVER_NAME}} MCP Server...\\n"
                bat_content += '"{{python_executable}}" "{{server_script}}"\\n'
                bat_content += "pause"
                script_content = bat_content
            else:
                # Create .sh file for Unix-like systems
                script_path = self.installation_path / f"run_{{SERVER_NAME}}.sh"
                sh_content = "#!/bin/bash\\n"
                sh_content += 'echo "Starting {{SERVER_NAME}} MCP Server..."\\n'
                sh_content += '"{{python_executable}}" "{{server_script}}"'
                script_content = sh_content
                
            with open(script_path, 'w') as f:
                f.write(script_content)
                
            # Make executable on Unix-like systems
            if self.system != "Windows":
                script_path.chmod(0o755)
                
            self.log(f"Run script created: {{script_path}}")
            return True
            
        except Exception as e:
            self.log(f"Failed to create run script: {{e}}", "ERROR")
            return False
            
    def install(self):
        """Main installation process"""
        self.log("=" * 60)
        self.log("MCP Server Installation Starting")
        self.log("=" * 60)
        
        steps = [
            ("Checking Python version", self.check_python),
            ("Creating installation directory", self.create_installation_directory),
            ("Creating virtual environment", self.create_virtual_environment),
            ("Installing Python requirements", self.install_requirements),
            ("Downloading server files", self.download_server_files),
            ("Configuring Claude Desktop", self.configure_claude_desktop),
            ("Creating run script", self.create_run_script)
        ]
        
        for step_name, step_func in steps:
            self.log(f"Step: {{step_name}}")
            if not step_func():
                self.log(f"Installation failed at step: {{step_name}}", "ERROR")
                return False
                
        self.log("=" * 60)
        self.log("Installation completed successfully!")
        self.log("=" * 60)
        self.log(f"MCP Server installed in: {{self.installation_path}}")
        self.log("Please restart Claude Desktop to use the new MCP server.")
        
        return True

def main():
    """Main entry point"""
    try:
        installer = MCPInstaller()
        success = installer.install()
        
        if success:
            input("\\nPress Enter to continue...")
            sys.exit(0)
        else:
            input("\\nInstallation failed. Press Enter to exit...")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\\nInstallation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\\nUnexpected error: {{e}}")
        input("Press Enter to exit...")
        sys.exit(1)

if __name__ == "__main__":
    main()
'''
        
        return installer_template

    def generate_server_package(server_name, server_type, server_config):
        """Generate server package files for download"""
        try:
            package_files = []
            
            if server_type == "swagger":
                # Generate Swagger-based MCP server
                swagger_url = server_config.get('swagger_url', '')
                base_url = server_config.get('base_url', '')
                enable_oauth = server_config.get('enable_oauth', False)
                oauth_config = server_config.get('oauth_config', {}) if enable_oauth else None
                
                # Parse swagger and generate tools
                from swagger_parser import parse_swagger_from_url
                endpoints = parse_swagger_from_url(swagger_url, base_url)
                
                # Generate MCP server code
                server_code, oauth_requirements = generate_mcp_server_code(endpoints, base_url, enable_oauth, oauth_config)
                
                # Save server file
                server_filename = f"mcp_server.py"
                server_path = os.path.join('generated_servers', server_filename)
                
                with open(server_path, 'w', encoding='utf-8') as f:
                    f.write(server_code)
                    
                package_files.append({
                    'filename': server_filename,
                    'download_url': f'/generated/{server_filename}',
                    'type': 'server'
                })
                
            elif server_type == "database":
                # Generate database MCP server files
                connections = server_config.get('connections', [])
                
                # Generate config.ini
                config_content = generate_database_config_ini(connections, selected_tools=None)
                config_filename = "config.ini"
                config_path = os.path.join('generated_servers', config_filename)
                
                with open(config_path, 'w', encoding='utf-8') as f:
                    f.write(config_content)
                    
                package_files.append({
                    'filename': config_filename,
                    'download_url': f'/generated/{config_filename}',
                    'type': 'config'
                })
                
                # Copy database MCP server files
                # This would copy from your dbhandler_mcpserver directory
                # For now, create a simple server script
                server_code = generate_database_mcp_server_wrapper()
                server_filename = "mcp_server.py"
                server_path = os.path.join('generated_servers', server_filename)
                
                with open(server_path, 'w', encoding='utf-8') as f:
                    f.write(server_code)
                    
                package_files.append({
                    'filename': server_filename,
                    'download_url': f'/generated/{server_filename}',
                    'type': 'server'
                })
                
            elif server_type == "codebase":
                # Generate codebase-based MCP server
                project_path = server_config.get('project_path', '')
                api_server_url = server_config.get('api_server_url', '')
                enable_oauth = server_config.get('enable_oauth', False)
                oauth_config = server_config.get('oauth_config', {}) if enable_oauth else None
                
                # Scan project for endpoints
                from intelligent_mcp_converter import scan_for_apis
                apis_result = scan_for_apis(project_path)
                
                if apis_result.get('success'):
                    endpoints = apis_result.get('apis', [])
                    server_code, oauth_requirements = generate_mcp_server_code(endpoints, api_server_url, enable_oauth, oauth_config)
                    
                    server_filename = f"mcp_server.py"
                    server_path = os.path.join('generated_servers', server_filename)
                    
                    with open(server_path, 'w', encoding='utf-8') as f:
                        f.write(server_code)
                        
                    package_files.append({
                        'filename': server_filename,
                        'download_url': f'/generated/{server_filename}',
                        'type': 'server'
                    })
            
            return {
                'server_name': server_name,
                'server_type': server_type,
                'files': package_files,
                'total_files': len(package_files)
            }
            
        except Exception as e:
            raise Exception(f"Failed to generate server package: {str(e)}")

    def generate_database_mcp_server_wrapper():
        """Generate a wrapper script for database MCP server"""
        return '''#!/usr/bin/env python3
"""
Database MCP Server Wrapper
Auto-generated by SCIKIQ MCP Studio
"""

import sys
import os
from pathlib import Path

# Add the current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

try:
    # Import and run the database MCP server
    from dbhandler_mcpserver.scikiq_pkg_dbutils.run_mcp_server import main
    
    if __name__ == "__main__":
        main()
        
except ImportError as e:
    print(f"Error: Database MCP server modules not found: {e}")
    print("Please ensure the database MCP server package is properly installed.")
    sys.exit(1)
except Exception as e:
    print(f"Error running database MCP server: {e}")
    sys.exit(1)
'''

    def get_installer_instructions():
        """Get installation instructions for users"""
        return {
            'steps': [
                "Download the installer script by clicking the download button",
                "Choose your installation directory (or use the default)",
                "Run the installer script: python [installer_name].py",
                "The installer will automatically:",
                "  - Create a virtual environment",
                "  - Install required packages",
                "  - Download MCP server files",
                "  - Configure Claude Desktop",
                "Restart Claude Desktop to use your new MCP server"
            ],
            'requirements': [
                "Python 3.8 or higher",
                "Internet connection for package downloads",
                "Claude Desktop installed (for automatic configuration)"
            ],
            'troubleshooting': [
                "If installation fails, check Python version and internet connection",
                "On Windows, you may need to run as Administrator",
                "On macOS/Linux, ensure you have write permissions to the installation directory"
            ]
        }

    def generate_mcp_server_code(endpoints, api_server_url, enable_oauth, oauth_config):
        """
        Generate MCP server code from endpoints
        """
        try:
            # Create converter instance just for code generation
            from intelligent_mcp_converter import IntelligentMCPConverter
            converter = IntelligentMCPConverter(project_root=".", base_url=api_server_url)
            
            # Manually set endpoints
            converter.endpoints = endpoints
            
            # Convert to tools
            converter.convert_to_mcp_tools()
            
            # Generate code using a temporary file
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.py') as tf:
                temp_path = tf.name
            
            # Close the file handle so converter can write to it
            
            converter.generate_mcp_server_code(temp_path)
            
            with open(temp_path, 'r', encoding='utf-8') as f:
                code = f.read()
                
            try:
                os.unlink(temp_path)
            except:
                pass
            
            return code, []
            
        except Exception as e:
            print(f"Error generating MCP server code: {e}")
            import traceback
            traceback.print_exc()
            return f"# Error generating code: {str(e)}", []

    print("[OK] MCP Studio routes initialized")
