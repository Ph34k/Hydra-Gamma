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
            "start_line": {
                "type": "integer",
                "description": "Start line for reading (1-based, inclusive).",
            },
            "end_line": {
                "type": "integer",
                "description": "End line for reading (1-based, inclusive).",
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

    async def execute(self, action: str, path: str, content: Optional[str] = None, edits: Optional[List[dict]] = None, start_line: Optional[int] = None, end_line: Optional[int] = None, **kwargs) -> ToolResult:
        try:
            if action == "read":
                text = await self.read(path, start_line, end_line)
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

    async def read(self, path: PathLike, start_line: Optional[int] = None, end_line: Optional[int] = None) -> str:
        """Read content from a file, optionally restricted to a line range."""
        full_path = self._validate_path(path)
        try:
            content = full_path.read_text(encoding="utf-8")
            if start_line is None and end_line is None:
                return content

            lines = content.splitlines()
            total_lines = len(lines)

            # Default indices
            start_idx = 0
            end_idx = total_lines

            if start_line is not None:
                if start_line < 1:
                     raise ToolError("start_line must be >= 1")
                start_idx = start_line - 1

            if end_line is not None:
                 end_idx = end_line

            # Slice lines
            selected_lines = lines[start_idx:end_idx]

            # Add line numbers for context if range is used
            result = []
            for i, line in enumerate(selected_lines):
                current_line_num = start_idx + i + 1
                result.append(f"{current_line_num:4d} | {line}")

            return "\n".join(result)

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
