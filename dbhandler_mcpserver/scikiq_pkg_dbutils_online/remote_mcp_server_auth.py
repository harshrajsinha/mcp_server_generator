#!/usr/bin/env python3
"""
SciKiq DB Utils - Remote MCP Server with OAuth 2.1 Authentication

This module creates a remote MCP server that supports OAuth 2.1 authentication
as required by the MCP specification for HTTP-based transports.

Features:
- OAuth 2.1 with PKCE support
- Authorization Server Metadata Discovery (RFC8414)
- Dynamic Client Registration (RFC7591)  
- Bearer token authentication
- Proper 401/403 error handling
- CORS support for web clients
- Production-ready deployment
- Claude Desktop integration
"""

import asyncio
import base64
import contextlib
import hashlib
import json
import logging
import os
import secrets
import sys
import time
import uuid
from collections.abc import AsyncIterator
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional
from urllib.parse import parse_qs, urlencode, urlparse

import click
import uvicorn
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.routing import Mount, Route
from starlette.responses import Response, JSONResponse, RedirectResponse, HTMLResponse
from starlette.requests import Request
from starlette.types import Receive, Scope, Send
from starlette.middleware.base import BaseHTTPMiddleware

# Add the package to Python path
package_root = Path(__file__).parent
sys.path.insert(0, str(package_root))

# Import our existing MCP server tools
from scikiq_dbutils.mcp_server.config.manager import ConfigManager
from scikiq_dbutils.mcp_server.config.ini_parser import IniConfigParser
from scikiq_dbutils.mcp_server.wrappers.connection_manager import ConnectionManager
from scikiq_dbutils.mcp_server.tools.registry import ToolRegistry
from scikiq_dbutils.mcp_server.wrappers.db_wrapper import DatabaseWrapper


logger = logging.getLogger(__name__)


class OAuthTokenStore:
    """Simple in-memory token store for OAuth tokens"""
    
    def __init__(self):
        self.clients: Dict[str, Dict[str, Any]] = {}  # client_id -> client_data
        self.authorization_codes: Dict[str, Dict[str, Any]] = {}  # code -> code_data
        self.access_tokens: Dict[str, Dict[str, Any]] = {}  # token -> token_data
        self.refresh_tokens: Dict[str, Dict[str, Any]] = {}  # refresh_token -> token_data
    
    def create_client(self, client_name: str = "MCP Client") -> Dict[str, Any]:
        """Create a new OAuth client (public client, no secret)"""
        client_id = f"mcp_client_{secrets.token_urlsafe(16)}"
        client_data = {
            "client_id": client_id,
            "client_name": client_name,
            "client_secret": None,  # Public client
            "redirect_uris": ["http://localhost:*", "https://localhost:*"],
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "token_endpoint_auth_method": "none",  # Public client
            "created_at": datetime.utcnow().isoformat()
        }
        self.clients[client_id] = client_data
        return client_data
    
    def get_client(self, client_id: str) -> Optional[Dict[str, Any]]:
        """Get client data by client_id"""
        return self.clients.get(client_id)
    
    def create_authorization_code(self, client_id: str, redirect_uri: str, code_challenge: str, 
                                code_challenge_method: str, scope: str = "mcp") -> str:
        """Create authorization code"""
        code = secrets.token_urlsafe(32)
        code_data = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "code_challenge": code_challenge,
            "code_challenge_method": code_challenge_method,
            "scope": scope,
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(minutes=10)
        }
        self.authorization_codes[code] = code_data
        return code
    
    def get_authorization_code(self, code: str) -> Optional[Dict[str, Any]]:
        """Get and consume authorization code"""
        code_data = self.authorization_codes.pop(code, None)
        if code_data and code_data["expires_at"] > datetime.utcnow():
            return code_data
        return None
    
    def create_access_token(self, client_id: str, scope: str = "mcp") -> Dict[str, str]:
        """Create access and refresh tokens"""
        access_token = f"mcp_access_{secrets.token_urlsafe(32)}"
        refresh_token = f"mcp_refresh_{secrets.token_urlsafe(32)}"
        
        token_data = {
            "client_id": client_id,
            "scope": scope,
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(hours=1)  # 1 hour expiry
        }
        
        self.access_tokens[access_token] = token_data.copy()
        self.refresh_tokens[refresh_token] = token_data.copy()
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": 3600,
            "scope": scope
        }
    
    def validate_access_token(self, access_token: str) -> Optional[Dict[str, Any]]:
        """Validate access token"""
        token_data = self.access_tokens.get(access_token)
        if token_data and token_data["expires_at"] > datetime.utcnow():
            return token_data
        return None
    
    def refresh_access_token(self, refresh_token: str) -> Optional[Dict[str, str]]:
        """Refresh access token"""
        token_data = self.refresh_tokens.get(refresh_token)
        if not token_data:
            return None
        
        # Remove old tokens
        old_access_token = None
        for token, data in self.access_tokens.items():
            if data["client_id"] == token_data["client_id"] and data["created_at"] == token_data["created_at"]:
                old_access_token = token
                break
        
        if old_access_token:
            del self.access_tokens[old_access_token]
        del self.refresh_tokens[refresh_token]
        
        # Create new tokens
        return self.create_access_token(token_data["client_id"], token_data["scope"])


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Middleware to handle OAuth 2.1 Bearer token authentication"""
    
    def __init__(self, app, token_store: OAuthTokenStore, require_auth: bool = True):
        super().__init__(app)
        self.token_store = token_store
        self.require_auth = require_auth
        
        # Public endpoints that don't require authentication
        self.public_endpoints = {
            "/health",
            "/mcp/info", 
            "/.well-known/oauth-authorization-server",
            "/authorize",
            "/token", 
            "/register"
        }
    
    async def dispatch(self, request: Request, call_next):
        # Skip authentication for public endpoints
        if not self.require_auth or request.url.path in self.public_endpoints:
            return await call_next(request)
        
        # Extract Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return JSONResponse(
                {"error": "authorization_required", "message": "Authorization header required"}, 
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Parse Bearer token
        try:
            scheme, token = auth_header.split(" ", 1)
            if scheme.lower() != "bearer":
                raise ValueError("Invalid scheme")
        except ValueError:
            return JSONResponse(
                {"error": "invalid_token", "message": "Invalid authorization header format"}, 
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Validate token
        token_data = self.token_store.validate_access_token(token)
        if not token_data:
            return JSONResponse(
                {"error": "invalid_token", "message": "Invalid or expired access token"}, 
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Add token data to request state
        request.state.token_data = token_data
        
        return await call_next(request)


class FastMCPServer:
    """FastMCP-style server using our existing tools"""
    
    def __init__(self, name: str, config_path: str):
        self.name = name
        self.config_path = config_path
        
        # Initialize our existing components
        try:
            enabled_tools = None
            if os.path.exists(config_path):
                parser = IniConfigParser(config_path)
                connection_configs = parser.parse_all_connections()
                # Get enabled tools from config if available
                if hasattr(parser, 'get_enabled_tools'):
                    enabled_tools = parser.get_enabled_tools()
                    if enabled_tools:
                        logger.info(f"Loaded enabled tools filter: {len(enabled_tools)} tools enabled")
            else:
                logger.warning(f"Config file {config_path} not found, using empty configuration")
                connection_configs = {}
                
            self.connection_manager = ConnectionManager(connection_configs)
            self.db_wrapper = DatabaseWrapper(self.connection_manager)
            self.tool_registry = ToolRegistry(self.db_wrapper, enabled_tools=enabled_tools)
            
        except Exception as e:
            logger.error(f"Failed to initialize MCP server: {e}")
            raise
    
    async def list_tools(self):
        """List available tools"""
        try:
            # Use the registry's list_tools method
            tools_data = self.tool_registry.list_tools()
            return {"tools": tools_data}
        except Exception as e:
            logger.error(f"Error listing tools: {e}")
            return {"tools": []}
    
    async def call_tool(self, name: str, arguments: dict):
        """Call a tool with arguments"""
        try:
            from scikiq_dbutils.mcp_server.protocol.messages import MCPToolCall
            
            # Create tool call object
            tool_call = MCPToolCall(name=name, arguments=arguments)
            
            # Execute the tool using the registry
            result = self.tool_registry.execute_tool(tool_call)
            
            # Convert result to the expected format
            if hasattr(result, 'is_error') and result.is_error:
                return {
                    "content": [{"type": "text", "text": result.content.get("message", "Tool execution failed")}],
                    "isError": True
                }
            else:
                # Success case
                if hasattr(result, 'content'):
                    if isinstance(result.content, dict):
                        content_text = str(result.content)
                    else:
                        content_text = str(result.content)
                else:
                    content_text = str(result)
                
                return {
                    "content": [{"type": "text", "text": content_text}],
                    "isError": False
                }
                
        except Exception as e:
            logger.error(f"Error calling tool {name}: {e}")
            return {
                "content": [{"type": "text", "text": f"Error executing tool: {str(e)}"}],
                "isError": True
            }


class RemoteMCPServer:
    """Remote MCP Server with OAuth 2.1 Authentication"""
    
    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 3000,
        config_path: str | None = None,
        cors_origins: list[str] | None = None,
        require_auth: bool = True,
        debug: bool = False
    ):
        self.host = host
        self.port = port
        self.config_path = config_path or os.getenv("CONFIG_PATH", "config.ini")
        self.cors_origins = cors_origins or ["*"]
        self.require_auth = require_auth
        self.debug = debug
        
        # Create OAuth token store
        self.token_store = OAuthTokenStore()
        
        # Create the MCP server
        self.mcp_server = FastMCPServer("SciKiq DB Utils", self.config_path)
        
        # Base URL for OAuth endpoints
        self.base_url = f"http://{host}:{port}" if host != "0.0.0.0" else f"http://localhost:{port}"
    
    def verify_pkce_challenge(self, code_verifier: str, code_challenge: str, method: str) -> bool:
        """Verify PKCE code challenge"""
        if method == "plain":
            return code_verifier == code_challenge
        elif method == "S256":
            # SHA256 hash and base64url encode
            digest = hashlib.sha256(code_verifier.encode()).digest()
            expected = base64.urlsafe_b64encode(digest).decode().rstrip("=")
            return expected == code_challenge
        return False
    
    async def create_starlette_app(self) -> Starlette:
        """Create the Starlette ASGI application with OAuth endpoints"""
        
        # OAuth 2.1 Authorization Server Metadata endpoint (RFC8414)
        async def oauth_metadata(request: Request):
            """OAuth 2.0 Authorization Server Metadata"""
            metadata = {
                "issuer": self.base_url,
                "authorization_endpoint": f"{self.base_url}/authorize",
                "token_endpoint": f"{self.base_url}/token",
                "registration_endpoint": f"{self.base_url}/register",
                "grant_types_supported": ["authorization_code", "refresh_token"],
                "response_types_supported": ["code"],
                "code_challenge_methods_supported": ["S256", "plain"],
                "token_endpoint_auth_methods_supported": ["none"],  # Public clients
                "scopes_supported": ["mcp"],
                "subject_types_supported": ["public"]
            }
            return JSONResponse(metadata)
        
        # Dynamic Client Registration endpoint (RFC7591)
        async def register_client(request: Request):
            """Dynamic Client Registration"""
            try:
                data = await request.json()
                client_name = data.get("client_name", "MCP Client")
                
                client_data = self.token_store.create_client(client_name)
                
                response = {
                    "client_id": client_data["client_id"],
                    "client_name": client_data["client_name"],
                    "grant_types": client_data["grant_types"],
                    "response_types": client_data["response_types"],
                    "token_endpoint_auth_method": client_data["token_endpoint_auth_method"]
                }
                
                return JSONResponse(response, status_code=201)
                
            except Exception as e:
                logger.error(f"Client registration error: {e}")
                return JSONResponse(
                    {"error": "invalid_request", "error_description": str(e)},
                    status_code=400
                )
        
        # Authorization endpoint
        async def authorize_endpoint(request: Request):
            """OAuth 2.1 Authorization endpoint"""
            try:
                # Get query parameters
                client_id = request.query_params.get("client_id")
                redirect_uri = request.query_params.get("redirect_uri")
                response_type = request.query_params.get("response_type")
                code_challenge = request.query_params.get("code_challenge")
                code_challenge_method = request.query_params.get("code_challenge_method", "S256")
                scope = request.query_params.get("scope", "mcp")
                state = request.query_params.get("state")
                
                # Validate parameters
                if not all([client_id, redirect_uri, response_type, code_challenge]):
                    return JSONResponse(
                        {"error": "invalid_request", "error_description": "Missing required parameters"},
                        status_code=400
                    )
                
                if response_type != "code":
                    return JSONResponse(
                        {"error": "unsupported_response_type"},
                        status_code=400
                    )
                
                # Validate client
                client = self.token_store.get_client(client_id)
                if not client:
                    return JSONResponse(
                        {"error": "invalid_client"},
                        status_code=400
                    )
                
                # For demo purposes, auto-approve (in production, show consent UI)
                auth_code = self.token_store.create_authorization_code(
                    client_id, redirect_uri, code_challenge, code_challenge_method, scope
                )
                
                # Redirect back to client with authorization code
                redirect_params = {"code": auth_code}
                if state:
                    redirect_params["state"] = state
                
                redirect_url = f"{redirect_uri}?{urlencode(redirect_params)}"
                return RedirectResponse(url=redirect_url)
                
            except Exception as e:
                logger.error(f"Authorization error: {e}")
                return JSONResponse(
                    {"error": "server_error", "error_description": str(e)},
                    status_code=500
                )
        
        # Token endpoint
        async def token_endpoint(request: Request):
            """OAuth 2.1 Token endpoint"""
            try:
                form_data = await request.form()
                grant_type = form_data.get("grant_type")
                
                if grant_type == "authorization_code":
                    # Authorization code grant
                    code = form_data.get("code")
                    redirect_uri = form_data.get("redirect_uri")
                    client_id = form_data.get("client_id")
                    code_verifier = form_data.get("code_verifier")
                    
                    if not all([code, redirect_uri, client_id, code_verifier]):
                        return JSONResponse(
                            {"error": "invalid_request", "error_description": "Missing parameters"},
                            status_code=400
                        )
                    
                    # Get and validate authorization code
                    code_data = self.token_store.get_authorization_code(code)
                    if not code_data:
                        return JSONResponse(
                            {"error": "invalid_grant", "error_description": "Invalid authorization code"},
                            status_code=400
                        )
                    
                    # Validate PKCE
                    if not self.verify_pkce_challenge(
                        code_verifier, 
                        code_data["code_challenge"], 
                        code_data["code_challenge_method"]
                    ):
                        return JSONResponse(
                            {"error": "invalid_grant", "error_description": "PKCE verification failed"},
                            status_code=400
                        )
                    
                    # Create access token
                    token_response = self.token_store.create_access_token(
                        client_id, code_data["scope"]
                    )
                    
                    return JSONResponse(token_response)
                
                elif grant_type == "refresh_token":
                    # Refresh token grant
                    refresh_token = form_data.get("refresh_token")
                    
                    if not refresh_token:
                        return JSONResponse(
                            {"error": "invalid_request", "error_description": "Missing refresh_token"},
                            status_code=400
                        )
                    
                    token_response = self.token_store.refresh_access_token(refresh_token)
                    if not token_response:
                        return JSONResponse(
                            {"error": "invalid_grant", "error_description": "Invalid refresh token"},
                            status_code=400
                        )
                    
                    return JSONResponse(token_response)
                
                else:
                    return JSONResponse(
                        {"error": "unsupported_grant_type"},
                        status_code=400
                    )
                
            except Exception as e:
                logger.error(f"Token error: {e}")
                return JSONResponse(
                    {"error": "server_error", "error_description": str(e)},
                    status_code=500
                )
        
        # Protected MCP endpoints
        async def list_tools_endpoint(request: Request):
            """List available tools endpoint (protected)"""
            try:
                tools = await self.mcp_server.list_tools()
                return JSONResponse(tools)
            except Exception as e:
                logger.error(f"Error in list_tools: {e}")
                return JSONResponse(
                    {"error": f"Failed to list tools: {str(e)}"},
                    status_code=500
                )
        
        async def call_tool_endpoint(request: Request):
            """Call tool endpoint (protected)"""
            try:
                data = await request.json()
                tool_name = data.get("name")
                arguments = data.get("arguments", {})
                
                if not tool_name:
                    return JSONResponse(
                        {"error": "Missing tool name"},
                        status_code=400
                    )
                
                result = await self.mcp_server.call_tool(tool_name, arguments)
                return JSONResponse(result)
                
            except Exception as e:
                logger.error(f"Error in call_tool: {e}")
                return JSONResponse(
                    {"error": f"Failed to call tool: {str(e)}"},
                    status_code=500
                )
        
        # Public endpoints
        async def health_check(request: Request):
            """Health check endpoint (public)"""
            try:
                # Test database connections
                connection_status = {}
                for conn_id in self.mcp_server.connection_manager.connections:
                    try:
                        conn_config = self.mcp_server.connection_manager.get_connection_config(conn_id)
                        connection_status[conn_id] = "available"
                    except Exception:
                        connection_status[conn_id] = "error"
                        
                return JSONResponse({
                    "status": "healthy",
                    "service": "SciKiq DB Utils MCP Server",
                    "version": "2.0.0",
                    "authentication": "OAuth 2.1" if self.require_auth else "Disabled",
                    "connections": connection_status,
                    "config_path": self.config_path
                })
            except Exception as e:
                return JSONResponse(
                    {
                        "status": "unhealthy", 
                        "error": str(e)
                    },
                    status_code=500
                )
        
        async def mcp_info(request: Request):
            """MCP server information (public)"""
            return JSONResponse({
                "name": "SciKiq DB Utils MCP Server",
                "version": "2.0.0",
                "description": "Database connectivity and analysis for Claude with OAuth 2.1",
                "capabilities": {
                    "tools": True,
                    "resources": False,
                    "prompts": False,
                    "authentication": "OAuth 2.1" if self.require_auth else "None"
                },
                "endpoints": {
                    "tools": "/mcp/tools",
                    "call": "/mcp/call",
                    "health": "/health",
                    "authorize": "/authorize",
                    "token": "/token",
                    "register": "/register",
                    "metadata": "/.well-known/oauth-authorization-server"
                }
            })
        
        # Create routes
        routes = [
            # Public endpoints
            Route("/health", endpoint=health_check, methods=["GET"]),
            Route("/mcp/info", endpoint=mcp_info, methods=["GET"]),
            Route("/.well-known/oauth-authorization-server", endpoint=oauth_metadata, methods=["GET"]),
            
            # OAuth endpoints
            Route("/register", endpoint=register_client, methods=["POST"]),
            Route("/authorize", endpoint=authorize_endpoint, methods=["GET", "POST"]),
            Route("/token", endpoint=token_endpoint, methods=["POST"]),
            
            # Protected MCP endpoints
            Route("/mcp/tools", endpoint=list_tools_endpoint, methods=["GET"]),
            Route("/mcp/call", endpoint=call_tool_endpoint, methods=["POST"]),
        ]
        
        # Create Starlette app
        app = Starlette(
            debug=self.debug,
            routes=routes,
        )
        
        # Add authentication middleware
        if self.require_auth:
            app.add_middleware(AuthenticationMiddleware, token_store=self.token_store, require_auth=True)
        
        # Add CORS middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=self.cors_origins,
            allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
            allow_headers=["*"],
            expose_headers=["Content-Type"],
            allow_credentials=True,
        )
        
        return app
    
    async def run(self):
        """Run the remote MCP server"""
        app = await self.create_starlette_app()
        
        auth_status = "🔒 OAuth 2.1 Enabled" if self.require_auth else "🔓 No Authentication"
        
        logger.info(f"🚀 SciKiq MCP Server starting on http://{self.host}:{self.port}")
        logger.info(f"🔧 Config: {self.config_path}")
        logger.info(f"🛡️ Auth: {auth_status}")
        logger.info(f"📡 Endpoints: /health, /mcp/info, /mcp/tools, /mcp/call")
        
        if self.require_auth:
            logger.info(f"🔑 OAuth Endpoints: /register, /authorize, /token")
            logger.info(f"📋 Metadata: /.well-known/oauth-authorization-server")
        
        # Configure uvicorn
        config = uvicorn.Config(
            app=app,
            host=self.host,
            port=self.port,
            log_level="info" if not self.debug else "debug",
            access_log=self.debug,
        )
        
        server = uvicorn.Server(config)
        await server.serve()


@click.command()
@click.option(
    "--host",
    default="0.0.0.0",
    help="Host to bind to (default: 0.0.0.0 for remote access)"
)
@click.option(
    "--port",
    default=3000,
    help="Port to listen on (default: 3000)"
)
@click.option(
    "--config-path",
    help="Path to configuration file (default: config.ini or CONFIG_PATH env var)"
)
@click.option(
    "--cors-origins",
    multiple=True,
    help="Allowed CORS origins (can be specified multiple times, default: all origins)"
)
@click.option(
    "--no-auth",
    is_flag=True,
    help="Disable OAuth authentication (NOT RECOMMENDED for production)"
)
@click.option(
    "--debug",
    is_flag=True,
    help="Enable debug mode with verbose logging"
)
def main(
    host: str,
    port: int,
    config_path: str | None,
    cors_origins: tuple[str, ...],
    no_auth: bool,
    debug: bool,
) -> int:
    """
    SciKiq DB Utils - Remote MCP Server with OAuth 2.1 Authentication
    
    This server provides database connectivity for Claude Desktop via HTTP transport
    with OAuth 2.1 authentication as required by the MCP specification.
    
    Examples:
    
        # Start server with OAuth 2.1 authentication
        python remote_mcp_server_auth.py --debug
        
        # Start server without authentication (development only)
        python remote_mcp_server_auth.py --no-auth --debug
        
        # Start server for production deployment  
        python remote_mcp_server_auth.py --host 0.0.0.0 --port 8080
        
        # Configure CORS for specific origins
        python remote_mcp_server_auth.py --cors-origins https://claude.ai
    """
    
    # Configure logging
    log_level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Convert CORS origins tuple to list
    cors_origins_list = list(cors_origins) if cors_origins else ["*"]
    
    # Create and run server
    server = RemoteMCPServer(
        host=host,
        port=port,
        config_path=config_path,
        cors_origins=cors_origins_list,
        require_auth=not no_auth,
        debug=debug
    )
    
    if no_auth:
        logger.warning("⚠️ Authentication is DISABLED. This is NOT secure for production!")
    else:
        logger.info("🔒 OAuth 2.1 authentication enabled (MCP specification compliant)")
    
    try:
        asyncio.run(server.run())
        return 0
    except KeyboardInterrupt:
        logger.info("🛑 Server stopped by user")
        return 0
    except Exception as e:
        logger.error(f"❌ Server error: {e}")
        if debug:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())