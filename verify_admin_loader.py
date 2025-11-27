import sys
import ast
import re
sys.path.insert(0, '.')
from online_deployment import OnlineDeployer

def verify_code():
    print('--- Starting Verification ---')
    deployer = OnlineDeployer()
    try:
        code = deployer._generate_admin_loader_code()
        print(f'✅ Code generated successfully. Length: {len(code)} bytes')
    except Exception as e:
        print(f'❌ Code generation failed: {e}')
        return

    # 1. Syntax Check
    try:
        ast.parse(code)
        print('✅ Syntax check passed')
    except SyntaxError as e:
        print(f'❌ Syntax check failed: {e}')
        return

    # 2. Check main function signature
    main_match = re.search(r'def main\((.*?)\)', code)
    if main_match:
        args = main_match.group(1)
        if 'config_path_unused: str' in args and 'yaml_files: tuple' in args:
            print('✅ main() signature correct')
        else:
            print(f'❌ main() signature incorrect: {args}')
    else:
        print('❌ main() function not found')

    # 3. Check Click options
    if '@click.option("--config-path-unused"' in code and '@click.option("--yaml-files"' in code:
        print('✅ Click options correct')
    else:
        print('❌ Click options missing or incorrect')

    # 4. Check RemoteMCPServerWithAdmin class
    class_match = re.search(r'class RemoteMCPServerWithAdmin:.*?(?=class |$)', code, re.DOTALL)
    if class_match:
        class_code = class_match.group(0)
        
        # Check for self.config_path usage
        if 'self.config_path' in class_code:
             matches = [(m.start(), m.group()) for m in re.finditer(r'self\.config_path', class_code)]
             print(f'❌ Found {len(matches)} usages of self.config_path in RemoteMCPServerWithAdmin')
             for pos, _ in matches:
                 print(f'   ...{class_code[pos-20:pos+30].replace(chr(10), " ")}...')
        else:
            print('✅ No self.config_path usage in RemoteMCPServerWithAdmin')
            
        # Check for self.yaml_paths usage
        if 'self.yaml_paths' in class_code:
            print('✅ Found self.yaml_paths usage in RemoteMCPServerWithAdmin')
        else:
            print('❌ No self.yaml_paths usage in RemoteMCPServerWithAdmin')
            
    else:
        print('❌ RemoteMCPServerWithAdmin class not found')

    print('--- Verification Complete ---')

if __name__ == "__main__":
    verify_code()
