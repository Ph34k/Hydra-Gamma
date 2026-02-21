import asyncio
import os
import uuid
import signal
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, PrivateAttr

from app.tool.base import BaseTool, ToolResult
from app.sandbox.docker import DockerSandbox

class ShellSession(BaseModel):
    id: str
    current_dir: str
    env_vars: Dict[str, str] = Field(default_factory=dict)
    history: List[str] = Field(default_factory=list)
    # Background processes tracking omitted for Docker simplicity for now
    # Ideally we'd map PID to container exec ID, but Docker exec IDs aren't PIDs.

class ShellTool(BaseTool):
    """
    A tool for executing bash commands with persistent sessions.
    Supports secure execution via DockerSandbox (Chapter 19).
    """
    name: str = "shell"
    description: str = """
    Execute bash commands in a persistent shell session.
    Supports foreground execution. Background processes are limited in Docker mode.
    """
    parameters: dict = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["exec", "wait", "send", "kill"],
                "description": "Action to perform (default: exec).",
                "default": "exec"
            },
            "command": {
                "type": "string",
                "description": "The bash command to execute (required for 'exec').",
            },
            "session_id": {
                "type": "string",
                "description": "Session ID to maintain state (optional).",
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds for 'exec' (default 60).",
            }
        },
        "required": [],
    }

    sessions: Dict[str, ShellSession] = Field(default_factory=dict, exclude=True)
    blacklist: List[str] = ["sudo", "reboot", "shutdown", "mount", "rm -rf /"]

    sandbox: Optional[Any] = Field(default=None, exclude=True)

    async def execute(
        self,
        action: str = "exec",
        command: Optional[str] = None,
        session_id: Optional[str] = None,
        timeout: int = 60,
        **kwargs
    ) -> ToolResult:
        if not session_id:
            session_id = await self.create_session()

        if session_id not in self.sessions:
             self.sessions[session_id] = ShellSession(id=session_id, current_dir="/workspace" if self.sandbox else os.getcwd())

        session = self.sessions[session_id]

        if action == "exec":
            if not command:
                return ToolResult(error="Command required for 'exec' action.")
            return await self._exec(session, command, timeout)
        else:
             return ToolResult(error=f"Action {action} not fully supported in this version.")

    async def _exec(self, session: ShellSession, command: str, timeout: int) -> ToolResult:
        # Blacklist check
        cmd_base = command.split()[0] if command else ""
        if cmd_base in self.blacklist:
            return ToolResult(error=f"Command '{cmd_base}' is blacklisted.")

        session.history.append(command)

        # Handle 'cd' specially
        if command.startswith("cd "):
            path = command.split(" ", 1)[1].strip()
            # Resolve path (simplistic resolution)
            if path.startswith("/"):
                new_dir = path
            else:
                new_dir = os.path.join(session.current_dir, path)

            # Verify directory exists?
            # In Docker, we can run 'test -d'
            if self.sandbox:
                exit_code, _ = self.sandbox.exec_run(f"test -d {new_dir}")
                if exit_code == 0:
                    session.current_dir = new_dir
                    return ToolResult(output=f"Changed directory to {new_dir}", system=f"Session ID: {session.id}")
                else:
                    return ToolResult(error=f"Directory not found: {path}")
            else:
                 # Local
                 if os.path.exists(new_dir) and os.path.isdir(new_dir):
                    session.current_dir = new_dir
                    return ToolResult(output=f"Changed directory to {new_dir}", system=f"Session ID: {session.id}")
                 else:
                    return ToolResult(error=f"Directory not found: {path}")

        # Execute
        if self.sandbox:
            # Docker Execution
            # We chain env vars setting if needed?
            # Docker exec_run accepts environment dict.
            # But updating env vars (export X=Y) is tricky in one-off exec.
            # We can capture exports by running command and printing env?
            # For now, simplistic execution.

            try:
                exit_code, output = self.sandbox.exec_run(
                    command,
                    workdir=session.current_dir,
                    timeout=timeout
                )
                if exit_code != 0:
                    return ToolResult(error=f"Command failed with code {exit_code}:\n{output}", system=f"Session ID: {session.id}")
                return ToolResult(output=output, system=f"Session ID: {session.id}")
            except Exception as e:
                return ToolResult(error=f"Docker execution error: {str(e)}")

        else:
            # Local Execution (Legacy fallback)
            try:
                process = await asyncio.create_subprocess_shell(
                    command,
                    cwd=session.current_dir,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    preexec_fn=os.setsid
                )
                try:
                    stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
                    output = stdout.decode().strip()
                    error = stderr.decode().strip()
                    full_output = output + (f"\nSTDERR:\n{error}" if error else "")

                    if process.returncode != 0:
                        return ToolResult(error=f"Command failed:\n{full_output}", system=f"Session ID: {session.id}")
                    return ToolResult(output=full_output, system=f"Session ID: {session.id}")
                except asyncio.TimeoutError:
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                    return ToolResult(error="Command timed out.")
            except Exception as e:
                return ToolResult(error=f"Local execution error: {str(e)}")

    async def create_session(self) -> str:
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = ShellSession(id=session_id, current_dir="/workspace" if self.sandbox else os.getcwd())
        return session_id
