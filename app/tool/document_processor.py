import asyncio
import os
from typing import Optional

from pdfminer.high_level import extract_text as extract_pdf_text
import html2text
from pydantic import Field

from app.llm import LLM
from app.logger import logger
from app.tool.base import BaseTool, ToolResult


class DocumentProcessor(BaseTool):
    name: str = "document_processor"
    description: str = """
    Process documents (PDF, Image, HTML) to extract text or convert to Markdown.
    Uses OCR (via Vision LLM) for images.
    """
    parameters: dict = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["extract_text", "convert_to_markdown"],
                "description": "Action to perform.",
            },
            "path": {
                "type": "string",
                "description": "Path to the document file.",
            },
        },
        "required": ["action", "path"],
    }

    llm: Optional[LLM] = Field(default_factory=LLM)

    async def execute(
        self,
        action: str,
        path: Optional[str] = None,
        **kwargs,
    ) -> ToolResult:
        try:
            if not path:
                return ToolResult(error="Path is required")

            if not os.path.exists(path):
                return ToolResult(error=f"File not found: {path}")

            if action == "extract_text":
                return await self._extract_text(path)
            elif action == "convert_to_markdown":
                return await self._convert_to_markdown(path)
            else:
                return ToolResult(error=f"Unknown action: {action}")
        except Exception as e:
            logger.exception(f"DocumentProcessor error: {e}")
            return ToolResult(error=str(e))

    def _extract_text_sync(self, path: str, ext: str) -> ToolResult:
        try:
            if ext == ".pdf":
                text = extract_pdf_text(path)
                return ToolResult(output=text)
            elif ext in [".html", ".htm"]:
                with open(path, "r") as f:
                    html = f.read()
                h = html2text.HTML2Text()
                h.ignore_links = False
                return ToolResult(output=h.handle(html))
            elif ext in [".txt", ".md"]:
                 with open(path, "r") as f:
                    return ToolResult(output=f.read())
            else:
                return ToolResult(error=f"Unsupported file type for extraction: {ext}")
        except Exception as e:
            return ToolResult(error=f"Extraction failed: {str(e)}")

    async def _extract_text(self, path: str) -> ToolResult:
        ext = os.path.splitext(path)[1].lower()
        if ext in [".png", ".jpg", ".jpeg", ".webp"]:
            return await self._ocr_image(path)

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._extract_text_sync, path, ext)

    async def _convert_to_markdown(self, path: str) -> ToolResult:
        # For now, just alias extract_text as we return text which is markdown-compatible usually
        return await self._extract_text(path)

    async def _ocr_image(self, path: str) -> ToolResult:
        # Use LLM Vision
        import base64

        try:
            with open(path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')

            prompt = "Transcribe the text in this image exactly as it appears."

            message = {
                "role": "user",
                "content": prompt,
                "base64_image": encoded_string
            }

            response = await self.llm.ask([message])
            return ToolResult(output=response)
        except Exception as e:
            return ToolResult(error=f"OCR failed: {str(e)}")
