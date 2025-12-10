# SCIKIQ MCP Studio

AI-powered tool by SCIKIQ to analyze and convert REST APIs to Anthropic MCP (Model Context Protocol) tools. Now with support for Swagger/OpenAPI parsing, auto-deployment to Claude Desktop, and online deployment with OAuth 2.1.

## Features

- 🔍 **Intelligent API Scanning** - Automatically detect and analyze API endpoints in Python projects
- 📜 **Swagger/OpenAPI Support** - Parse and convert Swagger/OpenAPI specifications to MCP tools
- 🤖 **AI-Powered Analysis** - Use GPT-4 to score API suitability for MCP conversion
- 🚀 **Auto-Deployment** - Automatically configure and register MCP servers with Claude Desktop
- ☁️ **Online Deployment** - Deploy MCP servers to AWS/Azure with HTTPS and OAuth 2.1 support
- 📊 **Domain Grouping** - Organize APIs by business domain with visual tree view
- ⚡ **Bulk Operations** - Analyze and convert multiple APIs simultaneously
- 📝 **Code Generation** - Generate production-ready MCP server code
- 🎨 **Syntax Highlighting** - Preview generated code with syntax highlighting
- 📖 **Setup Guide** - Step-by-step Claude Desktop integration instructions

## Installation

1. **Clone or extract the project**
   ```bash
   cd C:\demo\mcp-app
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   # or
   source venv/bin/activate  # Linux/Mac
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env and add your Azure OpenAI credentials
   ```

## Configuration

Create a `.env` file with the following:

```env
# Azure OpenAI Configuration
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4

# Flask Configuration
SECRET_KEY=your-secret-key-here
FLASK_ENV=development

# Optional: Claude Desktop Configuration
CLAUDE_DESKTOP_PATH=C:\Users\YourUser\AppData\Local\Programs\Claude
```

## Usage

1. **Start the server**
   ```bash
   python app.py
   ```

2. **Open browser**
   ```
   http://localhost:30211
   ```

3. **Scan your project**
   - Click "Scan Project"
   - Select the Python file containing your API routes OR provide a Swagger URL
   - View detected APIs organized by domain

4. **Analyze APIs**
   - Select individual APIs or use bulk analysis
   - Review AI-generated suitability scores
   - Filter for high-confidence APIs (80%+)

5. **Convert to MCP**
   - Select APIs to convert
   - Generate MCP server code
   - **Auto-Deploy**: Click "Deploy to Claude" to automatically register with Claude Desktop
   - **Online Deploy**: Click "Deploy Online" to deploy to AWS/Azure with OAuth

## API Endpoints

### Scanning
- `POST /api/scan-project` - Scan project for API endpoints
- `POST /api/scan-swagger` - Scan Swagger/OpenAPI specification

### Analysis
- `POST /api/analyze-endpoint` - Analyze single endpoint
- `POST /api/bulk-analyze-apis` - Analyze multiple endpoints

### Conversion
- `POST /api/batch-convert-to-mcp` - Convert APIs to MCP server

### Deployment
- `POST /api/auto-deploy` - Deploy to local Claude Desktop
- `POST /api/deploy-online` - Deploy to online infrastructure (AWS/Azure)

### Utilities
- `POST /api/read-file` - Read file content
- `GET /generated/<filename>` - Serve generated MCP files

## Project Structure

```
mcp-app/
├── app.py                          # Main Flask application
├── mcp_routes.py                   # API routes and handlers
├── intelligent_mcp_converter.py    # Intelligent API scanner
├── swagger_parser.py               # Swagger/OpenAPI parser
├── auto_deploy_mcp.py              # Auto-deployment logic
├── online_deployment.py            # Online deployment logic (AWS/Azure)
├── templates/
│   └── index.html                  # MCP Studio UI
├── generated_servers/              # Generated MCP server files
├── dbhandler_mcpserver/            # Database MCP server components
├── requirements.txt                # Python dependencies
└── README.md                       # This file
```

## How It Works

1. **Scanning Phase**
   - Parses Python files to detect API routes using AST analysis
   - Fetches and parses Swagger/OpenAPI specifications
   - Identifies Flask, FastAPI, Django endpoints

2. **Analysis Phase**
   - Sends endpoint code/spec to Azure OpenAI GPT-4
   - Receives MCP suitability score (0-100%)
   - Gets plain English explanations
   - Identifies strengths and weaknesses

3. **Conversion Phase**
   - Generates MCP server code from selected APIs
   - Creates proper MCP tool definitions
   - Includes parameter schemas
   - Adds documentation and examples

4. **Deployment Phase**
   - **Local**: Updates Claude Desktop config and restarts Claude
   - **Online**: Provisions AWS/Azure resources, sets up Nginx, SSL, and OAuth 2.1

## Technologies

- **Backend**: Flask 3.0, Starlette, Uvicorn
- **AI**: Azure OpenAI GPT-4
- **Frontend**: Vanilla JavaScript + Bootstrap 5
- **MCP**: Anthropic Model Context Protocol
- **Auth**: Authlib (OAuth 2.1)
- **Cloud**: Boto3 (AWS), Azure SDK
- **Languages**: Python 3.8+

## License

MIT License

## Support

For issues or questions, please open an issue on GitHub.
