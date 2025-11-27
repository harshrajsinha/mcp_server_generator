#!/usr/bin/env python3
"""
Debug Auto Deploy MCP - Test specific time usage
"""

def test_deployment():
    """Test deployment to find exact error location"""
    try:
        import sys
        import os
        sys.path.append(os.path.dirname(__file__))
        
        from auto_deploy_mcp import MCPAutoDeployer
        
        print("Creating MCPAutoDeployer instance...")
        deployer = MCPAutoDeployer()
        
        print("Testing deployment with dummy path...")
        # Test with a non-existent file to trigger error handling
        result = deployer.deploy_mcp_server(
            mcp_server_path="C:\\test\\dummy_server.py",
            server_name="test-server",
            auto_restart=False  # Don't restart Claude during test
        )
        
        print(f"Deployment result: {result['success']}")
        if not result['success']:
            print(f"Error: {result.get('error', 'Unknown error')}")
            
        return True
        
    except Exception as e:
        print(f"❌ Detailed Error: {e}")
        print(f"Error type: {type(e)}")
        import traceback
        print("Full traceback:")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_deployment()