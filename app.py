"""
SCIKIQ MCP Studio - Standalone API to MCP Conversion Tool
AI-powered tool by SCIKIQ to analyze and convert REST APIs to Anthropic MCP tools
"""
from flask import Flask, render_template, jsonify
from flask_cors import CORS
from datetime import datetime
import os
from dotenv import load_dotenv

from mcp_routes import setup_mcp_routes

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'mcp-studio-secret-key-change-in-production')
CORS(app)

# Setup MCP routes
setup_mcp_routes(app)

# ==================== HEALTH CHECK ====================

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'application': 'SCIKIQ MCP Studio',
        'version': '2.0',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/about')
def about():
    """About page"""
    return jsonify({
        'name': 'SCIKIQ MCP Studio',
        'description': 'AI-powered tool by SCIKIQ to analyze and convert REST APIs to Anthropic MCP tools',
        'version': '2.0',
        'features': [
            'Intelligent API scanning and detection',
            'AI-powered API analysis with confidence scoring',
            'Domain-based API grouping',
            'Bulk API analysis and conversion',
            'Generated MCP server code with syntax highlighting',
            'Multi-select and filtering capabilities',
            'Real-time code preview'
        ],
        'capabilities': [
            'Scan Python projects for API endpoints',
            'Analyze API suitability for MCP conversion',
            'Generate production-ready MCP server code',
            'Provide setup instructions for Claude Desktop',
            'Support multiple frameworks (Flask, FastAPI, Django)'
        ],
        'tech_stack': {
            'backend': 'Flask',
            'ai': 'Azure OpenAI GPT-4',
            'frontend': 'Vanilla JS + Bootstrap',
            'mcp': 'Anthropic MCP SDK'
        }
    })

# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({
        'error': 'Not Found',
        'message': 'The requested resource was not found',
        'status': 404
    }), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return jsonify({
        'error': 'Internal Server Error',
        'message': 'An internal server error occurred',
        'status': 500
    }), 500

# ==================== STARTUP ====================

if __name__ == '__main__':
    print("\n" + "="*70)
    print("[START] SCIKIQ MCP Studio Starting...")
    print("="*70)
    print("\nSCIKIQ MCP Studio - API to MCP Conversion Tool")
    print("   - Home: http://localhost:9555")
    print("   - Health Check: http://localhost:9555/health")
    print("   - About: http://localhost:9555/about")
    print("\nAPI Endpoints:")
    print("   - Scan Project: POST /api/scan-project")
    print("   - Analyze Endpoint: POST /api/analyze-endpoint")
    print("   - Bulk Analyze: POST /api/bulk-analyze-apis")
    print("   - Batch Convert: POST /api/batch-convert-to-mcp")
    print("   - Read File: POST /api/read-file")
    print("\nFeatures:")
    print("   - [+] Intelligent API detection with reasoning")
    print("   - [+] AI-powered MCP suitability scoring")
    print("   - [+] Domain-grouped API tree view")
    print("   - [+] Bulk analysis & conversion")
    print("   - [+] Generated MCP server code")
    print("   - [+] Claude Desktop integration guide")
    print("\n" + "="*70)
    print("[READY] Server starting on port 9555")
    print("="*70 + "\n")

    app.run(debug=True, host='0.0.0.0', port=9555, use_reloader=False)
