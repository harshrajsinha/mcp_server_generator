"""
Swagger/OpenAPI parser for MCP Studio
Adapted from harshrajsinha/rest_api_mcp_tools_generator
"""
import requests
import yaml
import json
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)


class SwaggerParser:
    """
    Parses Swagger/OpenAPI specifications and extracts API endpoint information
    """

    def __init__(self, swagger_url: str, api_base_url: str, **kwargs):
        self.swagger_url = swagger_url
        self.api_base_url = api_base_url
        self.spec = None

        # Extract additional configuration
        self.auth_type = kwargs.get('auth_type', 'none')
        self.auth_token = kwargs.get('auth_token')
        self.auth_user = kwargs.get('auth_user')
        self.auth_pass = kwargs.get('auth_pass')
        self.verify_ssl = kwargs.get('verify_ssl', True)
        self.timeout = kwargs.get('timeout', 30)

    def fetch_swagger_spec(self) -> Dict[str, Any]:
        """
        Fetch and validate Swagger specification from URL
        """
        try:
            # Build headers for authentication
            headers = {}
            auth = None

            if self.auth_type == 'bearer' and self.auth_token:
                headers['Authorization'] = f'Bearer {self.auth_token}'
            elif self.auth_type == 'api_key' and self.auth_token:
                headers['X-API-Key'] = self.auth_token
            elif self.auth_type == 'basic' and self.auth_user and self.auth_pass:
                auth = (self.auth_user, self.auth_pass)

            # Make request with SSL verification and authentication
            response = requests.get(
                self.swagger_url,
                headers=headers,
                auth=auth,
                verify=self.verify_ssl,
                timeout=self.timeout
            )
            response.raise_for_status()

            # Try to parse as JSON first, then YAML
            try:
                spec = response.json()
            except json.JSONDecodeError:
                try:
                    spec = yaml.safe_load(response.text)
                except yaml.YAMLError as ye:
                    raise Exception(f"Invalid YAML/JSON format: {str(ye)}")

            # Basic validation
            self._basic_spec_validation(spec)

            self.spec = spec
            return spec

        except requests.RequestException as e:
            raise Exception(f"Failed to fetch Swagger spec: {str(e)}")
        except Exception as e:
            raise Exception(f"Error parsing Swagger spec: {str(e)}")

    def _basic_spec_validation(self, spec: Dict[str, Any]) -> None:
        """
        Perform basic validation to ensure it's a valid Swagger/OpenAPI spec
        """
        if not isinstance(spec, dict):
            raise Exception("Specification must be a JSON object")

        swagger_version = spec.get('swagger')
        openapi_version = spec.get('openapi')

        if not swagger_version and not openapi_version:
            raise Exception("Missing 'swagger' or 'openapi' version field")

        if not spec.get('info'):
            raise Exception("Missing 'info' section")

        if not spec.get('paths'):
            logger.warning("No 'paths' section found in specification")

    def extract_endpoints(self) -> List[Dict[str, Any]]:
        """
        Extract all API endpoints from the Swagger specification
        """
        if not self.spec:
            raise Exception("Swagger spec not loaded. Call fetch_swagger_spec() first.")

        endpoints = []
        paths = self.spec.get('paths', {})

        for path, methods in paths.items():
            for method, operation in methods.items():
                if method.lower() in ['get', 'post', 'put', 'delete', 'patch', 'head', 'options']:
                    endpoint_info = self._extract_operation_info(path, method, operation)
                    endpoints.append(endpoint_info)

        return endpoints

    def _extract_operation_info(self, path: str, method: str, operation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract information from a single operation
        """
        return {
            'route': path,
            'methods': [method.upper()],
            'function_name': operation.get('operationId', path.replace('/', '_').replace('{', '').replace('}', '')),
            'docstring': operation.get('summary', '') or operation.get('description', ''),
            'parameters': self._extract_parameters(operation.get('parameters', []), operation.get('requestBody', {})),
            'tags': operation.get('tags', []),
        }

    def _extract_parameters(self, parameters: List[Dict[str, Any]], request_body: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract and normalize parameter information
        """
        extracted_params = []

        # Extract query/path/header parameters
        for param in parameters:
            param_info = {
                'name': param.get('name', ''),
                'type': self._get_parameter_type(param),
                'description': param.get('description', ''),
                'required': param.get('required', False),
                'location': param.get('in', 'query'),  # query, path, header, cookie
            }
            extracted_params.append(param_info)

        # Extract request body parameters (OpenAPI 3.0)
        if request_body:
            content = request_body.get('content', {})
            json_content = content.get('application/json', {})
            schema = json_content.get('schema', {})

            if schema:
                properties = schema.get('properties', {})
                required_fields = schema.get('required', [])

                for prop_name, prop_schema in properties.items():
                    param_info = {
                        'name': prop_name,
                        'type': prop_schema.get('type', 'string'),
                        'description': prop_schema.get('description', ''),
                        'required': prop_name in required_fields,
                        'location': 'body',
                    }
                    extracted_params.append(param_info)

        return extracted_params

    def _get_parameter_type(self, param: Dict[str, Any]) -> str:
        """
        Determine the parameter type from schema (handles both Swagger 2.0 and OpenAPI 3.0)
        """
        # For OpenAPI 3.0, type is in schema
        schema = param.get('schema', {})
        param_type = schema.get('type')

        # For Swagger 2.0, type is directly in parameter
        if not param_type:
            param_type = param.get('type', 'string')

        # Handle array types
        if param_type == 'array':
            items_schema = schema.get('items', {})
            items_type = items_schema.get('type', 'string')

            if not items_type:
                items_obj = param.get('items', {})
                items_type = items_obj.get('type', 'string')

            return f"array[{items_type}]"

        return param_type or 'string'


def scan_codebase_for_apis(project_path: str, source_file: str = None) -> Dict[str, Any]:
    """
    Scan codebase for APIs using IntelligentMCPConverter
    """
    try:
        from intelligent_mcp_converter import scan_for_apis
        
        # Use intelligent scanner
        result = scan_for_apis(project_path)
        
        if not result['success']:
            return {'success': False, 'error': result.get('error')}
            
        # Convert to format expected by UI
        api_definitions = []
        for endpoint in result['apis']:
            # Handle EndpointUnderstanding object
            api_definitions.append({
                'route': endpoint.path,
                'method': endpoint.methods[0],
                'function_name': endpoint.function_name,
                'docstring': endpoint.purpose,
                'parameters': endpoint.parameters
            })
            
        return {
            'success': True,
            'api_definitions': api_definitions,
            'file_tree': {}, 
            'intelligence': {
                'total_apis': len(api_definitions),
                'confidence': 0.9
            }
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}

