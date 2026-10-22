"""
NEXUS Orchestrator.
Central routing and planning engine. Analyzes requests, selects specialist agents,
executes agent chains, synthesizes results, and runs autonomous multi-step goals.
"""

import sys
import json
import re
from typing import Dict, Any, List, Optional
from rich.console import Console

from core.tool_registry import ToolRegistry
from core.memory import Memory
from tools.filesystem import FileSystemTool
from tools.shell import ShellTool
from tools.web_search import WebSearchTool
from tools.playwright_browser import PlaywrightBrowser
from tools.image_generator import ImageGeneratorTool
from tools.tts_engine import TTSEngine
from tools.youtube_api import YouTubeAPITool

from agents.code_agent import CodeAgent
from agents.browser_agent import BrowserAgent
from agents.research_agent import ResearchAgent
from agents.media_agent import MediaAgent
from agents.youtube_agent import YouTubeAgent

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

console = Console(legacy_windows=False)

ROUTING_SYSTEM_PROMPT = """You are a task router for the NEXUS multi-agent AI system.
Analyze the user's request and return ONLY a valid JSON object (no markdown code blocks, no explanation) with this structure:
{
    "agents": ["AgentName1", "AgentName2"],
    "plan": "Brief step-by-step plan",
    "mode": "chat"
}

Available specialist agents and when to use them:
- CodeAgent: writing code, creating/editing files, reading files, searching directories, running shell commands, debugging, installing packages.
- BrowserAgent: opening web pages with headless Chromium, taking screenshots, clicking buttons, filling forms, scraping DOM.
- ResearchAgent: searching Google/DuckDuckGo, YouTube videos, reading articles/URLs, compiling research summaries.
- MediaAgent: generating AI images (Gemini Imagen/PIL), text-to-speech audio (Edge-TTS/ElevenLabs), FFmpeg video composition.
- YouTubeAgent: querying video analytics (views/likes), listing channel videos, updating video metadata.

Rules:
1. For general knowledge, chit-chat, advice, or simple explanations that require NO external tools, return:
   {"agents": [], "plan": "direct_answer", "mode": "chat"}
2. Use the minimum number of agents needed.
3. For multi-step tasks requiring multiple specialties, list agents in execution sequence.
"""

class NexusOrchestrator:
    """
    Orchestrates agents, manages execution pipelines, and handles auto mode.
    """

    def __init__(self, brain, memory: Optional[Memory] = None, tools: Optional[ToolRegistry] = None):
        self.brain = brain
        self.memory = memory or Memory()
        self.brain.memory = self.memory  # Attach memory to brain for CLI status checks

        self.tools = tools or ToolRegistry()
        self._init_tools()

        self.agents: Dict[str, Any] = {}
        self._init_agents()

    def _init_tools(self):
        """Register all tool implementations."""
        self.tools.register(FileSystemTool())
        self.tools.register(ShellTool())
        self.tools.register(WebSearchTool())
        self.tools.register(PlaywrightBrowser())
        self.tools.register(ImageGeneratorTool(brain=self.brain))
        self.tools.register(TTSEngine())
        self.tools.register(YouTubeAPITool())

    def _init_agents(self):
        """Instantiate all specialist agents."""
        self.agents["CodeAgent"] = CodeAgent(self.brain, self.tools)
        self.agents["BrowserAgent"] = BrowserAgent(self.brain, self.tools)
        self.agents["ResearchAgent"] = ResearchAgent(self.brain, self.tools)
        self.agents["MediaAgent"] = MediaAgent(self.brain, self.tools)
        self.agents["YouTubeAgent"] = YouTubeAgent(self.brain, self.tools)

    def get_agent(self, name: str) -> Optional[Any]:
        """Lookup an agent by name."""
        return self.agents.get(name)

    def _parse_routing_json(self, raw_text: str) -> Dict[str, Any]:
        """Safely parse routing JSON from LLM output."""
        cleaned = raw_text.strip()
        if "```json" in cleaned:
            match = re.search(r"```json\s*(.*?)\s*```", cleaned, re.DOTALL)
            if match:
                cleaned = match.group(1).strip()
        elif "```" in cleaned:
            match = re.search(r"```\s*(.*?)\s*```", cleaned, re.DOTALL)
            if match:
                cleaned = match.group(1).strip()

        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            cleaned = cleaned[start:end+1]

        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict) and "agents" in parsed:
                return parsed
        except Exception:
            pass

        # Fallback if unparseable
        return {"agents": [], "plan": "direct_answer", "mode": "chat"}

    async def process(self, user_input: str) -> str:
        """
        Process a user prompt:
        1. Classify task and route to agents.
        2. Execute agent chain sequentially.
        3. Synthesize final answer.
        4. Log conversation history in memory.
        """
        self.memory.add_entry("user", user_input)
        recent_history = self.memory.get_formatted_history(limit=4)
        rules_context = self.memory.get_rules_prompt()

        context_prompt = f"User Request: {user_input}"
        if recent_history:
            context_prompt = f"Recent History:\n{recent_history}\n\n{context_prompt}"
        if rules_context:
            context_prompt = f"{rules_context}\n\n{context_prompt}"

        # Step 1: Routing & Planning
        routing_raw = await self.brain.think(context_prompt, ROUTING_SYSTEM_PROMPT)
        plan = self._parse_routing_json(routing_raw)

        # Step 2: Direct answer without tools
        if not plan.get("agents"):
            direct_response = await self.brain.think(
                context_prompt,
                system_prompt="You are NEXUS, an advanced AI Assistant. Provide an insightful, accurate answer in Vietnamese."
            )
            self.memory.add_entry("assistant", direct_response, agent="NexusDirect")
            return direct_response

        # Step 3: Execute Agent Chain
        console.print(f"[bold cyan]📋 Kế hoạch:[/bold cyan] {plan.get('plan', 'Thực thi')}")
        console.print(f"[bold cyan]👥 Agents được phân công:[/bold cyan] {', '.join(plan['agents'])}")

        chain_context = f"User Goal: {user_input}\nStep-by-step Plan: {plan.get('plan', '')}\n"

        for agent_name in plan["agents"]:
            agent = self.get_agent(agent_name)
            if not agent:
                console.print(f"[yellow]⚠️ Bỏ qua agent không tồn tại: {agent_name}[/]")
                continue

            console.print(f"\n[bold yellow]🚀 Đang khởi chạy {agent_name}...[/]")
            agent_result = await agent.execute(user_input, plan.get("plan", ""))
            console.print(f"[green]✓ {agent_name} hoàn tất bước làm việc.[/]")

            chain_context += f"\n=== [{agent_name} Output] ===\n{agent_result}\n"
            self.memory.add_entry("assistant", f"[{agent_name}]: {agent_result[:500]}...", agent=agent_name)

        # Step 4: Synthesize Final Output
        synthesis_prompt = (
            f"Dưới đây là yêu cầu ban đầu của người dùng và kết quả thực hiện từ các specialist agents:\n\n"
            f"{chain_context}\n\n"
            "Hãy tổng hợp lại toàn bộ kết quả một cách mạch lạc, đầy đủ, chuyên nghiệp bằng tiếng Việt. "
            "Nếu có file đã tạo, hãy liệt kê rõ đường dẫn file."
        )

        final_response = await self.brain.think(
            synthesis_prompt,
            system_prompt="You are NEXUS, an elite multi-agent AI assistant. Synthesize the results clearly and thoroughly."
        )

        self.memory.add_entry("assistant", final_response, agent="NexusOrchestrator")
        return final_response

    async def auto_mode(self, goal: str) -> str:
        """
        Autonomous execution mode:
        1. Breaks a large goal into sequential subtasks.
        2. Executes each subtask autonomously.
        3. Returns overall completion status.
        """
        planning_prompt = (
            f"Phân tích mục tiêu sau thành danh sách từ 2 đến 5 công việc con tuần tự:\n"
            f"Mục tiêu: {goal}\n\n"
            "Trả về DUY NHẤT một JSON hợp lệ dạng:\n"
            '{"subtasks": ["Nhiệm vụ 1", "Nhiệm vụ 2", ...]}'
        )

        raw_plan = await self.brain.think(planning_prompt)
        cleaned = self._parse_routing_json(raw_plan)
        subtasks = cleaned.get("subtasks", [goal])
        if not isinstance(subtasks, list) or not subtasks:
            subtasks = [goal]

        console.print(f"[bold yellow]🎯 Đã lập trình {len(subtasks)} nhiệm vụ con trong Auto Mode:[/]")
        for i, task in enumerate(subtasks, 1):
            console.print(f"  {i}. {task}")

        execution_results = []
        for i, task in enumerate(subtasks, 1):
            console.print(f"\n[bold cyan]▶ [Nhiệm vụ {i}/{len(subtasks)}]:[/] {task}")
            task_result = await self.process(task)
            execution_results.append(f"Bước {i} ({task}):\n{task_result}")

        summary_prompt = (
            f"Tổng kết quá trình thực hiện mục tiêu tự động:\nMục tiêu ban đầu: {goal}\n\n"
            + "\n\n".join(execution_results)
            + "\n\nHãy tóm tắt các kết quả đạt được và thông báo hoàn tất."
        )
        final_summary = await self.brain.think(summary_prompt)
        return final_summary
