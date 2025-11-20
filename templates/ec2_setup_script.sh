#!/bin/bash
set -e

# MCP Server Setup Script for EC2
# This script sets up the MCP server on an Ubuntu EC2 instance

echo "Starting MCP server setup..."

# Update system
sudo apt-get update -y
sudo apt-get upgrade -y

# Install required packages
sudo apt-get install -y python3 python3-pip python3-venv nginx certbot python3-certbot-nginx git

# Create directory for MCP server
sudo mkdir -p /opt/mcp-server
sudo chown ubuntu:ubuntu /opt/mcp-server
cd /opt/mcp-server

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install basic dependencies
pip install --upgrade pip
pip install mcp httpx pyyaml python-dotenv

# Install database-specific dependencies (if needed)
if [ "$SERVER_TYPE" = "database" ]; then
    pip install pymysql psycopg2-binary cx_Oracle pyodbc pymongo snowflake-connector-python google-cloud-bigquery boto3
fi

# Create server files using Python for better encoding handling
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

# Configure Nginx for HTTPS (if domain is provided)
if [ -n "$DOMAIN" ]; then
    echo "Configuring Nginx for domain: $DOMAIN"
    
    # Create Nginx configuration
    sudo tee /etc/nginx/sites-available/mcp-server > /dev/null << NGINX_EOF
server {
    listen 80;
    server_name $DOMAIN;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_cache_bypass \$http_upgrade;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
NGINX_EOF

    # Enable site
    sudo ln -sf /etc/nginx/sites-available/mcp-server /etc/nginx/sites-enabled/
    sudo rm -f /etc/nginx/sites-enabled/default
    sudo nginx -t
    
    # Setup SSL with Let's Encrypt
    sudo certbot --nginx -d $DOMAIN --non-interactive --agree-tos --email admin@$DOMAIN --redirect
    
    echo "Nginx and SSL configured successfully"
else
    echo "No domain provided. Skipping Nginx/SSL setup."
    echo "Server will be accessible directly on port 8000"
fi

# Create systemd service
cat << EOF | sudo tee /etc/systemd/system/mcp-server.service
[Unit]
Description=MCP Server
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/mcp-server
Environment="PATH=/opt/mcp-server/venv/bin"
ExecStart={{STARTUP_COMMAND}}
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and start service
sudo systemctl daemon-reload
sudo systemctl enable mcp-server
sudo systemctl start mcp-server

# Wait a moment for service to start
sleep 2

# Check service status
if sudo systemctl is-active --quiet mcp-server; then
    echo "MCP server started successfully!"
    if [ -n "$DOMAIN" ]; then
        echo "Server will be available at https://$DOMAIN after DNS propagation (5-10 minutes)"
    else
        echo "Server is running on port 8000"
    fi
else
    echo "Warning: MCP server service may not have started correctly"
    echo "Check status with: sudo systemctl status mcp-server"
fi

echo "Setup complete!"

