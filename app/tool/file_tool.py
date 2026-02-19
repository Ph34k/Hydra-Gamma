import asyncio
import os
import tempfile
import shutil
from pathlib import Path
from typing import List, Protocol, Tuple, Union, Optional
from pydantic import BaseModel
from app.exceptions import ToolError

PathLike = Union[str, Path]

class EditOperation(BaseModel):
    find: str
    replace: str
    all: bool = False

class AtomicFileTool:
    """A tool for safe and atomic file operations."""

    def __init__(self, base_dir: PathLike):
        self.base_dir = Path(base_dir).resolve()

    def _validate_path(self, path: PathLike) -> Path:
        """Validate that the path is within the base directory."""
        full_path = (self.base_dir / path).resolve()
        if not str(full_path).startswith(str(self.base_dir)):
            raise ToolError(f"Access denied: {path} is outside the sandbox.")
        return full_path

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
            # We must read, append, and write atomically to be safe,
            # or rely on OS append if we don't care about atomic replacement of the *whole* file.
            # But "Atomic Write" implies replacement.
            # For append, we can just open in append mode, but it's not atomic in the "replace" sense.
            # Following the chapter 18.3.1, let's do the read-modify-write cycle for true atomicity if needed,
            # but usually append is done directly.
            # However, to support `fsync` and full replacement safety:
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
             raise ToolError(f"Not a directory: {path}")
        return [p.name for p in full_path.iterdir()]
