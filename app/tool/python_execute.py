import multiprocessing
import sys
import io
import contextlib
from typing import Dict, Optional, Any
from pydantic import Field, PrivateAttr

from app.tool.base import BaseTool
from app.sandbox.docker import DockerSandbox
from app.logger import logger


class PythonExecute(BaseTool):
    """
    A tool for executing Python code.
    Supports secure execution via DockerSandbox (Chapter 16).
    """

    name: str = "python_execute"
    description: str = "Executes Python code. Use print() to output results."
    parameters: dict = {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "The Python code to execute.",
            },
            "timeout": {
                "type": "integer",
                "description": "Execution timeout in seconds.",
                "default": 30
            }
        },
        "required": ["code"],
    }

    # Use PrivateAttr or excluded Field to hold the sandbox reference
    sandbox: Optional[Any] = Field(default=None, exclude=True)

    async def execute(self, code: str, timeout: int = 30, **kwargs) -> Dict[str, Any]:
        """Execute code in sandbox or locally."""
        if self.sandbox:
            return await self._execute_in_sandbox(code, timeout)
        else:
            return await self._execute_local(code, timeout)

    async def _execute_in_sandbox(self, code: str, timeout: int) -> Dict[str, Any]:
        """Execute code using Docker Sandbox."""
        try:
            # Write code to file and run file
            filename = "script.py"
            # Assuming sandbox has write_file and exec_run
            self.sandbox.write_file(filename, code)

            exit_code, output = self.sandbox.exec_run(
                f"python3 {filename}",
                timeout=timeout
            )

            success = (exit_code == 0)
            return {
                "observation": output,
                "success": success
            }
        except Exception as e:
            logger.error(f"Sandbox execution error: {e}")
            return {
                "observation": f"Sandbox execution error: {e}",
                "success": False
            }

    async def _execute_local(self, code: str, timeout: int) -> Dict[str, Any]:
        """Execute code locally (Unsafe fallback)."""
        logger.warning("Executing Python code LOCALLY. Ensure environment is secure.")

        # Use multiprocessing to isolate memory space at least a bit and handle timeout
        with multiprocessing.Manager() as manager:
            result = manager.dict({"observation": "", "success": False})

            # Safe globals?
            safe_globals = {"__builtins__": __builtins__}
            if hasattr(__builtins__, '__dict__'):
                 safe_globals = {"__builtins__": __builtins__.__dict__.copy()}

            p = multiprocessing.Process(target=self._run_code_local, args=(code, result, safe_globals))
            p.start()
            p.join(timeout)

            if p.is_alive():
                p.terminate()
                p.join()
                return {"observation": f"Timeout after {timeout}s", "success": False}

            return dict(result)

    @staticmethod
    def _run_code_local(code: str, result_dict: Dict, globals_dict: Dict):
        """Helper for local execution."""
        output_buffer = io.StringIO()
        try:
            with contextlib.redirect_stdout(output_buffer), contextlib.redirect_stderr(output_buffer):
                exec(code, globals_dict)
            result_dict["observation"] = output_buffer.getvalue()
            result_dict["success"] = True
        except Exception as e:
            result_dict["observation"] = f"{output_buffer.getvalue()}\nError: {e}"
            result_dict["success"] = False
