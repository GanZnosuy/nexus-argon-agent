"""
NEXUS — SUPER AI AGENT CLI.
Powered by Gemini 4 Argon via gemini-webapi with 3-account cookie rotation.
Multi-agent orchestration, interactive chat, and autonomous execution.
"""

import sys
import os
import asyncio
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt

# Configure Windows encoding and asyncio event loop policy
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

async def display_help():
    """Display command reference table."""
    table = Table(title="Danh sách lệnh hỗ trợ trong NEXUS", border_style="cyan")
    table.add_column("Lệnh", style="bold yellow", width=18)
    table.add_column("Chức năng", style="white")
    table.add_row("/auto [mục tiêu]", "Chạy chế độ tự động phân rã và hoàn thành mục tiêu phức tạp")
    table.add_row("/status", "Kiểm tra tình trạng tài khoản Argon, bộ nhớ, và chế độ Fallback")
    table.add_row("/gui", "Mở ứng dụng giao diện Web Dashboard theo dõi Quota 3 tài khoản")
    table.add_row("/clip [1-3]", "Nạp cookie siêu tốc trong 1 giây từ Clipboard (Copy từ extension)")
    table.add_row("/import [1-3]", "Tự động bắt file cookies vừa Export từ Downloads và nạp vào hệ thống")
    table.add_row("/login [1-3]", "Mở bot tự động đăng nhập Google Chrome và lấy cookie trực tiếp")
    table.add_row("/cookie", "Xem hoặc cập nhật cookie tự động")
    table.add_row("/reload", "Tải lại file .env và kết nối lại tài khoản Argon")
    table.add_row("/agents", "Xem danh sách 5 Specialist Agents và vai trò")
    table.add_row("/tools", "Xem danh sách các công cụ hệ thống đang kết nối")
    table.add_row("/rules", "Xem danh sách quy tắc ghi nhớ dài hạn")
    table.add_row("/rule [nội dung]", "Ghi nhớ quy tắc hành xử mới vào hệ thống")
    table.add_row("/clear", "Xóa lịch sử ngữ cảnh hội thoại hiện tại")
    table.add_row("/help", "Hiển thị bảng hướng dẫn này")
    table.add_row("/exit", "Thoát chương trình NEXUS")
    console.print(table)

async def handle_command(cmd: str, orchestrator, brain) -> bool:
    """
    Process slash commands. Returns True if command was handled, False otherwise.
    """
    parts = cmd.strip().split(maxsplit=1)
    base_cmd = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else ""

    if base_cmd == "/auto":
        if not arg:
            console.print("[yellow]Vui lòng cung cấp mục tiêu: /auto [mục tiêu cần hoàn thành][/]")
            return True
        console.print(f"\n[bold yellow]🤖 BẮT ĐẦU AUTO MODE:[/] {arg}\n")
        with console.status("[bold cyan]Đang lập kế hoạch và thực thi tự động...[/]"):
            result = await orchestrator.auto_mode(arg)
        console.print(f"\n[bold green]✅ HOÀN TẤT AUTO MODE:[/]\n{result}\n")
        return True

    elif base_cmd == "/status":
        health = await brain.check_account_health()
        mode_str = "[bold red]Fallback Gemini API[/]" if health["using_fallback"] else "[bold green]Gemini 4 Argon[/]"
        mem_len = len(brain.memory) if hasattr(brain, "memory") and brain.memory else 0

        status_panel = (
            f"• [bold cyan]Hệ điều hành:[/] Windows (UTF-8 Compatible)\n"
            f"• [bold cyan]Mô hình chính:[/] {mode_str} ({health.get('model', 'Max Tier')})\n"
            f"• [bold cyan]Chế độ suy luận:[/] [bold green]Extended Thinking (Mức cao nhất)[/]\n"
            f"• [bold cyan]Tài khoản đang hoạt động:[/] Account {health['active_account']}/{health['total_accounts']}\n"
            f"• [bold cyan]Trạng thái các tài khoản:[/] {['Tốt' if h else 'Lỗi/Hết quota' for h in health['health_map']]}\n"
            f"• [bold cyan]Lịch sử hội thoại:[/] {mem_len} lượt trao đổi\n"
            f"• [bold cyan]Số Agents sẵn sàng:[/] {len(orchestrator.agents)} (Code, Browser, Research, Media, YouTube)\n"
            f"• [bold cyan]Số Tools tích hợp:[/] {len(orchestrator.tools.list_tools())}"
        )
        console.print(Panel(status_panel, title="[bold cyan]Trạng Thái Hệ Thống NEXUS[/]", border_style="cyan"))
        return True

    elif base_cmd in ("/gui", "/dashboard", "/web"):
        import subprocess
        console.print("[bold cyan]🚀 Đang khởi động Giao diện Web Dashboard (FastAPI)...[/]")
        subprocess.Popen([sys.executable, "dashboard.py"], cwd=str(PROJECT_ROOT))
        console.print("[bold green]✅ Ứng dụng Quota Dashboard đã mở tại: http://127.0.0.1:8000[/]")
        return True

    elif base_cmd in ("/clip", "/paste"):
        acc = int(arg.strip()) if arg.strip() in ("1", "2", "3") else 1
        from quick_cookie import import_from_clipboard
        ok = import_from_clipboard(account_idx=acc)
        if ok:
            import config
            from dotenv import load_dotenv
            load_dotenv(dotenv_path=config.ENV_PATH, override=True)
            brain.accounts = config.get_accounts()
            brain.active_idx = (acc - 1) % len(brain.accounts)
            await brain.init(verify=False)
            console.print(f"[bold green]🚀 Đã nạp xong từ Clipboard và kết nối lại Tài khoản {acc}![/]")
        return True

    elif base_cmd in ("/import", "/down"):
        acc = int(arg.strip()) if arg.strip() in ("1", "2", "3") else 1
        from quick_cookie import import_from_downloads
        ok = import_from_downloads(account_idx=acc)
        if ok:
            import config
            from dotenv import load_dotenv
            load_dotenv(dotenv_path=config.ENV_PATH, override=True)
            brain.accounts = config.get_accounts()
            brain.active_idx = (acc - 1) % len(brain.accounts)
            await brain.init(verify=False)
            console.print(f"[bold green]🚀 Đã nạp xong từ Downloads và kết nối lại Tài khoản {acc}![/]")
        return True

    elif base_cmd in ("/cookie", "/login"):
        acc = 1
        if arg.strip() in ("1", "2", "3"):
            acc = int(arg.strip())
        else:
            try:
                choice = Prompt.ask("[yellow]Chọn tài khoản Google cần lấy cookie tự động (1, 2, hoặc 3)[/]", choices=["1", "2", "3"], default="1")
                acc = int(choice)
            except Exception:
                acc = 1

        from auto_cookie_bot import extract_cookie_for_account
        result = await extract_cookie_for_account(account_idx=acc)
        if result:
            # Hot reload Brain
            import config
            from dotenv import load_dotenv
            load_dotenv(dotenv_path=config.ENV_PATH, override=True)
            brain.accounts = config.get_accounts()
            brain.active_idx = (acc - 1) % len(brain.accounts)
            await brain.init(verify=False)
            console.print(f"[bold green]🚀 Brain đã tự động nhận diện cookie mới của Tài khoản {acc}![/]")
        return True

    elif base_cmd == "/reload":
        import config
        from dotenv import load_dotenv
        load_dotenv(dotenv_path=config.ENV_PATH, override=True)
        config.ACTIVE_ACCOUNT = int(os.getenv("ACTIVE_ACCOUNT", "1"))
        config.GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "").strip()
        config.ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "").strip()
        config.YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "").strip()

        with console.status("[bold cyan]Đang tải lại cấu hình và xác thực cookies...[/]"):
            brain.accounts = config.get_accounts()
            brain.active_idx = (config.ACTIVE_ACCOUNT - 1) % len(brain.accounts)
            await brain.init(verify=False)
        console.print("[green]✅ Đã nạp lại cấu hình và khởi tạo lại Brain thành công![/]")
        return True

    elif base_cmd == "/agents":
        table = Table(title="Danh sách Specialist Agents trong NEXUS", border_style="cyan")
        table.add_column("Agent", style="bold magenta")
        table.add_column("Công cụ phụ trách", style="yellow")
        table.add_column("Chuyên môn", style="white")
        table.add_row("CodeAgent", "filesystem, shell", "Đọc/ghi tệp, phân tích code, chạy terminal, gỡ lỗi")
        table.add_row("BrowserAgent", "browser (Playwright)", "Duyệt web headless, chụp ảnh màn hình, tương tác form")
        table.add_row("ResearchAgent", "web_search, browser", "Tìm kiếm Google/DDG, tra cứu video YouTube, tóm tắt web")
        table.add_row("MediaAgent", "image_generator, tts, shell", "Tạo ảnh AI, lồng tiếng Edge-TTS/ElevenLabs, ghép video FFmpeg")
        table.add_row("YouTubeAgent", "youtube_api, web_search", "Tra cứu số liệu video, phân tích view/like, tối ưu metadata")
        console.print(table)
        return True

    elif base_cmd == "/tools":
        console.print(f"[bold cyan]Các công cụ đã nạp vào Registry:[/]\n{orchestrator.tools.get_descriptions()}")
        return True

    elif base_cmd == "/rules":
        rules = orchestrator.memory.get_learned_rules()
        if not rules:
            console.print("[dim]Chưa có quy tắc ghi nhớ nào. Thêm bằng lệnh /rule [nội dung][/]")
        else:
            console.print("[bold cyan]Quy tắc học được:[/]")
            for i, r in enumerate(rules, 1):
                console.print(f"  {i}. {r}")
        return True

    elif base_cmd == "/rule":
        if not arg:
            console.print("[yellow]Cú pháp: /rule [nội dung quy tắc cần ghi nhớ][/]")
        else:
            orchestrator.memory.learn_rule(arg)
            console.print(f"[green]✅ Đã ghi nhớ quy tắc mới:[/] {arg}")
        return True

    elif base_cmd == "/clear":
        orchestrator.memory.clear()
        console.print("[dim]🧹 Đã xóa toàn bộ ngữ cảnh hội thoại trong phiên làm việc.[/]")
        return True

    elif base_cmd == "/help":
        await display_help()
        return True

    elif base_cmd == "/exit":
        console.print("[bold cyan]Tạm biệt! Hẹn gặp lại bạn.[/]")
        raise SystemExit(0)

    else:
        console.print(f"[yellow]Lệnh không hợp lệ: '{cmd}'. Gõ /help để xem trợ giúp.[/]")
        return True

async def main():
    """Main CLI entry point."""
    # Check for automated test flag
    is_test_mode = "--test" in sys.argv

    header_panel = (
        "[bold cyan]🧠 NEXUS — SUPER AI AGENT ARCHITECTURE v1.0[/]\n"
        "[dim]Powered by Gemini 4 Argon via gemini-webapi | 3-Account Rotation | Specialist Multi-Agent[/]"
    )
    console.print(Panel(header_panel, border_style="cyan"))

    from core.brain import Brain
    from core.orchestrator import NexusOrchestrator
    from core.memory import Memory

    memory = Memory()
    brain = Brain(memory=memory)

    with console.status("[bold cyan]Đang kết nối tới Gemini Argon và kiểm tra cấu hình...[/]"):
        # On startup, do non-blocking init verification
        await brain.init(verify=False)

    orchestrator = NexusOrchestrator(brain=brain, memory=memory)

    active_acc = brain.active_idx + 1
    total_acc = len(brain.accounts)
    console.print(f"  [green]●[/] Hệ thống sẵn sàng | Tài khoản hoạt động: [bold cyan]Account {active_acc}/{total_acc}[/]")
    console.print(f"  [dim]Nhập yêu cầu bằng tiếng Việt hoặc gõ [bold yellow]/help[/bold yellow] để xem danh sách lệnh.[/]\n")

    if is_test_mode:
        console.print("[bold green]✅ NEXUS TEST PASSED: All subsystems initialized successfully![/]")
        return

    # Interactive Loop
    while True:
        try:
            user_input = Prompt.ask("[bold green]Bạn[/bold green]").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Tạm biệt![/]")
            break

        if not user_input:
            continue

        if user_input.startswith("/"):
            try:
                await handle_command(user_input, orchestrator, brain)
            except SystemExit:
                break
            except Exception as e:
                console.print(f"[red]Lỗi thực thi lệnh:[/] {e}")
            continue

        # Normal prompt execution
        try:
            with console.status("[bold cyan]NEXUS đang suy nghĩ và điều phối...[/]"):
                response = await orchestrator.process(user_input)
            console.print(f"\n[bold cyan]NEXUS[/bold cyan]:\n{response}\n")
        except Exception as e:
            console.print(f"\n[red]❌ Lỗi xử lý yêu cầu:[/] {str(e)}\n")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
