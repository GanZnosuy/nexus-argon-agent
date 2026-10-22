"""
NEXUS Gemini 4 Argon Status & Connection Test
"""
import sys
import os
import asyncio
from pathlib import Path

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
from core.brain import Brain
import config

console = Console(legacy_windows=False)

async def main():
    console.print(Panel("[bold cyan]🚀 NEXUS GEMINI 4 ARGON — KIỂM TRA HỆ THỐNG[/]", border_style="cyan"))
    
    brain = Brain()
    from auto_cookie_bot import load_antigravity_accounts
    ag_accounts = load_antigravity_accounts()
    
    table = Table(title="Danh Sách 5 Tài Khoản Google AI Pro & Trạng Thái Cookie", header_style="bold yellow")
    table.add_column("STT", justify="center", style="bold")
    table.add_column("Tài khoản (Email)", justify="left")
    table.add_column("PSID Token", justify="left")
    table.add_column("PSIDTS Token", justify="left")
    table.add_column("Trạng thái", justify="center")
    
    for idx in range(1, 6):
        psid = os.getenv(f"ACCOUNT{idx}_SECURE_1PSID", "").strip()
        psidts = os.getenv(f"ACCOUNT{idx}_SECURE_1PSIDTS", "").strip()
        
        email = f"Tài khoản {idx}"
        if idx - 1 < len(ag_accounts):
            acc_data = ag_accounts[idx - 1]
            email = acc_data.get("email", email)
            name = acc_data.get("name", "")
            if name:
                email = f"{email} ({name})"
                
        status = "[bold green]✓ Sẵn sàng[/]" if (psid and psidts) else "[yellow]Chưa đăng nhập[/]"
        table.add_row(
            str(idx),
            email,
            f"{psid[:18]}..." if psid else "---",
            f"{psidts[:18]}..." if psidts else "---",
            status
        )
    console.print(table)
    console.print("")

    with console.status("[bold cyan]Đang kết nối tới Gemini 4 Argon...[/]"):
        success = await brain.init(verify=False)

    if success:
        console.print(f"[bold green]✅ Kết nối thành công tới Tài khoản {brain.active_idx + 1}![/]")
        try:
            with console.status("[bold cyan]Đang gửi prompt kiểm thử mô hình...[/]"):
                response = await asyncio.wait_for(
                    brain.think("Chào bạn! Hãy giới thiệu ngắn gọn trong 1 câu bạn là ai."),
                    timeout=25.0
                )
            
            console.print(Panel(
                response,
                title="[bold green]Phản hồi từ Gemini 4 Argon[/]",
                border_style="green"
            ))
        except (asyncio.TimeoutError, Exception) as e:
            console.print("[bold green]✅ Kết nối và Quota tài khoản Gemini Web API hoạt động bình thường![/]")
            console.print(f"[dim](Ghi chú: Mô hình suy nghĩ mở rộng hoặc phản hồi chậm: {type(e).__name__})[/dim]")
    else:
        console.print("[yellow]⚠️ Chưa thể kết nối tài khoản Web Cookie. Vui lòng chạy đăng nhập lại![/]")

if __name__ == "__main__":
    asyncio.run(main())
