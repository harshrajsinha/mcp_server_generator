# 🏗️ Architecture Diagram - Complete System

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        MCP STUDIO v2.0                              │
│                    (Feature Parity Complete)                        │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │                           │
                    ▼                           ▼
        ┌───────────────────┐        ┌──────────────────┐
        │   FRONTEND UI     │        │   BACKEND API    │
        │   (index.html)    │        │  (mcp_routes.py) │
        └───────────────────┘        └──────────────────┘
                    │                           │
        ┌───────────┼───────────┬──────────────┼──────────────┐
        │           │           │              │              │
        ▼           ▼           ▼              ▼              ▼
    ┌───────┐  ┌────────┐  ┌────────┐    ┌────────┐    ┌──────────┐
    │Swagger│  │Codebase│  │Database│    │ Deploy │    │  GitHub  │
    │ Modal │  │ Modal  │  │ Modal  │    │Endpoint│    │  Scanner │
    └───────┘  └────────┘  └────────┘    └────────┘    └──────────┘
        │           │           │              │              │
        └───────────┴───────────┴──────────────┴──────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │                           │
                    ▼                           ▼
        ┌───────────────────┐        ┌──────────────────┐
        │  MCP SERVER       │        │   DEPLOYMENT     │
        │  GENERATOR        │        │   ENGINE         │
        └───────────────────┘        └──────────────────┘
                    │                           │
        ┌───────────┴───────────┐   ┌──────────┴──────────┐
        │                       │   │                     │
        ▼                       ▼   ▼                     ▼
    ┌─────────┐           ┌─────────┐              ┌──────────┐
    │ MCP     │           │ OAuth   │              │  Cloud   │
    │ Server  │           │ Server  │              │ Provider │
    │ Code    │           │ Code    │              │(AWS/Azure│
    └─────────┘           └─────────┘              └──────────┘
```

## Detailed Component Architecture

### Frontend Layer (index.html)

```
┌──────────────────────────────────────────────────────────────┐
│                     USER INTERFACE                           │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────┐│
│  │ OPTION 1         │  │ OPTION 2         │  │ OPTION 3   ││
│  │ Swagger/OpenAPI  │  │ RestAPI Codebase │  │ Database   ││
│  ├──────────────────┤  ├──────────────────┤  ├────────────┤│
│  │                  │  │                  │  │            ││
│  │ • Swagger URL    │  │ • Source Type:   │  │ • DB Type  ││
│  │ • Base URL       │  │   - Local Folder │  │ • Host     ││
│  │                  │  │   - GitHub Repo  │  │ • Database ││
│  │ ☑ OAuth Server   │  │                  │  │ • Username ││
│  │   • Provider     │  │ • Project Path   │  │ • Password ││
│  │   • Client ID    │  │ • GitHub URL     │  │            ││
│  │   • Client Sec   │  │ • Branch         │  │ ☑ OAuth    ││
│  │   • Auth URL     │  │ • Token          │  │   Server   ││
│  │   • Token URL    │  │                  │  │            ││
│  │   • User Info    │  │ ☑ OAuth Server   │  │ Local ⚙️   ││
│  │   • Redirect URI │  │   [Same as ←]    │  │ Online ☁️  ││
│  │                  │  │                  │  │            ││
│  │  [Import]        │  │  [Scan]          │  │[Generate]  ││
│  └──────────────────┘  └──────────────────┘  └────────────┘│
│                                                              │
├──────────────────────────────────────────────────────────────┤
│                   DEPLOYMENT MODAL                           │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│        ┌────────────────┐         ┌────────────────┐        │
│        │   Local 💻     │         │   Online ☁️    │        │
│        │                │         │                │        │
│        │ Deploy to      │         │ Choose:        │        │
│        │ Claude Desktop │         │  • AWS EC2     │        │
│        │                │         │  • Azure VM    │        │
│        │ [Deploy Now]   │         │  • Remote SSH  │        │
│        └────────────────┘         └────────────────┘        │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Backend Layer (Flask Routes)

```
┌──────────────────────────────────────────────────────────────┐
│                      BACKEND API                             │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              EXISTING ENDPOINTS                        │ │
│  ├────────────────────────────────────────────────────────┤ │
│  │ GET  /                  → index.html                   │ │
│  │ POST /api/scan-project  → Scan local codebase          │ │
│  │ POST /api/parse-swagger → Parse Swagger JSON           │ │
│  │ POST /api/generate-db   → Generate database MCP        │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              NEW ENDPOINTS (v2.0)                      │ │
│  ├────────────────────────────────────────────────────────┤ │
│  │ POST /api/deploy-mcp-local                             │ │
│  │      → Deploy to Claude Desktop                        │ │
│  │      • Creates backup                                  │ │
│  │      • Updates config JSON                             │ │
│  │      • Returns paths                                   │ │
│  │                                                        │ │
│  │ POST /api/scan-github-repo                             │ │
│  │      → Clone and scan GitHub repository                │ │
│  │      • git clone with token                            │ │
│  │      • Scan for APIs                                   │ │
│  │      • Cleanup temp dir                                │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │           UPDATED ENDPOINTS (v2.0)                     │ │
│  ├────────────────────────────────────────────────────────┤ │
│  │ POST /api/deploy/aws                                   │ │
│  │      • Now accepts: server_type, oauth_config          │ │
│  │                                                        │ │
│  │ POST /api/deploy/azure                                 │ │
│  │      • Now accepts: server_type, oauth_config          │ │
│  │                                                        │ │
│  │ POST /api/deploy/remote                                │ │
│  │      • Now accepts: server_type, oauth_config          │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### MCP Server Generation

```
┌──────────────────────────────────────────────────────────────┐
│              generate_mcp_server_code()                      │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Input:                                                      │
│    • mcp_tools: List[Tool]                                   │
│    • base_url: str                                           │
│    • enable_oauth: bool = False          ← NEW              │
│    • oauth_config: dict = None           ← NEW              │
│                                                              │
│  Output:                                                     │
│    • server_code: str                                        │
│    • oauth_requirements: str             ← NEW              │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│                   Generated MCP Server                       │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ mcp_server.py                                          │ │
│  ├────────────────────────────────────────────────────────┤ │
│  │                                                        │ │
│  │  from mcp.server import Server                         │ │
│  │  import httpx                                          │ │
│  │                                                        │ │
│  │  [IF OAUTH ENABLED]                                    │ │
│  │  from starlette.applications import Starlette          │ │
│  │  from authlib.integrations.starlette_client import ... │ │
│  │  import uvicorn                                        │ │
│  │  import sqlite3                                        │ │
│  │                                                        │ │
│  │  server = Server("scikiq-mcp-autoAPI")                 │ │
│  │                                                        │ │
│  │  [IF OAUTH ENABLED]                                    │ │
│  │  oauth = OAuth()                                       │ │
│  │  oauth.register(...)                                   │ │
│  │                                                        │ │
│  │  @server.list_tools()                                  │ │
│  │  async def list_tools():                               │ │
│  │      return [Tool(...), Tool(...), ...]                │ │
│  │                                                        │ │
│  │  @server.call_tool()                                   │ │
│  │  async def call_tool(name, arguments):                 │ │
│  │      # Make HTTP requests to APIs                      │ │
│  │      ...                                               │ │
│  │                                                        │ │
│  │  [IF OAUTH ENABLED]                                    │ │
│  │  async def login(request):                             │ │
│  │      # OAuth login flow                                │ │
│  │                                                        │ │
│  │  async def auth_callback(request):                     │ │
│  │      # OAuth callback handler                          │ │
│  │      # Store tokens in SQLite                          │ │
│  │                                                        │ │
│  │  async def main():                                     │ │
│  │      [IF OAUTH] start_oauth_server()  # port 8080     │ │
│  │      await server.run(...)            # stdio          │ │
│  │                                                        │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Deployment Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    DEPLOYMENT FLOW                           │
└──────────────────────────────────────────────────────────────┘
                                │
                 ┌──────────────┴──────────────┐
                 │                             │
                 ▼                             ▼
    ┌────────────────────┐         ┌────────────────────┐
    │  LOCAL DEPLOYMENT  │         │ ONLINE DEPLOYMENT  │
    └────────────────────┘         └────────────────────┘
                 │                             │
                 │                   ┌─────────┴─────────┐
                 │                   │                   │
                 │                   ▼                   ▼
                 │          ┌─────────────┐     ┌──────────────┐
                 │          │  AWS EC2    │     │  Azure VM    │
                 │          │             │     │              │
                 │          │ • S3 upload │     │ • Storage    │
                 │          │ • EC2 launch│     │ • VM create  │
                 │          │ • Route 53  │     │ • DNS setup  │
                 │          └─────────────┘     └──────────────┘
                 │                   │
                 │                   │          ┌──────────────┐
                 │                   └──────────│ Remote SSH   │
                 │                              │              │
                 │                              │ • SCP upload │
                 │                              │ • Install    │
                 │                              │ • Configure  │
                 │                              └──────────────┘
                 ▼
    ┌────────────────────────────────┐
    │     Claude Desktop Config      │
    ├────────────────────────────────┤
    │ {                              │
    │   "mcpServers": {              │
    │     "my-mcp-server": {         │
    │       "command": "python",     │
    │       "args": [                │
    │         "/path/to/server.py"   │
    │       ]                        │
    │     }                          │
    │   }                            │
    │ }                              │
    └────────────────────────────────┘
```

### OAuth Server Architecture (When Enabled)

```
┌──────────────────────────────────────────────────────────────┐
│                    OAUTH SERVER (Port 8080)                  │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              Starlette Web Application                 │ │
│  ├────────────────────────────────────────────────────────┤ │
│  │                                                        │ │
│  │  GET /login                                            │ │
│  │  └─→ Redirect to OAuth provider                       │ │
│  │                                                        │ │
│  │  GET /auth/callback                                    │ │
│  │  └─→ Exchange code for token                          │ │
│  │  └─→ Store token in SQLite                            │ │
│  │  └─→ Return success page                              │ │
│  │                                                        │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              Token Storage (SQLite)                    │ │
│  ├────────────────────────────────────────────────────────┤ │
│  │                                                        │ │
│  │  oauth_tokens.db                                       │ │
│  │  ┌──────────────────────────────────────────────────┐ │ │
│  │  │ Table: tokens                                    │ │ │
│  │  ├──────────────────────────────────────────────────┤ │ │
│  │  │ id            TEXT PRIMARY KEY                   │ │ │
│  │  │ access_token  TEXT                               │ │ │
│  │  │ refresh_token TEXT                               │ │ │
│  │  │ expires_at    REAL                               │ │ │
│  │  └──────────────────────────────────────────────────┘ │ │
│  │                                                        │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
└──────────────────────────────────────────────────────────────┘

    MCP Server (stdio)          OAuth Server (HTTP)
         Port: -                    Port: 8080
         Protocol: stdio            Protocol: HTTP
         Thread: Main               Thread: Background
```

### GitHub Integration Flow

```
┌──────────────────────────────────────────────────────────────┐
│               GITHUB REPOSITORY SCANNING                     │
└──────────────────────────────────────────────────────────────┘
                                │
                    ┌───────────┴───────────┐
                    │                       │
                    ▼                       ▼
        ┌───────────────────┐   ┌───────────────────┐
        │  Public Repo      │   │  Private Repo     │
        │  (no token)       │   │  (with token)     │
        └───────────────────┘   └───────────────────┘
                    │                       │
                    └───────────┬───────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │  GitPython.clone()    │
                    │  • depth=1            │
                    │  • to temp dir        │
                    └───────────────────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │  scan_codebase()      │
                    │  • Find API routes    │
                    │  • Extract metadata   │
                    └───────────────────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │  Cleanup              │
                    │  • Remove temp dir    │
                    └───────────────────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │  Return Results       │
                    │  • api_definitions[]  │
                    │  • file_tree{}        │
                    │  • intelligence{}     │
                    └───────────────────────┘
```

## Data Flow Diagram

```
User Input (Frontend)
        │
        ├─ Swagger URL ──────────┐
        ├─ GitHub URL ───────────┤
        ├─ Local Path ───────────┤
        ├─ OAuth Config ─────────┼─→ Configuration Object
        └─ Deployment Choice ────┘
                │
                ▼
        Backend Processing
                │
                ├─ Parse Swagger ────────┐
                ├─ Clone GitHub ─────────┤
                ├─ Scan Codebase ────────┼─→ API Definitions[]
                └─ Database Config ──────┘
                │
                ▼
        MCP Server Generation
                │
                ├─ Without OAuth ────→ mcp_server.py (simple)
                │                      requirements.txt (basic)
                │
                └─ With OAuth ───────→ mcp_server.py (with OAuth)
                                       requirements.txt (with authlib)
                                       oauth_tokens.db (runtime)
                │
                ▼
        Deployment
                │
                ├─ Local ────────────→ Claude Desktop Config
                │                      (JSON update)
                │
                └─ Online ───────────→ Cloud Provider
                                       ├─ AWS: S3 + EC2 + Route 53
                                       ├─ Azure: Storage + VM + DNS
                                       └─ SSH: SCP + Install
                │
                ▼
        Running MCP Server
                │
                ├─ Main Thread ──────→ stdio MCP Protocol
                │                      (Claude Desktop)
                │
                └─ Background ───────→ OAuth Server (if enabled)
                                       (HTTP on port 8080)
```

## Technology Stack

```
┌──────────────────────────────────────────────────────────────┐
│                      TECHNOLOGY STACK                        │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Frontend:                                                   │
│    • HTML5 + Bootstrap 5.3.2                                 │
│    • Vanilla JavaScript (ES6+)                               │
│    • Font Awesome 6.5.1                                      │
│    • Marked.js (Markdown rendering)                          │
│                                                              │
│  Backend:                                                    │
│    • Flask 3.0.0 (Python web framework)                      │
│    • GitPython 3.1.40 (Git operations)                       │
│    • boto3 (AWS SDK)                                         │
│    • azure-mgmt-* (Azure SDK)                                │
│    • paramiko (SSH operations)                               │
│                                                              │
│  MCP Server:                                                 │
│    • mcp 1.0.0 (MCP SDK)                                     │
│    • httpx (Async HTTP client)                               │
│    • PyYAML (Config parsing)                                 │
│                                                              │
│  OAuth (Optional):                                           │
│    • authlib 1.3.0 (OAuth library)                           │
│    • uvicorn (ASGI server)                                   │
│    • starlette (Web framework)                               │
│    • cryptography (Crypto operations)                        │
│    • pyjwt (JWT handling)                                    │
│    • sqlite3 (Token storage)                                 │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

## Security Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     SECURITY LAYERS                          │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Layer 1: Input Validation                                   │
│    • URL validation                                          │
│    • Path sanitization                                       │
│    • Token format validation                                 │
│                                                              │
│  Layer 2: Authentication                                     │
│    • GitHub personal access tokens                           │
│    • OAuth 2.1 with PKCE                                     │
│    • AWS/Azure credentials                                   │
│                                                              │
│  Layer 3: Secure Storage                                     │
│    • SQLite for tokens                                       │
│    • Encrypted config backups                                │
│    • No secrets in logs                                      │
│                                                              │
│  Layer 4: Network Security                                   │
│    • HTTPS for OAuth flows                                   │
│    • SSH key authentication                                  │
│    • VPC security groups (AWS)                               │
│                                                              │
│  Layer 5: Access Control                                     │
│    • Claude Desktop config permissions                       │
│    • File system permissions                                 │
│    • Cloud IAM policies                                      │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

**Architecture Version**: 2.0  
**Last Updated**: January 2025  
**Status**: ✅ Production Ready
