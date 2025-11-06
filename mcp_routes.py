"""
MCP Studio Routes
Standalone API to MCP conversion tool
"""

from flask import render_template, request, jsonify, send_from_directory, Response
from flask import stream_with_context
from pathlib import Path
from dotenv import load_dotenv
import os
import json
import yaml
import platform
from datetime import datetime

# Load environment variables from .env file
load_dotenv()


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

        tool_config = {
            'name': tool_name,
            'description': description,
            'endpoint': endpoint,
            'method': method,
            'input_schema': {
                'type': 'object',
                'properties': properties,
                'required': required
            }
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
from pathlib import Path
from typing import List, Dict, Any

# Server instance with descriptive name and version
# Following MCP SDK initialization pattern
server = Server("scikiq-mcp-autoAPI")

# Storage for all loaded tools and handlers
all_tools: List[types.Tool] = []
tool_handlers: Dict[str, Dict[str, Any]] = {}

# Track server metadata
SERVER_VERSION = "1.0.0"
SERVER_DESCRIPTION = "Dynamic API to MCP Tools Loader"


def log_message(level: str, message: str) -> None:
    """Log messages to stderr for debugging"""
    print(f"[MCP Loader] [{level.upper()}] {message}", file=sys.stderr)


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
                    'base_url': base_url,
                    'endpoint': endpoint,
                    'method': method,
                    'source': yaml_file_path
                }

                loaded_count += 1
                log_message("info", f"Loaded tool: {tool_name} ({method} {endpoint})")

            except Exception as e:
                log_message("error", f"Error loading tool #{idx + 1} from {yaml_file_path}: {str(e)}")
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
async def list_tools() -> list[types.Tool]:
    """
    List all loaded tools

    Returns list of available MCP tools with descriptions
    """
    return all_tools


def validate_tool_arguments(tool_name: str, arguments: dict, input_schema: dict) -> tuple[bool, str]:
    """
    Validate tool arguments against input schema
    Following MCP best practices for parameter validation

    Args:
        tool_name: Name of the tool being called
        arguments: Arguments provided by the user
        input_schema: JSON Schema for expected parameters

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        # Check required parameters
        required_params = input_schema.get('required', [])
        for param in required_params:
            if param not in arguments:
                return False, f"Missing required parameter: '{param}'"

        # Validate parameter types (basic validation)
        properties = input_schema.get('properties', {})
        for arg_name, arg_value in arguments.items():
            if arg_name in properties:
                expected_type = properties[arg_name].get('type', 'string')

                # Basic type checking
                if expected_type == 'string' and not isinstance(arg_value, str):
                    return False, f"Parameter '{arg_name}' must be a string"
                elif expected_type == 'number' and not isinstance(arg_value, (int, float)):
                    return False, f"Parameter '{arg_name}' must be a number"
                elif expected_type == 'integer' and not isinstance(arg_value, int):
                    return False, f"Parameter '{arg_name}' must be an integer"
                elif expected_type == 'boolean' and not isinstance(arg_value, bool):
                    return False, f"Parameter '{arg_name}' must be a boolean"
                elif expected_type == 'array' and not isinstance(arg_value, list):
                    return False, f"Parameter '{arg_name}' must be an array"
                elif expected_type == 'object' and not isinstance(arg_value, dict):
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


def generate_mcp_server_code(mcp_tools, base_url="http://localhost:9321"):
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

    server_template = f'''"""
Auto-generated MCP Server
Generated by SCIKIQ MCP Studio
"""

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types
import httpx

server = Server("scikiq-mcp-autoAPI")

# Base URL for the API server
BASE_URL = "{base_url}"


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
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
'''

    return server_template


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

        except Exception as e:
            import traceback
            traceback.print_exc()
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

                tool_definition = {
                    'name': function_name.replace('glic_', '').replace('_', '-'),
                    'description': description,
                    'endpoint': route,
                    'method': methods[0],
                    'parameters': parameters
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
            
            if not server_path:
                return jsonify({
                    'success': False,
                    'error': 'Server path is required'
                }), 400
            
            if not connections:
                return jsonify({
                    'success': False,
                    'error': 'At least one database connection is required'
                }), 400
            
            # Generate config.ini content
            config_content = generate_database_config_ini(connections)
            
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

    @app.route('/api/get-database-config', methods=['GET'])
    def mcp_get_database_config():
        """Get the content of a database config.ini file"""
        try:
            config_path = request.args.get('path')
            
            if not config_path or not Path(config_path).exists():
                return jsonify({
                    'success': False,
                    'error': 'Config file not found'
                }), 404
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config_content = f.read()
            
            return jsonify({
                'success': True,
                'config_content': config_content
            })
            
        except Exception as e:
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
            
            if not all([config_path, server_path, server_name]):
                return jsonify({
                    'success': False,
                    'error': 'Missing required parameters'
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


    def generate_database_config_ini(connections):
        """Generate config.ini content from database connections"""
        config_lines = []
        config_lines.append("# Database MCP Server Configuration")
        config_lines.append("# Generated by MCP Studio")
        config_lines.append(f"# Created: {datetime.now().isoformat()}")
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
                host = conn.get('host', 'localhost')
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
                elif db_type in ['POSTGRES', 'MYSQL', 'SQLSERVER']:
                    # Add default schema
                    if db_type == 'POSTGRES':
                        config_lines.append("SCHEMA=public")
                    elif db_type == 'SQLSERVER':
                        config_lines.append("SCHEMA=dbo")
                
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
            'BIGQUERY': 443
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


    print("[OK] MCP Studio routes initialized")
