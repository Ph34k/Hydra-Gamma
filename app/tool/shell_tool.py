import asyncio
import os
import uuid
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from app.exceptions import ToolError
from app.tool.base import BaseTool, ToolResult

class ShellSession(BaseModel):
    id: str
    current_dir: str
    history: List[str] = Field(default_factory=list)
    pid: Optional[int] = None

class ShellTool(BaseTool):
    """A tool for executing bash commands with persistent sessions."""
    name: str = "shell"
    description: str = "Execute bash commands in a persistent shell session. Use this for running tests, managing files, and git operations."
    parameters: dict = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The bash command to execute.",
            },
            "session_id": {
                "type": "string",
                "description": "Session ID to maintain state (optional).",
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds (default 60).",
            },
        },
        "required": ["command"],
    }

    sessions: Dict[str, ShellSession] = Field(default_factory=dict, exclude=True)
    _processes: Dict[str, asyncio.subprocess.Process] = {}

    blacklist: List[str] = ["sudo", "reboot", "shutdown", "mount", "rm -rf /"]

    async def execute(self, command: str, session_id: Optional[str] = None, timeout: int = 60, **kwargs) -> ToolResult:
        if not session_id:
            session_id = await self.create_session()

        if session_id not in self.sessions:
             # Auto-create if not found (or return error?)
             # For smoother UX, let's create a new one if not found, but warn?
             # Better to just create one if missing for now.
             self.sessions[session_id] = ShellSession(id=session_id, current_dir=os.getcwd())

        session = self.sessions[session_id]

        # Blacklist check
        cmd_base = command.split()[0] if command else ""
        if cmd_base in self.blacklist:
            return ToolResult(error=f"Command '{cmd_base}' is blacklisted.")

        session.history.append(command)

        # Handle 'cd' specially
        if command.startswith("cd "):
            path = command.split(" ", 1)[1].strip()
            # Handle relative paths correctly
            new_dir = os.path.abspath(os.path.join(session.current_dir, path))
            if os.path.exists(new_dir) and os.path.isdir(new_dir):
                session.current_dir = new_dir
                return ToolResult(output=f"Changed directory to {new_dir}", system=f"Session ID: {session_id}")
            else:
                return ToolResult(error=f"Directory not found: {path}")

        try:
            process = await asyncio.create_subprocess_shell(
                command,
                cwd=session.current_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                preexec_fn=os.setsid
            )

            # Store process? complex with async execution model of ToolCallAgent...
            # For now, just wait for result.

            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
                output = stdout.decode().strip()
                error = stderr.decode().strip()

                # Combine output
                full_output = output
                if error:
                     full_output += f"\nSTDERR:\n{error}"

                if process.returncode != 0:
                     return ToolResult(error=f"Command failed with code {process.returncode}:\n{full_output}", system=f"Session ID: {session_id}")

                return ToolResult(output=full_output if full_output else "Success (No Output)", system=f"Session ID: {session_id}")

            except asyncio.TimeoutError:
                try:
                    process.kill()
                except:
                    pass
                return ToolResult(error=f"Command timed out after {timeout} seconds.")

        except Exception as e:
            return ToolResult(error=f"Execution exception: {str(e)}")

    async def create_session(self) -> str:
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = ShellSession(id=session_id, current_dir=os.getcwd())
        return session_id
