
import os
import sys
import requests
import shutil

def test_github_scan():
    # URL of the running application
    api_url = "http://localhost:30211/api/scan-project"
    
    payload = {
        "project_path": "",
        "github_repo_url": "https://github.com/harshrajsinha/demorestaurantapp.git",
        "api_base_url": "http://localhost:5000"
    }
    
    print(f"Testing scan with URL: {payload['github_repo_url']}")
    
    try:
        response = requests.post(api_url, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            print(f"Success! Found {data.get('total_apis')} endpoints.")
            print(f"Message: {data.get('message')}")
            
            # Verify cloned directory exists
            cloned_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cloned_repos', 'demorestaurantapp')
            if os.path.exists(cloned_dir):
                print(f"Verified cloned directory exists at: {cloned_dir}")
            else:
                print(f"ERROR: Cloned directory not found at: {cloned_dir}")
                
        else:
            print(f"Failed with status code: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_github_scan()
