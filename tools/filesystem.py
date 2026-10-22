"""
NEXUS FileSystem Tool.
Read, write, list, and search files on the local filesystem with full UTF-8 support.
"""

import os
import glob
from pathlib import Path
from typing import Optional

class FileSystemTool:
    name = "filesystem"
    description = "Read, write, list, search, and manage files on the local computer"

    async def run(self, action: str, **kwargs) -> str:
        """Universal dispatcher for the tool registry."""
        actions = {
            "read_file": self.read_file,
            "write_file": self.write_file,
            "list_dir": self.list_dir,
            "search_files": self.search_files,
            "delete_file": self.delete_file,
        }
        handler = actions.get(action)
        if not handler:
            return f"[ERROR] Action '{action}' không hợp lệ. Hỗ trợ: {list(actions.keys())}"
        return await handler(**kwargs)

    async def read_file(self, path: str) -> str:
        """Read content of a file with UTF-8 encoding."""
        try:
            target = Path(path).resolve()
            if not target.exists():
                return f"[ERROR] Tệp không tồn tại: {path}"
            if target.is_dir():
                return f"[ERROR] Đường dẫn là thư mục, không phải tệp: {path}"

            with open(target, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            return content
        except Exception as e:
            return f"[ERROR] Không thể đọc tệp {path}: {str(e)}"

    async def write_file(self, path: str, content: str) -> str:
        """Write content to a file, automatically creating parent directories."""
        try:
            target = Path(path).resolve()
            target.parent.mkdir(parents=True, exist_ok=True)
            with open(target, "w", encoding="utf-8") as f:
                f.write(content)
            return f"[SUCCESS] Đã ghi tệp thành công: {target}"
        except Exception as e:
            return f"[ERROR] Không thể ghi tệp {path}: {str(e)}"

    async def list_dir(self, path: str = ".") -> str:
        """List files and folders in a directory."""
        try:
            target = Path(path).resolve()
            if not target.exists():
                return f"[ERROR] Thư mục không tồn tại: {path}"
            if not target.is_dir():
                return f"[ERROR] Đường dẫn không phải là thư mục: {path}"

            entries = []
            for item in sorted(target.iterdir()):
                prefix = "[DIR] " if item.is_dir() else "[FILE]"
                size_str = f" ({item.stat().st_size} bytes)" if item.is_file() else ""
                entries.append(f"{prefix} {item.name}{size_str}")

            if not entries:
                return f"[EMPTY] Thư mục rỗng: {path}"
            return "\n".join(entries)
        except Exception as e:
            return f"[ERROR] Không thể liệt kê thư mục {path}: {str(e)}"

    async def search_files(self, pattern: str, directory: str = ".") -> str:
        """Search files matching glob pattern recursively."""
        try:
            base_path = Path(directory).resolve()
            matches = list(base_path.glob(f"**/{pattern}"))
            if not matches:
                return f"[INFO] Không tìm thấy tệp khớp mẫu '{pattern}' trong {directory}"
            return "\n".join(str(m) for m in matches[:50])
        except Exception as e:
            return f"[ERROR] Lỗi khi tìm kiếm tệp: {str(e)}"

    async def delete_file(self, path: str) -> str:
        """Delete a file safely."""
        try:
            target = Path(path).resolve()
            if not target.exists():
                return f"[ERROR] Tệp không tồn tại: {path}"
            if target.is_dir():
                return f"[ERROR] Không thể xóa thư mục bằng delete_file: {path}"
            target.unlink()
            return f"[SUCCESS] Đã xóa tệp: {path}"
        except Exception as e:
            return f"[ERROR] Không thể xóa tệp: {str(e)}"
