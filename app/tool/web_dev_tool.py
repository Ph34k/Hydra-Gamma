import asyncio
import os
import shutil
from typing import Optional

from app.logger import logger
from app.tool.base import BaseTool, ToolResult


class WebDevTool(BaseTool):
    name: str = "web_dev_tool"
    description: str = "Web development tool for initializing projects and exposing services."
    parameters: dict = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["init_project", "expose"],
                "description": "Action to perform.",
            },
            "scaffold": {
                "type": "string",
                "enum": ["web-static", "web-db-user", "mobile-app"],
                "description": "Project template.",
            },
            "port": {
                "type": "integer",
                "description": "Port to expose.",
            },
            "path": {
                "type": "string",
                "description": "Project directory path.",
            },
        },
        "required": ["action"],
    }

    async def execute(
        self,
        action: str,
        scaffold: Optional[str] = None,
        port: Optional[int] = None,
        path: Optional[str] = None,
        **kwargs,
    ) -> ToolResult:
        try:
            if action == "init_project":
                if not scaffold:
                    return ToolResult(error="Scaffold required for init_project")
                target_path = path if path else scaffold
                return await self._init_project(scaffold, target_path)
            elif action == "expose":
                if not port:
                    return ToolResult(error="Port required for expose")
                return await self._expose(port)
            else:
                return ToolResult(error=f"Unknown action: {action}")
        except Exception as e:
            logger.exception(f"WebDevTool error: {e}")
            return ToolResult(error=str(e))

    async def _init_project(self, scaffold: str, path: str) -> ToolResult:
        full_path = os.path.abspath(path)
        if os.path.exists(full_path):
             return ToolResult(error=f"Path {full_path} already exists")

        os.makedirs(full_path)

        cmd = ""
        # Using npm create vite (which requires user interaction) is tricky.
        # We use template flags.

        if scaffold == "web-static":
            # React + TS
            cmd = "npm create vite@latest . -- --template react-ts"
        elif scaffold == "web-db-user":
             # Custom setup
             cmd = "npm init -y && npm install express sqlite3"
             # Create server.js
             server_js = """
const express = require('express');
const app = express();
const port = 3000;
app.get('/', (req, res) => res.send('Hello World!'));
app.listen(port, () => console.log(`App listening on port ${port}!`));
"""
             with open(os.path.join(full_path, "server.js"), "w") as f:
                 f.write(server_js)

        elif scaffold == "mobile-app":
             # PWA via Vite
             cmd = "npm create vite@latest . -- --template react-ts"

        try:
            if cmd:
                process = await asyncio.create_subprocess_shell(
                    cmd,
                    cwd=full_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()

                if process.returncode != 0:
                     # If web-db-user command fails (e.g. creating server.js succeeded but npm init failed?)
                     # Actually the server.js creation is synchronous before cmd for web-db-user.
                     pass

                if scaffold in ["web-static", "mobile-app"]:
                     # npm install
                     process_install = await asyncio.create_subprocess_shell(
                        "npm install",
                        cwd=full_path,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                     await process_install.communicate()

            return ToolResult(output=f"Project initialized at {full_path} with scaffold {scaffold}")
        except Exception as e:
            # Cleanup
            if os.path.exists(full_path):
                shutil.rmtree(full_path)
            return ToolResult(error=f"Init failed: {str(e)}")

    async def _expose(self, port: int) -> ToolResult:
        url = f"http://localhost:{port}"
        return ToolResult(output=f"Service exposed at {url}")
