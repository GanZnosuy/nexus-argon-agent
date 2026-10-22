"""
NEXUS Base Agent.
Abstract base class defining interface and multi-step tool execution loop for all agents.
"""

from abc import ABC, abstractmethod
import json
import re
from typing import List, Dict, Any, Optional
from rich.console import Console

import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

console = Console(legacy_windows=False)

class BaseAgent(ABC):
    """
    Abstract Base Agent equipped with the Brain and Tool Registry.
    """

    def __init__(self, brain, tool_registry, name: str = "BaseAgent"):
        self.brain = brain
        self.tools = tool_registry
        self.name = name

    @abstractmethod
    async def execute(self, user_request: str, plan: str) -> str:
        """
        Execute the agent's task and return the final response string.
        """
        pass

    def _clean_json_string(self, text: str) -> str:
        """Extract JSON substring even if enclosed in markdown code fences or surrounded by text."""
        cleaned = text.strip()
        # Remove ```json and ```
        if "```json" in cleaned:
            match = re.search(r"```json\s*(.*?)\s*```", cleaned, re.DOTALL)
            if match:
                return match.group(1).strip()
        elif "```" in cleaned:
            match = re.search(r"```\s*(.*?)\s*```", cleaned, re.DOTALL)
            if match:
                return match.group(1).strip()

        # Find first { and last }
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            return cleaned[start:end+1]

        return cleaned

    def _parse_json(self, text: str) -> Optional[Dict[str, Any]]:
        """Safely parse JSON from LLM output."""
        try:
            cleaned = self._clean_json_string(text)
            return json.loads(cleaned)
        except Exception:
            return None

    async def think_with_tools(self, prompt: str, available_tool_names: List[str], max_steps: int = 5) -> str:
        """
        Multi-turn reasoning and tool execution loop.
        Allows the agent to plan, invoke tools, inspect outputs, and conclude.
        """
        tool_objects = [self.tools.get(name) for name in available_tool_names if self.tools.get(name)]
        if not tool_objects:
            return await self.brain.think(prompt)

        descriptions = "\n".join(
            f"- {getattr(t, 'name', 'tool')}: {getattr(t, 'description', '')}"
            for t in tool_objects
        )

        history = f"Available Tools:\n{descriptions}\n\nTask Goal:\n{prompt}\n"

        for step in range(1, max_steps + 1):
            decision_prompt = (
                f"{history}\n"
                f"[Step {step}/{max_steps}]\n"
                "Decide the next action. Respond ONLY with a valid JSON object matching one of these formats:\n"
                'Format 1 (Invoke tool): {"tool": "<tool_name>", "args": {<arguments>}}\n'
                'Format 2 (Complete task): {"tool": "none", "answer": "<final answer or summary>"}\n'
            )

            raw_response = await self.brain.think(
                decision_prompt,
                system_prompt=(
                    f"You are {self.name}. Always output strictly valid JSON without explanation or commentary."
                )
            )

            parsed = self._parse_json(raw_response)
            if not parsed or not isinstance(parsed, dict) or "tool" not in parsed:
                # If cannot parse JSON, treat as final answer
                return raw_response

            tool_name = parsed.get("tool", "none")
            if tool_name == "none" or not tool_name:
                return parsed.get("answer", raw_response)

            args = parsed.get("args", {})
            if not isinstance(args, dict):
                args = {}

            console.print(f"  [cyan]🔧 [{self.name}][/] Gọi công cụ [bold]{tool_name}[/] với args: {args}")

            tool = self.tools.get(tool_name)
            if not tool:
                tool_output = f"[ERROR] Không tìm thấy công cụ '{tool_name}'"
            else:
                try:
                    if hasattr(tool, "run"):
                        tool_output = await tool.run(**args)
                    else:
                        tool_output = f"[ERROR] Công cụ '{tool_name}' không hỗ trợ method run"
                except Exception as e:
                    tool_output = f"[ERROR Tool Exception]: {str(e)}"

            truncated_output = tool_output[:2500] if len(tool_output) > 2500 else tool_output
            history += f"\n[Step {step} Tool Result for {tool_name}]:\n{truncated_output}\n"

        # If reached max steps, ask for final synthesis
        final_summary = await self.brain.think(
            f"{history}\n\nAll tool execution steps completed. Provide the comprehensive final answer for the user."
        )
        return final_summary
