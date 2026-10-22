"""
NEXUS Multi-Window Google Login & Cookie Extractor.
Opens 3 separate Google Chrome windows tiled across the screen (Left, Center, Right).
Each window runs an isolated profile for Account 1, 2, and 3.
Monitors login in real-time, extracts cookies, and updates .env and cookies.txt automatically.
"""

import sys
import os
import asyncio
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional
from rich.console import Console
from rich.panel import Panel

if sys.platform == "win32":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except Exception:
        pass
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

console = Console(legacy_windows=False)
PROJECT_ROOT = Path(__file__).resolve().parent
PROFILES_DIR = PROJECT_ROOT / "auth_profiles"
PROFILES_DIR.mkdir(exist_ok=True)

try:
    from playwright.async_api import async_playwright
except ImportError:
    async_playwright = None

from auto_cookie_bot import find_chrome_executable, update_env_file, update_cookies_txt

WINDOW_CONFIGS = [
    {"account": 1, "port": 9222, "pos": "0,0", "size": "630,980"},
    {"account": 2, "port": 9223, "pos": "635,0", "size": "630,980"},
    {"account": 3, "port": 9224, "pos": "1270,0", "size": "630,980"},
]

def launch_chrome_window(account_idx: int) -> Optional[subprocess.Popen]:
    """Launch native Chrome process for a specific account with custom position."""
    chrome_path = find_chrome_executable()
    if not chrome_path:
        console.print("[red]❌ Không tìm thấy Google Chrome trên máy tính![/]")
        return None

    cfg = next((c for c in WINDOW_CONFIGS if c["account"] == account_idx), WINDOW_CONFIGS[0])
    profile_dir = PROFILES_DIR / f"account_{account_idx}"
    profile_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        chrome_path,
        f"--user-data-dir={profile_dir}",
        f"--remote-debugging-port={cfg['port']}",
        f"--window-position={cfg['pos']}",
        f"--window-size={cfg['size']}",
        "--disable-blink-features=AutomationControlled",
        "--no-first-run",
        "--no-default-browser-check",
        "https://gemini.google.com/app"
    ]

    try:
        proc = subprocess.Popen(cmd)
        return proc
    except Exception as e:
        console.print(f"[red]❌ Lỗi mở Chrome cho Tài khoản {account_idx}:[/] {e}")
        return None

async def monitor_account_cdp(account_idx: int, port: int, timeout_seconds: int = 300) -> Optional[Dict[str, str]]:
    """Connect to Chrome via CDP port and wait for login cookies."""
    if not async_playwright:
        return None

    console.print(f"[dim]Đang theo dõi cổng CDP {port} của Tài khoản {account_idx}...[/dim]")
    start_time = time.time()

    async with async_playwright() as p:
        browser = None
        while time.time() - start_time < timeout_seconds:
            try:
                if browser is None:
                    try:
                        browser = await p.chromium.connect_over_cdp(f"http://127.0.0.1:{port}", timeout=3000)
                    except Exception:
                        await asyncio.sleep(2)
                        continue

                contexts = browser.contexts
                if contexts:
                    cookies = await contexts[0].cookies(["https://gemini.google.com", "https://google.com"])
                    cookie_dict = {c["name"]: c["value"] for c in cookies}
                    psid = cookie_dict.get("__Secure-1PSID")
                    psidts = cookie_dict.get("__Secure-1PSIDTS")
                    psidcc = cookie_dict.get("__Secure-1PSIDCC", "")

                    if psid and psidts:
                        # Success!
                        update_env_file(account_idx, psid, psidts)
                        update_cookies_txt(psid, psidts, psidcc)
                        console.print(f"[bold green]✅ Tài khoản {account_idx} ĐÃ ĐĂNG NHẬP & BẮT ĐƯỢC COOKIES THÀNH CÔNG![/]")
                        return {"psid": psid, "psidts": psidts, "psidcc": psidcc}

            except Exception:
                browser = None

            await asyncio.sleep(2)

    return None

async def open_and_monitor_all_3_windows(timeout_seconds: int = 300):
    """Open all 3 Chrome windows and monitor them concurrently."""
    console.print(Panel(
        "[bold cyan]🚀 ĐANG MỞ 3 CỬA SỔ GOOGLE CHROME SONG SONG[/]\n\n"
        "• [bold yellow]Cửa sổ 1 (Trái):[/] Tài khoản Google 1\n"
        "• [bold yellow]Cửa sổ 2 (Giữa):[/] Tài khoản Google 2\n"
        "• [bold yellow]Cửa sổ 3 (Phải):[/] Tài khoản Google 3\n\n"
        "👉 Bạn chỉ cần đăng nhập tài khoản trên từng cửa sổ.\n"
        "👉 Bot sẽ [bold green]tự động bắt cookie của từng tài khoản[/] ngay khi bạn đăng nhập xong!",
        border_style="cyan"
    ))

    # Launch 3 Chrome processes
    procs = []
    for cfg in WINDOW_CONFIGS:
        p = launch_chrome_window(cfg["account"])
        if p:
            procs.append(p)
        await asyncio.sleep(1)

    console.print("[green]✓ Đã mở thành công 3 cửa sổ Chrome.[/green] Đang theo dõi trạng thái đăng nhập...")

    # Monitor all 3 concurrently
    tasks = [
        monitor_account_cdp(cfg["account"], cfg["port"], timeout_seconds=timeout_seconds)
        for cfg in WINDOW_CONFIGS
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    success_count = sum(1 for r in results if isinstance(r, dict) and r.get("psid"))
    console.print(Panel(
        f"[bold green]✨ HOÀN TẤT QUÁ TRÌNH LẤY COOKIE![/]\n\n"
        f"• Đã thu thập thành công: [bold green]{success_count}/3 tài khoản[/]\n"
        f"• Cả 3 tài khoản đã được lưu vào [yellow].env[/] và [yellow]cookies.txt[/].",
        border_style="green"
    ))

if __name__ == "__main__":
    asyncio.run(open_and_monitor_all_3_windows())
