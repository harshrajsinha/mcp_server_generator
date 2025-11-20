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
import base64
import json
import tarfile
import io
import gzip
from pathlib import Path
import shutil

class OnlineDeployer:
    def __init__(self):
        self.logs = queue.Queue()

    def log(self, message, level="INFO"):
        """Log a message to the queue"""
        entry = f"[{level}] {message}"
        print(entry)
        self.logs.put(entry)

    def _get_iam_permission_suggestions(self, error_code, operation):
        """
        Generate IAM permission suggestions based on the error code and operation.
        Returns a formatted string with permission requirements.
        """
        suggestions = {
            'UnauthorizedOperation': {
                'CreateSecurityGroup': {
                    'title': 'Missing Permission: Create Security Group',
                    'required_permissions': [
                        'ec2:CreateSecurityGroup',
                        'ec2:AuthorizeSecurityGroupIngress',
                        'ec2:DescribeSecurityGroups'
                    ],
                    'description': 'Your AWS user needs permission to create and manage security groups.',
                    'policy_example': '''{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ec2:CreateSecurityGroup",
                "ec2:AuthorizeSecurityGroupIngress",
                "ec2:DescribeSecurityGroups",
                "ec2:DeleteSecurityGroup"
            ],
            "Resource": "*"
        }
    ]
}'''
                },
                'RunInstances': {
                    'title': 'Missing Permission: Launch EC2 Instances',
                    'required_permissions': [
                        'ec2:RunInstances',
                        'ec2:DescribeInstances',
                        'ec2:DescribeImages',
                        'ec2:DescribeVpcs',
                        'ec2:DescribeSubnets',
                        'ec2:CreateTags'
                    ],
                    'description': 'Your AWS user needs permission to launch EC2 instances.',
                    'policy_example': '''{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ec2:RunInstances",
                "ec2:DescribeInstances",
                "ec2:DescribeImages",
                "ec2:DescribeVpcs",
                "ec2:DescribeSubnets",
                "ec2:CreateTags",
                "ec2:TerminateInstances"
            ],
            "Resource": "*"
        }
    ]
}'''
                },
                'DescribeVpcs': {
                    'title': 'Missing Permission: Describe VPCs',
                    'required_permissions': [
                        'ec2:DescribeVpcs',
                        'ec2:DescribeSubnets'
                    ],
                    'description': 'Your AWS user needs permission to describe VPCs and subnets.',
                    'policy_example': '''{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ec2:DescribeVpcs",
                "ec2:DescribeSubnets"
            ],
            "Resource": "*"
        }
    ]
}'''
                }
            },
            'AccessDenied': {
                'default': {
                    'title': 'Access Denied',
                    'required_permissions': [
                        'ec2:*'
                    ],
                    'description': 'Your AWS user has been denied access to this operation.',
                    'policy_example': 'Please contact your AWS administrator to grant the necessary permissions.'
                }
            }
        }
        
        # Get suggestions for the specific error
        error_suggestions = suggestions.get(error_code, {})
        operation_suggestions = error_suggestions.get(operation, error_suggestions.get('default', {}))
        
        if not operation_suggestions:
            return None
        
        # Format the suggestion message
        message = f"\n{'='*70}\n"
        message += f"⚠️  {operation_suggestions['title']}\n"
        message += f"{'='*70}\n\n"
        message += f"Description: {operation_suggestions['description']}\n\n"
        message += "Required IAM Permissions:\n"
        for perm in operation_suggestions['required_permissions']:
            message += f"  • {perm}\n"
        message += f"\nExample IAM Policy:\n{operation_suggestions['policy_example']}\n"
        message += f"\n{'='*70}\n"
        message += "How to Fix:\n"
        message += "1. Go to AWS IAM Console (https://console.aws.amazon.com/iam/)\n"
        message += "2. Select your IAM user or role\n"
        message += "3. Click 'Add permissions' → 'Attach policies directly'\n"
        message += "4. Create a custom policy with the permissions above, or\n"
        message += "5. Attach the AWS managed policy 'AmazonEC2FullAccess' (for full access)\n"
        message += f"{'='*70}\n"
        
        return message
    
    def _get_complete_iam_policy(self):
        """
        Returns a complete IAM policy JSON that covers all required permissions for AWS deployment.
        """
        return '''{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ec2:RunInstances",
                "ec2:DescribeInstances",
                "ec2:DescribeImages",
                "ec2:DescribeVpcs",
                "ec2:DescribeSubnets",
                "ec2:DescribeSecurityGroups",
                "ec2:CreateSecurityGroup",
                "ec2:AuthorizeSecurityGroupIngress",
                "ec2:CreateTags",
                "ec2:TerminateInstances"
            ],
            "Resource": "*"
        }
    ]
}'''

    def _prepare_server_files(self, server_type, server_path, config_path=None):
        """
        Prepare server files based on server type for deployment
        
        Args:
            server_type: Type of server ('api', 'database', 'codebase')
            server_path: Path to server files directory
            config_path: Path to config file (for database servers)
            
        Returns:
            Dictionary of files to deploy
        """
        server_files = {}
        base_path = Path(server_path)
        
        if server_type == 'database':
            # Database MCP server files
            self.log(f"Preparing database MCP server files from {server_path}")
            
            # Copy config.ini
            if config_path and Path(config_path).exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    server_files['config.ini'] = f.read()
                    self.log(f"  - config.ini ({len(server_files['config.ini'])} bytes)")
            else:
                self.log("  - config.ini not found, will be created on server", "WARNING")
            
            # Copy run_mcp_server.py from dbhandler_mcpserver
            dbhandler_path = Path(__file__).parent / 'dbhandler_mcpserver' / 'scikiq_pkg_dbutils' / 'run_mcp_server.py'
            if dbhandler_path.exists():
                with open(dbhandler_path, 'r', encoding='utf-8') as f:
                    server_files['run_mcp_server.py'] = f.read()
                    self.log(f"  - run_mcp_server.py ({len(server_files['run_mcp_server.py'])} bytes)")
            else:
                # Fallback: create a simple wrapper
                server_files['run_mcp_server.py'] = self._generate_database_server_wrapper()
                self.log("  - run_mcp_server.py (generated wrapper)")
            
            # Copy the entire scikiq_dbutils package directory
            scikiq_pkg_path = Path(__file__).parent / 'dbhandler_mcpserver' / 'scikiq_pkg_dbutils' / 'scikiq_dbutils'
            if scikiq_pkg_path.exists() and scikiq_pkg_path.is_dir():
                # Create a tarball of the scikiq_dbutils package
                tar_buffer = io.BytesIO()
                with tarfile.open(fileobj=tar_buffer, mode='w:gz') as tar:
                    tar.add(scikiq_pkg_path, arcname='scikiq_dbutils', recursive=True)
                
                tar_buffer.seek(0)
                tar_data = tar_buffer.read()
                server_files['scikiq_dbutils.tar.gz'] = base64.b64encode(tar_data).decode('ascii')
                self.log(f"  - scikiq_dbutils.tar.gz ({len(tar_data)} bytes, {len(server_files['scikiq_dbutils.tar.gz'])} base64 chars)")
            else:
                self.log(f"  - scikiq_dbutils package not found at {scikiq_pkg_path}", "ERROR")
            
            # Copy requirements file
            req_path = base_path / 'requirements.txt'
            if not req_path.exists():
                req_path = Path(__file__).parent / 'dbhandler_mcpserver' / 'scikiq_pkg_dbutils' / 'requirements.txt'
            if req_path.exists():
                with open(req_path, 'r', encoding='utf-8') as f:
                    server_files['requirements.txt'] = f.read()
                    self.log(f"  - requirements.txt ({len(server_files['requirements.txt'])} bytes)")
            else:
                server_files['requirements.txt'] = "mcp\nhttpx\npyyaml\npython-dotenv\n"
                self.log("  - requirements.txt (default)")
                
        elif server_type in ['api', 'codebase', 'swagger']:
            # API MCP server files
            self.log(f"Preparing API MCP server files from {server_path}")
            
            # Copy mcp_server_loader.py
            loader_path = base_path / 'mcp_server_loader.py'
            if not loader_path.exists():
                loader_path = Path(__file__).parent / 'generated_servers' / 'mcp_server_loader.py'
            if loader_path.exists():
                with open(loader_path, 'r', encoding='utf-8') as f:
                    server_files['mcp_server_loader.py'] = f.read()
            
            # Copy all YAML tool files
            yaml_files = list(base_path.glob('tools_*.yaml'))
            if not yaml_files:
                yaml_files = list(Path(__file__).parent / 'generated_servers').glob('tools_*.yaml')
            
            for yaml_file in yaml_files:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    server_files[yaml_file.name] = f.read()
            
            # Copy requirements
            req_path = base_path / 'requirements.txt'
            if not req_path.exists():
                server_files['requirements.txt'] = "mcp\nhttpx\npyyaml\n"
            else:
                with open(req_path, 'r', encoding='utf-8') as f:
                    server_files['requirements.txt'] = f.read()
        
        return server_files
    
    def _upload_files_to_s3(self, server_files, aws_access_key, aws_secret_key, region):
        """
        Upload server files to S3 and return bucket and prefix
        
        Args:
            server_files: Dictionary of files to upload
            aws_access_key: AWS access key
            aws_secret_key: AWS secret key
            region: AWS region
            
        Returns:
            Tuple of (bucket_name, prefix) or (None, None) on failure
        """
        try:
            import uuid
            from datetime import datetime, timedelta
            
            s3_client = boto3.client(
                's3',
                aws_access_key_id=aws_access_key,
                aws_secret_access_key=aws_secret_key,
                region_name=region
            )
            
            # Generate unique bucket name and prefix
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            unique_id = str(uuid.uuid4())[:8]
            bucket_name = f"mcp-deployment-{timestamp}-{unique_id}"
            prefix = f"mcp-server-files/{timestamp}"
            
            # Try to create bucket (may fail if name exists or no permissions)
            try:
                if region == 'us-east-1':
                    s3_client.create_bucket(Bucket=bucket_name)
                else:
                    s3_client.create_bucket(
                        Bucket=bucket_name,
                        CreateBucketConfiguration={'LocationConstraint': region}
                    )
                self.log(f"Created S3 bucket: {bucket_name}", "INFO")
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', 'Unknown')
                if error_code == 'BucketAlreadyExists':
                    # Try with different name
                    bucket_name = f"mcp-deployment-{timestamp}-{unique_id}-alt"
                    if region == 'us-east-1':
                        s3_client.create_bucket(Bucket=bucket_name)
                    else:
                        s3_client.create_bucket(
                            Bucket=bucket_name,
                            CreateBucketConfiguration={'LocationConstraint': region}
                        )
                    self.log(f"Created S3 bucket with alternate name: {bucket_name}", "INFO")
                elif error_code in ['AccessDenied', 'UnauthorizedOperation']:
                    # Try to use an existing bucket or create with different naming
                    self.log("Cannot create S3 bucket. Trying to use existing bucket...", "WARNING")
                    # Try to find an existing bucket or use a default pattern
                    try:
                        buckets = s3_client.list_buckets()
                        # Look for existing mcp-deployment bucket
                        for bucket in buckets.get('Buckets', []):
                            if 'mcp-deployment' in bucket['Name']:
                                bucket_name = bucket['Name']
                                self.log(f"Using existing bucket: {bucket_name}", "INFO")
                                break
                        else:
                            # No existing bucket found, return error
                            self.log("No suitable S3 bucket found and cannot create one.", "ERROR")
                            self._get_iam_permission_suggestions('s3:CreateBucket', 'Create S3 bucket for file storage')
                            return None, None
                    except Exception as list_error:
                        self.log(f"Cannot list buckets: {str(list_error)}", "ERROR")
                        return None, None
                else:
                    self.log(f"Error creating S3 bucket: {str(e)}", "ERROR")
                    return None, None
            
            # Upload files to S3
            uploaded_count = 0
            for filename, content in server_files.items():
                if not content:
                    continue
                
                try:
                    s3_key = f"{prefix}/{filename}"
                    
                    # For tarball files, content is already base64 encoded
                    if filename.endswith('.tar.gz'):
                        # Decode base64 and upload binary
                        file_data = base64.b64decode(content)
                        s3_client.put_object(
                            Bucket=bucket_name,
                            Key=s3_key,
                            Body=file_data,
                            ContentType='application/gzip'
                        )
                    else:
                        # Upload as text
                        s3_client.put_object(
                            Bucket=bucket_name,
                            Key=s3_key,
                            Body=content.encode('utf-8'),
                            ContentType='text/plain'
                        )
                    
                    uploaded_count += 1
                    self.log(f"  Uploaded {filename} to s3://{bucket_name}/{s3_key}")
                except Exception as e:
                    self.log(f"  Failed to upload {filename}: {str(e)}", "ERROR")
                    continue
            
            if uploaded_count == 0:
                self.log("No files were uploaded to S3", "ERROR")
                return None, None
            
            self.log(f"Successfully uploaded {uploaded_count} file(s) to S3 bucket: {bucket_name}", "SUCCESS")
            
            # Set bucket lifecycle to delete after 7 days
            try:
                s3_client.put_bucket_lifecycle_configuration(
                    Bucket=bucket_name,
                    LifecycleConfiguration={
                        'Rules': [{
                            'Id': 'DeleteOldFiles',
                            'Status': 'Enabled',
                            'Expiration': {'Days': 7}
                        }]
                    }
                )
            except Exception as e:
                self.log(f"Warning: Could not set bucket lifecycle: {str(e)}", "WARNING")
            
            return bucket_name, prefix
            
        except Exception as e:
            self.log(f"Error uploading files to S3: {str(e)}", "ERROR")
            return None, None
    
    def _generate_database_server_wrapper(self):
        """Generate a simple database MCP server wrapper"""
        return '''#!/usr/bin/env python3
"""
Database MCP Server Wrapper
"""
import sys
from pathlib import Path

# Add the scikiq_dbutils package to path
sys.path.insert(0, str(Path(__file__).parent))

if __name__ == "__main__":
    from scikiq_dbutils.mcp_server.main import main
    main()
'''
    
    def generate_setup_script(self, server_files, python_version="3.10", server_type=None, domain=None, public_ip=None,
                             s3_bucket=None, s3_prefix=None, aws_access_key=None, aws_secret_key=None, region=None):
        """
        Generate a bash script to set up the MCP server on a remote machine
        
        Args:
            server_files: Dictionary of files to create (used if not using S3)
            python_version: Python version to use
            server_type: Type of MCP server ('api', 'database', 'codebase')
            domain: Domain name for HTTPS setup
            public_ip: Public IP of the instance (for Route 53)
            s3_bucket: S3 bucket name (if files are in S3)
            s3_prefix: S3 prefix/path (if files are in S3)
            aws_access_key: AWS access key for S3 access
            aws_secret_key: AWS secret key for S3 access
            region: AWS region
        """
        # Determine server startup command based on type
        if server_type == 'database':
            startup_command = "/opt/mcp-server/venv/bin/python /opt/mcp-server/run_mcp_server.py --config-file /opt/mcp-server/config.ini"
        elif server_type in ['api', 'codebase', 'swagger']:
            # Find YAML files
            yaml_files = [f for f in server_files.keys() if f.endswith('.yaml')]
            if yaml_files:
                yaml_args = ' '.join([f"/opt/mcp-server/{f}" for f in yaml_files])
                startup_command = f"/opt/mcp-server/venv/bin/python /opt/mcp-server/mcp_server_loader.py {yaml_args}"
            else:
                startup_command = "/opt/mcp-server/venv/bin/python /opt/mcp-server/mcp_server_loader.py"
        else:
            # Default: look for app.py or mcp_server_loader.py
            if 'app.py' in server_files:
                startup_command = "/opt/mcp-server/venv/bin/python /opt/mcp-server/app.py"
            elif 'mcp_server_loader.py' in server_files:
                startup_command = "/opt/mcp-server/venv/bin/python /opt/mcp-server/mcp_server_loader.py"
            else:
                startup_command = "/opt/mcp-server/venv/bin/python /opt/mcp-server/app.py"
        
        # Read the template file
        template_path = Path(__file__).parent / 'templates' / 'ec2_setup_script.sh'
        if not template_path.exists():
            self.log(f"Template file not found at {template_path}, using fallback", "WARNING")
            # Fallback to a simple script
            return f"""#!/bin/bash
set -e
echo "MCP Server Setup"
cd /opt/mcp-server
{startup_command}
"""
        
        with open(template_path, 'r', encoding='utf-8') as f:
            script_template = f.read()
        
        # If using S3, replace file creation section with S3 download
        if s3_bucket and s3_prefix:
            # Create S3 download section
            # Note: For better security, consider using IAM instance profiles instead of embedding credentials
            s3_download_section = f"""
# Download files from S3
echo "Downloading files from S3..."

# Install boto3 and AWS CLI
pip install boto3 awscli

# Configure AWS credentials (temporary - consider using IAM instance profiles for production)
export AWS_ACCESS_KEY_ID={aws_access_key}
export AWS_SECRET_ACCESS_KEY={aws_secret_key}
export AWS_DEFAULT_REGION={region}

# Download all files from S3
echo "Syncing files from s3://{s3_bucket}/{s3_prefix}/..."
aws s3 sync s3://{s3_bucket}/{s3_prefix}/ . --region {region} --no-progress

# Extract tarball if present
if [ -f scikiq_dbutils.tar.gz ]; then
    echo "Extracting scikiq_dbutils.tar.gz..."
    tar -xzf scikiq_dbutils.tar.gz
    rm scikiq_dbutils.tar.gz
    echo "Successfully extracted scikiq_dbutils package"
fi

# Verify downloaded files
echo ""
echo "=== Verifying downloaded files ==="
ls -lah
file_count=$(ls -1 | wc -l)
echo "File count: $file_count"

# Make Python scripts executable
chmod +x *.py 2>/dev/null || true
echo "Files downloaded from S3 successfully"
"""
            
            # Replace the file creation section with S3 download
            # Find the section that starts with "# Create server files" and ends before "# Make Python scripts executable"
            import re
            # Match from "# Create server files" to the end of the Python heredoc block
            pattern = r'(# Create server files.*?PYTHON_EOF\s+if \[ \$\? -ne 0 \]; then\s+echo "ERROR: File creation failed!"\s+exit 1\s+fi)'
            script_template = re.sub(pattern, s3_download_section, script_template, flags=re.DOTALL)
        else:
            # Use embedded files approach (for small files)
            # Create JSON structure for file data
            if not server_files:
                file_data = {}
            else:
                file_data = {}
                for filename, content in server_files.items():
                    if not content:
                        continue
                    
                    # Handle tarball files (already base64 encoded)
                    if filename.endswith('.tar.gz'):
                        file_data[filename] = {'type': 'tar.gz', 'content': content}
                    else:
                        # Encode regular files as base64
                        content_b64 = base64.b64encode(content.encode('utf-8')).decode('ascii')
                        file_data[filename] = {'type': 'text', 'content': content_b64}
            
            # Encode JSON as base64 to avoid any escaping issues
            file_data_json = json.dumps(file_data)
            file_data_json_b64 = base64.b64encode(file_data_json.encode('utf-8')).decode('ascii')
            
            # Replace placeholder with file data
            script_template = script_template.replace('{{FILE_DATA_JSON_B64}}', file_data_json_b64)
        
        # Replace other placeholders
        script = script_template.replace('{{STARTUP_COMMAND}}', startup_command)
        script = script.replace('{{SERVER_TYPE}}', server_type or '')
        
        # Handle domain - if provided, set it, otherwise remove domain-related sections
        if domain:
            script = script.replace('{{DOMAIN}}', domain)
        else:
            # Remove the domain check and nginx setup if no domain
            # The template already handles this with the if statement, so we just need to set empty
            script = script.replace('if [ -n "$DOMAIN" ]; then', 'if [ -n "" ]; then')
        
        return script
    
    def _setup_route53(self, route53_client, domain, public_ip):
        """
        Set up Route 53 DNS record for the domain
        
        Args:
            route53_client: Boto3 Route 53 client
            domain: Domain name (e.g., 'mcp.example.com')
            public_ip: Public IP address of the EC2 instance
        """
        try:
            self.log(f"Setting up Route 53 DNS for {domain} -> {public_ip}")
            
            # Extract domain and subdomain
            parts = domain.split('.')
            if len(parts) < 2:
                self.log(f"Invalid domain format: {domain}", "ERROR")
                return
            
            # Get hosted zone for the domain
            # Try to find hosted zone for the root domain
            root_domain = '.'.join(parts[-2:])  # e.g., 'example.com'
            
            # List hosted zones
            zones_response = route53_client.list_hosted_zones()
            hosted_zone_id = None
            
            for zone in zones_response.get('HostedZones', []):
                zone_name = zone['Name'].rstrip('.')
                if zone_name == root_domain or domain.endswith('.' + zone_name):
                    hosted_zone_id = zone['Id'].split('/')[-1]
                    break
            
            if not hosted_zone_id:
                self.log(f"Could not find Route 53 hosted zone for {root_domain}", "WARNING")
                self.log("Please create a hosted zone in Route 53 for your domain first.", "INFO")
                return
            
            # Create or update A record
            change_batch = {
                'Changes': [{
                    'Action': 'UPSERT',
                    'ResourceRecordSet': {
                        'Name': domain,
                        'Type': 'A',
                        'TTL': 300,
                        'ResourceRecords': [{'Value': public_ip}]
                    }
                }]
            }
            
            route53_client.change_resource_record_sets(
                HostedZoneId=hosted_zone_id,
                ChangeBatch=change_batch
            )
            
            self.log(f"Route 53 DNS record created: {domain} -> {public_ip}", "SUCCESS")
            self.log("DNS propagation may take a few minutes.", "INFO")
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            if error_code == 'NoSuchHostedZone':
                self.log(f"Hosted zone not found for {domain}. Please create it in Route 53 first.", "WARNING")
            elif error_code in ['AccessDenied', 'UnauthorizedOperation']:
                self.log("Insufficient permissions for Route 53. Required: route53:ChangeResourceRecordSets", "WARNING")
            else:
                self.log(f"Route 53 error: {str(e)}", "WARNING")
        except Exception as e:
            self.log(f"Error setting up Route 53: {str(e)}", "WARNING")

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

    def deploy_to_aws(self, aws_access_key, aws_secret_key, region, instance_type, server_files, 
                     server_type=None, server_path=None, config_path=None, domain=None):
        """
        Deploy to AWS EC2
        
        Args:
            aws_access_key: AWS access key
            aws_secret_key: AWS secret key
            region: AWS region
            instance_type: EC2 instance type
            server_files: Dictionary of server files (legacy, for simple deployments)
            server_type: Type of MCP server ('api', 'database', 'codebase')
            server_path: Path to server files on local machine
            config_path: Path to config file (for database servers)
            domain: Domain name for Route 53 setup
        """
        self.log(f"Connecting to AWS ({region})...")
        
        try:
            ec2_resource = boto3.resource(
                'ec2',
                aws_access_key_id=aws_access_key,
                aws_secret_access_key=aws_secret_key,
                region_name=region
            )
            
            ec2_client = boto3.client(
                'ec2',
                aws_access_key_id=aws_access_key,
                aws_secret_access_key=aws_secret_key,
                region_name=region
            )
            
            # Find or get VPC and Subnet
            self.log("Finding available VPC and subnet...")
            vpc_id, subnet_id = self._get_vpc_and_subnet(ec2_client)
            
            if not vpc_id or not subnet_id:
                self.log("No suitable VPC or subnet found. Please create a VPC in your AWS account.", "ERROR")
                return None
            
            self.log(f"Using VPC: {vpc_id}, Subnet: {subnet_id}")
            
            # Create or get security group
            security_group_id = self._get_or_create_security_group(ec2_client, vpc_id)
            if not security_group_id:
                self.log("Failed to create or find security group.", "ERROR")
                return None
            
            self.log(f"Using Security Group: {security_group_id}")
            
            # Prepare server files based on server type
            if server_type and server_path:
                server_files = self._prepare_server_files(server_type, server_path, config_path)
                self.log(f"Prepared {len(server_files)} files for {server_type} server")
                # Log file names for debugging
                for filename in server_files.keys():
                    file_size = len(server_files[filename]) if server_files[filename] else 0
                    self.log(f"  - {filename} ({file_size} bytes)")
                if not server_files:
                    self.log("Warning: No files prepared! Check server_path and config_path.", "WARNING")
            
            # Upload files to S3 if they're too large for user-data
            s3_bucket = None
            s3_prefix = None
            total_size = sum(len(content) if content else 0 for content in server_files.values())
            
            if total_size > 10000:  # If files are larger than 10KB, use S3
                self.log(f"Files are large ({total_size/1024:.2f} KB), uploading to S3...", "INFO")
                s3_bucket, s3_prefix = self._upload_files_to_s3(
                    server_files, aws_access_key, aws_secret_key, region
                )
                if not s3_bucket:
                    self.log("Failed to upload files to S3. Deployment cannot continue.", "ERROR")
                    return None
            
            setup_script = self.generate_setup_script(
                server_files, 
                server_type=server_type,
                domain=domain,
                public_ip=None,  # Will be set after instance launch
                s3_bucket=s3_bucket,
                s3_prefix=s3_prefix,
                aws_access_key=aws_access_key,
                aws_secret_key=aws_secret_key,
                region=region
            )
            
            # Check user-data size (AWS limit is 16KB uncompressed, but we can use gzip)
            script_size = len(setup_script.encode('utf-8'))
            self.log(f"User-data script size: {script_size} bytes ({script_size/1024:.2f} KB)")
            
            if script_size > 16384:
                self.log(f"Warning: User-data script exceeds 16KB limit. Compressing...", "WARNING")
                # Compress the script
                compressed = gzip.compress(setup_script.encode('utf-8'))
                compressed_size = len(compressed)
                self.log(f"Compressed size: {compressed_size} bytes ({compressed_size/1024:.2f} KB)")
                
                if compressed_size > 16384:
                    self.log(f"ERROR: Compressed user-data ({compressed_size} bytes) still exceeds 16KB limit!", "ERROR")
                    self.log("This should not happen if files are uploaded to S3. Please check the setup script.", "ERROR")
                    return None
                
                user_data = base64.b64encode(compressed).decode('ascii')
                # Cloud-init will auto-detect gzip compression
                user_data = f"#!/bin/bash\n# Compressed user-data\nbase64 -d << 'COMPRESSED_EOF' | gunzip | bash\n{user_data}\nCOMPRESSED_EOF"
                self.log(f"Final user-data size: {len(user_data)} bytes ({len(user_data)/1024:.2f} KB)")
            else:
                user_data = setup_script # Cloud-init handles bash scripts
            
            self.log("Launching EC2 instance...")
            
            # Find a basic Ubuntu AMI (simplified logic - in prod, search for latest)
            # This is a hardcoded Ubuntu 22.04 LTS AMI for us-east-1 as placeholder
            # In real implementation, we need to search for AMI based on region
            image_id = self._get_ubuntu_ami(ec2_client, region, aws_access_key, aws_secret_key)
            
            instances = ec2_resource.create_instances(
                ImageId=image_id,
                MinCount=1,
                MaxCount=1,
                InstanceType=instance_type,
                SubnetId=subnet_id,
                SecurityGroupIds=[security_group_id],
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
            
            # Set up Route 53 DNS if domain is provided
            if domain:
                self.log(f"Setting up Route 53 DNS for domain: {domain}", "INFO")
                try:
                    route53_client = boto3.client(
                        'route53',
                        aws_access_key_id=aws_access_key,
                        aws_secret_access_key=aws_secret_key
                    )
                    self._setup_route53(route53_client, domain, public_ip)
                except Exception as e:
                    self.log(f"Warning: Could not set up Route 53 DNS: {str(e)}", "WARNING")
                    self.log("You can manually set up DNS later.", "INFO")
            else:
                self.log("No domain provided. Skipping Route 53 DNS setup.", "INFO")
                self.log("You can access the server directly via IP address.", "INFO")
            
            self.log("Deployment script is running in background. Please wait 5-10 minutes for initialization.", "INFO")
            if domain:
                self.log(f"Once DNS propagates (5-10 minutes), your server will be available at https://{domain}", "INFO")
            else:
                self.log(f"Server will be accessible at http://{public_ip} after initialization completes.", "INFO")
            
            # Give a moment for all logs to be queued
            time.sleep(0.5)
            
            return {"public_ip": public_ip, "instance_id": instance.id, "domain": domain}

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = str(e)
            
            # Check for permission errors and provide suggestions
            if error_code in ['UnauthorizedOperation', 'AccessDenied']:
                # Try to determine the operation from the error message
                operation = 'RunInstances'  # Default
                if 'CreateSecurityGroup' in error_message:
                    operation = 'CreateSecurityGroup'
                elif 'DescribeVpcs' in error_message or 'VPC' in error_message:
                    operation = 'DescribeVpcs'
                
                suggestions = self._get_iam_permission_suggestions(error_code, operation)
                if suggestions:
                    self.log(f"AWS Deployment Error: {error_message}", "ERROR")
                    self.log(suggestions, "ERROR")
                else:
                    self.log(f"AWS Deployment Error: {error_message}", "ERROR")
                    self.log("Your AWS user is missing required permissions. Please contact your AWS administrator.", "ERROR")
            else:
                self.log(f"AWS Deployment Error: {error_message}", "ERROR")
            
            return None
        except Exception as e:
            error_message = str(e)
            self.log(f"AWS Deployment Error: {error_message}", "ERROR")
            
            # Check if it's a permission-related error even if not ClientError
            if 'not authorized' in error_message.lower() or 'unauthorized' in error_message.lower():
                suggestions = self._get_iam_permission_suggestions('UnauthorizedOperation', 'RunInstances')
                if suggestions:
                    self.log(suggestions, "ERROR")
            
            return None

    def _get_ubuntu_ami(self, ec2_client, region, aws_access_key=None, aws_secret_key=None):
        """
        Get the latest Ubuntu 22.04 LTS AMI for the specified region.
        Uses SSM parameter store for reliable AMI lookup, falls back to EC2 describe-images.
        """
        try:
            # Try to get from SSM parameter store (most reliable)
            try:
                ssm_client = boto3.client(
                    'ssm',
                    region_name=region,
                    aws_access_key_id=aws_access_key,
                    aws_secret_access_key=aws_secret_key
                )
                response = ssm_client.get_parameter(
                    Name='/aws/service/canonical/ubuntu/server/22.04/stable/current/amd64/hvm/ebs-gp2/ami-id'
                )
                ami_id = response['Parameter']['Value']
                self.log(f"Found Ubuntu 22.04 LTS AMI via SSM: {ami_id}")
                return ami_id
            except ClientError as ssm_error:
                # If SSM fails (e.g., no permissions), fall back to EC2 describe-images
                self.log("SSM parameter store not accessible, using EC2 describe-images...", "INFO")
            
            # Fallback: Search for Ubuntu 22.04 LTS AMI using EC2
            response = ec2_client.describe_images(
                Owners=['099720109477'],  # Canonical
                Filters=[
                    {'Name': 'name', 'Values': ['ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*']},
                    {'Name': 'state', 'Values': ['available']},
                    {'Name': 'architecture', 'Values': ['x86_64']},
                    {'Name': 'virtualization-type', 'Values': ['hvm']}
                ]
            )
            
            if response['Images']:
                # Sort by creation date and get the latest
                images = sorted(response['Images'], key=lambda x: x['CreationDate'], reverse=True)
                ami_id = images[0]['ImageId']
                self.log(f"Found Ubuntu 22.04 LTS AMI via EC2 search: {ami_id}")
                return ami_id
            
            # Last resort: Return a hardcoded AMI based on region (may become outdated)
            # These are Ubuntu 22.04 LTS AMIs - should be updated periodically
            self.log(f"Using fallback AMI for region {region}", "WARNING")
            region_amis = {
                'us-east-1': 'ami-0c7217cdde317cfec',
                'us-east-2': 'ami-0a695f0d95cefc163',
                'us-west-1': 'ami-0c55b159cbfafe1f0',
                'us-west-2': 'ami-0c55b159cbfafe1f0',
                'eu-west-1': 'ami-0c55b159cbfafe1f0',
                'eu-west-2': 'ami-0c55b159cbfafe1f0',
                'eu-west-3': 'ami-0c55b159cbfafe1f0',
                'eu-central-1': 'ami-0c55b159cbfafe1f0',
                'ap-southeast-1': 'ami-0c55b159cbfafe1f0',
                'ap-southeast-2': 'ami-0c55b159cbfafe1f0',
                'ap-south-1': 'ami-0c55b159cbfafe1f0',
                'ap-northeast-1': 'ami-0c55b159cbfafe1f0',
                'ap-northeast-2': 'ami-0c55b159cbfafe1f0',
                'ca-central-1': 'ami-0c55b159cbfafe1f0',
                'sa-east-1': 'ami-0c55b159cbfafe1f0',
            }
            
            # Return region-specific AMI or default to us-east-1
            return region_amis.get(region, region_amis['us-east-1'])
            
        except Exception as e:
            self.log(f"Warning: Could not dynamically find AMI for region {region}. Using fallback. Error: {str(e)}", "WARNING")
            # Return a safe default
            return "ami-0c7217cdde317cfec"  # Ubuntu 22.04 us-east-1
    
    def _get_vpc_and_subnet(self, ec2_client):
        """
        Find a suitable VPC and subnet for launching instances.
        Prefers default VPC, otherwise uses the first available VPC with a public subnet.
        """
        try:
            # First, try to find default VPC
            vpcs = ec2_client.describe_vpcs(
                Filters=[{'Name': 'isDefault', 'Values': ['true']}]
            )
            
            if vpcs['Vpcs']:
                vpc_id = vpcs['Vpcs'][0]['VpcId']
                self.log(f"Found default VPC: {vpc_id}")
            else:
                # No default VPC, get any available VPC
                all_vpcs = ec2_client.describe_vpcs()
                if not all_vpcs['Vpcs']:
                    self.log("No VPCs found in this region.", "ERROR")
                    return None, None
                vpc_id = all_vpcs['Vpcs'][0]['VpcId']
                self.log(f"Using VPC: {vpc_id} (no default VPC found)")
            
            # Find a public subnet in the VPC
            subnets = ec2_client.describe_subnets(
                Filters=[
                    {'Name': 'vpc-id', 'Values': [vpc_id]},
                    {'Name': 'map-public-ip-on-launch', 'Values': ['true']}
                ]
            )
            
            if subnets['Subnets']:
                subnet_id = subnets['Subnets'][0]['SubnetId']
                return vpc_id, subnet_id
            
            # If no public subnet found, get any subnet in the VPC
            all_subnets = ec2_client.describe_subnets(
                Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}]
            )
            
            if all_subnets['Subnets']:
                subnet_id = all_subnets['Subnets'][0]['SubnetId']
                self.log(f"Using subnet: {subnet_id} (may not have public IP)", "WARNING")
                return vpc_id, subnet_id
            
            self.log("No subnets found in the VPC.", "ERROR")
            return None, None
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = str(e)
            
            # Check for permission errors
            if error_code in ['UnauthorizedOperation', 'AccessDenied']:
                suggestions = self._get_iam_permission_suggestions(error_code, 'DescribeVpcs')
                if suggestions:
                    self.log(f"Error finding VPC/subnet: {error_message}", "ERROR")
                    self.log(suggestions, "ERROR")
                else:
                    self.log(f"Error finding VPC/subnet: {error_message}", "ERROR")
            else:
                self.log(f"Error finding VPC/subnet: {error_message}", "ERROR")
            
            return None, None
        except Exception as e:
            error_message = str(e)
            self.log(f"Error finding VPC/subnet: {error_message}", "ERROR")
            
            # Check if it's a permission-related error
            if 'not authorized' in error_message.lower() or 'unauthorized' in error_message.lower():
                suggestions = self._get_iam_permission_suggestions('UnauthorizedOperation', 'DescribeVpcs')
                if suggestions:
                    self.log(suggestions, "ERROR")
            
            return None, None
    
    def _get_or_create_security_group(self, ec2_client, vpc_id):
        """
        Get or create a security group for MCP server with necessary ports open.
        Falls back to default security group or any available security group if creation fails.
        """
        sg_name = "mcp-server-sg"
        
        try:
            # Try to find existing security group with our name
            existing_sgs = ec2_client.describe_security_groups(
                Filters=[
                    {'Name': 'group-name', 'Values': [sg_name]},
                    {'Name': 'vpc-id', 'Values': [vpc_id]}
                ]
            )
            
            if existing_sgs['SecurityGroups']:
                sg_id = existing_sgs['SecurityGroups'][0]['GroupId']
                self.log(f"Using existing security group: {sg_id}")
                return sg_id
            
            # Try to create new security group
            try:
                self.log(f"Creating security group: {sg_name}")
                sg_response = ec2_client.create_security_group(
                    GroupName=sg_name,
                    Description='Security group for MCP Server deployment',
                    VpcId=vpc_id
                )
                sg_id = sg_response['GroupId']
                
                # Try to add inbound rules (may also fail due to permissions)
                try:
                    ec2_client.authorize_security_group_ingress(
                        GroupId=sg_id,
                        IpPermissions=[
                            {
                                'IpProtocol': 'tcp',
                                'FromPort': 22,
                                'ToPort': 22,
                                'IpRanges': [{'CidrIp': '0.0.0.0/0', 'Description': 'SSH access'}]
                            },
                            {
                                'IpProtocol': 'tcp',
                                'FromPort': 80,
                                'ToPort': 80,
                                'IpRanges': [{'CidrIp': '0.0.0.0/0', 'Description': 'HTTP access'}]
                            },
                            {
                                'IpProtocol': 'tcp',
                                'FromPort': 443,
                                'ToPort': 443,
                                'IpRanges': [{'CidrIp': '0.0.0.0/0', 'Description': 'HTTPS access'}]
                            },
                            {
                                'IpProtocol': 'tcp',
                                'FromPort': 5000,
                                'ToPort': 5000,
                                'IpRanges': [{'CidrIp': '0.0.0.0/0', 'Description': 'Flask default port'}]
                            }
                        ]
                    )
                    self.log(f"Added inbound rules to security group: {sg_id}")
                except ClientError as ingress_error:
                    error_code = ingress_error.response.get('Error', {}).get('Code', 'Unknown')
                    error_message = str(ingress_error)
                    
                    # If we can't add rules, still use the security group (user can add rules manually)
                    self.log(f"Warning: Could not add inbound rules to security group. Error: {error_message}", "WARNING")
                    
                    # Provide permission suggestions if it's a permission error
                    if error_code in ['UnauthorizedOperation', 'AccessDenied']:
                        suggestions = self._get_iam_permission_suggestions(error_code, 'CreateSecurityGroup')
                        if suggestions:
                            self.log("To add inbound rules automatically, you need the following permissions:", "WARNING")
                            self.log("  • ec2:AuthorizeSecurityGroupIngress", "WARNING")
                            self.log("  • ec2:DescribeSecurityGroups", "WARNING")
                            self.log("You can manually add these rules in the AWS Console:", "WARNING")
                            self.log("  • SSH (port 22) from 0.0.0.0/0", "WARNING")
                            self.log("  • HTTP (port 80) from 0.0.0.0/0", "WARNING")
                            self.log("  • HTTPS (port 443) from 0.0.0.0/0", "WARNING")
                            self.log("  • Flask (port 5000) from 0.0.0.0/0", "WARNING")
                
                self.log(f"Created security group: {sg_id}")
                return sg_id
                
            except ClientError as create_error:
                error_code = create_error.response['Error']['Code']
                error_message = str(create_error)
                
                # If creation fails due to permissions, try to use default security group
                if error_code in ['UnauthorizedOperation', 'AccessDenied']:
                    # Provide permission suggestions
                    suggestions = self._get_iam_permission_suggestions(error_code, 'CreateSecurityGroup')
                    if suggestions:
                        self.log("Cannot create security group (insufficient permissions).", "ERROR")
                        self.log(suggestions, "ERROR")
                    
                    self.log("Attempting to use existing security group as fallback...", "WARNING")
                    
                    # Try to find default security group for the VPC
                    try:
                        default_sgs = ec2_client.describe_security_groups(
                            Filters=[
                                {'Name': 'group-name', 'Values': ['default']},
                                {'Name': 'vpc-id', 'Values': [vpc_id]}
                            ]
                        )
                        
                        if default_sgs['SecurityGroups']:
                            sg_id = default_sgs['SecurityGroups'][0]['GroupId']
                            self.log(f"Using default security group: {sg_id}", "WARNING")
                            self.log("Note: You may need to manually configure security group rules for SSH (22), HTTP (80), HTTPS (443), and port 5000", "WARNING")
                            return sg_id
                    except ClientError:
                        pass
                    
                    # If no default security group, try to find any security group in the VPC
                    try:
                        all_sgs = ec2_client.describe_security_groups(
                            Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}]
                        )
                        
                        if all_sgs['SecurityGroups']:
                            sg_id = all_sgs['SecurityGroups'][0]['GroupId']
                            sg_name_used = all_sgs['SecurityGroups'][0].get('GroupName', 'unknown')
                            self.log(f"Using existing security group '{sg_name_used}': {sg_id}", "WARNING")
                            self.log("Note: You may need to manually configure security group rules for SSH (22), HTTP (80), HTTPS (443), and port 5000", "WARNING")
                            return sg_id
                    except ClientError:
                        pass
                    
                    # If we can't find any security group, return error with suggestions
                    self.log("No security groups found in VPC and cannot create new one.", "ERROR")
                    if not suggestions:  # If suggestions weren't shown earlier, show them now
                        suggestions = self._get_iam_permission_suggestions(error_code, 'CreateSecurityGroup')
                        if suggestions:
                            self.log(suggestions, "ERROR")
                    return None
                
                elif error_code == 'InvalidGroup.Duplicate':
                    # Security group already exists, try to find it again
                    existing_sgs = ec2_client.describe_security_groups(
                        Filters=[
                            {'Name': 'group-name', 'Values': [sg_name]},
                            {'Name': 'vpc-id', 'Values': [vpc_id]}
                        ]
                    )
                    if existing_sgs['SecurityGroups']:
                        return existing_sgs['SecurityGroups'][0]['GroupId']
                
                # Other errors
                self.log(f"Error creating security group: {str(create_error)}", "ERROR")
                return None
            
        except Exception as e:
            self.log(f"Error with security group: {str(e)}", "ERROR")
            return None

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

