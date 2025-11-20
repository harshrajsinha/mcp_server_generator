import sqlite3
import json
import secrets
import requests
import time

# Wait for server to start
time.sleep(2)

# Login to admin panel
login_data = {
    'username': 'admin',
    'password': 'harsh123'
}

session = requests.Session()

# Login
login_response = session.post('http://localhost:3002/admin/login', data=login_data)
print(f"Login status: {login_response.status_code}")

if login_response.status_code == 200:
    # Create Claude client
    client_data = {
        'client_name': 'claude-test',
        'redirect_uris': 'https://claude.ai/api/mcp/auth_callback'
    }
    
    create_response = session.post('http://localhost:3002/admin/create-client', data=client_data)
    print(f"Create client status: {create_response.status_code}")
    print(f"Response: {create_response.text}")
    
    if create_response.status_code == 200:
        # Parse the response to get client details
        if 'Client created successfully!' in create_response.text:
            print("✅ Client created successfully!")
            
            # Get the client ID from the database
            conn = sqlite3.connect('mcp_auth.db')
            cursor = conn.cursor()
            cursor.execute("SELECT client_id, client_name, redirect_uris FROM oauth_clients WHERE client_name = 'claude-test'")
            client = cursor.fetchone()
            conn.close()
            
            if client:
                print(f"\n📋 Client Details:")
                print(f"Client ID: {client[0]}")
                print(f"Client Name: {client[1]}")
                print(f"Redirect URIs: {client[2]}")
                
                # Test the authorization endpoint
                test_url = f"http://localhost:3002/authorize?response_type=code&client_id={client[0]}&redirect_uri=https://claude.ai/api/mcp/auth_callback&code_challenge=dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk&code_challenge_method=S256"
                print(f"\n🔗 Test URL:")
                print(test_url)
                
                # Test authorization
                test_response = requests.get(test_url, allow_redirects=False)
                print(f"\n🧪 Authorization Test:")
                print(f"Status: {test_response.status_code}")
                print(f"Headers: {dict(test_response.headers)}")
                if test_response.status_code == 302:
                    print(f"✅ Redirect URL: {test_response.headers.get('location')}")
                else:
                    print(f"❌ Response: {test_response.text}")
else:
    print(f"❌ Login failed: {login_response.text}")