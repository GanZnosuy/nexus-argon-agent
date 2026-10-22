"""
Integration test for NEXUS MCP Server.
Simulates Antigravity JSON-RPC 2.0 handshake and tool execution over stdin/stdout.
"""

import sys
import subprocess
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

def test_mcp_server():
    print("=== KIỂM THỬ NEXUS MCP SERVER QUA STDIO ===")

    init_req = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}) + "\n"
    list_req = json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}) + "\n"
    status_req = json.dumps({"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "nexus_status", "arguments": {}}}) + "\n"

    python_bin = sys.executable
    server_script = str(PROJECT_ROOT / "nexus_mcp.py")

    proc = subprocess.Popen(
        [python_bin, server_script],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        cwd=str(PROJECT_ROOT)
    )

    combined_input = init_req + list_req + status_req
    stdout, stderr = proc.communicate(input=combined_input, timeout=30)

    lines = [line.strip() for line in stdout.strip().splitlines() if line.strip()]
    assert len(lines) >= 3, f"Expected at least 3 JSON responses, got: {len(lines)}\nStderr: {stderr}"

    # Response 1: initialize
    res1 = json.loads(lines[0])
    assert res1["id"] == 1
    assert res1["result"]["serverInfo"]["name"] == "nexus-agent"
    print("  ✓ Handshake initialize: OK (server: nexus-agent)")

    # Response 2: tools/list
    res2 = json.loads(lines[1])
    assert res2["id"] == 2
    tools = res2["result"]["tools"]
    tool_names = [t["name"] for t in tools]
    assert "nexus_process" in tool_names
    assert "nexus_argon_think" in tool_names
    assert "nexus_status" in tool_names
    print(f"  ✓ Tools discovery: OK ({len(tools)} tools exposed: {tool_names[:4]}...)")

    # Response 3: tools/call (nexus_status)
    res3 = json.loads(lines[2])
    assert res3["id"] == 3
    content_text = res3["result"]["content"][0]["text"]
    assert "NEXUS" in content_text
    print(f"  ✓ Tool execution (nexus_status): OK\n{content_text}")

    print("\n✅ NEXUS MCP SERVER HOÀN THÀNH KIỂM THỬ (100% PASS)!\n")

if __name__ == "__main__":
    test_mcp_server()
