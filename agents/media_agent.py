"""
NEXUS Media Agent.
Produces multimedia assets including AI images, voiceover audio, and video synthesis via FFmpeg.
"""

from agents.base_agent import BaseAgent

class MediaAgent(BaseAgent):
    """
    MediaAgent orchestrates image generation, speech audio creation (TTS),
    and multimedia assembly using FFmpeg.
    """

    def __init__(self, brain, tool_registry):
        super().__init__(brain, tool_registry, name="MediaAgent")
        self.available_tools = ["image_generator", "tts", "shell"]

    async def execute(self, user_request: str, plan: str) -> str:
        """
        Execute media generation and composition tasks.
        """
        prompt = (
            f"User Goal: {user_request}\n\n"
            f"Execution Plan: {plan}\n\n"
            "You are MediaAgent. You have access to:\n"
            "1. 'image_generator':\n"
            "   - Args: {\"prompt\": \"<detailed description>\", \"output\": \"<filename.png>\"}\n"
            "2. 'tts':\n"
            "   - Args: {\"action\": \"edge_tts\", \"text\": \"<content>\", \"voice\": \"vi-VN-NamMinhNeural\", \"rate\": \"+18%\", \"output\": \"<audio.mp3>\"}\n"
            "   - Args: {\"action\": \"elevenlabs\", \"text\": \"<content>\", \"output\": \"<audio.mp3>\"}\n"
            "3. 'shell':\n"
            "   - Run ffmpeg commands to combine audio, images, or edit videos:\n"
            "     Args: {\"command\": \"ffmpeg -y -loop 1 -i image.png -i voice.mp3 -c:v libx264 -tune stillimage -c:a aac -b:a 192k -pix_fmt yuv420p -shortest output.mp4\"}\n\n"
            "Execute the media production pipeline cleanly and verify that the generated files exist."
        )

        return await self.think_with_tools(prompt, self.available_tools, max_steps=6)
