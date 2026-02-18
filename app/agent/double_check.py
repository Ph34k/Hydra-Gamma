from typing import Any, Callable, Dict, Optional
from pydantic import BaseModel, Field, PrivateAttr
from app.tool.base import BaseTool, ToolResult
from app.utils.logger import logger
from app.tool.bash import Bash

class CriticalActionWrapper(BaseTool):
    """
    A wrapper tool that enforces a 'Double-Check' pattern for critical actions.
    It executes the action, then executes a verification command.
    """
    # Use PrivateAttr for fields that shouldn't be part of the Pydantic schema validation
    # or passed to super().__init__ if they are not in BaseTool.
    _wrapped_tool: BaseTool = PrivateAttr()
    _executor: Optional[BaseTool] = PrivateAttr()

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, wrapped_tool: BaseTool, executor: Optional[BaseTool] = None):
        super().__init__(
            name=wrapped_tool.name,
            description=wrapped_tool.description + " (Includes automated verification step)",
            parameters=wrapped_tool.parameters,
        )
        self._wrapped_tool = wrapped_tool
        self._executor = executor or wrapped_tool

    async def execute(self, **kwargs) -> ToolResult:
        # 1. Action
        logger.info(f"Executing critical action: {self.name} with args {kwargs}")
        result = await self._wrapped_tool.execute(**kwargs)

        if result.error:
            return result

        # 2. Verification Logic
        command = kwargs.get('command', '')
        if not command:
            return result

        verification_cmd = None

        # Determine if it's a bash-like tool
        is_bash = isinstance(self._wrapped_tool, Bash) or self.name.lower() in ['bash', 'terminal', 'shell']

        if is_bash:
             parts = command.strip().split()
             if not parts:
                 return result

             cmd_base = parts[0]

             # Find target argument (simplistic parsing)
             target = ""
             # Check for flags like -rf
             start_idx = 1
             while start_idx < len(parts) and parts[start_idx].startswith("-"):
                 start_idx += 1

             if start_idx < len(parts):
                 target = parts[start_idx]

             # Special case for cp/mv where target is last
             if cmd_base in ['cp', 'mv']:
                 target = parts[-1]

             if cmd_base == 'rm' and target:
                 # Use ls on target. If it fails, that's good (file gone).
                 verification_cmd = f"ls -la {target} 2>&1"
             elif cmd_base == 'mkdir' and target:
                 verification_cmd = f"ls -d {target}"
             elif cmd_base == 'touch' and target:
                 verification_cmd = f"ls -l {target}"
             elif (cmd_base == 'cp' or cmd_base == 'mv') and target:
                 verification_cmd = f"ls -l {target}"

        if verification_cmd and self._executor:
            logger.info(f"Double-Check: Verifying action with: {verification_cmd}")
            try:
                verify_result = await self._executor.execute(command=verification_cmd)

                original_output = str(result.output) if result.output else ""
                verify_output = str(verify_result.output) if verify_result.output else str(verify_result.error)

                combined_output = f"{original_output}\n\n[Double-Check Verification]\nCommand: `{verification_cmd}`\nResult:\n{verify_output}"
                result.output = combined_output

            except Exception as e:
                logger.warning(f"Double-Check Verification step failed to execute: {e}")
                result.output = f"{str(result.output)}\n\n[Double-Check Error] Verification failed to run: {e}"

        return result

def with_double_check(tool: BaseTool, executor: Optional[BaseTool] = None) -> BaseTool:
    """Decorator-like function to wrap a tool with double-check logic."""
    return CriticalActionWrapper(wrapped_tool=tool, executor=executor)
