"""
NEXUS Code Agent.
Specializes in file I/O, code generation, script execution, refactoring, and command-line tasks.
"""

from agents.base_agent import BaseAgent

class CodeAgent(BaseAgent):
    """
    CodeAgent manages local file system modifications, code writing,
    and terminal shell executions.
    """

    def __init__(self, brain, tool_registry):
        super().__init__(brain, tool_registry, name="CodeAgent")
        self.available_tools = ["filesystem", "shell"]

    async def execute(self, user_request: str, plan: str) -> str:
        """
        Execute coding and shell tasks.
        """
        prompt = (
            f"User Goal: {user_request}\n\n"
            f"Execution Plan: {plan}\n\n"
            "You are CodeAgent. You have access to filesystem and shell tools.\n"
            "- To read files: use filesystem tool with args: {\"action\": \"read_file\", \"path\": \"<file_path>\"}\n"
            "- To write files: use filesystem tool with args: {\"action\": \"write_file\", \"path\": \"<file_path>\", \"content\": \"<code/text>\"}\n"
            "- To list directories: use filesystem tool with args: {\"action\": \"list_dir\", \"path\": \"<folder>\"}\n"
            "- To search files: use filesystem tool with args: {\"action\": \"search_files\", \"pattern\": \"*.py\", \"directory\": \".\"}\n"
            "- To execute shell commands: use shell tool with args: {\"command\": \"<cmd>\"}\n\n"
            "Execute the necessary actions to accomplish the goal cleanly and verify any created or modified code."
        )

        return await self.think_with_tools(prompt, self.available_tools, max_steps=6)
