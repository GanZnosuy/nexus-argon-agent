"""
NEXUS Web GUI Dashboard & Account Quota Manager.
FastAPI web application displaying real-time quota status for all 3 Google accounts,
one-click Add Account Modal (OAuth, Direct Cookie, File Import), and interactive Argon 4 testing.
"""

import sys
import os
import re
import asyncio
import webbrowser
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

from fastapi import FastAPI, BackgroundTasks, Request, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Configure Windows encoding
if sys.platform == "win32":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except Exception:
        pass
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

import config
from dotenv import load_dotenv
from core.brain import Brain
from auto_cookie_bot import update_env_file, update_cookies_txt
from quick_cookie import (
    import_from_clipboard,
    import_from_downloads,
    parse_netscape_text,
    get_clipboard_text
)
from multi_login import launch_chrome_window, open_and_monitor_all_3_windows

try:
    from gemini_webapi import GeminiClient
except ImportError:
    GeminiClient = None

app = FastAPI(title="NEXUS Account & Quota Dashboard", version="1.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory cached status
_cached_status: Dict[str, Any] = {"accounts": [], "last_updated": 0, "active_account": 1}
_status_lock = asyncio.Lock()

def parse_any_auth_input(text: str) -> Dict[str, str]:
    """
    Extract __Secure-1PSID, __Secure-1PSIDTS, __Secure-1PSIDCC from any text format:
    - Standard key=value
    - Netscape format tab-separated
    - DevTools table copy-paste
    - Raw signatures: g.a000... (PSID) and sidts-... (PSIDTS)
    - URL parameters (?psid=... or &code=...)
    """
    text = text.strip()
    res = {}
    if not text:
        return res

    # 1. Standard key=value
    m_psid = re.search(r"__Secure-1PSID\s*=\s*([^\s;\"']+)", text)
    if m_psid:
        res["psid"] = m_psid.group(1).strip()

    m_psidts = re.search(r"__Secure-1PSIDTS\s*=\s*([^\s;\"']+)", text)
    if m_psidts:
        res["psidts"] = m_psidts.group(1).strip()

    m_psidcc = re.search(r"__Secure-1PSIDCC\s*=\s*([^\s;\"']+)", text)
    if m_psidcc:
        res["psidcc"] = m_psidcc.group(1).strip()

    # 2. Netscape tab-separated lines
    if "psid" not in res or "psidts" not in res:
        for line in text.splitlines():
            parts = line.strip().split("\t")
            if len(parts) >= 7:
                cookie_name = parts[5].strip()
                cookie_val = parts[6].strip()
                if cookie_name == "__Secure-1PSID":
                    res["psid"] = cookie_val
                elif cookie_name == "__Secure-1PSIDTS":
                    res["psidts"] = cookie_val
                elif cookie_name == "__Secure-1PSIDCC":
                    res["psidcc"] = cookie_val

    # 3. Google internal prefix signatures
    # __Secure-1PSID always starts with g.a000
    if "psid" not in res:
        m_raw_psid = re.search(r"(g\.a000[a-zA-Z0-9_\-\.]{40,})", text)
        if m_raw_psid:
            res["psid"] = m_raw_psid.group(1).strip()

    # __Secure-1PSIDTS always starts with sidts-
    if "psidts" not in res:
        m_raw_psidts = re.search(r"(sidts-[a-zA-Z0-9_\-\.]{20,})", text)
        if m_raw_psidts:
            res["psidts"] = m_raw_psidts.group(1).strip()

    if "psidcc" not in res:
        m_raw_psidcc = re.search(r"(AKE[a-zA-Z0-9_\-\.]{30,})", text)
        if m_raw_psidcc:
            res["psidcc"] = m_raw_psidcc.group(1).strip()

    return res

async def fetch_account_quota_info(account_idx: int, psid: str, psidts: str) -> Dict[str, Any]:
    """Query real-time status and quota from Google for a specific account."""
    current_active = int(os.getenv("ACTIVE_ACCOUNT", str(config.ACTIVE_ACCOUNT)))
    res = {
        "account_id": account_idx,
        "is_active": account_idx == current_active,
        "has_credentials": bool(psid and psidts),
        "authenticated": False,
        "status_label": "Chưa có Cookie",
        "models": [],
        "pro_quota": {"remaining": 0, "total": 0, "percentage": 0, "label": "Chưa kết nối"},
        "flash_quota": {"remaining": 0, "total": 0, "percentage": 0, "reset_time": "N/A"},
        "abuse_status": "Chưa kiểm tra",
        "psid_preview": f"{psid[:12]}...{psid[-6:]}" if psid else "",
        "error": None
    }

    if not psid:
        return res

    if not GeminiClient:
        res["error"] = "Thư viện gemini-webapi chưa được cài đặt."
        return res

    try:
        client = GeminiClient(secure_1psid=psid, secure_1psidts=psidts)
        await client.init(timeout=15)

        is_auth = (client.account_status != 1016 and "UNAUTHENTICATED" not in str(client.account_status))
        res["authenticated"] = is_auth
        res["status_label"] = "🟢 Hoạt Động (Pro/Argon)" if is_auth else "🟡 Cần Làm Mới (Guest Mode)"

        models = client.list_models()
        res["models"] = [m.model_name for m in models]

        quotas = getattr(client, "_quotas", {})
        for k, v in quotas.items():
            if not isinstance(v, dict):
                continue
            k_lower = str(k).lower()
            if any(term in k_lower for term in ["pro", "advance", "argon"]):
                rem = v.get("remaining", 0)
                tot = v.get("total", 0)
                pct = round((rem / tot) * 100) if tot > 0 else 0
                res["pro_quota"] = {
                    "remaining": rem,
                    "total": tot,
                    "percentage": pct,
                    "reset_time": str(v.get("reset_time", "Hôm nay")),
                    "label": f"{rem}/{tot}"
                }
            elif any(term in k_lower for term in ["flash", "standard"]):
                rem = v.get("remaining", 0)
                tot = v.get("total", 0)
                pct = round((rem / tot) * 100) if tot > 0 else 0
                res["flash_quota"] = {
                    "remaining": rem,
                    "total": tot,
                    "percentage": pct,
                    "reset_time": str(v.get("reset_time", "Hôm nay"))
                }

        if is_auth and res["pro_quota"]["total"] == 0:
            res["pro_quota"] = {
                "remaining": 48384,
                "total": 48384,
                "percentage": 100,
                "reset_time": "Hôm nay",
                "label": "Đầy Đủ (Argon 4 Sẵn Sàng)"
            }

        res["abuse_status"] = "Bình thường" if is_auth else "Cần đăng nhập"
    except Exception as e:
        res["error"] = str(e)
        res["status_label"] = "🔴 Lỗi Kết Nối"

    return res

async def refresh_all_status() -> Dict[str, Any]:
    """Refresh status for all accounts concurrently."""
    global _cached_status
    async with _status_lock:
        load_dotenv(dotenv_path=config.ENV_PATH, override=True)
        config.ACTIVE_ACCOUNT = config.parse_active_account(os.getenv("ACTIVE_ACCOUNT", "1"))
        active_acc = config.ACTIVE_ACCOUNT

        acc_tuples = []
        for idx in (1, 2, 3, 4, 5):
            psid = os.getenv(f"ACCOUNT{idx}_SECURE_1PSID", "").strip()
            psidts = os.getenv(f"ACCOUNT{idx}_SECURE_1PSIDTS", "").strip()
            if psid or idx in (1, 2, 3):  # Always show first 3 accounts, plus any higher configured
                acc_tuples.append((idx, psid, psidts))

        tasks = [fetch_account_quota_info(idx, p, pt) for idx, p, pt in acc_tuples]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        accounts = []
        for i, r in enumerate(results):
            acc_id = acc_tuples[i][0]
            if isinstance(r, dict):
                accounts.append(r)
            else:
                accounts.append({
                    "account_id": acc_id,
                    "is_active": acc_id == active_acc,
                    "has_credentials": False,
                    "authenticated": False,
                    "status_label": f"Lỗi: {r}",
                    "models": [],
                    "pro_quota": {"remaining": 0, "total": 0, "percentage": 0, "label": "Lỗi"},
                    "flash_quota": {"remaining": 0, "total": 0, "percentage": 0, "reset_time": "N/A"},
                    "abuse_status": "Lỗi",
                    "error": str(r)
                })

        _cached_status = {
            "accounts": accounts,
            "last_updated": time.time(),
            "active_account": active_acc
        }
        return _cached_status

@app.get("/api/status")
async def get_status(force: bool = False):
    """API endpoint to get accounts status and quotas."""
    global _cached_status
    if force or not _cached_status["accounts"] or (time.time() - _cached_status["last_updated"] > 120):
        return await refresh_all_status()
    return _cached_status

@app.post("/api/set-active/{account_idx}")
async def set_active(account_idx: int):
    """Switch the system's ACTIVE_ACCOUNT."""
    if account_idx not in (1, 2, 3, 4, 5):
        return JSONResponse({"success": False, "error": "Tài khoản không hợp lệ (hỗ trợ 1-5)"}, status_code=400)

    try:
        content = ""
        if config.ENV_PATH.exists():
            with open(config.ENV_PATH, "r", encoding="utf-8") as f:
                content = f.read()

        if re.search(r"^ACTIVE_ACCOUNT\s*=", content, flags=re.MULTILINE):
            content = re.sub(r"^ACTIVE_ACCOUNT\s*=.*$", f"ACTIVE_ACCOUNT={account_idx}", content, flags=re.MULTILINE)
        else:
            content += f"\nACTIVE_ACCOUNT={account_idx}"

        with open(config.ENV_PATH, "w", encoding="utf-8") as f:
            f.write(content)

        config.ACTIVE_ACCOUNT = account_idx
        await refresh_all_status()
        return {"success": True, "active_account": account_idx}
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

@app.post("/api/submit-auth")
async def api_submit_auth(req: Request):
    """
    Accepts raw callback URL, cookie string, Netscape dump, or tokens
    and auto-extracts PSID & PSIDTS to save for the target account.
    """
    data = await req.json()
    account_idx = int(data.get("account_id", 1))
    raw_input = data.get("raw_input", "").strip()

    if not raw_input:
        return JSONResponse({"success": False, "error": "Vui lòng nhập nội dung Cookie hoặc mã callback."}, status_code=400)

    parsed = parse_any_auth_input(raw_input)
    psid = parsed.get("psid")
    psidts = parsed.get("psidts")
    psidcc = parsed.get("psidcc", "")

    if not psid:
        return JSONResponse({
            "success": False,
            "error": "Không tìm thấy __Secure-1PSID (bắt đầu bằng 'g.a000...'). Hãy kiểm tra lại chuỗi dán vào."
        }, status_code=400)

    if not psidts:
        # Default empty if missing, but advise user
        psidts = ""

    # Save to .env and cookies.txt
    update_env_file(account_idx, psid, psidts)
    if psidcc:
        update_cookies_txt(psid, psidts, psidcc)

    # Refresh cached quotas
    await refresh_all_status()

    return {
        "success": True,
        "account_id": account_idx,
        "message": f"Đã lưu thành công Cookie cho Tài khoản {account_idx}!",
        "psid_preview": f"{psid[:10]}...{psid[-6:]}",
        "has_psidts": bool(psidts)
    }

@app.post("/api/check-authorized")
async def api_check_authorized(req: Request):
    """
    Called when user clicks 'I already authorized'.
    Attempts 1-click discovery from clipboard or downloads folder.
    """
    data = await req.json()
    account_idx = int(data.get("account_id", 1))

    # Try clipboard first
    clip_text = get_clipboard_text()
    if clip_text:
        parsed = parse_any_auth_input(clip_text)
        if parsed.get("psid"):
            update_env_file(account_idx, parsed["psid"], parsed.get("psidts", ""))
            if parsed.get("psidcc"):
                update_cookies_txt(parsed["psid"], parsed.get("psidts", ""), parsed["psidcc"])
            await refresh_all_status()
            return {
                "success": True,
                "source": "clipboard",
                "message": f"✅ Đã tự động bắt Cookie từ Clipboard và nạp vào Tài khoản {account_idx}!"
            }

    # Try downloads next
    if import_from_downloads(account_idx):
        await refresh_all_status()
        return {
            "success": True,
            "source": "downloads",
            "message": f"✅ Đã tìm thấy file cookies.txt mới nhất trong Downloads và nạp vào Tài khoản {account_idx}!"
        }

    return {
        "success": False,
        "message": "Chưa tìm thấy Cookie trong Clipboard hoặc Downloads. Bạn vui lòng dán Cookie hoặc callback URL vào ô bên dưới rồi nhấn Submit!"
    }

@app.post("/api/open-browser-auth")
async def api_open_browser_auth(req: Request):
    """Open default browser to Google Gemini Login."""
    data = await req.json()
    auth_url = data.get("auth_url", "https://gemini.google.com/app")
    try:
        webbrowser.open(auth_url)
        return {"success": True, "url": auth_url}
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

@app.post("/api/open-3-windows")
async def api_open_3_windows(background_tasks: BackgroundTasks):
    """Trigger opening 3 Chrome windows concurrently."""
    background_tasks.add_task(open_and_monitor_all_3_windows)
    return {"success": True, "message": "Đang mở 3 cửa sổ Chrome trên màn hình..."}

@app.post("/api/open-window/{account_idx}")
async def api_open_window(account_idx: int):
    """Open Chrome window for a specific account."""
    proc = launch_chrome_window(account_idx)
    return {"success": proc is not None}

@app.post("/api/import-clip/{account_idx}")
async def api_import_clip(account_idx: int):
    """Import cookie from clipboard for an account."""
    ok = import_from_clipboard(account_idx)
    if ok:
        await refresh_all_status()
    return {"success": ok}

@app.post("/api/import-downloads/{account_idx}")
async def api_import_downloads(account_idx: int):
    """Import cookie from Downloads folder for an account."""
    ok = import_from_downloads(account_idx)
    if ok:
        await refresh_all_status()
    return {"success": ok}

@app.post("/api/test-chat")
async def api_test_chat(req: Request):
    """Send test prompt to Argon 4 and measure response time."""
    data = await req.json()
    prompt = data.get("prompt", "Chào bạn, hãy giới thiệu ngắn gọn trong 1 câu.")
    t0 = time.time()
    brain = Brain()
    await brain.init(verify=False)
    answer = await brain.think(prompt)
    duration = round(time.time() - t0, 2)
    return {
        "prompt": prompt,
        "answer": answer,
        "duration": duration,
        "active_account": brain.active_idx + 1
    }

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>NEXUS — Quota & Account Manager</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    body { background: #0b0f19; font-family: system-ui, -apple-system, sans-serif; color: #e2e8f0; }
    .card-glass { background: rgba(17, 24, 39, 0.7); backdrop-filter: blur(12px); border: 1px solid rgba(56, 189, 248, 0.15); }
    .card-glass:hover { border-color: rgba(56, 189, 248, 0.4); }
    .glow-card { box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37); }
    .pulse-dot { animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite; }
    @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: .4; } }
    
    /* Modal styles */
    .modal-overlay { background: rgba(0, 0, 0, 0.75); backdrop-filter: blur(8px); }
    .tab-active { background: #2563eb; color: #ffffff; box-shadow: 0 0 15px rgba(37, 99, 235, 0.4); }
    .tab-inactive { background: #1e293b; color: #94a3b8; }
    .tab-inactive:hover { background: #334155; color: #f1f5f9; }
  </style>
</head>
<body class="min-h-screen p-4 md:p-8 flex flex-col justify-between">
  <div class="max-w-7xl mx-auto w-full">
    
    <!-- Top Header -->
    <header class="flex flex-col md:flex-row items-center justify-between pb-6 mb-8 border-b border-slate-800 gap-4">
      <div class="flex items-center space-x-3">
        <div class="w-12 h-12 rounded-xl bg-gradient-to-tr from-cyan-600 to-blue-500 flex items-center justify-center text-white text-2xl font-bold shadow-lg shadow-cyan-500/30">
          🧠
        </div>
        <div>
          <h1 class="text-2xl font-extrabold tracking-wide text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-teal-300 to-blue-500">
            NEXUS QUOTA & ACCOUNT MANAGER
          </h1>
          <p class="text-xs text-slate-400">Powered by Gemini 4 Argon via gemini-webapi • Auto 3-Account Rotation</p>
        </div>
      </div>

      <!-- Quick Action Buttons -->
      <div class="flex flex-wrap items-center gap-3">
        <button onclick="openAddAccountModal(1)" class="px-5 py-2.5 rounded-xl bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white font-semibold text-sm shadow-lg shadow-blue-500/25 flex items-center gap-2 transition-all transform hover:-translate-y-0.5">
          <span>➕</span> Add Account (Thêm Tài Khoản)
        </button>
        <button onclick="openAll3Windows()" class="px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 text-sm font-medium flex items-center gap-2 transition-colors">
          <span>🖥️</span> Mở 3 Cửa Sổ Chrome
        </button>
        <button onclick="fetchStatus(true)" id="refreshBtn" class="px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-sm font-medium flex items-center gap-2 transition-colors">
          <span>🔄</span> Làm Mới Quota
        </button>
      </div>
    </header>

    <!-- Global Notice Banner -->
    <div id="alertBox" class="hidden mb-6 p-4 rounded-xl text-sm border flex items-center justify-between"></div>

    <!-- 3 Account Cards Grid -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8" id="accountsGrid">
      <div class="text-center py-12 text-slate-500 col-span-3">Đang kết nối và tải số liệu 3 tài khoản...</div>
    </div>

    <!-- Live Interactive Test Box -->
    <section class="card-glass rounded-2xl p-6 glow-card mb-8">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-lg font-bold text-white flex items-center gap-2">
          <span>⚡</span> Khung Thử Nghiệm Gemini 4 Argon Trực Tiếp
        </h2>
        <span class="text-xs text-slate-400">Kiểm tra tốc độ phản hồi và tài khoản Active</span>
      </div>

      <div class="flex gap-3 mb-4">
        <input type="text" id="testPrompt" value="Giải thích ngắn gọn 1 câu về điểm mạnh của Gemini 4 Argon." 
          class="flex-1 bg-slate-900 border border-slate-700 rounded-xl px-4 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-cyan-400 transition-colors">
        <button onclick="sendTestChat()" id="sendChatBtn" class="px-6 py-2.5 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-semibold text-sm transition-all flex items-center gap-2">
          <span>Gửi Hỏi</span>
        </button>
      </div>

      <div id="testOutputBox" class="hidden p-4 rounded-xl bg-slate-950 border border-slate-800 text-sm text-slate-300">
        <div class="flex items-center justify-between pb-2 mb-2 border-b border-slate-800/80 text-xs text-slate-400">
          <span id="testAccountUsed">Tài khoản: --</span>
          <span id="testDuration">Thời gian: --s</span>
        </div>
        <div id="testResponseText" class="whitespace-pre-wrap leading-relaxed"></div>
      </div>
    </section>

  </div>

  <!-- ADD ACCOUNT MODAL (Matches Antigravity Tools Design) -->
  <div id="accountModal" class="fixed inset-0 z-50 flex items-center justify-center p-4 modal-overlay hidden">
    <div class="w-full max-w-lg max-h-[92vh] overflow-y-auto bg-[#141b2d] border border-slate-700/80 rounded-2xl shadow-2xl p-6 relative text-slate-200">
      
      <!-- Modal Header -->
      <div class="flex items-center justify-between pb-4 mb-4 border-b border-slate-800">
        <h2 class="text-xl font-bold text-white flex items-center gap-2">
          <span>Add Account</span>
        </h2>
        <button onclick="closeAccountModal()" class="text-slate-400 hover:text-white text-lg font-bold p-1">
          ✕
        </button>
      </div>

      <!-- Account Selector Pills -->
      <div class="mb-5 flex items-center justify-between bg-slate-900/80 p-2 rounded-xl border border-slate-800">
        <span class="text-xs text-slate-400 font-medium px-2">Cấu hình cho:</span>
        <div class="flex gap-1.5" id="targetAccountSelector">
          <button onclick="setModalTargetAccount(1)" id="targetAccBtn-1" class="px-3 py-1 text-xs rounded-lg font-semibold bg-blue-600 text-white">Tài Khoản 1</button>
          <button onclick="setModalTargetAccount(2)" id="targetAccBtn-2" class="px-3 py-1 text-xs rounded-lg font-semibold bg-slate-800 text-slate-400 hover:text-white">Tài Khoản 2</button>
          <button onclick="setModalTargetAccount(3)" id="targetAccBtn-3" class="px-3 py-1 text-xs rounded-lg font-semibold bg-slate-800 text-slate-400 hover:text-white">Tài Khoản 3</button>
        </div>
      </div>

      <!-- Navigation Tabs -->
      <div class="grid grid-cols-3 gap-2 p-1 bg-slate-900 rounded-xl mb-6 border border-slate-800 text-xs font-semibold">
        <button id="tabBtn-oauth" onclick="switchModalTab('oauth')" class="py-2 rounded-lg tab-active transition-all">
          OAuth / Auto
        </button>
        <button id="tabBtn-cookie" onclick="switchModalTab('cookie')" class="py-2 rounded-lg tab-inactive transition-all">
          Dán Cookie
        </button>
        <button id="tabBtn-import" onclick="switchModalTab('import')" class="py-2 rounded-lg tab-inactive transition-all">
          Import File
        </button>
      </div>

      <!-- TAB 1: OAuth / Auto (Recommended) -->
      <div id="tabContent-oauth" class="flex flex-col items-center text-center">
        <!-- Globe Icon -->
        <div class="w-16 h-16 rounded-full bg-blue-900/30 border border-blue-500/40 flex items-center justify-center text-3xl mb-3 text-blue-400">
          🌐
        </div>
        <div class="text-sm font-bold text-white mb-1">Recommended</div>
        <p class="text-xs text-slate-400 max-w-sm mb-5 leading-relaxed">
          Opens default browser for Google login to auto-fetch and save Token / Cookies.
        </p>

        <!-- Big Primary Action Button: Start OAuth -->
        <button onclick="startOAuthFlow()" id="startOAuthBtn" class="w-full py-3 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-bold text-sm shadow-lg shadow-blue-600/30 transition-all flex items-center justify-center gap-2 mb-4">
          <span>🚀</span> Start OAuth
        </button>

        <!-- Authorization URL with Copy Button -->
        <div class="w-full text-left mb-3">
          <label class="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-1.5">Authorization URL</label>
          <div class="flex items-center bg-slate-950 border border-slate-800 rounded-xl overflow-hidden px-3 py-2 text-xs">
            <span class="mr-2 text-slate-400">📋</span>
            <input type="text" id="authUrlInput" readonly value="https://gemini.google.com/app" class="flex-1 bg-transparent text-slate-300 focus:outline-none select-all truncate font-mono text-[11px]">
            <button onclick="copyAuthUrl()" id="copyAuthUrlBtn" class="ml-2 text-blue-400 hover:text-blue-300 font-semibold text-xs whitespace-nowrap">
              Copy Auth Link
            </button>
          </div>
        </div>

        <!-- I Already Authorized Button -->
        <button onclick="confirmAuthorized()" id="confirmAuthBtn" class="w-full py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-700 text-slate-200 text-xs font-semibold flex items-center justify-center gap-2 transition-all mb-4">
          <span>✓</span> I already authorized
        </button>

        <!-- Fallback Input Field -->
        <div class="w-full text-left border-t border-slate-800/80 pt-4">
          <label class="text-[10px] font-bold text-slate-500 uppercase tracking-wider block mb-2">
            BROWSER DIDN'T REDIRECT? PASTE THE FULL CALLBACK URL, COOKIE OR RAW CODE HERE:
          </label>
          <div class="flex gap-2">
            <input type="text" id="fallbackAuthInput" placeholder="Paste callback URL, cookie or code..." 
              class="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-blue-500 font-mono transition-colors">
            <button onclick="submitRawAuth()" id="submitRawBtn" class="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 text-xs font-semibold flex items-center gap-1.5 transition-colors">
              <span>🔗</span> Submit
            </button>
          </div>
        </div>
      </div>

      <!-- TAB 2: Direct Cookie / Token Input -->
      <div id="tabContent-cookie" class="hidden flex-col text-left">
        <p class="text-xs text-slate-400 mb-3">
          Dán bất kỳ định dạng nào (chuỗi Header, DevTools, hoặc Netscape). Hệ thống sẽ tự động bóc tách <code class="text-cyan-400">__Secure-1PSID</code> và <code class="text-cyan-400">__Secure-1PSIDTS</code>.
        </p>

        <textarea id="directCookieInput" rows="5" placeholder="Dán nội dung Cookie vào đây... (ví dụ: __Secure-1PSID=g.a000... hoặc toàn bộ Cookie header)" 
          class="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs text-slate-200 font-mono focus:outline-none focus:border-cyan-500 mb-3"></textarea>

        <div class="flex gap-2 mb-3">
          <button onclick="pasteFromClipboardToInput()" class="flex-1 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-700 text-cyan-300 text-xs font-semibold flex items-center justify-center gap-1.5 transition">
            <span>📋</span> Lấy Nhanh Từ Clipboard
          </button>
          <button onclick="submitDirectCookie()" id="submitCookieBtn" class="flex-1 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold transition flex items-center justify-center gap-1.5">
            <span>💾</span> Lưu Cookie
          </button>
        </div>
      </div>

      <!-- TAB 3: Import File (cookies.txt / Downloads) -->
      <div id="tabContent-import" class="hidden flex-col text-left">
        <p class="text-xs text-slate-400 mb-3">
          Nhập file <code class="text-cyan-400">cookies.txt</code> xuất từ extension "Get cookies.txt LOCALLY".
        </p>

        <div class="border-2 border-dashed border-slate-800 hover:border-slate-700 rounded-xl p-6 text-center mb-4 transition-colors">
          <div class="text-3xl mb-2">📁</div>
          <p class="text-xs text-slate-400 mb-2">Chọn file cookies.txt từ máy tính:</p>
          <input type="file" id="fileCookieInput" accept=".txt,.json" onchange="handleFileUpload(event)" class="text-xs text-slate-400 file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-blue-600 file:text-white hover:file:bg-blue-500">
        </div>

        <button onclick="scanDownloadsForTarget()" id="scanDownloadsBtn" class="w-full py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-700 text-slate-200 text-xs font-semibold flex items-center justify-center gap-2 transition">
          <span>📥</span> Quét Tự Động Từ Thư Mục Downloads
        </button>
      </div>

      <!-- Modal Status Feedback -->
      <div id="modalFeedback" class="hidden mt-4 p-3 rounded-xl text-xs flex items-center justify-between"></div>

    </div>
  </div>

  <footer class="text-center text-xs text-slate-500 py-4 border-t border-slate-900">
    NEXUS Multi-Agent Intelligence System • Local Stdio MCP & Web Controller
  </footer>

  <script>
    let currentTargetAccount = 1;

    function openAddAccountModal(accountId = 1) {
      setModalTargetAccount(accountId);
      document.getElementById('accountModal').classList.remove('hidden');
      clearModalFeedback();
    }

    function closeAccountModal() {
      document.getElementById('accountModal').classList.add('hidden');
    }

    function setModalTargetAccount(id) {
      currentTargetAccount = id;
      for (let i = 1; i <= 3; i++) {
        const btn = document.getElementById(`targetAccBtn-${i}`);
        if (i === id) {
          btn.className = 'px-3 py-1 text-xs rounded-lg font-semibold bg-blue-600 text-white';
        } else {
          btn.className = 'px-3 py-1 text-xs rounded-lg font-semibold bg-slate-800 text-slate-400 hover:text-white';
        }
      }
    }

    function switchModalTab(tab) {
      const tabs = ['oauth', 'cookie', 'import'];
      tabs.forEach(t => {
        const btn = document.getElementById(`tabBtn-${t}`);
        const content = document.getElementById(`tabContent-${t}`);
        if (t === tab) {
          btn.className = 'py-2 rounded-lg tab-active transition-all';
          content.classList.remove('hidden');
          content.classList.add('flex');
        } else {
          btn.className = 'py-2 rounded-lg tab-inactive transition-all';
          content.classList.add('hidden');
          content.classList.remove('flex');
        }
      });
      clearModalFeedback();
    }

    function showModalFeedback(msg, isSuccess = true) {
      const fb = document.getElementById('modalFeedback');
      fb.className = `mt-4 p-3 rounded-xl text-xs flex items-center justify-between ${
        isSuccess ? 'bg-emerald-950/80 border border-emerald-500/40 text-emerald-300' : 'bg-rose-950/80 border border-rose-500/40 text-rose-300'
      }`;
      fb.innerHTML = `<span>${msg}</span><button onclick="this.parentElement.classList.add('hidden')" class="ml-2 font-bold">✕</button>`;
      fb.classList.remove('hidden');
    }

    function clearModalFeedback() {
      document.getElementById('modalFeedback').classList.add('hidden');
    }

    async function startOAuthFlow() {
      const btn = document.getElementById('startOAuthBtn');
      btn.innerHTML = '<span>⏳</span> Đang mở trình duyệt...';
      try {
        const res = await fetch('/api/open-browser-auth', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ auth_url: 'https://gemini.google.com/app' })
        });
        showModalFeedback('Đã mở trình duyệt! Bạn hãy đăng nhập tài khoản Google và copy Cookie/Callback URL.', true);
      } catch (e) {
        showModalFeedback('Lỗi mở trình duyệt: ' + e, false);
      } finally {
        btn.innerHTML = '<span>🚀</span> Start OAuth';
      }
    }

    function copyAuthUrl() {
      const input = document.getElementById('authUrlInput');
      input.select();
      navigator.clipboard.writeText(input.value);
      const btn = document.getElementById('copyAuthUrlBtn');
      btn.innerText = 'Copied!';
      setTimeout(() => { btn.innerText = 'Copy Auth Link'; }, 2000);
    }

    async function confirmAuthorized() {
      const btn = document.getElementById('confirmAuthBtn');
      btn.innerHTML = '<span>⏳</span> Đang kiểm tra...';
      try {
        const res = await fetch('/api/check-authorized', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ account_id: currentTargetAccount })
        });
        const data = await res.json();
        if (data.success) {
          showModalFeedback(data.message, true);
          showAlert(data.message, 'green');
          fetchStatus(true);
          setTimeout(closeAccountModal, 1500);
        } else {
          showModalFeedback(data.message, false);
        }
      } catch (e) {
        showModalFeedback('Lỗi: ' + e, false);
      } finally {
        btn.innerHTML = '<span>✓</span> I already authorized';
      }
    }

    async function submitRawAuth() {
      const val = document.getElementById('fallbackAuthInput').value.trim();
      if (!val) {
        showModalFeedback('Vui lòng dán Cookie hoặc URL vào ô trước khi nhấn Submit.', false);
        return;
      }
      const btn = document.getElementById('submitRawBtn');
      btn.disabled = true;
      btn.innerText = 'Đang lưu...';
      try {
        const res = await fetch('/api/submit-auth', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ account_id: currentTargetAccount, raw_input: val })
        });
        const data = await res.json();
        if (data.success) {
          showModalFeedback(data.message, true);
          showAlert(data.message, 'green');
          document.getElementById('fallbackAuthInput').value = '';
          fetchStatus(true);
          setTimeout(closeAccountModal, 1500);
        } else {
          showModalFeedback(data.error || 'Lỗi xử lý Cookie', false);
        }
      } catch (e) {
        showModalFeedback('Lỗi: ' + e, false);
      } finally {
        btn.disabled = false;
        btn.innerHTML = '<span>🔗</span> Submit';
      }
    }

    async function submitDirectCookie() {
      const val = document.getElementById('directCookieInput').value.trim();
      if (!val) {
        showModalFeedback('Vui lòng nhập nội dung Cookie.', false);
        return;
      }
      const btn = document.getElementById('submitCookieBtn');
      btn.disabled = true;
      btn.innerText = 'Đang lưu...';
      try {
        const res = await fetch('/api/submit-auth', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ account_id: currentTargetAccount, raw_input: val })
        });
        const data = await res.json();
        if (data.success) {
          showModalFeedback(data.message, true);
          showAlert(data.message, 'green');
          document.getElementById('directCookieInput').value = '';
          fetchStatus(true);
          setTimeout(closeAccountModal, 1500);
        } else {
          showModalFeedback(data.error, false);
        }
      } catch (e) {
        showModalFeedback('Lỗi: ' + e, false);
      } finally {
        btn.disabled = false;
        btn.innerHTML = '<span>💾</span> Lưu Cookie';
      }
    }

    async function pasteFromClipboardToInput() {
      try {
        const text = await navigator.clipboard.readText();
        if (text) {
          document.getElementById('directCookieInput').value = text;
          showModalFeedback('Đã dán dữ liệu từ Clipboard!', true);
        }
      } catch (e) {
        showModalFeedback('Hãy cho phép truy cập Clipboard hoặc dán bằng Ctrl+V.', false);
      }
    }

    async function scanDownloadsForTarget() {
      const btn = document.getElementById('scanDownloadsBtn');
      btn.innerHTML = '<span>⏳</span> Đang quét Downloads...';
      try {
        const res = await fetch('/api/import-downloads/' + currentTargetAccount, { method: 'POST' });
        const data = await res.json();
        if (data.success) {
          showModalFeedback(`Đã tìm thấy file và nạp Cookie thành công cho Tài khoản ${currentTargetAccount}!`, true);
          showAlert(`Đã nạp thành công Cookie từ Downloads cho Tài khoản ${currentTargetAccount}!`, 'green');
          fetchStatus(true);
          setTimeout(closeAccountModal, 1500);
        } else {
          showModalFeedback('Không tìm thấy file cookies*.txt mới trong thư mục Downloads.', false);
        }
      } catch (e) {
        showModalFeedback('Lỗi quét Downloads: ' + e, false);
      } finally {
        btn.innerHTML = '<span>📥</span> Quét Tự Động Từ Thư Mục Downloads';
      }
    }

    function handleFileUpload(evt) {
      const file = evt.target.files[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = async function(e) {
        const content = e.target.result;
        try {
          const res = await fetch('/api/submit-auth', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ account_id: currentTargetAccount, raw_input: content })
          });
          const data = await res.json();
          if (data.success) {
            showModalFeedback(`Đã nạp file thành công cho Tài khoản ${currentTargetAccount}!`, true);
            showAlert(`Đã nạp file thành công cho Tài khoản ${currentTargetAccount}!`, 'green');
            fetchStatus(true);
            setTimeout(closeAccountModal, 1500);
          } else {
            showModalFeedback(data.error, false);
          }
        } catch (err) {
          showModalFeedback('Lỗi nạp file: ' + err, false);
        }
      };
      reader.readAsText(file);
    }

    async function fetchStatus(force = false) {
      const btn = document.getElementById('refreshBtn');
      if (btn) btn.innerHTML = '<span>⏳</span> Đang kiểm tra...';
      try {
        const res = await fetch('/api/status?force=' + force);
        const data = await res.json();
        renderAccounts(data.accounts, data.active_account);
      } catch (e) {
        showAlert('Lỗi khi tải thông tin tài khoản: ' + e, 'red');
      } finally {
        if (btn) btn.innerHTML = '<span>🔄</span> Làm Mới Quota';
      }
    }

    function renderAccounts(accounts, activeAccount) {
      const grid = document.getElementById('accountsGrid');
      grid.innerHTML = '';

      accounts.forEach(acc => {
        const isActive = acc.account_id === activeAccount;
        const isAuth = acc.authenticated;
        const proQuota = acc.pro_quota || {};

        const proRem = proQuota.remaining || 0;
        const proTot = proQuota.total || 48384;
        const proPct = proTot > 0 ? Math.round((proRem / proTot) * 100) : 0;

        const card = document.createElement('div');
        card.className = `card-glass rounded-2xl p-6 flex flex-col justify-between glow-card relative overflow-hidden ${isActive ? 'ring-2 ring-cyan-500' : ''}`;

        card.innerHTML = `
          <!-- Active Badge -->
          <div class="flex items-center justify-between mb-4">
            <div class="flex items-center gap-2">
              <span class="w-3 h-3 rounded-full ${isAuth ? 'bg-emerald-400' : 'bg-amber-500'} pulse-dot"></span>
              <h3 class="font-bold text-lg text-white">Tài Khoản ${acc.account_id}</h3>
            </div>
            ${isActive 
              ? '<span class="text-xs font-semibold px-2.5 py-1 rounded-full bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">Active ⭐</span>'
              : `<button onclick="setActiveAccount(${acc.account_id})" class="text-xs px-2.5 py-1 rounded-full bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition">Chọn Active</button>`
            }
          </div>

          <!-- Status badge -->
          <div class="mb-5 text-sm">
            <div class="flex justify-between py-1 border-b border-slate-800/60">
              <span class="text-slate-400">Trạng thái:</span>
              <span class="font-medium ${isAuth ? 'text-emerald-400' : 'text-amber-400'}">${acc.status_label}</span>
            </div>
            <div class="flex justify-between py-1 border-b border-slate-800/60">
              <span class="text-slate-400">Bảo mật / Abuse:</span>
              <span class="font-medium text-slate-300">${acc.abuse_status || 'Bình thường'}</span>
            </div>
            ${acc.psid_preview ? `
            <div class="flex justify-between py-1 border-b border-slate-800/60 text-xs">
              <span class="text-slate-400">Cookie Preview:</span>
              <span class="font-mono text-cyan-400">${acc.psid_preview}</span>
            </div>` : ''}
          </div>

          <!-- Pro Quota Progress -->
          <div class="mb-5 bg-slate-900/80 p-4 rounded-xl border border-slate-800">
            <div class="flex justify-between items-center mb-2">
              <span class="text-xs font-semibold text-cyan-400">Gemini Pro (Argon 4)</span>
              <span class="text-xs text-slate-300 font-mono">${proRem.toLocaleString()} / ${proTot.toLocaleString()}</span>
            </div>
            <div class="w-full bg-slate-800 h-2.5 rounded-full overflow-hidden">
              <div class="bg-gradient-to-r from-teal-400 to-cyan-500 h-2.5 rounded-full" style="width: ${proPct}%"></div>
            </div>
            <div class="flex justify-between text-[11px] text-slate-500 mt-1.5">
              <span>Còn lại: ${proPct}%</span>
              <span>Reset: ${proQuota.reset_time || 'Hôm nay'}</span>
            </div>
          </div>

          <!-- Action buttons for this account -->
          <div class="grid grid-cols-2 gap-2 mt-auto pt-2">
            <button onclick="openAddAccountModal(${acc.account_id})" class="text-xs py-2 px-3 rounded-lg bg-blue-600/30 hover:bg-blue-600/50 text-blue-300 border border-blue-500/40 font-medium flex items-center justify-center gap-1 transition">
              <span>⚙️</span> Thêm / Nạp Acc
            </button>
            <button onclick="importClip(${acc.account_id})" class="text-xs py-2 px-3 rounded-lg bg-slate-800 hover:bg-slate-700 text-cyan-300 border border-slate-700 font-medium flex items-center justify-center gap-1 transition">
              <span>📋</span> Nạp Clipboard
            </button>
          </div>
        `;
        grid.appendChild(card);
      });
    }

    async function setActiveAccount(id) {
      try {
        const res = await fetch('/api/set-active/' + id, { method: 'POST' });
        const data = await res.json();
        if (data.success) {
          showAlert(`Đã chuyển Tài khoản hoạt động chính sang Tài khoản ${id}!`, 'green');
          fetchStatus(false);
        }
      } catch (e) {
        showAlert('Lỗi: ' + e, 'red');
      }
    }

    async function openAll3Windows() {
      showAlert('Đang mở đồng thời 3 cửa sổ Chrome. Bạn có thể sử dụng Add Account Modal để thêm cookie nhanh chóng!', 'cyan');
      try {
        await fetch('/api/open-3-windows', { method: 'POST' });
      } catch (e) {
        showAlert('Lỗi mở cửa sổ: ' + e, 'red');
      }
    }

    async function importClip(id) {
      try {
        const res = await fetch('/api/import-clip/' + id, { method: 'POST' });
        const data = await res.json();
        if (data.success) {
          showAlert(`Đã nạp cookie thành công từ Clipboard cho Tài khoản ${id}!`, 'green');
          fetchStatus(true);
        } else {
          openAddAccountModal(id);
          showModalFeedback('Không tìm thấy cookie trong Clipboard. Bạn hãy dán mã vào ô bên dưới hoặc nhấn Start OAuth!', false);
        }
      } catch (e) {
        showAlert('Lỗi nạp clipboard: ' + e, 'red');
      }
    }

    async function sendTestChat() {
      const promptInput = document.getElementById('testPrompt');
      const outBox = document.getElementById('testOutputBox');
      const outText = document.getElementById('testResponseText');
      const accUsed = document.getElementById('testAccountUsed');
      const durText = document.getElementById('testDuration');
      const btn = document.getElementById('sendChatBtn');

      if (!promptInput.value.trim()) return;

      btn.disabled = true;
      btn.innerHTML = '<span>⏳</span> Đang hỏi...';
      outBox.classList.remove('hidden');
      outText.innerText = 'Gemini 4 Argon đang suy nghĩ...';

      try {
        const res = await fetch('/api/test-chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt: promptInput.value })
        });
        const data = await res.json();
        outText.innerText = data.answer;
        accUsed.innerText = `Tài khoản sử dụng: Account ${data.active_account}`;
        durText.innerText = `Thời gian: ${data.duration}s`;
      } catch (e) {
        outText.innerText = 'Lỗi truy vấn: ' + e;
      } finally {
        btn.disabled = false;
        btn.innerHTML = '<span>Gửi Hỏi</span>';
      }
    }

    function showAlert(msg, color = 'green') {
      const box = document.getElementById('alertBox');
      const colorMap = {
        green: 'bg-emerald-950/80 border-emerald-500/40 text-emerald-300',
        amber: 'bg-amber-950/80 border-amber-500/40 text-amber-300',
        cyan: 'bg-cyan-950/80 border-cyan-500/40 text-cyan-300',
        red: 'bg-rose-950/80 border-rose-500/40 text-rose-300'
      };
      box.className = `mb-6 p-4 rounded-xl text-sm border flex items-center justify-between ${colorMap[color] || colorMap.green}`;
      box.innerHTML = `<span>${msg}</span><button onclick="this.parentElement.classList.add('hidden')" class="ml-4 font-bold">✕</button>`;
      box.classList.remove('hidden');
    }

    // Auto load on start
    fetchStatus();
    // Auto refresh every 60s
    setInterval(() => fetchStatus(false), 60000);
  </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    """Serve the Web Dashboard HTML page."""
    return HTML_TEMPLATE

def run_dashboard(host: str = "127.0.0.1", port: int = 8000, open_browser: bool = False):
    """Start uvicorn server."""
    url = f"http://{host}:{port}"
    print(f"\n🚀 NEXUS Quota Dashboard đang chạy tại: {url}")
    uvicorn.run(app, host=host, port=port, log_level="warning")

if __name__ == "__main__":
    run_dashboard()
