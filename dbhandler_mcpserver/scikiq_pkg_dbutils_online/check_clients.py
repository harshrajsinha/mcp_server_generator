import sqlite3
import json

conn = sqlite3.connect('mcp_auth.db')
cursor = conn.cursor()

print("=== OAuth Clients ===")
cursor.execute('SELECT client_id, redirect_uris, client_name, client_secret FROM oauth_clients')
clients = cursor.fetchall()

if clients:
    for client in clients:
        print(f"Client ID: {client[0]}")
        print(f"Name: {client[2]}")
        print(f"Secret: {client[3][:8]}..." if client[3] else "None")
        print(f"Redirect URIs: {client[1]}")
        print("-" * 40)
else:
    print("No OAuth clients found in database")

print("\n=== Admin Users ===")
cursor.execute('SELECT username, created_at FROM users')
users = cursor.fetchall()

if users:
    for user in users:
        print(f"Username: {user[0]}")
        print(f"Created: {user[1]}")
        print("-" * 20)
else:
    print("No admin users found")

conn.close()