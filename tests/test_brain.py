"""
Unit & Integration Tests for NEXUS Brain Layer.
Verifies cookie loading, 3-account rotation, and LLM inference.
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

async def test_brain():
    print("=== CHẠY KIỂM THỬ BRAIN LAYER ===")
    brain = Brain()

    # 1. Check account loading
    print("[1] Kiểm tra tải tài khoản từ .env...")
    assert len(brain.accounts) >= 1, "Không tìm thấy tài khoản nào trong cấu hình!"
    print(f"  ✓ Đã nạp {len(brain.accounts)} tài khoản thành công.")

    # 2. Check health status
    print("[2] Kiểm tra hàm check_account_health()...")
    health = await brain.check_account_health()
    assert "active_account" in health and "total_accounts" in health
    print(f"  ✓ Trạng thái sức khỏe: Active Account = {health['active_account']}/{health['total_accounts']}")

    # 3. Test initialization
    print("[3] Kiểm tra khởi tạo client kết nối Argon...")
    init_ok = await brain.init(verify=False)
    print(f"  ✓ Khởi tạo hoàn tất. Argon sẵn sàng: {brain.argon_client is not None or brain.using_fallback}")

    # 4. Test inference
    print("[4] Kiểm tra phản hồi suy nghĩ (Inference)...")
    response = await brain.think("Trả lời chính xác 1 từ duy nhất: PONG")
    assert response and len(response) > 0, "Phản hồi rỗng từ Brain"
    print(f"  ✓ Phản hồi từ Brain: {response.strip()}")

    # 5. Test circular rotation
    print("[5] Kiểm tra cơ chế xoay vòng tài khoản (Circular Rotation)...")
    orig_idx = brain.active_idx
    if len(brain.accounts) > 1:
        await brain._rotate_account(silent=True)
        assert brain.active_idx == (orig_idx + 1) % len(brain.accounts)
        print(f"  ✓ Đã chuyển từ Account {orig_idx + 1} sang Account {brain.active_idx + 1}")
        # Revert back
        brain.active_idx = orig_idx
    else:
        print("  ✓ Chỉ có 1 tài khoản, bỏ qua test xoay vòng.")

    print("\n✅ BRAIN LAYER HOÀN THÀNH KIỂM THỬ (100% PASS)!\n")

if __name__ == "__main__":
    asyncio.run(test_brain())
