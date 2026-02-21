import asyncio
import os
import uuid
import signal
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, PrivateAttr

from app.exceptions import ToolError
from app.tool.base import BaseTool, ToolResult

class ShellSession(BaseModel):
    id: str
    current_dir: str
    history: List[str] = Field(default_factory=list)
    # Store active background processes (PID -> Process)
    # Note: Process objects are not serializable, so we exclude/private them
    _processes: Dict[int, asyncio.subprocess.Process] = PrivateAttr(default_factory=dict)

    def add_process(self, pid: int, process: asyncio.subprocess.Process):
        self._processes[pid] = process

    def get_process(self, pid: int) -> Optional[asyncio.subprocess.Process]:
        return self._processes.get(pid)

    def remove_process(self, pid: int):
        if pid in self._processes:
            del self._processes[pid]

class ShellTool(BaseTool):
    """A tool for executing bash commands with persistent sessions."""
    name: str = "shell"
    description: str = """
    Execute bash commands in a persistent shell session.
    Supports foreground execution, background processes (&), waiting, input sending, and killing processes.
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
                "description": "Timeout in seconds for 'exec' or 'wait' (default 60).",
            },
            "pid": {
                "type": "integer",
                "description": "Process ID for 'wait', 'send', or 'kill'.",
            },
            "text": {
                "type": "string",
                "description": "Text input for 'send' action.",
            }
        },
        "required": [], # Action defaults to exec, command required if exec
    }

    sessions: Dict[str, ShellSession] = Field(default_factory=dict, exclude=True)
    blacklist: List[str] = ["sudo", "reboot", "shutdown", "mount", "rm -rf /"]

    async def execute(
        self,
        action: str = "exec",
        command: Optional[str] = None,
        session_id: Optional[str] = None,
        timeout: int = 60,
        pid: Optional[int] = None,
        text: Optional[str] = None,
        **kwargs
    ) -> ToolResult:
        if not session_id:
            session_id = await self.create_session()

        if session_id not in self.sessions:
             self.sessions[session_id] = ShellSession(id=session_id, current_dir=os.getcwd())

        session = self.sessions[session_id]

        if action == "exec":
            if not command:
                return ToolResult(error="Command required for 'exec' action.")
            return await self._exec(session, command, timeout)
        elif action == "wait":
            if pid is None:
                return ToolResult(error="PID required for 'wait' action.")
            return await self._wait(session, pid, timeout)
        elif action == "send":
            if pid is None or text is None:
                return ToolResult(error="PID and text required for 'send' action.")
            return await self._send(session, pid, text)
        elif action == "kill":
            if pid is None:
                return ToolResult(error="PID required for 'kill' action.")
            return await self._kill(session, pid)
        else:
             # Fallback for backward compatibility if action is missing but command is present
             if command:
                 return await self._exec(session, command, timeout)
             return ToolResult(error=f"Unknown action: {action}")

    async def _exec(self, session: ShellSession, command: str, timeout: int) -> ToolResult:
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
                return ToolResult(output=f"Changed directory to {new_dir}", system=f"Session ID: {session.id}")
            else:
                return ToolResult(error=f"Directory not found: {path}")

        # Check for background execution
        is_background = False
        if command.strip().endswith("&"):
            is_background = True
            command = command.strip()[:-1].strip()

        try:
            # We use setsid to allow killing the whole process group later if needed
            process = await asyncio.create_subprocess_shell(
                command,
                cwd=session.current_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.PIPE, # Open stdin for potential 'send'
                preexec_fn=os.setsid
            )

            if is_background:
                session.add_process(process.pid, process)
                return ToolResult(output=f"Started background process with PID: {process.pid}", system=f"Session ID: {session.id}")

            # Foreground execution
            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
                output = stdout.decode().strip()
                error = stderr.decode().strip()

                full_output = output
                if error:
                     full_output += f"\nSTDERR:\n{error}"

                if process.returncode != 0:
                     return ToolResult(error=f"Command failed with code {process.returncode}:\n{full_output}", system=f"Session ID: {session.id}")

                return ToolResult(output=full_output if full_output else "Success (No Output)", system=f"Session ID: {session.id}")

            except asyncio.TimeoutError:
                try:
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                except:
                    pass
                return ToolResult(error=f"Command timed out after {timeout} seconds.")

        except Exception as e:
            return ToolResult(error=f"Execution exception: {str(e)}")

    async def _wait(self, session: ShellSession, pid: int, timeout: int) -> ToolResult:
        process = session.get_process(pid)
        if not process:
            return ToolResult(error=f"Process {pid} not found in session {session.id}")

        try:
            # We assume stdout/stderr capture is not possible for background process unless piped to file
            # But asyncio process object might buffer it if we didn't consume it?
            # Actually, if we didn't await communicate(), the pipes are still open.
            # We can try to read them.

            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
            session.remove_process(pid)

            output = stdout.decode().strip()
            error = stderr.decode().strip()

            full_output = output
            if error:
                 full_output += f"\nSTDERR:\n{error}"

            return ToolResult(output=f"Process {pid} finished:\n{full_output}", system=f"Session ID: {session.id}")

        except asyncio.TimeoutError:
            return ToolResult(error=f"Wait timed out for PID {pid} after {timeout} seconds.")
        except Exception as e:
            return ToolResult(error=f"Wait failed: {str(e)}")

    async def _send(self, session: ShellSession, pid: int, text: str) -> ToolResult:
        process = session.get_process(pid)
        if not process:
            return ToolResult(error=f"Process {pid} not found in session {session.id}")

        if not process.stdin:
            return ToolResult(error=f"Process {pid} does not have open stdin.")

        try:
            process.stdin.write(text.encode())
            await process.stdin.drain()
            return ToolResult(output=f"Sent text to PID {pid}", system=f"Session ID: {session.id}")
        except Exception as e:
            return ToolResult(error=f"Send failed: {str(e)}")

    async def _kill(self, session: ShellSession, pid: int) -> ToolResult:
        # Check if it's a managed background process
        process = session.get_process(pid)
        if process:
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                session.remove_process(pid)
                return ToolResult(output=f"Killed managed process {pid}", system=f"Session ID: {session.id}")
            except Exception as e:
                return ToolResult(error=f"Failed to kill managed process {pid}: {str(e)}")

        # Try to kill arbitrary PID if allowed (dangerous?)
        # For now, restrict to managed processes or implement generic kill if needed
        # Chapter 19 mentions kill tool, implies generic.
        try:
            os.kill(pid, signal.SIGKILL)
            return ToolResult(output=f"Killed process {pid}", system=f"Session ID: {session.id}")
        except Exception as e:
            return ToolResult(error=f"Failed to kill process {pid}: {str(e)}")

    async def create_session(self) -> str:
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = ShellSession(id=session_id, current_dir=os.getcwd())
        return session_id
