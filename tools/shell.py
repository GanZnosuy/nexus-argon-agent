"""
NEXUS Shell Execution Tool.
Executes Windows PowerShell / CMD commands asynchronously with safety timeouts.
"""

import asyncio
import subprocess
import os
from typing import Optional

class ShellTool:
    name = "shell"
    description = "Execute terminal commands on Windows with timeout and output capture"

    async def run(self, command: str = "", cmd: str = "", cwd: Optional[str] = None, timeout: int = 120, **kwargs) -> str:
        """Universal entry point for tool execution."""
        command_to_run = command or cmd
        if not command_to_run:
            return "[ERROR] Không có lệnh nào được chỉ định để thực thi."
        return await self.execute(command_to_run, cwd=cwd, timeout=timeout)

    async def execute(self, command: str, cwd: Optional[str] = None, timeout: int = 120) -> str:
        """
        Execute command asynchronously in thread executor to prevent blocking the event loop.
        """
        def _sync_run():
            try:
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    cwd=cwd,
                    timeout=timeout,
                    encoding="utf-8",
                    errors="replace"
                )
                output = (result.stdout or "") + (result.stderr or "")
                # Truncate if output is excessively long
                truncated = output[-4000:] if len(output) > 4000 else output
                status = f"[Exit Code: {result.returncode}]"
                return f"{status}\n{truncated.strip()}"
            except subprocess.TimeoutExpired:
                return f"[ERROR] Lệnh bị quá thời gian cho phép ({timeout}s): {command}"
            except Exception as e:
                return f"[ERROR] Không thể thực thi lệnh: {str(e)}"

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _sync_run)
