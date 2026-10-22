# ================================================================================
# NEXUS — SUPER AI AGENT IMPLEMENTATION BLUEPRINT
# Powered by Gemini 4 Argon via gemini-webapi (Cookie Auth, Free Tier)
# ================================================================================
#
# TARGET: Any AI coding agent (Cursor, Claude Code, Windsurf, Antigravity)
# PROJECT DIR: ./nexus-argon-agent/
# LANGUAGE: Python 3.13 on Windows 11
# ================================================================================

<role>
You are a Senior Python Systems Architect building NEXUS — a local Super AI Agent
that uses Google Gemini 4 Argon as its brain (accessed for FREE via the gemini-webapi
Python package with cookie authentication). NEXUS is a multi-agent orchestrator
with 5 specialist sub-agents, 7 tool modules, dual interaction modes (chat + autonomous),
and automatic 3-account cookie rotation with fallback to Gemini Flash via official API.
</role>

<project_root>
./nexus-argon-agent/
</project_root>

<existing_files>
The following files already exist in the project directory — DO NOT overwrite them:
- cookies.txt     — Netscape cookie file with 3 Google accounts
- .env            — Extracted __Secure-1PSID and __Secure-1PSIDTS for all 3 accounts
                    plus ACTIVE_ACCOUNT selector and optional API keys
</existing_files>

# ================================================================================
# SECTION 1: ARCHITECTURE OVERVIEW
# ================================================================================

## System Architecture Diagram

```
USER (CLI Terminal — Vietnamese UI)
    │
    ▼
┌──────────────────────────────────────────────────────┐
│                  NEXUS ORCHESTRATOR                  │
│  (Task classification → Agent routing → Synthesis)   │
└──────────────┬───────────────────────┬───────────────┘
               │                       │
    ┌──────────▼──────────┐  ┌────────▼────────────┐
    │    BRAIN LAYER      │  │   MEMORY LAYER       │
    │                     │  │                      │
    │  Primary: Argon 4   │  │  conversation.json   │
    │  (gemini-webapi)    │  │  learned_rules.json  │
    │  3-account rotation │  │                      │
    │                     │  └──────────────────────┘
    │  Fallback: Flash    │
    │  (google-genai SDK) │
    └─────────────────────┘
               │
    ┌──────────▼──────────────────────────────────────┐
    │              5 SPECIALIST AGENTS                 │
    ├──────────┬──────────┬──────────┬────────────────┤
    │ CodeAgent│ Browser  │ Research │ Media  │YouTube │
    │          │ Agent    │ Agent    │ Agent  │Agent   │
    └────┬─────┴────┬─────┴────┬─────┴───┬────┴───┬───┘
         │          │          │         │        │
    ┌────▼───┐ ┌───▼────┐ ┌──▼───┐ ┌──▼───┐ ┌──▼──────┐
    │FileSys │ │Playwrgt│ │WebSrc│ │ImgGen│ │YT API v3│
    │Shell   │ │Browser │ │Google│ │TTS   │ │Upload   │
    └────────┘ └────────┘ └──────┘ └──────┘ └─────────┘
```

## Directory Structure to Create

```
nexus-argon-agent/
├── nexus.py                    # [NEW] Main CLI entry point
├── config.py                   # [NEW] Configuration loader
├── requirements.txt            # [NEW] Python dependencies
├── cookies.txt                 # [EXISTS] 3-account cookie file
├── .env                        # [EXISTS] Credentials
├── .gitignore                  # [NEW] Exclude secrets
│
├── core/
│   ├── __init__.py             # [NEW]
│   ├── orchestrator.py         # [NEW] Main agent router & task planner
│   ├── brain.py                # [NEW] LLM abstraction (Argon + Flash + rotation)
│   ├── memory.py               # [NEW] Conversation history & persistent memory
│   └── tool_registry.py        # [NEW] Tool discovery & dispatch
│
├── agents/
│   ├── __init__.py             # [NEW]
│   ├── base_agent.py           # [NEW] Abstract base class
│   ├── code_agent.py           # [NEW] File I/O + shell execution
│   ├── browser_agent.py        # [NEW] Web browsing via Playwright
│   ├── research_agent.py       # [NEW] Web search & data collection
│   ├── media_agent.py          # [NEW] Image generation, TTS, video
│   └── youtube_agent.py        # [NEW] YouTube API operations
│
├── tools/
│   ├── __init__.py             # [NEW]
│   ├── filesystem.py           # [NEW] Read/write/list/search files
│   ├── shell.py                # [NEW] Execute terminal commands
│   ├── web_search.py           # [NEW] Google search, URL reading
│   ├── playwright_browser.py   # [NEW] Full browser automation
│   ├── image_generator.py      # [NEW] AI image generation
│   ├── tts_engine.py           # [NEW] Text-to-speech (Edge-TTS + ElevenLabs)
│   └── youtube_api.py          # [NEW] YouTube Data API v3 wrapper
│
├── memory/
│   ├── conversation_log.json   # [AUTO-CREATED] Session history
│   └── learned_rules.json      # [AUTO-CREATED] Persistent learnings
│
└── tests/
    ├── test_brain.py            # [NEW] Brain layer tests
    ├── test_orchestrator.py     # [NEW] Orchestrator routing tests
    └── test_tools.py            # [NEW] Tool module tests
```

# ================================================================================
# SECTION 2: CORE BRAIN LAYER (CRITICAL — BUILD FIRST)
# ================================================================================

## File: core/brain.py

The Brain is the most critical component. It MUST implement:

### 2.1 Three-Account Cookie Rotation
- Load 3 sets of credentials from .env (ACCOUNT1/2/3_SECURE_1PSID + _1PSIDTS)
- Start with ACTIVE_ACCOUNT (default: 1)
- On AuthError or 429 RateLimit → automatically rotate to next account
- Rotation order: 1 → 2 → 3 → 1 (circular)
- Log which account is active

### 2.2 gemini-webapi Integration
```python
import asyncio
from gemini import GeminiClient

class Brain:
    def __init__(self):
        self.accounts = self._load_accounts()  # List of (PSID, PSIDTS) tuples
        self.active_idx = int(os.getenv("ACTIVE_ACCOUNT", "1")) - 1
        self.argon_client = None
        self.flash_client = None

    async def init(self):
        """Initialize Argon client with current account cookies."""
        psid, psidts = self.accounts[self.active_idx]
        self.argon_client = GeminiClient(psid, psidts)
        await self.argon_client.init(timeout=30)

    async def think(self, prompt: str, system_prompt: str = None) -> str:
        """Primary thinking method. Try Argon → rotate accounts → fallback Flash."""
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt

        # Try Argon with account rotation
        for attempt in range(len(self.accounts)):
            try:
                response = await self.argon_client.generate_content(full_prompt)
                return response.text
            except Exception as e:
                print(f"  [⚠️] Account {self.active_idx+1} error: {e}")
                await self._rotate_account()

        # All accounts exhausted → fallback to Flash
        return await self._flash_fallback(full_prompt)

    async def _rotate_account(self):
        """Switch to next account in circular order."""
        self.active_idx = (self.active_idx + 1) % len(self.accounts)
        psid, psidts = self.accounts[self.active_idx]
        print(f"  [🔄] Rotating to Account {self.active_idx+1}")
        self.argon_client = GeminiClient(psid, psidts)
        await self.argon_client.init(timeout=30)

    async def _flash_fallback(self, prompt: str) -> str:
        """Fallback to Gemini Flash via official API."""
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            return "[ERROR] All Argon accounts exhausted and no GOOGLE_API_KEY set for Flash fallback."
        from google import genai
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        return response.text
```

### 2.3 Cookie Health Check
- On startup, verify each account by sending a test prompt ("Hello")
- Mark dead accounts as inactive
- Warn user if all accounts are dead

# ================================================================================
# SECTION 3: ORCHESTRATOR (ROUTING ENGINE)
# ================================================================================

## File: core/orchestrator.py

The Orchestrator classifies user requests and routes to specialist agents.

### 3.1 Routing Logic
```python
ROUTING_SYSTEM_PROMPT = """You are a task router. Analyze the user's request and return
ONLY a JSON object (no markdown, no explanation) with this structure:
{
    "agents": ["AgentName1", "AgentName2"],
    "plan": "Brief step-by-step plan",
    "mode": "chat"
}

Available agents and when to use them:
- CodeAgent: writing code, creating files, reading files, running shell commands, debugging
- BrowserAgent: opening web pages, clicking buttons, filling forms, scraping page content
- ResearchAgent: searching Google/YouTube, gathering information, comparing data
- MediaAgent: generating images with AI, text-to-speech, video editing with FFmpeg
- YouTubeAgent: uploading videos, getting analytics, managing YouTube channel

Rules:
- Use the minimum number of agents needed
- For simple questions that need no tools, return: {"agents": [], "plan": "direct_answer", "mode": "chat"}
- For complex multi-step goals, chain multiple agents in order
"""

class NexusOrchestrator:
    async def process(self, user_input: str) -> str:
        # Step 1: Route
        routing_json = await self.brain.think(user_input, ROUTING_SYSTEM_PROMPT)
        plan = json.loads(routing_json)

        # Step 2: Direct answer (no agent needed)
        if not plan["agents"]:
            return await self.brain.think(user_input)

        # Step 3: Execute agent chain
        context = user_input
        for agent_name in plan["agents"]:
            agent = self.get_agent(agent_name)
            result = await agent.execute(context, plan["plan"])
            context += f"\n\n[{agent_name} Result]: {result}"

        # Step 4: Synthesize final response
        return await self.brain.think(
            f"Based on these agent results, provide a clear final answer:\n{context}",
            "You are NEXUS, a helpful AI assistant. Summarize the work done."
        )
```

### 3.2 Auto Mode
When user types `/auto [goal]`:
- Break goal into subtasks
- Execute each subtask sequentially without user confirmation
- Report progress after each subtask
- Stop only on unrecoverable error

# ================================================================================
# SECTION 4: AGENT IMPLEMENTATIONS
# ================================================================================

## File: agents/base_agent.py
```python
from abc import ABC, abstractmethod

class BaseAgent(ABC):
    def __init__(self, brain, tool_registry):
        self.brain = brain
        self.tools = tool_registry

    @abstractmethod
    async def execute(self, user_request: str, plan: str) -> str:
        """Execute the agent's task and return result string."""
        pass

    async def think_with_tools(self, prompt: str, available_tools: list) -> str:
        """Ask brain to decide which tool to use, then execute it."""
        tool_descriptions = "\n".join(
            f"- {t.name}: {t.description}" for t in available_tools
        )
        decision = await self.brain.think(
            f"Available tools:\n{tool_descriptions}\n\nTask: {prompt}\n\n"
            "Return JSON: {\"tool\": \"tool_name\", \"args\": {...}} or "
            "{\"tool\": \"none\", \"answer\": \"direct answer\"}"
        )
        parsed = json.loads(decision)
        if parsed["tool"] == "none":
            return parsed["answer"]
        tool = self.tools.get(parsed["tool"])
        return await tool.run(**parsed["args"])
```

## File: agents/code_agent.py
Tools: filesystem.read_file, filesystem.write_file, filesystem.list_dir, shell.execute
Capabilities:
- Read and write any file on the local filesystem
- Execute any terminal command (python, git, npm, ffmpeg, etc.)
- Analyze code, fix bugs, create new files
- Run tests and report results

## File: agents/browser_agent.py
Tools: playwright_browser.navigate, .screenshot, .click, .fill, .scrape_text
Capabilities:
- Open any URL in headless Chromium
- Take screenshots of web pages
- Click buttons, fill forms, login to websites
- Scrape text content from specific CSS selectors
- Navigate multi-step web workflows

## File: agents/research_agent.py
Tools: web_search.google_search, .youtube_search, .read_url
Capabilities:
- Search Google for any query, return top 10 results with snippets
- Search YouTube for videos, return title/views/channel/URL
- Read and extract text content from any URL
- Compare and analyze data from multiple sources

## File: agents/media_agent.py
Tools: image_generator.generate, tts_engine.edge_tts, tts_engine.elevenlabs
Capabilities:
- Generate images via Gemini Imagen (through Argon brain)
- Text-to-speech via Edge-TTS (free, Vietnamese voices) or ElevenLabs
- Compose FFmpeg commands for video editing

## File: agents/youtube_agent.py
Tools: youtube_api.upload, .get_analytics, .list_videos, .update_metadata
Capabilities:
- Upload videos to YouTube via Data API v3
- Retrieve video analytics (views, CTR, retention)
- Update video titles, descriptions, tags, thumbnails
- List all videos on a channel

# ================================================================================
# SECTION 5: TOOL IMPLEMENTATIONS
# ================================================================================

## File: tools/filesystem.py
```python
class FileSystemTool:
    name = "filesystem"
    description = "Read, write, list, and search files on the local computer"

    async def read_file(self, path: str) -> str:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    async def write_file(self, path: str, content: str) -> str:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"File written: {path}"

    async def list_dir(self, path: str = ".") -> str:
        entries = os.listdir(path)
        return "\n".join(entries)

    async def search_files(self, pattern: str, directory: str = ".") -> str:
        import glob
        matches = glob.glob(os.path.join(directory, "**", pattern), recursive=True)
        return "\n".join(matches)
```

## File: tools/shell.py
```python
import subprocess

class ShellTool:
    name = "shell"
    description = "Execute terminal commands on Windows"

    async def execute(self, command: str, cwd: str = None, timeout: int = 120) -> str:
        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True,
                cwd=cwd, timeout=timeout, encoding="utf-8", errors="replace"
            )
            output = result.stdout + result.stderr
            return f"[Exit {result.returncode}]\n{output[-3000:]}"
        except subprocess.TimeoutExpired:
            return "[ERROR] Command timed out"
```

## File: tools/web_search.py
Use `aiohttp` to query Google search results via scraping or DuckDuckGo API.
Return structured results: [{title, url, snippet}, ...]

## File: tools/playwright_browser.py
```python
from playwright.async_api import async_playwright

class PlaywrightBrowser:
    name = "browser"
    description = "Browse web pages, take screenshots, click, fill forms"

    async def navigate(self, url: str) -> str:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, timeout=30000)
            text = await page.inner_text("body")
            await browser.close()
            return text[:5000]

    async def screenshot(self, url: str, save_path: str = "screenshot.png") -> str:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, timeout=30000)
            await page.screenshot(path=save_path, full_page=True)
            await browser.close()
            return f"Screenshot saved: {save_path}"
```

## File: tools/tts_engine.py
```python
import edge_tts

class TTSEngine:
    name = "tts"
    description = "Convert text to speech audio files"

    async def edge_tts_generate(self, text: str, voice: str = "vi-VN-NamMinhNeural",
                                 rate: str = "+18%", output: str = "voice.mp3") -> str:
        communicate = edge_tts.Communicate(text, voice, rate=rate)
        await communicate.save(output)
        return f"Audio saved: {output}"
```

## File: tools/image_generator.py
Use the Brain (Argon) to generate images via Gemini's built-in image generation.
Fallback: Generate simple PIL placeholder images.

## File: tools/youtube_api.py
Use google-api-python-client for YouTube Data API v3.
Support: upload_video, get_analytics, list_videos, update_metadata.

# ================================================================================
# SECTION 6: CLI INTERFACE
# ================================================================================

## File: nexus.py
```python
import asyncio
import sys
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

console = Console()

async def main():
    # Initialize
    console.print(Panel.fit(
        "[bold cyan]🧠 NEXUS — Super AI Agent v1.0[/]\n"
        "[dim]Powered by Gemini 4 Argon (gemini-webapi)[/]",
        border_style="cyan"
    ))

    from core.brain import Brain
    from core.orchestrator import NexusOrchestrator

    brain = Brain()
    await brain.init()  # Connect to Argon, verify cookies

    orchestrator = NexusOrchestrator(brain)

    console.print(f"  Model: Gemini 4 Argon ✅  Account: {brain.active_idx+1}/3")
    console.print(f"  Gõ lệnh hoặc hỏi bất kỳ điều gì. /help để xem hướng dẫn.\n")

    # Main loop
    while True:
        try:
            user_input = Prompt.ask("[bold green]Bạn[/]")
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Tạm biệt![/]")
            break

        if not user_input.strip():
            continue

        # Handle commands
        if user_input.startswith("/"):
            await handle_command(user_input, orchestrator, brain)
            continue

        # Process through orchestrator
        with console.status("[bold cyan]Đang suy nghĩ...[/]"):
            response = await orchestrator.process(user_input)
        console.print(f"\n[bold cyan]NEXUS[/]: {response}\n")

async def handle_command(cmd, orchestrator, brain):
    if cmd.startswith("/auto "):
        goal = cmd[6:]
        console.print(f"[bold yellow]🤖 Auto Mode:[/] {goal}")
        # Break into subtasks and execute autonomously
        result = await orchestrator.auto_mode(goal)
        console.print(f"\n[bold green]✅ Hoàn tất:[/] {result}\n")
    elif cmd == "/status":
        console.print(f"  Account: {brain.active_idx+1}/3")
        console.print(f"  Memory entries: {len(brain.memory)}")
    elif cmd == "/cookie":
        console.print("  Mở .env và cập nhật cookie mới, sau đó gõ /reload")
    elif cmd == "/agents":
        console.print("  CodeAgent | BrowserAgent | ResearchAgent | MediaAgent | YouTubeAgent")
    elif cmd == "/clear":
        brain.memory.clear()
        console.print("  [dim]Đã xóa context[/]")
    elif cmd == "/help":
        console.print("  /auto [goal]  — Chế độ tự động")
        console.print("  /status       — Trạng thái hệ thống")
        console.print("  /cookie       — Cập nhật cookie")
        console.print("  /agents       — Danh sách agents")
        console.print("  /clear        — Xóa context")
        console.print("  /exit         — Thoát")
    elif cmd == "/exit":
        raise SystemExit

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
```

# ================================================================================
# SECTION 7: DEPENDENCIES & SETUP
# ================================================================================

## File: requirements.txt
```
gemini-webapi>=1.0.0
google-genai>=2.28.0
playwright>=1.40
rich>=13.0
python-dotenv>=1.0
aiohttp>=3.9
edge-tts>=6.1
Pillow>=10.0
duckduckgo-search>=6.0
```

## File: .gitignore
```
.env
cookies.txt
memory/
__pycache__/
*.pyc
.venv/
```

## Setup commands (run in order):
```bash
git clone https://github.com/GanZnosuy/nexus-argon-agent.git
cd nexus-argon-agent
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
python nexus.py
```

# ================================================================================
# SECTION 8: BUILD ORDER (SPRINT SEQUENCE)
# ================================================================================

Execute in this EXACT order. Do NOT skip steps. Test each step before moving on.

| Step | File(s) | Test Command | Done? |
|------|---------|--------------|-------|
| 1 | requirements.txt, .gitignore, config.py | pip install -r requirements.txt | [ ] |
| 2 | core/__init__.py, core/brain.py | python -c "from core.brain import Brain; print('OK')" | [ ] |
| 3 | core/memory.py | python -c "from core.memory import Memory; print('OK')" | [ ] |
| 4 | tools/__init__.py, tools/filesystem.py, tools/shell.py | python -c "from tools.filesystem import FileSystemTool; print('OK')" | [ ] |
| 5 | core/tool_registry.py | python -c "from core.tool_registry import ToolRegistry; print('OK')" | [ ] |
| 6 | agents/__init__.py, agents/base_agent.py, agents/code_agent.py | python -c "from agents.code_agent import CodeAgent; print('OK')" | [ ] |
| 7 | tools/web_search.py, tools/playwright_browser.py | python -c "from tools.web_search import WebSearchTool; print('OK')" | [ ] |
| 8 | agents/browser_agent.py, agents/research_agent.py | python -c "from agents.research_agent import ResearchAgent; print('OK')" | [ ] |
| 9 | tools/image_generator.py, tools/tts_engine.py | python -c "from tools.tts_engine import TTSEngine; print('OK')" | [ ] |
| 10 | agents/media_agent.py, tools/youtube_api.py, agents/youtube_agent.py | python -c "from agents.youtube_agent import YouTubeAgent; print('OK')" | [ ] |
| 11 | core/orchestrator.py | python -c "from core.orchestrator import NexusOrchestrator; print('OK')" | [ ] |
| 12 | nexus.py | python nexus.py --test | [ ] |
| 13 | Full integration test: type "Hello" in CLI | Manual verification | [ ] |

# ================================================================================
# SECTION 9: CRITICAL RULES FOR THE IMPLEMENTING AGENT
# ================================================================================

1. ALWAYS use `asyncio` — gemini-webapi is async-only
2. ALWAYS set `asyncio.WindowsSelectorEventLoopPolicy()` on Windows
3. ALWAYS use `encoding="utf-8"` when opening files (Windows default is cp1252)
4. ALWAYS use `sys.stdout.reconfigure(encoding="utf-8")` at startup
5. NEVER hardcode cookie values — always read from .env
6. NEVER skip error handling — every API call must have try/except
7. NEVER leave placeholder code (# TODO, pass, ...) — implement everything fully
8. The .env and cookies.txt files ALREADY EXIST — do not overwrite them
9. Test each module individually before building the next
10. The CLI must display Vietnamese text correctly on Windows terminal
