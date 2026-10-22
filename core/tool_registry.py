"""
NEXUS Tool Registry.
Central registry for discovering, inspecting, and executing tools across all agents.
"""

from typing import Dict, Any, List, Optional
from rich.console import Console

console = Console()

class ToolRegistry:
    """
    Manages tool lifecycle, registration, and dispatch.
    """

    def __init__(self):
        self._tools: Dict[str, Any] = {}

    def register(self, tool: Any, name: Optional[str] = None):
        """
        Register a tool instance.
        Uses tool.name if name is not explicitly passed.
        """
        tool_name = name or getattr(tool, "name", tool.__class__.__name__.lower())
        self._tools[tool_name] = tool

    def get(self, name: str) -> Optional[Any]:
        """
        Retrieve a registered tool by name.
        """
        return self._tools.get(name)

    def list_tools(self) -> List[Any]:
        """
        Return a list of all registered tool objects.
        """
        return list(self._tools.values())

    def list_names(self) -> List[str]:
        """
        Return names of all registered tools.
        """
        return list(self._tools.keys())

    def get_descriptions(self) -> str:
        """
        Generate a comprehensive summary of available tools for LLM prompts.
        """
        lines = []
        for name, tool in self._tools.items():
            desc = getattr(tool, "description", "No description provided")
            lines.append(f"- {name}: {desc}")
        return "\n".join(lines)

    async def execute(self, tool_name: str, **kwargs) -> str:
        """
        Dispatch a call to a registered tool safely with error wrapping.
        """
        tool = self.get(tool_name)
        if not tool:
            return f"[ERROR] Không tìm thấy công cụ '{tool_name}' trong registry."

        try:
            if hasattr(tool, "run"):
                return await tool.run(**kwargs)
            else:
                return f"[ERROR] Công cụ '{tool_name}' không có hàm 'run'."
        except Exception as e:
            return f"[ERROR khi chạy {tool_name}]: {str(e)}"
