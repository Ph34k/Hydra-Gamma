import os
from typing import Optional

from pydantic import Field

from app.llm import LLM
from app.logger import logger
from app.tool.base import BaseTool, ToolResult


class MediaGenerationTool(BaseTool):
    name: str = "media_generation_tool"
    description: str = """
    Generates media assets: Images (DALL-E/Mock), Slides (Markdown to HTML), and Audio (Mock).
    """
    parameters: dict = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["generate_image", "generate_slides", "generate_audio"],
                "description": "Action to perform.",
            },
            "prompt": {
                "type": "string",
                "description": "Prompt for image generation.",
            },
            "content_path": {
                "type": "string",
                "description": "Path to markdown content for slides.",
            },
            "text": {
                "type": "string",
                "description": "Text for audio generation.",
            },
            "style": {
                "type": "string",
                "enum": ["PHOTOREALISTIC", "CARTOON", "SKETCH"],
                "default": "PHOTOREALISTIC",
                "description": "Style for image generation.",
            },
            "mode": {
                "type": "string",
                "enum": ["HTML", "PDF"],
                "default": "HTML",
                "description": "Output format for slides.",
            },
            "voice_profile": {
                "type": "string",
                "enum": ["MALE", "FEMALE", "NEUTRAL"],
                "default": "NEUTRAL",
                "description": "Voice profile for audio generation.",
            },
        },
        "required": ["action"],
    }

    llm: Optional[LLM] = Field(default_factory=LLM)

    async def execute(
        self,
        action: str,
        prompt: Optional[str] = None,
        content_path: Optional[str] = None,
        text: Optional[str] = None,
        style: str = "PHOTOREALISTIC",
        mode: str = "HTML",
        voice_profile: str = "NEUTRAL",
        **kwargs,
    ) -> ToolResult:
        try:
            if action == "generate_image":
                if not prompt:
                    return ToolResult(error="Prompt required for generate_image")
                return await self._generate_image(prompt, style)
            elif action == "generate_slides":
                if not content_path:
                    return ToolResult(error="Content path required for generate_slides")
                return await self._generate_slides(content_path, mode)
            elif action == "generate_audio":
                if not text:
                    return ToolResult(error="Text required for generate_audio")
                return await self._generate_audio(text, voice_profile)
            else:
                return ToolResult(error=f"Unknown action: {action}")
        except Exception as e:
            logger.exception(f"MediaGenerationTool error: {e}")
            return ToolResult(error=str(e))

    async def _generate_image(self, prompt: str, style: str) -> ToolResult:
        # Mock implementation as we don't have DALL-E keys configured in this environment explicitly
        # In a real implementation, we would call OpenAI Image API
        filename = f"generated_image_{hash(prompt)}.png"
        path = os.path.join(os.getcwd(), "generated_media", filename)
        os.makedirs(os.path.dirname(path), exist_ok=True)

        # Create a placeholder image
        from PIL import Image, ImageDraw

        img = Image.new('RGB', (512, 512), color=(73, 109, 137))
        d = ImageDraw.Draw(img)
        d.text((10,10), f"Image: {prompt[:20]}...", fill=(255,255,0))
        d.text((10,30), f"Style: {style}", fill=(255,255,0))
        img.save(path)

        return ToolResult(output=f"Image generated at {path}")

    async def _generate_slides(self, content_path: str, mode: str) -> ToolResult:
        if not os.path.exists(content_path):
            return ToolResult(error=f"File not found: {content_path}")

        with open(content_path, "r") as f:
            content = f.read()

        # Simple Markdown to HTML Slide conversion (Reveal.js style simplified)
        slides_html = f"""
        <html>
        <head>
            <title>Presentation</title>
            <style>
                body {{ font-family: sans-serif; display: flex; flex-direction: column; align-items: center; }}
                .slide {{ border: 1px solid #ccc; padding: 20px; margin: 20px; width: 800px; height: 600px; overflow: auto; page-break-after: always; }}
            </style>
        </head>
        <body>
        """

        # Split by "---" for slides
        slides = content.split("---")
        import markdown

        for slide in slides:
            html_content = markdown.markdown(slide)
            slides_html += f'<div class="slide">{html_content}</div>'

        slides_html += "</body></html>"

        output_path = content_path.replace(".md", f".{mode.lower()}").replace(".txt", f".{mode.lower()}")
        if output_path == content_path:
            output_path += f".{mode.lower()}"

        if mode == "PDF":
             # Mock PDF conversion
             with open(output_path, "w") as f:
                 f.write(f"PDF content for {content_path}")
        else:
            with open(output_path, "w") as f:
                f.write(slides_html)

        return ToolResult(output=f"Slides generated at {output_path} (Mode: {mode})")

    async def _generate_audio(self, text: str, voice_profile: str) -> ToolResult:
        # Mock implementation
        filename = f"generated_audio_{hash(text)}.mp3"
        path = os.path.join(os.getcwd(), "generated_media", filename)
        os.makedirs(os.path.dirname(path), exist_ok=True)

        with open(path, "w") as f:
            f.write(f"Audio placeholder content using profile {voice_profile}")

        return ToolResult(output=f"Audio generated at {path}")
