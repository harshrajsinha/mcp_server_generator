
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.getcwd())

from online_deployment import OnlineDeployment

def debug_loader_generation():
    deployment = OnlineDeployment()
    
    try:
        loader_code = deployment._generate_admin_loader_code()
        print("Successfully generated admin loader code.")
        print(f"Code length: {len(loader_code)}")
        
        # Save to file for inspection
        with open("debug_generated_loader.py", "w", encoding="utf-8") as f:
            f.write(loader_code)
            
        print("Saved generated code to debug_generated_loader.py")
        
        # Check for FastMCPServer definition
        if "class FastMCPServer" in loader_code:
            print("Found FastMCPServer class definition.")
        else:
            print("FastMCPServer class definition NOT found.")
            
        # Check for YAML loading logic
        if "yaml.safe_load" in loader_code:
            print("Found yaml.safe_load.")
        else:
            print("yaml.safe_load NOT found.")
            
    except Exception as e:
        print(f"Error generating loader: {e}")

if __name__ == "__main__":
    debug_loader_generation()
