import asyncio
import os
import tempfile
import shutil
from pathlib import Path
from typing import List, Protocol, Tuple, Union, Optional
from pydantic import BaseModel, Field
from app.exceptions import ToolError
from app.tool.base import BaseTool, ToolResult

PathLike = Union[str, Path]

class EditOperation(BaseModel):
    find: str
    replace: str
    all: bool = False

class FileTool(BaseTool):
    """A tool for safe and atomic file operations."""
    name: str = "file_tool"
    description: str = "Read, write, append, and edit files atomically."
    parameters: dict = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["read", "write", "append", "edit", "list"],
                "description": "The file operation to perform.",
            },
            "path": {
                "type": "string",
                "description": "The file path relative to the workspace.",
            },
            "content": {
                "type": "string",
                "description": "Content to write or append.",
            },
            "edits": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "find": {"type": "string"},
                        "replace": {"type": "string"},
                        "all": {"type": "boolean"},
                    }
                },
                "description": "List of edit operations (find/replace).",
            },
        },
        "required": ["action", "path"],
    }

    base_dir: Path = Field(default_factory=lambda: Path(os.getcwd()))

    def _validate_path(self, path: PathLike) -> Path:
        """Validate that the path is within the base directory."""
        full_path = (self.base_dir / path).resolve()
        if not str(full_path).startswith(str(self.base_dir.resolve())):
             raise ToolError(f"Access denied: {path} is outside the sandbox.")
        return full_path

    async def execute(self, action: str, path: str, content: Optional[str] = None, edits: Optional[List[dict]] = None, **kwargs) -> ToolResult:
        try:
            if action == "read":
                text = await self.read(path)
                return ToolResult(output=text)
            elif action == "write":
                if content is None:
                    return ToolResult(error="Content required for write action")
                await self.write(path, content)
                return ToolResult(output=f"Successfully wrote to {path}")
            elif action == "append":
                if content is None:
                    return ToolResult(error="Content required for append action")
                await self.append(path, content)
                return ToolResult(output=f"Successfully appended to {path}")
            elif action == "edit":
                if edits is None:
                    return ToolResult(error="Edits required for edit action")
                # Parse edits from dict to EditOperation
                edit_ops = [EditOperation(**e) for e in edits]
                await self.edit(path, edit_ops)
                return ToolResult(output=f"Successfully edited {path}")
            elif action == "list":
                files = await self.list_files(path)
                return ToolResult(output="\n".join(files))
            else:
                return ToolResult(error=f"Unknown action: {action}")
        except Exception as e:
            return ToolResult(error=str(e))

    async def read(self, path: PathLike) -> str:
        """Read content from a file."""
        full_path = self._validate_path(path)
        try:
            return full_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            raise ToolError(f"File not found: {path}")
        except Exception as e:
            raise ToolError(f"Failed to read {path}: {str(e)}")

    async def write(self, path: PathLike, content: str) -> None:
        """Write content to a file atomically."""
        full_path = self._validate_path(path)

        # Ensure directory exists
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Atomic write implementation
        tmp_fd, tmp_path = tempfile.mkstemp(dir=self.base_dir, text=True)
        try:
            with os.fdopen(tmp_fd, 'w', encoding="utf-8") as tmp:
                tmp.write(content)
                tmp.flush()
                os.fsync(tmp.fileno())  # Ensure data is on disk

            # Atomic rename
            os.replace(tmp_path, full_path)
        except Exception as e:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise ToolError(f"Failed to write to {path}: {str(e)}")

    async def append(self, path: PathLike, content: str) -> None:
        """Append content to a file."""
        full_path = self._validate_path(path)
        try:
            original = ""
            if full_path.exists():
                 original = full_path.read_text(encoding="utf-8")

            await self.write(path, original + content)
        except Exception as e:
            raise ToolError(f"Failed to append to {path}: {str(e)}")

    async def edit(self, path: PathLike, edits: List[EditOperation]) -> None:
        """Apply a series of find/replace operations to a file."""
        content = await self.read(path)

        for edit in edits:
            if edit.all:
                content = content.replace(edit.find, edit.replace)
            else:
                content = content.replace(edit.find, edit.replace, 1)

        await self.write(path, content)

    async def list_files(self, path: PathLike = ".") -> List[str]:
        """List files in a directory."""
        full_path = self._validate_path(path)
        if not full_path.is_dir():
             if full_path.is_file():
                 return [full_path.name]
             raise ToolError(f"Not a directory: {path}")
        return [p.name for p in full_path.iterdir()]
