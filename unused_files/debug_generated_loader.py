#!/usr/bin/env python3
"""
SciKiq DB Utils - Remote MCP Server with Admin User Management

This module creates a remote MCP server with comprehensive user and client management.
Features admin users who can create and manage OAuth clients.

Features:
- Admin user authentication with password hashing
- Client management (create, update, delete clients)
- User roles and permissions
- OAuth 2.1 with PKCE support for clients
- Admin dashboard for user/client management
- Persistent user and client storage
"""

import asyncio
import base64
import contextlib
import hashlib
import json
import logging
import os
import secrets
import sqlite3
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
import yaml
import httpx
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


class DatabaseManager:
    """SQLite database manager for users, clients, and tokens"""
    
    def __init__(self, db_path: str = "mcp_auth.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                email TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        """)
        
        # OAuth clients table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS oauth_clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id TEXT UNIQUE NOT NULL,
                client_name TEXT NOT NULL,
                client_secret TEXT,
                redirect_uris TEXT,
                grant_types TEXT,
                response_types TEXT,
                scope TEXT DEFAULT 'mcp',
                created_by_user_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (created_by_user_id) REFERENCES users (id)
            )
        """)
        
        # Access tokens table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS access_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token TEXT UNIQUE NOT NULL,
                client_id TEXT NOT NULL,
                user_id INTEGER,
                scope TEXT,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (client_id) REFERENCES oauth_clients (client_id),
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        
        # Refresh tokens table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS refresh_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token TEXT UNIQUE NOT NULL,
                access_token_id INTEGER NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (access_token_id) REFERENCES access_tokens (id)
            )
        """)
        
        # Authorization codes table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS authorization_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                client_id TEXT NOT NULL,
                user_id INTEGER,
                redirect_uri TEXT NOT NULL,
                code_challenge TEXT NOT NULL,
                code_challenge_method TEXT NOT NULL,
                scope TEXT,
                state TEXT,
                is_used BOOLEAN DEFAULT FALSE,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (client_id) REFERENCES oauth_clients (client_id),
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        
        # Admin sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admin_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT UNIQUE NOT NULL,
                user_id INTEGER NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        
        conn.commit()
        conn.close()
        
        # Run database migrations
        self.migrate_database()
    
    def migrate_database(self):
        """Handle database migrations for existing databases"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Check if state column exists in authorization_codes table
            cursor.execute("PRAGMA table_info(authorization_codes)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'state' not in columns:
                cursor.execute("ALTER TABLE authorization_codes ADD COLUMN state TEXT")
                print("✅ Added 'state' column to authorization_codes table")
            
            if 'is_used' not in columns:
                cursor.execute("ALTER TABLE authorization_codes ADD COLUMN is_used BOOLEAN DEFAULT FALSE")
                print("✅ Added 'is_used' column to authorization_codes table")
            
            conn.commit()
        except Exception as e:
            print(f"❌ Migration error: {e}")
        finally:
            conn.close()
    
    def hash_password(self, password: str) -> str:
        """Hash password with salt"""
        salt = secrets.token_hex(32)
        password_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return f"{salt}:{password_hash.hex()}"
    
    def verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password against hash"""
        try:
            salt, hash_hex = password_hash.split(':')
            password_hash_check = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
            return password_hash_check.hex() == hash_hex
        except:
            return False
    
    def create_admin_user(self, username: str, password: str, email: str = None) -> Dict[str, Any]:
        """Create an admin user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            password_hash = self.hash_password(password)
            cursor.execute("""
                INSERT INTO users (username, password_hash, role, email)
                VALUES (?, ?, 'admin', ?)
            """, (username, password_hash, email))
            
            user_id = cursor.lastrowid
            conn.commit()
            
            return {
                "id": user_id,
                "username": username,
                "role": "admin",
                "email": email,
                "created_at": datetime.utcnow().isoformat()
            }
        except sqlite3.IntegrityError:
            raise ValueError(f"Username '{username}' already exists")
        finally:
            conn.close()
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user credentials"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, username, password_hash, role, email, is_active
            FROM users WHERE username = ? AND is_active = 1
        """, (username,))
        
        user = cursor.fetchone()
        conn.close()
        
        if user and self.verify_password(password, user[2]):
            return {
                "id": user[0],
                "username": user[1],
                "role": user[3],
                "email": user[4]
            }
        return None
    
    def create_admin_session(self, user_id: int) -> str:
        """Create admin session"""
        session_id = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=8)  # 8 hour sessions
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO admin_sessions (session_id, user_id, expires_at)
            VALUES (?, ?, ?)
        """, (session_id, user_id, expires_at))
        
        conn.commit()
        conn.close()
        
        return session_id
    
    def validate_admin_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Validate admin session"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT s.user_id, u.username, u.role, u.email
            FROM admin_sessions s
            JOIN users u ON s.user_id = u.id
            WHERE s.session_id = ? AND s.expires_at > ? AND u.is_active = 1
        """, (session_id, datetime.utcnow()))
        
        session = cursor.fetchone()
        conn.close()
        
        if session:
            return {
                "id": session[0],
                "username": session[1],
                "role": session[2],
                "email": session[3]
            }
        return None
    
    def create_oauth_client(self, client_name: str, created_by_user_id: int, 
                          redirect_uris: List[str] = None) -> Dict[str, Any]:
        """Create OAuth client"""
        client_id = f"mcp_client_{secrets.token_urlsafe(16)}"
        client_secret = f"mcp_secret_{secrets.token_urlsafe(32)}"
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        redirect_uris_json = json.dumps(redirect_uris or ["http://localhost:*"])
        grant_types_json = json.dumps(["authorization_code", "refresh_token"])
        response_types_json = json.dumps(["code"])
        
        cursor.execute("""
            INSERT INTO oauth_clients 
            (client_id, client_name, client_secret, redirect_uris, grant_types, response_types, created_by_user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (client_id, client_name, client_secret, redirect_uris_json, grant_types_json, 
              response_types_json, created_by_user_id))
        
        conn.commit()
        conn.close()
        
        return {
            "client_id": client_id,
            "client_secret": client_secret,
            "client_name": client_name,
            "redirect_uris": redirect_uris or ["http://localhost:*"],
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "token_endpoint_auth_method": "client_secret_basic"
        }
    
    def get_oauth_client(self, client_id: str) -> Optional[Dict[str, Any]]:
        """Get OAuth client by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT client_id, client_name, redirect_uris, grant_types, response_types, scope, is_active
            FROM oauth_clients WHERE client_id = ? AND is_active = 1
        """, (client_id,))
        
        client = cursor.fetchone()
        conn.close()
        
        if client:
            return {
                "client_id": client[0],
                "client_name": client[1],
                "redirect_uris": json.loads(client[2]),
                "grant_types": json.loads(client[3]),
                "response_types": json.loads(client[4]),
                "scope": client[5],
                "token_endpoint_auth_method": "none"
            }
        return None
    
    def update_oauth_client(self, client_id: str, client_name: str = None, 
                          redirect_uris: List[str] = None) -> bool:
        """Update OAuth client"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Build update query dynamically based on provided parameters
        update_fields = []
        params = []
        
        if client_name is not None:
            update_fields.append("client_name = ?")
            params.append(client_name)
            
        if redirect_uris is not None:
            update_fields.append("redirect_uris = ?")
            params.append(json.dumps(redirect_uris))
        
        if not update_fields:
            conn.close()
            return False
        
        params.append(client_id)  # for WHERE clause
        
        cursor.execute(f"""
            UPDATE oauth_clients 
            SET {', '.join(update_fields)}
            WHERE client_id = ? AND is_active = 1
        """, params)
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        return success
    
    def get_oauth_client_for_edit(self, client_id: str) -> Optional[Dict[str, Any]]:
        """Get OAuth client details for editing (includes all fields)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT client_id, client_name, redirect_uris, grant_types, response_types, scope, is_active, created_at
            FROM oauth_clients WHERE client_id = ?
        """, (client_id,))
        
        client = cursor.fetchone()
        conn.close()
        
        if client:
            return {
                "client_id": client[0],
                "client_name": client[1],
                "redirect_uris": json.loads(client[2]),
                "grant_types": json.loads(client[3]),
                "response_types": json.loads(client[4]),
                "scope": client[5],
                "is_active": bool(client[6]),
                "created_at": client[7]
            }
        return None
    
    def list_oauth_clients(self, created_by_user_id: int = None) -> List[Dict[str, Any]]:
        """List OAuth clients"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if created_by_user_id:
            cursor.execute("""
                SELECT client_id, client_name, redirect_uris, created_at, is_active
                FROM oauth_clients WHERE created_by_user_id = ? ORDER BY created_at DESC
            """, (created_by_user_id,))
        else:
            cursor.execute("""
                SELECT client_id, client_name, redirect_uris, created_at, is_active
                FROM oauth_clients ORDER BY created_at DESC
            """)
        
        clients = cursor.fetchall()
        conn.close()
        
        return [
            {
                "client_id": client[0],
                "client_name": client[1],
                "redirect_uris": json.loads(client[2]),
                "created_at": client[3],
                "is_active": bool(client[4])
            }
            for client in clients
        ]
    
    def create_access_token(self, client_id: str, user_id: int = None, scope: str = "mcp") -> Dict[str, str]:
        """Create access and refresh tokens"""
        access_token = f"mcp_access_{secrets.token_urlsafe(32)}"
        refresh_token = f"mcp_refresh_{secrets.token_urlsafe(32)}"
        expires_at = datetime.utcnow() + timedelta(hours=1)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create access token
        cursor.execute("""
            INSERT INTO access_tokens (token, client_id, user_id, scope, expires_at)
            VALUES (?, ?, ?, ?, ?)
        """, (access_token, client_id, user_id, scope, expires_at))
        
        access_token_id = cursor.lastrowid
        
        # Create refresh token
        refresh_expires_at = datetime.utcnow() + timedelta(days=30)
        cursor.execute("""
            INSERT INTO refresh_tokens (token, access_token_id, expires_at)
            VALUES (?, ?, ?)
        """, (refresh_token, access_token_id, refresh_expires_at))
        
        conn.commit()
        conn.close()
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": 3600,
            "scope": scope
        }
    
    def validate_access_token(self, access_token: str) -> Optional[Dict[str, Any]]:
        """Validate access token"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT t.client_id, t.user_id, t.scope, c.client_name
            FROM access_tokens t
            JOIN oauth_clients c ON t.client_id = c.client_id
            WHERE t.token = ? AND t.expires_at > ? AND c.is_active = 1
        """, (access_token, datetime.utcnow()))
        
        token_data = cursor.fetchone()
        conn.close()
        
        if token_data:
            return {
                "client_id": token_data[0],
                "user_id": token_data[1],
                "scope": token_data[2],
                "client_name": token_data[3]
            }
        return None

    def create_authorization_code(self, client_id: str, redirect_uri: str, scope: str = "mcp",
                                code_challenge: str = None, code_challenge_method: str = None,
                                state: str = None) -> str:
        """Create authorization code for OAuth flow"""
        code = f"mcp_code_{secrets.token_urlsafe(32)}"
        expires_at = datetime.utcnow() + timedelta(minutes=10)  # Authorization codes expire quickly
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO authorization_codes (code, client_id, redirect_uri, scope, 
                                           code_challenge, code_challenge_method, state, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (code, client_id, redirect_uri, scope, code_challenge, code_challenge_method, state, expires_at))
        
        conn.commit()
        conn.close()
        
        return code
    
    def validate_authorization_code(self, code: str, client_id: str, redirect_uri: str,
                                  code_verifier: str = None) -> Optional[Dict[str, Any]]:
        """Validate and consume authorization code"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        logger.info(f"Validating auth code: code={code[:20]}..., client_id={client_id}, redirect_uri={redirect_uri}")
        logger.info(f"Code verifier present: {bool(code_verifier)}")
        
        cursor.execute("""
            SELECT client_id, redirect_uri, scope, code_challenge, code_challenge_method, state, is_used
            FROM authorization_codes 
            WHERE code = ? AND expires_at > ? AND client_id = ? AND redirect_uri = ?
        """, (code, datetime.utcnow(), client_id, redirect_uri))
        
        code_data = cursor.fetchone()
        
        if not code_data:
            logger.error(f"No authorization code found for: {code[:20]}...")
            conn.close()
            return None
            
        if code_data[6]:  # code_data[6] is is_used
            logger.error(f"Authorization code already used: {code[:20]}...")
            conn.close()
            return None
        
        logger.info(f"Authorization code found: scope={code_data[2]}, challenge_method={code_data[4]}")
        
        # Validate PKCE if present
        if code_data[3]:  # code_challenge exists
            logger.info(f"Validating PKCE challenge...")
            if not code_verifier:
                logger.error("PKCE challenge required but code_verifier missing")
                conn.close()
                return None
            
            # Verify code challenge
            if code_data[4] == "S256":
                import hashlib
                import base64
                challenge = base64.urlsafe_b64encode(
                    hashlib.sha256(code_verifier.encode()).digest()
                ).decode().rstrip('=')
                if challenge != code_data[3]:
                    logger.error(f"PKCE S256 validation failed: expected={code_data[3]}, got={challenge}")
                    conn.close()
                    return None
                logger.info("PKCE S256 validation successful")
            elif code_data[4] == "plain":
                if code_verifier != code_data[3]:
                    logger.error(f"PKCE plain validation failed")
                    conn.close()
                    return None
                logger.info("PKCE plain validation successful")
        else:
            logger.info("No PKCE challenge to validate")
        
        # Mark code as used
        cursor.execute("""
            UPDATE authorization_codes SET is_used = 1 WHERE code = ?
        """, (code,))
        
        conn.commit()
        conn.close()
        
        logger.info("Authorization code validation completed successfully")
        
        return {
            "client_id": code_data[0],
            "redirect_uri": code_data[1],
            "scope": code_data[2],
            "state": code_data[5]
        }


class AdminAuthMiddleware(BaseHTTPMiddleware):
    """Middleware for admin authentication"""
    
    def __init__(self, app, db_manager: DatabaseManager):
        super().__init__(app)
        self.db_manager = db_manager
        
        # Admin endpoints that require authentication
        self.admin_endpoints = {
            "/admin/dashboard",
            "/admin/clients",
            "/admin/clients/new",
            "/admin/users",
            "/admin/logout"
        }
        
        # Admin endpoint patterns that require authentication (for dynamic routes)
        self.admin_endpoint_patterns = [
            "/admin/clients/",  # Matches /admin/clients/{client_id}/edit
        ]
    
    async def dispatch(self, request: Request, call_next):
        # Check if this is an admin endpoint (exact match or pattern match)
        is_admin_endpoint = (
            request.url.path in self.admin_endpoints or
            any(request.url.path.startswith(pattern) for pattern in self.admin_endpoint_patterns)
        )
        
        if not is_admin_endpoint:
            return await call_next(request)
        
        # Check for admin session cookie
        session_id = request.cookies.get("admin_session")
        if not session_id:
            return RedirectResponse(url="/admin/login", status_code=302)
        
        # Validate session
        user_data = self.db_manager.validate_admin_session(session_id)
        if not user_data or user_data["role"] != "admin":
            return RedirectResponse(url="/admin/login", status_code=302)
        
        # Add user data to request state
        request.state.admin_user = user_data
        
        return await call_next(request)


class OAuthAuthMiddleware(BaseHTTPMiddleware):
    """Middleware for OAuth token authentication"""
    
    def __init__(self, app, db_manager: DatabaseManager):
        super().__init__(app)
        self.db_manager = db_manager
        
        # Public endpoints that don't require authentication
        self.public_endpoints = {
            "/health",
            "/mcp/info",
            "/.well-known/oauth-authorization-server",
            "/authorize",
            "/token",
            "/register"
        }
        
        # Admin endpoints (handled by AdminAuthMiddleware)
        self.admin_endpoints = {
            "/admin/login",
            "/admin/dashboard", 
            "/admin/clients",
            "/admin/clients/new",
            "/admin/users",
            "/admin/logout"
        }
        
        # Admin endpoint patterns (for dynamic routes)
        self.admin_endpoint_patterns = [
            "/admin/clients/",  # Matches /admin/clients/{client_id}/edit
        ]
    
    async def dispatch(self, request: Request, call_next):
        # Skip authentication for public and admin endpoints
        if (request.url.path in self.public_endpoints or 
            request.url.path in self.admin_endpoints or
            request.url.path.startswith("/admin/")):
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
        token_data = self.db_manager.validate_access_token(token)
        if not token_data:
            return JSONResponse(
                {"error": "invalid_token", "message": "Invalid or expired access token"}, 
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Add token data to request state
        request.state.token_data = token_data
        
        return await call_next(request)




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


class FastMCPServer_OLD:
    """FastMCP-style server using our existing tools"""
    
    def __init__(self, name: str, config_path: str):
        self.name = name
        self.config_path = config_path
        
        # Initialize our existing components
        try:
            if os.path.exists(config_path):
                parser = IniConfigParser(config_path)
                connection_configs = parser.parse_all_connections()
            else:
                logger.warning(f"Config file {config_path} not found, using empty configuration")
                connection_configs = {}
                
            self.connection_manager = ConnectionManager(connection_configs)
            self.db_wrapper = DatabaseWrapper(self.connection_manager)
            self.tool_registry = ToolRegistry(self.db_wrapper)
            
        except Exception as e:
            logger.error(f"Failed to initialize MCP server: {e}")
            raise
    
    async def list_tools(self):
        """List available tools"""
        try:
            tools_data = self.tool_registry.list_tools()
            return {"tools": tools_data}
        except Exception as e:
            logger.error(f"Error listing tools: {e}")
            return {"tools": []}
    
    async def call_tool(self, name: str, arguments: dict):
        """Call a tool with arguments"""
        try:
            from scikiq_dbutils.mcp_server.protocol.messages import MCPToolCall
            
            tool_call = MCPToolCall(name=name, arguments=arguments)
            result = self.tool_registry.execute_tool(tool_call)
            
            if hasattr(result, 'is_error') and result.is_error:
                return {
                    "content": [{"type": "text", "text": result.content.get("message", "Tool execution failed")}],
                    "isError": True
                }
            else:
                if hasattr(result, 'content'):
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


class RemoteMCPServerWithAdmin:
    """Remote MCP Server with Admin User Management"""
    
    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 3000,
        yaml_paths: list[str] | None = None,
        cors_origins: list[str] | None = None,
        db_path: str = "mcp_auth.db",
        debug: bool = False
    ):
        self.host = host
        self.port = port
        self.yaml_paths = yaml_paths or []
        self.cors_origins = cors_origins or ["*"]
        self.debug = debug
        
        # Create database manager
        self.db_manager = DatabaseManager(db_path)
        
        # Create the MCP server
        self.mcp_server = FastMCPServer("MCP API Server", self.yaml_paths)
        
        # Base URL for OAuth endpoints - configurable via environment variable
        # For production, set SERVER_BASE_URL=https://mcp.scikiq.com
        server_base_url = os.getenv("SERVER_BASE_URL")
        if server_base_url:
            self.base_url = server_base_url
        else:
            # Default to localhost for development
            self.base_url = f"http://{host}:{port}" if host != "0.0.0.0" else f"http://localhost:{port}"
    
    def verify_pkce_challenge(self, code_verifier: str, code_challenge: str, method: str) -> bool:
        """Verify PKCE code challenge"""
        if method == "plain":
            return code_verifier == code_challenge
        elif method == "S256":
            digest = hashlib.sha256(code_verifier.encode()).digest()
            expected = base64.urlsafe_b64encode(digest).decode().rstrip("=")
            return expected == code_challenge
        return False
    
    async def create_starlette_app(self) -> Starlette:
        """Create the Starlette ASGI application"""
        
        # Admin login page
        async def admin_login_page(request: Request):
            """Admin login page"""
            if request.method == "GET":
                html = """
<!DOCTYPE html>
<html>
<head>
    <title>SciKiq MCP Server - Admin Login</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 400px; margin: 100px auto; padding: 20px; }
        .form-group { margin-bottom: 15px; }
        label { display: block; margin-bottom: 5px; }
        input[type="text"], input[type="password"] { width: 100%; padding: 8px; box-sizing: border-box; }
        button { background: #007cba; color: white; padding: 10px 20px; border: none; cursor: pointer; }
        .error { color: red; margin-top: 10px; }
        .success { color: green; margin-top: 10px; }
    </style>
</head>
<body>
    <h2>SciKiq MCP Server</h2>
    <h3>Admin Login</h3>
    <form method="post">
        <div class="form-group">
            <label>Username:</label>
            <input type="text" name="username" required>
        </div>
        <div class="form-group">
            <label>Password:</label>
            <input type="password" name="password" required>
        </div>
        <button type="submit">Login</button>
    </form>
</body>
</html>"""
                return HTMLResponse(html)
            
            elif request.method == "POST":
                form_data = await request.form()
                username = form_data.get("username")
                password = form_data.get("password")
                
                user = self.db_manager.authenticate_user(username, password)
                if user and user["role"] == "admin":
                    session_id = self.db_manager.create_admin_session(user["id"])
                    response = RedirectResponse(url="/admin/dashboard", status_code=302)
                    response.set_cookie("admin_session", session_id, httponly=True, max_age=8*3600)
                    return response
                else:
                    html = """
<!DOCTYPE html>
<html>
<head><title>Login Failed</title></head>
<body>
    <h2>Login Failed</h2>
    <p>Invalid username or password.</p>
    <a href="/admin/login">Try Again</a>
</body>
</html>"""
                    return HTMLResponse(html, status_code=401)
        
        # Admin dashboard
        async def admin_dashboard(request: Request):
            """Admin dashboard"""
            user = request.state.admin_user
            clients = self.db_manager.list_oauth_clients()
            
            clients_html = ""
            for client in clients:
                status = "Active" if client["is_active"] else "Inactive"
                clients_html += f"""
                <tr>
                    <td>{client['client_name']}</td>
                    <td>{client['client_id']}</td>
                    <td>{client['created_at']}</td>
                    <td>{status}</td>
                    <td>
                        <a href="/admin/clients/{client['client_id']}/edit" class="btn btn-sm">Edit</a>
                    </td>
                </tr>
                """
            
            html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>SciKiq MCP Server - Admin Dashboard</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th, td {{ padding: 10px; border: 1px solid #ddd; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .header {{ display: flex; justify-content: space-between; align-items: center; }}
        .btn {{ background: #007cba; color: white; padding: 8px 16px; text-decoration: none; border-radius: 4px; }}
        .btn-sm {{ padding: 4px 8px; font-size: 12px; }}
        .btn-danger {{ background: #dc3545; }}
    </style>
</head>
<body>
    <div class="header">
        <h2>Admin Dashboard</h2>
        <div>
            Welcome, {user['username']} | <a href="/admin/logout">Logout</a>
        </div>
    </div>
    
    <h3>OAuth Clients</h3>
    <a href="/admin/clients/new" class="btn">Create New Client</a>
    
    <table>
        <thead>
            <tr>
                <th>Client Name</th>
                <th>Client ID</th>
                <th>Created At</th>
                <th>Status</th>
                <th>Actions</th>
            </tr>
        </thead>
        <tbody>
            {clients_html}
        </tbody>
    </table>
    
    <h3>Server Info</h3>
    <p><strong>Version:</strong> 2.0.0</p>
    <p><strong>MCP Tools:</strong> {len(self.mcp_server._tools)} available</p>
    <p><strong>OAuth Endpoint:</strong> {self.base_url}/.well-known/oauth-authorization-server</p>
</body>
</html>"""
            
            return HTMLResponse(html)
        
        # Create new client page
        async def create_client_page(request: Request):
            """Create new OAuth client"""
            if request.method == "GET":
                html = """
<!DOCTYPE html>
<html>
<head>
    <title>Create OAuth Client</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; }
        .form-group { margin-bottom: 15px; }
        label { display: block; margin-bottom: 5px; }
        input, textarea { width: 100%; padding: 8px; box-sizing: border-box; }
        button { background: #007cba; color: white; padding: 10px 20px; border: none; cursor: pointer; }
    </style>
</head>
<body>
    <h2>Create New OAuth Client</h2>
    <form method="post">
        <div class="form-group">
            <label>Client Name:</label>
            <input type="text" name="client_name" required placeholder="e.g., Claude Desktop">
        </div>
        <div class="form-group">
            <label>Redirect URIs (one per line):</label>
            <textarea name="redirect_uris" rows="4" placeholder="http://localhost:8080/callback&#10;https://myapp.com/callback">http://localhost:*</textarea>
        </div>
        <button type="submit">Create Client</button>
        <a href="/admin/dashboard" style="margin-left: 10px;">Cancel</a>
    </form>
</body>
</html>"""
                return HTMLResponse(html)
            
            elif request.method == "POST":
                form_data = await request.form()
                client_name = form_data.get("client_name")
                redirect_uris_text = form_data.get("redirect_uris", "http://localhost:*")
                
                redirect_uris = [uri.strip() for uri in redirect_uris_text.split('\n') if uri.strip()]
                
                user = request.state.admin_user
                client_data = self.db_manager.create_oauth_client(client_name, user["id"], redirect_uris)
                
                html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Client Created</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; }}
        .success {{ background: #d4edda; border: 1px solid #c3e6cb; color: #155724; padding: 15px; border-radius: 4px; }}
        .warning {{ background: #fff3cd; border: 1px solid #ffecb5; color: #856404; padding: 15px; border-radius: 4px; margin: 15px 0; }}
        code {{ background: #f8f9fa; padding: 2px 4px; border-radius: 3px; font-family: monospace; }}
        .copy-btn {{ background: #007cba; color: white; border: none; padding: 5px 10px; margin-left: 10px; cursor: pointer; border-radius: 3px; }}
    </style>
    <script>
        function copyToClipboard(text) {{
            navigator.clipboard.writeText(text).then(function() {{
                alert('Copied to clipboard!');
            }});
        }}
    </script>
</head>
<body>
    <div class="success">
        <h3>✅ OAuth Client Created Successfully!</h3>
        <p><strong>Client Name:</strong> {client_data['client_name']}</p>
        <p><strong>Client ID:</strong> 
            <code id="client-id">{client_data['client_id']}</code>
            <button class="copy-btn" onclick="copyToClipboard('{client_data['client_id']}')">Copy</button>
        </p>
        <p><strong>Client Secret:</strong> 
            <code id="client-secret">{client_data['client_secret']}</code>
            <button class="copy-btn" onclick="copyToClipboard('{client_data['client_secret']}')">Copy</button>
        </p>
        <p><strong>Redirect URIs:</strong></p>
        <ul>
            {''.join(f'<li><code>{uri}</code></li>' for uri in client_data['redirect_uris'])}
        </ul>
    </div>
    <div class="warning">
        <strong>⚠️ Important Security Notice:</strong><br>
        • Save both the Client ID and Client Secret securely<br>
        • The Client Secret will not be displayed again for security reasons<br>
        • Use these credentials to configure your OAuth application<br>
        • Keep the Client Secret confidential and never expose it in client-side code
    </div>
    <a href="/admin/dashboard">Back to Dashboard</a>
</body>
</html>"""
                return HTMLResponse(html)
        
        # Edit client page
        async def edit_client_page(request: Request):
            """Edit OAuth client"""
            # Extract client_id from path parameters
            client_id = request.path_params.get("client_id")
            if not client_id:
                return RedirectResponse(url="/admin/dashboard", status_code=302)
            
            if request.method == "GET":
                # Get client details for editing
                client = self.db_manager.get_oauth_client_for_edit(client_id)
                if not client:
                    return RedirectResponse(url="/admin/dashboard", status_code=302)
                
                redirect_uris_text = '\n'.join(client['redirect_uris'])
                
                html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Edit OAuth Client</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; }}
        .form-group {{ margin-bottom: 15px; }}
        label {{ display: block; margin-bottom: 5px; }}
        input, textarea {{ width: 100%; padding: 8px; box-sizing: border-box; }}
        button {{ background: #007cba; color: white; padding: 10px 20px; border: none; cursor: pointer; }}
        .readonly {{ background-color: #f8f9fa; }}
    </style>
</head>
<body>
    <h2>Edit OAuth Client</h2>
    <form method="post">
        <div class="form-group">
            <label>Client ID:</label>
            <input type="text" value="{client['client_id']}" readonly class="readonly">
        </div>
        <div class="form-group">
            <label>Client Name:</label>
            <input type="text" name="client_name" value="{client['client_name']}" required>
        </div>
        <div class="form-group">
            <label>Redirect URIs (one per line):</label>
            <textarea name="redirect_uris" rows="4" required>{redirect_uris_text}</textarea>
        </div>
        <div class="form-group">
            <label>Status:</label>
            <input type="text" value="{'Active' if client['is_active'] else 'Inactive'}" readonly class="readonly">
        </div>
        <div class="form-group">
            <label>Created At:</label>
            <input type="text" value="{client['created_at']}" readonly class="readonly">
        </div>
        <button type="submit">Update Client</button>
        <a href="/admin/dashboard" style="margin-left: 10px;">Cancel</a>
    </form>
</body>
</html>"""
                return HTMLResponse(html)
            
            elif request.method == "POST":
                form_data = await request.form()
                client_name = form_data.get("client_name")
                redirect_uris_text = form_data.get("redirect_uris", "")
                
                redirect_uris = [uri.strip() for uri in redirect_uris_text.split('\n') if uri.strip()]
                
                # Update the client
                success = self.db_manager.update_oauth_client(
                    client_id=client_id,
                    client_name=client_name,
                    redirect_uris=redirect_uris
                )
                
                if success:
                    html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Client Updated</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; }}
        .success {{ background: #d4edda; border: 1px solid #c3e6cb; color: #155724; padding: 15px; border-radius: 4px; }}
    </style>
</head>
<body>
    <div class="success">
        <h3>✅ OAuth Client Updated Successfully!</h3>
        <p><strong>Client ID:</strong> {client_id}</p>
        <p><strong>Client Name:</strong> {client_name}</p>
        <p><strong>Redirect URIs:</strong></p>
        <ul>
            {''.join(f'<li>{uri}</li>' for uri in redirect_uris)}
        </ul>
    </div>
    <a href="/admin/dashboard">Back to Dashboard</a>
</body>
</html>"""
                else:
                    html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Update Failed</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; }}
        .error {{ background: #f8d7da; border: 1px solid #f5c6cb; color: #721c24; padding: 15px; border-radius: 4px; }}
    </style>
</head>
<body>
    <div class="error">
        <h3>❌ Failed to Update Client</h3>
        <p>There was an error updating the OAuth client. Please try again.</p>
    </div>
    <a href="/admin/dashboard">Back to Dashboard</a>
</body>
</html>"""
                
                return HTMLResponse(html)
        
        # OAuth endpoints
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
                "token_endpoint_auth_methods_supported": ["none"],
                "scopes_supported": ["mcp"],
                "subject_types_supported": ["public"]
            }
            return JSONResponse(metadata)
        
        # OAuth protected resource metadata
        async def oauth_protected_resource_metadata(request: Request):
            """OAuth 2.1 Protected Resource Metadata"""
            return JSONResponse({
                "resource": self.base_url,
                "authorization_servers": [self.base_url],
                "scopes_supported": ["mcp"],
                "bearer_methods_supported": ["header"],
                "resource_documentation": f"{self.base_url}/mcp/info"
            })
        
        # Root MCP endpoint - main protocol endpoint
        async def mcp_root_endpoint(request: Request):
            """Main MCP protocol endpoint"""
            # Check OAuth authentication
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return JSONResponse(
                    {"error": "unauthorized", "error_description": "Bearer token required"},
                    status_code=401,
                    headers={"WWW-Authenticate": "Bearer"}
                )
            
            token = auth_header[7:]  # Remove "Bearer " prefix
            token_data = self.db_manager.validate_access_token(token)
            if not token_data:
                return JSONResponse(
                    {"error": "invalid_token", "error_description": "Invalid or expired access token"},
                    status_code=401,
                    headers={"WWW-Authenticate": "Bearer"}
                )
            
            # Handle MCP protocol requests
            if request.method == "POST":
                # Handle MCP RPC calls - JSON-RPC 2.0 protocol
                try:
                    body = await request.json()
                    method = body.get("method")
                    request_id = body.get("id")
                    
                    logger.info(f"MCP JSON-RPC request: method={method}, id={request_id}")
                    
                    if method == "initialize":
                        # MCP protocol initialization
                        params = body.get("params", {})
                        logger.info(f"Initialize request params: {params}")
                        
                        response = {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "result": {
                                "protocolVersion": "2024-11-05",
                                "capabilities": {
                                    "tools": {},
                                    "resources": {},
                                    "prompts": {}
                                },
                                "serverInfo": {
                                    "name": "SCIKIQMCP",
                                    "version": "1.0.0"
                                }
                            }
                        }
                        logger.info(f"Initialize response: {response}")
                        return JSONResponse(response)
                        
                    elif method == "tools/list":
                        # List available tools
                        logger.info("Tools list request")
                        tools = await self.mcp_server.list_tools()
                        response = {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "result": tools
                        }
                        logger.info(f"Tools list response: {response}")
                        return JSONResponse(response)
                        
                    elif method == "tools/call":
                        # Call a specific tool
                        params = body.get("params", {})
                        tool_name = params.get("name")
                        arguments = params.get("arguments", {})
                        
                        logger.info(f"Tool call request: tool={tool_name}, args={arguments}")
                        
                        if not tool_name:
                            error_response = {
                                "jsonrpc": "2.0",
                                "id": request_id,
                                "error": {"code": -32602, "message": "Invalid params: missing tool name"}
                            }
                            logger.error(f"Tool call error response: {error_response}")
                            return JSONResponse(error_response)
                        
                        result = await self.mcp_server.call_tool(tool_name, arguments)
                        response = {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "result": result
                        }
                        logger.info(f"Tool call response: {response}")
                        return JSONResponse(response)
                        
                    else:
                        # Unknown method
                        error_response = {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "error": {"code": -32601, "message": f"Method not found: {method}"}
                        }
                        logger.error(f"Unknown method error: {error_response}")
                        return JSONResponse(error_response)
                        
                except Exception as e:
                    logger.error(f"MCP protocol error: {e}")
                    error_response = {
                        "jsonrpc": "2.0",
                        "id": body.get("id") if 'body' in locals() else None,
                        "error": {"code": -32603, "message": f"Internal error: {str(e)}"}
                    }
                    return JSONResponse(error_response)
            else:
                # HEAD or GET - return server info
                return JSONResponse({
                    "protocol": "mcp",
                    "version": "1.0",
                    "server": "SCIKIQMCP",
                    "endpoints": {
                        "tools": "/mcp/tools",
                        "call": "/mcp/call"
                    }
                })
        
        # Register endpoint - creates clients via API
        async def register_client(request: Request):
            """Dynamic Client Registration (API)"""
            try:
                data = await request.json()
                client_name = data.get("client_name", "API Client")
                redirect_uris = data.get("redirect_uris", ["http://localhost:*"])
                
                # For API registration, we'll use a system user ID (1) or create one
                # In production, you might want to require API authentication
                client_data = self.db_manager.create_oauth_client(client_name, 1, redirect_uris)
                
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
        
        # Other OAuth and MCP endpoints would go here...
        
        async def authorize_endpoint(request: Request):
            """OAuth 2.1 Authorization Endpoint"""
            try:
                # Get query parameters
                response_type = request.query_params.get("response_type")
                client_id = request.query_params.get("client_id")
                redirect_uri = request.query_params.get("redirect_uri")
                scope = request.query_params.get("scope", "mcp")
                state = request.query_params.get("state")
                code_challenge = request.query_params.get("code_challenge")
                code_challenge_method = request.query_params.get("code_challenge_method", "S256")
                
                logger.info(f"Authorization request: client_id={client_id}, redirect_uri={redirect_uri}")
                
                # Validate required parameters
                if not all([response_type, client_id, redirect_uri]):
                    logger.error("Missing required parameters")
                    return JSONResponse(
                        {"error": "invalid_request", "error_description": "Missing required parameters"},
                        status_code=400
                    )
                
                if response_type != "code":
                    logger.error(f"Unsupported response type: {response_type}")
                    return JSONResponse(
                        {"error": "unsupported_response_type", "error_description": "Only 'code' response type is supported"},
                        status_code=400
                    )
                
                # Validate client
                logger.info(f"Looking up client: {client_id}")
                client = self.db_manager.get_oauth_client(client_id)
                if not client:
                    logger.error(f"Client not found: {client_id}")
                    return JSONResponse(
                        {"error": "invalid_client", "error_description": "Invalid client_id"},
                        status_code=400
                    )
                
                logger.info(f"Client found: {client['client_name']}, redirect_uris: {client['redirect_uris']}")
                
                # Validate redirect URI
                if redirect_uri not in client["redirect_uris"]:
                    # Check for wildcard localhost pattern
                    localhost_allowed = any(
                        uri.startswith("http://localhost:") and uri.endswith("*") 
                        for uri in client["redirect_uris"]
                    )
                    if not (localhost_allowed and redirect_uri.startswith("http://localhost:")):
                        logger.error(f"Invalid redirect URI: {redirect_uri}, allowed: {client['redirect_uris']}")
                        return JSONResponse(
                            {"error": "invalid_request", "error_description": f"Invalid redirect_uri: {redirect_uri}"},
                            status_code=400
                        )
                
                # For Claude's API integration, we auto-approve the authorization
                # In a real system, you might show a user consent screen here
                
                logger.info(f"Creating authorization code for client: {client_id}")
                # Create authorization code
                auth_code = self.db_manager.create_authorization_code(
                    client_id=client_id,
                    redirect_uri=redirect_uri,
                    scope=scope,
                    code_challenge=code_challenge,
                    code_challenge_method=code_challenge_method,
                    state=state
                )
                

                logger.info(f"Authorization code created: {auth_code}")
                
                # Build redirect URL
                from urllib.parse import urlencode
                params = {"code": auth_code}
                if state:
                    params["state"] = state
                
                redirect_url = f"{redirect_uri}?{urlencode(params)}"
                logger.info(f"Redirecting to: {redirect_url}")
                return RedirectResponse(url=redirect_url, status_code=302)
                
            except Exception as e:
                logger.error(f"Authorization error: {str(e)}", exc_info=True)
                return JSONResponse(
                    {"error": "server_error", "error_description": f"Internal server error: {str(e)}"},
                    status_code=500
                )
        
        async def token_endpoint(request: Request):
            """OAuth 2.1 Token Endpoint"""
            try:
                form_data = await request.form()
                grant_type = form_data.get("grant_type")
                
                logger.info(f"Token request: grant_type={grant_type}")
                logger.info(f"Form data keys: {list(form_data.keys())}")
                
                if grant_type == "authorization_code":
                    # Authorization code grant
                    code = form_data.get("code")
                    redirect_uri = form_data.get("redirect_uri") 
                    client_id = form_data.get("client_id")
                    code_verifier = form_data.get("code_verifier")
                    
                    logger.info(f"Token exchange: client_id={client_id}, code={code[:20]}..., redirect_uri={redirect_uri}")
                    
                    if not all([code, redirect_uri, client_id]):
                        logger.error(f"Missing parameters: code={bool(code)}, redirect_uri={bool(redirect_uri)}, client_id={bool(client_id)}")
                        return JSONResponse(
                            {"error": "invalid_request", "error_description": "Missing required parameters"},
                            status_code=400
                        )
                    
                    # Validate authorization code
                    logger.info(f"Validating authorization code...")
                    code_data = self.db_manager.validate_authorization_code(
                        code=code,
                        client_id=client_id,
                        redirect_uri=redirect_uri,
                        code_verifier=code_verifier
                    )
                    
                    if not code_data:
                        logger.error(f"Authorization code validation failed for code: {code[:20]}...")
                        return JSONResponse(
                            {"error": "invalid_grant", "error_description": "Invalid or expired authorization code"},
                            status_code=400
                        )
                    
                    logger.info(f"Authorization code validated successfully, creating access token...")
                    
                    # Create access token
                    token_data = self.db_manager.create_access_token(
                        client_id=client_id,
                        scope=code_data["scope"]
                    )
                    
                    logger.info(f"Access token created: {token_data.get('access_token', '')[:20]}...")
                    return JSONResponse(token_data)
                
                elif grant_type == "refresh_token":
                    # Refresh token grant (implement if needed)
                    return JSONResponse(
                        {"error": "unsupported_grant_type", "error_description": "Refresh token not yet implemented"},
                        status_code=400
                    )
                
                else:
                    return JSONResponse(
                        {"error": "unsupported_grant_type", "error_description": f"Grant type '{grant_type}' not supported"},
                        status_code=400
                    )
                    
            except Exception as e:
                logger.error(f"Token endpoint error: {str(e)}", exc_info=True)
                return JSONResponse(
                    {"error": "server_error", "error_description": f"Internal server error: {str(e)}"},
                    status_code=500
                )
        
        # Protected MCP endpoints
        async def list_tools_endpoint(request: Request):
            """List available MCP tools (OAuth protected)"""
            # Check OAuth authentication
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return JSONResponse(
                    {"error": "unauthorized", "error_description": "Bearer token required"},
                    status_code=401,
                    headers={"WWW-Authenticate": "Bearer"}
                )
            
            token = auth_header[7:]
            token_data = self.db_manager.validate_access_token(token)
            if not token_data:
                return JSONResponse(
                    {"error": "invalid_token", "error_description": "Invalid or expired access token"},
                    status_code=401,
                    headers={"WWW-Authenticate": "Bearer"}
                )
            
            try:
                tools = await self.mcp_server.list_tools()
                return JSONResponse(tools)
            except Exception as e:
                logger.error(f"Error listing tools: {e}")
                return JSONResponse(
                    {"error": f"Failed to list tools: {str(e)}"},
                    status_code=500
                )
        
        async def call_tool_endpoint(request: Request):
            """Call MCP tool (OAuth protected)"""
            # Check OAuth authentication
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return JSONResponse(
                    {"error": "unauthorized", "error_description": "Bearer token required"},
                    status_code=401,
                    headers={"WWW-Authenticate": "Bearer"}
                )
            
            token = auth_header[7:]
            token_data = self.db_manager.validate_access_token(token)
            if not token_data:
                return JSONResponse(
                    {"error": "invalid_token", "error_description": "Invalid or expired access token"},
                    status_code=401,
                    headers={"WWW-Authenticate": "Bearer"}
                )
                
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
                logger.error(f"Error calling tool: {e}")
                return JSONResponse(
                    {"error": f"Failed to call tool: {str(e)}"},
                    status_code=500
                )
        # (authorize_endpoint, token_endpoint, mcp endpoints, etc.)
        # I'll add the key ones for brevity
        
        # Health endpoint
        async def health_check(request: Request):
            """Health check endpoint"""
            return JSONResponse({
                "status": "healthy",
                "service": "SciKiq DB Utils MCP Server",
                "version": "2.0.0",
                "authentication": "OAuth 2.1 with Admin Management",
                "admin_panel": f"{self.base_url}/admin/login",
                "yaml_paths": self.yaml_paths
            })
        
        # MCP info endpoint
        async def mcp_info(request: Request):
            """MCP server information"""
            return JSONResponse({
                "name": "SciKiq DB Utils MCP Server",
                "version": "2.0.0", 
                "description": "Database connectivity with admin-managed OAuth 2.1",
                "capabilities": {
                    "tools": True,
                    "resources": False,
                    "prompts": False,
                    "authentication": "OAuth 2.1",
                    "admin_management": True
                },
                "endpoints": {
                    "tools": "/mcp/tools",
                    "call": "/mcp/call",
                    "health": "/health",
                    "admin": "/admin/login"
                }
            })
        
        # Create routes
        routes = [
            # Root MCP protocol endpoint
            Route("/", endpoint=mcp_root_endpoint, methods=["GET", "POST", "HEAD"]),
            
            # Public endpoints
            Route("/health", endpoint=health_check, methods=["GET"]),
            Route("/mcp/info", endpoint=mcp_info, methods=["GET"]),
            Route("/.well-known/oauth-authorization-server", endpoint=oauth_metadata, methods=["GET"]),
            Route("/.well-known/oauth-protected-resource", endpoint=oauth_protected_resource_metadata, methods=["GET"]),
            
            # Admin endpoints
            Route("/admin/login", endpoint=admin_login_page, methods=["GET", "POST"]),
            Route("/admin/dashboard", endpoint=admin_dashboard, methods=["GET"]),
            Route("/admin/clients/new", endpoint=create_client_page, methods=["GET", "POST"]),
            Route("/admin/clients/{client_id}/edit", endpoint=edit_client_page, methods=["GET", "POST"]),
            
            # OAuth endpoints
            Route("/register", endpoint=register_client, methods=["POST"]),
            Route("/authorize", endpoint=authorize_endpoint, methods=["GET"]),
            Route("/token", endpoint=token_endpoint, methods=["POST"]),
            
            # Protected MCP endpoints (require OAuth authentication)
            Route("/mcp/tools", endpoint=list_tools_endpoint, methods=["GET"]),
            Route("/mcp/call", endpoint=call_tool_endpoint, methods=["POST"]),
        ]
        
        # Create Starlette app
        app = Starlette(
            debug=self.debug,
            routes=routes,
        )
        
        # Add middleware (order matters - first added is executed last)
        app.add_middleware(OAuthAuthMiddleware, db_manager=self.db_manager)
        app.add_middleware(AdminAuthMiddleware, db_manager=self.db_manager)
        
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
        
        logger.info(f"🚀 SciKiq MCP Server with Admin Management starting on http://{self.host}:{self.port}")
        logger.info(f"🔧 YAML Files: {self.yaml_paths}")
        logger.info(f"🛡️ Auth: OAuth 2.1 with Admin Panel")
        logger.info(f"👤 Admin Panel: {self.base_url}/admin/login")
        logger.info(f"📡 OAuth: {self.base_url}/.well-known/oauth-authorization-server")
        
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
@click.option("--host", default="0.0.0.0", help="Host to bind to")
@click.option("--port", default=3000, help="Port to listen on")
@click.option("--yaml-files", multiple=True, type=click.Path(exists=True), help="YAML tool files to load")
@click.option("--config-path-unused", help="Path to database configuration file")
@click.option("--db-path", default="mcp_auth.db", help="Path to authentication database")
@click.option("--create-admin", help="Create admin user: username:password:email")
@click.option("--debug", is_flag=True, help="Enable debug mode")
def main(host: str, port: int, config_path_unused: str, db_path: str, create_admin: str, debug: bool, yaml_files: tuple) -> int:
    """
    SciKiq DB Utils - Remote MCP Server with Admin Management
    
    Environment Variables:
        SERVER_BASE_URL: Base URL for OAuth endpoints (e.g., https://mcp.scikiq.com)
                        If not set, defaults to http://localhost:PORT
    
    Examples:
    
        # Create admin user and start server
        python remote_mcp_server_admin.py --create-admin admin:password123:admin@example.com
        
        # Start server (admin must be created first)
        python remote_mcp_server_admin.py --debug
        
        # Production deployment with environment variable
        export SERVER_BASE_URL=https://mcp.scikiq.com
        python remote_mcp_server_admin.py --host 0.0.0.0 --port 80
        
        # Custom configuration
        python remote_mcp_server_admin.py --host 0.0.0.0 --port 8080 --db-path custom.db
    """
    
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Create database manager
    db_manager = DatabaseManager(db_path)
    
    # Create admin user if requested
    if create_admin:
        try:
            parts = create_admin.split(":")
            if len(parts) < 2:
                logger.error("❌ Create admin format: username:password[:email]")
                return 1
            
            username = parts[0]
            password = parts[1]
            email = parts[2] if len(parts) > 2 else None
            
            admin_user = db_manager.create_admin_user(username, password, email)
            logger.info(f"✅ Admin user created: {admin_user['username']}")
            logger.info(f"🔗 Login at: http://{host}:{port}/admin/login")
            
            if not debug:
                return 0  # Exit after creating admin user unless in debug mode
                
        except ValueError as e:
            logger.error(f"❌ Failed to create admin user: {e}")
            return 1
    
    # Create and run server
    server = RemoteMCPServerWithAdmin(
        host=host,
        port=port,
        yaml_paths=list(yaml_files) if yaml_files else [],
        db_path=db_path,
        debug=debug
    )
    
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