"""
NEXUS YouTube Agent.
Manages YouTube channel analytics, video statistics retrieval, metadata optimization, and content research.
"""

from agents.base_agent import BaseAgent

class YouTubeAgent(BaseAgent):
    """
    YouTubeAgent handles interactions with YouTube Data API and video research.
    """

    def __init__(self, brain, tool_registry):
        super().__init__(brain, tool_registry, name="YouTubeAgent")
        self.available_tools = ["youtube_api", "web_search"]

    async def execute(self, user_request: str, plan: str) -> str:
        """
        Execute YouTube operations and video analytics tracking.
        """
        prompt = (
            f"User Goal: {user_request}\n\n"
            f"Execution Plan: {plan}\n\n"
            "You are YouTubeAgent. You have access to:\n"
            "1. 'youtube_api':\n"
            "   - Get video analytics/views/likes: {\"action\": \"get_analytics\", \"video_id\": \"<video_id_or_url>\"}\n"
            "   - List channel videos: {\"action\": \"list_videos\", \"channel_id\": \"<channel_id>\", \"max_results\": 10}\n"
            "   - Search videos: {\"action\": \"list_videos\", \"query\": \"<keywords>\", \"max_results\": 10}\n"
            "2. 'web_search':\n"
            "   - YouTube Search: {\"action\": \"youtube_search\", \"query\": \"<keywords>\", \"max_results\": 5}\n\n"
            "Execute the requested operation and summarize the findings or metrics clearly."
        )

        return await self.think_with_tools(prompt, self.available_tools, max_steps=5)
