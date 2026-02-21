import asyncio
import base64
import json
import os
from typing import Any, List, Optional

from playwright.async_api import Browser, BrowserContext, Page, async_playwright
from pydantic import BaseModel, Field, PrivateAttr

from app.config import config
from app.llm import LLM
from app.logger import logger
from app.tool.base import BaseTool, ToolResult


class PageContent(BaseModel):
    url: str
    relevant_links: List[str]
    content: str  # text/html representation
    captcha_detected: bool = False


class BrowserTool(BaseTool):
    name: str = "browser_tool"
    description: str = """
    A comprehensive browser tool for headless navigation and interaction.
    Encapsulates navigation, clicking, typing, and extraction.
    Supports session persistence via task_id.
    Includes robustness features for CAPTCHA detection.
    """
    parameters: dict = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "navigate",
                    "click",
                    "type",
                    "screenshot",
                    "get_element_text",
                    "get_element_html",
                ],
                "description": "The operation to perform.",
            },
            "url": {
                "type": "string",
                "description": "URL for navigation.",
            },
            "intent": {
                "type": "string",
                "enum": ["informational", "transactional", "navigational"],
                "description": "Purpose of navigation.",
            },
            "focus": {
                "type": "string",
                "description": "What to look for on the page (optimizes content).",
            },
            "selector": {
                "type": "string",
                "description": "CSS or XPath selector for interaction. If 'vision_needed', uses Vision model.",
            },
            "text": {
                "type": "string",
                "description": "Text to type.",
            },
            "path": {
                "type": "string",
                "description": "Path to save screenshot.",
            },
            "task_id": {
                "type": "string",
                "description": "Session ID for persistent browser profile.",
                "default": "default",
            },
        },
        "required": ["action"],
    }

    _playwright: Any = PrivateAttr(default=None)
    _browser: Optional[Browser] = PrivateAttr(default=None)
    _context: Optional[BrowserContext] = PrivateAttr(default=None)
    _page: Optional[Page] = PrivateAttr(default=None)
    _lock: asyncio.Lock = PrivateAttr(default_factory=asyncio.Lock)
    llm: Optional[LLM] = Field(default_factory=LLM)

    async def _ensure_initialized(self, task_id: str):
        if self._playwright is None:
            self._playwright = await async_playwright().start()

        if self._context is None:
            # Profile path
            user_data_dir = os.path.expanduser(f"~/.browser_profiles/{task_id}")
            os.makedirs(user_data_dir, exist_ok=True)

            # Launch persistent context
            try:
                self._context = await self._playwright.chromium.launch_persistent_context(
                    user_data_dir,
                    headless=True,
                    args=["--disable-blink-features=AutomationControlled"],  # Stealth
                    viewport={"width": 1280, "height": 720},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                )
            except Exception as e:
                 logger.error(f"Failed to launch persistent context: {e}")
                 # Fallback to non-persistent if locking fails or other issue
                 browser = await self._playwright.chromium.launch(headless=True)
                 self._context = await browser.new_context()

            self._page = self._context.pages[0] if self._context.pages else await self._context.new_page()

    async def _detect_captcha(self) -> bool:
        """Simple heuristic for CAPTCHA detection."""
        try:
            content = await self._page.content()
            if "captcha" in content.lower() or "recaptcha" in content.lower() or "cloudflare" in content.lower():
                # Verify if it's visible or blocking
                # This is a simplification; robust detection would need more checks
                return True
        except:
            pass
        return False

    async def _resolve_selector_with_vision(self, description: str) -> Optional[str]:
        """
        Stub for Vision-based selector resolution (Chapter 21.3).
        Takes a screenshot and asks a Vision Model to locate the element.
        """
        # 1. Take screenshot
        screenshot_bytes = await self._page.screenshot()
        # 2. Call Vision Model (e.g., GPT-4o) with image + description
        # 3. Model returns coordinates or improved selector

        # Placeholder implementation
        logger.info(f"Vision selector resolution requested for: {description}")
        return None # Not fully implemented without Vision API key in this context

    async def execute(
        self,
        action: str,
        url: Optional[str] = None,
        intent: Optional[str] = None,
        focus: Optional[str] = None,
        selector: Optional[str] = None,
        text: Optional[str] = None,
        path: Optional[str] = None,
        task_id: str = "default",
        **kwargs,
    ) -> ToolResult:
        async with self._lock:
            try:
                await self._ensure_initialized(task_id)
                if not self._page:
                    return ToolResult(error="Browser page not initialized")

                # Check for CAPTCHA before any action
                if await self._detect_captcha():
                     return ToolResult(
                         error="CAPTCHA detected. User intervention required.",
                         output="Please solve the CAPTCHA manually or use a different source."
                     )

                # Vision Selector Handling
                if selector and selector.startswith("vision:"):
                    vision_selector = await self._resolve_selector_with_vision(selector[7:])
                    if vision_selector:
                        selector = vision_selector
                    else:
                        # Fallback or error
                        pass # proceed with original string maybe it's valid, or fail

                if action == "navigate":
                    if not url:
                        return ToolResult(error="URL required for navigate")
                    return await self._navigate(url, intent, focus)
                elif action == "click":
                    if not selector:
                        return ToolResult(error="Selector required for click")
                    return await self._click(selector)
                elif action == "type":
                    if not selector or text is None:
                        return ToolResult(error="Selector and text required for type")
                    return await self._type(selector, text)
                elif action == "screenshot":
                    if not path:
                        return ToolResult(error="Path required for screenshot")
                    return await self._screenshot(path)
                elif action == "get_element_text":
                    if not selector:
                        return ToolResult(error="Selector required for get_element_text")
                    return await self._get_element_text(selector)
                elif action == "get_element_html":
                    if not selector:
                        return ToolResult(error="Selector required for get_element_html")
                    return await self._get_element_html(selector)
                else:
                    return ToolResult(error=f"Unknown action: {action}")

            except Exception as e:
                logger.exception(f"BrowserTool action '{action}' failed")
                return ToolResult(error=f"Error executing {action}: {str(e)}")

    async def _navigate(self, url: str, intent: Optional[str], focus: Optional[str]) -> ToolResult:
        try:
            response = await self._page.goto(url, wait_until="domcontentloaded")
            if not response:
                 return ToolResult(error="Navigation failed, no response")

            if response.status == 401 or "login" in response.url:
                 logger.warning(f"Possible session expiration/login required at {url}")

            await self._page.evaluate("""() => {
                const elements = document.querySelectorAll('script, style, meta, noscript, iframe');
                elements.forEach(el => el.remove());
            }""")

            content = await self._page.content()
            links = await self._page.evaluate("""() => {
                return Array.from(document.querySelectorAll('a[href]'))
                    .map(a => a.href)
                    .slice(0, 50);
            }""")

            if focus:
                text_content = await self._page.evaluate("document.body.innerText")
                truncated_text = text_content[:10000]
                prompt = f"""
                Analyze the following web page content and extract the section relevant to: "{focus}".
                Return only the relevant text.

                Content:
                {truncated_text}
                """
                try:
                    summary = await self.llm.ask([{"role": "user", "content": prompt}])
                    content = summary
                except Exception as llm_e:
                    logger.warning(f"LLM extraction failed: {llm_e}")
                    content = text_content[:2000]
            else:
                 content = await self._page.evaluate("document.body.innerText")
                 content = content[:5000]

            captcha = await self._detect_captcha()
            page_content = PageContent(url=self._page.url, relevant_links=links, content=content, captcha_detected=captcha)

            return ToolResult(output=page_content.model_dump_json(indent=2))

        except Exception as e:
            return ToolResult(error=f"Navigation failed: {str(e)}")

    async def _click(self, selector: str) -> ToolResult:
        try:
            await self._page.click(selector)
            return ToolResult(output="true")
        except Exception as e:
            return ToolResult(error=f"Click failed: {str(e)}")

    async def _type(self, selector: str, text: str) -> ToolResult:
        try:
            await self._page.fill(selector, text)
            return ToolResult(output="true")
        except Exception as e:
            return ToolResult(error=f"Type failed: {str(e)}")

    async def _screenshot(self, path: str) -> ToolResult:
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            await self._page.screenshot(path=path)
            return ToolResult(output=f"Screenshot saved to {path}")
        except Exception as e:
            return ToolResult(error=f"Screenshot failed: {str(e)}")

    async def _get_element_text(self, selector: str) -> ToolResult:
        try:
            text = await self._page.inner_text(selector)
            return ToolResult(output=text)
        except Exception as e:
            return ToolResult(error=f"Get text failed: {str(e)}")

    async def _get_element_html(self, selector: str) -> ToolResult:
        try:
            html = await self._page.inner_html(selector)
            return ToolResult(output=html)
        except Exception as e:
            return ToolResult(error=f"Get HTML failed: {str(e)}")

    async def cleanup(self):
        if self._context:
            await self._context.close()
        if self._playwright:
            await self._playwright.stop()
