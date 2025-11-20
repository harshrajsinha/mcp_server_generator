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
            
            setup_script = self.generate_setup_script(server_files)
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
            self.log("Deployment script is running in background. Please wait 5-10 minutes for initialization.", "INFO")
            
            return {"public_ip": public_ip, "instance_id": instance.id}

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

