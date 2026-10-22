"""
NEXUS Quick Cookie Importer.
Lightning-fast cookie extraction from 'Get cookies.txt LOCALLY' extension:
1. Direct from Clipboard (Copy button in extension)
2. Auto-detect newest exported file from Downloads folder
3. File parse from local cookies.txt
"""

import sys
import os
import re
import time
import subprocess
from pathlib import Path
from typing import Dict, Optional, Tuple
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

console = Console(legacy_windows=False)
PROJECT_ROOT = Path(__file__).resolve().parent
ENV_FILE = PROJECT_ROOT / ".env"
COOKIES_FILE = PROJECT_ROOT / "cookies.txt"
DOWNLOADS_DIR = Path(os.path.expanduser("~")) / "Downloads"

def parse_netscape_text(text: str) -> Dict[str, str]:
    """Extract cookies from Netscape HTTP Cookie text."""
    cookies = {}
    for line in text.strip().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) >= 7:
            name = parts[5].strip()
            val = parts[6].strip()
            cookies[name] = val
        elif "=" in line:
            # Handle key=value formats
            m = re.search(r"(__Secure-1PSID[A-Za-z0-9_-]*)\s*=\s*([^;]+)", line)
            if m:
                cookies[m.group(1)] = m.group(2).strip()

    return cookies

def get_clipboard_text() -> str:
    """Read text from Windows clipboard via PowerShell."""
    try:
        res = subprocess.run(
            ["powershell", "-NoProfile", "-Command", "Get-Clipboard"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5
        )
        return res.stdout.strip()
    except Exception as e:
        console.print(f"[red]Lỗi đọc clipboard:[/] {e}")
        return ""

def find_newest_downloaded_cookie_file(max_age_minutes: int = 15) -> Optional[Path]:
    """Find the most recently exported cookies.txt file in Downloads folder."""
    if not DOWNLOADS_DIR.exists():
        return None

    candidates = []
    for pattern in ["*cookie*.txt", "gemini*.txt", "cookies*.txt"]:
        for f in DOWNLOADS_DIR.glob(pattern):
            if f.is_file():
                candidates.append(f)

    if not candidates:
        return None

    # Sort by modification time descending
    candidates.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    newest = candidates[0]

    # Check age
    age_seconds = time.time() - newest.stat().st_mtime
    if age_seconds <= max_age_minutes * 60:
        return newest
    return None

def update_env_account(account_idx: int, psid: str, psidts: str) -> bool:
    """Update account credentials in .env file."""
    if not ENV_FILE.exists():
        console.print("[red]❌ File .env không tồn tại![/]")
        return False

    try:
        with open(ENV_FILE, "r", encoding="utf-8") as f:
            content = f.read()

        psid_key = f"ACCOUNT{account_idx}_SECURE_1PSID"
        psidts_key = f"ACCOUNT{account_idx}_SECURE_1PSIDTS"

        if re.search(rf"^{psid_key}\s*=", content, flags=re.MULTILINE):
            content = re.sub(rf"^{psid_key}\s*=.*$", f'{psid_key}="{psid}"', content, flags=re.MULTILINE)
        else:
            content += f'\n{psid_key}="{psid}"'

        if re.search(rf"^{psidts_key}\s*=", content, flags=re.MULTILINE):
            content = re.sub(rf"^{psidts_key}\s*=.*$", f'{psidts_key}="{psidts}"', content, flags=re.MULTILINE)
        else:
            content += f'\n{psidts_key}="{psidts}"'

        with open(ENV_FILE, "w", encoding="utf-8") as f:
            f.write(content)

        return True
    except Exception as e:
        console.print(f"[red]❌ Lỗi cập nhật .env:[/] {e}")
        return False

def sync_cookies_txt(psid: str, psidts: str, psidcc: str = ""):
    """Sync values to cookies.txt."""
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

        expiry = str(int(time.time()) + 31536000)
        new_lines.append(f".google.com\tTRUE\t/\tTRUE\t{expiry}\t__Secure-1PSID\t{psid}\n")
        new_lines.append(f".google.com\tTRUE\t/\tTRUE\t{expiry}\t__Secure-1PSIDTS\t{psidts}\n")
        if psidcc:
            new_lines.append(f".google.com\tTRUE\t/\tTRUE\t{expiry}\t__Secure-1PSIDCC\t{psidcc}\n")

        with open(COOKIES_FILE, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
    except Exception:
        pass

def apply_cookies(account_idx: int, cookies: Dict[str, str], source_name: str) -> bool:
    """Verify and apply parsed cookies to .env and system."""
    psid = cookies.get("__Secure-1PSID")
    psidts = cookies.get("__Secure-1PSIDTS")
    psidcc = cookies.get("__Secure-1PSIDCC", "")

    if not psid:
        console.print(f"[red]❌ Không tìm thấy __Secure-1PSID trong {source_name}![/]")
        return False

    if not psidts:
        console.print(f"[yellow]⚠️ Tìm thấy __Secure-1PSID nhưng thiếu __Secure-1PSIDTS trong {source_name}.[/]")

    ok = update_env_account(account_idx, psid, psidts or "")
    if ok:
        sync_cookies_txt(psid, psidts or "", psidcc)
        console.print(Panel(
            f"[bold green]⚡ CẬP NHẬT SIÊU TỐC THÀNH CÔNG CHO TÀI KHOẢN {account_idx}![/]\n\n"
            f"• [bold cyan]Nguồn:[/] {source_name}\n"
            f"• [bold cyan]__Secure-1PSID:[/] {psid[:25]}...\n"
            f"• [bold cyan]__Secure-1PSIDTS:[/] {(psidts[:25] + '...') if psidts else 'None'}\n"
            f"• [bold cyan]Trạng thái:[/] Đã lưu vào .env và đồng bộ cookies.txt\n"
            f"• [bold green]Argon 4 sẵn sàng sử dụng ngay lập tức![/]",
            border_style="green"
        ))
        return True
    return False

def import_from_clipboard(account_idx: int = 1) -> bool:
    """Import directly from clipboard copied from 'Get cookies.txt LOCALLY'."""
    console.print(f"[dim]Đang kiểm tra dữ liệu clipboard cho Tài khoản {account_idx}...[/dim]")
    clip_text = get_clipboard_text()
    if not clip_text:
        console.print("[yellow]Clipboard đang trống! Hãy bấm icon extension 'Get cookies.txt LOCALLY' -> bấm Copy rồi thử lại.[/]")
        return False

    cookies = parse_netscape_text(clip_text)
    return apply_cookies(account_idx, cookies, "Clipboard (Copy từ extension)")

def import_from_downloads(account_idx: int = 1) -> bool:
    """Import from newest cookies.txt exported to Downloads folder."""
    console.print(f"[dim]Đang quét thư mục Downloads cho Tài khoản {account_idx}...[/dim]")
    newest = find_newest_downloaded_cookie_file(max_age_minutes=20)
    if not newest:
        console.print(f"[yellow]Không tìm thấy file cookies mới nào trong {DOWNLOADS_DIR} (trong 20 phút qua).[/]")
        console.print("[dim]Gợi ý: Mở tab Gemini, bấm extension 'Get cookies.txt LOCALLY' -> bấm Export/Download, sau đó chạy lại lệnh.[/dim]")
        return False

    console.print(f"[cyan]Tìm thấy file mới nhất: {newest.name}[/]")
    try:
        with open(newest, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        cookies = parse_netscape_text(content)
        return apply_cookies(account_idx, cookies, f"Tệp tải về ({newest.name})")
    except Exception as e:
        console.print(f"[red]Lỗi đọc file {newest}:[/] {e}")
        return False

def import_from_local_file(file_path: str, account_idx: int = 1) -> bool:
    """Import from a specific local file."""
    path = Path(file_path).resolve()
    if not path.exists():
        console.print(f"[red]Không tìm thấy tệp: {file_path}[/]")
        return False
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
    cookies = parse_netscape_text(content)
    return apply_cookies(account_idx, cookies, str(path.name))

def watch_downloads_loop(account_idx: int = 1):
    """Background watcher for automatic zero-click updates from Downloads."""
    console.print(Panel(
        f"[bold cyan]👀 ĐANG THEO DÕI THƯ MỤC DOWNLOADS — TÀI KHOẢN {account_idx}[/]\n\n"
        f"Mỗi khi bạn ở tab Gemini và bấm [bold yellow]'Export'[/] trên extension [bold green]'Get cookies.txt LOCALLY'[/],\n"
        f"Hệ thống sẽ [bold green]tự động phát hiện và cập nhật vào NEXUS ngay lập tức[/]!\n\n"
        f"[dim](Nhấn Ctrl+C để dừng theo dõi)[/]",
        border_style="cyan"
    ))

    last_seen_mtime = 0
    newest = find_newest_downloaded_cookie_file(max_age_minutes=1)
    if newest:
        last_seen_mtime = newest.stat().st_mtime

    try:
        while True:
            time.sleep(1.0)
            candidate = find_newest_downloaded_cookie_file(max_age_minutes=1)
            if candidate and candidate.stat().st_mtime > last_seen_mtime:
                last_seen_mtime = candidate.stat().st_mtime
                time.sleep(0.5)  # Let file finish writing
                import_from_downloads(account_idx)
    except KeyboardInterrupt:
        console.print("\n[dim]Đã dừng theo dõi.[/]")

def main():
    """Main CLI entry point."""
    account_idx = 1
    action = "auto"  # clip, downloads, watch, file

    for i, a in enumerate(sys.argv):
        if a in ("-a", "--account") and i + 1 < len(sys.argv):
            try: account_idx = int(sys.argv[i + 1])
            except ValueError: pass
        elif a in ("1", "2", "3"):
            account_idx = int(a)
        elif a in ("--clip", "-c", "clip"):
            action = "clip"
        elif a in ("--downloads", "-d", "downloads"):
            action = "downloads"
        elif a in ("--watch", "-w", "watch"):
            action = "watch"

    if action == "clip":
        import_from_clipboard(account_idx)
    elif action == "downloads":
        import_from_downloads(account_idx)
    elif action == "watch":
        watch_downloads_loop(account_idx)
    else:
        # Auto mode: try clipboard first, then downloads
        console.print(Panel(
            f"[bold cyan]⚡ NEXUS FAST COOKIE IMPORTER — TÀI KHOẢN {account_idx}[/]\n"
            f"[dim]Tương thích 100% với extension 'Get cookies.txt LOCALLY'[/]",
            border_style="cyan"
        ))
        
        # Try clipboard
        clip = get_clipboard_text()
        if "__Secure-1PSID" in clip:
            console.print("[green]Phát hiện cookie trong Clipboard! Đang nạp...[/]")
            import_from_clipboard(account_idx)
            return

        # Try downloads
        downloaded = find_newest_downloaded_cookie_file(max_age_minutes=15)
        if downloaded:
            console.print(f"[green]Phát hiện file cookie trong Downloads ({downloaded.name})! Đang nạp...[/]")
            import_from_downloads(account_idx)
            return

        console.print(
            "Chọn cách lấy cookie nhanh:\n"
            "  1. [bold yellow]Clipboard[/]: Mở extension 'Get cookies.txt LOCALLY' -> bấm Copy -> chạy lại lệnh này.\n"
            "  2. [bold yellow]Downloads[/]: Mở extension -> bấm Export/Download -> chạy lại lệnh này.\n"
            "  3. [bold yellow]Theo dõi ngầm (Watch)[/]: Tự động cập nhật mỗi khi bấm Export.\n"
        )
        choice = Prompt.ask("Bạn muốn chọn cách nào?", choices=["1", "2", "3"], default="1")
        if choice == "1":
            import_from_clipboard(account_idx)
        elif choice == "2":
            import_from_downloads(account_idx)
        elif choice == "3":
            watch_downloads_loop(account_idx)

if __name__ == "__main__":
    main()
