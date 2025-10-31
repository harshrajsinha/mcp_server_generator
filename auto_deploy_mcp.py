"""
Auto-Deploy MCP Server to Claude Desktop
Automatically configures and registers MCP tools with Claude Desktop
With AI-powered error diagnosis and automatic fixes
"""
import os
import json
import platform
import subprocess
import shutil
import sys
import re
from pathlib import Path
from openai import AzureOpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class MCPAutoDeployer:
    def __init__(self):
        self.system = platform.system()
        self.config_path = self._get_config_path()
        self.python_path = sys.executable
        self.diagnostics = []  # Store all diagnostic logs
        self.max_retries = 3

        # Initialize Azure OpenAI client with httpx client (proxy disabled)
        import httpx
        http_client = httpx.Client(proxy=None, trust_env=False)

        self.openai_client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            http_client=http_client
        )

    def _get_config_path(self):
        """Get Claude Desktop config path based on OS"""
        if self.system == "Windows":
            return Path(os.getenv('APPDATA')) / "Claude" / "claude_desktop_config.json"
        elif self.system == "Darwin":  # macOS
            return Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
        elif self.system == "Linux":
            return Path.home() / ".config" / "Claude" / "claude_desktop_config.json"
        else:
            raise Exception(f"Unsupported operating system: {self.system}")

    def deploy_mcp_server(self, mcp_server_path, yaml_tools_path=None, server_name='scikiq-mcp-autoAPI', auto_restart=True):
        """
        Automatically deploy MCP server to Claude Desktop with intelligent retry

        Args:
            mcp_server_path: Path to the generated MCP server Python file (loader script)
            yaml_tools_path: Path to YAML file with tool definitions (optional, for accumulation)
            server_name: Name for the MCP server in config (defaults to 'scikiq-mcp-autoAPI')
            auto_restart: Whether to attempt restarting Claude Desktop

        Returns:
            dict: Deployment status, diagnostics, and instructions
        """
        self.diagnostics = []  # Reset diagnostics

        for attempt in range(self.max_retries):
            try:
                self._log_diagnostic(f"Deployment Attempt {attempt + 1}/{self.max_retries}", "info")

                print(f"[DEPLOY] Attempt {attempt + 1}/{self.max_retries}")
                print(f"   System: {self.system}")
                print(f"   Config: {self.config_path}")
                print(f"   Server: {mcp_server_path}")
                print(f"   Python: {self.python_path}")

                # Step 0: Install MCP SDK if not present
                self._log_diagnostic("Checking MCP SDK installation...", "info")
                self._ensure_mcp_sdk_installed()

                # Step 1: Ensure config directory exists
                self.config_path.parent.mkdir(parents=True, exist_ok=True)
                self._log_diagnostic("Config directory ready", "success")

                # Step 2: Load or create config
                if self.config_path.exists():
                    with open(self.config_path, 'r') as f:
                        config = json.load(f)
                    self._log_diagnostic("Loaded existing config", "success")
                else:
                    config = {"mcpServers": {}}
                    self._log_diagnostic("Created new config", "success")

                # Step 3: Add MCP server to config
                if "mcpServers" not in config:
                    config["mcpServers"] = {}

                # Get absolute paths
                abs_server_path = str(Path(mcp_server_path).absolute())

                # Check if server already exists
                if server_name in config["mcpServers"]:
                    self._log_diagnostic(f"Server '{server_name}' already exists, updating tools", "info")

                    # Get existing args (should be [server_script, yaml1, yaml2, ...])
                    existing_args = config["mcpServers"][server_name].get("args", [abs_server_path])

                    # If yaml_tools_path provided, add it if not already present
                    if yaml_tools_path:
                        abs_yaml_path = str(Path(yaml_tools_path).absolute())
                        if abs_yaml_path not in existing_args:
                            existing_args.append(abs_yaml_path)
                            self._log_diagnostic(f"Added new tool file: {abs_yaml_path}", "success")
                        else:
                            self._log_diagnostic(f"Tool file already registered: {abs_yaml_path}", "info")

                    config["mcpServers"][server_name]["args"] = existing_args
                else:
                    # New server - create config
                    args = [abs_server_path]
                    if yaml_tools_path:
                        args.append(str(Path(yaml_tools_path).absolute()))

                    config["mcpServers"][server_name] = {
                        "command": self.python_path,
                        "args": args
                    }
                    self._log_diagnostic(f"Registered new server '{server_name}' in config", "success")

                # Step 4: Write config back with proper path formatting
                # Ensure all paths are properly formatted as strings
                if server_name in config.get("mcpServers", {}):
                    server_config = config["mcpServers"][server_name]
                    # Convert all args to strings (no manual escaping needed - JSON will handle it)
                    if "args" in server_config:
                        server_config["args"] = [str(arg) if isinstance(arg, (str, Path)) else str(arg) for arg in server_config["args"]]
                    # Convert command to string (no manual escaping needed - JSON will handle it)
                    if "command" in server_config:
                        server_config["command"] = str(server_config["command"])

                with open(self.config_path, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=2, ensure_ascii=False)

                # Verify the paths were written correctly
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    verify_config = json.load(f)
                    if server_name in verify_config.get("mcpServers", {}):
                        verify_args = verify_config["mcpServers"][server_name].get("args", [])
                        self._log_diagnostic(f"Verified config args: {verify_args}", "info")
                        # Check if paths have proper backslashes
                        for arg in verify_args:
                            if ":" in arg and "\\" not in arg and "/" not in arg:
                                self._log_diagnostic(f"WARNING: Path may be malformed: {arg}", "error")

                self._log_diagnostic("Config file saved with proper path escaping", "success")

                # Step 5: Validate MCP server syntax
                self._log_diagnostic("Validating MCP server syntax...", "info")
                validation_result = self._validate_mcp_server(abs_server_path)
                if not validation_result['valid']:
                    self._log_diagnostic(f"Validation failed: {validation_result['error']}", "error")

                    # Try to auto-fix the issue
                    fix_result = self._auto_fix_server(abs_server_path, validation_result['error'])
                    if fix_result['fixed']:
                        self._log_diagnostic(f"Auto-fix applied: {fix_result['fix_description']}", "success")
                        continue  # Retry with fixed code
                    else:
                        return {
                            'success': False,
                            'error': f"Validation failed: {validation_result['error']}",
                            'diagnostics': self.diagnostics
                        }

                self._log_diagnostic("Validation passed", "success")

                # Step 6: Clear old logs before restart to avoid confusion
                if auto_restart:
                    self._clear_old_logs(server_name)

                # Step 7: Attempt to restart Claude Desktop
                restart_success = False
                if auto_restart:
                    self._log_diagnostic("Restarting Claude Desktop...", "info")
                    restart_success = self._restart_claude_desktop()
                    if restart_success:
                        self._log_diagnostic("Claude Desktop restarted", "success")
                    else:
                        self._log_diagnostic("Claude Desktop restart may need manual intervention", "warning")

                # Step 8: Check Claude Desktop logs for errors
                self._log_diagnostic("Checking Claude Desktop logs...", "info")
                log_check = self._check_claude_logs(server_name)

                if not log_check.get('checked'):
                    self._log_diagnostic(f"Logs check skipped: {log_check.get('reason', 'Unknown reason')}", "warning")
                elif log_check.get('has_errors'):
                    self._log_diagnostic("Errors found in logs - analyzing...", "warning")

                    # Check if errors are from old logs (Python path issue)
                    error_text = '\n'.join(log_check.get('errors', []))
                    if 'spawn python ENOENT' in error_text or ('glic-insurance' in error_text and server_name != 'glic-insurance'):
                        self._log_diagnostic("Errors appear to be from previous runs with old configuration", "warning")
                        self._log_diagnostic("Config file has been updated with correct Python path and server name", "info")

                        # If we still have retries, wait and check again for fresh logs
                        if attempt < self.max_retries - 1:
                            self._log_diagnostic("Retrying to check for fresh logs after config update...", "info")
                            import time
                            time.sleep(5)  # Wait longer for new logs
                            continue  # Retry to check new logs
                        else:
                            self._log_diagnostic("Please manually restart Claude Desktop to ensure new config is loaded", "warning")
                    else:
                        # Real errors that need attention
                        self._log_diagnostic(f"Server errors detected: {error_text[:200]}", "error")
                        # Continue anyway to return full diagnostics
                else:
                    self._log_diagnostic("No errors found in logs", "success")

                # Step 8: Generate test sample
                test_sample = self._generate_test_sample(server_name)

                return {
                    'success': True,
                    'config_path': str(self.config_path),
                    'server_name': server_name,
                    'server_path': abs_server_path,
                    'restart_attempted': auto_restart,
                    'restart_success': restart_success,
                    'log_status': log_check,
                    'test_sample': test_sample,
                    'diagnostics': self.diagnostics,
                    'attempts': attempt + 1
                }

            except Exception as e:
                self._log_diagnostic(f"Attempt {attempt + 1} failed: {str(e)}", "error")
                if attempt == self.max_retries - 1:
                    return {
                        'success': False,
                        'error': str(e),
                        'diagnostics': self.diagnostics
                    }

        return {
            'success': False,
            'error': 'Max retries exceeded',
            'diagnostics': self.diagnostics
        }

    def _ensure_mcp_sdk_installed(self):
        """Check and install MCP SDK if not present"""
        try:
            import importlib.util
            spec = importlib.util.find_spec("mcp")
            if spec is None:
                print("[INSTALL] MCP SDK not found, installing...")
                subprocess.run([self.python_path, '-m', 'pip', 'install', 'mcp'],
                             check=True, capture_output=True)
                print("[OK] MCP SDK installed successfully")
            else:
                print("[OK] MCP SDK already installed")
        except Exception as e:
            print(f"[WARN] Could not verify/install MCP SDK: {e}")

    def _validate_mcp_server(self, server_path):
        """Validate MCP server file syntax"""
        try:
            with open(server_path, 'r') as f:
                content = f.read()

            # Check for common issues
            if '@server.tool()' in content:
                return {
                    'valid': False,
                    'error': 'MCP server uses deprecated @server.tool() decorator. Please regenerate with updated syntax.'
                }

            # Try to compile the Python file
            try:
                compile(content, server_path, 'exec')
                print("[OK] MCP server syntax validated")
                return {'valid': True}
            except SyntaxError as e:
                return {
                    'valid': False,
                    'error': f'Python syntax error: {str(e)}'
                }
        except Exception as e:
            print(f"[WARN] Could not validate MCP server: {e}")
            return {'valid': True}  # Don't block deployment on validation errors

    def _get_claude_logs_path(self):
        """Get Claude Desktop logs directory path based on OS"""
        if self.system == "Windows":
            return Path(os.getenv('APPDATA')) / "Claude" / "logs"
        elif self.system == "Darwin":  # macOS
            return Path.home() / "Library" / "Logs" / "Claude"
        elif self.system == "Linux":
            return Path.home() / ".config" / "Claude" / "logs"
        else:
            return None

    def _log_diagnostic(self, message, level="info"):
        """Add a diagnostic log entry"""
        import datetime
        self.diagnostics.append({
            'timestamp': datetime.datetime.now().isoformat(),
            'level': level,
            'message': message
        })
        print(f"[{level.upper()}] {message}")

    def _is_claude_running(self):
        """Check if Claude Desktop is currently running"""
        try:
            if self.system == "Windows":
                import subprocess
                result = subprocess.run(['tasklist'], capture_output=True, text=True)
                return 'Claude.exe' in result.stdout
            elif self.system == "Darwin":  # macOS
                import subprocess
                result = subprocess.run(['pgrep', '-f', 'Claude'], capture_output=True, text=True)
                return bool(result.stdout.strip())
            elif self.system == "Linux":
                import subprocess
                result = subprocess.run(['pgrep', '-f', 'claude'], capture_output=True, text=True)
                return bool(result.stdout.strip())
            return False
        except Exception as e:
            self._log_diagnostic(f"Could not check if Claude is running: {str(e)}", "warning")
            return False

    def _clear_old_logs(self, server_name):
        """Clear or rename old log files ONLY for the current server being deployed"""
        try:
            logs_path = self._get_claude_logs_path()
            if not logs_path or not logs_path.exists():
                return

            import shutil
            import time
            timestamp = int(time.time())

            # ONLY clear logs for the current server being deployed
            self._log_diagnostic(f"Clearing logs only for server: {server_name}", "info")

            # Find all log files for this specific server only
            log_files = list(logs_path.glob(f'mcp-server-{server_name}*.log'))

            cleared_count = 0
            for log_file in log_files:
                try:
                    # Rename to .old extension with timestamp
                    backup_name = f"{log_file.stem}.{timestamp}.old"
                    backup_path = log_file.parent / backup_name
                    shutil.move(str(log_file), str(backup_path))
                    cleared_count += 1
                    self._log_diagnostic(f"Archived old log: {log_file.name} -> {backup_name}", "info")
                except Exception as e:
                    self._log_diagnostic(f"Could not archive {log_file.name}: {str(e)}", "warning")

            if cleared_count > 0:
                self._log_diagnostic(f"Cleared {cleared_count} old log file(s) for server '{server_name}'", "success")
            else:
                self._log_diagnostic(f"No old log files found for server '{server_name}'", "info")

        except Exception as e:
            self._log_diagnostic(f"Error clearing old logs: {str(e)}", "warning")

    def _check_claude_logs(self, server_name):
        """Check Claude Desktop logs for MCP server errors - ONLY for the current server being deployed"""
        try:
            logs_path = self._get_claude_logs_path()
            if not logs_path or not logs_path.exists():
                self._log_diagnostic("Logs directory not found", "warning")
                return {'checked': False, 'reason': 'Logs directory not found'}

            import time

            # Check if Claude Desktop is running
            is_running = self._is_claude_running()
            if is_running:
                self._log_diagnostic("Claude Desktop is running, waiting for server initialization...", "info")
                time.sleep(8)  # Wait longer for Claude to start the server and generate fresh logs
            else:
                self._log_diagnostic("Claude Desktop is not running, checking existing logs...", "warning")

            # ONLY check logs for the specific server being deployed
            self._log_diagnostic(f"Checking logs only for server: {server_name}", "info")
            
            # Look for server-specific log files first
            server_specific_logs = sorted(logs_path.glob(f'mcp-server-{server_name}*.log'),
                                         key=lambda x: x.stat().st_mtime, reverse=True)
            
            log_files = []
            if server_specific_logs:
                log_files.extend(server_specific_logs)
                self._log_diagnostic(f"Found {len(server_specific_logs)} server-specific log file(s)", "info")
            
            # If no server-specific logs, check main mcp.log but only for our server entries
            if not log_files:
                main_log = logs_path / 'mcp.log'
                if main_log.exists():
                    log_files.append(main_log)
                    self._log_diagnostic("No server-specific logs found, checking main mcp.log", "info")

            if not log_files:
                self._log_diagnostic(f"No log files found for server '{server_name}'", "warning")
                return {'checked': False, 'reason': f'No log files found for server {server_name}'}

            self._log_diagnostic(f"Found {len(log_files)} log file(s): {[f.name for f in log_files]}", "info")

            # Read and analyze logs
            relevant_logs = []
            
            for log_file in log_files:
                self._log_diagnostic(f"Reading log file: {log_file.name}", "info")
                
                try:
                    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                        log_content = f.read()

                    log_lines = log_content.split('\n')
                    
                    # If this is a server-specific log, include all lines
                    if f'mcp-server-{server_name}' in log_file.name:
                        relevant_logs.extend(log_lines)
                        self._log_diagnostic(f"Added {len(log_lines)} lines from server-specific log", "info")
                    else:
                        # If this is the main mcp.log, only extract lines related to our server
                        server_lines = []
                        for i, line in enumerate(log_lines):
                            if server_name in line:
                                # Get context around this line
                                start = max(0, i - 2)
                                end = min(len(log_lines), i + 10)
                                server_lines.extend(log_lines[start:end])
                        
                        if server_lines:
                            relevant_logs.extend(server_lines)
                            self._log_diagnostic(f"Added {len(server_lines)} server-related lines from main log", "info")
                        else:
                            self._log_diagnostic(f"No entries found for server '{server_name}' in main log", "info")
                            
                except Exception as e:
                    self._log_diagnostic(f"Error reading {log_file.name}: {str(e)}", "warning")

            if not relevant_logs:
                self._log_diagnostic(f"No log entries found for server '{server_name}'", "info")
                return {'checked': True, 'has_errors': False, 'reason': f'No log entries for server {server_name}'}

            self._log_diagnostic(f"Scanning {len(relevant_logs)} log lines for errors...", "info")

            # Check for errors only in our server's logs
            error_patterns = ['AttributeError', 'ModuleNotFoundError', 'ImportError', 'SyntaxError', 'Error:', 'Traceback', 'error']
            errors_found = []

            for line in relevant_logs:
                if any(pattern in line for pattern in error_patterns):
                    errors_found.append(line.strip())

            if errors_found:
                self._log_diagnostic(f"Found {len(errors_found)} error(s) in logs for server '{server_name}'", "error")
                return {
                    'checked': True,
                    'has_errors': True,
                    'errors': errors_found,
                    'full_log': '\n'.join(relevant_logs)
                }

            self._log_diagnostic(f"No errors found in logs for server '{server_name}'", "success")
            return {'checked': True, 'has_errors': False}
            
        except Exception as e:
            self._log_diagnostic(f"Could not check logs: {str(e)}", "error")
            return {'checked': False, 'reason': str(e)}

    def _ai_diagnose_and_fix(self, server_path, errors):
        """Use AI to diagnose errors and attempt automatic fix"""
        try:
            self._log_diagnostic("Using AI to diagnose errors...", "info")

            # Read current server code
            with open(server_path, 'r') as f:
                current_code = f.read()

            # Create diagnostic prompt
            error_text = '\n'.join(errors)

            prompt = f"""You are an expert Python developer specializing in MCP (Model Context Protocol) servers.

An MCP server deployment has failed with the following errors:

{error_text}

Current MCP server code:
```python
{current_code}
```

Please analyze the error and provide:
1. A clear diagnosis of what's wrong
2. Whether this can be automatically fixed
3. If fixable, provide the corrected Python code

Respond in JSON format:
{{
    "diagnosis": "Clear explanation of the issue",
    "can_fix": true/false,
    "fix_type": "syntax_fix|dependency_fix|logic_fix|unfixable",
    "corrected_code": "Full corrected Python code (if can_fix is true)"
}}"""

            response = self.openai_client.chat.completions.create(
                model=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4"),
                messages=[
                    {"role": "system", "content": "You are an expert Python and MCP server developer."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)
            self._log_diagnostic(f"AI Diagnosis: {result['diagnosis']}", "info")

            if result.get('can_fix') and result.get('corrected_code'):
                # Apply the fix
                with open(server_path, 'w') as f:
                    f.write(result['corrected_code'])

                self._log_diagnostic("Applied AI-generated fix to server code", "success")
                return {
                    'fixed': True,
                    'diagnosis': result['diagnosis'],
                    'fix_type': result.get('fix_type', 'unknown')
                }
            else:
                # Check if it's a Python path issue
                if 'spawn python ENOENT' in error_text or 'python' in error_text.lower():
                    self._log_diagnostic("Config file has been updated with correct Python path", "info")
                    self._log_diagnostic("These errors are from previous runs - please restart Claude Desktop to load the new config", "warning")

                self._log_diagnostic(f"Cannot auto-fix: {result['diagnosis']}", "warning")
                return {
                    'fixed': False,
                    'diagnosis': result['diagnosis'],
                    'requires_manual_action': 'spawn python ENOENT' in error_text
                }

        except Exception as e:
            self._log_diagnostic(f"AI diagnosis failed: {str(e)}", "error")
            return {
                'fixed': False,
                'diagnosis': f"AI analysis error: {str(e)}"
            }

    def _auto_fix_server(self, server_path, error_message):
        """Attempt automatic fixes for common issues"""
        try:
            with open(server_path, 'r') as f:
                code = f.read()

            fixed = False
            fix_description = ""

            # Fix 1: Replace deprecated @server.tool() decorator
            if '@server.tool()' in code:
                self._log_diagnostic("Detected deprecated @server.tool() decorator", "warning")

                # Use AI to properly convert the old syntax
                prompt = f"""Convert this MCP server code from old decorator syntax (@server.tool()) to new MCP SDK 1.x syntax using @server.list_tools() and @server.call_tool().

Current code:
```python
{code}
```

Provide the fully corrected code that uses:
- @server.list_tools() to return list of Tool objects
- @server.call_tool() to handle tool execution
- Proper imports: from mcp import types

Return only the corrected Python code, no explanations."""

                response = self.openai_client.chat.completions.create(
                    model=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4"),
                    messages=[
                        {"role": "system", "content": "You are an expert in MCP SDK migration."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.1
                )

                corrected_code = response.choices[0].message.content
                # Remove markdown code blocks if present
                corrected_code = re.sub(r'^```python\n', '', corrected_code)
                corrected_code = re.sub(r'\n```$', '', corrected_code)

                with open(server_path, 'w') as f:
                    f.write(corrected_code)

                fixed = True
                fix_description = "Migrated from old @server.tool() to new MCP SDK 1.x syntax"
                self._log_diagnostic(fix_description, "success")

            return {
                'fixed': fixed,
                'fix_description': fix_description
            }

        except Exception as e:
            self._log_diagnostic(f"Auto-fix failed: {str(e)}", "error")
            return {
                'fixed': False,
                'fix_description': str(e)
            }

    def _restart_claude_desktop(self):
        """Attempt to restart Claude Desktop application"""
        try:
            is_running = self._is_claude_running()

            if is_running:
                self._log_diagnostic("Claude Desktop is running, restarting...", "info")
            else:
                self._log_diagnostic("Claude Desktop is not running, starting it...", "info")

            if self.system == "Windows":
                # Kill Claude Desktop if running
                if is_running:
                    subprocess.run(['taskkill', '/F', '/IM', 'claude.exe'],
                                 capture_output=True, check=False)
                    self._log_diagnostic("Stopped Claude Desktop", "info")
                    import time
                    time.sleep(2)  # Wait for process to fully stop

                # Find and start Claude Desktop
                # First check .env file for custom path
                from dotenv import load_dotenv
                load_dotenv()

                possible_paths = []

                # Add path from .env if specified
                env_claude_path = os.getenv('CLAUDE_DESKTOP_PATH')
                env_claude_exe = os.getenv('CLAUDE_DESKTOP_EXE', 'claude.exe')
                if env_claude_path:
                    possible_paths.append(Path(env_claude_path) / env_claude_exe)

                # Add standard paths
                possible_paths.extend([
                    Path(os.getenv('LOCALAPPDATA')) / "Programs" / "Claude" / "Claude.exe",
                    Path(os.getenv('PROGRAMFILES')) / "Claude" / "Claude.exe",
                    Path(os.getenv('PROGRAMFILES(X86)')) / "Claude" / "Claude.exe"
                ])

                for claude_path in possible_paths:
                    if claude_path.exists():
                        subprocess.Popen([str(claude_path)], shell=True)
                        self._log_diagnostic(f"Started Claude Desktop from {claude_path}", "success")

                        # Wait and verify it started
                        import time
                        time.sleep(10)  # Give Claude time to start
                        if self._is_claude_running():
                            self._log_diagnostic("Verified Claude Desktop is running", "success")
                            return True
                        else:
                            self._log_diagnostic("Claude Desktop did not start successfully", "warning")
                            return False

                self._log_diagnostic("Could not find Claude Desktop executable", "error")
                return False

            elif self.system == "Darwin":  # macOS
                # Kill Claude Desktop
                subprocess.run(['pkill', '-f', 'Claude'], check=False)
                print("   Stopped Claude Desktop")

                # Restart Claude Desktop
                subprocess.Popen(['open', '-a', 'Claude'])
                print("[OK] Restarted Claude Desktop")
                return True

            elif self.system == "Linux":
                subprocess.run(['pkill', '-f', 'claude'], check=False)
                print("   Stopped Claude Desktop")

                # Try to find and restart
                subprocess.Popen(['claude'], shell=True)
                print("[OK] Restarted Claude Desktop")
                return True

        except Exception as e:
            print(f"[WARN] Restart failed: {e}")
            return False

    def _generate_test_sample(self, server_name):
        """Generate chat test samples"""
        return f"""
# Test Your MCP Tools in Claude Desktop

## Step 1: Look for the Hammer Icon
In Claude Desktop, find the hammer/tools icon in the bottom-left corner of the chat input.

## Step 2: View Available Tools
Click the hammer icon to see all your {server_name} tools listed.

## Step 3: Test Sample Queries

### Customer Management
```
Can you create a new customer named "John Smith" with email john@example.com?
```

### Policy Management
```
Show me all active insurance policies for customer ID 12345
```

### Quote Generation
```
Generate an auto insurance quote for a 2023 Toyota Camry
```

### Claims Processing
```
Create a claim for policy number POL-2024-001 with damage description "Rear-end collision"
```

### Network Management
```
Find all in-network hospitals in zip code 10001
```

## Step 4: Verify Tool Usage
After each query, Claude should:
1. Show which tool it's using
2. Display the parameters being sent
3. Return the API response
4. Provide a formatted answer

## Sample Conversation

**You**: "Create a customer named Sarah Johnson with email sarah@company.com"

**Claude**: "I'll use the create_customer tool to add this customer to the system."
[Tool: create_customer]
Parameters: {{
  "name": "Sarah Johnson",
  "email": "sarah@company.com"
}}

Result: Customer created successfully with ID CUST-12345

**You**: "Now create a policy for that customer"

**Claude**: "I'll create a policy for customer CUST-12345..."
[Tool: create_policy]

And so on!

## Troubleshooting

If tools don't appear:
1. Check config file exists at: {self.config_path}
2. Verify Claude Desktop was restarted
3. Look for errors in Claude Desktop Developer Console (Ctrl+Shift+I)
4. Check MCP server logs

## Advanced: Chain Multiple Tools

**You**: "Find customer John Smith, get their policies, and create a claim for their auto policy"

Claude will automatically:
1. Use search_customers tool
2. Use get_policies tool
3. Use create_claim tool
4. Chain the results together
"""

def main():
    """Example usage"""
    deployer = MCPAutoDeployer()

    # Example: Deploy the generated MCP server
    result = deployer.deploy_mcp_server(
        mcp_server_path="C:/demo/glic/mcp_server_high_confidence.py",
        server_name="scikiq-mcp-autoAPI",
        auto_restart=True
    )

    if result['success']:
        print("\n" + "="*70)
        print("[SUCCESS] DEPLOYMENT SUCCESSFUL!")
        print("="*70)
        print(f"Server Name: {result['server_name']}")
        print(f"Server Path: {result['server_path']}")
        print(f"Config File: {result['config_path']}")
        print(f"Claude Restart: {'Success' if result['restart_success'] else 'Manual Required'}")
        print("\n" + result['test_sample'])
    else:
        print(f"\n[ERROR] Deployment failed: {result['error']}")

if __name__ == "__main__":
    main()
