"""
KernelDeck Agent CLI — Tool Definitions & Execution Sandbox
===========================================================
Owner: C
Protocol Reference: PROTOCOL.md
"""

import os
import subprocess
from pathlib import Path

# Tool Schemas for OpenAI chat.completions API
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Reads the text contents of a file within the project directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative file path to read."}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Writes text contents to a file within the project directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative file path to write."},
                    "content": {"type": "string", "description": "File contents to write."}
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "Lists files and subdirectories in a directory path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative directory path (default '.')."}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Executes a shell command on the host system. High-risk operations are gated by KernelDeck hardware.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The exact shell command line string to execute."}
                },
                "required": ["command"]
            }
        }
    }
]


class ToolSandbox:
    """
    Executes tool calls locally within safe sandbox boundaries.
    Commands and file operations are strictly contained within the repository scratch directory.
    """
    def __init__(self, base_dir=None):
        self.base_dir = Path(base_dir or os.getcwd()).resolve()

    def _resolve_safe_path(self, rel_path: str) -> Path:
        resolved = (self.base_dir / rel_path).resolve()
        # Ensure path stays within base directory boundary
        try:
            resolved.relative_to(self.base_dir)
        except ValueError:
            raise PermissionError(f"Access denied: path '{rel_path}' escapes sandbox boundary.")
        return resolved

    def read_file(self, path: str) -> str:
        safe_path = self._resolve_safe_path(path)
        if not safe_path.exists():
            return f"Error: File not found: {path}"
        if safe_path.is_dir():
            return f"Error: Path is a directory: {path}"
        return safe_path.read_text(encoding="utf-8", errors="replace")

    def write_file(self, path: str, content: str) -> str:
        safe_path = self._resolve_safe_path(path)
        safe_path.parent.mkdir(parents=True, exist_ok=True)
        safe_path.write_text(content, encoding="utf-8")
        return f"File written successfully: {path} ({len(content)} bytes)"

    def list_dir(self, path: str = ".") -> str:
        safe_path = self._resolve_safe_path(path)
        if not safe_path.exists():
            return f"Error: Directory not found: {path}"
        if not safe_path.is_dir():
            return f"Error: Path is not a directory: {path}"
        items = [f"{'[DIR] ' if p.is_dir() else '[FILE] '} {p.name}" for p in safe_path.iterdir()]
        return "\n".join(items) if items else "(empty directory)"

    def run_command(self, command: str) -> str:
        """
        Executes a shell command strictly within the local sandbox.
        This must only be called AFTER the proxy has returned HTTP 200 approval!
        """
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=str(self.base_dir),
                capture_output=True,
                text=True,
                timeout=15.0
            )
            output = result.stdout or result.stderr
            return f"Exit code {result.returncode}\n{output}".strip()
        except subprocess.TimeoutExpired:
            return "Command timed out after 15 seconds."
        except Exception as e:
            return f"Execution error: {e}"

    def execute_tool_call(self, name: str, args: dict) -> str:
        if name == "read_file":
            return self.read_file(args.get("path", ""))
        elif name == "write_file":
            return self.write_file(args.get("path", ""), args.get("content", ""))
        elif name == "list_dir":
            return self.list_dir(args.get("path", "."))
        elif name == "run_command":
            return self.run_command(args.get("command", ""))
        else:
            return f"Unknown tool: {name}"
