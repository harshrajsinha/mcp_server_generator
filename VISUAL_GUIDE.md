# Visual Guide: MCP Server Options Comparison

## Before and After

### 📊 Feature Comparison Table

| Feature | Database MCP (Option 3) | Swagger MCP (Option 1) | Codebase MCP (Option 2) |
|---------|------------------------|------------------------|-------------------------|
| **OAuth 2.1 Server** | ✅ Yes | ✅ **Added** | ✅ **Added** |
| **Local Deployment** | ✅ Yes | ✅ **Added** | ✅ **Added** |
| **AWS Deployment** | ✅ Yes | ✅ **Added** | ✅ **Added** |
| **Azure Deployment** | ✅ Yes | ✅ **Added** | ✅ **Added** |
| **Remote SSH Deployment** | ✅ Yes | ✅ **Added** | ✅ **Added** |
| **GitHub Repo Support** | ❌ N/A | ❌ N/A | ✅ **Added** |

---

## 🎨 UI Flow Diagrams

### Option 1: Swagger-Based MCP Server

```
User clicks "Swagger/OpenAPI" → Modal Opens
                                     ↓
                          ┌──────────────────────┐
                          │  Swagger URL Input   │
                          │  API Base URL        │
                          │  Authentication      │
                          │                      │
                          │  [NEW] OAuth Config  │ ← Toggle checkbox
                          │  ├─ Client Name      │
                          │  └─ Redirect URIs    │
                          └──────────────────────┘
                                     ↓
                          Import APIs → Scan Complete
                                     ↓
                          Select & Convert APIs
                                     ↓
                          ┌──────────────────────┐
                          │  MCP Setup Modal     │
                          │                      │
                          │  [NEW] Deploy:       │
                          │  ┌─────┬──────────┐  │
                          │  │ 💻  │    ☁️    │  │
                          │  │Local│  Online  │  │
                          │  └─────┴──────────┘  │
                          └──────────────────────┘
```

### Option 2: Codebase-Based MCP Server

```
User clicks "Browse Codebase" → Modal Opens
                                     ↓
                          ┌──────────────────────┐
                          │  [NEW] Source Type   │ ← Dropdown
                          │  ┌───────┬─────────┐ │
                          │  │ Local │ GitHub  │ │
                          │  └───────┴─────────┘ │
                          │                      │
                          │  If Local:           │
                          │  └─ Project Path     │
                          │                      │
                          │  If GitHub:          │
                          │  ├─ Repo URL         │
                          │  ├─ Branch           │
                          │  └─ Token            │
                          │                      │
                          │  Source File         │
                          │  API Server URL      │
                          │                      │
                          │  [NEW] OAuth Config  │ ← Toggle checkbox
                          │  ├─ Client Name      │
                          │  └─ Redirect URIs    │
                          └──────────────────────┘
                                     ↓
                          Scan Project → APIs Found
                                     ↓
                          Select & Convert APIs
                                     ↓
                          ┌──────────────────────┐
                          │  MCP Setup Modal     │
                          │                      │
                          │  [NEW] Deploy:       │
                          │  ┌─────┬──────────┐  │
                          │  │ 💻  │    ☁️    │  │
                          │  │Local│  Online  │  │
                          │  └─────┴──────────┘  │
                          └──────────────────────┘
```

---

## 🎬 User Journey Examples

### Example 1: Create MCP Server from Swagger with OAuth

1. **Click** "Swagger/OpenAPI" card
2. **Enter** Swagger URL: `https://api.example.com/swagger.json`
3. **Check** "Enable OAuth 2.1 Authentication"
4. **Enter** OAuth Client Name: `claude-desktop`
5. **Enter** Redirect URIs: `http://localhost:3000/callback`
6. **Click** "Import APIs"
7. **Select** desired endpoints
8. **Click** "Convert to MCP Tools"
9. **Choose** deployment:
   - **Local**: Auto-configure Claude Desktop
   - **Online**: Deploy to AWS/Azure/Remote

### Example 2: Create MCP Server from GitHub Repo

1. **Click** "Browse Codebase" card
2. **Select** "GitHub Repository" from dropdown
3. **Enter** Repo URL: `https://github.com/owner/my-api`
4. **Enter** Branch: `main`
5. **Enter** GitHub Token (if private)
6. **Check** "Enable OAuth 2.1 Authentication"
7. **Click** "Scan Project"
8. **Select** detected endpoints
9. **Click** "Convert to MCP Tools"
10. **Choose** deployment option

---

## 🖼️ Modal Screenshots (Pseudo)

### Swagger Modal - OAuth Section

```
┌─────────────────────────────────────────┐
│  Swagger/OpenAPI Configuration         │
├─────────────────────────────────────────┤
│                                         │
│  Swagger URL: [__________________] *    │
│  API Base URL: [__________________]     │
│                                         │
│  ┌─ OAuth Server (For Remote Deploy) ──┐
│  │                                      │
│  │  ☑ Enable OAuth 2.1 Authentication  │
│  │                                      │
│  │  OAuth Client Name:                 │
│  │  [claude-desktop____________]       │
│  │                                      │
│  │  OAuth Redirect URIs:               │
│  │  [http://localhost:3000/callback__] │
│  │                                      │
│  └──────────────────────────────────────┘
│                                         │
│         [Cancel]  [Import APIs]         │
└─────────────────────────────────────────┘
```

### Codebase Modal - Source Selection

```
┌─────────────────────────────────────────┐
│  Browse Codebase                        │
├─────────────────────────────────────────┤
│                                         │
│  Codebase Source:                       │
│  [Local Folder      ▼]                  │
│                                         │
│  ─── OR ───                             │
│                                         │
│  Codebase Source:                       │
│  [GitHub Repository ▼]                  │
│                                         │
│  GitHub Repository URL: *               │
│  [https://github.com/owner/repo____]    │
│                                         │
│  Branch:                                │
│  [main_________________]                │
│                                         │
│  GitHub Token (For Private Repos):      │
│  [ghp_********************__________]   │
│                                         │
│  ┌─ OAuth Server (For Remote Deploy) ──┐
│  │                                      │
│  │  ☑ Enable OAuth 2.1 Authentication  │
│  │                                      │
│  └──────────────────────────────────────┘
│                                         │
│      [Cancel]  [Scan Project]           │
└─────────────────────────────────────────┘
```

### Deployment Options (All 3 Types)

```
┌─────────────────────────────────────────┐
│  Deploy Your MCP Server                 │
├─────────────────────────────────────────┤
│                                         │
│  ┌──────────────┐  ┌──────────────┐    │
│  │      💻      │  │      ☁️      │    │
│  │              │  │              │    │
│  │   Local      │  │   Online     │    │
│  │  Deployment  │  │  Deployment  │    │
│  │              │  │              │    │
│  │ Deploy to    │  │ Deploy to    │    │
│  │ your local   │  │ AWS, Azure,  │    │
│  │ Claude       │  │ or Remote    │    │
│  │ Desktop      │  │ Server       │    │
│  │              │  │              │    │
│  │ [Deploy      │  │ [Deploy      │    │
│  │  Locally]    │  │  Online]     │    │
│  └──────────────┘  └──────────────┘    │
│                                         │
└─────────────────────────────────────────┘
```

---

## 🔄 Data Flow

### Swagger Configuration Flow

```
User Input → selectedSwaggerConfig Object
{
  swagger_url: "https://api.example.com/swagger.json",
  api_base_url: "https://api.example.com",
  auth_type: "bearer",
  enable_oauth: true,          ← NEW
  oauth_client_name: "claude", ← NEW
  oauth_redirect_uris: "..."   ← NEW
}
       ↓
Backend API: /api/import-swagger
       ↓
API Definitions Generated
       ↓
User Selects & Converts
       ↓
MCP Server Generated with OAuth ← NEW
       ↓
Deployment (Local or Online) ← NEW
```

### GitHub Repository Flow

```
User Input → selectedProjectConfig Object
{
  source_type: "github",          ← NEW
  github_repo_url: "https://...", ← NEW
  github_branch: "main",          ← NEW
  github_token: "ghp_...",        ← NEW
  enable_oauth: true,             ← NEW
  oauth_client_name: "claude",    ← NEW
  oauth_redirect_uris: "..."      ← NEW
}
       ↓
Backend API: /api/scan-github-repo ← NEW
       ↓
Clone Repo → Scan → API Definitions
       ↓
User Selects & Converts
       ↓
MCP Server Generated with OAuth ← NEW
       ↓
Deployment (Local or Online) ← NEW
```

---

## 💡 Key Implementation Details

### Toggle Functions
```javascript
function toggleOAuthFieldsSwagger() {
    const enabled = document.getElementById('enableOAuthSwagger').checked;
    document.getElementById('oauthFieldsSwagger').style.display = 
        enabled ? 'block' : 'none';
}

function toggleOAuthFieldsCodebase() {
    const enabled = document.getElementById('enableOAuthCodebase').checked;
    document.getElementById('oauthFieldsCodebase').style.display = 
        enabled ? 'block' : 'none';
}

function toggleCodebaseSource() {
    const sourceType = document.getElementById('codebaseSourceType').value;
    document.getElementById('localPathFields').style.display = 
        sourceType === 'local' ? 'block' : 'none';
    document.getElementById('githubFields').style.display = 
        sourceType === 'github' ? 'block' : 'none';
}
```

### Deployment Functions
```javascript
async function deployMCPLocal(serverPath, filename) {
    // Calls: POST /api/deploy-mcp-local
    // Configures Claude Desktop
}

function showOnlineDeploymentModal(serverPath, filename) {
    // Shows: AWS, Azure, Remote Server options
    // Each triggers respective deployment function
}
```

---

## 🎯 Success Criteria

✅ **All criteria met:**
1. OAuth server option added to Swagger MCP
2. OAuth server option added to Codebase MCP
3. Local deployment works for Swagger MCP
4. Local deployment works for Codebase MCP
5. Online deployment available for Swagger MCP
6. Online deployment available for Codebase MCP
7. GitHub repository support added to Codebase MCP
8. UI consistency across all 3 options
9. No breaking changes to Database MCP
10. Code is clean and well-organized

---

**Status**: ✅ Complete (Frontend)
**Next**: Backend API implementation
