"""
NEXUS Auto Cookie Extraction Bot.
Automates Google Account login and cookie extraction using Playwright & Chrome.
Captures __Secure-1PSID, __Secure-1PSIDTS, __Secure-1PSIDCC and automatically updates .env and cookies.txt.
"""

import sys
import os
import json
import asyncio
import time
import re
from pathlib import Path
from typing import Dict, Optional, Tuple
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

# Configure UTF-8 for Windows console
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
ENV_FILE = PROJECT_ROOT / ".env"
COOKIES_FILE = PROJECT_ROOT / "cookies.txt"
PROFILES_DIR = PROJECT_ROOT / "auth_profiles"
PROFILES_DIR.mkdir(exist_ok=True)

try:
    from playwright.async_api import async_playwright
except ImportError:
    async_playwright = None

def find_chrome_executable() -> Optional[str]:
    """Find installed Google Chrome or Edge path."""
    candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return None

def update_env_file(account_idx: int, psid: str, psidts: str) -> bool:
    """Update or append account cookies in .env without losing existing keys."""
    if not ENV_FILE.exists():
        console.print("[red]❌ Không tìm thấy file .env![/]")
        return False

    try:
        with open(ENV_FILE, "r", encoding="utf-8") as f:
            content = f.read()

        psid_key = f"ACCOUNT{account_idx}_SECURE_1PSID"
        psidts_key = f"ACCOUNT{account_idx}_SECURE_1PSIDTS"

        # Regex replace if key exists
        if re.search(rf"^{psid_key}\s*=", content, flags=re.MULTILINE):
            content = re.sub(
                rf"^{psid_key}\s*=.*$",
                f"{psid_key}=\"{psid}\"",
                content,
                flags=re.MULTILINE
            )
        else:
            content += f"\n{psid_key}=\"{psid}\""

        if re.search(rf"^{psidts_key}\s*=", content, flags=re.MULTILINE):
            content = re.sub(
                rf"^{psidts_key}\s*=.*$",
                f"{psidts_key}=\"{psidts}\"",
                content,
                flags=re.MULTILINE
            )
        else:
            content += f"\n{psidts_key}=\"{psidts}\""

        with open(ENV_FILE, "w", encoding="utf-8") as f:
            f.write(content)

        return True
    except Exception as e:
        console.print(f"[red]❌ Lỗi khi cập nhật file .env:[/] {e}")
        return False

def update_cookies_txt(psid: str, psidts: str, psidcc: str = ""):
    """Update cookies.txt with new Netscape cookie records."""
    if not COOKIES_FILE.exists():
        return

    try:
        with open(COOKIES_FILE, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()

        new_lines = []
        skip_names = {"__Secure-1PSID", "__Secure-1PSIDTS", "__Secure-1PSIDCC"}

        for line in lines:
            if line.startswith("#") or not line.strip():
                new_lines.append(line)
                continue
            parts = line.strip().split("\t")
            if len(parts) >= 7 and parts[5] in skip_names:
                continue
            new_lines.append(line)

        # Append new values
        expiry = str(int(time.time()) + 31536000)  # 1 year
        new_lines.append(f".google.com\tTRUE\t/\tTRUE\t{expiry}\t__Secure-1PSID\t{psid}\n")
        new_lines.append(f".google.com\tTRUE\t/\tTRUE\t{expiry}\t__Secure-1PSIDTS\t{psidts}\n")
        if psidcc:
            new_lines.append(f".google.com\tTRUE\t/\tTRUE\t{expiry}\t__Secure-1PSIDCC\t{psidcc}\n")

        with open(COOKIES_FILE, "w", encoding="utf-8") as f:
            f.writelines(new_lines)

    except Exception as e:
        console.print(f"[dim][Lỗi cập nhật cookies.txt]: {e}[/dim]")

async def extract_cookie_for_account(account_idx: int = 1, timeout_seconds: int = 300) -> Optional[Dict[str, str]]:
    """
    Open interactive Chrome window, let user log in, automatically sniff cookies,
    and save them to .env and cookies.txt.
    """
    if not async_playwright:
        console.print("[red]❌ Playwright chưa được cài đặt![/]")
        return None

    profile_dir = PROFILES_DIR / f"account_{account_idx}"
    profile_dir.mkdir(exist_ok=True)

    chrome_path = find_chrome_executable()
    launch_kwargs = {
        "user_data_dir": str(profile_dir),
        "headless": False,
        "args": [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--start-maximized"
        ],
        "ignore_default_args": ["--enable-automation"]
    }
    if chrome_path:
        launch_kwargs["executable_path"] = chrome_path

    console.print(Panel(
        f"[bold cyan]🤖 NEXUS AUTO COOKIE BOT — TÀI KHOẢN {account_idx}[/]\n\n"
        f"1. Cửa sổ Google Chrome đang được mở ra.\n"
        f"2. Bạn chỉ cần [bold yellow]đăng nhập tài khoản Google[/] trên cửa sổ đó.\n"
        f"3. Bot sẽ [bold green]tự động phát hiện khi đăng nhập xong[/], trích xuất cookies và cập nhật vào hệ thống!\n"
        f"   [dim](Thời gian chờ: {timeout_seconds} giây)[/]",
        border_style="cyan"
    ))

    captured_cookies = {}

    async with async_playwright() as p:
        try:
            context = await p.chromium.launch_persistent_context(**launch_kwargs)
            page = context.pages[0] if context.pages else await context.new_page()

            console.print("[dim]Đang điều hướng tới Google Gemini (https://gemini.google.com/app)...[/dim]")
            await page.goto("https://gemini.google.com/app", timeout=60000)

            start_time = time.time()
            with console.status(f"[bold cyan]Đang chờ bạn đăng nhập Tài khoản {account_idx}...[/]") as status:
                while time.time() - start_time < timeout_seconds:
                    await asyncio.sleep(1.5)

                    try:
                        cookies = await context.cookies(["https://gemini.google.com", "https://google.com"])
                        cookie_dict = {c["name"]: c["value"] for c in cookies}

                        psid = cookie_dict.get("__Secure-1PSID", "")
                        psidts = cookie_dict.get("__Secure-1PSIDTS", "")
                        psidcc = cookie_dict.get("__Secure-1PSIDCC", "")

                        current_url = page.url

                        # Check if authenticated session cookies are captured
                        if psid and psidts and ("gemini.google.com" in current_url or "myaccount.google.com" in current_url):
                            captured_cookies = {
                                "psid": psid,
                                "psidts": psidts,
                                "psidcc": psidcc
                            }
                            break
                    except Exception:
                        pass

            if not captured_cookies:
                console.print(f"[red]❌ Hết thời gian chờ ({timeout_seconds}s) hoặc chưa hoàn tất đăng nhập.[/]")
                await context.close()
                return None

            console.print(f"\n[bold green]🎉 BẮT ĐƯỢC COOKIES THÀNH CÔNG CHO TÀI KHOẢN {account_idx}![/]")
            console.print(f"  • __Secure-1PSID: [dim]{captured_cookies['psid'][:20]}...[/dim]")
            console.print(f"  • __Secure-1PSIDTS: [dim]{captured_cookies['psidts'][:20]}...[/dim]")

            # Update .env
            env_updated = update_env_file(account_idx, captured_cookies["psid"], captured_cookies["psidts"])
            if env_updated:
                console.print(f"[green]✓ Đã cập nhật thành công vào file .env cho ACCOUNT{account_idx}![/]")

            # Update cookies.txt
            update_cookies_txt(captured_cookies["psid"], captured_cookies["psidts"], captured_cookies["psidcc"])
            console.print(f"[green]✓ Đã đồng bộ file cookies.txt![/]")

            # Đồng bộ sang daemon nếu có trên máy người dùng
            try:
                sync_script = Path.home() / "OneDrive" / "Desktop" / "CAIDATHETTHONG" / "gemini_cookie_daemon.py"
                if sync_script.exists():
                    import subprocess
                    subprocess.run(
                        [sys.executable, str(sync_script), "--once"],
                        capture_output=True,
                        text=True,
                        encoding="utf-8"
                    )
                    console.print("[bold green]✓ Đã đồng bộ toàn diện sang CAIDATHETTHONG, gemini_cookies.json & germini![/]")
            except Exception as e:
                console.print(f"[dim][Lỗi đồng bộ mở rộng]: {e}[/dim]")

            # Quick verification with GeminiClient
            console.print("[dim]Đang kiểm tra kết nối tới Gemini 4 Argon...[/dim]")
            try:
                from gemini_webapi import GeminiClient
                test_client = GeminiClient(secure_1psid=captured_cookies["psid"], secure_1psidts=captured_cookies["psidts"])
                await test_client.init(timeout=25)
                models = test_client.list_models()
                models_str = ", ".join(m.model_name for m in models) if models else "Gemini Argon"
                console.print(f"[bold green]✅ XÁC THỰC THÀNH CÔNG:[/] Mô hình sẵn sàng: [cyan]{models_str}[/]")
            except Exception as e:
                console.print(f"[yellow]⚠️ Lưu ý kiểm tra:[/ {e}")

            # Close browser
            await asyncio.sleep(2)
            await context.close()

            console.print(Panel(
                f"[bold green]✨ HOÀN TẤT![/]\n"
                f"Tài khoản {account_idx} đã được cập nhật cookie mới nhất và sẵn sàng phục vụ!\n"
                f"Lần sau khi cần làm mới, daemon chạy ngầm sẽ tự động gia hạn mỗi 1 giờ.",
                border_style="green"
            ))

            return captured_cookies

        except Exception as e:
            console.print(f"[red]❌ Lỗi trong quá trình chạy bot:[/] {e}")
            return None

def load_antigravity_accounts():
    """Đọc danh sách tài khoản từ Antigravity Tools (~/.antigravity_tools/accounts.json)."""
    p = Path(os.path.expanduser(r"~/.antigravity_tools/accounts.json"))
    if p.exists():
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("accounts", [])
        except Exception:
            pass
    return []

def main():
    """CLI entry point for auto_cookie_bot.py."""
    accounts = load_antigravity_accounts()
    account_arg = None

    if len(sys.argv) > 1:
        for i, a in enumerate(sys.argv):
            if a in ("--account", "-a") and i + 1 < len(sys.argv):
                try:
                    account_arg = int(sys.argv[i + 1])
                except ValueError:
                    pass
            elif a in ("1", "2", "3", "4", "5"):
                account_arg = int(a)

    if not account_arg:
        console.print(Panel("[bold cyan]🤖 NEXUS GOOGLE AI PRO COOKIE AUTO-EXTRACTOR[/]", border_style="cyan"))
        console.print("[bold yellow]Danh sách các tài khoản Google AI PRO trong Antigravity Tools:[/]")
        choices = []
        for idx in range(1, 6):
            choices.append(str(idx))
            acc_info = accounts[idx - 1] if idx - 1 < len(accounts) else {}
            email = acc_info.get("email", f"Tài khoản {idx}")
            name = acc_info.get("name", "")
            console.print(f"  [bold green][{idx}][/] {email} [dim]({name})[/dim]")
        console.print("")

        choice = Prompt.ask(
            "[bold yellow]Chọn tài khoản bạn muốn đăng nhập để lấy cookie (1-5)[/]",
            choices=choices,
            default="1"
        )
        account_arg = int(choice)

    asyncio.run(extract_cookie_for_account(account_idx=account_arg))

if __name__ == "__main__":
    main()
