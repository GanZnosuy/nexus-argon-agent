# 🌟 NEXUS — Autonomous Multi-Agent AI System (Gemini 4 Argon)

> **Autonomous multi-agent intelligence system powered by Google Gemini 4 Argon via reverse-engineered cookie authentication, circular multi-account quota rotation, and Model Context Protocol (MCP) support.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![Model](https://img.shields.io/badge/Brain-Gemini%204%20Argon-792ee5.svg)](https://gemini.google.com)
[![Status](https://img.shields.io/badge/Dashboard-FastAPI%20%2B%20Tailwind-009688.svg)](http://127.0.0.1:8000)

---

## ✨ Features

- **🧠 Google Gemini 4 Argon Brain**: Harnesses the highest-tier reasoning model (`gemini-argon`) with deep extended thinking, structured planning, and multi-turn conversational memory.
- **🔄 Strict Argon Enforcement & Account Rotation**: Automatically detects accounts with Argon capability. If an account lacks Argon permissions or cookies expire, it rotates or reports an explicit error without silently downgrading to Flash.
- **🌐 Real-Time Quota & Account Dashboard**: Sleek modern Web GUI (`http://127.0.0.1:8000`) built with FastAPI, Tailwind CSS, and WebSocket live updates to monitor remaining credits, reset timers, and abuse status.
- **👥 5 Specialist Sub-Agents**:
  - **CodeAgent**: File system operations, script generation, and terminal command execution.
  - **BrowserAgent**: Headless Chromium automation via Playwright with screenshots and DOM extraction.
  - **ResearchAgent**: Deep web research via Google Search and DuckDuckGo.
  - **MediaAgent**: Multimodal asset synthesis, TTS narration (Edge-TTS / ElevenLabs), and poster rendering.
  - **YouTubeAgent**: Video transcript extraction, comment analysis, and search.
- **🔌 Model Context Protocol (MCP) Server**: Full native MCP server (`nexus_mcp.py`) allowing Antigravity, Claude Desktop, Cursor, or Windsurf to call NEXUS agents and tools seamlessly.
- **🔐 Privacy & Open Source Security**: Zero hardcoded secrets. Cookies and credentials stay exclusively in local, git-ignored `.env` files.

---

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/GanZnosuy/nexus-argon-agent.git
cd nexus-argon-agent
```

### 2. Set Up Virtual Environment
```bash
python -m venv .venv

# Windows:
.venv\Scripts\activate

# Linux / macOS:
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
playwright install chromium
```

### 4. Configure Environment
Copy `.env.example` to `.env`:
```bash
copy .env.example .env   # Windows
# or: cp .env.example .env # Linux / Mac
```

Extract your Gemini Web session cookies (`__Secure-1PSID` and `__Secure-1PSIDTS`) from your browser while logged into [gemini.google.com](https://gemini.google.com), and paste them into `.env`:
```env
ACTIVE_ACCOUNT=1
ACCOUNT1_SECURE_1PSID=your___Secure-1PSID_here
ACCOUNT1_SECURE_1PSIDTS=your___Secure-1PSIDTS_here
```

*(Optional: Use `python quick_cookie.py` or run `DANG_NHAP_GOOGLE_AI_PRO_NEXUS.bat` on Windows for automated cookie capture.)*

---

## 🖥️ Running the Application

### 1. Launch the Quota & Account Web Dashboard
```bash
python dashboard.py
```
Open **[http://127.0.0.1:8000](http://127.0.0.1:8000)** in your browser to inspect live quotas, switch active accounts, and test Argon reasoning in real time.

### 2. Interactive CLI Mode
```bash
python nexus.py
```

### 3. Autonomous Goal Execution
```bash
python nexus.py --goal "Research the latest AI breakthroughs this week and compile an executive summary"
```

### 4. Setup Model Context Protocol (MCP)
To register NEXUS tools with an MCP host (Antigravity, Claude Desktop, Cursor):
```bash
python setup_mcp.py
```

---

## 🛡️ Security & Privacy Notice

This repository is **Open Source (MIT)**.
- **Never commit `.env` or `cookies.txt`**. The `.gitignore` is pre-configured to strictly exclude all credentials, tokens, session profiles (`auth_profiles/`), temporary files, and conversation logs.
- All Google authentication tokens remain strictly on your local machine.

---

## 📜 License

Distributed under the **MIT License**. See [`LICENSE`](./LICENSE) for full details.
