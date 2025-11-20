import sqlite3
import json

# Connect to the database and check the redirect URIs
conn = sqlite3.connect('mcp_auth.db')
cursor = conn.cursor()

print("=== Checking OAuth Client Redirect URIs ===")
cursor.execute("""
    SELECT client_id, client_name, redirect_uris 
    FROM oauth_clients 
    WHERE client_id = 'mcp_client_SXZetzG6fTVUpA-CwNt5PQ'
""")

client = cursor.fetchone()
if client:
    print(f"Client ID: {client[0]}")
    print(f"Client Name: {client[1]}")
    print(f"Redirect URIs (raw): {client[2]}")
    
    try:
        redirect_uris = json.loads(client[2])
        print(f"Redirect URIs (parsed): {redirect_uris}")
        print(f"Type: {type(redirect_uris)}")
        
        # Check if Claude's redirect URI is in the list
        claude_redirect = "https://claude.ai/api/mcp/auth_callback"
        print(f"\nClaude redirect URI: {claude_redirect}")
        print(f"Is in redirect_uris: {claude_redirect in redirect_uris}")
        
    except json.JSONDecodeError as e:
        print(f"Error parsing redirect URIs: {e}")
else:
    print("Client not found!")

conn.close()