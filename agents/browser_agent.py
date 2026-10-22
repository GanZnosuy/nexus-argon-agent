"""
NEXUS Browser Agent.
Controls headless browser automation to navigate pages, capture screenshots, and interact with web UI.
"""

from agents.base_agent import BaseAgent

class BrowserAgent(BaseAgent):
    """
    BrowserAgent operates Playwright for dynamic web browsing, screenshot capture,
    form filling, and DOM scraping.
    """

    def __init__(self, brain, tool_registry):
        super().__init__(brain, tool_registry, name="BrowserAgent")
        self.available_tools = ["browser"]

    async def execute(self, user_request: str, plan: str) -> str:
        """
        Execute web browsing actions.
        """
        prompt = (
            f"User Goal: {user_request}\n\n"
            f"Execution Plan: {plan}\n\n"
            "You are BrowserAgent. You control headless Chromium through the 'browser' tool.\n"
            "Supported actions:\n"
            "- Navigate to URL: {\"action\": \"navigate\", \"url\": \"<url>\"}\n"
            "- Take screenshot: {\"action\": \"screenshot\", \"url\": \"<url>\", \"save_path\": \"screenshot.png\"}\n"
            "- Click element: {\"action\": \"click\", \"url\": \"<url>\", \"selector\": \"<css_selector>\"}\n"
            "- Fill form: {\"action\": \"fill\", \"url\": \"<url>\", \"selector\": \"<css_selector>\", \"text\": \"<text>\"}\n"
            "- Scrape selector: {\"action\": \"scrape_text\", \"url\": \"<url>\", \"selector\": \"<css_selector>\"}\n\n"
            "Execute the required actions to fulfill the user request and synthesize the findings clearly."
        )

        return await self.think_with_tools(prompt, self.available_tools, max_steps=5)
