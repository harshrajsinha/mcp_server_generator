import ast
from intelligent_mcp_converter import IntelligentMCPConverter, IntelligentCodeAnalyzer

code_snippet = """
from flask import Flask, jsonify
app = Flask(__name__)

SCHEMA = "public"
TABLES = {'dim_customer': {'columns': ['id', 'name']}}
def execute_query(query, params, fetch=True): return []

@app.route('/api/business/customer/<customer_id>/summary', methods=['GET'])
def get_customer_summary(customer_id):
    try:
        # 1. Customer Details
        customer_query = f"SELECT * FROM {SCHEMA}.dim_customer WHERE customer_id = :cid"
        customer = execute_query(customer_query, {'cid': customer_id}, fetch=True)
        if not customer:
            return jsonify({"error": "Customer not found"}), 404
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
"""

def test_extraction():
    print("Initializing converter...")
    # Mock the analyzer to avoid needing full project structure
    converter = IntelligentMCPConverter(".")
    
    # Parse the code
    print("Parsing code...")
    tree = ast.parse(code_snippet)
    
    # Find the function
    func_node = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == 'get_customer_summary':
            func_node = node
            break
            
    if not func_node:
        print("Function not found!")
        return

    # Extract route info
    print("Extracting route info...")
    route_info = converter.analyzer._extract_route_info_intelligently(func_node)
    print(f"Extracted Route Info: {route_info}")
    
    if route_info:
        print(f"Path: {route_info['path']}")
        if '<customer_id>' in route_info['path']:
            print("SUCCESS: <customer_id> preserved in path")
        else:
            print("FAILURE: <customer_id> missing from path")
            
    # Also test the full analysis pipeline if possible
    # This might be harder to mock without a file, but let's try to simulate what analyze_codebase does
    
if __name__ == "__main__":
    test_extraction()
