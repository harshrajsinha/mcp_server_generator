"""
MCP Server Cleanup and Management
Handles deletion and cleanup of MCP servers from Claude Desktop
"""
import os
import json
import platform
import subprocess
import shutil
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class MCPCleanup:
    def __init__(self):
        self.system = platform.system()
        self.config_path = self._get_config_path()

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

    def list_servers(self):
        """List all registered MCP servers"""
        try:
            if not self.config_path.exists():
                return {"success": True, "servers": [], "message": "No config file found"}

            with open(self.config_path, 'r') as f:
                config = json.load(f)

            servers = config.get("mcpServers", {})
            server_list = []

            for name, details in servers.items():
                server_info = {
                    "name": name,
                    "command": details.get("command", ""),
                    "args": details.get("args", []),
                    "env": details.get("env", {})
                }
                server_list.append(server_info)

            return {
                "success": True,
                "servers": server_list,
                "count": len(server_list)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def delete_server(self, server_name, delete_files=True, restart_claude=True):
        """
        Delete an MCP server from Claude Desktop config and optionally clean up files

        Args:
            server_name: Name of the server to delete
            delete_files: Whether to delete associated generated files
            restart_claude: Whether to restart Claude Desktop after deletion

        Returns:
            dict: Status of deletion operation
        """
        try:
            results = {
                "server_name": server_name,
                "config_removed": False,
                "files_deleted": [],
                "claude_restarted": False,
                "errors": []
            }

            # Step 1: Load config
            if not self.config_path.exists():
                return {"success": False, "error": "Config file not found"}

            with open(self.config_path, 'r') as f:
                config = json.load(f)

            # Step 2: Check if server exists
            if server_name not in config.get("mcpServers", {}):
                return {"success": False, "error": f"Server '{server_name}' not found in config"}

            # Step 3: Get server details before deletion (for file cleanup)
            server_details = config["mcpServers"][server_name]
            server_args = server_details.get("args", [])

            # Step 4: Remove from config
            del config["mcpServers"][server_name]

            # Write updated config
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)

            results["config_removed"] = True
            print(f"[OK] Removed '{server_name}' from Claude Desktop config")

            # Step 5: Delete associated files if requested
            if delete_files and server_args:
                for arg_path in server_args:
                    try:
                        path = Path(arg_path)
                        if path.exists():
                            if path.is_file():
                                path.unlink()
                                results["files_deleted"].append(str(path))
                                print(f"[OK] Deleted file: {path}")
                            elif path.is_dir():
                                shutil.rmtree(path)
                                results["files_deleted"].append(str(path))
                                print(f"[OK] Deleted directory: {path}")
                    except Exception as e:
                        error_msg = f"Could not delete {arg_path}: {str(e)}"
                        results["errors"].append(error_msg)
                        print(f"[WARN] {error_msg}")

            # Step 6: Clean up logs
            try:
                logs_path = self._get_claude_logs_path()
                if logs_path and logs_path.exists():
                    log_files = list(logs_path.glob(f'mcp-server-{server_name}*.log'))
                    for log_file in log_files:
                        log_file.unlink()
                        results["files_deleted"].append(str(log_file))
                        print(f"[OK] Deleted log: {log_file.name}")
            except Exception as e:
                results["errors"].append(f"Could not clean logs: {str(e)}")

            # Step 7: Restart Claude Desktop if requested
            if restart_claude:
                restart_result = self._restart_claude_desktop()
                results["claude_restarted"] = restart_result
                if restart_result:
                    print("[OK] Claude Desktop restarted")
                else:
                    print("[WARN] Could not restart Claude Desktop - please restart manually")

            return {
                "success": True,
                "results": results
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def delete_all_servers(self, delete_files=True, restart_claude=True):
        """Delete all MCP servers"""
        try:
            servers_result = self.list_servers()
            if not servers_result["success"]:
                return servers_result

            results = []
            for server in servers_result["servers"]:
                result = self.delete_server(server["name"], delete_files, restart_claude=False)
                results.append(result)

            # Restart once after all deletions
            if restart_claude:
                self._restart_claude_desktop()

            return {
                "success": True,
                "deleted_count": len(results),
                "results": results
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _get_claude_logs_path(self):
        """Get Claude Desktop logs directory"""
        try:
            if self.system == "Windows":
                return Path(os.getenv('APPDATA')) / "Claude" / "logs"
            elif self.system == "Darwin":
                return Path.home() / "Library" / "Application Support" / "Claude" / "logs"
            elif self.system == "Linux":
                return Path.home() / ".config" / "Claude" / "logs"
        except:
            return None

    def _is_claude_running(self):
        """Check if Claude Desktop is running"""
        try:
            if self.system == "Windows":
                result = subprocess.run(['tasklist'], capture_output=True, text=True)
                return 'claude.exe' in result.stdout.lower()
            elif self.system == "Darwin":
                result = subprocess.run(['pgrep', '-f', 'Claude'], capture_output=True, text=True)
                return bool(result.stdout.strip())
            elif self.system == "Linux":
                result = subprocess.run(['pgrep', '-f', 'claude'], capture_output=True, text=True)
                return bool(result.stdout.strip())
        except:
            return False

    def _restart_claude_desktop(self):
        """Restart Claude Desktop"""
        try:
            is_running = self._is_claude_running()

            if self.system == "Windows":
                # Kill if running
                if is_running:
                    subprocess.run(['taskkill', '/F', '/IM', 'claude.exe'], capture_output=True, check=False)
                    import time
                    time.sleep(2)

                # Start Claude Desktop
                env_claude_path = os.getenv('CLAUDE_DESKTOP_PATH')
                env_claude_exe = os.getenv('CLAUDE_DESKTOP_EXE', 'claude.exe')

                if env_claude_path:
                    claude_path = Path(env_claude_path) / env_claude_exe
                    if claude_path.exists():
                        subprocess.Popen([str(claude_path)], shell=True)
                        return True

                return False

            elif self.system == "Darwin":
                subprocess.run(['pkill', '-f', 'Claude'], check=False)
                import time
                time.sleep(2)
                subprocess.run(['open', '-a', 'Claude'], check=False)
                return True

            elif self.system == "Linux":
                subprocess.run(['pkill', '-f', 'claude'], check=False)
                import time
                time.sleep(2)
                subprocess.run(['claude'], check=False)
                return True

            return False
        except Exception as e:
            print(f"[ERROR] Could not restart Claude: {e}")
            return False


def main():
    """CLI interface for MCP cleanup"""
    import sys

    cleanup = MCPCleanup()

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python mcp_cleanup.py list")
        print("  python mcp_cleanup.py delete <server_name>")
        print("  python mcp_cleanup.py delete-all")
        return

    command = sys.argv[1]

    if command == "list":
        result = cleanup.list_servers()
        if result["success"]:
            print(f"\n[SERVERS] Found {result['count']} MCP server(s):\n")
            for server in result["servers"]:
                print(f"  Name: {server['name']}")
                print(f"  Command: {server['command']}")
                print(f"  Args: {', '.join(server['args'])}")
                print()
        else:
            print(f"[ERROR] {result['error']}")

    elif command == "delete" and len(sys.argv) > 2:
        server_name = sys.argv[2]
        result = cleanup.delete_server(server_name, delete_files=True, restart_claude=True)
        if result["success"]:
            print(f"\n[SUCCESS] Server '{server_name}' deleted successfully")
        else:
            print(f"[ERROR] {result['error']}")

    elif command == "delete-all":
        confirm = input("Delete ALL MCP servers? (yes/no): ")
        if confirm.lower() == "yes":
            result = cleanup.delete_all_servers(delete_files=True, restart_claude=True)
            if result["success"]:
                print(f"\n[SUCCESS] Deleted {result['deleted_count']} server(s)")
            else:
                print(f"[ERROR] {result['error']}")

    else:
        print(f"[ERROR] Unknown command: {command}")


if __name__ == "__main__":
    main()
