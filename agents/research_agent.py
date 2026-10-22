"""
NEXUS Research Agent.
Specializes in search engine queries, gathering information from web pages and YouTube,
and cross-referencing information to compile comprehensive research summaries.
"""

from agents.base_agent import BaseAgent

class ResearchAgent(BaseAgent):
    """
    ResearchAgent gathers intelligence, searches the web, analyzes articles,
    and returns synthesized knowledge.
    """

    def __init__(self, brain, tool_registry):
        super().__init__(brain, tool_registry, name="ResearchAgent")
        self.available_tools = ["web_search", "browser"]

    async def execute(self, user_request: str, plan: str) -> str:
        """
        Execute research operations across web and video sources.
        """
        prompt = (
            f"User Goal: {user_request}\n\n"
            f"Execution Plan: {plan}\n\n"
            "You are ResearchAgent. You have access to the following tools:\n"
            "1. 'web_search':\n"
            "   - Web Search: {\"action\": \"search\", \"query\": \"<keywords>\", \"max_results\": 10}\n"
            "   - YouTube Search: {\"action\": \"youtube_search\", \"query\": \"<keywords>\", \"max_results\": 5}\n"
            "   - Read URL: {\"action\": \"read_url\", \"url\": \"<url>\"}\n"
            "2. 'browser' (for dynamic sites or screenshot verification):\n"
            "   - Navigate: {\"action\": \"navigate\", \"url\": \"<url>\"}\n\n"
            "Perform search queries, inspect relevant articles, and produce an objective, well-structured research report."
        )

        return await self.think_with_tools(prompt, self.available_tools, max_steps=6)
