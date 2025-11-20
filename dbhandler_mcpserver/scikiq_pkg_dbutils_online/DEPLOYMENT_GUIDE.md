# SciKiq DB Utils - Claude Connector Deployment Guide

## Remote MCP Server Deployment

This guide explains how to deploy the SciKiq DB Utils MCP Server as a remote Claude Connector.

### Quick Start

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Database Connections**
   ```bash
   # Copy and edit the configuration file
   cp config.ini.example config.ini
   # Edit config.ini with your database connections
   ```

3. **Start Remote Server**
   ```bash
   # For local development
   python remote_mcp_server.py --debug
   
   # For production deployment
   python remote_mcp_server.py --host 0.0.0.0 --port 8080
   ```

4. **Add to Claude Desktop**
   - Go to Settings > Connectors in Claude Desktop
   - Add new connector with URL: `http://your-server:port/mcp`

### Deployment Options

#### Local Development
```bash
python remote_mcp_server.py --debug --port 3000
```
**Connector URL**: `http://localhost:3000/mcp`

#### Docker Deployment
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8080

CMD ["python", "remote_mcp_server.py", "--host", "0.0.0.0", "--port", "8080"]
```

#### Cloud Deployment (Railway, Render, etc.)
```bash
# Set environment variables
CONFIG_PATH=config.ini
PORT=8080

# Start command
python remote_mcp_server.py --host 0.0.0.0 --port $PORT
```

#### AWS Lambda/Serverless
Use AWS Lambda with the ASGI adapter:
```python
from mangum import Mangum
from remote_mcp_server import RemoteMCPServer

server = RemoteMCPServer()
app = await server.create_starlette_app()
handler = Mangum(app)
```

### Configuration

#### Environment Variables
- `CONFIG_PATH`: Path to database configuration file (default: config.ini)
- `PORT`: Server port (default: 3000)
- `HOST`: Server host (default: 0.0.0.0)
- `CORS_ORIGINS`: Comma-separated list of allowed origins

#### Command Line Options
```bash
python remote_mcp_server.py --help

Options:
  --host TEXT                     Host to bind to (default: 0.0.0.0)
  --port INTEGER                  Port to listen on (default: 3000)
  --transport [streamable-http|sse]  Transport type (default: streamable-http)
  --config-path TEXT              Path to configuration file
  --cors-origins TEXT             Allowed CORS origins (repeatable)
  --enable-auth                   Enable OAuth authentication
  --debug                         Enable debug mode
```

### Security Configuration

#### CORS Settings
```bash
# Allow specific origins
python remote_mcp_server.py \
  --cors-origins https://claude.ai \
  --cors-origins https://claude.com
```

#### Authentication (Optional)
```bash
# Enable OAuth authentication
python remote_mcp_server.py --enable-auth
```

#### Network Security
- Use HTTPS in production
- Configure firewall rules
- Use VPN or private networks when possible
- Implement rate limiting

### Monitoring

#### Health Check
```bash
curl http://your-server:port/health
```

Response:
```json
{
  "status": "healthy",
  "service": "SciKiq DB Utils MCP Server"
}
```

#### Logging
- Debug mode: `--debug` flag
- Production: Configure log aggregation
- Monitor database connection health

### Claude Desktop Integration

#### Add Remote Connector

1. **Open Claude Desktop Settings**
   - Go to Settings > Connectors

2. **Add New Connector**
   - Name: "SciKiq DB Utils"
   - URL: `http://your-server:port/mcp`
   - Description: "Database connectivity and analysis"

3. **Test Connection**
   - Claude will verify the connector is working
   - Test with: "Show me all my databases"

#### Example Connector URLs

| Environment | URL |
|-------------|-----|
| Local Dev | `http://localhost:3000/mcp` |
| Docker | `http://localhost:8080/mcp` |
| Production | `https://your-domain.com/mcp` |
| Cloud Service | `https://your-app.railway.app/mcp` |

### Troubleshooting

#### Connection Issues
```bash
# Check if server is running
curl http://localhost:3000/health

# Test MCP endpoint
curl -X POST http://localhost:3000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}'
```

#### Configuration Issues
```bash
# Test with debug mode
python remote_mcp_server.py --debug

# Check configuration file
python -c "from scikiq_dbutils.mcp_server.config.ini_parser import IniConfigParser; print(IniConfigParser('config.ini').parse_all_connections())"
```

#### Database Connection Issues
```bash
# Test specific database connection
python -c "
from scikiq_dbutils.mcp_server.tools.database_tools import test_database_connection
result = test_database_connection('your_connection_id')
print(result)
"
```

### Production Best Practices

#### Performance
- Use persistent database connections
- Configure connection pooling
- Monitor memory usage
- Use async operations

#### Security
- Enable HTTPS with valid certificates
- Implement authentication for sensitive data
- Use environment variables for credentials
- Regular security updates

#### Reliability
- Implement graceful shutdown
- Add health checks
- Configure restart policies
- Monitor error rates

#### Scaling
- Use load balancers for multiple instances
- Configure horizontal pod autoscaling
- Implement circuit breakers
- Monitor response times

### Examples

#### Local Development Setup
```bash
# 1. Start the server
python remote_mcp_server.py --debug --port 3000

# 2. Add to Claude Desktop
# Settings > Connectors > Add Connector
# URL: http://localhost:3000/mcp

# 3. Test in Claude
"Show me all my databases"
"What tables are in my production database?"
```

#### Production Docker Setup
```yaml
# docker-compose.yml
version: '3.8'
services:
  scikiq-mcp:
    build: .
    ports:
      - "8080:8080"
    environment:
      - CONFIG_PATH=/app/config.ini
    volumes:
      - ./config.ini:/app/config.ini:ro
    restart: unless-stopped
```

#### Cloud Railway Deployment
```json
{
  "build": {
    "buildCommand": "pip install -r requirements.txt"
  },
  "deploy": {
    "startCommand": "python remote_mcp_server.py --host 0.0.0.0 --port $PORT",
    "restartPolicyType": "ON_FAILURE"
  }
}
```

### Support

For issues and questions:
- Check the [MCP_SERVER_DOCUMENTATION.md](MCP_SERVER_DOCUMENTATION.md) for comprehensive documentation
- Review the [SETUP_GUIDE.md](SETUP_GUIDE.md) for detailed setup instructions
- Use the [QUICK_REFERENCE.md](QUICK_REFERENCE.md) for troubleshooting

---

*SciKiq DB Utils Remote MCP Server - Connecting Claude to Your Data Universe* 🌟