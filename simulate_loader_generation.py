
import os
from typing import List

def simulate_loader_generation():
    template_path = r"c:\DAAS\MCP POC\gaurav\dbhandler_mcpserver\scikiq_pkg_dbutils_online\remote_mcp_server_admin.py"
    
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            code = f.read()
            
        adapted_code = code
        
        # Add YAML tool loader class (FIXED)
        yaml_loader_class = '''

class YAMLToolLoader:
    """Load MCP tools from YAML files"""
    
    def __init__(self, yaml_paths: List[str]):
        self.yaml_paths = yaml_paths
        self.tools = []
        self.load_tools()
    
    def load_tools(self):
        """Load tools from all YAML files"""
        for yaml_path in self.yaml_paths:
            if not os.path.exists(yaml_path):
                logger.warning(f"YAML file not found: {yaml_path}")
                continue
            
            try:
                with open(yaml_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                
                if not data or 'tools' not in data:
                    logger.warning(f"No tools found in {yaml_path}")
                    continue
                
                tools_data = data['tools']
                base_url = data.get('base_url', 'http://localhost:8000')
                
                for tool_data in tools_data:
                    # Handle both snake_case and camelCase input schema
                    input_schema = tool_data.get('input_schema') or tool_data.get('inputSchema') or {}
                    
                    # Ensure type: object is present
                    if 'type' not in input_schema:
                        input_schema['type'] = 'object'
                        
                    tool = {
                        "name": tool_data['name'],
                        "description": tool_data.get('description', ''),
                        "inputSchema": input_schema,
                        "endpoint": tool_data.get('endpoint', ''),
                        "method": tool_data.get('method', 'GET'),
                        "base_url": base_url
                    }
                    self.tools.append(tool)
                
                logger.info(f"Loaded {len(tools_data)} tools from {yaml_path}")
            except Exception as e:
                logger.error(f"Error loading YAML file {yaml_path}: {e}")
    
    async def list_tools(self):
        """List all loaded tools"""
        return {"tools": [
            {
                "name": tool["name"],
                "description": tool["description"],
                "inputSchema": tool["inputSchema"]
            }
            for tool in self.tools
        ]}
    
    async def call_tool(self, name: str, arguments: dict):
        """Call a tool by name"""
        tool = next((t for t in self.tools if t["name"] == name), None)
        if not tool:
            return {
                "content": [{"type": "text", "text": f"Tool '{name}' not found"}],
                "isError": True
            }
        
        try:
            base_url = tool['base_url'].rstrip('/')
            endpoint = tool['endpoint'].lstrip('/')
            url = f"{base_url}/{endpoint}"
            method = tool['method'].upper()
            
            async with httpx.AsyncClient() as client:
                if method == "GET":
                    response = await client.get(url, params=arguments, timeout=30.0)
                elif method == "POST":
                    response = await client.post(url, json=arguments, timeout=30.0)
                elif method == "PUT":
                    response = await client.put(url, json=arguments, timeout=30.0)
                elif method == "DELETE":
                    response = await client.delete(url, params=arguments, timeout=30.0)
                else:
                    return {
                        "content": [{"type": "text", "text": f"Unsupported HTTP method: {method}"}],
                        "isError": True
                    }
                
                response.raise_for_status()
                result_text = response.text
                
                return {
                    "content": [{"type": "text", "text": result_text}],
                    "isError": False
                }
        except Exception as e:
            return {
                "content": [{"type": "text", "text": f"Error calling tool: {str(e)}"}],
                "isError": True
            }
'''
        
        fast_mcp_replacement = '''
class FastMCPServer:
    """MCP server using YAML-loaded tools"""
    
    def __init__(self, name: str, yaml_paths: List[str]):
        self.name = name
        self.tool_loader = YAMLToolLoader(yaml_paths)
        self._tools = self.tool_loader.tools
    
    async def list_tools(self):
        """List available tools"""
        return await self.tool_loader.list_tools()
    
    async def call_tool(self, name: str, arguments: dict):
        """Call a tool with arguments"""
        return await self.tool_loader.call_tool(name, arguments)
'''
        
        # Insert YAML loader class before FastMCPServer
        adapted_code = adapted_code.replace(
            'class FastMCPServer:',
            yaml_loader_class + '\n' + fast_mcp_replacement + '\n\nclass FastMCPServer_OLD:'
        )
        
        # Update RemoteMCPServerWithAdmin to accept YAML paths
        adapted_code = adapted_code.replace(
            'config_path: str | None = None,',
            'yaml_paths: list[str] | None = None,'
        ).replace(
            'self.config_path = config_path or os.getenv("CONFIG_PATH", "config.ini")',
            'self.yaml_paths = yaml_paths or []'
        ).replace(
            'self.mcp_server = FastMCPServer("SciKiq DB Utils", self.config_path)',
            'self.mcp_server = FastMCPServer("MCP API Server", self.yaml_paths)'
        ).replace(
            '"config_path": self.config_path',
            '"yaml_paths": self.yaml_paths'
        ).replace(
            'logger.info(f"🔧 Config: {self.config_path}")',
            'logger.info(f"🔧 YAML Files: {self.yaml_paths}")'
        ).replace(
            '<p><strong>Database Tools:</strong>',
            '<p><strong>MCP Tools:</strong>'
        ).replace(
            'len(self.mcp_server.tool_registry._tools)',
            'len(self.mcp_server._tools)'
        )
        
        adapted_code = adapted_code.replace(
            '@click.option("--config-path",',
            '@click.option("--yaml-files", multiple=True, type=click.Path(exists=True), help="YAML tool files to load")\n@click.option("--config-path-unused",'
        ).replace(
            'def main(host: str, port: int, config_path: str, db_path: str, create_admin: str, debug: bool)',
            'def main(host: str, port: int, config_path_unused: str, db_path: str, create_admin: str, debug: bool, yaml_files: tuple)'
        ).replace(
            '"""Remote MCP Server with Admin Interface"""',
            '"""MCP Server with Admin Interface - Load tools from YAML files"""'
        ).replace(
            'config_path=config_path,',
            'yaml_paths=list(yaml_files) if yaml_files else [],'
        )
        
        adapted_code = adapted_code.replace(
            'import uvicorn',
            'import uvicorn\nimport yaml\nimport httpx'
        )
        
        with open("debug_generated_loader.py", "w", encoding="utf-8") as f:
            f.write(adapted_code)
            
        print("Successfully generated debug_generated_loader.py")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    simulate_loader_generation()
