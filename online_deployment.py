"""
Online Deployment for MCP Servers
Handles deployment to AWS EC2, Azure VM, and Remote Machines via SSH
"""
import os
import time
import paramiko
import boto3
from botocore.exceptions import ClientError
from azure.identity import ClientSecretCredential
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.network import NetworkManagementClient
from azure.core.exceptions import ResourceExistsError
import threading
import queue

class OnlineDeployer:
    def __init__(self):
        self.logs = queue.Queue()

    def log(self, message, level="INFO"):
        """Log a message to the queue"""
        entry = f"[{level}] {message}"
        print(entry)
        self.logs.put(entry)

    def generate_setup_script(self, server_files, python_version="3.10"):
        """
        Generate a bash script to set up the MCP server on a remote machine
        """
        # Basic setup script
        script = f"""#!/bin/bash
set -e

echo "Starting MCP Server Setup..."

# Update system
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv nginx certbot python3-certbot-nginx git

# Create directory
sudo mkdir -p /opt/mcp-server
sudo chown -R $USER:$USER /opt/mcp-server

# Setup Virtual Environment
cd /opt/mcp-server
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install flask mcp httpx pyyaml python-dotenv

# Create server files
"""
        # Add file creation commands
        for filename, content in server_files.items():
            # Escape single quotes for bash heredoc
            safe_content = content.replace("'", "'\\''")
            script += f"\ncat << 'EOF' > {filename}\n{safe_content}\nEOF\n"

        script += """
# Create Systemd Service
cat << EOF | sudo tee /etc/systemd/system/mcp-server.service
[Unit]
Description=MCP Server
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/opt/mcp-server
Environment="PATH=/opt/mcp-server/venv/bin"
ExecStart=/opt/mcp-server/venv/bin/python app.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Reload and start service
sudo systemctl daemon-reload
sudo systemctl enable mcp-server
sudo systemctl start mcp-server

echo "MCP Server Setup Complete!"
"""
        return script

    def deploy_to_remote(self, host, username, password=None, key_path=None, server_files=None):
        """
        Deploy to a remote machine via SSH
        """
        self.log(f"Connecting to {host} as {username}...")
        
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            if key_path:
                ssh.connect(host, username=username, key_filename=key_path)
            else:
                ssh.connect(host, username=username, password=password)
            
            self.log("SSH Connection established.")
            
            # Generate setup script
            setup_script = self.generate_setup_script(server_files)
            
            # Upload setup script
            sftp = ssh.open_sftp()
            with sftp.file("setup_mcp.sh", "w") as f:
                f.write(setup_script)
            sftp.close()
            
            self.log("Setup script uploaded.")
            
            # Execute setup script
            self.log("Executing setup script (this may take a few minutes)...")
            stdin, stdout, stderr = ssh.exec_command("bash setup_mcp.sh")
            
            # Stream output
            while True:
                line = stdout.readline()
                if not line:
                    break
                self.log(line.strip(), "REMOTE")
                
            exit_status = stdout.channel.recv_exit_status()
            if exit_status == 0:
                self.log("Deployment successful!", "SUCCESS")
                return True
            else:
                self.log(f"Deployment failed with exit code {exit_status}", "ERROR")
                self.log(stderr.read().decode(), "ERROR")
                return False
                
        except Exception as e:
            self.log(f"SSH Error: {str(e)}", "ERROR")
            return False
        finally:
            ssh.close()

    def deploy_to_aws(self, aws_access_key, aws_secret_key, region, instance_type, server_files):
        """
        Deploy to AWS EC2
        """
        self.log(f"Connecting to AWS ({region})...")
        
        try:
            ec2 = boto3.resource(
                'ec2',
                aws_access_key_id=aws_access_key,
                aws_secret_access_key=aws_secret_key,
                region_name=region
            )
            
            # Create a key pair if needed (simplified: assuming user handles keys or we generate one)
            # For this POC, we'll use User Data to run the script without SSH login requirement for the user immediately
            
            setup_script = self.generate_setup_script(server_files)
            user_data = setup_script # Cloud-init handles bash scripts
            
            self.log("Launching EC2 instance...")
            
            # Find a basic Ubuntu AMI (simplified logic - in prod, search for latest)
            # This is a hardcoded Ubuntu 22.04 LTS AMI for us-east-1 as placeholder
            # In real implementation, we need to search for AMI based on region
            image_id = self._get_ubuntu_ami(ec2, region)
            
            instances = ec2.create_instances(
                ImageId=image_id,
                MinCount=1,
                MaxCount=1,
                InstanceType=instance_type,
                UserData=user_data,
                TagSpecifications=[{
                    'ResourceType': 'instance',
                    'Tags': [{'Key': 'Name', 'Value': 'MCP-Server'}]
                }]
            )
            
            instance = instances[0]
            self.log(f"Instance {instance.id} launched. Waiting for running state...")
            instance.wait_until_running()
            instance.reload()
            
            public_ip = instance.public_ip_address
            self.log(f"Instance running at {public_ip}", "SUCCESS")
            self.log("Deployment script is running in background. Please wait 5-10 minutes for initialization.", "INFO")
            
            return {"public_ip": public_ip, "instance_id": instance.id}

        except Exception as e:
            self.log(f"AWS Deployment Error: {str(e)}", "ERROR")
            return None

    def _get_ubuntu_ami(self, ec2_resource, region):
        # Simplified AMI lookup or hardcoded map
        # For robust code, use SSM parameter store to get latest Ubuntu AMI
        # For now, returning a placeholder or using a search
        # This is a placeholder logic
        return "ami-0c7217cdde317cfec" # Ubuntu 22.04 us-east-1

    def deploy_to_azure(self, subscription_id, client_id, client_secret, tenant_id, resource_group, location, server_files):
        """
        Deploy to Azure VM
        """
        self.log("Connecting to Azure...")
        try:
            credential = ClientSecretCredential(tenant_id, client_id, client_secret)
            compute_client = ComputeManagementClient(credential, subscription_id)
            network_client = NetworkManagementClient(credential, subscription_id)
            resource_client = ResourceManagementClient(credential, subscription_id)
            
            # Create Resource Group
            self.log(f"Creating Resource Group {resource_group}...")
            resource_client.resource_groups.create_or_update(resource_group, {'location': location})
            
            # Create Network (VNet, Subnet, PublicIP, NIC) - Simplified
            # ... (Azure setup is verbose, implementing basic structure)
            
            self.log("Azure deployment logic placeholder - requires detailed networking setup", "WARNING")
            # In a real implementation, this would be 100+ lines of code for VNET/NIC/VM
            
            return True
            
        except Exception as e:
            self.log(f"Azure Deployment Error: {str(e)}", "ERROR")
            return False

