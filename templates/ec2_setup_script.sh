#!/bin/bash
# Don't use set -e here - we want to continue even if some commands fail
# We'll handle errors explicitly

# MCP Server Setup Script for EC2
# This script sets up the MCP server on an Ubuntu EC2 instance

# Set domain variable (will be replaced by deployment script)
DOMAIN="{{DOMAIN}}"

# Log everything to a file for debugging
exec > >(tee -a /var/log/mcp-server-setup.log) 2>&1

echo "=========================================="
echo "Starting MCP server setup..."
echo "Timestamp: $(date)"
if [ -n "$DOMAIN" ]; then
    echo "Domain: $DOMAIN"
fi
echo "=========================================="

# Wait for system to be fully ready (network, services, etc.)
echo "Waiting for system services to be ready..."
sleep 10

# Update system
echo "Updating system packages..."
sudo apt-get update -y || { echo "ERROR: apt-get update failed"; exit 1; }
sudo apt-get upgrade -y || { echo "WARNING: apt-get upgrade failed, continuing..."; }

# Install required packages
echo "Installing required packages..."
sudo apt-get install -y python3 python3-pip python3-venv nginx certbot python3-certbot-nginx git build-essential default-libmysqlclient-dev pkg-config || { echo "ERROR: Package installation failed"; exit 1; }
echo "Packages installed successfully"

# Create directory for MCP server
echo "Creating MCP server directory..."
sudo mkdir -p /opt/mcp-server
sudo chown ubuntu:ubuntu /opt/mcp-server
cd /opt/mcp-server
echo "Current directory: $(pwd)"
echo "Directory contents before setup:"
ls -la || echo "Directory is empty (expected)"

# Create virtual environment
echo "Creating Python virtual environment..."
python3 -m venv venv || { echo "ERROR: Failed to create virtual environment"; exit 1; }
source venv/bin/activate || { echo "ERROR: Failed to activate virtual environment"; exit 1; }

# Upgrade pip first
echo "Upgrading pip..."
pip install --upgrade pip || { echo "WARNING: pip upgrade failed, continuing..."; }

# Create server files FIRST so requirements.txt is available
echo "Creating server files..."
python3 << 'PYTHON_EOF'
import base64
import os
import tarfile
import io
import json

# File data as base64-encoded JSON (avoids escaping issues)
file_data_json_b64 = "{{FILE_DATA_JSON_B64}}"

# Decode the JSON data
file_data_json = base64.b64decode(file_data_json_b64).decode('utf-8')
file_data = json.loads(file_data_json)

# Create files
for filename, file_info in file_data.items():
    try:
        print(f"Creating {filename}...")
        file_type = file_info['type']
        encoded_content = file_info['content']
        
        if file_type == 'tar.gz':
            # Decode and extract tarball
            tar_data = base64.b64decode(encoded_content)
            tar_file = io.BytesIO(tar_data)
            with tarfile.open(fileobj=tar_file, mode='r:gz') as tar:
                tar.extractall('.')
            print(f"Successfully extracted {filename}")
        else:
            # Decode and write text file
            content = base64.b64decode(encoded_content).decode('utf-8')
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Successfully created {filename} ({len(content)} bytes)")
            
            # Make Python scripts executable
            if filename.endswith('.py'):
                os.chmod(filename, 0o755)
    except Exception as e:
        print(f"ERROR creating {filename}: {e}")
        import traceback
        traceback.print_exc()
        import sys
        sys.exit(1)

print("")
print("=== Verifying created files ===")
import subprocess
result = subprocess.run(['ls', '-lah'], capture_output=True, text=True)
print(result.stdout)
file_count = len([f for f in os.listdir('.') if os.path.isfile(f)])
dir_count = len([d for d in os.listdir('.') if os.path.isdir(d)])
print(f"Files: {file_count}, Directories: {dir_count}")
print("File creation complete!")
PYTHON_EOF

if [ $? -ne 0 ]; then
    echo "ERROR: File creation failed!"
    exit 1
fi

# Make Python scripts executable
chmod +x *.py 2>/dev/null || true

# Now install dependencies from requirements.txt if it exists
echo ""
echo "=========================================="
echo "Installing Python dependencies..."
echo "=========================================="

if [ -f "requirements.txt" ]; then
    echo "Installing dependencies from requirements.txt..."
    echo "Requirements file size: $(wc -l < requirements.txt) lines"
    echo "This may take several minutes..."
    # Install with retries for network issues
    pip install -r requirements.txt 2>&1 | tee /tmp/pip-install.log || {
        echo "WARNING: Some requirements.txt dependencies failed to install, trying again..."
        echo "First attempt errors saved to /tmp/pip-install.log"
        pip install -r requirements.txt --no-cache-dir 2>&1 | tee -a /tmp/pip-install.log || {
            echo "ERROR: Failed to install requirements.txt dependencies after retry"
            echo "Attempting to install critical packages individually..."
            # Install critical packages that are definitely needed
            pip install mcp uvicorn starlette fastapi click httpx requests pyyaml python-dotenv pandas pypika sqlalchemy pymysql psycopg2-binary pymongo boto3 || {
                echo "ERROR: Failed to install critical packages"
                exit 1
            }
        }
    }
    echo "Requirements.txt installation completed"
else
    echo "WARNING: requirements.txt not found, installing basic dependencies..."
    pip install mcp httpx requests pyyaml python-dotenv pandas pypika sqlalchemy || { echo "ERROR: Failed to install basic dependencies"; exit 1; }
    
    # Install database-specific dependencies if needed
    if [ "$SERVER_TYPE" = "database" ]; then
        echo "Installing database-specific dependencies..."
        pip install pymysql psycopg2-binary cx-Oracle pyodbc pymongo snowflake-connector-python google-cloud-bigquery boto3 || { echo "WARNING: Some database dependencies failed to install, continuing..."; }
    fi
fi

# Verify critical packages are installed (simplified to save space)
echo ""
echo "Verifying critical packages..."
python3 -c "import mcp,httpx,requests,pandas,pypika,sqlalchemy,numpy,yaml,dotenv,pymysql,psycopg2,pymongo,boto3" && echo "✓ Critical packages OK" || {
    echo "ERROR: Missing packages. Installing..."
    pip install mcp uvicorn starlette fastapi click httpx requests pandas pypika sqlalchemy numpy pyyaml python-dotenv pymysql psycopg2-binary pymongo boto3 || exit 1
}

echo "Python dependencies installation completed"

# Configure Nginx for all HTTP-based MCP servers
# All online deployments now use HTTP transport with OAuth (database, api, swagger)
echo "Configuring Nginx for {{SERVER_TYPE}} MCP server with HTTP/OAuth..."

if [ -n "$DOMAIN" ]; then
    echo "Configuring Nginx for domain: $DOMAIN"
    
    # Create Nginx configuration with domain
    sudo tee /etc/nginx/sites-available/mcp-server > /dev/null << NGINX_EOF
server {
    listen 80;
    listen [::]:80;
    server_name $DOMAIN _;
    
    # Increase timeouts for long-running requests
    proxy_connect_timeout 300s;
    proxy_send_timeout 300s;
    proxy_read_timeout 300s;
    send_timeout 300s;
    
    # Increase body size for large requests
    client_max_body_size 100M;
    
    location / {
        proxy_pass http://127.0.0.1:{{SERVER_PORT}};
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_cache_bypass \$http_upgrade;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # WebSocket support
        proxy_set_header X-Forwarded-Host \$host;
        proxy_set_header X-Forwarded-Port \$server_port;
    }
}
NGINX_EOF
else
    echo "Configuring Nginx for IP access (no domain)"
    
    # Create Nginx configuration for IP access
    sudo tee /etc/nginx/sites-available/mcp-server > /dev/null << NGINX_EOF
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;
    
    # Increase timeouts for long-running requests
    proxy_connect_timeout 300s;
    proxy_send_timeout 300s;
    proxy_read_timeout 300s;
    send_timeout 300s;
    
    # Increase body size for large requests
    client_max_body_size 100M;
    
    location / {
        proxy_pass http://127.0.0.1:{{SERVER_PORT}};
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_cache_bypass \$http_upgrade;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # WebSocket support
        proxy_set_header X-Forwarded-Host \$host;
        proxy_set_header X-Forwarded-Port \$server_port;
    }
}
NGINX_EOF
fi

# Enable site
sudo ln -sf /etc/nginx/sites-available/mcp-server /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test Nginx configuration
echo "Testing Nginx configuration..."
sudo nginx -t || { echo "ERROR: Nginx configuration test failed"; exit 1; }

# Enable and start Nginx service
echo "Enabling and starting Nginx..."
sudo systemctl enable nginx || echo "Warning: Could not enable Nginx service"
sudo systemctl restart nginx || { echo "ERROR: Could not start Nginx"; exit 1; }

# Verify Nginx is running
if sudo systemctl is-active --quiet nginx; then
    echo "✓ Nginx is running on port 80"
else
    echo "ERROR: Nginx is not running"
    sudo systemctl status nginx || true
    exit 1
fi

# Setup SSL with Let's Encrypt (only if domain is provided)
if [ -n "$DOMAIN" ]; then
    echo "Setting up SSL certificate with Let's Encrypt for $DOMAIN..."
    
    # Get server's public IP (try multiple methods)
    server_ip=""
    
    # Try AWS metadata service
    server_ip=$(curl -s --connect-timeout 2 http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo "")
    
    # If AWS metadata not available, try other cloud providers or fallback
    if [ -z "$server_ip" ]; then
    # Try hostname -I as fallback
    server_ip=$(hostname -I | awk '{print $1}')
    fi
    
    echo "Server IP: $server_ip"
    echo "Waiting 60 seconds for DNS to propagate..."
    sleep 60
    
    # Check if domain resolves to this server's IP
    echo "Checking DNS resolution..."
    resolved_ip=$(dig +short $DOMAIN @8.8.8.8 2>/dev/null | tail -1 | grep -E '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$' || echo "")
    
    if [ -n "$resolved_ip" ]; then
    echo "Domain $DOMAIN resolves to: $resolved_ip"
    if [ "$resolved_ip" = "$server_ip" ]; then
        echo "✓ DNS is correctly pointing to this server"
    else
        echo "⚠ DNS points to $resolved_ip, but this server is $server_ip"
        echo "Waiting additional 60 seconds for DNS update..."
        sleep 60
    fi
    else
    echo "⚠ Could not resolve domain. Continuing anyway..."
    fi
    
    # Try certbot with retries (non-interactive mode)
    max_retries=3
    retry_count=0
    ssl_success=false
    
    while [ $retry_count -lt $max_retries ]; do
    echo ""
    echo "Attempt $((retry_count + 1)) of $max_retries to obtain SSL certificate..."
        
    # Run certbot in non-interactive mode
    # Use --redirect to automatically set up HTTP to HTTPS redirect
    if sudo certbot --nginx -d $DOMAIN \
        --non-interactive \
        --agree-tos \
        --email admin@$DOMAIN \
        --redirect \
        --no-eff-email \
        --expand \
        2>&1 | tee /tmp/certbot.log; then
        echo "✓ SSL certificate obtained successfully!"
        ssl_success=true
        
        # Verify certbot updated the Nginx config
        if grep -q "listen 443" /etc/nginx/sites-enabled/mcp-server 2>/dev/null; then
            echo "✓ Nginx configuration updated with SSL"
        else
            echo "⚠ Certbot did not update Nginx config. Manually adding SSL configuration..."
            # Backup current config
            sudo cp /etc/nginx/sites-available/mcp-server /etc/nginx/sites-available/mcp-server.backup
            
            # Add SSL configuration manually with complete security settings
            sudo tee /etc/nginx/sites-available/mcp-server > /dev/null << NGINX_SSL_EOF
# HTTP server - redirect to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name $DOMAIN _;
    return 301 https://\$host\$request_uri;
}

# HTTPS server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name $DOMAIN _;
    
    # SSL certificates (installed by certbot)
    ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;
    
    # Include Let's Encrypt SSL options (these are created by certbot)
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;
    
    # Additional SSL security settings (ssl_protocols and ssl_ciphers are in options-ssl-nginx.conf)
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    ssl_session_tickets off;
    
    # OCSP stapling for better security and performance
    ssl_stapling on;
    ssl_stapling_verify on;
    ssl_trusted_certificate /etc/letsencrypt/live/$DOMAIN/chain.pem;
    resolver 8.8.8.8 8.8.4.4 valid=300s;
    resolver_timeout 5s;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    
    # Increase timeouts for long-running requests
    proxy_connect_timeout 300s;
    proxy_send_timeout 300s;
    proxy_read_timeout 300s;
    send_timeout 300s;
    
    # Increase body size for large requests
    client_max_body_size 100M;
    
    location / {
    proxy_pass http://127.0.0.1:{{SERVER_PORT}};
    proxy_http_version 1.1;
    proxy_set_header Upgrade \$http_upgrade;
    proxy_set_header Connection 'upgrade';
    proxy_set_header Host \$host;
    proxy_cache_bypass \$http_upgrade;
    proxy_set_header X-Real-IP \$remote_addr;
    proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto \$scheme;
    
    # WebSocket support
    proxy_set_header X-Forwarded-Host \$host;
    proxy_set_header X-Forwarded-Port \$server_port;
    }
}
NGINX_SSL_EOF
            
            # Test and reload Nginx
            sudo nginx -t && sudo systemctl reload nginx && echo "✓ SSL configuration added manually" || {
                echo "ERROR: Failed to add SSL config. Restoring backup..."
                sudo cp /etc/nginx/sites-available/mcp-server.backup /etc/nginx/sites-available/mcp-server
            }
        fi
        break
    else
        certbot_exit_code=${PIPESTATUS[0]}
        echo "Certbot exited with code: $certbot_exit_code"
        retry_count=$((retry_count + 1))
        
        if [ $retry_count -lt $max_retries ]; then
            echo "SSL certificate setup failed. Waiting 90 seconds before retry..."
            sleep 90
        else
            echo ""
            echo "WARNING: SSL certificate setup failed after $max_retries attempts."
            echo "Common reasons:"
            echo "  1. DNS is not pointing to this server yet (check with: dig $DOMAIN)"
            echo "  2. Port 80 is not accessible from the internet (check security group)"
            echo "  3. Domain already has a certificate on another server"
            echo "  4. Let's Encrypt rate limits (too many requests)"
            echo ""
            echo "You can manually run:"
            echo "  sudo certbot --nginx -d $DOMAIN"
            echo ""
            echo "Certbot logs: /tmp/certbot.log"
            echo "Let's Encrypt logs: /var/log/letsencrypt/letsencrypt.log"
        fi
    fi
    done
    
    # Verify Nginx configuration after certbot
    echo ""
    echo "Verifying Nginx configuration..."
    sudo nginx -t || {
    echo "ERROR: Nginx configuration is invalid after certbot!"
    echo "Checking current Nginx config..."
    sudo cat /etc/nginx/sites-enabled/mcp-server || true
    }
    
    # Check if Nginx is listening on port 443
    if sudo ss -tlnp | grep -q ":443"; then
    echo "✓ Nginx is listening on port 443"
    else
    echo "⚠ Nginx is not listening on port 443"
    echo "Checking if SSL certificates exist..."
    if [ -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ]; then
        echo "✓ SSL certificates found at /etc/letsencrypt/live/$DOMAIN/"
        echo "Attempting to fix Nginx configuration..."
        
        # Check if config has SSL block
        if ! grep -q "listen 443" /etc/nginx/sites-enabled/mcp-server; then
            echo "Adding SSL configuration to Nginx..."
            # Create SSL-enabled config with complete security settings
            sudo tee /etc/nginx/sites-available/mcp-server > /dev/null << NGINX_FIX_EOF
# HTTP server - redirect to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name $DOMAIN _;
    return 301 https://\$host\$request_uri;
}

# HTTPS server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name $DOMAIN _;
    
    # SSL certificates
    ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;
    
    # Include Let's Encrypt SSL options (these are created by certbot)
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;
    
    # Additional SSL security settings (ssl_protocols and ssl_ciphers are in options-ssl-nginx.conf)
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    ssl_session_tickets off;
    
    # OCSP stapling
    ssl_stapling on;
    ssl_stapling_verify on;
    ssl_trusted_certificate /etc/letsencrypt/live/$DOMAIN/chain.pem;
    resolver 8.8.8.8 8.8.4.4 valid=300s;
    resolver_timeout 5s;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    
    # Increase timeouts
    proxy_connect_timeout 300s;
    proxy_send_timeout 300s;
    proxy_read_timeout 300s;
    send_timeout 300s;
    
    client_max_body_size 100M;
    
    location / {
    proxy_pass http://127.0.0.1:{{SERVER_PORT}};
    proxy_http_version 1.1;
    proxy_set_header Upgrade \$http_upgrade;
    proxy_set_header Connection 'upgrade';
    proxy_set_header Host \$host;
    proxy_cache_bypass \$http_upgrade;
    proxy_set_header X-Real-IP \$remote_addr;
    proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto \$scheme;
    proxy_set_header X-Forwarded-Host \$host;
    proxy_set_header X-Forwarded-Port \$server_port;
    }
}
NGINX_FIX_EOF
            
            sudo nginx -t && sudo systemctl reload nginx && echo "✓ SSL configuration fixed!" || {
                echo "ERROR: Failed to fix SSL config"
                sudo systemctl status nginx || true
            }
        fi
    else
        echo "ERROR: SSL certificates not found!"
    fi
    fi
    
    # Ensure Nginx is running and reloaded
    sudo systemctl reload nginx || sudo systemctl restart nginx || {
    echo "ERROR: Could not reload/restart Nginx"
    sudo systemctl status nginx || true
    }
    
    # Verify Nginx is running
    if sudo systemctl is-active --quiet nginx; then
    echo "✓ Nginx is running"
    # Verify ports
    if sudo ss -tlnp | grep -q ":443"; then
        echo "✓ Nginx is listening on port 443 (HTTPS)"
    fi
    if sudo ss -tlnp | grep -q ":80"; then
        echo "✓ Nginx is listening on port 80 (HTTP)"
    fi
    else
    echo "ERROR: Nginx is not running after SSL setup"
    sudo systemctl status nginx || true
    fi
    
    if [ "$ssl_success" = true ]; then
    echo ""
    echo "=========================================="
    echo "✓ Nginx and SSL configured successfully!"
    echo "=========================================="
    echo "Server is now accessible at:"
    echo "  - https://$DOMAIN (HTTPS)"
    echo "  - http://$DOMAIN (redirects to HTTPS)"
    else
        echo ""
        echo "Nginx is configured, but SSL certificate needs to be obtained manually"
        echo "Run: sudo certbot --nginx -d $DOMAIN"
    fi
fi

# Create systemd service
# Determine SERVER_BASE_URL for OAuth redirects
if [ -n "$DOMAIN" ]; then
    SERVER_BASE_URL="https://$DOMAIN"
else
    # Get public IP for base URL (try multiple methods)
    PUBLIC_IP=""
    
    # Try AWS metadata service
    PUBLIC_IP=$(curl -s --connect-timeout 2 http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo "")
    
    # If metadata service not available, try hostname -I
    if [ -z "$PUBLIC_IP" ]; then
        PUBLIC_IP=$(hostname -I | awk '{print $1}')
    fi
    
    if [ -n "$PUBLIC_IP" ]; then
        SERVER_BASE_URL="http://$PUBLIC_IP"
    else
        SERVER_BASE_URL="http://localhost:30210"
    fi
fi

# Create systemd service - all online servers use HTTP and run as persistent services
cat << EOF | sudo tee /etc/systemd/system/mcp-server.service
[Unit]
Description=MCP Server ({{SERVER_TYPE}} with HTTP/OAuth)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/mcp-server
Environment="PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/opt/mcp-server/venv/bin"
Environment="SERVER_BASE_URL=$SERVER_BASE_URL"
Environment="MCP_TRANSPORT=http"
Environment="MCP_PORT=30210"
Environment="MCP_HOST=0.0.0.0"
ExecStart={{STARTUP_COMMAND}}
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and enable service (but don't start yet)
sudo systemctl daemon-reload
sudo systemctl enable mcp-server

# Wait for all initialization to complete before starting the server
echo "Waiting for system initialization to complete..."
# Wait for network to be fully up
while ! ping -c 1 8.8.8.8 &> /dev/null; do
    echo "Waiting for network connectivity..."
    sleep 2
done
echo "Network connectivity confirmed"

# Wait a bit more for any background processes
sleep 3

# Verify server files are present
echo ""
echo "=========================================="
echo "=== Verifying MCP Server Files ==="
echo "=========================================="
cd /opt/mcp-server
echo "Files in /opt/mcp-server:"
ls -lah
echo ""

# Check for YAML files if this is an API/Swagger server
YAML_COUNT=$(find . -maxdepth 1 -name "*.yaml" -type f | wc -l)
if [ $YAML_COUNT -gt 0 ]; then
    echo "Found $YAML_COUNT YAML tool file(s):"
    ls -lh *.yaml
    echo ""
fi

# Check for mcp_server_loader.py
if [ -f "mcp_server_loader.py" ]; then
    echo "✓ mcp_server_loader.py found"
else
    echo "✗ mcp_server_loader.py NOT found"
fi

# Quick import test based on server type
echo ""
if [ "{{SERVER_TYPE}}" = "database" ]; then
    echo "Testing database-specific imports..."
    python3 -c "import sys;sys.path.insert(0,'.');from scikiq_dbutils.mcp_server.wrappers.connection_manager import ConnectionManager;from scikiq_dbutils.handlers.DBConnection import clsDBConnection" && echo "✓ Database imports OK" || {
        echo "WARNING: Some database imports failed. Server may have issues."
    }
else
    echo "Testing API/Swagger server imports..."
    python3 -c "import mcp,httpx,yaml,starlette,uvicorn" && echo "✓ MCP and HTTP imports OK" || {
        echo "WARNING: Some imports failed. Server may have issues."
    }
fi

# Now start the MCP server service
echo ""
echo "=========================================="
echo "=== Starting MCP Server Service ==="
echo "=========================================="
echo "Startup command configured in systemd:"
grep "ExecStart=" /etc/systemd/system/mcp-server.service
echo ""
sudo systemctl start mcp-server

# Wait a moment for service to start
sleep 5

# Check service status - all online servers run as HTTP services
if sudo systemctl is-active --quiet mcp-server; then
    echo "✓ MCP {{SERVER_TYPE}} Server started successfully!"
    # Get server IP for display
    DISPLAY_IP=$(curl -s --connect-timeout 2 http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || hostname -I | awk '{print $1}' || echo 'server-ip')
    
    if [ -n "$DOMAIN" ]; then
        echo "Server is available at:"
        echo "  - https://$DOMAIN (HTTPS - after SSL certificate is obtained)"
        echo "  - http://$DOMAIN (HTTP - redirects to HTTPS)"
        echo "  - http://${DISPLAY_IP}:30210 (Direct access)"
        echo ""
        if [ "{{SERVER_TYPE}}" = "database" ]; then
            echo "OAuth Admin Interface: https://$DOMAIN/admin/login"
        else
            echo "OAuth Metadata: https://$DOMAIN/.well-known/oauth-authorization-server"
            echo "Health Check: https://$DOMAIN/health"
        fi
    else
        echo "Server is accessible at:"
        echo "  - http://${DISPLAY_IP}:80 (via Nginx)"
        echo "  - http://${DISPLAY_IP}:30210 (Direct access)"
        echo ""
        if [ "{{SERVER_TYPE}}" = "database" ]; then
            echo "OAuth Admin Interface: http://${DISPLAY_IP}/admin/login"
        else
            echo "OAuth Metadata: http://${DISPLAY_IP}/.well-known/oauth-authorization-server"
            echo "Health Check: http://${DISPLAY_IP}/health"
        fi
    fi
else
    echo "Warning: MCP server service may not have started correctly"
    echo "Check status with: sudo systemctl status mcp-server"
    echo "Checking service logs..."
    sudo journalctl -u mcp-server -n 20 --no-pager || true
fi

echo "=========================================="
echo "Setup complete!"
echo "Timestamp: $(date)"
echo "=========================================="
echo ""
echo "Setup log saved to: /var/log/mcp-server-setup.log"
echo "You can check the log with: sudo cat /var/log/mcp-server-setup.log"

