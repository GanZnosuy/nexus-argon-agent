"""
NEXUS MCP Server for Antigravity & Claude/Cursor IDEs.
Provides Model Context Protocol (MCP) interface over Stdio (JSON-RPC 2.0).
Exposes Gemini 4 Argon, 3-account rotation, specialist agents, and tools.
"""

import sys
import os
import json
import asyncio
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure project root is in sys.path and set as current working directory
PROJECT_ROOT = Path(__file__).resolve().parent
os.chdir(str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT))

# Setup Windows event loop and UTF-8 encoding
if sys.platform == "win32":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except Exception:
        pass

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", newline="\n")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")
if hasattr(sys.stdin, "reconfigure"):
    sys.stdin.reconfigure(encoding="utf-8")

# Reserve pure stdout exclusively for JSON-RPC transport to prevent protocol corruption
_mcp_stdout = sys.stdout
sys.stdout = sys.stderr

from core.brain import Brain
from core.orchestrator import NexusOrchestrator
from core.memory import Memory

# Global runtime state
_brain: Optional[Brain] = None
_memory: Optional[Memory] = None
_orchestrator: Optional[NexusOrchestrator] = None
_loop: Optional[asyncio.AbstractEventLoop] = None

def get_orchestrator() -> NexusOrchestrator:
    """Lazy initialize and return singleton Orchestrator."""
    global _brain, _memory, _orchestrator
    if _orchestrator is None:
        print("[DEBUG] Initializing NEXUS Brain and Orchestrator for MCP...", file=sys.stderr)
        _memory = Memory()
        _brain = Brain(memory=_memory)
        # Initialize brain in async loop
        try:
            loop = get_event_loop()
            loop.run_until_complete(_brain.init(verify=False))
        except Exception as e:
            print(f"[WARN] Brain init warning: {e}", file=sys.stderr)
        _orchestrator = NexusOrchestrator(brain=_brain, memory=_memory)
        print("[DEBUG] NEXUS Orchestrator initialized successfully.", file=sys.stderr)
    return _orchestrator

def get_event_loop() -> asyncio.AbstractEventLoop:
    """Retrieve or create persistent event loop."""
    global _loop
    if _loop is None or _loop.is_closed():
        _loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_loop)
    return _loop

# Tools Definition for MCP
TOOLS = [
    {
        "name": "nexus_process",
        "description": "Send any complex request or question to NEXUS. Automatically plans, routes to specialist agents (Code, Browser, Research, Media, YouTube), executes tools, and synthesizes a complete response.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "user_input": {
                    "type": "string",
                    "description": "User request or task description in Vietnamese or English"
                }
            },
            "required": ["user_input"]
        }
    },
    {
        "name": "nexus_auto_goal",
        "description": "Execute an end-to-end goal autonomously. NEXUS breaks the goal into sequential subtasks, executes each step without requiring confirmation, and summarizes the final result.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "goal": {
                    "type": "string",
                    "description": "The high-level goal to accomplish autonomously"
                }
            },
            "required": ["goal"]
        }
    },
    {
        "name": "nexus_argon_think",
        "description": "Directly query Google Gemini 4 Argon via gemini-webapi with automatic 3-account cookie rotation and Flash fallback.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "The prompt to send to Gemini 4 Argon"
                },
                "system_prompt": {
                    "type": "string",
                    "description": "Optional system prompt instructions"
                }
            },
            "required": ["prompt"]
        }
    },
    {
        "name": "nexus_status",
        "description": "Get current health status of NEXUS, active Google cookie account, rotation health, and memory entry count.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "nexus_code_agent",
        "description": "Specialist agent for reading, writing, editing local files, searching directories, and executing shell commands on Windows.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "Coding or filesystem task to perform"
                },
                "plan": {
                    "type": "string",
                    "description": "Optional step-by-step guidance"
                }
            },
            "required": ["task"]
        }
    },
    {
        "name": "nexus_research_agent",
        "description": "Specialist agent for searching the web, searching YouTube videos, and reading article contents from URLs.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query_or_url": {
                    "type": "string",
                    "description": "Search keyword or URL to investigate"
                },
                "plan": {
                    "type": "string",
                    "description": "Optional research scope instructions"
                }
            },
            "required": ["query_or_url"]
        }
    },
    {
        "name": "nexus_browser_agent",
        "description": "Specialist agent controlling headless Chromium via Playwright. Navigates dynamic SPAs, takes screenshots, clicks elements, fills forms, and scrapes content.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Web page URL to browse"
                },
                "action": {
                    "type": "string",
                    "enum": ["navigate", "screenshot", "click", "fill", "scrape_text"],
                    "description": "Browser action to execute (default: navigate)"
                },
                "selector": {
                    "type": "string",
                    "description": "CSS selector for click/fill/scrape actions"
                },
                "text": {
                    "type": "string",
                    "description": "Input text for fill action"
                },
                "save_path": {
                    "type": "string",
                    "description": "File path for screenshot (e.g. screenshot.png)"
                }
            },
            "required": ["url"]
        }
    },
    {
        "name": "nexus_tts_generate",
        "description": "Convert text to natural speech audio file (.mp3) using Edge-TTS (Vietnamese & English) or ElevenLabs.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Text script to speak"
                },
                "voice": {
                    "type": "string",
                    "default": "vi-VN-NamMinhNeural",
                    "description": "Voice identifier (e.g. vi-VN-NamMinhNeural, vi-VN-HoaiMyNeural, en-US-ChristopherNeural)"
                },
                "rate": {
                    "type": "string",
                    "default": "+18%",
                    "description": "Speaking rate adjustment (e.g. +18%, +0%, -10%)"
                },
                "output": {
                    "type": "string",
                    "default": "voice.mp3",
                    "description": "Target .mp3 file path"
                }
            },
            "required": ["text"]
        }
    },
    {
        "name": "nexus_image_generate",
        "description": "Generate AI images using Gemini Argon Imagen, Google Imagen 3 API, or high-aesthetic PIL poster design.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Description of the image to generate"
                },
                "output": {
                    "type": "string",
                    "default": "generated_image.png",
                    "description": "Target image file path"
                }
            },
            "required": ["prompt"]
        }
    },
    {
        "name": "nexus_youtube_analytics",
        "description": "Query YouTube video statistics (views, likes, comments, title, channel) or list channel videos via YouTube Data API v3.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["get_analytics", "list_videos"],
                    "default": "get_analytics",
                    "description": "Action to perform"
                },
                "video_id": {
                    "type": "string",
                    "description": "YouTube video ID or URL"
                },
                "query": {
                    "type": "string",
                    "description": "Search keyword when listing videos"
                }
            }
        }
    },
    {
        "name": "nexus_login_bot",
        "description": "Launch the automated Google login bot in visible Chrome. The user logs in and the bot captures fresh cookies (__Secure-1PSID, __Secure-1PSIDTS) and updates NEXUS automatically.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "account": {
                    "type": "integer",
                    "enum": [1, 2, 3],
                    "default": 1,
                    "description": "Google account slot to update (1, 2, or 3)"
                }
            }
        }
    }
]

def execute_tool(name: str, args: Dict[str, Any]) -> str:
    """Execute MCP tool invocation."""
    orch = get_orchestrator()
    loop = get_event_loop()

    if name == "nexus_process":
        user_input = args.get("user_input", "")
        return loop.run_until_complete(orch.process(user_input))

    elif name == "nexus_auto_goal":
        goal = args.get("goal", "")
        return loop.run_until_complete(orch.auto_mode(goal))

    elif name == "nexus_argon_think":
        prompt = args.get("prompt", "")
        sys_prompt = args.get("system_prompt")
        return loop.run_until_complete(orch.brain.think(prompt, system_prompt=sys_prompt))

    elif name == "nexus_status":
        from dotenv import load_dotenv
        load_dotenv(override=True)
        orch.brain.accounts = config.get_accounts()
        loop.run_until_complete(orch.brain.init(verify=False))
        health = loop.run_until_complete(orch.brain.check_account_health())
        status_info = {
            "system": "NEXUS Super AI Agent",
            "model": "Gemini Pro / Flash Fallback" if health.get("using_fallback") else f"{health.get('model', 'Gemini 4 Argon')} (Mức cao nhất)",
            "extended_thinking": "Bật (Suy luận sâu tối đa)",
            "active_account": f"Account {health.get('active_account')}/{health.get('total_accounts')}",
            "health_map": health.get("health_map"),
            "memory_entries": len(orch.memory),
            "agents_available": list(orch.agents.keys()),
            "tools_available": orch.tools.list_names()
        }
        return json.dumps(status_info, ensure_ascii=False, indent=2)

    elif name == "nexus_code_agent":
        agent = orch.get_agent("CodeAgent")
        task = args.get("task", "")
        plan = args.get("plan", "Execute code and filesystem operations")
        return loop.run_until_complete(agent.execute(task, plan))

    elif name == "nexus_research_agent":
        agent = orch.get_agent("ResearchAgent")
        query = args.get("query_or_url", "")
        plan = args.get("plan", "Investigate and summarize information")
        return loop.run_until_complete(agent.execute(query, plan))

    elif name == "nexus_browser_agent":
        browser_tool = orch.tools.get("browser")
        action = args.get("action", "navigate")
        return loop.run_until_complete(browser_tool.run(action=action, **args))

    elif name == "nexus_tts_generate":
        tts_tool = orch.tools.get("tts")
        return loop.run_until_complete(tts_tool.run(action="edge_tts", **args))

    elif name == "nexus_image_generate":
        img_tool = orch.tools.get("image_generator")
        return loop.run_until_complete(img_tool.run(action="generate", **args))

    elif name == "nexus_youtube_analytics":
        yt_tool = orch.tools.get("youtube_api")
        action = args.get("action", "get_analytics")
        return loop.run_until_complete(yt_tool.run(action=action, **args))

    elif name == "nexus_login_bot":
        from auto_cookie_bot import extract_cookie_for_account
        acc = args.get("account", 1)
        res = loop.run_until_complete(extract_cookie_for_account(account_idx=int(acc)))
        if res:
            return f"[SUCCESS] Đã bắt thành công cookie cho Tài khoản {acc} và cập nhật .env!"
        return f"[ERROR] Không thể lấy cookie cho Tài khoản {acc}."

    else:
        return f"[ERROR] Tool '{name}' không tồn tại trong NEXUS MCP Server."

def handle_request(request_data: str) -> Optional[str]:
    """Process incoming JSON-RPC 2.0 messages from Antigravity."""
    if not request_data or not request_data.strip():
        return None

    try:
        request = json.loads(request_data.strip())
        method = request.get("method")
        msg_id = request.get("id")

        if method == "initialize":
            response = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "experimental": {},
                        "tools": {"listChanged": False}
                    },
                    "serverInfo": {
                        "name": "nexus-agent",
                        "version": "1.0.0"
                    }
                }
            }
            return json.dumps(response, ensure_ascii=False)

        elif method == "notifications/initialized":
            return None

        elif method == "tools/list":
            response = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "tools": TOOLS
                }
            }
            return json.dumps(response, ensure_ascii=False)

        elif method == "tools/call":
            params = request.get("params", {})
            tool_name = params.get("name", "")
            arguments = params.get("arguments", {})

            result_text = execute_tool(tool_name, arguments)

            response = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": str(result_text)
                        }
                    ]
                }
            }
            return json.dumps(response, ensure_ascii=False)

        elif method == "ping":
            return json.dumps({"jsonrpc": "2.0", "id": msg_id, "result": {}}, ensure_ascii=False)

        else:
            return json.dumps({
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {
                    "code": -32601,
                    "message": f"Method '{method}' not found"
                }
            }, ensure_ascii=False)

    except Exception as e:
        print(f"[ERROR] MCP request error: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return json.dumps({
            "jsonrpc": "2.0",
            "id": None,
            "error": {
                "code": -32603,
                "message": str(e)
            }
        }, ensure_ascii=False)

def main():
    """Main Stdio JSON-RPC event loop."""
    print("[INFO] Starting NEXUS MCP Server on Stdio...", file=sys.stderr)
    print(f"[INFO] Loaded {len(TOOLS)} MCP tools for Antigravity integration.", file=sys.stderr)

    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break

            response = handle_request(line)
            if response:
                _mcp_stdout.write(response + "\n")
                _mcp_stdout.flush()

        except (KeyboardInterrupt, EOFError):
            break
        except Exception as e:
            print(f"[ERROR] Main loop exception: {e}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)

if __name__ == "__main__":
    main()
