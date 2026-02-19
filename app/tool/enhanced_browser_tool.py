from typing import List, Optional
from pydantic import BaseModel
from app.tool.browser_use_tool import BrowserUseTool as OriginalBrowserUseTool

class PageContent(BaseModel):
    url: str
    content: str
    relevant_links: List[str]

class EnhancedBrowserUseTool(OriginalBrowserUseTool):
    """Enhanced Browser Tool with Intent and Focus."""

    intent: Optional[str] = None
    focus: Optional[str] = None

    async def navigate(self, url: str, intent: Optional[str] = None, focus: Optional[str] = None) -> PageContent:
        """Enhanced navigation with intent and focus extraction."""
        self.intent = intent
        self.focus = focus

        result = await self.execute(action="go_to_url", url=url)
        if result.error:
            raise ToolError(result.error)

        # Get content
        page_content_result = await self.execute(action="extract_content", goal=self.focus or "Summarize the page")
        if page_content_result.error:
             raise ToolError(page_content_result.error)

        return PageContent(
            url=url,
            content=page_content_result.output,
            relevant_links=[] # Simplified for now
        )
