"""
Unit & Integration Tests for NEXUS Tools.
"""

import sys
import os
import asyncio
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from tools.filesystem import FileSystemTool
from tools.shell import ShellTool
from tools.web_search import WebSearchTool
from tools.tts_engine import TTSEngine
from tools.image_generator import ImageGeneratorTool
from tools.youtube_api import YouTubeAPITool
from core.tool_registry import ToolRegistry

async def test_filesystem():
    print("[TEST] FileSystemTool...")
    fs = FileSystemTool()
    test_file = PROJECT_ROOT / "temp_test_file.txt"
    try:
        # Write
        w_res = await fs.write_file(str(test_file), "Xin chào NEXUS")
        assert "SUCCESS" in w_res, f"Write failed: {w_res}"

        # Read
        r_res = await fs.read_file(str(test_file))
        assert r_res == "Xin chào NEXUS", f"Read mismatch: {r_res}"

        # List
        l_res = await fs.list_dir(str(PROJECT_ROOT))
        assert "temp_test_file.txt" in l_res, "File not in list_dir"

        # Search
        s_res = await fs.search_files("temp_test_file.txt", str(PROJECT_ROOT))
        assert "temp_test_file.txt" in s_res, "Search failed"
        print("  ✓ FileSystemTool passed")
    finally:
        if test_file.exists():
            test_file.unlink()

async def test_shell():
    print("[TEST] ShellTool...")
    sh = ShellTool()
    res = await sh.execute("echo HELLO_FROM_SHELL")
    assert "HELLO_FROM_SHELL" in res, f"Shell output unexpected: {res}"
    print("  ✓ ShellTool passed")

async def test_web_search():
    print("[TEST] WebSearchTool...")
    ws = WebSearchTool()
    res = await ws.search("Python 3 programming", max_results=2)
    assert "KẾT QUẢ TÌM KIẾM" in res or "http" in res, f"Search failed: {res}"
    print("  ✓ WebSearchTool passed")

async def test_tts():
    print("[TEST] TTSEngine...")
    tts = TTSEngine()
    out_file = PROJECT_ROOT / "temp_test_voice.mp3"
    try:
        res = await tts.edge_tts_generate("NEXUS xin chào bạn", output=str(out_file))
        assert out_file.exists() and out_file.stat().st_size > 0, "TTS file not generated"
        print("  ✓ TTSEngine passed")
    finally:
        if out_file.exists():
            out_file.unlink()

async def test_image_gen():
    print("[TEST] ImageGeneratorTool...")
    img_gen = ImageGeneratorTool()
    out_file = PROJECT_ROOT / "temp_test_banner.png"
    try:
        res = await img_gen.generate("NEXUS Multi-Agent AI System", output=str(out_file))
        assert out_file.exists() and out_file.stat().st_size > 0, "Image file not generated"
        print("  ✓ ImageGeneratorTool passed")
    finally:
        if out_file.exists():
            out_file.unlink()

async def test_registry():
    print("[TEST] ToolRegistry...")
    reg = ToolRegistry()
    reg.register(FileSystemTool())
    reg.register(ShellTool())
    assert "filesystem" in reg.list_names()
    assert "shell" in reg.list_names()
    print("  ✓ ToolRegistry passed")

async def main():
    print("=== CHẠY KIỂM THỬ TẤT CẢ CÔNG CỤ (TOOLS) ===")
    await test_filesystem()
    await test_shell()
    await test_web_search()
    await test_tts()
    await test_image_gen()
    await test_registry()
    print("\n✅ TẤT CẢ CÔNG CỤ ĐÃ VƯỢT QUA KIỂM THỬ (100% PASS)!\n")

if __name__ == "__main__":
    asyncio.run(main())
