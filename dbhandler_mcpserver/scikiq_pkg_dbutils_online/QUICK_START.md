# SciKiq DB Utils - Remote MCP Server Quick Start Guide

This guide helps you quickly set up and test the Remote MCP Server for Claude Desktop connectivity.

## 🚀 Quick Start (5 minutes)

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Create Configuration

Copy and customize the configuration file:

```bash
# Windows
copy config.ini.example config.ini

# Linux/Mac  
cp config.ini.example config.ini
```

Edit `config.ini` with your database connection details.

### 3. Start the Server

```bash
# Start with default settings (localhost:3000)
python remote_mcp_server.py

# Start with debug mode for development
python remote_mcp_server.py --debug

# Start for remote access (production)
python remote_mcp_server.py --host 0.0.0.0 --port 8080
```

### 4. Test the Server

```bash
# Run the test suite
python test_remote_server.py
```

### 5. Connect to Claude Desktop

1. Open Claude Desktop
2. Go to Settings > Connectors
3. Add new connector:
   - **Name**: SciKiq DB Utils
   - **URL**: `http://localhost:3000` (or your server URL)
   - **Description**: Database connectivity and analysis

## 🔧 Configuration Examples

### Basic PostgreSQL Connection

```ini
[my_postgres]
database_type = POSTGRES
host = localhost
port = 5432
database = mydb
username = user
password = pass123
```

### Production MySQL with SSL

```ini
[production_mysql]
database_type = MYSQL
host = mysql.company.com
port = 3306
database = production
username = readonly_user
password = ${MYSQL_PASSWORD}
connectivity_mechanism = SSL
ssl_cert_path = /path/to/cert.pem
```

### Cloud BigQuery

```ini
[bigquery_analytics]
database_type = BIGQUERY
project_id = my-project-123
credentials_file = /path/to/service-account.json
dataset = analytics
```

## 🧪 Testing Your Setup

### Health Check

Visit: `http://localhost:3000/health`

Should return:
```json
{
  "status": "healthy",
  "service": "SciKiq DB Utils MCP Server",
  "connections": {...}
}
```

### List Available Tools

Visit: `http://localhost:3000/mcp/tools`

Should return a list of available database tools.

### Test with Claude Desktop

Once connected, try asking Claude:

```
"What database connections are available?"

"Can you show me the tables in my PostgreSQL database?"

"Run a query to count rows in the users table"
```

## 🐳 Docker Deployment (Optional)

### Build and Run

```bash
# Build the image
docker build -t scikiq-mcp-server .

# Run with config file
docker run -d \
  --name scikiq-mcp \
  -p 3000:3000 \
  -v $(pwd)/config.ini:/app/config.ini \
  scikiq-mcp-server
```

### Using Docker Compose

```bash
# Start the full stack
docker-compose up -d

# Check logs
docker-compose logs -f mcp-server
```

## 🔍 Troubleshooting

### Server Won't Start

1. **Check dependencies**: `pip install -r requirements.txt`
2. **Check configuration**: Verify `config.ini` syntax
3. **Check ports**: Ensure port 3000 is available
4. **Run with debug**: `python remote_mcp_server.py --debug`

### Database Connection Issues

1. **Test connectivity**: Use database client tools first
2. **Check credentials**: Verify username/password
3. **Check network**: Ensure database is accessible
4. **Check SSL**: Verify SSL certificates if using SSL

### Claude Desktop Won't Connect

1. **Check URL**: Ensure server is running and accessible
2. **Check CORS**: Server allows all origins by default
3. **Check network**: Firewall might block the connection
4. **Check logs**: Look at server logs for connection attempts

## 📊 Available Database Types

The server supports 25+ database systems:

- **Relational**: PostgreSQL, MySQL, Oracle, SQL Server
- **Cloud**: BigQuery, Snowflake, Redshift, Azure SQL
- **NoSQL**: MongoDB, DynamoDB, Cassandra
- **Analytics**: DuckDB, ClickHouse, Vertica
- **Enterprise**: SAP HANA, DB2, Teradata, Netezza
- **In-Memory**: Redis, MemSQL
- **Vector**: ChromaDB, Pinecone
- **Other**: SQLite, Access, Sybase

## 🛡️ Security Best Practices

### Production Deployment

1. **Use environment variables** for sensitive data:
   ```ini
   password = ${DATABASE_PASSWORD}
   ```

2. **Enable SSL/TLS**:
   ```bash
   python remote_mcp_server.py --host 0.0.0.0 --port 8080
   # Use nginx with SSL termination
   ```

3. **Restrict CORS origins**:
   ```bash
   python remote_mcp_server.py --cors-origins https://claude.ai
   ```

4. **Use read-only database users** when possible

5. **Monitor access logs** and database connections

## 📞 Getting Help

- **Check logs**: Server logs show detailed error information
- **Run tests**: `python test_remote_server.py` diagnoses issues
- **Debug mode**: Add `--debug` flag for verbose output
- **Documentation**: See `DEPLOYMENT_GUIDE.md` for advanced setup

## 🎉 Success!

Once everything is working, you'll see:

- ✅ Health check passes
- ✅ Tools are listed
- ✅ Claude Desktop connects successfully
- ✅ Database queries work through Claude

You can now ask Claude to help with database analysis, queries, and insights!