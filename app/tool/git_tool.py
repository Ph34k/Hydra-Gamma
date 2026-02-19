import asyncio
import re
from typing import List, Optional

from app.logger import logger
from app.tool.base import BaseTool, ToolResult


class GitTool(BaseTool):
    name: str = "git_tool"
    description: str = "Git and GitHub integration tool for version control and collaboration."
    parameters: dict = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["clone", "add", "commit", "push", "checkout", "pr_create"],
                "description": "Git action to perform.",
            },
            "repo_url": {
                "type": "string",
                "description": "Repository URL for clone.",
            },
            "message": {
                "type": "string",
                "description": "Commit message (must follow Conventional Commits).",
            },
            "branch": {
                "type": "string",
                "description": "Branch name.",
            },
            "title": {
                "type": "string",
                "description": "PR title.",
            },
            "body": {
                "type": "string",
                "description": "PR body.",
            },
        },
        "required": ["action"],
    }

    async def execute(
        self,
        action: str,
        repo_url: Optional[str] = None,
        message: Optional[str] = None,
        branch: Optional[str] = None,
        title: Optional[str] = None,
        body: Optional[str] = None,
        **kwargs,
    ) -> ToolResult:
        try:
            if action == "clone":
                if not repo_url:
                    return ToolResult(error="Repo URL required for clone")
                return await self._run_cmd(["git", "clone", repo_url])
            elif action == "add":
                return await self._run_cmd(["git", "add", "."])
            elif action == "commit":
                if not message:
                    return ToolResult(error="Message required for commit")
                if not self._validate_conventional_commit(message):
                    return ToolResult(error="Commit message must follow Conventional Commits (e.g., 'feat: description')")
                return await self._run_cmd(["git", "commit", "-m", message])
            elif action == "push":
                args = ["git", "push"]
                if branch:
                    args.extend(["origin", branch])
                return await self._run_cmd(args)
            elif action == "checkout":
                if not branch:
                    return ToolResult(error="Branch required for checkout")
                # Try creating new branch first
                res = await self._run_cmd(["git", "checkout", "-b", branch])
                if res.error:
                    # Fallback to checking out existing
                    res = await self._run_cmd(["git", "checkout", branch])
                return res
            elif action == "pr_create":
                if not title or not body:
                    return ToolResult(error="Title and body required for PR")
                return await self._run_cmd(["gh", "pr", "create", "--title", title, "--body", body])
            else:
                return ToolResult(error=f"Unknown action: {action}")
        except Exception as e:
            logger.exception(f"GitTool error: {e}")
            return ToolResult(error=str(e))

    async def _run_cmd(self, args: List[str]) -> ToolResult:
        try:
            process = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            output = stdout.decode().strip()
            error = stderr.decode().strip()

            if process.returncode != 0:
                # Git often outputs to stderr even on success (e.g. checkout), check returncode
                return ToolResult(error=f"Command failed: {error or output}")

            return ToolResult(output=output if output else "Success")
        except FileNotFoundError:
             return ToolResult(error=f"Command not found: {args[0]}")

    def _validate_conventional_commit(self, message: str) -> bool:
        # Regex for Conventional Commits
        pattern = r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\(.+\))?: .+"
        return bool(re.match(pattern, message))
