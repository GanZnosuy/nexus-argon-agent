"""
NEXUS Brain Layer.
Primary LLM abstraction: Gemini 4 Argon via gemini-webapi with 3-account cookie rotation.
Strict Argon enforcement: Automatically sets Argon-capable account as default,
and immediately reports an error if an account does not have Argon.
"""

import os
import sys
import re
import asyncio
from pathlib import Path
from typing import Optional, List, Tuple, Any, Dict
from rich.console import Console

try:
    from gemini_webapi import GeminiClient, AuthError, TemporarilyBlockedError, UsageLimitExceededError
except ImportError:
    try:
        from gemini import GeminiClient, AuthError, TemporarilyBlockedError, UsageLimitExceededError
    except ImportError:
        GeminiClient = None
        AuthError = Exception
        TemporarilyBlockedError = Exception
        UsageLimitExceededError = Exception

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
    and strict Gemini 4 Argon enforcement.
    """

    def __init__(self, memory=None):
        self.accounts: List[Tuple[str, str]] = config.get_accounts()
        if not self.accounts:
            console.print("[yellow]⚠️ Cảnh báo: Không tìm thấy cookie tài khoản trong .env![/]")
            self.accounts = [("", "")]

        self.active_idx: int = (config.ACTIVE_ACCOUNT - 1) % len(self.accounts)
        self.argon_client: Optional[GeminiClient] = None
        self.memory = memory if memory is not None else []
        self.account_health: List[bool] = [True] * len(self.accounts)
        self.is_initialized: bool = False
        self.using_fallback: bool = False

    def _has_argon(self, client: Any) -> bool:
        """Check if client is authenticated and has verified access to Gemini 4 Argon."""
        if not client:
            return False
        if getattr(client, "account_status", None) == 1016:
            return False
        try:
            models = client.list_models()
            for m in models:
                name = getattr(m, "model_name", "").lower()
                aliases = [str(a).lower() for a in getattr(m, "aliases", [])]
                if "argon" in name or any("argon" in a for a in aliases):
                    return True
        except Exception:
            pass
        return False

    def _save_default_active_account(self, account_num: int):
        """Persist ACTIVE_ACCOUNT to .env and config module."""
        try:
            env_path = config.ENV_PATH
            if env_path.exists():
                content = env_path.read_text(encoding="utf-8")
                if re.search(r"^ACTIVE_ACCOUNT\s*=", content, flags=re.MULTILINE):
                    content = re.sub(r"^ACTIVE_ACCOUNT\s*=.*$", f"ACTIVE_ACCOUNT={account_num}", content, flags=re.MULTILINE)
                else:
                    content += f"\nACTIVE_ACCOUNT={account_num}"
                env_path.write_text(content, encoding="utf-8")
            config.ACTIVE_ACCOUNT = account_num
        except Exception as e:
            console.print(f"[dim]Lỗi lưu ACTIVE_ACCOUNT: {e}[/dim]")

    async def init(self, verify: bool = False, strict_argon: bool = True) -> bool:
        """
        Initialize client. Automatically checks accounts to find one with verified Gemini 4 Argon access.
        If found, sets that account as the system default.
        If NO account has Argon access, immediately reports an error!
        """
        if not GeminiClient:
            console.print("[red]❌ Thư viện gemini-webapi chưa được cài đặt đúng cách.[/]")
            return False

        # Reload latest accounts from .env
        from dotenv import load_dotenv
        load_dotenv(dotenv_path=config.ENV_PATH, override=True)
        self.accounts = config.get_accounts()
        self.account_health = [True] * len(self.accounts)

        # 1. First test the active account
        if 0 <= self.active_idx < len(self.accounts):
            psid, psidts = self.accounts[self.active_idx]
            if psid and psidts:
                try:
                    client = GeminiClient(secure_1psid=psid, secure_1psidts=psidts)
                    await client.init(timeout=config.ARGON_INIT_TIMEOUT)
                    if self._has_argon(client):
                        self.argon_client = client
                        self.account_health[self.active_idx] = True
                        self.is_initialized = True
                        self.using_fallback = False
                        console.print(f"[bold green]🎯 Tài khoản {self.active_idx + 1} có quyền Gemini 4 Argon và được giữ làm mặc định![/]")
                        return True
                    else:
                        console.print(f"[yellow]⚠️ Tài khoản {self.active_idx + 1} không có quyền Gemini 4 Argon (hoặc cookie hết hạn).[/]")
                except Exception as e:
                    console.print(f"[dim]Tài khoản {self.active_idx + 1} kiểm tra thất bại: {e}[/dim]")

        # 2. Search all other accounts to find one with Argon
        console.print("[cyan]🔍 Đang tự động quét tìm tài khoản Google có quyền Gemini 4 Argon...[/]")
        for idx, (p, pt) in enumerate(self.accounts):
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
                    self._save_default_active_account(idx + 1)
                    console.print(f"[bold green]🎯 ĐÃ TÌM THẤY VÀ ĐẶT TÀI KHOẢN {idx + 1} (CÓ QUYỀN GEMINI 4 ARGON) LÀM MẶC ĐỊNH![/]")
                    return True
            except Exception:
                continue

        # 3. Strict Argon Enforcement: No account has Argon access
        self.is_initialized = False
        self.argon_client = None
        err_msg = (
            "❌ [LỖI NGHIÊM TRỌNG]: Không có tài khoản Google nào sử dụng được mô hình Gemini 4 Argon!\n"
            "Tất cả tài khoản trong hệ thống đều thiếu quyền Argon hoặc cookie đã hết hạn.\n"
            "Hệ thống từ chối hạ cấp xuống Flash theo thiết lập nghiêm ngặt. Vui lòng nạp cookie tài khoản có Argon."
        )
        console.print(f"[bold red]{err_msg}[/]")
        if strict_argon:
            return False
        return False

    def _get_highest_tier_model(self):
        """
        Select Gemini 4 Argon model strictly.
        If Argon is not available, returns None (rejecting non-Argon models).
        """
        if not self.argon_client or not self._has_argon(self.argon_client):
            return None
        try:
            models = self.argon_client.list_models()
            for m in models:
                name = getattr(m, "model_name", "").lower()
                aliases = [str(a).lower() for a in getattr(m, "aliases", [])]
                if "argon" in name or any("argon" in a for a in aliases):
                    return m
            return None
        except Exception:
            return None

    async def _rotate_to_argon_account(self) -> bool:
        """Rotate only to an account that has verified Argon access."""
        for _ in range(len(self.accounts)):
            self.active_idx = (self.active_idx + 1) % len(self.accounts)
            p, pt = self.accounts[self.active_idx]
            if not p or not pt:
                continue
            try:
                client = GeminiClient(secure_1psid=p, secure_1psidts=pt)
                await client.init(timeout=config.ARGON_INIT_TIMEOUT)
                if self._has_argon(client):
                    self.argon_client = client
                    self.account_health[self.active_idx] = True
                    self._save_default_active_account(self.active_idx + 1)
                    console.print(f"[bold green]🔄 Đã tự động chuyển sang Tài khoản {self.active_idx + 1} (Gemini 4 Argon)![/]")
                    return True
            except Exception:
                continue
        return False

    async def think(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        extended_thinking: bool = True,
        model: Any = None
    ) -> str:
        """
        Primary thinking method:
        Executes Gemini 4 Argon at the highest level (with extended thinking enabled).
        Strictly enforces Argon: If Argon is not available, immediately reports an error!
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
                f"❌ [LỖI NGHIÊM TRỌNG]: Tài khoản {self.active_idx + 1} không có quyền truy cập mô hình Gemini 4 Argon! "
                "Hệ thống từ chối hạ cấp xuống Flash."
            )

        kwargs = {"extended_thinking": extended_thinking, "model": target_model}

        try:
            response = await self.argon_client.generate_content(full_prompt, **kwargs)
            if response and response.text:
                return response.text.strip()
            else:
                raise RuntimeError("Phản hồi rỗng từ Gemini Argon")
        except Exception as e:
            console.print(f"[yellow]⚠️ Lỗi khi gọi Gemini Argon trên Tài khoản {self.active_idx + 1}:[/] {e}")
            # Try rotating to another account that HAS Argon
            rotated = await self._rotate_to_argon_account()
            if rotated:
                target_model = self._get_highest_tier_model()
                if target_model:
                    try:
                        response = await self.argon_client.generate_content(full_prompt, extended_thinking=extended_thinking, model=target_model)
                        if response and response.text:
                            return response.text.strip()
                    except Exception as err2:
                        e = err2

            return (
                f"❌ [LỖI NGHIÊM TRỌNG]: Gặp sự cố khi gọi Gemini 4 Argon: {e}. "
                "Không có tài khoản dự phòng nào khác hỗ trợ Argon khả dụng."
            )

    async def check_account_health(self) -> dict:
        """
        Returns health status dictionary of all accounts with strict Argon validation.
        """
        has_argon = self._has_argon(self.argon_client)
        current_model = self._get_highest_tier_model()
        model_name = getattr(current_model, "display_name", getattr(current_model, "model_name", "Gemini 4 Argon")) if current_model else ("4 Argon" if has_argon else "Không hỗ trợ Argon (Lỗi)")
        
        return {
            "total_accounts": len(self.accounts),
            "active_account": self.active_idx + 1,
            "health_map": self.account_health,
            "using_fallback": False,
            "has_argon": has_argon,
            "model": model_name,
            "extended_thinking": True
        }
