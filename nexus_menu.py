"""
NEXUS & ANTIGRAVITY — Interactive Multi-Account Manager & Login Hub
"""
import sys
import os
import asyncio
import subprocess
from pathlib import Path

# Setup Windows console encoding
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

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt

console = Console(legacy_windows=False)
PYTHON_EXE = sys.executable

def load_accounts():
    """Load accounts from Antigravity Tools."""
    try:
        from auto_cookie_bot import load_antigravity_accounts
        return load_antigravity_accounts()
    except Exception:
        return []

def get_account_status():
    """Check which accounts have cookies in .env."""
    from dotenv import dotenv_values
    env_path = PROJECT_ROOT / ".env"
    env_vals = dotenv_values(env_path) if env_path.exists() else {}
    
    status = {}
    for i in range(1, 6):
        psid = env_vals.get(f"ACCOUNT{i}_SECURE_1PSID", "").strip()
        psidts = env_vals.get(f"ACCOUNT{i}_SECURE_1PSIDTS", "").strip()
        status[i] = bool(psid and psidts)
    return status

def show_menu():
    accounts = load_accounts()
    acc_status = get_account_status()
    
    console.clear()
    console.print(Panel(
        "[bold cyan]🚀 NEXUS & ANTIGRAVITY — ĐĂNG NHẬP GOOGLE AI PRO & LẤY COOKIE[/]\n"
        "[dim]Hệ thống tự động hóa lấy Cookies & Xoay tua Token cho Gemini 4 Argon[/dim]",
        border_style="cyan"
    ))
    
    table = Table(title="Danh Sách Tài Khoản Google AI Pro trong Antigravity Tools", header_style="bold yellow")
    table.add_column("STT", justify="center", style="bold")
    table.add_column("Email", justify="left")
    table.add_column("Chủ tài khoản", justify="left")
    table.add_column("Trạng thái Web Cookie", justify="center")
    
    for idx in range(1, 6):
        email = f"Tài khoản {idx}"
        name = ""
        if idx - 1 < len(accounts):
            acc = accounts[idx - 1]
            email = acc.get("email", email)
            name = acc.get("name", "")
            
        is_ready = acc_status.get(idx, False)
        st_text = "[bold green]✓ Sẵn sàng[/]" if is_ready else "[yellow]Chưa có cookie[/]"
        table.add_row(str(idx), email, name, st_text)
        
    console.print(table)
    console.print("")
    
    console.print("[bold yellow]LỰA CHỌN THAO TÁC:[/]")
    for idx in range(1, 6):
        email = accounts[idx - 1].get("email", f"Tài khoản {idx}") if idx - 1 < len(accounts) else f"Tài khoản {idx}"
        prefix = "[bold green]✓[/]" if acc_status.get(idx, False) else "[yellow]?[/]"
        console.print(f"  [bold cyan][{idx}][/] {prefix} Đăng nhập và lấy cookie cho [bold white]{email}[/]")
        
    console.print("  [dim]─────────────────────────────────────────────────────────────────[/dim]")
    console.print("  [bold cyan][6][/] 🪟 Mở trình duyệt song song để đăng nhập cùng lúc")
    console.print("  [bold cyan][7][/] 📋 Nhập nhanh Cookie từ Clipboard / Extension Get cookies.txt")
    console.print("  [bold cyan][8][/] 🔄 Đồng bộ & Làm mới toàn bộ Cookies ngay lập tức")
    console.print("  [bold cyan][9][/] ⚡ Kiểm tra kết nối NEXUS Gemini 4 Argon")
    console.print("  [bold red][0][/] Thoát")
    console.print("")

def run_login_for_account(acc_idx: int):
    """Launch auto_cookie_bot as a dedicated subprocess for a specific account."""
    cmd = [PYTHON_EXE, str(PROJECT_ROOT / "auto_cookie_bot.py"), "--account", str(acc_idx)]
    subprocess.run(cmd)

def run_multi_login():
    cmd = [PYTHON_EXE, str(PROJECT_ROOT / "multi_login.py")]
    subprocess.run(cmd)

def run_quick_cookie():
    cmd = [PYTHON_EXE, str(PROJECT_ROOT / "quick_cookie.py")]
    subprocess.run(cmd)

def run_sync_now():
    daemon_script = Path.home() / "OneDrive" / "Desktop" / "CAIDATHETTHONG" / "gemini_cookie_daemon.py"
    if daemon_script.exists():
        console.print("[bold cyan]🔄 Đang làm mới và đồng bộ toàn bộ Cookies...[/]")
        subprocess.run([PYTHON_EXE, str(daemon_script), "--once"])
    else:
        console.print("[red]❌ Không tìm thấy script daemon![/]")

def run_test_status():
    test_script = PROJECT_ROOT / "test_argon_status.py"
    if test_script.exists():
        subprocess.run([PYTHON_EXE, str(test_script)])
    else:
        console.print("[red]❌ Không tìm thấy script kiểm tra![/]")

def main():
    while True:
        show_menu()
        choice = Prompt.ask(
            "[bold yellow]👉 Nhập lựa chọn của bạn (0-9)[/]",
            choices=["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"],
            default="9"
        )
        
        if choice == "0":
            console.print("[green]Tạm biệt! Hệ thống daemon tự động vẫn chạy ngầm để làm mới cookies mỗi 1h.[/green]")
            break
        elif choice in ("1", "2", "3", "4", "5"):
            acc_num = int(choice)
            console.print(f"\n[bold cyan]Đang chuẩn bị mở trình duyệt cho Tài khoản {acc_num}...[/]")
            run_login_for_account(acc_num)
            Prompt.ask("\n[dim]Nhấn Enter để quay lại Menu...[/dim]")
        elif choice == "6":
            run_multi_login()
            Prompt.ask("\n[dim]Nhấn Enter để quay lại Menu...[/dim]")
        elif choice == "7":
            run_quick_cookie()
            Prompt.ask("\n[dim]Nhấn Enter để quay lại Menu...[/dim]")
        elif choice == "8":
            run_sync_now()
            Prompt.ask("\n[dim]Nhấn Enter để quay lại Menu...[/dim]")
        elif choice == "9":
            run_test_status()
            Prompt.ask("\n[dim]Nhấn Enter để quay lại Menu...[/dim]")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nĐã hủy bởi người dùng.")
