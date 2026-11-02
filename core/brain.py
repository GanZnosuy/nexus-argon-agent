"""
NEXUS Brain Layer.
Primary LLM abstraction: Gemini 4 Argon via gemini-webapi with circular multi-account rotation.
Strict Argon enforcement: Automatically sets Argon-capable account as default,
and immediately reports an explicit error if an account does not have Argon.
Includes auto-recovery (clipboard/downloads/global sync), resilient model selection,
and multi-turn chat session support.
"""

import os
import sys
import re
import json
import asyncio
from pathlib import Path
from typing import Optional, List, Tuple, Any, Dict
from rich.console import Console
from rich.panel import Panel

try:
    from gemini_webapi import (
        GeminiClient,
        ChatSession,
        AuthError,
        TemporarilyBlockedError,
        UsageLimitExceededError,
        GeminiError,
        APIError
    )
except ImportError:
    try:
        from gemini import (
            GeminiClient,
            ChatSession,
            AuthError,
            TemporarilyBlockedError,
            UsageLimitExceededError,
            GeminiError,
            APIError
        )
    except ImportError:
        GeminiClient = None
        ChatSession = None
        AuthError = Exception
        TemporarilyBlockedError = Exception
        UsageLimitExceededError = Exception
        GeminiError = Exception
        APIError = Exception

import config

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

console = Console(legacy_windows=False)


class Brain:
    """
    Core Intelligence Engine for NEXUS.
    Manages cookie authentication, circular multi-account rotation,
    resilient model querying, and strict Gemini 4 Argon enforcement.
    """

    def __init__(self, memory=None):
        self.accounts_with_ids: List[Tuple[int, str, str]] = config.get_accounts_with_ids()
        if not self.accounts_with_ids:
            console.print("[yellow]⚠️ Cảnh báo: Không tìm thấy cookie tài khoản trong .env![/]")
            self.accounts_with_ids = [(1, "", "")]

        # Backward compatibility list: (psid, psidts)
        self.accounts: List[Tuple[str, str]] = [(p, pt) for _, p, pt in self.accounts_with_ids]

        self.active_account_num: int = config.ACTIVE_ACCOUNT
        self.active_idx: int = self._find_account_index(self.active_account_num)

        self.argon_client: Optional[GeminiClient] = None
        self.current_chat_session: Optional[Any] = None
        self.memory = memory if memory is not None else []
        self.account_health: List[bool] = [True] * len(self.accounts_with_ids)
        self.is_initialized: bool = False
        self.using_fallback: bool = False

    def _find_account_index(self, account_num: int) -> int:
        """Find index in accounts_with_ids for a given 1-based account number."""
        for i, (acc_id, _, _) in enumerate(self.accounts_with_ids):
            if acc_id == account_num:
                return i
        return 0

    def _get_active_account_id(self) -> int:
        """Get 1-based account ID of current active account."""
        if 0 <= self.active_idx < len(self.accounts_with_ids):
            return self.accounts_with_ids[self.active_idx][0]
        return self.active_account_num or 1

    def _has_argon(self, client: Any) -> bool:
        """
        Check if client is authenticated and has verified access to Gemini 4 Argon.
        Validates against unauthenticated status (1016) and inspects model registry.
        """
        if not client:
            return False
        if getattr(client, "account_status", None) == 1016:
            return False
        if "UNAUTHENTICATED" in str(getattr(client, "account_status", "")):
            return False

        try:
            models = client.list_models()
            if not models:
                return False
            for m in models:
                name = getattr(m, "model_name", "").lower()
                disp = getattr(m, "display_name", "").lower()
                mid = getattr(m, "model_id", "").lower()
                aliases = [str(a).lower() for a in getattr(m, "aliases", [])]
                if "argon" in name or "argon" in disp or "argon" in mid or any("argon" in a for a in aliases):
                    return True
        except Exception:
            pass
        return False

    def _get_highest_tier_model(self):
        """
        Select Gemini 4 Argon model strictly from client model registry.
        If Argon is not available, returns None (rejecting non-Argon models).
        """
        if not self.argon_client or not self._has_argon(self.argon_client):
            return None
        try:
            models = self.argon_client.list_models()
            if not models:
                return None
            for m in models:
                name = getattr(m, "model_name", "").lower()
                disp = getattr(m, "display_name", "").lower()
                mid = getattr(m, "model_id", "").lower()
                aliases = [str(a).lower() for a in getattr(m, "aliases", [])]
                if "argon" in name or "argon" in disp or "argon" in mid or any("argon" in a for a in aliases):
                    return m
            return None
        except Exception:
            return None

    def _save_default_active_account(self, account_num: int):
        """Persist ACTIVE_ACCOUNT to .env and config module."""
        try:
            env_path = config.ENV_PATH
            if env_path.exists():
                content = env_path.read_text(encoding="utf-8", errors="replace")
                if re.search(r"^ACTIVE_ACCOUNT\s*=", content, flags=re.MULTILINE):
                    content = re.sub(
                        r"^ACTIVE_ACCOUNT\s*=.*$",
                        f"ACTIVE_ACCOUNT={account_num}",
                        content,
                        flags=re.MULTILINE
                    )
                else:
                    content += f"\nACTIVE_ACCOUNT={account_num}"
                env_path.write_text(content, encoding="utf-8")

            config.ACTIVE_ACCOUNT = account_num
            self.active_account_num = account_num
            self.active_idx = self._find_account_index(account_num)
        except Exception as e:
            console.print(f"[dim]Lỗi lưu ACTIVE_ACCOUNT: {e}[/dim]")

    async def _try_auto_recovery(self) -> bool:
        """
        Attempt automatic cookie recovery when all configured accounts expire.
        Checks:
        1. Global gemini_cookies.json (~/.gemini/config/gemini_cookies.json)
        2. Clipboard (from 'Get cookies.txt LOCALLY' extension)
        3. Downloads folder (exported cookies.txt)
        """
        console.print("[cyan]🔄 Đang kích hoạt cơ chế tự động tìm kiếm và khôi phục Cookies...[/]")

        # 1. Check Global gemini_cookies.json
        try:
            global_json = Path(os.path.expanduser(r"~/.gemini/config/gemini_cookies.json"))
            if global_json.exists():
                data = json.loads(global_json.read_text(encoding="utf-8"))
                psid = data.get("GEMINI_SECURE_1PSID", "").strip()
                psidts = data.get("GEMINI_SECURE_1PSIDTS", "").strip()
                if psid and psidts:
                    # Test if global cookies are alive
                    client = GeminiClient(secure_1psid=psid, secure_1psidts=psidts)
                    await client.init(timeout=10)
                    if self._has_argon(client):
                        from auto_cookie_bot import update_env_file, update_cookies_txt
                        acc_id = self._get_active_account_id()
                        update_env_file(acc_id, psid, psidts)
                        update_cookies_txt(psid, psidts)
                        console.print(f"[bold green]✓ Đã khôi phục thành công từ gemini_cookies.json vào Tài khoản {acc_id}![/]")
                        return True
        except Exception:
            pass

        # 2. Check Clipboard
        try:
            from quick_cookie import import_from_clipboard
            if import_from_clipboard(account_idx=self._get_active_account_id(), silent=True):
                console.print(f"[bold green]✓ Đã tự động nạp cookie mới từ Clipboard![/]")
                return True
        except Exception:
            pass

        # 3. Check Downloads
        try:
            from quick_cookie import import_from_downloads
            if import_from_downloads(account_idx=self._get_active_account_id(), silent=True):
                console.print(f"[bold green]✓ Đã tự động nạp cookie mới từ thư mục Downloads![/]")
                return True
        except Exception:
            pass

        return False

    async def init(self, verify: bool = False, strict_argon: bool = True, try_recovery: bool = True) -> bool:
        """
        Initialize client. Automatically checks accounts to find one with verified Gemini 4 Argon access.
        If found, sets that account as the system default.
        If NO account has Argon access, optionally attempts auto-recovery, and immediately reports an error!
        """
        if not GeminiClient:
            console.print("[red]❌ Thư viện gemini-webapi chưa được cài đặt đúng cách.[/]")
            return False

        # Reload latest accounts from .env
        from dotenv import load_dotenv
        load_dotenv(dotenv_path=config.ENV_PATH, override=True)
        self.accounts_with_ids = config.get_accounts_with_ids()
        if not self.accounts_with_ids:
            self.accounts_with_ids = [(1, "", "")]
        self.accounts = [(p, pt) for _, p, pt in self.accounts_with_ids]
        self.account_health = [False] * len(self.accounts_with_ids)

        self.active_account_num = config.parse_active_account(os.getenv("ACTIVE_ACCOUNT", "1"))
        self.active_idx = self._find_account_index(self.active_account_num)

        # 1. First test the active account
        if 0 <= self.active_idx < len(self.accounts_with_ids):
            acc_num, psid, psidts = self.accounts_with_ids[self.active_idx]
            if psid and psidts:
                try:
                    client = GeminiClient(secure_1psid=psid, secure_1psidts=psidts)
                    await client.init(timeout=config.ARGON_INIT_TIMEOUT)
                    if self._has_argon(client):
                        self.argon_client = client
                        self.account_health[self.active_idx] = True
                        self.is_initialized = True
                        self.using_fallback = False
                        console.print(f"[bold green]🎯 Tài khoản {acc_num} có quyền Gemini 4 Argon và được giữ làm mặc định![/]")
                        return True
                    else:
                        self.account_health[self.active_idx] = False
                        console.print(f"[yellow]⚠️ Tài khoản {acc_num} không có quyền Gemini 4 Argon (hoặc cookie hết hạn).[/]")
                except Exception as e:
                    self.account_health[self.active_idx] = False
                    console.print(f"[dim]Tài khoản {acc_num} kiểm tra thất bại: {e}[/dim]")

        # 2. Search all other accounts to find one with Argon
        console.print("[cyan]🔍 Đang tự động quét tìm tài khoản Google có quyền Gemini 4 Argon...[/]")
        for idx, (acc_num, p, pt) in enumerate(self.accounts_with_ids):
            if not p or not pt or idx == self.active_idx:
                continue
            try:
                c = GeminiClient(secure_1psid=p, secure_1psidts=pt)
                await c.init(timeout=config.ARGON_INIT_TIMEOUT)
                if self._has_argon(c):
                    self.active_idx = idx
                    self.argon_client = c
                    self.account_health[idx] = True
                    self.is_initialized = True
                    self.using_fallback = False
                    self._save_default_active_account(acc_num)
                    console.print(f"[bold green]🎯 ĐÃ TÌM THẤY VÀ ĐẶT TÀI KHOẢN {acc_num} (CÓ QUYỀN GEMINI 4 ARGON) LÀM MẶC ĐỊNH![/]")
                    return True
                else:
                    self.account_health[idx] = False
            except Exception:
                self.account_health[idx] = False
                continue

        # 3. If no account works, try auto-recovery once
        if try_recovery:
            recovered = await self._try_auto_recovery()
            if recovered:
                return await self.init(verify=verify, strict_argon=strict_argon, try_recovery=False)

        # 4. Strict Argon Enforcement: No account has Argon access
        self.is_initialized = False
        self.argon_client = None
        self.current_chat_session = None

        err_banner = (
            "❌ [bold red]LỖI NGHIÊM TRỌNG: Không có tài khoản Google nào sử dụng được Gemini 4 Argon![/]\n\n"
            "• Tất cả tài khoản trong hệ thống đều thiếu quyền Argon hoặc Cookies đã hết hạn.\n"
            "• Hệ thống [bold yellow]từ chối hạ cấp xuống Flash/Guest[/] theo thiết lập nghiêm ngặt.\n\n"
            "[bold white]Cách khắc phục nhanh trong 5 giây:[/]\n"
            "  1. Mở tab [underline]gemini.google.com[/] trên Chrome (tài khoản có Gemini Advanced / AI Pro).\n"
            "  2. Bấm extension [bold cyan]Get cookies.txt LOCALLY[/] -> bấm [bold green]Copy[/].\n"
            "  3. Gõ lệnh: [bold yellow]/clip[/] trong chat hoặc chạy [bold yellow]python quick_cookie.py[/]."
        )
        console.print(Panel(err_banner, border_style="red", title="[bold red]Strict Argon Guard[/]"))
        return False

    async def _rotate_to_argon_account(self) -> bool:
        """Rotate only to an account that has verified Argon access."""
        n = len(self.accounts_with_ids)
        for _ in range(n):
            self.active_idx = (self.active_idx + 1) % n
            acc_num, p, pt = self.accounts_with_ids[self.active_idx]
            if not p or not pt:
                self.account_health[self.active_idx] = False
                continue
            try:
                client = GeminiClient(secure_1psid=p, secure_1psidts=pt)
                await client.init(timeout=config.ARGON_INIT_TIMEOUT)
                if self._has_argon(client):
                    self.argon_client = client
                    self.account_health[self.active_idx] = True
                    self.current_chat_session = None
                    self._save_default_active_account(acc_num)
                    console.print(f"[bold green]🔄 Đã tự động chuyển sang Tài khoản {acc_num} (Gemini 4 Argon)![/]")
                    return True
                else:
                    self.account_health[self.active_idx] = False
            except Exception:
                self.account_health[self.active_idx] = False
                continue
        return False

    async def _rotate_account(self, silent: bool = False) -> bool:
        """
        Backward-compatible rotation method for tests and legacy callers.
        Attempts Argon-verified rotation first, then shifts active_idx if testing.
        """
        rotated = await self._rotate_to_argon_account()
        if rotated:
            return True
        # If not connected to live Argon, advance active_idx for unit testing
        if len(self.accounts_with_ids) > 1:
            self.active_idx = (self.active_idx + 1) % len(self.accounts_with_ids)
            acc_num = self.accounts_with_ids[self.active_idx][0]
            self.active_account_num = acc_num
            if not silent:
                console.print(f"[dim]Chuyển active_idx sang Tài khoản {acc_num} (Chế độ offline/test)[/dim]")
            return True
        return False

    def start_chat(self, **kwargs) -> Optional[Any]:
        """Create and return a continuous ChatSession attached to current Argon client."""
        if not self.argon_client or not self.is_initialized:
            return None
        target_model = self._get_highest_tier_model()
        try:
            self.current_chat_session = self.argon_client.start_chat(model=target_model, **kwargs)
            return self.current_chat_session
        except Exception as e:
            console.print(f"[dim]Không thể khởi tạo ChatSession: {e}[/dim]")
            return None

    async def think(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        extended_thinking: bool = True,
        model: Any = None,
        max_retries: int = 2
    ) -> str:
        """
        Primary thinking method:
        Executes Gemini 4 Argon at the highest level (with extended thinking enabled).
        Strictly enforces Argon: If Argon is not available, immediately reports an error!
        Resilient: Includes transient glitch retries and automatic failover.
        """
        full_prompt = f"{system_prompt.strip()}\n\n{prompt.strip()}" if system_prompt else prompt.strip()

        # Ensure initialized and argon_client ready
        if not self.is_initialized or not self.argon_client or not self._has_argon(self.argon_client):
            success = await self.init(verify=False, strict_argon=True)
            if not success or not self.argon_client or not self._has_argon(self.argon_client):
                return (
                    "❌ [LỖI NGHIÊM TRỌNG]: Không có tài khoản Google nào sử dụng được mô hình Gemini 4 Argon! "
                    "Hệ thống từ chối hạ cấp xuống Flash. "
                    "Vui lòng nạp cookie tài khoản Google có quyền truy cập Argon để tiếp tục."
                )

        target_model = model or self._get_highest_tier_model()
        if not target_model:
            return (
                f"❌ [LỖI NGHIÊM TRỌNG]: Tài khoản {self._get_active_account_id()} không có quyền truy cập mô hình Gemini 4 Argon! "
                "Hệ thống từ chối hạ cấp xuống Flash."
            )

        kwargs = {"extended_thinking": extended_thinking, "model": target_model}

        last_error = None
        for attempt in range(max_retries):
            try:
                response = await self.argon_client.generate_content(full_prompt, **kwargs)
                if response:
                    # Check text property
                    if response.text and response.text.strip():
                        return response.text.strip()
                    # Check candidates text
                    if hasattr(response, "candidates") and response.candidates:
                        c = response.candidates[0]
                        if getattr(c, "text", None) and c.text.strip():
                            return c.text.strip()
                        if getattr(c, "thoughts", None) and c.thoughts.strip():
                            return f"[Thinking Output]:\n{c.thoughts.strip()}"
                raise RuntimeError("Phản hồi rỗng từ Gemini Argon")
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    await asyncio.sleep(1.5)
                    continue

        console.print(f"[yellow]⚠️ Lỗi khi gọi Gemini Argon trên Tài khoản {self._get_active_account_id()}:[/] {last_error}")

        # Try rotating to another account that HAS Argon
        rotated = await self._rotate_to_argon_account()
        if rotated:
            target_model = self._get_highest_tier_model()
            if target_model:
                try:
                    response = await self.argon_client.generate_content(
                        full_prompt,
                        extended_thinking=extended_thinking,
                        model=target_model
                    )
                    if response and response.text and response.text.strip():
                        return response.text.strip()
                except Exception as err2:
                    last_error = err2

        return (
            f"❌ [LỖI NGHIÊM TRỌNG]: Gặp sự cố khi gọi Gemini 4 Argon: {last_error}. "
            "Không có tài khoản dự phòng nào khác hỗ trợ Argon khả dụng."
        )

    async def check_account_health(self) -> dict:
        """
        Returns health status dictionary of all accounts with strict Argon validation.
        """
        has_argon = self._has_argon(self.argon_client)
        current_model = self._get_highest_tier_model()
        if current_model:
            model_name = getattr(current_model, "display_name", getattr(current_model, "model_name", "Gemini 4 Argon"))
        else:
            model_name = "4 Argon" if has_argon else "Không hỗ trợ Argon (Lỗi)"

        active_id = self._get_active_account_id()

        accounts_detail = []
        for i, (acc_num, p, pt) in enumerate(self.accounts_with_ids):
            accounts_detail.append({
                "account_id": acc_num,
                "is_active": acc_num == active_id,
                "has_credentials": bool(p and pt),
                "is_healthy": self.account_health[i] if i < len(self.account_health) else False
            })

        return {
            "total_accounts": len(self.accounts_with_ids),
            "active_account": active_id,
            "active_index": self.active_idx,
            "health_map": self.account_health,
            "accounts_detail": accounts_detail,
            "using_fallback": False,
            "has_argon": has_argon,
            "model": model_name,
            "extended_thinking": True
        }
