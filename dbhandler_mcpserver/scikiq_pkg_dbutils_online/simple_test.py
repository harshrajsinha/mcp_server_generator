#!/usr/bin/env python3
"""
Simple test for the remote server
"""

import asyncio
import httpx

async def test_server():
    """Test the remote server"""
    try:
        async with httpx.AsyncClient() as client:
            # Test health endpoint
            response = await client.get("http://localhost:3000/health")
            print(f"Health Status: {response.status_code}")
            if response.status_code == 200:
                print(f"Health Response: {response.json()}")
                
                # Test tools endpoint
                response = await client.get("http://localhost:3000/mcp/tools")
                print(f"Tools Status: {response.status_code}")
                if response.status_code == 200:
                    data = response.json()
                    print(f"Found {len(data.get('tools', []))} tools")
                    return True
            
    except Exception as e:
        print(f"Error: {e}")
    return False

if __name__ == "__main__":
    result = asyncio.run(test_server())
    print(f"Test {'PASSED' if result else 'FAILED'}")