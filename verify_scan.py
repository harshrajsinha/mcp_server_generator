
from swagger_parser import scan_codebase_for_apis
import os
import json

# Create a dummy file with a route
with open("dummy_route.py", "w") as f:
    f.write("""
from flask import Flask
app = Flask(__name__)

@app.route('/api/business/customer/<customer_id>/summary')
def get_customer_summary(customer_id):
    return {"id": customer_id}
""")

print("Scanning codebase...")
try:
    result = scan_codebase_for_apis(".", "dummy_route.py")
    
    if result['success']:
        # Filter for dummy_route
        dummy_apis = [api for api in result['api_definitions'] if 'customer' in api['route']]
        print(json.dumps(dummy_apis, indent=2))
    else:
        print(f"Scan failed: {result.get('error')}")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

if os.path.exists("dummy_route.py"):
    os.remove("dummy_route.py")
