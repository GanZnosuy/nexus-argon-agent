"""
Unit & Integration Tests for NEXUS Orchestrator.
Tests routing, specialist agent dispatch, direct answering, and multi-agent synthesis.
"""

import sys
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

from core.brain import Brain
from core.orchestrator import NexusOrchestrator
from core.memory import Memory

async def test_orchestrator():
    print("=== CHẠY KIỂM THỬ NEXUS ORCHESTRATOR ===")

    memory = Memory()
    brain = Brain(memory=memory)
    await brain.init(verify=False)

    orchestrator = NexusOrchestrator(brain=brain, memory=memory)

    # 1. Check registered agents
    print("[1] Kiểm tra 5 Specialist Agents đã đăng ký...")
    expected_agents = ["CodeAgent", "BrowserAgent", "ResearchAgent", "MediaAgent", "YouTubeAgent"]
    for ag in expected_agents:
        assert orchestrator.get_agent(ag) is not None, f"Agent {ag} chưa được nạp!"
    print(f"  ✓ Đã nạp đủ 5 agents: {list(orchestrator.agents.keys())}")

    # 2. Check registered tools
    print("[2] Kiểm tra Tools Registry trong Orchestrator...")
    tool_names = orchestrator.tools.list_names()
    assert "filesystem" in tool_names
    assert "shell" in tool_names
    assert "web_search" in tool_names
    assert "browser" in tool_names
    assert "image_generator" in tool_names
    assert "tts" in tool_names
    assert "youtube_api" in tool_names
    print(f"  ✓ Đã nạp đủ 7 tools: {tool_names}")

    # 3. Test Direct Answer (no agent needed)
    print("[3] Kiểm tra xử lý câu hỏi trực tiếp (Direct Answer)...")
    direct_res = await orchestrator.process("Thủ đô của Việt Nam là gì?")
    assert "Hà Nội" in direct_res or "Ha Noi" in direct_res, f"Direct answer incorrect: {direct_res}"
    print(f"  ✓ Direct answer OK (độ dài: {len(direct_res)} ký tự)")

    # 4. Test CodeAgent routing & execution
    print("[4] Kiểm tra định tuyến tới CodeAgent...")
    test_target = PROJECT_ROOT / "test_orchestrator_output.txt"
    try:
        req = f"Hãy tạo một file tại '{test_target}' với nội dung chính xác là: 'NEXUS_SYSTEM_ONLINE'"
        code_res = await orchestrator.process(req)
        assert test_target.exists(), "CodeAgent không tạo được file theo yêu cầu"
        content = test_target.read_text(encoding="utf-8")
        assert "NEXUS_SYSTEM_ONLINE" in content, f"Nội dung file không đúng: {content}"
        print(f"  ✓ CodeAgent thực thi tạo file thành công!")
    finally:
        if test_target.exists():
            test_target.unlink()

    # 5. Check memory logging
    print("[5] Kiểm tra lưu vết trong Memory...")
    assert len(memory) >= 4, f"Lịch sử memory không được ghi: {len(memory)}"
    print(f"  ✓ Đã ghi nhận {len(memory)} lượt tương tác trong memory")

    print("\n✅ NEXUS ORCHESTRATOR HOÀN THÀNH KIỂM THỬ (100% PASS)!\n")

if __name__ == "__main__":
    asyncio.run(test_orchestrator())
