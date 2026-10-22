"""
NEXUS MCP Registration & Schema Exporter for Antigravity.
"""

import sys
import json
from pathlib import Path
from nexus_mcp import TOOLS

def export_schemas():
    mcp_dir = Path.home() / ".gemini" / "antigravity" / "mcp" / "nexus-agent"
    mcp_dir.mkdir(parents=True, exist_ok=True)

    for tool in TOOLS:
        tool_file = mcp_dir / f"{tool['name']}.json"
        schema = {
            "name": tool["name"],
            "description": tool["description"],
            "parameters": tool["inputSchema"]
        }
        with open(tool_file, "w", encoding="utf-8") as f:
            json.dump(schema, f, ensure_ascii=False, indent=2)

    instructions_file = mcp_dir / "instructions.md"
    instructions_text = """# NEXUS MCP Server Integration Guide
NEXUS is an autonomous multi-agent intelligence system powered by Google Gemini 4 Argon via gemini-webapi with circular 3-account cookie rotation.

## Available Tools:
- `nexus_process`: Submit any prompt/task; automatically routes across specialist agents and synthesizes results.
- `nexus_auto_goal`: Fully autonomous multi-step goal execution.
- `nexus_argon_think`: Direct inference from Gemini 4 Argon.
- `nexus_status`: System health, active cookie account (1/3), and remaining quotas.
- `nexus_code_agent`: Local file reading/writing and terminal command execution.
- `nexus_research_agent`: Web search (Google/DDG) and YouTube video queries.
- `nexus_browser_agent`: Headless Chromium navigation, screenshotting, form interaction.
- `nexus_tts_generate`: Vietnamese & English speech synthesis (Edge-TTS / ElevenLabs).
- `nexus_image_generate`: Image generation (Gemini Argon Imagen / Google Imagen 3 / PIL poster).
- `nexus_youtube_analytics`: Query YouTube video metrics, views, likes, and comments.
"""
    with open(instructions_file, "w", encoding="utf-8") as f:
        f.write(instructions_text)

    print(f"[OK] Exported {len(TOOLS)} tool schemas and instructions.md to: {mcp_dir}")

if __name__ == "__main__":
    export_schemas()
