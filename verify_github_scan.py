
from swagger_parser import scan_codebase_for_apis
import json
import os

repo_path = "cloned_repos/gaurdiaandemoapp"

print(f"Scanning {repo_path}...")
try:
    result = scan_codebase_for_apis(repo_path)
    
    if result['success']:
        print(f"Found {len(result['api_definitions'])} APIs")
        
        # Print all routes to check for parameter preservation
        for api in result['api_definitions']:
            print(f"Route: {api['route']}")
            print(f"  Function: {api['function_name']}")
            print(f"  Parameters: {[p['name'] for p in api['parameters']]}")
            print("-" * 20)
            
        # Check for duplicates
        routes = [api['route'] for api in result['api_definitions']]
        if len(routes) != len(set(routes)):
            print("WARNING: Duplicate routes found!")
            from collections import Counter
            print(Counter(routes))
        else:
            print("No duplicate routes found.")
            
    else:
        print(f"Scan failed: {result.get('error')}")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
