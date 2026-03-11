import sys
sys.path.insert(0, '.')
from online_deployment import OnlineDeployer

def verify_nginx_port():
    print("--- Verifying Nginx Port Configuration ---")
    deployer = OnlineDeployer()
    
    # Test cases
    test_cases = [
        {
            "name": "Swagger Server",
            "server_type": "swagger",
            "server_files": {"mcp_server_loader.py": "", "requirements.txt": ""},
            "expected_port": "30210"
        },
        {
            "name": "API Server",
            "server_type": "api",
            "server_files": {"mcp_server_loader.py": ""},
            "expected_port": "30210"
        },
        {
            "name": "Database Server (Admin)",
            "server_type": "database",
            "server_files": {"remote_mcp_server_admin.py": ""},
            "expected_port": "30210"
        },
        {
            "name": "Standard Server (No Admin)",
            "server_type": "stdio",
            "server_files": {"server.py": ""},
            "expected_port": "8000"
        }
    ]
    
    all_passed = True
    
    for case in test_cases:
        print(f"\nTesting: {case['name']}")
        
        # Mock inputs for generate_setup_script
        # We only care about the Nginx port logic, so we can pass dummy values for others
        script = deployer.generate_setup_script(
            server_files=case['server_files'],
            server_type=case['server_type'],
            python_version="3.10",
            admin_username="admin",
            admin_password="password",
            domain="example.com", # Domain needed to trigger Nginx setup
            s3_bucket="bucket",
            s3_prefix="prefix",
            aws_access_key="key",
            aws_secret_key="secret",
            region="ap-south-1"
        )
        
        # Check for port 30210
        if f"proxy_pass http://127.0.0.1:{case['expected_port']};" in script:
             print(f"✅ Correctly configured proxy_pass to {case['expected_port']}")
        else:
             print(f"❌ Failed to find proxy_pass to {case['expected_port']}")
             # Print relevant section for debugging
             if "proxy_pass" in script:
                 import re
                 match = re.search(r"proxy_pass.*?;", script)
                 print(f"   Found: {match.group(0) if match else 'None'}")
             all_passed = False

        # Check echo message
        if case['expected_port'] == "30210":
            if 'Server is running on port 30210 (internal)' in script:
                print("✅ Correctly updated echo message")
            else:
                print("❌ Failed to update echo message")
                all_passed = False

    print("\n--- Verification Result ---")
    if all_passed:
        print("✅ All Nginx configuration tests PASSED")
    else:
        print("❌ Some tests FAILED")

if __name__ == "__main__":
    verify_nginx_port()
